#!/usr/bin/env python3
"""Fixed-node, all-legal-move diagnostic on deterministically selected positions."""
import argparse
import concurrent.futures
import json
import time
from multiprocessing.util import Finalize
from pathlib import Path

import chess
import chess.engine
import numpy as np
from core import ARMS, Policy, effective, move_index, sha256, weighted_distribution

HERE = Path(__file__).resolve().parent
POLICY = ENGINE = None


def initialize(model, engine):
    global POLICY, ENGINE
    POLICY = Policy(model, cache_limit=0)
    ENGINE = chess.engine.SimpleEngine.popen_uci(engine)
    ENGINE.configure({'Threads': 1, 'Hash': 32})
    Finalize(None, ENGINE.quit, exitpriority=10)


def evaluate(case):
    started = time.monotonic()
    board = chess.Board(case['fen'])
    logits = POLICY.logits(board, case['elo'])
    distributions = {}
    for arm in ARMS:
        t, p = effective(arm, board.fullmove_number)
        moves, weights, tie = weighted_distribution(board, logits, t, p)
        assert not tie
        distributions[arm] = {m.uci(): w / sum(weights) for m, w in zip(moves, weights)}
    assert distributions['B'] == distributions['C']
    values = []
    for move in sorted(board.legal_moves, key=lambda m: m.uci()):
        child = board.copy(stack=False)
        child.push(move)
        if child.is_checkmate():
            cp, mate, used, depth = 32000, 1, 0, 0
        elif child.is_stalemate() or child.is_insufficient_material():
            cp, mate, used, depth = 0, None, 0, 0
        else:
            ENGINE.configure({'Clear Hash': None})
            info = ENGINE.analyse(child, chess.engine.Limit(nodes=20000))
            score = info['score'].pov(board.turn)
            cp, mate = score.score(mate_score=32000), score.mate()
            used, depth = info.get('nodes'), info.get('depth')
        values.append({'uci': move.uci(), 'cp': cp, 'mate': mate,
                       'nodes': used, 'depth': depth,
                       'maia_logit': float(logits[move_index(move, not board.turn)])})
    best = max(v['cp'] for v in values)
    measures = {}
    for arm, probs in distributions.items():
        losses = {v['uci']: best - v['cp'] for v in values}
        measures[arm] = {'expected_cp_loss': sum(probs.get(m, 0.) * loss for m, loss in losses.items()),
                         'probability_loss_ge100cp': sum(probs.get(m, 0.) for m, loss in losses.items() if loss >= 100),
                         'probability_loss_ge200cp': sum(probs.get(m, 0.) for m, loss in losses.items() if loss >= 200)}
    raw = distributions['A']
    retained = distributions['C']
    fidelity = {'legal_moves': len(raw), 'retained_moves': len(retained),
                'removed_raw_probability': sum(p for m, p in raw.items() if m not in retained)}
    assert fidelity['removed_raw_probability'] <= .05 + 1e-12
    return {**case, 'values': values, 'probabilities': distributions, 'measures': measures,
            'conditional_fidelity': fidelity,
            'seconds': time.monotonic() - started}


def select(ratings=(600, 1600, 2400)):
    from analyze import read
    all_matches = read('matches')
    cases = []
    for rating in ratings:
        games = sorted([r for r in all_matches if r['elo'] == rating and r['pair_index'] == 0],
                       key=lambda r: r['index'])
        used = set()
        for row in games:
            if row['cluster'] in used or len(used) == 60:
                continue
            for ply in ((12, 24, 40)[row['cluster'] % 3] + row['cluster'] % 2,):
                if len(row['moves_uci']) <= ply:
                    continue
                board = chess.Board()
                for uci in row['moves_uci'][:ply]:
                    board.push_uci(uci)
                if board.is_game_over():
                    continue
                cases.append({'id': f"quality-{rating}-{row['cluster']}", 'elo': rating,
                              'game': row['id'], 'pair_cluster': row['cluster'], 'ply': ply,
                              'fen': board.fen(en_passant='fen')})
                used.add(row['cluster'])
                break
        assert len(used) == 60, (rating, len(used))
    (HERE / 'data/quality-inputs.json').write_text(json.dumps(cases, indent=2) + '\n')
    (HERE / 'data/quality-input-manifest.json').write_text(json.dumps({
        'selection_addendum_sha256': sha256(HERE / 'DIAGNOSTIC_ADDENDUM.md'),
        'selection_script_sha256': sha256(__file__),
        'input_sha256': sha256(HERE / 'data/quality-inputs.json'),
        'positions': len(cases),
    }, indent=2) + '\n')
    return cases


def summarize(rows):
    output = {}
    for rating in (600, 1600, 2400):
        subset = [r for r in rows if r['elo'] == rating]
        assert len(subset) == 60
        rng = np.random.default_rng(58000000000 + rating)
        metrics = {}
        for metric in ('expected_cp_loss', 'probability_loss_ge100cp', 'probability_loss_ge200cp'):
            a = np.array([r['measures']['A'][metric] for r in subset])
            c = np.array([r['measures']['C'][metric] for r in subset])
            delta = c - a
            samples = rng.choice(delta, size=(10000, len(delta)), replace=True).mean(axis=1)
            metrics[metric] = {'A_mean': float(a.mean()), 'C_mean': float(c.mean()),
                               'C_minus_A_mean': float(delta.mean()),
                               'C_minus_A_95_ci': np.quantile(samples, [.025, .975]).tolist()}
        output[str(rating)] = {'positions': len(subset),
                               'plies': dict(__import__('collections').Counter(r['ply'] for r in subset)),
                               'side_to_move': dict(__import__('collections').Counter(
                                   'white' if chess.Board(r['fen']).turn else 'black' for r in subset)),
                               'mean_raw_probability_removed': float(np.mean([
                                   r['conditional_fidelity']['removed_raw_probability'] for r in subset])),
                               'metrics': metrics}
    (HERE / 'quality-results.json').write_text(json.dumps(output, indent=2) + '\n')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--model', required=True)
    ap.add_argument('--stockfish', required=True)
    ap.add_argument('--workers', type=int, default=2)
    ap.add_argument('--rating', type=int, choices=[600, 1600, 2400], default=None,
                    help='Evaluate a completed rating subset; full run resumes remaining cases')
    args = ap.parse_args()
    pinned = json.loads((HERE / 'environment.json').read_text())
    assert sha256(Path(args.stockfish).resolve()) == pinned['stockfish_sha256']
    cases = select((args.rating,) if args.rating is not None else (600, 1600, 2400))
    dest = HERE / 'data/quality.jsonl'
    rows = [json.loads(l) for l in dest.read_text().splitlines()] if dest.exists() else []
    done = {r['id'] for r in rows}
    with concurrent.futures.ProcessPoolExecutor(args.workers, initializer=initialize,
                                                initargs=(args.model, args.stockfish)) as pool:
        futures = [pool.submit(evaluate, c) for c in cases if c['id'] not in done]
        with dest.open('a') as stream:
            for f in concurrent.futures.as_completed(futures):
                row = f.result()
                stream.write(json.dumps(row, separators=(',', ':')) + '\n')
                stream.flush()
                rows.append(row)
                if len(rows) % 10 == 0:
                    print(json.dumps({'quality_positions': len(rows), 'target': 180}), flush=True)
    assert {c['id'] for c in cases} <= {r['id'] for r in rows}
    if args.rating is None:
        assert len(rows) == len(cases) == 180
        summarize(sorted(rows, key=lambda r: r['id']))
    print('COMPLETE', flush=True)


if __name__ == '__main__':
    main()
