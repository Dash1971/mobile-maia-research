"""Recount published Ginger results directly from raw final labels."""
import collections
import gzip
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def main():
    games=json.loads((ROOT/'ginger/runner-input.json').read_text())
    raw=json.loads(gzip.decompress((ROOT/'ginger/engine-runs.json.gz').read_bytes()))
    report=json.loads((ROOT/'ginger/summary.json').read_text())
    runs={r['game']:r for r in raw['runs']}
    published={g['id']:g for g in report['perGame']}
    count=collections.Counter()
    expected_cases=set()
    for g in games:
        scope=set(g['scoredPlies'])
        reference={r['ply'] for r in g['strictBrilliants']}
        awards={a:{x['ply'] for x in runs[g['id']][a]['final'] if x['label']=='brilliant'}&scope for a in ('old','new')}
        a,b=awards['old'],awards['new']
        actual={'games':1,'scoredMoves':len(scope),'targets':len(reference),
                'oldHits':len(a&reference),'newHits':len(b&reference),
                'oldAwards':len(a),'newAwards':len(b),'oldOutside':len(a-reference),'newOutside':len(b-reference),
                'gainedTargets':len((b-a)&reference),'lostTargets':len((a-b)&reference)}
        assert published[g['id']]['stats']==actual
        assert set(published[g['id']]['oldAwards'])==a
        assert set(published[g['id']]['newAwards'])==b
        count.update(actual)
        expected_cases|={(g['id'],p) for p in reference|a|b}
    assert dict(count)==report['totals']
    assert {(c['game'],c['ply']) for c in report['cases']}==expected_cases
    assert len(report['cases'])==len(expected_cases)
    assert count['newHits']-count['oldHits']==count['gainedTargets']-count['lostTargets']
    assert all(count[a+'Hits']+count[a+'Outside']==count[a+'Awards'] for a in ('old','new'))
    assert len(runs)==27 and count['targets']==32 and count['scoredMoves']==922
    print('PASS: independent raw-label recount agrees with every total, game row and move case.')
    print(json.dumps(dict(count),indent=2))

if __name__=='__main__':main()
