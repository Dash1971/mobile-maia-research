"""Summarize the frozen online sample, retaining matches and disagreements."""
import argparse
import gzip
import json
from pathlib import Path

import chess
import chess.pgn

from summarize import labelmap, move_label, pv

ROOT = Path(__file__).resolve().parents[1]
KEYS = ('games', 'scoredMoves', 'targets', 'oldHits', 'newHits', 'oldAwards', 'newAwards',
        'oldOutside', 'newOutside', 'gainedTargets', 'lostTargets', 'gainedAwards', 'lostAwards',
        'galleryTargets', 'oldGalleryHits', 'newGalleryHits')
NAMES = {'hansen':'Eric Hansen', 'KNVB':'Aman Hambleton', 'nelsi':'nelsi',
         'GothamChess':'GothamChess', 'Hikaru':'Hikaru', 'MagnusCarlsen':'MagnusCarlsen', 'Witty_Alien':'Witty_Alien'}


def build(raw):
    games = json.loads((ROOT / 'online/games.json').read_text())
    assert len(raw['runs']) == len(games) == 42, 'Do not publish a partial study.'
    runs = {r['game']: r for r in raw['runs']}
    assert len(runs) == 42 and all(r['quality'] == 'fast' for r in raw['runs'])
    totals = dict.fromkeys(KEYS, 0)
    accounts, public, per_game, exports = {}, [], [], {'old':[], 'new':[], 'reference':[]}
    for g in games:
        r = runs[g['id']]
        assert len(r['scores']) == len(g['positions'])
        scope = set(g['scoredPlies'])
        targets = {a['ply'] for a in g['strictBrilliants']}
        gallery = set(g['galleryBrilliants'])
        maps = {k: labelmap(r[k]) for k in ('old','new')}
        old, new = ({p for p, label in maps[k].items() if label == 'brilliant'} & scope for k in ('old','new'))
        s = dict(games=1,scoredMoves=len(scope),targets=len(targets),oldHits=len(old & targets),newHits=len(new & targets),
                 oldAwards=len(old),newAwards=len(new),oldOutside=len(old-targets),newOutside=len(new-targets),
                 gainedTargets=len((new-old)&targets),lostTargets=len((old-new)&targets),
                 gainedAwards=len(new-old),lostAwards=len(old-new),galleryTargets=len(gallery),
                 oldGalleryHits=len(old&gallery),newGalleryHits=len(new&gallery))
        a = accounts.setdefault(g['account'],dict.fromkeys(KEYS,0))
        for key in KEYS:
            totals[key] += s[key]; a[key] += s[key]
        cases = []
        for ply in sorted(targets | gallery | old | new):
            before, after = r['scores'][ply-1:ply+1]
            d = r['modelDecisions'].get(str(ply), {})
            label = maps['new'].get(ply)
            provisional = labelmap(r['new'],'provisional').get(ply)
            reason = ('Awarded Brilliant after the app’s evidence checks.' if label == 'brilliant' else
                      'The engine-based error grade takes precedence.' if label in ('blunder','mistake','dubious') else
                      'The app withheld a provisional award after its evidence checks.' if provisional == 'brilliant' else
                      'The piece-offer test is not met.' if d.get('candidate') is False else
                      'The model score is below its Brilliant cutoff.' if d.get('candidate') is True else
                      'A standalone model diagnostic was not recorded.')
            recorded = g['reviewLabels'][str(ply)]
            c = {'ply':ply,'move':move_label(g,ply),'uci':g['moves'][ply-1],
                 'before':g['positions'][ply-1],'after':g['positions'][ply],
                 'landmark':ply in targets,'sourceMark':'!!' if ply in targets else None,
                 'sourceListed':ply in targets or ply in gallery,'galleryBrilliant':ply in gallery,
                 'referenceLabel': 'Chess.com review: ' + ('Brilliant !!' if recorded=='brilliant' else recorded.replace('-',' ').capitalize()),
                 'idea':'','modes':{'fast':{'old':maps['old'].get(ply),'new':label,'provisionalNew':provisional,
                    'candidate':d.get('candidate'),'score':d.get('score'),'reason':reason,
                    'depths':[x['evidence']['depth'] if x['evidence'] else 0 for x in (before,after)],
                    'beforeCp':before['cp'],'beforeMate':before['mate'],'afterCp':after['cp'],'afterMate':after['mate'],
                    'beforePV':pv(g['positions'][ply-1],before['lines'][0]['moves']) if before['lines'] else '',
                    'afterPV':pv(g['positions'][ply],after['lines'][0]['moves']) if after['lines'] else ''}}}
            cases.append(c)
        h = g['headers']
        public.append({'id':g['id'],'collection':'online','account':g['account'],'accountName':NAMES[g['account']],
                       'title':h['White']+' – '+h['Black'],'year':h['Date'].replace('.','/'),
                       'source':{'url':h['Link'],'title':'Original online game'},'headers':h,
                       'modelRelationship':g['modelRelationship'],'stats':{'fast':s},'cases':cases,
                       'defaultPly': next((c['ply'] for c in cases if c['landmark'] and c['modes']['fast']['old']!='brilliant' and c['modes']['fast']['new']=='brilliant'),cases[0]['ply']) if cases else None})
        per_game.append({'id':g['id'],'account':g['account'],'stats':s,
                         'gained':sorted(new-old),'lost':sorted(old-new),
                         'gainedReference':sorted((new-old)&targets),'lostReference':sorted((old-new)&targets)})
        for algorithm in ('old','new','reference'):
            score = chess.pgn.Game(); score.headers.clear(); score.headers.update(h)
            score.headers['Annotator'] = ('Recorded Chess.com review November 22, 2026; selected-account labels' if algorithm=='reference' else
                ('Mobile Maia En Croissant-derived detector' if algorithm=='old' else 'Mobile Maia Open Brilly Finder') + '; native Stockfish18 Fast')
            cursor = score
            for i, uci in enumerate(g['moves'],1):
                cursor = cursor.add_variation(chess.Move.from_uci(uci))
                if (i in targets if algorithm=='reference' else maps[algorithm].get(i)=='brilliant'):
                    cursor.nags.add(chess.pgn.NAG_BRILLIANT_MOVE)
            # python-chess's comments flag also governs NAG output. These clean
            # nodes contain no prose, but must retain the measured !! symbols.
            exports[algorithm].append(score.accept(chess.pgn.StringExporter(headers=True,variations=False,comments=True)))
    for algorithm,texts in exports.items():
        name='review-labels.pgn' if algorithm=='reference' else algorithm+'-awards.pgn'
        (ROOT / 'online' / name).write_text('\n\n'.join(texts)+'\n\n')
    spotlight_path=ROOT/'online/spotlights.json'
    if spotlight_path.exists():
        for s in json.loads(spotlight_path.read_text()):
            g=next(g for g in public if g['id']==s['game'])
            c=next(c for c in g['cases'] if c['ply']==s['ply'])
            assert c['landmark'] and c['modes']['fast']['new']=='brilliant'
            c['idea']=s['text']
    result = {'appSource':raw['appSource'],'planCommit':raw['planCommit'],'modelSource':raw['modelSource'],
              'modelSha256':raw['modelSha256'],'engine':raw['engine'],'cutoff':raw['cutoff'],
              'mode':'fast','totals':totals,'accounts':accounts,'perGame':per_game,'games':public}
    (ROOT/'online/summary.json').write_text(json.dumps({k:v for k,v in result.items() if k!='games'},indent=2)+'\n')
    (ROOT/'web/online-results.json').write_text(json.dumps(result,ensure_ascii=False,separators=(',',':'))+'\n')
    return result


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--runs',type=Path,required=True);a=p.parse_args()
    raw=json.loads(a.runs.read_text())
    if a.runs.resolve() != (ROOT/'online/engine-runs.json.gz').resolve():
        (ROOT/'online/engine-runs.json.gz').write_bytes(gzip.compress(json.dumps(raw,separators=(',',':')).encode()+b'\n',mtime=0))
    result=build(raw)
    print(json.dumps({'totals':result['totals'],'accounts':result['accounts']},indent=2))
