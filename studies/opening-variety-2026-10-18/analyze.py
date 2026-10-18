#!/usr/bin/env python3
"""Regenerate match statistics, opening labels, integrity checks, and public PGNs."""
import collections
import csv
import hashlib
import json
import math
from pathlib import Path

import chess
import chess.pgn
import numpy as np
from core import ARMS, outcome, position_key, sha256
from run import MATCH_GAMES, OPENING_GAMES, PAIRS

HERE = Path(__file__).resolve().parent


def read(mode):
    return [json.loads(line) for file in sorted((HERE / 'data').glob(mode + '-*.jsonl'))
            for line in file.read_text().splitlines()]


def relative_elo(score):
    return 400 * math.log10(score / (1 - score)) if 0 < score < 1 else None


def basic(rows):
    counts = collections.Counter(r['score_first'] for r in rows)
    score = sum(r['score_first'] for r in rows) / len(rows)
    return {'games': len(rows), 'wins': counts[1.], 'draws': counts[.5],
            'losses': counts[0.], 'score': score, 'relative_match_elo': relative_elo(score)}


def match_summary(rows, rating, contrast):
    assert len(rows) == MATCH_GAMES[rating]
    rows = sorted(rows, key=lambda r: r['index'])
    clusters = np.array([(rows[i]['score_first'] + rows[i + 1]['score_first']) / 2
                         for i in range(0, len(rows), 2)])
    for i in range(0, len(rows), 2):
        assert rows[i]['cluster'] == rows[i + 1]['cluster']
        assert rows[i]['white'] == rows[i + 1]['black']
    seed = 38000000000 + rating + contrast
    rng = np.random.default_rng(seed)
    samples = []
    for _ in range(100):
        sample = rng.choice(clusters, size=(1000, len(clusters)), replace=True).mean(axis=1)
        samples.append(sample)
    low, high = np.quantile(np.concatenate(samples), [.025, .975])
    caps = [r for r in rows if r['termination'] == 'max_plies']
    uncapped = [r for r in rows if r['termination'] != 'max_plies']
    score_noncaps = sum(r['score_first'] for r in uncapped)
    return {**basic(rows), 'first': rows[0]['first'], 'second': rows[0]['second'],
            'score_95_ci': [float(low), float(high)],
            'relative_match_elo_95_ci': [relative_elo(float(low)), relative_elo(float(high))],
            'bootstrap_seed': seed, 'bootstrap_replicates': 100000,
            'bootstrap_unit': 'reverse-color pair, not independent game',
            'by_first_color': {c: basic([r for r in rows if (r['white'] == r['first']) == (c == 'white')])
                               for c in ('white', 'black')},
            'terminations': dict(collections.Counter(r['termination'] for r in rows)),
            'mean_plies': float(np.mean([len(r['moves_uci']) for r in rows])),
            'max_plies_caps': len(caps),
            'score_excluding_caps': score_noncaps / len(uncapped) if uncapped else None,
            'score_caps_all_loss': score_noncaps / len(rows),
            'score_caps_all_win': (score_noncaps + len(caps)) / len(rows),
            'unique_full_games': len({r['movetext_sha256'] for r in rows})}


def verify_and_pgn(matches, openings):
    assert len(matches) == 3000 and len(openings) == 5400
    assert len({r['id'] for r in matches + openings}) == 8400
    total_plies = 0
    pgn_path = HERE / 'games.pgn'
    claim_rows = []
    with pgn_path.open('w') as pgn:
        for row in matches + openings:
            board = chess.Board()
            counts = collections.Counter({position_key(board): 1})
            canonical_counts = collections.Counter({board._transposition_key(): 1})
            repeated = False
            earliest_claim = None
            game = chess.pgn.Game()
            game.headers.update({'Event': 'Mobile Maia opening-variety study', 'Site': 'local CPU',
                                 'Date': '2026.10.18', 'White': row['white'], 'Black': row['black'],
                                 'ConditioningElo': str(row['elo']), 'StudyId': row['id'],
                                 'Result': row['result'], 'Termination': row['termination'],
                                 'RandomSeeds': json.dumps(row['seeds'], separators=(',', ':'))})
            node = game
            for ply, uci in enumerate(row['moves_uci']):
                assert outcome(board, counts) is None, ('continued terminal', row['id'], ply)
                move = chess.Move.from_uci(uci)
                assert move in board.legal_moves, (row['id'], ply, uci)
                board.push(move)
                node = node.add_variation(move)
                counts[position_key(board)] += 1
                canonical_counts[board._transposition_key()] += 1
                repeated = repeated or canonical_counts[board._transposition_key()] >= 2
                if row['mode'] == 'matches' and earliest_claim is None:
                    if ((board.halfmove_clock >= 99 and board.can_claim_fifty_moves()) or
                            (repeated and board.can_claim_threefold_repetition())):
                        earliest_claim = ply + 1
            assert board.fen(en_passant='fen') == row['final_fen']
            assert hashlib.sha256(' '.join(row['moves_uci']).encode()).hexdigest() == row['movetext_sha256']
            terminal = outcome(board, counts)
            if row['mode'] == 'matches':
                actual = terminal or ('1/2-1/2', 'max_plies')
                assert actual == (row['result'], row['termination'])
                if terminal is None:
                    assert len(row['moves_uci']) == 400
                sw = {'1-0': 1., '0-1': 0., '1/2-1/2': .5}[row['result']]
                assert row['score_first'] == (sw if row['white'] == row['first'] else 1 - sw)
                pgn.write(str(game) + '\n\n')
                claim_rows.append({'id': row['id'], 'elo': row['elo'], 'pair_index': row['pair_index'],
                                   'index': row['index'], 'cluster': row['cluster'],
                                   'first': row['first'], 'second': row['second'], 'white': row['white'],
                                   'score_first': .5 if earliest_claim is not None else row['score_first'],
                                   'earliest_claim_ply': earliest_claim,
                                   'actual_score_first': row['score_first']})
            else:
                assert terminal or len(row['moves_uci']) == 24
            total_plies += len(row['moves_uci'])
    (HERE / 'verification/claim-sensitivity.json').write_text(json.dumps(claim_rows, separators=(',', ':')) + '\n')
    return {'passed': True, 'matches': len(matches), 'opening_rollouts': len(openings),
            'legal_plies_replayed': total_plies, 'unique_ids': 8400,
            'full_game_pgn_sha256': sha256(pgn_path),
            'actual_vs_prospective_claim_changed_results': sum(
                r['score_first'] != r['actual_score_first'] for r in claim_rows)}


def diversity(labels):
    counts = collections.Counter(labels)
    n = len(labels)
    entropy = -sum((v / n) * math.log2(v / n) for v in counts.values())
    return {'samples': n, 'unique': len(counts), 'effective': 2 ** entropy,
            'top_fraction': max(counts.values()) / n,
            'repeat_fraction': 1 - len(counts) / n}


def opening_summary(rows, ratings=(600, 1600, 2400), write_labels=True):
    label_path = HERE.parent / 'maia3-sampling/openings/source/lichess_openings.tsv'
    labels = {}
    for r in csv.DictReader(label_path.open(), delimiter='\t'):
        labels[r['epd']] = (r['eco'], r['name'].split(':')[0])
    enriched = []
    for r in rows:
        board = chess.Board()
        family, eco, trace = 'Unclassified', 'none', []
        for uci in r['moves_uci']:
            board.push_uci(uci)
            # Table uses legal en-passant representation (python-chess default).
            epd = ' '.join(board.fen().split()[:4])
            if epd in labels:
                eco, family = labels[epd]
            trace.append({'eco': eco, 'family': family, 'book_match': epd in labels})
        enriched.append({**r, 'labels': trace})
    by_rating = {}
    for rating in ratings:
        arms = {a: sorted([r for r in enriched if r['elo'] == rating and r['arm'] == a],
                          key=lambda r: r['index']) for a in ARMS}
        assert all(len(v) == OPENING_GAMES[rating] for v in arms.values())
        assert all(a['moves_uci'][:10] == c['moves_uci'][:10]
                   for a, c in zip(arms['A'], arms['C']))
        report = {}
        for arm, subset in arms.items():
            report[arm] = {}
            for depth in (8, 10, 12, 16, 24):
                eligible = [r for r in subset if len(r['moves_uci']) >= depth]
                families = [r['labels'][depth - 1]['family'] for r in eligible]
                lines = [' '.join(r['moves_uci'][:depth]) for r in eligible]
                carried = [r['labels'][min(depth, len(r['labels'])) - 1]['family'] for r in subset]
                eco = [r['labels'][min(depth, len(r['labels'])) - 1]['eco'] for r in subset]
                prefixes = [' '.join(r['moves_uci'][:depth]) +
                            (f" [ended:{r['termination']}]" if len(r['moves_uci']) < depth else '')
                            for r in subset]
                report[arm][str(depth)] = {'families': diversity(families),
                                          'exact_lines': diversity(lines),
                                          'early_terminations': len(subset) - len(eligible),
                                          'unclassified_fraction': families.count('Unclassified') / len(families),
                                          'all_rollouts': {
                                              'families_carried': diversity(carried),
                                              'eco_codes_carried': diversity(eco),
                                              'book_match_at_depth_fraction': sum(
                                                  len(r['labels']) >= depth and r['labels'][depth - 1]['book_match']
                                                  for r in subset) / len(subset),
                                              'exact_prefixes_with_terminal_marker': diversity(prefixes),
                                              'unclassified_fraction': carried.count('Unclassified') / len(carried)}}
        # Pair-resample indices; early terminals carry their last label, explicitly
        # reported separately above. This avoids discarding different survivors.
        family_arrays = {a: np.array([r['labels'][-1]['family'] for r in arms[a]]) for a in ('A', 'C')}
        seed = 48000000000 + rating
        rng = np.random.default_rng(seed)
        ratios = []
        n = len(arms['A'])
        for _ in range(2000):
            idx = rng.integers(0, n, n)
            ratios.append(diversity(family_arrays['C'][idx])['effective'] /
                          diversity(family_arrays['A'][idx])['effective'])
        ratio = diversity(family_arrays['C'])['effective'] / diversity(family_arrays['A'])['effective']
        eco_arrays = {a: np.array([r['labels'][-1]['eco'] for r in arms[a]]) for a in ('A', 'C')}
        eco_seed = 48000100000 + rating
        eco_rng = np.random.default_rng(eco_seed)
        eco_ratios = []
        for _ in range(2000):
            idx = eco_rng.integers(0, n, n)
            eco_ratios.append(diversity(eco_arrays['C'][idx])['effective'] /
                              diversity(eco_arrays['A'][idx])['effective'])
        first_divergence = collections.Counter()
        for a, c in zip(arms['A'], arms['C']):
            different = next((i + 1 for i, (x, y) in enumerate(zip(a['moves_uci'], c['moves_uci']))
                              if x != y), None)
            if different is None and len(a['moves_uci']) != len(c['moves_uci']):
                different = min(len(a['moves_uci']), len(c['moves_uci'])) + 1
            first_divergence[str(different) if different is not None else 'same_through_end'] += 1
        by_rating[str(rating)] = {'arms': report, 'all_final_labels_CA_ratio': ratio,
                                  'all_final_labels_CA_ratio_95_ci': np.quantile(ratios, [.025, .975]).tolist(),
                                  'bootstrap_seed': seed, 'bootstrap_replicates': 2000,
                                  'CA_same_final_family': int(sum(family_arrays['A'] == family_arrays['C'])),
                                  'supplementary_book_matches_after_ply10': {
                                      a: sum(any(step['book_match'] for step in r['labels'][10:]) for r in arms[a])
                                      for a in ARMS},
                                  'supplementary_posthoc_ECO': {
                                      'CA_ratio': diversity(eco_arrays['C'])['effective'] / diversity(eco_arrays['A'])['effective'],
                                      'CA_ratio_95_ci': np.quantile(eco_ratios, [.025, .975]).tolist(),
                                      'CA_same_final_ECO': int(sum(eco_arrays['A'] == eco_arrays['C'])),
                                      'bootstrap_seed': eco_seed, 'bootstrap_replicates': 2000},
                                  'CA_prefix_agreement': {str(d): sum(a['moves_uci'][:d] == c['moves_uci'][:d]
                                                                     for a, c in zip(arms['A'], arms['C']))
                                                          for d in (8, 10, 12, 16, 24)},
                                  'CA_first_divergence_ply': dict(first_divergence),
                                  'AC_identical_first_10_plies': n,
                                  'CA_same_24_ply_line': sum(a['moves_uci'] == c['moves_uci']
                                                           for a, c in zip(arms['A'], arms['C']))}
    if write_labels:
        (HERE / 'data/opening-labels.json').write_text(json.dumps(enriched, separators=(',', ':')) + '\n')
    return {'opening_table_sha256': sha256(label_path), 'by_rating': by_rating}


def main():
    matches, openings = read('matches'), read('openings')
    integrity = verify_and_pgn(matches, openings)
    summaries = {}
    for rating in (600, 1600, 2400):
        summaries[str(rating)] = {}
        for i, (first, second) in enumerate(PAIRS):
            subset = [r for r in matches if r['elo'] == rating and r['pair_index'] == i]
            summaries[str(rating)][f'{first}-{second}'] = match_summary(subset, rating, i)
    claim_rows = json.loads((HERE / 'verification/claim-sensitivity.json').read_text())
    claims = {str(rating): {f'{a}-{b}': basic([r for r in claim_rows if r['elo'] == rating and r['pair_index'] == i])
                           for i, (a, b) in enumerate(PAIRS)} for rating in (600, 1600, 2400)}
    out = {'integrity': integrity, 'matches': summaries, 'claim_sensitivity': claims,
           'openings': opening_summary(openings), 'analysis_sha256': sha256(__file__)}
    (HERE / 'results.json').write_text(json.dumps(out, indent=2) + '\n')
    (HERE / 'verification/integrity.json').write_text(json.dumps(integrity, indent=2) + '\n')
    print(json.dumps({'integrity': integrity, 'primary_C_A_1600': summaries['1600']['C-A']}, indent=2))


if __name__ == '__main__':
    main()
