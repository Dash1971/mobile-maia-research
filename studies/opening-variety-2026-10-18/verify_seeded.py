#!/usr/bin/env python3
"""Replay one reverse-color pair in every rating/contrast from recorded seeds."""
import argparse
import collections
import json
import random
from pathlib import Path

import chess
from core import Policy, outcome, position_key, sha256

HERE = Path(__file__).resolve().parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--model', required=True)
    args = ap.parse_args()
    policy = Policy(args.model)
    rows = [json.loads(line) for p in sorted((HERE / 'data').glob('matches-*.jsonl'))
            for line in p.read_text().splitlines()]
    selected = [r for r in rows if r['index'] in (0, 1)]
    assert len(selected) == 18
    checks = []
    for row in selected:
        seed = 18000000000 + row['elo'] * 1000000 + row['pair_index'] * 100000 + row['cluster'] * 10
        expected_seeds = {row['first']: seed, row['second']: seed + 1}
        assert expected_seeds == row['seeds']
        rngs = {a: random.Random(s) for a, s in row['seeds'].items()}
        board = chess.Board()
        counts = collections.Counter({position_key(board): 1})
        for ply, expected in enumerate(row['moves_uci']):
            assert outcome(board, counts) is None
            arm = row['white'] if board.turn else row['black']
            actual = policy.move(board, arm, row['elo'], rngs[arm])
            assert actual.uci() == expected, (row['id'], ply, actual.uci(), expected)
            board.push(actual)
            counts[position_key(board)] += 1
        assert board.fen(en_passant='fen') == row['final_fen']
        checks.append({'id': row['id'], 'plies': len(row['moves_uci']), 'passed': True})
        print('replayed', row['id'], flush=True)
    receipt = {'passed': True, 'games': checks, 'inferences': policy.calls,
               'cutoff_ties': policy.boundary_ties, 'verifier_sha256': sha256(__file__)}
    assert policy.boundary_ties == 0
    (HERE / 'verification/seeded-replay.json').write_text(json.dumps(receipt, indent=2) + '\n')


if __name__ == '__main__':
    main()
