"""Independently verify the frozen online sample, native evidence and publication."""
import gzip
import io
import json
from pathlib import Path
import subprocess

import chess
import chess.pgn

ROOT=Path(__file__).resolve().parents[1]
PLAN='a3c44bf2ba76021db8a8688881f1dc80748318df'


def awards(run,algorithm):
    return {x['ply'] for x in run[algorithm]['final'] if x['label']=='brilliant'}


def main():
    for name in ['games.json','games.pgn','selection.json','PLAN.md']:
        file=ROOT/'online'/name
        relative=file.relative_to(ROOT.parents[1])
        frozen=subprocess.check_output(['git','-C',str(ROOT), 'show',f'{PLAN}:{relative}'])
        assert frozen==file.read_bytes(),('Frozen input changed',name)
    games=json.loads((ROOT/'online/games.json').read_text())
    raw=json.loads(gzip.decompress((ROOT/'online/engine-runs.json.gz').read_bytes()))
    public=json.loads((ROOT/'web/online-results.json').read_text())
    assert raw['planCommit']==PLAN and len(games)==len(raw['runs'])==42
    assert len({g['id'] for g in games})==42
    assert sum(len(g['moves']) for g in games)==3364
    assert sum(len(g['scoredPlies']) for g in games)==1692
    assert sum(len(g['strictBrilliants']) for g in games)==51
    assert raw['threads']==1 and raw['hashMiB']==64 and raw['multiPV']==2
    runs={r['game']:r for r in raw['runs']}
    pmap={g['id']:g for g in public['games']}
    assert len(runs)==len(pmap)==42
    totals=dict(oldHits=0,newHits=0,oldAwards=0,newAwards=0,oldOutside=0,newOutside=0,gainedTargets=0,lostTargets=0,
                gainedAwards=0,lostAwards=0,galleryTargets=0,oldGalleryHits=0,newGalleryHits=0)
    positions=0
    for g in games:
        board=chess.Board(g['positions'][0])
        for i,uci in enumerate(g['moves'],1):
            move=chess.Move.from_uci(uci)
            assert move in board.legal_moves and board.san(move)==g['sans'][i-1]
            board.push(move);assert board.fen()==g['positions'][i]
        r=runs[g['id']];assert r['quality']=='fast' and len(r['scores'])==len(g['positions'])
        positions+=len(r['scores'])
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
                    move=chess.Move.from_uci(uci);assert move in trial.legal_moves
                    trial.push(move)
        for a in ('old','new'):
            assert r[a]['confirmationSearches']<=6
            provisional={x['ply'] for x in r[a]['provisional'] if x['label']=='brilliant'}
            assert awards(r,a)<=provisional
        scope=set(g['scoredPlies']);reference={a['ply'] for a in g['strictBrilliants']}
        assert all(g['reviewLabels'][str(i)]=='brilliant' for i in reference)
        old,new=(awards(r,a)&scope for a in ('old','new'))
        counts=dict(oldHits=len(old&reference),newHits=len(new&reference),oldAwards=len(old),newAwards=len(new),
                    oldOutside=len(old-reference),newOutside=len(new-reference),gainedTargets=len((new-old)&reference),lostTargets=len((old-new)&reference),
                    gainedAwards=len(new-old),lostAwards=len(old-new),galleryTargets=len(g['galleryBrilliants']),
                    oldGalleryHits=len(old&set(g['galleryBrilliants'])),newGalleryHits=len(new&set(g['galleryBrilliants'])))
        for key,n in counts.items():
            assert pmap[g['id']]['stats']['fast'][key]==n
            totals[key]+=n
        expected_cases=old|new|reference|set(g['galleryBrilliants'])
        assert {c['ply'] for c in pmap[g['id']]['cases']}==expected_cases
        for c in pmap[g['id']]['cases']:
            assert c['before']==g['positions'][c['ply']-1] and c['after']==g['positions'][c['ply']]
            for a in ('old','new'):
                assert c['modes']['fast'][a]==next((x['label'] for x in r[a]['final'] if x['ply']==c['ply']),None)
    assert positions==3406
    for key,n in totals.items():assert public['totals'][key]==n
    for field in public['totals']:
        assert sum(s[field] for s in public['accounts'].values())==public['totals'][field]
    for algorithm in ['old','new','reference']:
        path=ROOT/'online'/('review-labels.pgn' if algorithm=='reference' else algorithm+'-awards.pgn')
        scores=[]
        with path.open() as f:
            while (score:=chess.pgn.read_game(f)) is not None:scores.append(score)
        assert len(scores)==42
        for g,score in zip(games,scores):
            assert [m.uci() for m in score.mainline_moves()]==g['moves']
            annotated={i for i,n in enumerate(score.mainline(),1) if chess.pgn.NAG_BRILLIANT_MOVE in n.nags}
            expected={a['ply'] for a in g['strictBrilliants']} if algorithm=='reference' else awards(runs[g['id']],algorithm)
            assert annotated==expected
    for s in json.loads((ROOT/'online/spotlights.json').read_text()):
        c=next(c for c in pmap[s['game']]['cases'] if c['ply']==s['ply'])
        assert c['landmark'] and c['modes']['fast']['new']=='brilliant' and c['modes']['fast']['old']!='brilliant'
        assert c['idea']==s['text']
    print('PASS: frozen 42-game sample, 3,364 legal moves, 3,406 native positions, all PVs/awards/counts, 3 PGN exports and both Chessbrah examples.')


if __name__=='__main__':main()
