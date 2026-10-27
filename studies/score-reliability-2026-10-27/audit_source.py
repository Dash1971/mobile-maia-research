"""Independently replay source selection and clocks, without inference/downloads.

  python audit_source.py --source /path/allie-test.jsonl --scratch /path/cache

Expanded studies require cached validation JSONL files and official compressed
prefixes from collect_supplement.py. Only data/source-crosscheck.json is written.
No collector/study code is imported; chess replay and selection are recalculated.
"""
import argparse
import codecs
import collections
import hashlib
import io
import json
import math
import re
from pathlib import Path

import chess
import chess.pgn

ROOT = Path(__file__).resolve().parent
SOURCE_HASH = 'a6014de8ef861b2ee23a84d7ce824e644390577a000350fad06bd995bcddab0d'
REVISION = '990f79105b1f08a8fd367fcb10c5e18c69436e30'
SEED = 2026102701
RESULT = {'1-0': 1., '0-1': 0., '1/2-1/2': .5}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def rows(path):
    return [json.loads(line) for line in path.read_bytes().splitlines()]


def priority(kind, game, *tail):
    return sha('|'.join(map(str, (SEED, kind, game, *tail))).encode())


def replay(game, target):
    """Check complete legal game; independently choose minimum-hash eligible ply."""
    try:
        ratings = [int(game[s + '-elo']) for s in ('white', 'black')]
    except (KeyError, TypeError, ValueError):
        return 'missing_ratings', None
    if not all(target - 100 <= elo <= target + 100 for elo in ratings):
        return 'outside_band', None
    if not game['event'].startswith('Rated Blitz') or game['termination'] != 'Normal' or game['result'] not in RESULT:
        return 'event_or_result_excluded', None
    try:
        base, inc = [int(x) for x in game['time-control'].split('+')]
        moves, seconds = game['moves-uci'].split(), game['moves-seconds']
        assert base > 0 and inc >= 0 and len(moves) == len(seconds)
        assert all(isinstance(x, (int, float)) and math.isfinite(x) and x >= 0 for x in seconds)
    except (KeyError, TypeError, ValueError, AssertionError):
        return 'invalid_clocks', None
    board = chess.Board()
    history = [board.fen(en_passant='fen')]
    clocks = [float(base), float(base)]
    first_pressure = False
    candidates = []
    for ply, (uci, spent) in enumerate(zip(moves, seconds)):
        try:
            move = chess.Move.from_uci(uci)
        except ValueError:
            return 'illegal_replay', None
        if move not in board.legal_moves:
            return 'illegal_replay', None
        side = int(board.turn == chess.BLACK)
        remaining = clocks[side] - spent
        first_pressure = first_pressure or min(clocks) < 30 or remaining < 30
        if not first_pressure and board.fullmove_number >= 11 and not board.is_game_over(claim_draw=False):
            candidates.append(dict(ply=ply, history=history[-8:].copy(), prefixUci=moves[:ply], playedUci=uci, clocksBefore=clocks.copy(), moverClockAfterThink=remaining))
        clocks[side] = remaining + inc
        board.push(move)
        history.append(board.fen(en_passant='fen'))
    outcome = board.outcome(claim_draw=False)
    if outcome is not None and outcome.result() != game['result']:
        return 'contradictory_result', None
    if not candidates:
        return 'no_eligible_position', None
    chosen = min(candidates, key=lambda x: priority('position', game['game-id'], x['ply']))
    chosen.update(game=game['game-id'], elo=target, whiteElo=ratings[0], blackElo=ratings[1], result=game['result'], actualWhiteScore=RESULT[game['result']], termination='Normal', timeControl=game['time-control'], eligiblePositions=len(candidates), consistency=False)
    return 'eligible', chosen


def check_observation(observed, expected):
    for field, value in expected.items():
        if field != 'consistency':
            assert observed[field] == value, (observed['game'], field)


def original_selection(original, sample):
    seen_ids, seen_sequences = set(), set()
    cohorts = {1600: [], 2600: []}
    for game in original:
        gid, sequence = game['game-id'], game['moves-uci']
        if gid in seen_ids or sequence in seen_sequences:
            continue
        seen_ids.add(gid); seen_sequences.add(sequence)
        try:
            ratings = [int(game[s + '-elo']) for s in ('white', 'black')]
        except (KeyError, TypeError, ValueError):
            continue
        target = next((elo for elo in cohorts if all(abs(x - elo) <= 100 for x in ratings)), None)
        if target is not None:
            status, observed = replay(game, target)
            if status == 'eligible':
                cohorts[target].append(observed)
    expected = []
    for elo, cap in ((1600, 500), (2600, 250)):
        selected = sorted(cohorts[elo], key=lambda x: priority('game', x['game']))[:cap]
        expected.extend(selected)
    assert len(sample) == len(expected)
    for observed, selected in zip(sample, expected):
        check_observation(observed, selected)
    return {str(elo): len(group) for elo, group in cohorts.items()}


def pgn_record(block):
    parsed = chess.pgn.read_game(io.StringIO(block))
    if parsed is None or parsed.errors:
        raise ValueError('Invalid PGN')
    h = parsed.headers
    if h.get('SetUp') == '1' or 'FEN' in h or h.get('Variant', 'Standard') != 'Standard':
        raise ValueError('Nonstandard start')
    base, inc = map(int, h['TimeControl'].split('+'))
    previous = [base, base]
    moves, seconds = [], []
    for ply, node in enumerate(parsed.mainline()):
        clock = node.clock()
        if clock is None or not math.isfinite(clock) or clock < 0:
            raise ValueError('Missing or invalid clock')
        post_move = int(clock)
        side = ply % 2
        # Preserve the pinned ALLIE conversion, including first-move increment.
        seconds.append(previous[side] + inc - post_move)
        previous[side] = post_move
        moves.append(node.move.uci())
    return {'game-id': h['Site'], 'moves-uci': ' '.join(moves), 'moves-seconds': seconds, 'event': h['Event'], 'result': h['Result'], 'white-elo': h['WhiteElo'], 'black-elo': h['BlackElo'], 'termination': h['Termination'], 'time-control': h['TimeControl'], 'opening': h.get('Opening', ''), 'utc-date': h.get('UTCDate'), 'utc-time': h.get('UTCTime')}


def decode(raw):
    # Each archive can contain multiple concatenated zstd frames and a partial last one.
    from compression import zstd
    decoded = []
    while raw:
        decompressor = zstd.ZstdDecompressor()
        decoded.append(decompressor.decompress(raw))
        if not decompressor.eof:
            break
        raw = decompressor.unused_data
    return codecs.getincrementaldecoder('utf-8')().decode(b''.join(decoded), final=False)


def supplement_selection(original, supplement, manifest, cache):
    assert manifest['sourceRevision'] == REVISION
    assert manifest['originalSourceSha256'] == SOURCE_HASH
    assert manifest['selectionSeed'] == SEED
    assert manifest['collectorSha256'] == sha((ROOT / 'collect_supplement.py').read_bytes())
    assert len(manifest['validationSources']) == 12
    assert [Path(x['path']).name for x in manifest['validationSources']] == [f'2022-{m:02d}-val.jsonl' for m in range(1, 13)]
    seen_ids = {g['game-id'] for g in original}
    seen_sequences = {g['moves-uci'] for g in original}
    val_selected, all_val = [], []
    totals = collections.Counter()
    for source in manifest['validationSources']:
        raw = (cache / Path(source['path']).name).read_bytes()
        assert len(raw) == source['bytes'] and sha(raw) == source['sha256']
        assert source['revision'] == REVISION
        assert source['url'] == 'https://huggingface.co/datasets/yimingzhang/allie-data/resolve/' + REVISION + '/' + source['path']
        games = [json.loads(line) for line in raw.splitlines()]
        all_val.extend(games)
        counts = collections.Counter()
        for game in games:
            counts['rows'] += 1
            gid, sequence = game['game-id'], game['moves-uci']
            if gid in seen_ids or sequence in seen_sequences:
                counts['duplicates'] += 1
                continue
            seen_ids.add(gid); seen_sequences.add(sequence)
            status, observation = replay(game, 2600)
            counts[status] += 1
            if status == 'eligible':
                val_selected.append((game, observation, source['path']))
        assert dict(counts) == source['counts'], source['path']
        totals.update(counts)
    assert dict(totals) == manifest['validationCounts']
    assert len(val_selected) == 121
    raw_selected = []
    stage_reports = []
    for number, stage in enumerate(manifest['rawStages']):
        size = (8 * 1024**2) * 2**number
        assert size <= 32 * 1024**2 and stage['prefixBytesPerMonth'] == size
        assert len(stage['sources']) == 12
        assert [s['archive'] for s in stage['sources']] == [f'lichess_db_standard_rated_2022-{m:02d}.pgn.zst' for m in range(1, 13)]
        seen_ids = {g['game-id'] for g in original + all_val}
        seen_sequences = {g['moves-uci'] for g in original + all_val}
        pool = []
        for source in stage['sources']:
            raw = (cache / (source['archive'] + '.prefix')).read_bytes()[:size]
            assert len(raw) == size == source['prefixBytes']
            assert sha(raw) == source['prefixSha256']
            assert source['url'] == 'https://database.lichess.org/standard/' + source['archive']
            text = decode(raw)
            assert len(text.encode()) == source['decodedBytes']
            boundaries = [m.start() for m in re.finditer(r'^\[Event ', text, re.MULTILINE)]
            counts, dates = collections.Counter(), []
            for start, end in zip(boundaries, boundaries[1:]):
                block = text[start:end]
                headers = dict(re.findall(r'^\[([^ ]+) "(.*)"\]$', block, re.MULTILINE))
                counts['complete_games'] += 1
                try:
                    in_band = all(2500 <= int(headers[side + 'Elo']) <= 2700 for side in ('White', 'Black'))
                except (KeyError, ValueError, TypeError):
                    counts['missing_ratings'] += 1
                    continue
                if not in_band:
                    counts['outside_band'] += 1
                    continue
                counts['rating_matches'] += 1
                if not headers.get('Event', '').startswith('Rated Blitz') or headers.get('Termination') != 'Normal' or headers.get('Result') not in RESULT:
                    counts['event_or_result_excluded'] += 1
                    continue
                if headers.get('Site') in seen_ids:
                    counts['duplicate_id'] += 1
                    continue
                try:
                    game = pgn_record(block)
                except (KeyError, ValueError, TypeError, AssertionError):
                    counts['invalid_pgn_or_clocks'] += 1
                    continue
                if game['moves-uci'] in seen_sequences:
                    counts['duplicate_sequence'] += 1
                    continue
                seen_ids.add(game['game-id']); seen_sequences.add(game['moves-uci'])
                status, observation = replay(game, 2600)
                counts[status] += 1
                if status == 'eligible':
                    pool.append((game, observation, source['archive']))
                    dates.append(game['utc-date'])
            assert dict(counts) == source['counts'], source['archive']
            assert source['eligibleDateRange'] == ([min(dates), max(dates)] if dates else None)
            assert source['trailingGameDiscarded'] == bool(boundaries)
            headers = {k.lower(): v for k, v in source['http'].items()}
            assert source['responseStatus'] == 206
            assert source['responseMethod'] in ('GET', 'HEAD')
            first_byte = 0 if source['responseMethod'] == 'HEAD' or number == 0 else size // 2
            assert headers.get('content-range', '').startswith(f'bytes {first_byte}-{size - 1}/')
            assert int(headers['content-length']) == size - first_byte
            assert headers['etag'] and headers['last-modified']
            if source['responseMethod'] == 'HEAD':
                assert source['responsePurpose'] == 'cached-prefix-revalidation; initial GET response headers unavailable'
                sidecar = json.loads((cache / (source['archive'] + '.prefix.http.json')).read_text())
                assert sidecar == dict(url=source['url'], prefixSha256=sha(raw), method='HEAD', purpose=source['responsePurpose'], status=206, headers=source['http'])
            stage_reports.append(dict(archive=source['archive'], prefixBytes=size, sha256=sha(raw), eligibleGames=counts['eligible']))
        assert len(pool) == stage['eligibleRawGames']
        assert len(pool) == len({g['game-id'] for g, _, _ in pool}) == len({g['moves-uci'] for g, _, _ in pool})
        if number < len(manifest['rawStages']) - 1:
            assert len(pool) < 154, 'Expanded despite sufficient prior stage'
        else:
            assert len(pool) >= 154
            raw_selected = sorted(pool, key=lambda x: priority('game', x[0]['game-id']))[:154]
    assert raw_selected
    expected = sorted(val_selected, key=lambda x: priority('game', x[0]['game-id'])) + raw_selected
    assert len(expected) == len(supplement) == 275
    assert manifest['selectedGames'] == 275 and manifest['selectedValidationGames'] == 121 and manifest['selectedRawGames'] == 154
    original_ids = {g['game-id'] for g in original}
    original_sequences = {g['moves-uci'] for g in original}
    assert not (original_ids & {g['game-id'] for g in supplement})
    assert not (original_sequences & {g['moves-uci'] for g in supplement})
    assert len({g['game-id'] for g in supplement}) == len({g['moves-uci'] for g in supplement}) == 275
    for index, (observed, (game, position, filename)) in enumerate(zip(supplement, expected)):
        assert {key: observed[key] for key in game} == game, ('Source fields differ', observed['game-id'])
        assert observed['selectedPosition'] == position
        assert observed['sourceFile'] == filename
        kind = 'allie-validation' if index < 121 else 'lichess-archive-prefix'
        assert observed['sourceKind'] == observed['source']['kind'] == kind
        if index < 121:
            assert observed['source'] == dict(kind=kind, path=filename, revision=REVISION)
        else:
            assert observed['source'] == dict(kind=kind, archive=filename, prefixBytes=manifest['rawStages'][-1]['prefixBytesPerMonth'])
    assert manifest['selectedIds']['validation'] == [g['game-id'] for g, _, _ in sorted(val_selected, key=lambda x: priority('game', x[0]['game-id']))]
    assert manifest['selectedIds']['raw'] == [g['game-id'] for g, _, _ in raw_selected]
    return dict(validationGames=121, rawGames=154, rawEligiblePool=len(pool), validationFiles=12, rawStages=len(manifest['rawStages']), prefixes=stage_reports, selectedRawDateRange=[min(g['utc-date'] for g, _, _ in raw_selected), max(g['utc-date'] for g, _, _ in raw_selected)])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--scratch', type=Path)
    args = parser.parse_args()
    raw = args.source.read_bytes()
    assert sha(raw) == SOURCE_HASH
    original = [json.loads(line) for line in raw.splitlines()]
    data = ROOT / 'data'
    sample = rows(data / 'sample.jsonl')
    expanded = (data / 'initial-sample.jsonl').exists()
    initial = rows(data / 'initial-sample.jsonl') if expanded else sample
    eligible_counts = original_selection(original, initial)
    report = dict(status='pass', noInferencePerformed=True, noDownloadsPerformed=True, selectedGames=len(sample), sourceSha256=sha(raw), sampleSha256=sha((data / 'sample.jsonl').read_bytes()), originalEligibleGames=eligible_counts, checks=['Original whole-source game and position hash selection independently replayed', 'Full legal games, normal termination, ratings, outcomes and eight-position history reconstructed', 'Every clock threshold through the sampled move checked; no earlier time pressure allowed', 'Sampled positions chosen before a legal recorded move, from full move 11'])
    source_lookup = {g['game-id']: g for g in original}
    if expanded:
        assert args.scratch, 'Expanded audit requires --scratch with the collector cache'
        supplement = rows(data / 'supplement-games.jsonl')
        manifest = json.loads((data / 'supplement-sources.json').read_text())
        assert manifest['outputSha256'] == sha((data / 'supplement-games.jsonl').read_bytes())
        report['supplement'] = supplement_selection(original, supplement, manifest, args.scratch)
        source_lookup.update({g['game-id']: g for g in supplement})
        report['supplementManifestSha256'] = sha((data / 'supplement-sources.json').read_bytes())
        report['checks'] += ['All twelve cached validation source hashes and counts; all 121 eligible additions', 'Equal official compressed prefixes, hashes, complete-game boundaries and processing counts', 'Integer PGN clock conversion, standard starts and all 304 eligible raw games', 'First sufficient twelve-month stage and 154 lowest game hashes independently selected', 'All supplement source fields, provenance and deterministic sampled positions match cached source', 'No duplicate IDs or full move sequences against the whole original source or among additions']
    sequences = []
    for observation in sample:
        game = source_lookup[observation['game']]
        status, expected = replay(game, observation['elo'])
        assert status == 'eligible'
        check_observation(observation, expected)
        sequences.append(game['moves-uci'])
    assert len(sample) == len({r['game'] for r in sample}) == len(set(sequences))
    report['scope'] = 'Independent direct-source replay and deterministic selection from cached source bytes. No model inference or downloads.'
    report['limits'] = ['Cached bytes match recorded source hashes; HTTP identity is recorded evidence, not an independently refetched response.', 'Full-file official archive checksums do not validate the prefixes; actual cached prefix hashes are checked.', 'Game resampling cannot account for all repeat-player or source/time concentration.']
    report['auditSourceScriptSha256'] = sha(Path(__file__).read_bytes())
    (data / 'source-crosscheck.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
