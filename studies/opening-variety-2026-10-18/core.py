"""79M, history-off research policy; distribution semantics follow pinned Dart.

Encoder/move indexing adapted from the published Mobile Maia sampling study.
This is a research implementation, not application runtime code.
"""
import collections
import hashlib
import math
from pathlib import Path

import chess
import numpy as np
import onnxruntime as ort

MODEL_SHA256 = '3454b03ae78baa64a87b345fdb1a457265d912caec531039b074f07eda0d8010'
APP_SHA = '3702f6f197135dbac9ae38a9aa9720e15c603e5c'
ARMS = {
    'A': {'temperature': 1.0, 'top_p': 1.0, 'opening_variety': False},
    'B': {'temperature': 1.0, 'top_p': 0.95, 'opening_variety': False},
    'C': {'temperature': 1.0, 'top_p': 0.95, 'opening_variety': True},
}


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def encode(board):
    current = np.zeros((64, 12), np.float32)
    black = board.turn == chess.BLACK
    for square, piece in board.piece_map().items():
        square = chess.square_mirror(square) if black else square
        own = (piece.color == chess.WHITE) != black
        current[square, piece.piece_type - 1 + (0 if own else 6)] = 1
    tokens = np.zeros((64, 97), np.float32)
    for slot in range(8):
        tokens[:, slot * 12:(slot + 1) * 12] = current
    return tokens


def move_index(move, black=False):
    f, t = move.from_square, move.to_square
    if black:
        f, t = chess.square_mirror(f), chess.square_mirror(t)
    if move.promotion:
        return 4096 + (chess.square_file(f) * 8 + chess.square_file(t)) * 4 + {
            chess.QUEEN: 0, chess.ROOK: 1, chess.BISHOP: 2, chess.KNIGHT: 3,
        }[move.promotion]
    return f * 64 + t


def effective(arm, fullmove):
    p = ARMS[arm]
    return (1.0, 1.0) if p['opening_variety'] and 1 <= fullmove <= 5 else (
        p['temperature'], p['top_p'])


def weighted_distribution(board, logits, temperature=1.0, top_p=1.0):
    moves = list(board.legal_moves)
    values = [float(logits[move_index(m, board.turn == chess.BLACK)]) for m in moves]
    if temperature <= 0:
        return [moves[max(range(len(moves)), key=values.__getitem__)]], [1.0], False
    temperature = min(1.0, max(0.001, temperature))
    values = [v / temperature for v in values]
    maximum = max(values)
    weighted = [(m, math.exp(v - maximum)) for m, v in zip(moves, values)]
    weighted.sort(key=lambda pair: -pair[1])
    total = sum(w for _, w in weighted)
    nucleus, cumulative = [], 0.0
    for m, w in weighted:
        nucleus.append((m, w))
        cumulative += w / total
        if top_p < 1.0 and cumulative >= max(0.0, top_p):
            break
    boundary_tie = (len(nucleus) < len(weighted) and
                    nucleus[-1][1] == weighted[len(nucleus)][1])
    return [m for m, _ in nucleus], [w for _, w in nucleus], boundary_tie


def draw_move(moves, weights, draw):
    target = draw * sum(weights)
    for move, weight in zip(moves, weights):
        target -= weight
        if target <= 0:
            return move
    return moves[-1]


def position_key(board):
    return ' '.join(board.fen(en_passant='fen').split()[:4])


def outcome(board, counts):
    if board.is_checkmate():
        return ('0-1' if board.turn else '1-0', 'checkmate')
    if board.halfmove_clock >= 100:
        return ('1/2-1/2', 'fifty_moves_actual')
    if board.is_stalemate():
        return ('1/2-1/2', 'stalemate')
    if board.is_insufficient_material():
        return ('1/2-1/2', 'insufficient_material')
    if counts[position_key(board)] >= 3:
        return ('1/2-1/2', 'threefold_repetition_actual')
    return None


class Policy:
    def __init__(self, model, cache_limit=2500):
        assert sha256(model) == MODEL_SHA256, 'Wrong 79M model'
        ort.disable_telemetry_events()
        options = ort.SessionOptions()
        options.intra_op_num_threads = 1
        options.inter_op_num_threads = 1
        options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        self.session = ort.InferenceSession(str(model), sess_options=options,
                                           providers=['CPUExecutionProvider'])
        self.cache = collections.OrderedDict()
        self.cache_limit = cache_limit
        self.calls = self.hits = self.boundary_ties = 0

    def logits(self, board, elo=1600):
        key = (board.board_fen(), board.turn, elo)
        if key in self.cache:
            self.hits += 1
            self.cache.move_to_end(key)
            return self.cache[key]
        logits = self.session.run(['move_logits'], {
            'tokens': encode(board)[None, :, :],
            'self_elo': np.array([elo], np.int64),
            'opponent_elo': np.array([elo], np.int64),
        })[0][0]
        assert np.isfinite(logits).all()
        self.calls += 1
        if self.cache_limit:
            self.cache[key] = logits
            if len(self.cache) > self.cache_limit:
                self.cache.popitem(last=False)
        return logits

    def move(self, board, arm, elo, rng):
        temperature, top_p = effective(arm, board.fullmove_number)
        moves, weights, tie = weighted_distribution(
            board, self.logits(board, elo), temperature, top_p)
        self.boundary_ties += tie
        # Dart consumes one draw even if only one legal/retained move exists.
        return draw_move(moves, weights, rng.random())
