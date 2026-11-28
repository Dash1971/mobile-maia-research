"""Validate and summarize Ginger in all three actual Mobile Maia analysis modes.

Requires chess==1.11.2 for legal-move/PV validation; no engines are run here.
Fast remains the original frozen recording. Balanced/Thorough are fresh searches.
"""
import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import statistics
import subprocess

import chess

ROOT = Path(__file__).resolve().parents[1]
APP = '096591bd8d42759e5a3f3a288d56d7c93245d6d1'
MODEL = '992a792a646b11e612486c4fe26796fc38ee47f395f2220b00d26db65ba1e27d'
PIN_KEYS = ('schema', 'appSource', 'planCommit', 'modelSource', 'modelSha256',
            'engine', 'threads', 'hashMiB', 'multiPV', 'cutoff')
FIELDS = ('games', 'scoredMoves', 'targets', 'oldHits', 'newHits', 'oldAwards',
          'newAwards', 'oldOutside', 'newOutside', 'gainedTargets', 'lostTargets')


def verify_frozen_inputs():
    hashes = {}
    for filename, revision in [
        *[(name, '6844202bf606211c11a27b777560cf009293f30f') for name in
          ('PLAN.md', 'gallery-selection.json', 'games.pgn', 'games.json', 'overlap-audit.json')],
        ('runner-input.json', 'e6737cb02f0c5209c59c38df6f74a88975e065b2'),
        ('engine-runs.json.gz', 'e6737cb02f0c5209c59c38df6f74a88975e065b2'),
    ]:
        path = ROOT / 'ginger' / filename
        original = subprocess.check_output(['git', '-C', str(ROOT.parents[1]),
            'show', f'{revision}:{path.relative_to(ROOT.parents[1])}'])
        assert original == path.read_bytes(), ('Frozen input changed', filename)
        hashes[filename] = hashlib.sha256(original).hexdigest()
    return hashes


def read(path):
    raw = path.read_bytes()
    return json.loads(gzip.decompress(raw) if path.suffix == '.gz' else raw)


def labels(run, algorithm, stage='final'):
    rows = run[algorithm][stage]
    result = {row['ply']: row['label'] for row in rows}
    assert len(result) == len(rows), 'Duplicate classification ply'
    return result


def count(game, run):
    scope = set(game['scoredPlies'])
    targets = {r['ply'] for r in game['strictBrilliants']}
    old, new = ({p for p, label in labels(run, a).items()
                 if label == 'brilliant'} & scope for a in ('old', 'new'))
    return dict(games=1, scoredMoves=len(scope), targets=len(targets),
                oldHits=len(old & targets), newHits=len(new & targets),
                oldAwards=len(old), newAwards=len(new),
                oldOutside=len(old-targets), newOutside=len(new-targets),
                gainedTargets=len((new-old) & targets),
                lostTargets=len((old-new) & targets))


def verify_run(game, run):
    assert len(run['scores']) == len(game['positions'])
    q = run['quality']
    board = chess.Board(game['positions'][0])
    for ply, uci in enumerate(game['moves'], 1):
        move = chess.Move.from_uci(uci)
        assert move in board.legal_moves and board.san(move) == game['sans'][ply-1]
        board.push(move)
        assert board.fen() == game['positions'][ply]
    for fen, score in zip(game['positions'], run['scores']):
        board = chess.Board(fen)
        if not score['lines']:
            assert board.is_game_over()
            continue
        assert score['evidence']['quality'] == q and score['evidence']['complete']
        assert score['cp'] == score['lines'][0]['cp']
        assert score['mate'] == score['lines'][0]['mate']
        assert len({l['moves'][0] for l in score['lines']}) == len(score['lines'])
        for line in score['lines']:
            trial = board.copy()
            for uci in line['moves']:
                move = chess.Move.from_uci(uci)
                assert move in trial.legal_moves, (game['id'], q, fen, uci)
                trial.push(move)
    for algorithm in ('old', 'new'):
        assert run[algorithm]['confirmationSearches'] <= 6
        provisional = {p for p, l in labels(run, algorithm, 'provisional').items() if l == 'brilliant'}
        final = {p for p, l in labels(run, algorithm).items() if l == 'brilliant'}
        assert final <= provisional
        assert set(labels(run, algorithm)) <= set(range(1, len(game['moves'])+1))
        for key, confirmation in run[algorithm]['confirmations'].items():
            ply = int(key)
            for side, index in [('before', ply-1), ('after', ply)]:
                evidence = confirmation[side]['evidence']
                assert evidence['complete'] and evidence['quality'] == q
                assert evidence['depth'] >= run['scores'][index]['evidence']['depth']


def summarize(fast, extra, games):
    for key in PIN_KEYS:
        assert fast[key] == extra[key], ('Provenance mismatch', key)
    assert fast['appSource'] == APP and fast['modelSha256'] == MODEL
    assert fast['planCommit'] == '6844202bf606211c11a27b777560cf009293f30f'
    assert fast['cutoff'] == 0.8193002847777424
    assert (fast['threads'], fast['hashMiB'], fast['multiPV']) == (1, 64, 2)
    assert fast['engine']['binarySha256'] == 'ae4c93fa9676ca7750d0714342fd8a5b1d018000fc6e0f6cedf112067b5ef374'
    assert len(games) == 27
    assert sum(len(g['scoredPlies']) for g in games) == 922
    assert sum(len(g['strictBrilliants']) for g in games) == 32
    runs = {}
    for source, allowed in [(fast, {'fast'}), (extra, {'balanced', 'thorough'})]:
        for run in source['runs']:
            assert run['quality'] in allowed
            key = (run['game'], run['quality'])
            assert key not in runs
            runs[key] = run
    assert len(runs) == 81
    result = {k: fast[k] for k in PIN_KEYS}
    result.update(modes={}, perGame=[], targets=[])
    for quality in ('fast', 'balanced', 'thorough'):
        totals = dict.fromkeys(FIELDS, 0)
        depths = Counter()
        confirmations = Counter()
        starved = []
        low_depth_awards = []
        for game in games:
            run = runs[(game['id'], quality)]
            verify_run(game, run)
            stats = count(game, run)
            for key, value in stats.items():
                totals[key] += value
            result['perGame'].append({'game': game['id'], 'quality': quality, **stats})
            for score in run['scores']:
                if score['lines']:
                    depths[score['evidence']['depth']] += 1
            confirmations[run['new']['confirmationSearches']] += 1
            requested = set(run['new']['confirmationRequested'])
            for row in run['new']['provisional']:
                if row['label'] == 'brilliant' and row['reliable'] is False and row['ply'] not in requested:
                    starved.append({'game': game['id'], 'ply': row['ply']})
            final = labels(run, 'new')
            for ply, label in final.items():
                if label == 'brilliant' and ply in set(game['scoredPlies']):
                    pair = [run['scores'][i]['evidence']['depth'] for i in (ply-1, ply)]
                    if min(pair) < 12:
                        low_depth_awards.append({'game': game['id'], 'ply': ply, 'depths': pair})
            for target in game['strictBrilliants']:
                ply = target['ply']
                d = run['modelDecisions'][str(ply)]
                result['targets'].append({
                    'game': game['id'], 'quality': quality, 'ply': ply,
                    'move': game['sans'][ply-1], 'old': labels(run, 'old').get(ply),
                    'new': final.get(ply), 'candidate': d['candidate'], 'score': d['score'],
                    'depths': [run['scores'][i]['evidence']['depth'] for i in (ply-1, ply)],
                })
        result['modes'][quality] = dict(totals=totals, completedDepths=dict(sorted(depths.items())),
                                       confirmationSearchesPerGame=dict(sorted(confirmations.items())),
                                       unselectedUnreliableBrilliants=starved,
                                       gingerAwardsWithBaselineBelow12=low_depth_awards)
    targets = {(r['game'], r['ply'], r['quality']): r for r in result['targets']}
    shifts = {}
    for quality in ('balanced', 'thorough'):
        rows = []
        for game in games:
            for target in game['strictBrilliants']:
                a = targets[(game['id'], target['ply'], 'fast')]
                b = targets[(game['id'], target['ply'], quality)]
                if a['candidate'] and b['candidate']:
                    rows.append({'game': game['id'], 'ply': target['ply'],
                                 'fastScore': a['score'], 'score': b['score'],
                                 'delta': b['score']-a['score']})
        ds = [r['delta'] for r in rows]
        cutoff = fast['cutoff']
        shifts[quality] = dict(commonCandidates=len(rows), medianDelta=statistics.median(ds),
                               minDelta=min(ds), maxDelta=max(ds),
                               crossesUp=sum(r['fastScore'] < cutoff <= r['score'] for r in rows),
                               crossesDown=sum(r['score'] < cutoff <= r['fastScore'] for r in rows),
                               cases=rows)
    result['targetScoreShiftsFromFast'] = shifts
    return result


def report(result):
    lines = ['# Ginger: Fast, Balanced and Thorough', '',
             'The same 27 games, 32 captured gallery brillies and 922 Ginger moves.',
             'Both classifiers use the same engine evidence within each mode.',
             'Fast is the original published run; Balanced and Thorough use fresh searches.',
             '', '| Mode | En Croissant (adapted): gallery !! found | Open Brilly Finder: gallery !! found | Adapted / new awards outside gallery |',
             '|---|---:|---:|---:|']
    for mode, data in result['modes'].items():
        t = data['totals']
        lines.append(f"| {mode.title()} | {t['oldHits']} / 32 | {t['newHits']} / 32 | {t['oldOutside']} / {t['newOutside']} |")
    lines += ['', '## What changes with the mode', '',
              '| Mode | Gallery labels gained over adapted En Croissant | Labels lost | All adapted / new Brilliant awards |',
              '|---|---:|---:|---:|']
    for mode, data in result['modes'].items():
        t = data['totals']
        lines.append(f"| {mode.title()} | {t['gainedTargets']} | {t['lostTargets']} | {t['oldAwards']} / {t['newAwards']} |")
    lines += ['', 'The model and cutoff are unchanged. These are final app awards after normal',
              'grading precedence, previous-iteration checks and bounded confirmations.',
              'Deeper search can change an evaluation and a label. The table measures the',
              'observed effect; it does not assume deeper evidence always improves a score.',
              '', '## Raw model-score shifts on the same targets', '',
              'These shifts cover only gallery targets that are piece-offer candidates in',
              'both modes. They are baseline model scores before the app reliability guards,',
              'not probabilities or final Brilliant awards.', '',
              '| Compared with Fast | Common candidates | Median score change | Minimum / maximum change | Cutoff crossed up / down |',
              '|---|---:|---:|---:|---:|']
    for mode, d in result['targetScoreShiftsFromFast'].items():
        lines.append(f"| {mode.title()} | {d['commonCandidates']} | {d['medianDelta']:+.4f} | {d['minDelta']:+.4f} / {d['maxDelta']:+.4f} | {d['crossesUp']} / {d['crossesDown']} |")
    lines += ['', '## Search evidence', '',
              '| Mode | Nonterminal positions | Completed depth: number of positions | New Brilliant candidates omitted from confirmation budget |',
              '|---|---:|---|---:|']
    for mode, d in result['modes'].items():
        depths=', '.join(f"{depth}: {n}" for depth,n in d['completedDepths'].items())
        lines.append(f"| {mode.title()} | {sum(d['completedDepths'].values())} | {depths} | {len(d['unselectedUnreliableBrilliants'])} |")
    lines += ['', 'Search requests: Fast 12 / 500 ms, Balanced 14 / 1,000 ms, Thorough 16 /',
              '1,500 ms. Time limits can stop an iteration before the requested depth.',
              'The app retains its existing completeness and annotation-agreement guards.',
              'Evidence-depth and budget diagnostics cover both players; award totals count',
              'only Ginger’s moves. All runs use one thread, 64 MiB hash, MultiPV 2 and normal within-session hash',
              'reuse. Each classifier keeps its normal six-search-unit confirmation budget.',
              '', '## Every captured gallery move', '',
              'Each cell is adapted En Croissant / Open Brilly Finder: !! means a final',
              'Brilliant award, and — means no Brilliant award.', '',
              '| Game | Move | Fast: adapted / new | Balanced: adapted / new | Thorough: adapted / new |',
              '|---|---|---|---|---|']
    by = {(r['game'],r['ply'],r['quality']): r for r in result['targets']}
    for r in result['targets']:
        if r['quality'] != 'fast': continue
        cells=[]
        for q in ('fast','balanced','thorough'):
            v=by[(r['game'],r['ply'],q)]
            cells.append(('!!' if v['old']=='brilliant' else '—')+' / '+('!!' if v['new']=='brilliant' else '—'))
        move=f"{(r['ply']+1)//2}"+('.' if r['ply']%2 else '...')+r['move']
        lines.append(f"| [{r['game']}](https://www.chess.com/game/live/{r['game']}) | {move} | "+' | '.join(cells)+' |')
    lines += ['', '## Scope and reproduction', '',
              'This sample was selected for containing gallery brillies. Awards outside the',
              'captured gallery are disagreements, not proven false positives. These results',
              'do not establish precision across ordinary games or calibrate the model.',
              'They test the app’s current mode behavior rather than reproduce the training',
              'search distribution. They do not measure Android speed or memory.', '',
              '[Plan](PLAN.md) · [Original sample and overlap audit](../REPORT.md) ·',
              '[All counts and scores](summary.json) · [Raw searches](engine-runs.json.gz)', '',
              'Use the shared Flutter host environment and desktop Stockfish 18. The runner',
              'takes the existing Ginger runner input wrapped with the pinned provenance and',
              '`qualities: ["balanced", "thorough"]`. Resume completed checkpoints with',
              '`BRILLY_STUDY_RESUME=1`; a partial game/mode is rerun, never counted twice.',
              'The 120-minute harness timeout does not change any engine search budget.', '',
              '```sh',
              'python tools/compare_ginger_modes.py --runs /path/to/ginger-balanced-thorough.json',
              '```', '',
              'No Android builds, Actions, LFS downloads, model changes or website deployment.']
    return '\n'.join(lines)+'\n'


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--runs', required=True, type=Path)
    args=p.parse_args()
    frozen_hashes=verify_frozen_inputs()
    fast=read(ROOT/'ginger/engine-runs.json.gz')
    extra=read(args.runs)
    games=read(ROOT/'ginger/runner-input.json')
    result=summarize(fast,extra,games)
    result['frozenInputSha256']=frozen_hashes
    output=ROOT/'ginger/modes'
    output.mkdir(exist_ok=True)
    (output/'engine-runs.json.gz').write_bytes(gzip.compress(json.dumps(extra,separators=(',',':')).encode()+b'\n',mtime=0))
    (output/'summary.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    (output/'REPORT.md').write_text(report(result))
    print(json.dumps({q:d['totals'] for q,d in result['modes'].items()},indent=2))
    print('PASS: all 81 game/mode runs, legal mainlines and PVs, complete evidence, confirmation depths and budgets, fixed source/model pins.')
    print('Raw follow-up SHA256',hashlib.sha256((output/'engine-runs.json.gz').read_bytes()).hexdigest())


if __name__ == '__main__':
    main()
