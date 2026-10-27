"""Reproduce the fixed-protocol Maia score study; see README.md for commands."""
from pathlib import Path
import argparse, collections, hashlib, json, math, platform, time
import chess
import numpy as np
import onnxruntime as ort

ROOT = Path(__file__).resolve().parent
SOURCE_HASH = 'a6014de8ef861b2ee23a84d7ce824e644390577a000350fad06bd995bcddab0d'
MODEL_HASH = '3454b03ae78baa64a87b345fdb1a457265d912caec531039b074f07eda0d8010'

def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1048576), b''): h.update(block)
    return h.hexdigest()

def priority(*parts):
    return hashlib.sha256('|'.join(map(str, parts)).encode()).hexdigest()

def read_rows(path):
    with open(path) as f: return [json.loads(line) for line in f]

def write_rows(path, rows):
    with open(path, 'w') as f:
        for row in rows: f.write(json.dumps(row, separators=(',', ':'), allow_nan=False) + '\n')

def select(source):
    assert digest(source) == SOURCE_HASH, 'Wrong source bytes'
    out = ROOT / 'data'; out.mkdir(exist_ok=True)
    seen_ids, seen_sequences = set(), set()
    counts = collections.Counter(); cohorts = {1600: [], 2600: []}
    for g in read_rows(source):
        counts['source_games'] += 1
        gid, sequence = g['game-id'], g['moves-uci']
        if gid in seen_ids or sequence in seen_sequences:
            counts['duplicates'] += 1; continue
        seen_ids.add(gid); seen_sequences.add(sequence)
        try: ratings = [int(g['white-elo']), int(g['black-elo'])]
        except (KeyError, ValueError, TypeError): counts['missing_ratings'] += 1; continue
        target = next((e for e in cohorts if all(abs(r-e) <= 100 for r in ratings)), None)
        if target is None: counts['outside_bands'] += 1; continue
        label = str(target)
        counts[label + '_rating_matches'] += 1
        if not g['event'].startswith('Rated Blitz') or g['termination'] != 'Normal' or g['result'] not in ['1-0', '0-1', '1/2-1/2']:
            counts[label + '_event_or_result_excluded'] += 1; continue
        try:
            base, increment = map(int, g['time-control'].split('+'))
            assert base > 0 and increment >= 0
            ucis, seconds = sequence.split(), g['moves-seconds']
            assert len(ucis) == len(seconds)
            assert all(isinstance(t, (float, int)) and math.isfinite(t) and t >= 0 for t in seconds)
        except (KeyError, TypeError, ValueError, AssertionError):
            counts[label + '_invalid_clocks'] += 1; continue
        board = chess.Board(); fens = [board.fen(en_passant='fen')]
        clocks = [float(base), float(base)]; eligible = True; candidates = []; valid = True
        for ply, (uci, spent) in enumerate(zip(ucis, seconds)):
            try: move = chess.Move.from_uci(uci)
            except ValueError: valid = False; break
            if move not in board.legal_moves: valid = False; break
            side = ply % 2
            if min(clocks) < 30 or clocks[side] - spent < 30: eligible = False
            if eligible and board.fullmove_number >= 11 and not board.is_game_over(claim_draw=False):
                candidates.append({'ply': ply, 'history': fens[-8:].copy(), 'prefixUci': ucis[:ply], 'playedUci': uci, 'clocksBefore': clocks.copy(), 'moverClockAfterThink': clocks[side]-spent})
            clocks[side] += increment - spent
            board.push(move); fens.append(board.fen(en_passant='fen'))
        if not valid: counts[label + '_illegal_replay'] += 1; continue
        outcome = board.outcome(claim_draw=False)
        if outcome is not None and outcome.result() != g['result']:
            counts[label + '_contradictory_result'] += 1; continue
        if not candidates: counts[label + '_no_eligible_position'] += 1; continue
        chosen = min(candidates, key=lambda r: priority(2026102701, 'position', gid, r['ply']))
        chosen.update(game=gid, elo=target, whiteElo=ratings[0], blackElo=ratings[1], result=g['result'], actualWhiteScore={'1-0': 1., '0-1': 0., '1/2-1/2': .5}[g['result']], termination=g['termination'], timeControl=g['time-control'], eligiblePositions=len(candidates))
        cohorts[target].append(chosen)
    sample = []
    for target, desired in [(1600, 500), (2600, 250)]:
        counts[str(target) + '_eligible_games'] = len(cohorts[target])
        chosen = sorted(cohorts[target], key=lambda r: priority(2026102701, 'game', r['game']))[:desired]
        ids = {r['game'] for r in sorted(chosen, key=lambda r: priority(2026102703, 'consistency', r['game']))[:50]}
        for r in chosen: r['consistency'] = r['game'] in ids
        sample.extend(chosen); counts[str(target) + '_selected_games'] = len(chosen)
    assert len(sample) == len({r['game'] for r in sample})
    write_rows(out/'sample.jsonl', sample)
    coverage = {}
    for elo in cohorts:
        rows = [r for r in sample if r['elo'] == elo]
        coverage[str(elo)] = {'games': len(rows), 'termination': dict(collections.Counter(r['termination'] for r in rows)), 'results': dict(collections.Counter(r['result'] for r in rows)), 'timeControls': dict(collections.Counter(r['timeControl'] for r in rows)), 'sideToMove': dict(collections.Counter(r['history'][-1].split()[1] for r in rows)), 'stages': dict(collections.Counter('11-20' if r['ply']//2+1 <= 20 else '21-40' if r['ply']//2+1 <= 40 else '41+' for r in rows)), 'whiteRatingRange': [min(r['whiteElo'] for r in rows), max(r['whiteElo'] for r in rows)], 'blackRatingRange': [min(r['blackElo'] for r in rows), max(r['blackElo'] for r in rows)], 'meanWhiteRating': float(np.mean([r['whiteElo'] for r in rows])), 'meanBlackRating': float(np.mean([r['blackElo'] for r in rows]))}
    (out/'selection.json').write_text(json.dumps({'counts': dict(counts), 'coverage': coverage, 'sourceSha256': SOURCE_HASH, 'sampleSha256': digest(out/'sample.jsonl'), 'protocolSha256': digest(ROOT/'PROTOCOL.md')}, indent=2))
    print(json.dumps({'counts': dict(counts), 'coverage': coverage}, indent=2), flush=True)

def tokens(history, enabled=True):
    window = history[-8:] if enabled else history[-1:]
    window = [window[0]] * (8-len(window)) + window
    array = np.zeros((64, 97), dtype=np.float32)
    for t, fen in enumerate(window):
        board = chess.Board(fen); black = board.turn == chess.BLACK
        for square, piece in board.piece_map().items():
            sq = chess.square_mirror(square) if black else square
            own = piece.color == board.turn
            array[sq, 12*t + piece.piece_type - 1 + (0 if own else 6)] = 1
    return array

def move_index(move, black):
    start, end = move.from_square, move.to_square
    if black: start, end = chess.square_mirror(start), chess.square_mirror(end)
    if move.promotion: return 4096 + (chess.square_file(start)*8 + chess.square_file(end))*4 + {chess.QUEEN: 0, chess.ROOK: 1, chess.BISHOP: 2, chess.KNIGHT: 3}[move.promotion]
    return start*64 + end

def board_from_row(row):
    board = chess.Board()
    for uci in row['prefixUci']: board.push_uci(uci)
    assert board.fen(en_passant='fen') == row['history'][-1]
    return board

class Model:
    def __init__(self, model):
        assert digest(model) == MODEL_HASH, 'Wrong model bytes'
        opts = ort.SessionOptions(); opts.intra_op_num_threads = 2; opts.inter_op_num_threads = 1
        opts.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_BASIC
        opts.enable_mem_pattern = False
        self.session = ort.InferenceSession(str(model), sess_options=opts, providers=['CPUExecutionProvider'])
    def predict(self, history, elo, enabled=True):
        token = tokens(history, enabled)
        ml, vl = self.session.run(['move_logits', 'value_logits'], {'tokens': token[None], 'self_elo': np.array([elo], np.int64), 'opponent_elo': np.array([elo], np.int64)})
        v = vl[0].astype(float); assert len(v) == 3 and np.isfinite(v).all()
        q = np.exp(v-max(v)); q /= sum(q); stm = float(q[2]+.5*q[1])
        white = stm if chess.Board(history[-1]).turn == chess.WHITE else 1-stm
        return ml[0], {'valueLogits': v.tolist(), 'stmLDW': q.tolist(), 'whiteScore': white, 'tokensSha256': hashlib.sha256(token.tobytes()).hexdigest()}

def infer(model_path):
    out = ROOT/'data'; rows = read_rows(out/'sample.jsonl'); model = Model(model_path); start = time.monotonic()
    predictions = []; parent_cache = {}
    with (out/'predictions.jsonl').open('w') as f:
        for i, row in enumerate(rows):
            for history in [True, False]:
                logits, value = model.predict(row['history'], row['elo'], history)
                r = dict(game=row['game'], elo=row['elo'], history=history, actualWhiteScore=row['actualWhiteScore'], **value)
                f.write(json.dumps(r, separators=(',', ':'))+'\n'); predictions.append(r)
                if row['consistency'] and history: parent_cache[(row['game'], row['elo'])] = (logits, value)
            if (i+1)%50 == 0: f.flush(); print('Human outcomes', i+1, '/', len(rows), 'seconds', round(time.monotonic()-start,1), flush=True)
    selected = [r for r in rows if r['consistency']]
    with (out/'consistency.jsonl').open('w') as f:
        for i, row in enumerate(selected):
            board = board_from_row(row); moves = sorted(board.legal_moves, key=lambda m: m.uci())
            for elo in [1600, 2600]:
                logits, value = parent_cache.get((row['game'], elo)) or model.predict(row['history'], elo)
                scores = np.array([float(logits[move_index(m, board.turn == chess.BLACK)]) for m in moves]); weights = np.exp(scores-max(scores)); policy = weights/sum(weights)
                assert abs(sum(policy)-1) < 1e-12
                children = []
                for move, p, logit in zip(moves, policy, scores):
                    child = board.copy(stack=True); child.push(move); child_fen = child.fen(en_passant='fen')
                    _, child_value = model.predict(row['history'] + [child_fen], elo)
                    result = child.outcome(claim_draw=False)
                    score = child_value['whiteScore'] if result is None else .5 if result.winner is None else float(result.winner)
                    children.append(dict(uci=move.uci(), san=board.san(move), index=move_index(move, board.turn == chess.BLACK), logit=float(logit), probability=float(p), childFen=child_fen, terminalResult=result.result() if result else None, childWhiteScore=score, childModel=child_value))
                weighted = math.fsum(r['probability']*r['childWhiteScore'] for r in children)
                r = dict(game=row['game'], sourceElo=row['elo'], elo=elo, parent=value, weightedWhiteScore=weighted, gap=weighted-value['whiteScore'], children=children)
                f.write(json.dumps(r, separators=(',', ':'))+'\n')
            f.flush(); print('Consistency', i+1, '/', len(selected), 'seconds', round(time.monotonic()-start,1), flush=True)
    meta = {'modelSha256': MODEL_HASH, 'sourceSha256': SOURCE_HASH, 'sampleSha256': digest(out/'sample.jsonl'), 'protocolSha256': digest(ROOT/'PROTOCOL.md'), 'scriptSha256': digest(Path(__file__)), 'python': platform.python_version(), 'numpy': np.__version__, 'onnxruntime': ort.__version__, 'chess': chess.__version__, 'seconds': time.monotonic()-start, 'backend': 'local CPU; no phone execution', 'session': {'intraThreads': 2, 'interThreads': 1, 'optimization': 'BASIC', 'memoryPattern': False}, 'files': {p.name: digest(p) for p in [out/'sample.jsonl', out/'predictions.jsonl', out/'consistency.jsonl']}}
    (out/'run.json').write_text(json.dumps(meta, indent=2)); print(json.dumps(meta, indent=2), flush=True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(); sub = parser.add_subparsers(dest='action', required=True)
    s = sub.add_parser('select'); s.add_argument('--source', type=Path, required=True)
    i = sub.add_parser('infer'); i.add_argument('--model', type=Path, required=True)
    args = parser.parse_args()
    if args.action == 'select': select(args.source)
    else: infer(args.model)
