#!/usr/bin/env python3
"""Fixed-size, resumable match and opening experiments; output shards are durable."""
import argparse
import collections
import concurrent.futures
import datetime
import json
import os
import platform
import random
import sys
import time
from pathlib import Path

import chess
import numpy as np
import onnxruntime as ort
from core import APP_SHA, ARMS, MODEL_SHA256, Policy, outcome, position_key, sha256

HERE = Path(__file__).resolve().parent
PAIRS = [('C', 'A'), ('B', 'A'), ('C', 'B')]
POLICY = None
MATCH_GAMES = {600: 200, 1600: 600, 2400: 200}
OPENING_GAMES = {600: 400, 1600: 1000, 2400: 400}


def initialize(model):
    global POLICY
    POLICY = Policy(model)


def tasks(mode):
    jobs = []
    if mode in ('matches', 'all'):
        for elo in (1600, 600, 2400):
            for pair_index in range(3):
                for offset in range(0, MATCH_GAMES[elo], 100):
                    jobs.append({'mode': 'matches', 'elo': elo, 'pair': pair_index,
                                 'offset': offset, 'count': 100})
    if mode in ('openings', 'all'):
        for elo in (1600, 600, 2400):
            for arm in ARMS:
                for offset in range(0, OPENING_GAMES[elo], 100):
                    jobs.append({'mode': 'openings', 'elo': elo, 'arm': arm,
                                 'offset': offset, 'count': 100})
    return jobs


def job_id(job):
    return f"{job['mode']}-{job['elo']}-{job.get('pair', job.get('arm'))}-{job['offset']:04d}"


def execute(job):
    jid = job_id(job)
    destination = HERE / 'data' / (jid + '.jsonl')
    rows = []
    if destination.exists():
        rows = [json.loads(l) for l in destination.read_text().splitlines()]
    assert len({r['id'] for r in rows}) == len(rows)
    done = {r['index'] for r in rows}
    started = time.monotonic()
    before_calls = POLICY.calls
    before_ties = POLICY.boundary_ties
    with destination.open('a') as stream:
        for index in range(job['offset'], job['offset'] + job['count']):
            if index in done:
                continue
            board = chess.Board()
            counts = collections.Counter({position_key(board): 1})
            if job['mode'] == 'matches':
                first, second = PAIRS[job['pair']]
                white, black = ((first, second) if index % 2 == 0 else (second, first))
                # Reverse-color games are a statistical cluster. Streams follow profile.
                seed = 18000000000 + job['elo'] * 1000000 + job['pair'] * 100000 + (index // 2) * 10
                seeds = {first: seed, second: seed + 1}
                rngs = {arm: random.Random(s) for arm, s in seeds.items()}
                limit = 400
            else:
                white = black = job['arm']
                seed = 28000000000 + job['elo'] * 1000000 + index * 10
                seeds = {'white': seed, 'black': seed + 1}
                # Matched A/B/C rollouts share streams: A/C must match through ply 10.
                rngs = {True: random.Random(seed), False: random.Random(seed + 1)}
                limit = 24
            moves = []
            while len(moves) < limit and outcome(board, counts) is None:
                arm = white if board.turn else black
                rng = rngs[arm] if job['mode'] == 'matches' else rngs[board.turn]
                move = POLICY.move(board, arm, job['elo'], rng)
                assert move in board.legal_moves
                moves.append(move.uci())
                board.push(move)
                counts[position_key(board)] += 1
            terminal = outcome(board, counts)
            row = {'id': f'{jid}-{index:04d}', 'index': index, 'elo': job['elo'],
                   'mode': job['mode'], 'white': white, 'black': black,
                   'seeds': seeds, 'moves_uci': moves,
                   'movetext_sha256': __import__('hashlib').sha256(' '.join(moves).encode()).hexdigest(),
                   'final_fen': board.fen(en_passant='fen'),
                   'termination': terminal[1] if terminal else ('max_plies' if limit == 400 else 'rollout_limit'),
                   'result': terminal[0] if terminal else ('1/2-1/2' if limit == 400 else '*')}
            if job['mode'] == 'matches':
                row.update(first=first, second=second, pair_index=job['pair'], cluster=index // 2)
                score = {'1-0': 1., '0-1': 0., '1/2-1/2': .5}[row['result']]
                row['score_first'] = score if white == first else 1 - score
            else:
                row['arm'] = job['arm']
            stream.write(json.dumps(row, separators=(',', ':')) + '\n')
            stream.flush()
            rows.append(row)
    assert len(rows) == job['count']
    receipt = {'job': job, 'rows': len(rows), 'sha256': sha256(destination),
               'seconds_this_run': time.monotonic() - started,
               'inferences_this_run': POLICY.calls - before_calls,
               'boundary_ties_this_run': POLICY.boundary_ties - before_ties}
    (HERE / 'data' / (jid + '.receipt.json')).write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--model', required=True, type=Path)
    p.add_argument('--mode', choices=['all', 'matches', 'openings'], default='all')
    p.add_argument('--workers', type=int, default=6)
    args = p.parse_args()
    assert sha256(args.model) == MODEL_SHA256
    config = {'study': 'opening-variety-2026-10-18', 'app_sha': APP_SHA,
              'model_sha256': MODEL_SHA256, 'model_bytes': args.model.stat().st_size,
              'arms': ARMS, 'match_games_per_pair': MATCH_GAMES,
              'opening_rollouts_per_arm': OPENING_GAMES, 'history': False,
              'provider': 'CPUExecutionProvider', 'inference_threads': 1,
              'python': platform.python_version(), 'chess': chess.__version__,
              'numpy': np.__version__, 'onnxruntime': ort.__version__,
              'platform': platform.platform(), 'protocol_sha256': sha256(HERE / 'PROTOCOL.md'),
              'core_sha256': sha256(HERE / 'core.py'), 'runner_sha256': sha256(__file__)}
    manifest = HERE / 'manifest.json'
    if manifest.exists():
        assert json.loads(manifest.read_text()) == config, 'Study configuration changed'
    else:
        manifest.write_text(json.dumps(config, indent=2) + '\n')
    jobs = tasks(args.mode)
    missing = []
    for job in jobs:
        dest = HERE / 'data' / (job_id(job) + '.jsonl')
        receipt = HERE / 'data' / (job_id(job) + '.receipt.json')
        if dest.exists() and receipt.exists():
            assert json.loads(receipt.read_text())['sha256'] == sha256(dest)
        else:
            missing.append(job)
    print(json.dumps({'jobs': len(jobs), 'remaining': len(missing), 'workers': args.workers}), flush=True)
    with concurrent.futures.ProcessPoolExecutor(args.workers, initializer=initialize,
                                                initargs=(str(args.model),)) as pool:
        futures = {pool.submit(execute, job): job for job in missing}
        for future in concurrent.futures.as_completed(futures):
            receipt = future.result()
            print(json.dumps(receipt), flush=True)
    print('COMPLETE', flush=True)


if __name__ == '__main__':
    main()
