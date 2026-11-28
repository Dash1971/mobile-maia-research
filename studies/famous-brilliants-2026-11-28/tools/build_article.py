"""Build the reader-facing report and website from the three recorded comparisons."""
import hashlib
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESEARCH = 'https://github.com/Dash1971/mobile-maia-research/blob/__RESEARCH_COMMIT__/studies/famous-brilliants-2026-11-28/'
OBF = 'https://github.com/Dash1971/open-brilly-finder'
ENC = 'https://github.com/franciscoBSalgueiro/en-croissant'
e = html.escape


def table(headers, rows, caption=''):
    head = ''.join('<th scope="col">'+e(str(h))+'</th>' for h in headers)
    body = ''.join('<tr><th scope="row">'+e(str(row[0]))+'</th>'+''.join('<td>'+e(str(v))+'</td>' for v in row[1:])+'</tr>' for row in rows)
    return f'<div class="brilly-table-wrap"><table class="brilly-table">'+(f'<caption>{e(caption)}</caption>' if caption else '')+f'<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def markdown_table(headers, rows):
    return '\n'.join(['| '+' | '.join(map(str,headers))+' |','| '+' | '.join('---' for _ in headers)+' |']+['| '+' | '.join(map(str,row))+' |' for row in rows])


def main():
    classic=json.loads((ROOT/'web/results.json').read_text())
    online=json.loads((ROOT/'web/online-results.json').read_text())
    ginger=json.loads((ROOT/'ginger/summary.json').read_text())['totals']
    story=json.loads((ROOT/'data/story.json').read_text())
    spots=json.loads((ROOT/'online/spotlights.json').read_text())
    t=online['totals']; values={**t,'hitGain':t['newHits']-t['oldHits'],'hitPercent':round(100*(t['newHits']-t['oldHits'])/t['oldHits'])}
    values.update(gingerGames=ginger['games'],gingerTargets=ginger['targets'],gingerGained=ginger['gainedTargets'],gingerLost=ginger['lostTargets'],gingerGain=ginger['newHits']-ginger['oldHits'],gingerNewPercent=100*ginger['newHits']/ginger['targets'],gingerMissed=ginger['targets']-ginger['newHits'])
    copy={k:([p.format(**values) for p in v] if isinstance(v,list) else v.format(**values)) for k,v in story.items()}
    p=lambda text:'<p>'+e(text)+'</p>'
    paras=lambda texts:''.join(p(text) for text in texts)
    classic_rows=[[g['title'],g['stats']['fast']['targets'],g['stats']['fast']['oldHits'],g['stats']['fast']['newHits']] for g in classic['games']]
    account_rows=[[next(g['accountName'] for g in online['games'] if g['account']==a),s['targets'],s['oldHits'],s['newHits']] for a,s in online['accounts'].items()]
    account_rows.append(['Total',t['targets'],t['oldHits'],t['newHits']])
    comparison_headers=['Recorded Brilliant moves','En Croissant-derived','Open Brilly Finder']
    comparison_rows=[['Found',t['oldHits'],t['newHits']],['Missed',t['targets']-t['oldHits'],t['targets']-t['newHits']],['Awards outside those labels',t['oldOutside'],t['newOutside']],['All Brilliant awards',t['oldAwards'],t['newAwards']]]
    ginger_headers=['Fast analysis','En Croissant (adapted)','Open Brilly Finder']
    ginger_rows=[['Gallery brillies found',f"{ginger['oldHits']}/{ginger['targets']} ({100*ginger['oldHits']/ginger['targets']:.1f}%)",f"{ginger['newHits']}/{ginger['targets']} ({100*ginger['newHits']/ginger['targets']:.1f}%)"],['Gallery brillies missed',ginger['targets']-ginger['oldHits'],ginger['targets']-ginger['newHits']],['Awards outside the gallery',ginger['oldOutside'],ginger['newOutside']]]
    ginger_md=['## An independent check: Ginger','',copy['gingerIntro'],'',markdown_table(ginger_headers,ginger_rows),'',copy['gingerResult'],'',copy['gingerLimit'],'','[All Ginger games, moves and training-overlap audit](ginger/REPORT.md)','']
    spot_html=[]; spot_md=[]
    for s in spots:
        g=next(g for g in online['games'] if g['id']==s['game'])
        c=next(c for c in g['cases'] if c['ply']==s['ply'])
        f=f'figures/{g["id"]}-{c["ply"]:03d}.png'
        assert (ROOT/f).is_file()
        title=s['title']; note=f'{g["title"]} · {g["year"]} · {c["move"]}'
        old=classic['grades'][c['modes']['fast']['old'] or 'null']; new=classic['grades'][c['modes']['fast']['new'] or 'null']
        spot_html.append(f'<section class="brilly-spotlight"><h3>{e(title)}</h3><p class="brilly-small">{e(note)}</p>{p(s["text"])}<figure><img src="{f}" width="960" height="550" loading="lazy" alt="Actual board before and after {e(c["move"])} in {e(g["title"])}."><figcaption>Existing: {e(old)}. Open Brilly Finder: {e(new)}. Recorded Chess.com review: Brilliant.</figcaption></figure><p><a class="brilly-button" href="#explore" data-open-game="{g["id"]}" data-open-ply="{c["ply"]}">Inspect this move</a> <a href="{e(g["source"]["url"])}">Original game</a></p></section>')
        spot_md += [f'### {title}', '',note,'',s['text'],'',f'![{note}]({f})','',f'Existing: **{old}**. Open Brilly Finder: **{new}**. Recorded Chess.com review: **Brilliant**.','',f'[Original game]({g["source"]["url"]})','']
    classics_static=[]
    for g in classic['games']:
        figures=[]
        for c in g['cases']:
            if not c['landmark']:continue
            m=c['modes']['fast']; grade=lambda x:classic['grades'][x or 'null']
            figures.append(f'<figure class="brilly-static-case"><h4>{e(c["move"])} · published !!</h4>{p(c["idea"])}<img loading="lazy" src="figures/{g["id"]}-{c["ply"]:03d}.png" width="960" height="550" alt="Before and after {e(c["move"])} in {e(g["title"])}."><figcaption>Fast: {e(grade(m["old"]))} → {e(grade(m["new"]))}.</figcaption></figure>')
        classics_static.append(f'<details class="brilly-static-game"><summary>{e(g["title"])} · {g["year"]}</summary><p><a href="{e(g["source"]["url"])}">Published annotation</a></p>{"".join(figures)}</details>')
    online_game_rows=[]
    for g in online['games']:
        s=g['stats']['fast'];online_game_rows.append([g['title']+' · '+g['year'],g['account'],s['targets'],s['oldHits'],s['newHits'],s['oldOutside'],s['newOutside']])
    mode_rows=[[q.title(),s['oldHits'],s['newHits']] for q,s in classic['totals'].items()]
    source_links=''.join(f'<li><a href="{e(g["source"]["url"])}">{e(g["title"])}: {e(g["source"]["title"])}</a></li>' for g in classic['games'])
    bars=''.join(f'<div class="brilly-bar-row"><span>{e(name)}</span><div class="brilly-bar-track"><div class="brilly-bar {cls}" style="width:{100*n/t["targets"]:.4f}%"></div></div><strong>{n} / {t["targets"]}</strong></div>' for name,n,cls in [('En Croissant-derived',t['oldHits'],'old'),('Open Brilly Finder',t['newHits'],'new')])
    body=f'''<main id="main" class="container research-page brilly-page">
<p class="breadcrumb"><a href="../">Research</a><span aria-hidden="true"> / </span>Brilliant moves</p>
<header class="brilly-hero"><div><p class="eyebrow">MOBILE MAIA RESEARCH</p><h1>Finding more<br><em>brilliant moves</em></h1>{paras(copy['intro'])}<p class="brilly-target">{e(copy['release'])}</p><nav class="brilly-contents" aria-label="In this report"><a href="#detectors">The two detectors</a><a href="#classics">Classical games</a><a href="#online">Online games</a><a href="#chessbrah">Chessbrah examples</a><a href="#ginger">Ginger check</a><a href="#decision">Our decision</a></nav></div><figure><img src="figures/hero-opera.png" width="1280" height="720" fetchpriority="high" alt="The Opera Game before Morphy’s 16.Qb8+ queen sacrifice."><figcaption>Morphy’s 16.Qb8+ in the Opera Game. Both detectors recognize it.</figcaption></figure></header>
<section id="detectors" class="brilly-section" aria-labelledby="detectors-title"><h2 id="detectors-title">The two detectors</h2><div class="brilly-detectors"><div><h3>Existing: En Croissant-derived rules</h3>{p(copy['old'])}<a href="{ENC}/blob/v0.15.0/src/utils/score.ts">En Croissant’s scoring code</a></div><div><h3>New: Open Brilly Finder</h3>{p(copy['new'])}<a href="{OBF}">Open Brilly Finder project</a></div></div>{p(copy['offline'])}{p(copy['paired'])}</section>
<section id="classics" class="brilly-section" aria-labelledby="score-title"><h2 id="score-title">First, the classics: a small improvement</h2>{p(copy['classics'])}{p(copy['classicGains'])}<div class="brilly-mode" role="group" aria-label="Classical-game analysis mode"><span>Classical-game analysis</span><button type="button" class="brilly-button" data-quality="fast" aria-pressed="true">Fast</button><button type="button" class="brilly-button" data-quality="balanced" aria-pressed="false">Balanced</button><button type="button" class="brilly-button" data-quality="thorough" aria-pressed="false">Thorough</button></div><p class="brilly-results" id="brilly-tally">9 → 10 of 14 published Brilliant moves found</p><div class="brilly-table-wrap"><table class="brilly-table"><caption>Moves marked !! in the chosen published annotations. Fast analysis is shown by default.</caption><thead><tr><th>Game</th><th class="num">Published !!</th><th class="num">Existing</th><th class="num">Open Brilly</th></tr></thead><tbody>{''.join(f'<tr><th scope="row">{e(g["title"])}</th><td class="num">{g["stats"]["fast"]["targets"]}</td><td class="num" data-game-old="{g["id"]}">{g["stats"]["fast"]["oldHits"]}/{g["stats"]["fast"]["targets"]}</td><td class="num" data-game-new="{g["id"]}">{g["stats"]["fast"]["newHits"]}/{g["stats"]["fast"]["targets"]}</td></tr>' for g in classic['games'])}</tbody></table></div>{p(copy['classicMisses'])}<details class="brilly-method"><summary>All three modes and complete classical results</summary>{table(['Mode','Existing finds','Open Brilly finds'],mode_rows,'Out of fourteen published Brilliant moves.')}<p id="brilly-total-awards">Total awards in Fast: existing detector 19; Open Brilly Finder 20.</p><p>An extra award is not automatically a match to a published !!. The complete move lists include those differences.</p>{''.join(classics_static)}</details></section>
<section id="online" class="brilly-section" aria-labelledby="online-title"><h2 id="online-title">Next, online games: {values['hitGain']} more brilliancies found</h2>{p(copy['online'])}{p(copy['onlineScope'])}<div class="brilly-bars" role="img" aria-label="Recorded online Brilliant moves found: existing detector {t['oldHits']} of 51; Open Brilly Finder {t['newHits']} of 51.">{bars}</div>{p(copy['onlineResult'])}{table(['Player / account','Recorded !!','Existing finds','Open Brilly finds'],account_rows,'Six games per account. Fast analysis; only that account’s moves are scored.')}{p(copy['onlineHeldout'])}{p(copy['onlineAwards'])}{table(comparison_headers,comparison_rows)}<details class="brilly-method"><summary>All 42 games and PGN downloads</summary>{table(['Game / date','Scored account','Recorded !!','Old finds','New finds','Old other','New other'],online_game_rows,'“Other” means an award outside the recorded Brilliant labels.')}<p><a href="online-games.pgn" download>Recorded reference PGN</a> · <a href="en-croissant-awards.pgn" download>Existing detector PGN</a> · <a href="open-brilly-awards.pgn" download>Open Brilly Finder PGN</a></p><p>The detector PGNs include awards on both players’ moves. The comparison above scores only the selected account’s moves.</p></details></section>
<section id="chessbrah" class="brilly-section" aria-labelledby="chessbrah-title"><h2 id="chessbrah-title">Two games from Chessbrah</h2><p>These examples come from the fixed sample: <a href="https://www.chess.com/member/hansen">Eric Hansen (hansen)</a> and <a href="https://www.chess.com/member/knvb">Aman Hambleton (KNVB)</a>.</p>{''.join(spot_html)}</section>
<section id="ginger" class="brilly-section" aria-labelledby="ginger-title"><h2 id="ginger-title">An independent check: Ginger</h2>{p(copy['gingerIntro'])}{table(ginger_headers,ginger_rows,'27 games, 32 captured Chess.com gallery brillies. Only Ginger’s moves are scored.')}{p(copy['gingerResult'])}{p(copy['gingerLimit'])}<p><a href="{RESEARCH}ginger/REPORT.md">All Ginger games, moves and training-overlap audit</a></p></section>
<section id="explore" class="brilly-section" aria-labelledby="explore-title"><h2 id="explore-title">Compare the moves yourself</h2><p>Choose a classical or online game. The board shows the position before or after the move, alongside both detectors’ labels. Online games use Fast analysis; the classical comparison also includes Balanced and Thorough.</p><p id="brilly-load-status" role="status">Loading recorded results…</p><div id="brilly-explorer" class="brilly-explorer" hidden><div class="brilly-inputs"><label class="brilly-field">Game<select id="brilly-game"></select></label><label class="brilly-field">Position<select id="brilly-position"></select></label></div><div class="brilly-board-layout"><div class="brilly-board-panel"><div class="brilly-board-wrap"><div class="brilly-ranks" aria-hidden="true">{''.join(f'<span>{n}</span>' for n in range(8,0,-1))}</div><div id="brilly-board" class="brilly-board" role="img" aria-label="Recorded chess position"></div><div class="brilly-files" aria-hidden="true">{''.join(f'<span>{c}</span>' for c in 'abcdefgh')}</div></div><div class="brilly-board-actions" role="group" aria-label="Board position"><button class="brilly-button" type="button" id="brilly-before" aria-pressed="true">Before move</button><button class="brilly-button" type="button" id="brilly-after" aria-pressed="false">After move</button></div><div class="brilly-case-nav"><button class="brilly-button" type="button" id="brilly-previous">Previous position</button><span id="brilly-case-count"></span><button class="brilly-button" type="button" id="brilly-next">Next position</button></div></div><div class="brilly-case" aria-live="polite"><p class="brilly-small" id="brilly-game-title"></p><h3 id="brilly-case-title"></h3><p class="brilly-annotation" id="brilly-annotation"></p><p id="brilly-idea"></p><div class="brilly-grades"><div class="brilly-grade"><span>En Croissant-derived</span><strong id="brilly-old"></strong></div><div class="brilly-grade"><span>Open Brilly Finder</span><strong id="brilly-new"></strong></div></div><p id="brilly-change"></p><p class="brilly-small" id="brilly-game-awards"></p><a id="brilly-annotation-source" href="#sources">Source</a><details><summary>Technical evidence</summary><p id="brilly-reason"></p><p id="brilly-model"></p><p id="brilly-engine"></p></details></div></div><details class="brilly-all"><summary>All comparison moves in this game</summary><div class="brilly-table-wrap"><table class="brilly-table"><thead><tr><th>Move</th><th>Reference</th><th>Existing</th><th>Open Brilly</th></tr></thead><tbody id="brilly-all-awards"></tbody></table></div><p>Missing annotations are not proof that a move is bad. Online references are the recorded November 22 reviews, which may differ from a new review today.</p></details></div><noscript><p>The tables and board diagrams in this report work without JavaScript.</p></noscript></section>
<section id="decision" class="brilly-section" aria-labelledby="decision-title"><h2 id="decision-title">Our decision: Open Brilly Finder for 2.7</h2>{p(copy['decision'])}</section>
<section class="brilly-section" aria-labelledby="methods-title"><h2 id="methods-title">How we tested</h2><p>The classical comparison contains 492 mainline moves across nine games, analyzed in all three modes. The online comparison contains 3,364 mainline moves across 42 games, analyzed in Fast. The Ginger follow-up adds 1,837 mainline moves across 27 games, also in Fast. All three comparisons use Mobile Maia’s actual analyzer and classifiers, identical baseline Stockfish 18 evidence, and the app’s normal confirmation checks.</p><details class="brilly-method"><summary>Sample limits, settings and reproduction</summary>{paras(copy['limits'])}<p>Fast: depth 12 / up to 500 ms. Balanced: depth 14 / 1,000 ms. Thorough: depth 16 / 1,500 ms. One engine thread, 64 MiB hash, two root lines; fresh session per game and mode. Model and cutoff unchanged.</p><p>Both detectors also show a shared shallow-search inconsistency at Opera 15.Bxd7+: Fast calls it a Blunder and Balanced a Mistake; Thorough leaves it unmarked. That is separate from the Brilliant model.</p><p><a href="{RESEARCH}online/PLAN.md">Fixed online plan</a> · <a href="{RESEARCH}PLAN.md">Fixed classical plan</a> · <a href="{RESEARCH}README.md">Data, pins and reproduction</a></p></details></section>
<section id="sources" class="brilly-section" aria-labelledby="sources-title"><h2 id="sources-title">Sources and code</h2><p><a href="{ENC}">En Croissant</a> supplies the original move-grading and sacrifice-search approach adapted in Mobile Maia. <a href="{OBF}">Open Brilly Finder</a> publishes the Mute Exchange code, weights, games and recorded review labels.</p><p><a href="{OBF}/blob/59cab58a8b63387d9775252f03a6875fe451f697/studies/brilliant-exchange-2026-11-22/METHODS.md">Open Brilly Finder methods and dataset</a> · <a href="https://www.chess.com/tv/shows/chessbrahs">Chessbrah player identities</a> · <a href="{RESEARCH}REPORT.md">Research-repository report</a> · <a href="https://github.com/Dash1971/maia-chess-android-preview/pull/284">Mobile Maia implementation PR</a></p><details><summary>Classical annotations and artwork</summary><ol class="brilly-source-list">{source_links}</ol><p>Cburnett chess pieces by Colin M. L. Burnett, <a href="GPL-2.0.txt">GPL-2.0-or-later</a>. <a href="{RESEARCH}THIRD_PARTY.md">Artwork notices</a>. All boards show recorded game positions.</p></details></section>
</main>'''
    (ROOT/'web/article-body.html').write_text(body+'\n')
    card=f'Mobile Maia is testing a new way to recognize brilliant moves. Compare En Croissant-derived rules with Open Brilly Finder on nine classics, 42 online games and an independent 27-game Ginger sample.'
    (ROOT/'web/index-card.json').write_text(json.dumps({'title':story['title'],'description':card},ensure_ascii=False,indent=2)+'\n')
    md=['# '+story['title'],'',*sum(([x,''] for x in copy['intro']),[]),copy['release'],'',
        '## The two detectors','', '**Existing: En Croissant-derived rules.** '+copy['old'],'',
        '**New: Open Brilly Finder.** '+copy['new'],'',copy['offline'],'',copy['paired'],'',
        '## First, the classics: a small improvement','',copy['classics'],'',copy['classicGains'],'',
        '![The Opera Game before and after 16.Qb8+](figures/opera-1858-031.png)','', 'Both detectors recognize Morphy’s queen sacrifice.','',markdown_table(['Game','Published !!','Existing finds','Open Brilly finds'],classic_rows),'',copy['classicMisses'],'',
        markdown_table(['Analysis mode','Existing finds / 14','Open Brilly finds / 14'],mode_rows),'',
        '[All classical moves, diagrams and sources](CLASSICS.md)','',
        f'## Next, online games: {values["hitGain"]} more brilliancies found','',copy['online'],'',copy['onlineScope'],'',copy['onlineResult'],'',
        markdown_table(['Player / account','Recorded !!','Existing finds','Open Brilly finds'],account_rows),'',copy['onlineHeldout'],'',copy['onlineAwards'],'',
        markdown_table(comparison_headers,comparison_rows),'','## Two games from Chessbrah','',
        *spot_md,*ginger_md,'## Our decision: Open Brilly Finder for 2.7','',copy['decision'],'',
        '## How we tested','',
        'Classical games: 492 mainline moves, nine games, all three modes. Online games: 3,364 mainline moves, 42 games, Fast. The independent Ginger follow-up adds 1,837 mainline moves across 27 games, in Fast. The paired classifiers share baseline Stockfish 18 evidence and keep their normal evidence and confirmation checks. No model, cutoff or classification-rule changes were made for this study.','',
        *sum(([x,''] for x in copy['limits']),[]),
        'Both detectors also show a shared shallow-search inconsistency at Opera 15.Bxd7+: Fast calls it a Blunder and Balanced a Mistake; Thorough leaves it unmarked. That is separate from the Brilliant model.','',
        '[Fixed online plan](online/PLAN.md) · [Selection](online/selection.json) · [All game-level results](online/summary.json) · [Online raw evidence](online/engine-runs.json.gz) · [Data and reproduction](README.md)','',
        '[Recorded reference PGN](online/review-labels.pgn) · [Existing detector PGN](online/old-awards.pgn) · [Open Brilly Finder PGN](online/new-awards.pgn). The detector PGNs include awards for both players; tables score only the selected account.','',
        '## Sources and credits','',f'[En Croissant]({ENC}) · [Open Brilly Finder]({OBF}) · [Chessbrah player identities](https://www.chess.com/tv/shows/chessbrahs) · [Classical annotations](CLASSICS.md) · [Artwork notices](THIRD_PARTY.md)','',
        '[Interactive report on mobilemaia.org](https://mobilemaia.org/research/brilliant-moves/)','']
    (ROOT/'REPORT.md').write_text('\n'.join(md))
    mapping={'web/article-body.html':'research-source/brilliant-study/article-body.html','web/index-card.json':'research-source/brilliant-study/index-card.json',
             **{f'web/{name}':f'site/research/brilliant-moves/{name}' for name in ['brilliant.css','brilliant.js','results.json','online-results.json']},
             'data/games.pgn':'site/research/brilliant-moves/games.pgn','online/review-labels.pgn':'site/research/brilliant-moves/online-games.pgn',
             'online/old-awards.pgn':'site/research/brilliant-moves/en-croissant-awards.pgn','online/new-awards.pgn':'site/research/brilliant-moves/open-brilly-awards.pgn',
             'GPL-2.0.txt':'site/research/brilliant-moves/GPL-2.0.txt'}
    for folder,pattern in [('figures','*.png'),('artwork','*.webp')]:
        for path in sorted((ROOT/folder).glob(pattern)):mapping[f'{folder}/{path.name}']=f'site/research/brilliant-moves/{folder}/{path.name}'
    files=[]
    for source,target in mapping.items():
        b=(ROOT/source).read_bytes();files.append({'source':source,'target':target,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
    (ROOT/'web/website-files.json').write_text(json.dumps({'files':files},indent=2)+'\n')
    print(f'Prepared {len(files)} website files ({sum(r["bytes"] for r in files):,} bytes).')


if __name__ == '__main__':
    main()
