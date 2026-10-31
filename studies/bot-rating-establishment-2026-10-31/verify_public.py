#!/usr/bin/env python3
"""Offline public integrity checks. No fit, model artifact, database or network."""
import argparse
from collections import Counter
import csv
import datetime as dt
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
import re

import chess
import chess.pgn

RUN = 'r20261031n163'
MAIN = '8930c60cced8d85d9aec770dcb0a022a8709a07c'
MODEL = '3454b03ae78baa64a87b345fdb1a457265d912caec531039b074f07eda0d8010'
ROSTER = 'ac9cb13a2c2e6b59daf1c7d09a74527da7c07fcdd166ea2d0389e72c5d669296'
ORIGINAL = '1ba436c37456a7f621225791d6fa039891632f9029076c0377f77683c500b6d7'
PREDICTOR = 'f35c16b5c504abc48ca0b9d7e15bf1f5720f7c271d3ca6a7716186c0152474b1'
SPEEDS = ('blitz', 'rapid')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def pairs(rows):
    result = {}
    for key, value in rows:
        require(key not in result, 'Duplicate JSON key')
        result[key] = value
    return result


def loads(text):
    return json.loads(text, object_pairs_hook=pairs, parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))


def read(path):
    return loads(Path(path).read_text())


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def js_json(value):
    def normalize(item):
        if isinstance(item, float) and item.is_integer(): return int(item)
        if isinstance(item, list): return [normalize(v) for v in item]
        if isinstance(item, dict): return {k: normalize(v) for k, v in item.items()}
        return item
    return json.dumps(normalize(value), ensure_ascii=False, separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(js_json(value).encode()).hexdigest()


def file(root, name):
    relative = Path(name)
    require(not relative.is_absolute() and '..' not in relative.parts, 'Unsafe public artifact path')
    target = Path(root)/relative
    require(target.is_file() and not any(p.is_symlink() for p in [target, *target.parents]), 'Missing/linked public artifact')
    return target


def rows(path):
    opener = gzip.open if str(path).endswith('.gz') else open
    with opener(path, 'rt') as stream:
        for line in stream:
            require(bool(line.strip()), 'Empty JSONL row')
            yield loads(line)


def perfs(values, identities):
    require(set(values) == set(identities), 'Native perf population differs')
    for identity in identities:
        require(set(values[identity]) == set(SPEEDS), 'Native speed map differs')
        for speed in SPEEDS:
            perf = values[identity][speed]
            require(set(perf) == {'rating','rd','volatility','games','provisional'}, 'Unexpected native perf fields')
            require(all(isinstance(perf[k], (int,float)) and not isinstance(perf[k],bool) and math.isfinite(perf[k])
                        for k in ('rating','rd','volatility')), 'Invalid native numeric perf')
            require(0 < perf['rd'] <= 500 and perf['volatility'] > 0 and type(perf['games']) is int and perf['games'] >= 0,
                    'Invalid native uncertainty/count')
            require(type(perf['provisional']) is bool and perf['provisional'] == (perf['rd'] >= 110),
                    'Native provisional flag/RD boundary differs from pinned source')


def flags(values):
    return {speed: sum(not p[speed]['provisional'] for p in values.values()) for speed in SPEEDS}


def epoch_seconds(value):
    return dt.datetime.fromisoformat(value.replace('Z','+00:00')).timestamp()


def policy(production, bot):
    expected = {'bot':bot['id'],'name':bot['name'],'modelSha256':MODEL,
        'encoderRevision':'CSSLab-1e13597c-numpy-history-v1','selfElo':bot['conditioning_self'],
        'opponentElo':bot['conditioning_opponent'],'history':bot['personality']['history'],
        'historyMixture':'fixed per bot','profile':bot['sampling_profile'],
        'openingFullMoves':bot['opening']['full_moves'] or 0,'temperature':bot['temperature_after_opening'],
        'topP':bot['top_p_after_opening'],'timingVersion':'lognormal-mobile-controls-personality-v3',
        'humanTiming':bot['personality']['humanTiming'],'timingStyle':bot['personality']['timingStyle'],
        'rated':False,'calibration':'experimental-unvalidated' if bot['conditioning_self'] >= 2200 else 'unvalidated-provisional'}
    version = digest({'bot':bot,'model':MODEL,'sampler':'softmax-categorical-numpy-pcg64-inclusive-nucleus-v1',
        'timing':'lognormal-mobile-controls-personality-v3'})[:16]
    expected['version'] = 'maia79-lila-v3-' + version
    require(production == expected, 'Fixed production settings/history/personality/version differ')


class StrictGame(chess.pgn.GameBuilder):
    def handle_error(self, error):
        raise ValueError('Invalid or illegal PGN') from error


def replay(path, record, bot_map):
    stream = io.StringIO(Path(path).read_text())
    game = chess.pgn.read_game(stream, Visitor=StrictGame)
    require(game is not None and not game.errors and chess.pgn.read_game(stream, Visitor=StrictGame) is None,
            'Missing/invalid/multiple PGN games')
    board = game.board()
    require(not board.chess960 and board.fen() == chess.STARTING_FEN, 'Nonstandard initial position')
    require(game.headers.get('Site') == 'https://mutechess.org/game/' + record['id'], 'PGN public site differs')
    for side in ('white','black'):
        require(game.headers.get(side.title()) == bot_map[record[side]]['username'] and
                game.headers.get(side.title()+'Title') == 'BOT', 'PGN seats are not exact public BOT identities')
    moves = []
    for move in game.mainline_moves():
        require(move in board.legal_moves, 'Illegal PGN mainline move')
        moves.append(move.uci()); board.push(move)
    result = record['result']; expected = {'white':'1-0','black':'0-1',None:'1/2-1/2'}[result['winner']]
    require(type(result['plies']) is int and result['plies'] == len(moves) and game.headers.get('Result') == expected,
            'PGN native result/plies differ')
    if result['status'] == 'mate' or board.is_checkmate():
        require(result['status'] == 'mate' and board.is_checkmate() and board.result() == expected, 'Mate endpoint differs')
    if result['status'] == 'stalemate' or board.is_stalemate():
        require(result['status'] == 'stalemate' and board.is_stalemate() and expected == '1/2-1/2', 'Stalemate endpoint differs')
    if result['status'] == 'draw': require(expected == '1/2-1/2', 'Native draw has a winner')
    require(game.headers.get('TimeControl') == ('300+3' if record['speed'] == 'blitz' else '600+5'), 'Native PGN clock differs')
    return moves


def verify(root, require_checksums=False):
    require(chess.__version__ == '1.11.2', 'Pinned chess1.11.2 required')
    root = Path(root).resolve(); lineage = read(file(root,'data/integrity-lineage.json'))
    require(lineage['schemaVersion'] == 'night163-public-integrity-v1' and lineage['run'] == RUN and lineage['main'] == MAIN,
            'Wrong completed study provenance')
    for name, expected in lineage['artifacts'].items(): require(sha(file(root,name)) == expected, 'Published artifact checksum differs: '+name)
    if require_checksums:
        checked = set()
        for line in file(root,'SHA256SUMS').read_text().splitlines():
            expected, name = line.split('  ',1)
            require(name not in checked,'Duplicate publication checksum path'); checked.add(name)
            require(sha(file(root,name)) == expected, 'Publication checksum differs: '+name)
        require(set(lineage['artifacts']) | {'data/integrity-lineage.json'} <= checked,
                'Publication checksums omit public integrity evidence')
    bots = read(file(root,'data/configurations.json')); bot_map = {b['id']:b for b in bots}
    require(len(bots) == len(bot_map) == 250 and digest(bots) == ROSTER, 'Frozen250 roster differs')
    source_manifest = file(root,'data/original-design-manifest.json')
    require(sha(source_manifest) == ORIGINAL, 'Exact original source manifest differs')
    manifest = read(source_manifest); training = set(manifest['trainingIds']); heldout = set(manifest['heldoutIds'])
    require(len(training) == 200 and len(heldout) == 50 and not training & heldout and training | heldout == set(bot_map), 'Fixed split differs')
    metadata = read(file(root,'data/establishment-manifest.json'))
    require(metadata['runId'] == RUN and metadata['version'] == 'rating-establishment-v1' and
        metadata['combinedRosterSha256'] == ROSTER and metadata['originalManifestSha256'] == ORIGINAL and
        metadata['trainingIds'] == manifest['trainingIds'] and metadata['heldoutIds'] == manifest['heldoutIds'] and
        metadata['admissionEndUtc'] == '2026-10-31T21:00:00.000Z' and metadata['hardStopUtc'] == '2026-10-31T21:30:00.000Z' and
        metadata['maximumAdmitted'] == 3000 and metadata['maximumConcurrency'] == 22 and metadata['workerCount'] == 2,
        'New-run dated scope differs')
    initial, frozen, final = [read(file(root,'data/'+n)) for n in ('initial-native-perfs.json','frozen-training-perfs.json','final-native-perfs.json')]
    for values in (initial,frozen,final): perfs(values,bot_map)
    require(flags(final) == {'blitz':250,'rapid':250}, 'Final500 native flags not established')
    freeze = lineage['freeze']; require(freeze['admitted'] == 349 and freeze['predictorSourceSha256'] == PREDICTOR and
        sha(file(root,'data/frozen-training-perfs.json')) == freeze['trainingSnapshotSha256'], 'Frozen training boundary/hash differs')
    require(all(not frozen[i][s]['provisional'] for i in training for s in SPEEDS), 'Training400 flags not established at freeze')
    games = list(rows(file(root,'data/games.jsonl.gz')))
    require(len(games) == 826 and len({g['id'] for g in games}) == 826, 'Exactly826 unique admissions required')
    require(len({g['admissionEventIndex'] for g in games}) == len({g['finishEventIndex'] for g in games}) == 826,
            'Duplicate admission/finish event observations')
    counts, freeze_counts, epochs, speeds = Counter(), Counter(), Counter(), Counter()
    acknowledgments = {}
    for row in rows(file(root,'data/acknowledged-moves.jsonl.gz')):
        key = row['id'], row['ply']; require(key not in acknowledgments, 'Duplicate acknowledged game/ply')
        require(type(row['ply']) is int and row['ply'] >= 0 and row['addedWaitMs'] == 0 and type(row['worker']) is int and row['worker'] in (0,1) and
                type(row['concurrency']) is int and 0 < row['concurrency'] <= 22 and
                all(isinstance(row[k],(int,float)) and not isinstance(row[k],bool) and math.isfinite(row[k])
                    for k in ('inferenceMs','totalMs','beforeCommitMs','turnToCommitMs')),
                'ACK scope/worker/waits/concurrency/latency differs')
        acknowledgments[key] = row['move']
    unique_plies = 0
    for ordinal, game in enumerate(games,1):
        require(game['admissionOrdinal'] == ordinal and game['runId'] == RUN and re.fullmatch(r'[A-Za-z0-9]{8}',game['id']) and
            game['white'] in bot_map and game['black'] in bot_map and game['white'] != game['black'] and game['speed'] in SPEEDS,
            'Admission identity/order/speed differs')
        require(game['state'] == 'finished' and game['result']['ratedUpdate'] is True and game['result']['winner'] in (None,'white','black'),
                'Abort/unfinished/unrated result in completed cohort')
        require(game['admissionEventIndex'] < game['finishEventIndex'], 'Finish observation precedes admission')
        require(epoch_seconds(metadata['startedAtUtc']) <= epoch_seconds(game['admittedAtUtc']) < epoch_seconds(metadata['admissionEndUtc']) and
                epoch_seconds(game['finishedAtUtc']) <= epoch_seconds(metadata['hardStopUtc']), 'Game observation outside fixed authorized window')
        before = game['admissionEventIndex'] < freeze['eventIndex']
        if before:
            require(ordinal <= 349 and game['epoch'] == 'training' and game['modelFrozen'] is False and
                {game['white'],game['black']} <= training and game['finishEventIndex'] < freeze['eventIndex'],
                'Training cohort not fully finished/drained before freeze')
        else:
            require(ordinal > 349 and game['modelFrozen'] is True and game['admittedAtUtc'] >= freeze['eventAtUtc'], 'Post-freeze ordering differs')
            if game['epoch'] == 'heldout': require(len({game['white'],game['black']} & heldout) == 1, 'Held-out must play training only')
            else: require(game['epoch'] == 'training-maintenance' and {game['white'],game['black']} <= training, 'Invalid post-freeze epoch')
        for side in ('white','black'):
            wrapper = game['policies'][side]
            require(wrapper['version'] == 'native-no-wait-study-v1' and wrapper['runId'] == RUN and wrapper['addedHumanWait'] is False and wrapper['rated'] is True,
                    'Study policy override differs')
            policy(wrapper['production'],bot_map[game[side]])
            counts[(game[side],game['speed'])] += 1
            if before: freeze_counts[(game[side],game['speed'])] += 1
        moves = replay(file(root,'data/pgns/'+game['id']+'.pgn'),game,bot_map)
        require(moves == game['moves'] and all(acknowledgments.get((game['id'],ply)) == move for ply,move in enumerate(moves)), 'PGN/ACK/UCI parity differs')
        require(sum(key[0] == game['id'] for key in acknowledgments) == len(moves), 'Missing/extra ACK positions')
        unique_plies += len(moves); epochs[game['epoch']] += 1; speeds[game['speed']] += 1
    require(len(acknowledgments) == unique_plies, 'ACKs outside final game set')
    for identity in bot_map:
        for speed in SPEEDS:
            require(final[identity][speed]['games'] - initial[identity][speed]['games'] == counts[(identity,speed)], 'Native final count delta differs')
            require(frozen[identity][speed]['games'] - initial[identity][speed]['games'] == freeze_counts[(identity,speed)], 'Training freeze count delta differs')
    progress = list(rows(file(root,'data/native-progress.jsonl.gz')))
    previous=initial
    for row in progress:
        perfs(row['ratings'],bot_map)
        require(all(row['ratings'][i][s]['games'] >= previous[i][s]['games'] for i in bot_map for s in SPEEDS),
                'Observed native lifetime counts regressed')
        previous=row['ratings']
    complete=[row for row in progress if flags(row['ratings']) == {'blitz':250,'rapid':250}]
    require(complete and epoch_seconds(complete[0]['at']) <= epoch_seconds(lineage['goalReachedAtUtc']), 'Goal lacks a preceding500-flag native observation')
    with file(root,'data/frozen-predictions-v2.csv').open() as stream: prediction_rows = list(csv.DictReader(stream))
    require(len(prediction_rows) == 500 and {(r['id'],r['speed']) for r in prediction_rows} == {(i,s) for i in bot_map for s in SPEEDS} and
        all(math.isfinite(float(r['prediction'])) for r in prediction_rows), 'Frozen prediction coverage differs')
    with file(root,'data/ratings.csv').open() as stream: rating_rows=list(csv.DictReader(stream))
    require(len(rating_rows)==500 and {(r['id'],r['speed']) for r in rating_rows}=={(i,s) for i in bot_map for s in SPEEDS},'Rating CSV population differs')
    for row in rating_rows:
        i,s=row['id'],row['speed'];a,b=initial[i][s],final[i][s]
        expected={'initialNativeRating':a['rating'],'finalNativeRating':b['rating'],'ratingChangeThisRun':b['rating']-a['rating'],
            'absoluteRatingChange':abs(b['rating']-a['rating']),'initialRd':a['rd'],'finalRd':b['rd'],
            'initialGames':a['games'],'finalGames':b['games'],'nativeGamesAdded':counts[(i,s)],
            'studyRatedAppearances':counts[(i,s)],'studyAdmissions':counts[(i,s)]}
        require(all(float(row[k])==value for k,value in expected.items()),'Rating CSV differs from native/game evidence')
        require(row['initialProvisional']==str(a['provisional']) and row['finalProvisional']==str(b['provisional']), 'Rating CSV native flags differ')
    summary=read(file(root,'data/execution-summary.json'))
    require(summary['run']==RUN and summary['main']==MAIN and summary['admitted']==summary['finishedRated']==826 and
        summary['aborted']==summary['unfinished']==0 and summary['trainingFinishedBeforeFreeze']==349 and
        summary['uniqueAcknowledgedPlies']==unique_plies and summary['finalNonprovisional']==flags(final), 'Execution summary differs')
    return {'schemaVersion':'night163-public-verification-v1','run':RUN,'main':MAIN,'finishedRatedGames':len(games),
        'aborted':0,'unfinished':0,'uniqueVerifiedPlies':unique_plies,'uniqueAcknowledgedPlies':len(acknowledgments),
        'duplicateAcknowledgedPlies':0,'trainingFinishedBeforeFreeze':349,'epochs':dict(epochs),'speeds':dict(speeds),
        'finalNonprovisional':flags(final),'ratedPlayerCountIncrements':sum(counts.values()),
        'progressObservations':len(progress),'artifactChecksumsVerified':len(lineage['artifacts']),
        'firstObserved500FlagsAtUtc':complete[0]['at'],'goalReachedAtUtc':lineage['goalReachedAtUtc'],
        'rawModelBytesVerified':False,'fitOrInferencePerformed':False,
        'limits':['Public projection consistency is checked; original service/DB observations are separate operator evidence.',
                  'The omitted fitted artifact is committed by hash; its absent bytes are not independently checked.',
                  'Previously observed policies are follow-up test cases, not fresh unseen-configuration evidence.',
                  'Native establishment does not independently validate external human Lichess alignment.']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle',type=Path,required=True); parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--require-checksums',action='store_true')
    args = parser.parse_args()
    require(not args.output.exists() and args.bundle.resolve() not in args.output.resolve().parents, 'New separate output required')
    report = verify(args.bundle,args.require_checksums)
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('finishedRatedGames','uniqueVerifiedPlies','finalNonprovisional','fitOrInferencePerformed')}))
