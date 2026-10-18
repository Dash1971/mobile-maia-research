#!/usr/bin/env python3
"""Independent cached-data audit; needs numpy/chess but no model or inference."""
import collections
import hashlib
import json
import math
from pathlib import Path

import chess
import numpy as np

HERE = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    report = json.loads((HERE / 'results.json').read_text())
    quality = json.loads((HERE / 'quality-results.json').read_text())
    rows = [json.loads(line) for p in sorted((HERE / 'data').glob('matches-*.jsonl'))
            for line in p.read_text().splitlines()]
    assert len(rows) == 3000
    checks = []
    for elo in (600, 1600, 2400):
        for first, second in (('C', 'A'), ('B', 'A'), ('C', 'B')):
            r = [x for x in rows if x['elo'] == elo and (x['first'], x['second']) == (first, second)]
            scores = [x['score_first'] for x in r]
            published = report['matches'][str(elo)][f'{first}-{second}']
            counter = collections.Counter(scores)
            assert counter[1.] == published['wins']
            assert counter[.5] == published['draws']
            assert counter[0.] == published['losses']
            assert abs(sum(scores) / len(scores) - published['score']) < 1e-14
            assert sum(x['white'] == first for x in r) == len(r) // 2
            checks.append(f'{elo}/{first}-{second}: WDL, score and color balance')
    values = [json.loads(line) for line in (HERE / 'data/quality.jsonl').read_text().splitlines()]
    assert len(values) == 180
    by_id = {r['id']: r for r in rows}
    assert len({(r['elo'], r['pair_cluster']) for r in values}) == 180
    for row in values:
        assert row['ply'] == (12, 24, 40)[row['pair_cluster'] % 3] + row['pair_cluster'] % 2
        original = by_id[row['game']]
        restored = chess.Board()
        for uci in original['moves_uci'][:row['ply']]:
            restored.push_uci(uci)
        assert restored.fen(en_passant='fen') == row['fen']
        fen = chess.Board(row['fen'])
        actual = {m.uci() for m in fen.legal_moves}
        assert {v['uci'] for v in row['values']} == actual
        scores = {v['uci']: v['cp'] for v in row['values']}
        peak = max(scores.values())
        logits = {v['uci']: v['maia_logit'] for v in row['values']}
        maximum = max(logits.values())
        raw = {m: math.exp(v - maximum) for m, v in logits.items()}
        normalizer = sum(raw.values())
        expected = {m: v / normalizer for m, v in raw.items()}
        assert all(abs(expected[m] - row['probabilities']['A'][m]) < 1e-12 for m in actual)
        ranked = sorted(expected, key=lambda m: -expected[m])
        retained, mass = [], 0.
        for m in ranked:
            retained.append(m)
            mass += expected[m]
            if mass >= .95:
                break
        assert set(retained) == set(row['probabilities']['C'])
        assert all(abs(expected[m] / mass - row['probabilities']['C'][m]) < 1e-12 for m in retained)
        for arm in ('A', 'B', 'C'):
            probs = row['probabilities'][arm]
            assert set(probs) <= actual and abs(sum(probs.values()) - 1) < 1e-12
            loss = sum(p * (peak - scores[m]) for m, p in probs.items())
            assert abs(loss - row['measures'][arm]['expected_cp_loss']) < 1e-9
            for threshold in (100, 200):
                mass = sum(p for m, p in probs.items() if peak - scores[m] >= threshold)
                assert abs(mass - row['measures'][arm][f'probability_loss_ge{threshold}cp']) < 1e-12
        assert row['probabilities']['B'] == row['probabilities']['C']
    for rating in (600, 1600, 2400):
        subset = [r for r in values if r['elo'] == rating]
        for metric, published in quality[str(rating)]['metrics'].items():
            for arm in ('A', 'C'):
                mean = sum(r['measures'][arm][metric] for r in subset) / len(subset)
                assert abs(mean - published[arm + '_mean']) < 1e-9
    checks.append('180 cached quality positions: legal coverage, normalized probabilities, expected losses and thresholds')
    labels = json.loads((HERE / 'data/opening-labels.json').read_text())
    assert len(labels) == 5400
    for elo in (600, 1600, 2400):
        arms = {a: sorted([r for r in labels if r['elo'] == elo and r['arm'] == a],
                          key=lambda r: r['index']) for a in ('A', 'B', 'C')}
        assert all(a['moves_uci'][:10] == c['moves_uci'][:10] for a, c in zip(arms['A'], arms['C']))
        for arm, subset in arms.items():
            for depth in (8, 10, 12, 16, 24):
                families = [r['labels'][depth - 1]['family'] for r in subset if len(r['labels']) >= depth]
                count = collections.Counter(families)
                n = len(families)
                effective = math.exp(-sum((v/n) * math.log(v/n) for v in count.values()))
                published = report['openings']['by_rating'][str(elo)]['arms'][arm][str(depth)]['families']
                assert len(count) == published['unique']
                assert abs(effective - published['effective']) < 1e-10
    checks.append('All opening-family counts/entropies and matched first-five-move sequences')
    for path in (HERE / 'data').glob('*.receipt.json'):
        receipt = json.loads(path.read_text())
        raw = path.with_name(path.name.replace('.receipt.json', '.jsonl'))
        assert digest(raw) == receipt['sha256']
        assert receipt['boundary_ties_this_run'] == 0, ('cutoff ties need investigation', path.name)
    out = {'passed': True, 'model_inference_calls': 0, 'checks': checks,
           'results_sha256': digest(HERE / 'results.json'),
           'quality_results_sha256': digest(HERE / 'quality-results.json'),
           'auditor_sha256': digest(Path(__file__))}
    (HERE / 'verification/cached-audit.json').write_text(json.dumps(out, indent=2) + '\n')
    print(json.dumps(out, indent=2))


if __name__ == '__main__':
    main()
