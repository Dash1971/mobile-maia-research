#!/usr/bin/env python3
"""Run the pinned app's actual Dart encoder/sampler on model-generated cases."""
import argparse
import json
import random
import re
import subprocess
from pathlib import Path

import chess
import numpy as np
from core import ARMS, Policy, draw_move, effective, encode, move_index, sha256, weighted_distribution

HERE = Path(__file__).resolve().parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--model', required=True, type=Path)
    ap.add_argument('--dart', required=True, type=Path)
    ap.add_argument('--packages', required=True, type=Path)
    args = ap.parse_args()
    policy = Policy(args.model)
    # Official independent PyTorch reference, from the earlier published study.
    ref = (HERE.parent / 'maia3-sampling/strength/portable/reference/maia3_reference.dart').read_text()
    official = []
    for block in ref.split('  Maia3ReferenceCase(')[1:]:
        fen = re.search("fen: '([^']+)'", block)[1]
        se = int(re.search(r'selfElo: (\d+)', block)[1])
        oe = int(re.search(r'opponentElo: (\d+)', block)[1])
        # Official references include unequal ratings; call the session directly.
        board = chess.Board(fen)
        logits = policy.session.run(['move_logits'], {
            'tokens': encode(board)[None, :, :],
            'self_elo': np.array([se], np.int64), 'opponent_elo': np.array([oe], np.int64),
        })[0][0]
        expected = dict((m, float(v)) for m, v in re.findall(
            r"'([a-h][1-8][a-h][1-8][qrbn]?)': ([\d.]+)", block))
        errors = [abs(float(logits[move_index(chess.Move.from_uci(m), not board.turn)]) - v)
                  for m, v in expected.items()]
        assert max(errors) < 1e-4
        official.append({'fen': fen, 'self_elo': se, 'opponent_elo': oe,
                         'moves': len(errors), 'max_absolute_error': max(errors)})
    boards = []
    board = chess.Board()
    rng = random.Random(181818)
    for ply in range(30):
        if ply in (0, 1, 8, 9, 10, 11, 16, 23, 29):
            boards.append(board.copy())
        board.push(rng.choice(list(board.legal_moves)))
    boards.extend(chess.Board(fen) for fen in (
        '4k3/P7/8/8/8/8/7p/4K3 w - - 0 5',
        '4k3/P7/8/8/8/8/7p/4K3 b - - 0 6',
        'r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 6',
        '4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 6',
    ))
    cases = []
    for i, b in enumerate(boards):
        logits = policy.logits(b).tolist()
        for arm in ARMS:
            cases.append({'id': f'{i}-{arm}', 'fen': b.fen(en_passant='fen'),
                          'arm': arm, 'logits': logits, 'draw': 0.37123456789})
    # Numerical and crossing/degenerate boundaries using distinct injected logits.
    for j, (temperature, top_p) in enumerate(((1., .6), (1., 0.), (0., .95), (.5, .9))):
        b = chess.Board()
        logits = np.full(4352, -100., np.float32)
        for m, prob in zip(list(b.legal_moves)[:3], (.55, .3, .15)):
            logits[move_index(m)] = np.log(prob)
        cases.append({'id': f'boundary-{j}', 'fen': b.fen(), 'arm': 'A',
                      'logits': logits.tolist(), 'draw': .90123,
                      'temperature': temperature, 'top_p': top_p})
    source = (HERE / 'source/maia.dart').read_text()
    settings = (HERE / 'source/maia_play_settings.dart').read_text()
    dart = """import 'dart:convert';
import 'dart:io';
import 'dart:math';
import 'dart:typed_data';
import 'package:chess/chess.dart' as chess;
""" + source[source.index('class MaiaMoveProbability'):] + '\n' + settings[settings.index('class MaiaPlaySettings'):] + r'''
class FixedRandom implements Random {
  FixedRandom(this.value);
  final double value;
  double nextDouble() => value;
  int nextInt(int max) => throw UnsupportedError('unused');
  bool nextBool() => throw UnsupportedError('unused');
}
void main(List<String> args) {
  final cases = jsonDecode(File(args.single).readAsStringSync()) as List;
  final output = <Map<String, Object?>>[];
  for (final raw in cases) {
    final c = raw as Map<String, dynamic>;
    final fen = c['fen'] as String;
    final game = chess.Chess.fromFEN(fen);
    final arm = c['arm'];
    final settings = MaiaPlaySettings(temperature: 1.0,
      topP: arm == 'A' ? 1.0 : 0.95, maxOpeningVariety: arm == 'C').forFen(fen);
    Map<String, Object?>? trace;
    final move = MaiaEncoding.sampleLegalMove(game,
      game.moves({'asObjects': true}).cast<chess.Move>(),
      (c['logits'] as List).map((v) => (v as num).toDouble()).toList(),
      temperature: (c['temperature'] as num?)?.toDouble() ?? settings.temperature,
      topP: (c['top_p'] as num?)?.toDouble() ?? settings.topP,
      random: FixedRandom((c['draw'] as num).toDouble()), onSample: (v) => trace = v);
    output.add({'id': c['id'], 'selected': MaiaEncoding.uci(move), 'trace': trace,
      'temperature': settings.temperature, 'top_p': settings.topP,
      'tokens': MaiaEncoding.historicalTokens([fen]).toList()});
  }
  stdout.writeln(jsonEncode(output));
}
'''
    helper = HERE / 'verification/app_sampler.dart'
    helper.write_text(dart)
    inputs = HERE / 'verification/policy-inputs.json'
    inputs.write_text(json.dumps(cases))
    result = subprocess.run([str(args.dart), '--packages=' + str(args.packages),
                             str(helper), str(inputs)], capture_output=True, text=True, check=True)
    outputs = json.loads(result.stdout)
    checks = []
    max_error = 0.
    for c, d in zip(cases, outputs):
        assert c['id'] == d['id']
        b = chess.Board(c['fen'])
        assert np.array_equal(encode(b).reshape(-1), np.array(d['tokens']))
        t, p = effective(c['arm'], b.fullmove_number)
        assert (t, p) == (d['temperature'], d['top_p'])
        t, p = c.get('temperature', t), c.get('top_p', p)
        moves, weights, tie = weighted_distribution(b, c['logits'], t, p)
        assert not tie
        selected = moves[0] if t <= 0 else draw_move(moves, weights, c['draw'])
        assert selected.uci() == d['selected']
        if t > 0:
            trace = d['trace']['random']
            dart_weights = trace['weightedOrder'][:trace['nucleusCount']]
            py_probs = {m.uci(): w / sum(weights) for m, w in zip(moves, weights)}
            total = trace['total']
            dart_probs = {r['uci']: r['weight'] / total for r in dart_weights}
            assert py_probs.keys() == dart_probs.keys()
            error = max(abs(py_probs[m] - dart_probs[m]) for m in py_probs)
            max_error = max(max_error, error)
            assert error < 1e-12
        checks.append({'id': c['id'], 'selected': d['selected'], 'retained': len(moves)})
    receipt = {'passed': True, 'official_pytorch_cases': official,
               'dart_cases': checks, 'maximum_probability_error': max_error,
               'checks': ['all encoder tokens', 'effective phase for both colors',
                          'retained sets/probabilities', 'fixed-draw selections',
                          'promotion/castling/en-passant mapping', 'crossing and zero boundaries'],
               'dart_helper_sha256': sha256(helper), 'input_sha256': sha256(inputs)}
    (HERE / 'verification/policy-parity.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({'passed': True, 'cases': len(checks), 'max_error': max_error}))


if __name__ == '__main__':
    main()
