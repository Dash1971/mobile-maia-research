"""Summarize and verify the independently frozen Ginger comparison."""
import argparse
import gzip
import html
import io
import json
from pathlib import Path
import subprocess

import chess
import chess.pgn
import chess.svg

ROOT=Path(__file__).resolve().parents[1]
FROZEN='6844202bf606211c11a27b777560cf009293f30f'
OLD='En Croissant (adapted)'
NEW='Open Brilly Finder'
FIELDS=('games','scoredMoves','targets','oldHits','newHits','oldAwards','newAwards','oldOutside','newOutside','gainedTargets','lostTargets')

def labelmap(run,algorithm,stage='final'):
    return {x['ply']:x['label'] for x in run[algorithm][stage]}

def name(g,ply):
    return f'{(ply+1)//2}'+('.' if ply%2 else '...')+g['sans'][ply-1]

def escape(s):return html.escape(str(s))

def board_svg(board,prefix):
    text=chess.svg.board(board,size=300)
    return text.replace('id="','id="'+prefix).replace('href="#','href="#'+prefix)

def verify(raw,games):
    for filename in ('PLAN.md','gallery-selection.json','games.pgn','games.json','overlap-audit.json'):
        path=ROOT/'ginger'/filename
        frozen=subprocess.check_output(['git','-C',str(ROOT),'show',f'{FROZEN}:{path.relative_to(ROOT.parents[1])}'])
        assert frozen==path.read_bytes(),('Frozen file changed',filename)
    assert raw['planCommit']==FROZEN
    assert raw['appSource']=='096591bd8d42759e5a3f3a288d56d7c93245d6d1'
    assert raw['modelSource']=='59cab58a8b63387d9775252f03a6875fe451f697'
    assert raw['modelSha256']=='992a792a646b11e612486c4fe26796fc38ee47f395f2220b00d26db65ba1e27d'
    assert raw['cutoff']==0.8193002847777424
    assert (raw['threads'],raw['hashMiB'],raw['multiPV'])==(1,64,2)
    assert raw['engine']['binarySha256']=='ae4c93fa9676ca7750d0714342fd8a5b1d018000fc6e0f6cedf112067b5ef374'
    assert len(games)==len(raw['runs'])==27
    runs={r['game']:r for r in raw['runs']}
    assert len(runs)==27
    total_positions=0
    for g in games:
        r=runs[g['id']]
        assert r['quality']=='fast' and len(r['scores'])==len(g['positions'])==len(g['moves'])+1
        board=chess.Board(g['positions'][0])
        for ply,uci in enumerate(g['moves'],1):
            move=chess.Move.from_uci(uci)
            assert move in board.legal_moves and board.san(move)==g['sans'][ply-1]
            board.push(move)
            assert board.fen()==g['positions'][ply]
        for fen,score in zip(g['positions'],r['scores']):
            board=chess.Board(fen)
            if not score['lines']:
                assert board.is_game_over();continue
            assert score['evidence']['complete'] and score['evidence']['quality']=='fast'
            assert score['cp']==score['lines'][0]['cp'] and score['mate']==score['lines'][0]['mate']
            assert len({line['moves'][0] for line in score['lines']})==len(score['lines'])
            for line in score['lines']:
                trial=board.copy()
                for uci in line['moves']:
                    move=chess.Move.from_uci(uci)
                    assert move in trial.legal_moves
                    trial.push(move)
        for a in ('old','new'):
            assert r[a]['confirmationSearches']<=6
            pmap,fmap=labelmap(r,a,'provisional'),labelmap(r,a)
            assert {p for p,l in fmap.items() if l=='brilliant'}<={p for p,l in pmap.items() if l=='brilliant'}
            assert len(fmap)==len(r[a]['final'])
            assert set(fmap)<=set(range(1,len(g['moves'])+1))
            assert all(l in {'brilliant','good','interesting','dubious','mistake','blunder'} for l in fmap.values())
        total_positions+=len(r['scores'])
    assert total_positions==1864
    assert sum(len(g['moves']) for g in games)==1837
    assert sum(len(g['scoredPlies']) for g in games)==922
    assert sum(len(g['strictBrilliants']) for g in games)==32
    audit=json.loads((ROOT/'ginger/overlap-audit.json').read_text())
    assert audit['training_rows']==33037 and audit['candidate_rows']==36543
    assert audit['eligible_games']==27 and not audit['ginger_in_original_gallery']
    assert all(not g['all_development_position_move_overlaps'] for g in json.loads((ROOT/'ginger/games.json').read_text()))
    return runs

def build(raw,games):
    runs=verify(raw,games)
    totals=dict.fromkeys(FIELDS,0)
    per_game,cases,exports=[],[],{'old':[],'new':[],'reference':[]}
    for g in games:
        r=runs[g['id']]
        maps={a:labelmap(r,a) for a in ('old','new')}
        scope=set(g['scoredPlies']);targets={x['ply'] for x in g['strictBrilliants']}
        old,new=({p for p,l in maps[a].items() if l=='brilliant'}&scope for a in ('old','new'))
        stats=dict(games=1,scoredMoves=len(scope),targets=len(targets),oldHits=len(old&targets),newHits=len(new&targets),oldAwards=len(old),newAwards=len(new),oldOutside=len(old-targets),newOutside=len(new-targets),gainedTargets=len((new-old)&targets),lostTargets=len((old-new)&targets))
        for key in FIELDS:totals[key]+=stats[key]
        per_game.append({'id':g['id'],'white':g['headers']['White'],'black':g['headers']['Black'],'date':g['headers']['Date'],'stats':stats,'oldAwards':sorted(old),'newAwards':sorted(new),'gainedTargets':sorted((new-old)&targets),'lostTargets':sorted((old-new)&targets)})
        for ply in sorted(targets|old|new):
            d=r['modelDecisions'].get(str(ply),{})
            cases.append({'game':g['id'],'white':g['headers']['White'],'black':g['headers']['Black'],'date':g['headers']['Date'],'ply':ply,'move':name(g,ply),'galleryBrilliant':ply in targets,'old':maps['old'].get(ply,'no annotation'),'new':maps['new'].get(ply,'no annotation'),'provisionalNew':labelmap(r,'new','provisional').get(ply,'no annotation'),'modelCandidate':d.get('candidate'),'modelScore':d.get('score'),'before':g['positions'][ply-1],'after':g['positions'][ply],'url':f"https://www.chess.com/analysis/game/live/{g['id']}?move={ply-1}"})
        for algorithm in exports:
            game=chess.pgn.Game();game.headers.clear();game.headers.update(g['headers'])
            game.headers['Annotator']=('Chess.com gallery captured 2026-11-28' if algorithm=='reference' else OLD if algorithm=='old' else NEW)+'; Ginger moves only; Fast analysis'
            cursor=game
            awarded=targets if algorithm=='reference' else old if algorithm=='old' else new
            for ply,uci in enumerate(g['moves'],1):
                cursor=cursor.add_variation(chess.Move.from_uci(uci))
                if ply in awarded:cursor.nags.add(chess.pgn.NAG_BRILLIANT_MOVE)
            exports[algorithm].append(game.accept(chess.pgn.StringExporter(headers=True,variations=False,comments=True)))
    result={k:raw[k] for k in ('appSource','planCommit','modelSource','modelSha256','cutoff','engine')}
    result.update(mode='fast',totals=totals,perGame=per_game,cases=cases)
    output=ROOT/'ginger'
    (output/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    for algorithm,records in exports.items():
        path=output/('gallery-labels.pgn' if algorithm=='reference' else algorithm+'-awards.pgn')
        path.write_text('\n\n'.join(records)+'\n')
        # Assert the actual exported PGNs retain exactly the measured symbols.
        stream=io.StringIO(path.read_text())
        for record,g in zip(per_game,games):
            game=chess.pgn.read_game(stream)
            assert game is not None and not game.errors
            assert [m.uci() for m in game.mainline_moves()]==g['moves']
            got={p for p,node in enumerate(game.mainline(),1) if chess.pgn.NAG_BRILLIANT_MOVE in node.nags}
            want={a['ply'] for a in g['strictBrilliants']} if algorithm=='reference' else set(record[algorithm+'Awards'])
            assert got==want
        assert chess.pgn.read_game(stream) is None
    return result

def report(result):
    t=result['totals']
    old_percent=100*t['oldHits']/t['targets'];new_percent=100*t['newHits']/t['targets']
    delta=t['newHits']-t['oldHits']
    intro=f"On 27 Ginger_GM games outside the published development data, {OLD} recovered **{t['oldHits']} of 32** gallery Brilliants ({old_percent:.1f}%). {NEW} recovered **{t['newHits']} of 32** ({new_percent:.1f}%). That is **{delta:+d} matching Brilliants**."
    metrics=[('Gallery Brilliants found',t['oldHits'],t['newHits']),('Gallery Brilliants missed',32-t['oldHits'],32-t['newHits']),('All Brilliant awards on Ginger moves',t['oldAwards'],t['newAwards']),('Awards outside the captured gallery',t['oldOutside'],t['newOutside'])]
    lines=['# Ginger: an independent brilliant-move comparison','','![Measured comparison](comparison.png)','',intro,'','| Fast analysis | '+OLD+' | '+NEW+' |','|---|---:|---:|']
    lines.extend(f'| {label} | {a} | {b} |' for label,a,b in metrics)
    lines+=['',f"The new detector gained {t['gainedTargets']} gallery labels and lost {t['lostTargets']} that the adapted En Croissant detector found.",'','## What the result means','','The improvement survives outside the published development games: Open Brilly Finder recovers 13 more of the 32 gallery labels. Its 62.5% hit rate is lower than the 86.3% in the earlier development-heavy 42-game comparison, so that earlier rate should not be treated as a general expectation. This independent sample supports the planned 2.7 adoption, while showing that 12 gallery brillies are still missed.','','One gallery brilly is lost: [14...Nxe4 against 98766789Maverick](https://www.chess.com/analysis/game/live/186807227802?move=27). The adapted En Croissant detector calls it Brilliant; Open Brilly Finder calls it Interesting. Its baseline model score is 0.6932, below the unchanged 0.8193 cutoff.','','The one remaining outside-gallery award, [12.Nb5 against Blunder_Punisher01](https://www.chess.com/analysis/game/live/187353132044?move=22), is shared by both detectors. Open Brilly Finder introduces no new outside-gallery awards in this sample.','','## What this tests','',
        'The earlier online comparison reused development games. This follow-up uses a frozen sample from another account. We checked all mainline position-and-move pairs against the published candidate table, not just game IDs. Three of the initial 30 games repeated training positions and were excluded entirely, without replacements. The retained 27 games have no matching games or candidate position-and-move pairs in that public data. Ginger does not appear as either player in its original 7,019-game gallery collection.','',
        'Both detectors used the actual Mobile Maia code and identical fresh Stockfish 18 searches: Fast, depth 12 / 500 ms, one thread, 64 MiB hash, two lines. Each retained its ordinary six-search-unit confirmation budget. The published model and 0.8193002847777424 cutoff were unchanged. We analyzed 1,864 positions and scored Ginger’s 922 moves.','',
        'This measures recovery of Chess.com’s captured gallery labels on games selected for containing brillies. It does not measure precision across ordinary games or all players. An award outside the gallery is a disagreement, not automatically a false positive. A fresh Game Review may produce different labels.','',
        '[Frozen plan](PLAN.md) · [Training-overlap audit](overlap-audit.json) · [All recorded results](summary.json) · [Native searches and decisions](engine-runs.json.gz) · [Visual move-by-move report](comparison.html)','','## Every game','','| Date | Game | Gallery !! | '+OLD+' found | '+NEW+' found | Outside gallery: adapted / new |','|---|---|---:|---:|---:|---:|']
    for g in result['perGame']:
        s=g['stats'];link=f"[{g['white']} – {g['black']}](https://www.chess.com/game/live/{g['id']})"
        lines.append(f"| {g['date'].replace('.','/')} | {link} | {s['targets']} | {s['oldHits']} | {s['newHits']} | {s['oldOutside']} / {s['newOutside']} |")
    lines+=['','## Every reference move and additional award','','“Outside gallery” means it was not among the frozen gallery cards for this sample. Both detector columns show the final app classification, after evidence checks.','','| Game | Move | Captured gallery | '+OLD+' | '+NEW+' |','|---|---|---|---|---|']
    for c in result['cases']:
        lines.append(f"| {c['white']} – {c['black']} | [{c['move']}]({c['url']}) | {'Brilliant !!' if c['galleryBrilliant'] else 'Outside gallery'} | {c['old']} | {c['new']} |")
    lines+=['','## PGN downloads','','These exports mark only Ginger’s Brilliant moves, matching the scoring scope.','',f'- [{OLD}](old-awards.pgn)',f'- [{NEW}](new-awards.pgn)','- [Captured gallery labels](gallery-labels.pgn)','','No Android builds, GitHub Actions, LFS downloads or model training.']
    (ROOT/'ginger/REPORT.md').write_text('\n'.join(lines)+'\n')
    # Self-contained, accessible static research artifact; diagrams derive from
    # the recorded FENs, and each table row and count is driven by measured data.
    metric_rows=''.join(f'<tr><th>{escape(label)}</th><td>{a}</td><td>{b}</td></tr>' for label,a,b in metrics)
    game_rows=''.join(f'<tr><td>{escape(g["date"].replace(".","/"))}</td><td>{escape(g["white"])} – {escape(g["black"])}</td><td>{g["stats"]["targets"]}</td><td>{g["stats"]["oldHits"]}</td><td>{g["stats"]["newHits"]}</td><td>{g["stats"]["oldOutside"]} / {g["stats"]["newOutside"]}</td></tr>' for g in result['perGame'])
    cards=[]
    for c in result['cases']:
        gain=c['galleryBrilliant'] and c['new']=='brilliant' and c['old']!='brilliant'
        lost=c['galleryBrilliant'] and c['old']=='brilliant' and c['new']!='brilliant'
        kind='Recovered gallery brilly' if gain else 'Lost gallery brilly' if lost else 'Gallery brilly' if c['galleryBrilliant'] else 'Award outside gallery'
        board=chess.Board(c['before']);after=chess.Board(c['after'])
        boards='<figure>'+board_svg(board,f'g{c["game"]}-{c["ply"]}-before-')+'<figcaption>Before '+escape(c['move'])+'</figcaption></figure><figure>'+board_svg(after,f'g{c["game"]}-{c["ply"]}-after-')+'<figcaption>After the same move</figcaption></figure>'
        score='Not a piece-offer candidate' if c['modelCandidate'] is False else 'Baseline model score '+(f"{c['modelScore']:.4f}" if c['modelScore'] is not None else 'not recorded')+'; cutoff 0.8193'
        cards.append(f'<details id="g{c["game"]}-{c["ply"]}"><summary><span>{escape(kind)}</span><strong>{escape(c["move"])}</strong> {escape(c["white"])} – {escape(c["black"])}</summary><p><a href="{escape(c["url"])}">Original game on Chess.com</a> · {escape(c["date"])}</p><div class="boards">{boards}</div><table><tr><th>{OLD}</th><th>{NEW}</th></tr><tr><td>{escape(c["old"].capitalize())}</td><td>{escape(c["new"].capitalize())}</td></tr></table><p>{escape(score)}.</p></details>')
    page=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Ginger: independent brilliant-move comparison</title><style>
    :root{{color-scheme:dark}}*{{box-sizing:border-box}}body{{margin:0;background:#111a20;color:#e9eef0;font:16px/1.6 system-ui,sans-serif}}main{{max-width:1100px;margin:auto;padding:40px 24px}}h1{{font-size:clamp(30px,5vw,52px);line-height:1.12}}h2{{margin-top:44px}}p{{max-width:850px}}a{{color:#93cbff}}.eyebrow{{color:#b6c4cd}}.bars{{display:grid;gap:18px;margin:28px 0}}.bar{{height:38px;background:#81bdff;border-radius:4px;min-width:2px}}.bar.new{{background:#f1b356}}.bars label{{display:block;margin-bottom:6px}}.scroll{{overflow:auto}}table{{border-collapse:collapse;width:100%;margin:20px 0}}td,th{{padding:12px;border-bottom:1px solid #3b4851;text-align:left}}td:not(:first-child){{font-variant-numeric:tabular-nums}}details{{margin:14px 0;border:1px solid #40505c;padding:14px;border-radius:10px;background:#19262e}}summary{{cursor:pointer}}summary span{{display:block;color:#f1b356}}summary strong{{font-size:22px;margin-right:10px}}.boards{{display:flex;gap:16px;flex-wrap:wrap}}figure{{margin:0;flex:1;min-width:200px;max-width:340px}}figure svg{{width:100%;height:auto}}figcaption{{text-align:center}}.note{{padding:16px;background:#25323b;border-left:4px solid #f1b356}}footer{{margin-top:40px;color:#bdc9d0;font-size:14px}}</style><main>
    <p class="eyebrow">Mobile Maia research · Frozen independent sample · Fast analysis</p><h1>Can we find more of Ginger’s brillies?</h1><p>{escape(intro.replace('**',''))}</p>
    <div class="bars"><div><label>{OLD}: <b>{t['oldHits']} / 32</b> ({old_percent:.1f}%)</label><div class="bar" style="width:{old_percent}%"></div></div><div><label>{NEW}: <b>{t['newHits']} / 32</b> ({new_percent:.1f}%)</label><div class="bar new" style="width:{new_percent}%"></div></div></div>
    <table><thead><tr><th>Fast analysis</th><th>{OLD}</th><th>{NEW}</th></tr></thead><tbody>{metric_rows}</tbody></table><p>Gallery labels gained: <b>{t['gainedTargets']}</b>. Lost: <b>{t['lostTargets']}</b>.</p>
    <h2>What the result means</h2><p>The improvement survives on this independent sample: 13 more of the 32 gallery labels are recovered. The 62.5% hit rate is lower than the earlier development-heavy sample’s 86.3%; 12 gallery brillies are still missed.</p><p>The one lost gallery brilly is <a href="#g186807227802-28">14...Nxe4 against 98766789Maverick</a>. Its baseline model score is 0.6932, below the unchanged 0.8193 cutoff. The one remaining outside-gallery award is shared by both detectors.</p><h2>Outside the development data</h2><p>27 games, 32 captured gallery brillies, 922 Ginger moves. We excluded three of the initial 30 games because they repeated training positions and moves. None of the retained games or their played position-and-move pairs matches the published candidate data. Ginger does not appear as either player in the original 7,019-game collection.</p>
    <p>Both detectors use identical fresh Stockfish 18 searches and actual Mobile Maia code. The published model, cutoff and normal confirmation budgets are unchanged.</p><p class="note">This is a test of recovering gallery brillies, on games selected because they contain brillies. An additional award outside the captured gallery is a disagreement, not proof of a false positive. This sample cannot establish precision across ordinary games.</p>
    <h2>Every game</h2><div class="scroll"><table><tr><th>Date</th><th>Game</th><th>Gallery !!</th><th>{OLD}</th><th>{NEW}</th><th>Outside gallery<br>adapted / new</th></tr>{game_rows}</table></div>
    <h2>Review every move</h2><p>Open a row to see the position before and after the move, the captured reference, and each detector’s final classification. These are two positions for the same move; the table compares the detectors. The final label includes the app’s normal grading and confirmation checks.</p>{''.join(cards)}
    <footer>Sample frozen at {FROZEN}. Model source {result['modelSource']}. No Android builds, Actions, LFS downloads or retraining. Piece artwork: Cburnett, GPL-2.0-or-later; rendered by python-chess.</footer></main></html>'''
    (ROOT/'ginger/comparison.html').write_text(page)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runs',type=Path,required=True)
    args=parser.parse_args()
    content=args.runs.read_bytes()
    raw=json.loads(gzip.decompress(content) if args.runs.suffix=='.gz' else content)
    games=json.loads((ROOT/'ginger/runner-input.json').read_text())
    result=build(raw,games)
    (ROOT/'ginger/engine-runs.json.gz').write_bytes(gzip.compress(json.dumps(raw,separators=(',',':')).encode()+b'\n',mtime=0))
    report(result)
    print(json.dumps(result['totals'],indent=2))
    print('PASS: frozen inputs, all 1,837 legal moves, 1,864 positions and PVs, confirmation budgets, model pins, counts and three annotated PGN round trips.')
