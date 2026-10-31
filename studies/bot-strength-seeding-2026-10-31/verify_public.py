#!/usr/bin/env python3
"""Verify published projections and recompute frozen-table metrics, without fitting.

No model inference, database, network, regression fitting or raw fitted-artifact
loading is performed. The omitted primary artifact's hash is provenance only.
"""
import argparse
from collections import Counter, defaultdict
import csv
import datetime as dt
import gzip
import hashlib
import io
import json
import math
from pathlib import Path, PurePosixPath
import re

SCHEMA = 'mute-strength-public-results-v1'
VERSION = 'mute-strength-public-verifier-v1'
SPEEDS = ('blitz', 'rapid')
REQUIRED_ROLES = ('configurations', 'designManifest', 'initialPerfs', 'frozenTrainingPerfs',
                  'finalPerfs', 'games', 'primaryPredictions', 'secondaryPredictions', 'seedBaseline')
ATOL, RTOL = 1e-10, 1e-12


class VerificationError(ValueError):
    pass


def require(ok, message):
    if not ok:
        raise VerificationError(message)


def file_hash(path):
    result = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024*1024), b''):
            result.update(block)
    return result.hexdigest()


def reject_duplicate_keys(pairs):
    value = {}
    for key, item in pairs:
        require(key not in value, 'Duplicate JSON key')
        value[key] = item
    return value


def loads(text):
    return json.loads(text, object_pairs_hook=reject_duplicate_keys)


def read(path):
    return loads(path.read_text())


def read_jsonl(path):
    opener = gzip.open if path.name.endswith('.gz') else open
    with opener(path, 'rt', encoding='utf-8') as source:
        for line_number, line in enumerate(source, 1):
            require(bool(line.strip()), f'{path.name}: blank JSONL line {line_number}')
            yield loads(line)


def safe_file(root, relative):
    require(isinstance(relative, str) and bool(relative), 'Missing public artifact path')
    parts = PurePosixPath(relative)
    require(not parts.is_absolute() and '..' not in parts.parts and '\\' not in relative,
            'Public artifact must use a safe relative path')
    path = root.joinpath(*parts.parts)
    require(root.resolve() in path.resolve().parents and path.is_file() and not path.is_symlink(),
            f'Missing/unsafe public artifact: {relative}')
    return path


def finite(value, label, minimum=None):
    require(isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value),
            f'{label}: finite number required')
    require(minimum is None or value >= minimum, f'{label}: below minimum')
    return value


def integer(value, label, minimum=0):
    finite(value, label, minimum)
    require(int(value) == value, f'{label}: integer required')
    return int(value)


def timestamp(value):
    parsed = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
    require(parsed.tzinfo is not None, 'Timestamps need explicit timezones')
    return parsed.timestamp()


def canonical_digest(value):
    def normalize(item):
        if isinstance(item, float) and item.is_integer():
            return int(item)
        if isinstance(item, list):
            return [normalize(v) for v in item]
        if isinstance(item, dict):
            return {k: normalize(v) for k, v in item.items()}
        return item
    return hashlib.sha256(json.dumps(normalize(value), ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def effective_key(bot):
    t, p = bot['temperature_after_opening'], bot['top_p_after_opening']
    opening = bot['opening']['full_moves'] or 0
    if t == 0 or p == 0:
        t, p = 0, 0
    elif t == 1 and p == 1:
        opening = 0
    return (bot['conditioning_self'], bot['conditioning_opponent'], bot['personality']['history'], t, p, opening)


def verify_checksums(root, provenance, require_outer):
    artifacts = provenance['artifacts']
    require(isinstance(artifacts, dict), 'Artifact hash map required')
    for relative, expected in artifacts.items():
        require(re.fullmatch(r'[0-9a-f]{64}', expected) is not None, 'Invalid artifact SHA-256')
        require(file_hash(safe_file(root, relative)) == expected, f'Artifact checksum mismatch: {relative}')
        require(not relative.lower().endswith(('.onnx', '.pt', '.pth', '.safetensors')),
                'Neural model weights are excluded from this public schema')
    outer = root/'SHA256SUMS'
    require(outer.exists() or not require_outer, 'Final reported-result verification requires SHA256SUMS')
    if outer.exists():
        recorded = {}
        for line in outer.read_text().splitlines():
            if not line or line.startswith('#'):
                continue
            match = re.fullmatch(r'([0-9a-f]{64}) [ *](.+)', line)
            require(match is not None, 'Malformed SHA256SUMS line')
            expected, relative = match.groups()
            require(relative not in recorded and relative != 'SHA256SUMS', 'Duplicate/self checksum entry')
            require(file_hash(safe_file(root, relative)) == expected, f'Publication checksum mismatch: {relative}')
            recorded[relative] = expected
        require('provenance.json' in recorded and set(artifacts) <= recorded.keys(),
                'SHA256SUMS must cover provenance and every declared artifact')
    return {'declaredArtifactChecksumsVerified': len(artifacts), 'outerPublicationChecksumsVerified': outer.exists()}


def predictions(path, expected):
    result = {}
    with path.open(newline='') as source:
        reader = csv.DictReader(source)
        require(reader.fieldnames is not None and {'id', 'speed', 'prediction'} <= set(reader.fieldnames),
                f'{path.name}: prediction columns missing')
        for row in reader:
            key = (row['id'], row['speed'])
            require(key not in result, f'{path.name}: duplicate identity/speed')
            try:
                value = float(row['prediction'])
            except (ValueError, TypeError) as error:
                raise VerificationError(f'{path.name}: invalid prediction') from error
            finite(value, 'Frozen prediction')
            result[key] = value
    require(set(result) == expected, f'{path.name}: missing or extra identity/speed predictions')
    return result


def validate_perfs(perfs, identities, label):
    require(set(perfs) == identities, f'{label}: native identity coverage mismatch')
    for identity in identities:
        require(set(perfs[identity]) == set(SPEEDS), f'{label}: speed coverage mismatch')
        for speed in SPEEDS:
            perf = perfs[identity][speed]
            finite(perf['rating'], 'Native rating')
            finite(perf['rd'], 'Native RD', 0)
            integer(perf['games'], 'Native game count')
            require(isinstance(perf['provisional'], bool), 'Native provisional flag required')


def calculate_metrics(table, heldout, final, games, bootstrap, label_only=False):
    # Preserve the original evaluator's sorted held-out order, NumPy RNG,
    # bootstrap count, quantiles, and White-perspective score convention.
    import numpy as np
    require(np.__version__ == bootstrap['numpyVersion'], 'NumPy version differs from published cached-analysis pin')
    require(bootstrap['method'] == 'numpy-default_rng-configuration-bootstrap'
            and bootstrap['seed'] == 137 and bootstrap['replicates'] == 1000,
            'Unreviewed bootstrap method/seed/count')
    report = {'targetMae': 100, 'speeds': {}, 'noisyLabelTargetMet': False}
    for speed in SPEEDS:
        errors, details, scored = [], [], []
        for identity in sorted(heldout):
            perf = final[identity][speed]
            if perf['games'] <= 0:
                continue
            prediction = table[(identity, speed)]
            error = abs(prediction-perf['rating'])
            errors.append(error)
            details.append({'id': identity, 'prediction': prediction, 'nativeRating': perf['rating'],
                'rd': perf['rd'], 'nativeGames': perf['games'], 'absoluteError': error})
        if not label_only:
            for game in games:
                if game['speed'] != speed or game['state'] != 'finished':
                    continue
                a, b = game['white'], game['black']
                if not {a, b} & heldout:
                    continue
                winner = game['result'].get('winner')
                score = .5 if not winner else float(winner == 'white')
                delta = table[(a, speed)]-table[(b, speed)]
                try:
                    expected = 1/(1+10**(-delta/400))
                except OverflowError:
                    expected = 0.
                scored.append((expected, score))
        rng = np.random.default_rng(137)
        boot = [float(np.mean(rng.choice(errors, size=len(errors), replace=True)))
                for _ in range(1000)] if errors else []
        mae = float(np.mean(errors)) if errors else None
        report['speeds'][speed] = {'configurations': len(details), 'nativeRatingMae': mae,
            'configurationBootstrapMae95': np.quantile(boot, [.025, .975]).tolist() if boot else None,
            'medianNativeRd': float(np.median([row['rd'] for row in details])) if details else None,
            'frozenOutcomeGames': len(scored),
            'brier': float(np.mean([(p-y)**2 for p, y in scored])) if scored else None,
            'expectedScoreCrossEntropy': float(np.mean([-y*np.log(max(p, 1e-12))-(1-y)*np.log(max(1-p, 1e-12))
                for p, y in scored])) if scored else None,
            'meetsNoisyLabelMaeTarget': len(details) == len(heldout) and mae <= 100,
            'details': details}
    report['noisyLabelTargetMet'] = all(value['meetsNoisyLabelMaeTarget'] for value in report['speeds'].values())
    return report


def compare_reported(actual, expected, prefix='evaluation'):
    if isinstance(actual, dict):
        require(isinstance(expected, dict) and actual.keys() == expected.keys(), f'{prefix}: reported keys differ')
        for key in actual:
            compare_reported(actual[key], expected[key], prefix+'.'+key)
    elif isinstance(actual, list):
        require(isinstance(expected, list) and len(actual) == len(expected), f'{prefix}: reported list length differs')
        for index, (a, b) in enumerate(zip(actual, expected)):
            compare_reported(a, b, f'{prefix}[{index}]')
    elif isinstance(actual, (int, float)) and not isinstance(actual, bool):
        require(isinstance(expected, (int, float)) and not isinstance(expected, bool)
                and math.isfinite(expected) and math.isclose(actual, expected, rel_tol=RTOL, abs_tol=ATOL),
                f'{prefix}: numerical result differs')
    else:
        require(type(actual) is type(expected) and actual == expected, f'{prefix}: reported value differs')


def replay_pgns(root, directory, games, artifacts):
    try:
        import chess.pgn
    except ImportError as error:
        raise VerificationError('--verify-pgn requires pinned chess1.11.2') from error
    require(chess.__version__ == '1.11.2', 'PGN replay requires chess1.11.2')
    finished = [game for game in games if game['state'] == 'finished']
    for record in finished:
        relative = directory.rstrip('/')+'/'+record['id']+'.pgn'
        require(relative in artifacts, 'PGN missing from public artifact hash map')
        source = io.StringIO(safe_file(root, relative).read_text())
        game = chess.pgn.read_game(source)
        require(game is not None and not game.errors and chess.pgn.read_game(source) is None,
                'PGN is missing, invalid or contains multiple games')
        board = game.board()
        require(board.fen() == chess.Board().fen(), 'PGN has a nonstandard initial position')
        moves = list(game.mainline_moves())
        require([move.uci() for move in moves] == record['moves'], 'PGN/public UCI sequence mismatch')
        for move in moves:
            require(move in board.legal_moves, 'Illegal PGN move')
            board.push(move)
        result = record['result']
        expected = '1-0' if result.get('winner') == 'white' else '0-1' if result.get('winner') == 'black' else '1/2-1/2'
        require(game.headers.get('Result') == expected, 'PGN/native result mismatch')
        if result['status'] == 'mate':
            require(board.is_checkmate() and board.result() == expected, 'Invalid recorded mate')
        elif result['status'] == 'stalemate':
            require(board.is_stalemate(), 'Invalid recorded stalemate')
    return {'files': len(finished), 'legalReplay': True, 'publicUciParity': True,
            'nativeResultHeaderParity': True, 'mateStalemateEndpointsVerified': True}


def verify_bundle(root, check_reported=False, verify_pgn=False):
    root = root.resolve()
    provenance = read(safe_file(root, 'provenance.json'))
    require(provenance.get('schemaVersion') == SCHEMA and provenance.get('status') == 'final',
            'A final public bundle with the supported schema is required; method drafts are not results')
    require(provenance.get('fullPrimaryFitArtifactIncluded') is False,
            'This public schema uses prediction tables, not raw fitted coefficient artifacts')
    checksums = verify_checksums(root, provenance, check_reported)
    roles = provenance['dataFiles']
    require(set(REQUIRED_ROLES) <= roles.keys(), 'Missing required public data role')
    require(len(set(roles.values())) == len(roles), 'Public data roles must have distinct files')
    for role, relative in roles.items():
        require(relative in provenance['artifacts'], f'Data role lacks a declared hash: {role}')
    paths = {role: safe_file(root, relative) for role, relative in roles.items()}
    bots = read(paths['configurations'])
    require(isinstance(bots, list), 'Configuration roster must be an array')
    bot_map = {bot['id']: bot for bot in bots}
    require(len(bot_map) == len(bots) and bool(bots), 'Empty/duplicate configuration identities')
    identities = set(bot_map)
    for bot in bots:
        a, b = bot['conditioning_self'], bot['conditioning_opponent']
        require(integer(a, 'Self conditioning', 600) <= 2600 and a == b,
                'This study uses equal self/opponent conditioning in600–2600')
        require(isinstance(bot['personality']['history'], bool), 'Fixed history must be boolean')
        for name in ('temperature_after_opening', 'top_p_after_opening'):
            require(finite(bot[name], name, 0) <= 1, 'Sampling input outside0–1')
        integer(bot['opening']['full_moves'] or 0, 'Opening full moves')
    manifest = read(paths['designManifest'])
    train, heldout, existing = (set(manifest[name]) for name in ('trainingIds', 'heldoutIds', 'existingIds'))
    require(len(train) == len(manifest['trainingIds']) and len(heldout) == len(manifest['heldoutIds'])
            and len(existing) == len(manifest['existingIds']) and existing <= train
            and not train & heldout and train | heldout == identities, 'Invalid identity split')
    require(canonical_digest(bots) == manifest['combinedRosterSha256'], 'Public configuration/manifest digest mismatch')
    effective = {identity: effective_key(bot) for identity, bot in bot_map.items()}
    train_keys, test_keys = {effective[i] for i in train}, {effective[i] for i in heldout}
    require(not train_keys & test_keys and len(test_keys) == len(heldout), 'Held-out effective policy aliases/leakage')
    counts = {'identities': len(identities), 'trainingIdentities': len(train),
        'trainingEffectiveConfigurations': len(train_keys), 'heldoutIdentities': len(heldout),
        'heldoutEffectiveConfigurations': len(test_keys), 'crossSplitEffectiveAliases': len(train_keys & test_keys)}
    require(counts == provenance['expectedCounts'], 'Published population counts differ')
    initial, frozen, final = (read(paths[name]) for name in ('initialPerfs', 'frozenTrainingPerfs', 'finalPerfs'))
    for label, perfs in [('initial', initial), ('frozen training', frozen), ('final', final)]:
        validate_perfs(perfs, identities, label)
    pins = provenance['sourcePins']
    for name in ('originalMain', 'secondaryProcedureCommit'):
        require(re.fullmatch(r'[0-9a-f]{40}', pins[name]) is not None, 'Invalid source commit pin')
    for name in ('maiaModelSha256', 'primaryFitArtifactSha256', 'frozenTrainingSnapshotSha256'):
        require(re.fullmatch(r'[0-9a-f]{64}', pins[name]) is not None, 'Invalid source-artifact SHA-256 pin')
    require(file_hash(paths['frozenTrainingPerfs']) == pins['frozenTrainingSnapshotSha256'], 'Published training snapshot bytes differ from original freeze pin')
    require(provenance['secondaryFitTrainingSnapshotSha256'] == pins['frozenTrainingSnapshotSha256'], 'Secondary fit declares a different training snapshot')
    freeze = provenance['predictionFreeze']
    require(freeze['admitted'] == manifest['stages']['trainingEnd']
            and freeze['modelSha256'] == pins['primaryFitArtifactSha256'], 'Freeze provenance mismatch')
    require(timestamp(provenance['timingAmendment']['authorizedAtUtc']) < timestamp(freeze['atUtc']),
            'Timing amendment must retain its pre-held-out prospective boundary')
    tables = {label: predictions(paths[role], {(i, s) for i in identities for s in SPEEDS})
              for label, role in [('primaryV1', 'primaryPredictions'), ('secondaryV2', 'secondaryPredictions')]}
    baseline_scope = provenance.get('seedBaselineScope', 'heldout-native-label-only')
    require(baseline_scope in ('heldout-native-label-only', 'all-identities-native-label-and-outcome'), 'Unknown seed baseline scope')
    require(isinstance(provenance.get('seedBaselineDefinition'), str) and bool(provenance['seedBaselineDefinition'].strip()),
            'Publish the exact seed baseline definition')
    baseline_ids = identities if baseline_scope == 'all-identities-native-label-and-outcome' else heldout
    baseline = predictions(paths['seedBaseline'], {(i, s) for i in baseline_ids for s in SPEEDS})
    for identity in baseline_ids:
        for speed in SPEEDS:
            require(baseline[(identity, speed)] == bot_map[identity]['ratings'][speed]['initial_rating'],
                    'Seed baseline does not match recorded roster initial_rating')
    games = list(read_jsonl(paths['games']))
    by_id, rated_appearances = {}, Counter()
    segment_counts, state_counts, stage_counts = defaultdict(Counter), Counter(), Counter()
    first_heldout = None
    segments = provenance['segments']
    require(isinstance(segments, list) and segments and len({s['id'] for s in segments}) == len(segments),
            'Missing/duplicate execution segments')
    require(len(segments) <= 2, 'Only the original and one validation continuation are supported')
    for segment in segments:
        require(re.fullmatch(r'[0-9a-f]{40}', segment['sourceCommit']) is not None, 'Invalid segment source commit')
    require(segments[0]['sourceCommit'] == pins['originalMain'], 'Original segment/source pin mismatch')
    if len(segments) == 2:
        require(segments[1]['sourceCommit'] == pins.get('continuationMain'), 'Continuation segment/source pin mismatch')
    segment_map = {segment['id']: segment for segment in segments}
    for ordinal, game in enumerate(games, 1):
        identity, speed = game['id'], game['speed']
        require(re.fullmatch(r'[A-Za-z0-9_-]+', identity) is not None and identity not in by_id, 'Invalid/duplicate public game ID')
        require(game['admissionOrdinal'] == ordinal and game['segment'] in segment_map, 'Admission ordering/segment mismatch')
        require(speed in SPEEDS and game['white'] in identities and game['black'] in identities and game['white'] != game['black'], 'Invalid public game seats/speed')
        expected_stage = 'warmup' if ordinal <= manifest['stages']['warmupEnd'] else 'training' if ordinal <= manifest['stages']['trainingEnd'] else 'validation'
        require(game['stage'] == expected_stage, 'Admission stage boundary mismatch')
        seats = {game['white'], game['black']}
        if expected_stage == 'validation':
            require(len(seats & heldout) == 1 and len(seats & train) == 1, 'Validation requires one held-out and one training participant')
            require(timestamp(game['admittedAtUtc']) >= timestamp(freeze['atUtc']), 'Held-out admission precedes model freeze')
            if first_heldout is None:
                first_heldout = game
        else:
            require(seats <= (existing if expected_stage == 'warmup' else train), 'Pre-freeze admission violates split')
        require(game['segment'] == segments[0]['id'] or expected_stage == 'validation',
                'Continuation segment may contain only validation games')
        segment = segment_map[game['segment']]
        require(timestamp(segment['startedAtUtc']) <= timestamp(game['admittedAtUtc']) <= timestamp(segment['endedAtUtc']),
                'Admission observation falls outside its segment worker window')
        state = game['state']
        require(state in ('finished', 'aborted', 'unfinished'), 'Unsupported final public game state')
        if state == 'finished':
            result = game['result']
            require(isinstance(result['ratedUpdate'], bool) and result.get('winner') in (None, 'white', 'black'), 'Invalid native result')
            require(integer(result['plies'], 'Finished plies') == len(game['moves']) and
                    all(re.fullmatch(r'[a-h][1-8][a-h][1-8][qrbn]?', move) for move in game['moves']), 'Public UCI/ply count mismatch')
            if result['ratedUpdate']:
                rated_appearances.update((player, speed) for player in seats)
        by_id[identity] = game
        segment_counts[game['segment']].update([state, 'admitted'])
        state_counts[state] += 1
        stage_counts[expected_stage] += 1
    require(len(games) <= manifest['maximumAdmitted'], 'Aggregate public admission ceiling exceeded')
    offset = 0
    previous_end = None
    for segment in segments:
        count = segment_counts[segment['id']]
        require(segment['admittedAtStart'] == offset and segment['admitted'] == count['admitted'], 'Segment/global admission offset mismatch')
        require(all(segment[state] == count[state] for state in ('finished', 'aborted', 'unfinished')), 'Segment state accounting mismatch')
        selected_ordinals = [g['admissionOrdinal'] for g in games if g['segment'] == segment['id']]
        require(selected_ordinals == list(range(offset+1, offset+count['admitted']+1)), 'Segments must contain consecutive admissions without replay')
        started, ended = timestamp(segment['startedAtUtc']), timestamp(segment['endedAtUtc'])
        require(ended >= started and (previous_end is None or started >= previous_end), 'Segment worker windows overlap or regress')
        offset += count['admitted']
        previous_end = ended
    if first_heldout:
        require(freeze['firstHeldoutAdmissionOrdinal'] == first_heldout['admissionOrdinal']
                and freeze['firstHeldoutAdmissionAtUtc'] == first_heldout['admittedAtUtc'], 'First held-out provenance mismatch')
    unattributed = 0
    for identity in identities:
        for speed in SPEEDS:
            require(initial[identity][speed]['games'] <= frozen[identity][speed]['games'] <= final[identity][speed]['games'], 'Native game counts regress across snapshots')
            delta = final[identity][speed]['games']-initial[identity][speed]['games']
            require(delta >= rated_appearances[(identity, speed)], 'Native game-count deficit relative to study results')
            unattributed += delta-rated_appearances[(identity, speed)]
    ack_report = {'provided': 'acknowledgments' in paths, 'uniqueSequenceVerified': False}
    if 'acknowledgments' in paths:
        seen, attempts = defaultdict(dict), 0
        for ack in read_jsonl(paths['acknowledgments']):
            require(ack['id'] in by_id, 'Acknowledgment has no public study game')
            ply = integer(ack['ply'], 'Acknowledgment ply')
            prior = seen[ack['id']].get(ply)
            require(prior is None or prior == ack['move'], 'Contradictory duplicate acknowledgment')
            seen[ack['id']][ply] = ack['move']
            attempts += 1
        for game in games:
            if game['state'] == 'finished':
                require(seen[game['id']] == dict(enumerate(game['moves'])), 'Published acknowledgment/UCI sequence mismatch')
        unique = sum(len(sequence) for sequence in seen.values())
        ack_report.update(uniqueSequenceVerified=True, acknowledgedEvents=attempts,
                          uniqueAcknowledgedGamePlies=unique, duplicateAcknowledgedEvents=attempts-unique,
                          scope='Complete sequence parity is checked for finished games; unfinished/aborted acknowledgment totals remain separate evidence.')
    import numpy as np
    coverage = {}
    for speed in SPEEDS:
        appearances = [rated_appearances[(identity, speed)] for identity in sorted(heldout)]
        coverage[speed] = {'identities': len(heldout), 'withRatedStudyResult': sum(n > 0 for n in appearances),
            'minRatedStudyAppearances': min(appearances), 'maxRatedStudyAppearances': max(appearances),
            'medianRatedStudyAppearances': float(np.median(appearances)),
            'finalNonprovisional': sum(not final[identity][speed]['provisional'] for identity in heldout),
            'medianFinalRd': float(np.median([final[identity][speed]['rd'] for identity in heldout]))}
    metrics = {'schemaVersion': SCHEMA, 'population': counts, 'heldoutCoverage': coverage,
        'accounting': {'admitted': len(games), 'states': dict(state_counts), 'stages': dict(stage_counts),
            'nativeRatedUpdates': sum(g['state'] == 'finished' and g['result']['ratedUpdate'] for g in games),
            'unattributedNativePlayerResultDelta': unattributed},
        'procedures': {name: calculate_metrics(table, heldout, final, games, provenance['bootstrap'])
                       for name, table in tables.items()},
        'seedBaselineScope': baseline_scope,
        'seedBaseline': calculate_metrics(baseline, heldout, final, games, provenance['bootstrap'],
                                          baseline_scope == 'heldout-native-label-only')}
    if check_reported:
        require('reportedEvaluation' in paths, '--check-reported needs the declared reportedEvaluation file')
        compare_reported(metrics, read(paths['reportedEvaluation']))
    replay = replay_pgns(root, provenance['pgnDirectory'], games, provenance['artifacts']) if verify_pgn else {'legalReplay': False}
    verification = {'verifierVersion': VERSION, 'verifierSourceSha256': file_hash(Path(__file__)),
        **checksums, 'reportedMetricsMatched': check_reported, 'bootstrap': provenance['bootstrap'],
        'pgn': replay, 'acknowledgments': ack_report,
        'frozenTrainingSnapshotBytesVerified': True,
        'originalFullPrimaryArtifactBytesVerified': False,
        'recordedOmittedPrimaryArtifactSha256': pins['primaryFitArtifactSha256'],
        'regressionFitOrInferencePerformed': False,
        'limits': ['Prediction tables and published projections were verified; the omitted fitted-artifact bytes were not.',
            'Declared extraction/source lineage is not an independent reexecution of the original service or regression fit.',
            'Native snapshot count reconciliation is not an independent live database audit.',
            'Resource/capacity calculations belong to the separate published segment summarizer; this verifier does not duplicate them.',
            'Native-label error and Glicko RD do not establish true strength or absolute human Lichess alignment.']}
    return metrics, verification


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--check-reported', action='store_true')
    parser.add_argument('--verify-pgn', action='store_true')
    args = parser.parse_args()
    bundle, output = args.bundle.resolve(), args.output.resolve()
    require(output != bundle and bundle not in output.parents and output not in bundle.parents, 'Output must be separate from publication evidence')
    require(not output.exists() or not any(output.iterdir()), 'Output must be new or empty')
    metrics, verification = verify_bundle(bundle, args.check_reported, args.verify_pgn)
    output.mkdir(parents=True, exist_ok=True)
    (output/'recomputed-evaluation.json').write_text(json.dumps(metrics, indent=2, allow_nan=False)+'\n')
    (output/'verification.json').write_text(json.dumps(verification, indent=2, allow_nan=False)+'\n')
    print(json.dumps({'verifier': VERSION, 'admitted': metrics['accounting']['admitted'],
                      'reportedMetricsMatched': args.check_reported, 'legalPgnReplay': args.verify_pgn}))


if __name__ == '__main__':
    try:
        main()
    except (VerificationError, KeyError, ValueError, TypeError, OSError, ImportError) as error:
        raise SystemExit(f'Public verification refused: {error}')
