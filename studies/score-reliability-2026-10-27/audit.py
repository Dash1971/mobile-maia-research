"""Independently validate saved score-study rows and published summary.

No model inference. Requires numpy and python-chess. Run after summarize.py:
    python audit.py [--study-dir PATH] [--source FILE] [--model FILE]
Only audit.json is written; optional source/model inputs are hash-checked.
"""
from pathlib import Path
import argparse
import collections
import hashlib
import json
import math

import chess
import numpy as np

INITIAL_HASHES = {
    'sample.jsonl': 'f12fb7d79a37f12a43f11d95a789891172970cc0cf919ba4598193bb2f64f9df',
    'predictions.jsonl': '5c8658168abcb1faff736fe0fabe7a4e717b68a22ce301c90d100585402eb361',
    'consistency.jsonl': '90ec8b883c5e118b6e1ea7e6781b9ed45d4a6b9d87019ca6d65708d1633040c9',
}


def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def read_rows(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def check_close(actual, expected, label, tolerance=2e-12):
    assert math.isfinite(float(actual)) and abs(actual - expected) <= tolerance, (label, actual, expected)


def compare_tree(actual, expected, path='summary'):
    if isinstance(expected, dict):
        for key, value in expected.items():
            compare_tree(actual[key], value, path + '.' + key)
    elif isinstance(expected, list):
        assert len(actual) == len(expected), path
        for i, value in enumerate(expected):
            compare_tree(actual[i], value, path + f'[{i}]')
    elif isinstance(expected, bool) or isinstance(expected, str):
        assert actual == expected, (path, actual, expected)
    else:
        check_close(actual, expected, path)


def softmax(logits):
    top = max(logits)
    exp = [math.exp(value - top) for value in logits]
    total = math.fsum(exp)
    return [value / total for value in exp]


def token_digest(fens, history=True):
    selected = fens[-8:] if history else fens[-1:]
    selected = [selected[0]] * (8 - len(selected)) + selected
    features = np.zeros((64, 97), dtype=np.float32)
    for position, fen in enumerate(selected):
        board = chess.Board(fen)
        for square, piece in board.piece_map().items():
            oriented = square if board.turn else square ^ 56
            feature = position * 12 + piece.piece_type - 1 + 6 * (piece.color != board.turn)
            features[oriented, feature] = 1
    return hashlib.sha256(features.tobytes()).hexdigest()


def value_check(value, board, fens, history=True):
    assert len(value['valueLogits']) == len(value['stmLDW']) == 3
    probs = softmax(value['valueLogits'])
    for actual, expected in zip(value['stmLDW'], probs):
        check_close(actual, expected, 'LDW softmax')
    check_close(math.fsum(value['stmLDW']), 1, 'LDW total')
    expected = probs[2] + probs[1] / 2
    if not board.turn:
        expected = 1 - expected
    check_close(value['whiteScore'], expected, 'White perspective')
    assert value['tokensSha256'] == token_digest(fens, history), 'History token digest'


def ci(values):
    return np.percentile(values, [2.5, 97.5]).tolist()


def independent_metrics(predictions, consistency):
    """Use saved rows only, with protocol seeds/order for exact CI comparison."""
    output = {'bootstrapReplicates': 5000, 'calibration': {}, 'historyComparison': {}, 'consistency': {}}
    generator = np.random.default_rng(2026102702)
    for rating in (1600, 2600):
        rows = {mode: sorted((r for r in predictions if r['elo'] == rating and r['history'] == mode), key=lambda r: r['game']) for mode in (True, False)}
        outcomes = np.array([r['actualWhiteScore'] for r in rows[True]])
        indices = generator.integers(len(outcomes), size=(5000, len(outcomes)))
        baseline_error = (outcomes - 0.5) ** 2
        errors = {}
        for mode in (True, False):
            scores = np.array([r['whiteScore'] for r in rows[mode]])
            differences = scores - outcomes
            errors[mode] = differences ** 2
            bins = []
            for number in range(5):
                # Explicit intervals independently check summary's integer bin assignment.
                inside = (scores >= number / 5) & ((scores < (number + 1) / 5) if number < 4 else (scores <= 1))
                count = int(inside.sum())
                entry = {'bin': number, 'lower': number * .2, 'upper': (number + 1) * .2, 'n': count}
                if count:
                    p, y = scores[inside], outcomes[inside]
                    draws = generator.integers(count, size=(5000, count))
                    entry.update(meanPrediction=float(np.mean(p)), meanActualScore=float(np.mean(y)), actualScoreCI=ci(np.mean(y[draws], axis=1)), predictionMinusActual=float(np.mean(p-y)), gapCI=ci(np.mean((p-y)[draws], axis=1)), sparse=count < 30)
                bins.append(entry)
            error = errors[mode]
            output['calibration'][f'{rating}-history-{str(mode).lower()}'] = dict(n=len(scores), meanPrediction=float(scores.mean()), meanActualScore=float(outcomes.mean()), mse=float(error.mean()), mseCI=ci(error[indices].mean(axis=1)), baselineMse=float(baseline_error.mean()), mseMinusBaseline=float((error-baseline_error).mean()), mseMinusBaselineCI=ci((error-baseline_error)[indices].mean(axis=1)), mseReductionPercent=float((1-error.mean()/baseline_error.mean())*100), whiteBias=float(differences.mean()), whiteBiasCI=ci(differences[indices].mean(axis=1)), bins=bins)
        delta = errors[True] - errors[False]
        output['historyComparison'][str(rating)] = dict(onMinusOffMse=float(delta.mean()), pairedCI=ci(delta[indices].mean(axis=1)))
    generator = np.random.default_rng(2026102704)
    for rating in (1600, 2600):
        rows = sorted((r for r in consistency if r['elo'] == rating), key=lambda r: (r['sourceElo'], r['game']))
        gaps = np.array([100 * (r['weightedWhiteScore'] - r['parent']['whiteScore']) for r in rows])
        source = np.array([r['sourceElo'] for r in rows])
        def describe(values):
            absolute = np.abs(values)
            return dict(n=len(values), meanSignedGapPP=float(values.mean()), medianAbsoluteGapPP=float(np.median(absolute)), p90AbsoluteGapPP=float(np.percentile(absolute, 90)), fractionAbove5=float(np.count_nonzero(absolute > 5) / len(values)), fractionAbove10=float(np.count_nonzero(absolute > 10) / len(values)), maxAbsoluteGapPP=float(absolute.max()))
        samples = []
        for cohort in (1600, 2600):
            group = np.flatnonzero(source == cohort)
            samples.append(generator.choice(group, size=(5000, len(group)), replace=True))
        bootstrap = gaps[np.concatenate(samples, axis=1)]
        absolute = np.abs(bootstrap)
        intervals = dict(meanSignedGapPP=ci(bootstrap.mean(axis=1)), medianAbsoluteGapPP=ci(np.median(absolute, axis=1)), p90AbsoluteGapPP=ci(np.percentile(absolute, 90, axis=1)), fractionAbove5=ci(np.mean(absolute > 5, axis=1)), fractionAbove10=ci(np.mean(absolute > 10, axis=1)))
        output['consistency'][str(rating)] = {**describe(gaps), 'CI': intervals, 'bySourceCohort': {str(cohort): describe(gaps[source == cohort]) for cohort in (1600, 2600)}}
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--study-dir', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--source', type=Path)
    parser.add_argument('--model', type=Path)
    args = parser.parse_args()
    root = args.study_dir
    data = root / 'data'
    # A run record is written only after inference has closed both output files.
    run = json.loads((data / 'run.json').read_text())
    selection = json.loads((data / 'selection.json').read_text())
    sample = read_rows(data / 'sample.jsonl')
    predictions = read_rows(data / 'predictions.jsonl')
    consistency = read_rows(data / 'consistency.jsonl')
    summary = json.loads((data / 'summary.json').read_text())
    for filename, checksum in run['files'].items():
        assert digest(data / filename) == checksum, filename
    assert run['sampleSha256'] == selection['sampleSha256'] == digest(data / 'sample.jsonl')
    assert run['protocolSha256'] == selection['protocolSha256'] == digest(root / 'PROTOCOL.md')
    assert run['scriptSha256'] == digest(root / 'study.py')
    assert run['sourceSha256'] == selection['sourceSha256']
    expanded = 'expansionScriptSha256' in run
    initial_sample = sample
    if expanded:
        assert run['expansionScriptSha256'] == digest(root / 'expand.py')
        assert run['collectorScriptSha256'] == digest(root / 'collect_supplement.py')
        initial_run = json.loads((data / 'initial-run.json').read_text())
        for name, expected in INITIAL_HASHES.items():
            assert initial_run['files'][name] == expected, 'Published initial checksum changed: ' + name
        initial_sample = read_rows(data / 'initial-sample.jsonl')
        assert collections.Counter(r['elo'] for r in initial_sample) == {1600: 500, 2600: 225}
        assert collections.Counter(r['elo'] for r in sample) == {1600: 500, 2600: 500}
        # Byte prefixes check preservation of every original row and its ordering.
        for name in ('sample.jsonl', 'predictions.jsonl'):
            original = (data / ('initial-' + name)).read_bytes()
            assert hashlib.sha256(original).hexdigest() == initial_run['files'][name]
            assert (data / name).read_bytes().startswith(original), 'Original bytes changed: ' + name
        assert digest(data / 'consistency.jsonl') == initial_run['files']['consistency.jsonl']
        assert initial_run['modelSha256'] == run['modelSha256']
        assert initial_run['sourceSha256'] == run['sourceSha256']
        assert initial_run['scriptSha256'] == run['scriptSha256']
        supplement = read_rows(data / 'supplement-games.jsonl')
        assert len(supplement) == 275
        assert collections.Counter(g['sourceKind'] for g in supplement) == {'allie-validation': 121, 'lichess-archive-prefix': 154}
        for observed, source in zip(sample[len(initial_sample):], supplement):
            expected = dict(source['selectedPosition'], sourceKind=source['sourceKind'], sourceFile=source['sourceFile'], consistency=False)
            assert observed == expected, 'Supplement sample/source mismatch'
        source_manifest = json.loads((data / 'supplement-sources.json').read_text())
        assert source_manifest['outputSha256'] == digest(data / 'supplement-games.jsonl')
        assert source_manifest['collectorSha256'] == run['collectorScriptSha256']
    external = {}
    for kind, path in [('source', args.source), ('model', args.model)]:
        if path:
            assert digest(path) == run[kind + 'Sha256'], kind
            external[kind] = 'actual bytes verified'
        else:
            external[kind] = 'recorded checksum only; optional input not supplied'
    by_game = {r['game']: r for r in sample}
    assert len(by_game) == len(sample)
    assert len({tuple(r['prefixUci']) for r in sample}) == len(sample), 'Duplicate sampled prefixes'
    boards = {}
    for row in sample:
        assert row['termination'] == 'Normal'
        assert row['elo'] in (1600, 2600)
        assert all(abs(row[side + 'Elo'] - row['elo']) <= 100 for side in ('white', 'black'))
        board = chess.Board()
        fens = [board.fen(en_passant='fen')]
        for move in row['prefixUci']:
            assert chess.Move.from_uci(move) in board.legal_moves
            board.push_uci(move)
            fens.append(board.fen(en_passant='fen'))
        assert fens[-8:] == row['history'] and row['ply'] == len(row['prefixUci'])
        assert board.fullmove_number >= 11 and not board.is_game_over(claim_draw=False)
        assert chess.Move.from_uci(row['playedUci']) in board.legal_moves
        assert min(row['clocksBefore']) >= 30 and row['moverClockAfterThink'] >= 30
        assert row['actualWhiteScore'] == {'1-0': 1, '0-1': 0, '1/2-1/2': .5}[row['result']]
        boards[row['game']] = board
    expected_predictions = {(r['game'], r['elo'], mode) for r in sample for mode in (True, False)}
    actual_predictions = {(r['game'], r['elo'], r['history']) for r in predictions}
    assert actual_predictions == expected_predictions and len(predictions) == len(expected_predictions)
    pred_lookup = {}
    for row in predictions:
        parent = by_game[row['game']]
        assert row['actualWhiteScore'] == parent['actualWhiteScore']
        value_check(row, boards[row['game']], parent['history'], row['history'])
        pred_lookup[(row['game'], row['elo'], row['history'])] = row
    selected = [r for r in sample if r['consistency']]
    assert collections.Counter(r['elo'] for r in selected) == {1600: 50, 2600: 50}
    for rating in (1600, 2600):
        # The second stage explicitly retains the original consistency sample.
        cohort = [r for r in initial_sample if r['elo'] == rating]
        priority = lambda r: hashlib.sha256(f"2026102703|consistency|{r['game']}".encode()).hexdigest()
        assert {r['game'] for r in sorted(cohort, key=priority)[:50]} == {r['game'] for r in selected if r['elo'] == rating}
        current = [r for r in sample if r['elo'] == rating]
        coverage = selection['coverage'][str(rating)]
        expected_coverage = dict(games=len(current), termination=dict(collections.Counter(r['termination'] for r in current)), results=dict(collections.Counter(r['result'] for r in current)), timeControls=dict(collections.Counter(r['timeControl'] for r in current)), sideToMove=dict(collections.Counter(r['history'][-1].split()[1] for r in current)), stages=dict(collections.Counter('11-20' if r['ply']//2+1 <= 20 else '21-40' if r['ply']//2+1 <= 40 else '41+' for r in current)), whiteRatingRange=[min(r['whiteElo'] for r in current), max(r['whiteElo'] for r in current)], blackRatingRange=[min(r['blackElo'] for r in current), max(r['blackElo'] for r in current)], meanWhiteRating=float(np.mean([r['whiteElo'] for r in current])), meanBlackRating=float(np.mean([r['blackElo'] for r in current])))
        if expanded and rating == 2600:
            expected_coverage['sourceCounts'] = dict(collections.Counter(r.get('sourceKind', 'initial-allie-test') for r in current))
        compare_tree(coverage, expected_coverage, 'coverage.' + str(rating))
    expected_consistency = {(r['game'], rating) for r in selected for rating in (1600, 2600)}
    assert {(r['game'], r['elo']) for r in consistency} == expected_consistency
    assert len(consistency) == len(expected_consistency)
    child_count = terminal_count = black_child_count = 0
    largest_policy_error = 0.
    for row in consistency:
        parent = by_game[row['game']]
        board = boards[row['game']]
        assert row['sourceElo'] == parent['elo']
        value_check(row['parent'], board, parent['history'])
        if row['elo'] == parent['elo']:
            recorded = pred_lookup[(row['game'], row['elo'], True)]
            for field in ('valueLogits', 'stmLDW', 'whiteScore', 'tokensSha256'):
                assert row['parent'][field] == recorded[field]
        children = row['children']
        assert {r['uci'] for r in children} == {m.uci() for m in board.legal_moves}
        assert len(children) == board.legal_moves.count()
        probabilities = softmax([r['logit'] for r in children])
        largest_policy_error = max(largest_policy_error, abs(math.fsum(r['probability'] for r in children) - 1))
        for child, probability in zip(children, probabilities):
            check_close(child['probability'], probability, 'full legal softmax')
            move = chess.Move.from_uci(child['uci'])
            start, end = move.from_square, move.to_square
            if not board.turn:
                start, end = start ^ 56, end ^ 56
            index = start * 64 + end if not move.promotion else 4096 + (chess.square_file(start)*8 + chess.square_file(end))*4 + {5: 0, 4: 1, 3: 2, 2: 3}[move.promotion]
            assert child['index'] == index and child['san'] == board.san(move)
            after = board.copy(stack=True)
            after.push(move)
            assert after.fen(en_passant='fen') == child['childFen']
            value_check(child['childModel'], after, parent['history'] + [child['childFen']])
            outcome = after.outcome(claim_draw=False)
            assert child['terminalResult'] == (outcome.result() if outcome else None)
            expected_score = child['childModel']['whiteScore'] if outcome is None else .5 if outcome.winner is None else int(outcome.winner)
            check_close(child['childWhiteScore'], expected_score, 'terminal override')
            child_count += 1
            terminal_count += outcome is not None
            black_child_count += not after.turn
        weighted = math.fsum(r['probability'] * r['childWhiteScore'] for r in children)
        check_close(row['weightedWhiteScore'], weighted, 'weighted child score')
        check_close(row['gap'], weighted - row['parent']['whiteScore'], 'signed residual')
    recalculated = independent_metrics(predictions, consistency)
    compare_tree(summary, recalculated)
    if expanded:
        original_summary = json.loads((data / 'initial-summary.json').read_text())
        for mode in ('true', 'false'):
            compare_tree(summary['calibration']['1600-history-' + mode], original_summary['calibration']['1600-history-' + mode], 'preserved1600')
        compare_tree(summary['historyComparison']['1600'], original_summary['historyComparison']['1600'], 'preserved1600History')
        compare_tree(summary['consistency'], original_summary['consistency'], 'preservedConsistency')
        comparison = json.loads((data / 'expansion-comparison.json').read_text())
        for label, group in [('original225', [r for r in initial_sample if r['elo'] == 2600]), ('additional275', sample[len(initial_sample):]), ('combined500', [r for r in sample if r['elo'] == 2600])]:
            ids = {r['game'] for r in group}
            paired = [r for r in predictions if r['elo'] == 2600 and r['history'] and r['game'] in ids]
            assert len(paired) == len(group)
            p = np.array([r['whiteScore'] for r in paired]); y = np.array([r['actualWhiteScore'] for r in paired])
            compare_tree(comparison[label], dict(games=len(paired), meanPrediction=float(p.mean()), meanActualScore=float(y.mean()), mse=float(np.mean((p-y)**2)), baselineMse=float(np.mean((.5-y)**2)), whiteBias=float(np.mean(p-y))), 'expansionComparison.' + label)
    report = dict(status='pass', noInferencePerformed=True, summaryPointEstimatesAndBootstrapIntervals='all checked against saved rows; agreement within 2e-12', bootstrapReplicates=5000, cohorts={str(elo): dict(n=sum(r['elo'] == elo for r in sample), draws=sum(r['elo'] == elo and r['actualWhiteScore'] == .5 for r in sample)) for elo in (1600, 2600)}, predictions=len(predictions), consistencyRows=len(consistency), legalChildEvaluations=child_count, terminalChildEvaluations=terminal_count, blackToMoveChildEvaluations=black_child_count, largestPolicySumError=largest_policy_error, checks=['Run, sample, protocol, study script and recorded output checksums', 'Unique games and paired history rows', 'Normal endings, rating bands, move eligibility and recorded clocks', 'Full prefix and actual eight-position parent/child history token hashes', 'LDW normalization, logits softmax and White perspective', 'Every legal child, move index, child FEN, SAN and full legal softmax', 'Terminal outcomes from full game prefix and exact result override', 'Draw-aware baseline, MSE, White bias, fixed calibration bins and sparse flags', 'Paired history comparison and stratified consistency bootstrap'], externalByteVerification=external, limits=['No model inference rerun; validates recorded model outputs, not their accuracy against fresh execution.', 'Upstream game selection and full clock reconstruction are not independently rerun by this audit; the saved prefix, recorded clocks and source checksum are checked.', 'Intervals describe game resampling; repeat-player dependence cannot be measured.', 'Source is a known benchmark, not established untouched holdout; normal-ending selected blitz sample limits generalization.'], files={name: digest(root / name) for name in ['PROTOCOL.md', 'study.py', 'summarize.py', 'audit.py']} | {f'data/{name}': digest(data / name) for name in ['sample.jsonl', 'selection.json', 'predictions.jsonl', 'consistency.jsonl', 'run.json', 'summary.json']})
    if expanded:
        report['stage'] = '500 original near-1600; 225 original plus 275 added near-2600'
        report['originalRowsPreserved'] = dict(sample=725, predictions=1450, consistency=200, verification='Original sample and prediction bytes are exact prefixes; consistency file has its original hash; original near-1600 and consistency summaries agree.')
        report['checks'] += ['Expansion and collector hashes, supplement row mapping and all cohort coverage metadata', 'Original 725 sample rows, 1450 predictions and 200 consistency rows unchanged', 'Original225, additional275 and combined500 outcome metrics']
        report['limits'][1] = 'Full source selection and clock reconstruction are checked separately in data/source-crosscheck.json.'
        report['limits'][-1] = 'Original/validation data are established benchmarks; the supplemented Normal-ending prefix sample does not establish a representative untouched holdout.'
        report['files'].update({name: digest(root / name) for name in ['expand.py', 'collect_supplement.py', 'audit_source.py']})
        report['files'].update({f'data/{name}': digest(data / name) for name in ['initial-sample.jsonl', 'initial-predictions.jsonl', 'initial-run.json', 'initial-summary.json', 'supplement-games.jsonl', 'supplement-sources.json', 'expansion-comparison.json']})
    (root / 'audit.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
