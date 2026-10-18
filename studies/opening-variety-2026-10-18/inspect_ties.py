#!/usr/bin/env python3
"""Investigate every observed tied nucleus boundary against the pinned app.

Replay only completed shards whose receipts count a boundary tie. Preserve the
original study rows; this diagnostic neither changes outcomes nor selects seeds.
"""
import argparse
import json
import random
import subprocess
from pathlib import Path

import chess
from core import Policy, draw_move, effective, weighted_distribution, sha256

HERE = Path(__file__).resolve().parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--model', required=True)
    ap.add_argument('--dart', required=True)
    ap.add_argument('--packages', required=True)
    args = ap.parse_args()
    policy = Policy(args.model)
    cases, scans = [], []
    for file in sorted((HERE / 'data').glob('*.receipt.json')):
        receipt = json.loads(file.read_text())
        count = receipt['boundary_ties_this_run']
        if not count:
            continue
        raw = file.with_name(file.name.replace('.receipt.json', '.jsonl'))
        rows = [json.loads(l) for l in raw.read_text().splitlines()]
        initial = len(cases)
        for row in rows:
            board = chess.Board()
            if row['mode'] == 'matches':
                rngs = {a: random.Random(s) for a, s in row['seeds'].items()}
            else:
                rngs = {True: random.Random(row['seeds']['white']),
                        False: random.Random(row['seeds']['black'])}
            for ply, uci in enumerate(row['moves_uci']):
                arm = row['white'] if board.turn else row['black']
                rng = rngs[arm] if row['mode'] == 'matches' else rngs[board.turn]
                logits = policy.logits(board, row['elo'])
                temperature, top_p = effective(arm, board.fullmove_number)
                moves, weights, tie = weighted_distribution(board, logits, temperature, top_p)
                draw = rng.random()
                selected = draw_move(moves, weights, draw)
                assert selected.uci() == uci, (row['id'], ply)
                if tie:
                    cases.append({'id': f"{row['id']}-ply{ply}", 'game': row['id'],
                                  'elo': row['elo'], 'mode': row['mode'], 'arm': arm,
                                  'fen': board.fen(en_passant='fen'), 'draw': draw,
                                  'logits': logits.tolist(),
                                  'python_selected': selected.uci(),
                                  'python_probabilities': {m.uci(): w / sum(weights) for m, w in zip(moves, weights)}})
                    print('found cutoff tie', cases[-1]['id'], flush=True)
                board.push(selected)
        assert len(cases) - initial == count, (raw.name, count, len(cases) - initial)
        scans.append({'file': raw.name, 'sha256': sha256(raw),
                      'games_replayed': len(rows), 'ties': count})
        print('scanned', raw.name, flush=True)
    inputs = HERE / 'verification/tie-inputs.json'
    inputs.write_text(json.dumps(cases, separators=(',', ':')) + '\n')
    if cases:
        completed = subprocess.run([args.dart, '--packages=' + args.packages,
                                    str(HERE / 'verification/app_sampler.dart'), str(inputs)],
                                   capture_output=True, text=True, check=True)
        dart = json.loads(completed.stdout)
    else:
        dart = []
    findings = []
    for case, app in zip(cases, dart):
        trace = app['trace']['random']
        nucleus = trace['weightedOrder'][:trace['nucleusCount']]
        probs = {r['uci']: r['weight'] / trace['total'] for r in nucleus}
        python = case['python_probabilities']
        all_moves = set(probs) | set(python)
        error = max(abs(probs.get(m, 0.) - python.get(m, 0.)) for m in all_moves)
        findings.append({'id': case['id'], 'game': case['game'], 'elo': case['elo'],
                         'mode': case['mode'], 'arm': case['arm'],
                         'fen': case['fen'], 'draw': case['draw'],
                         'python_selected': case['python_selected'], 'dart_selected': app['selected'],
                         'same_retained_set': probs.keys() == python.keys(),
                         'maximum_probability_difference': error,
                         'total_variation_distance': sum(abs(probs.get(m, 0.) - python.get(m, 0.)) for m in all_moves) / 2,
                         'python_probabilities': python, 'dart_probabilities': probs})
    out = {'investigated_boundary_ties': len(cases), 'scans': scans, 'findings': findings,
           'all_probability_parity': all(r['maximum_probability_difference'] < 1e-12 for r in findings),
           'all_fixed_draw_selections_match': all(r['python_selected'] == r['dart_selected'] for r in findings),
           'verifier_sha256': sha256(__file__)}
    (HERE / 'verification/tie-investigation.json').write_text(json.dumps(out, indent=2) + '\n')
    print(json.dumps({k: v for k, v in out.items() if k not in ('findings', 'scans')}, indent=2), flush=True)


if __name__ == '__main__':
    main()
