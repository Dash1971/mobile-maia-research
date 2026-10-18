// Independent app-library replay: no Python game rules determine this result.
import 'dart:convert';
import 'dart:io';
import 'package:chess/chess.dart' as chess;

void main(List<String> args) {
  var checkedGames = 0;
  var checkedPlies = 0;
  final terminations = <String, int>{};
  for (final filename in args) {
    for (final line in File(filename).readAsLinesSync()) {
      if (line.trim().isEmpty) continue;
      final row = jsonDecode(line) as Map<String, dynamic>;
      final game = chess.Chess();
      for (final raw in row['moves_uci'] as List) {
        if (game.game_over) {
          throw StateError('Continued terminal app position: ${row["id"]}');
        }
        final uci = raw as String;
        if (!game.move({
          'from': uci.substring(0, 2),
          'to': uci.substring(2, 4),
          if (uci.length == 5) 'promotion': uci.substring(4),
        })) {
          throw StateError('Illegal app move $uci: ${row["id"]}');
        }
        checkedPlies++;
      }
      if (game.fen != row['final_fen']) {
        throw StateError('App FEN mismatch: ${row["id"]}: ${game.fen}');
      }
      if (row['mode'] == 'matches') {
        final expected = game.game_over
            ? (game.in_checkmate
                ? (game.turn == chess.Color.WHITE ? '0-1' : '1-0')
                : '1/2-1/2')
            : '1/2-1/2'; // Explicit study cap, not a natural app result.
        if (expected != row['result']) {
          throw StateError('App result mismatch: ${row["id"]}');
        }
        if (!game.game_over &&
            ((row['moves_uci'] as List).length != 400 ||
                row['termination'] != 'max_plies')) {
          throw StateError('Unlabelled cap: ${row["id"]}');
        }
        final actual = game.in_checkmate
            ? 'checkmate'
            : game.half_moves >= 100
                ? 'fifty_moves_actual'
                : game.in_stalemate
                    ? 'stalemate'
                    : game.insufficient_material
                        ? 'insufficient_material'
                        : game.in_threefold_repetition
                            ? 'threefold_repetition_actual'
                            : 'max_plies';
        if (actual != row['termination']) {
          throw StateError('Termination mismatch: ${row["id"]}: $actual');
        }
        terminations.update(actual, (n) => n + 1, ifAbsent: () => 1);
      }
      checkedGames++;
    }
  }
  stdout.writeln(jsonEncode({
    'passed': true,
    'games_and_openings': checkedGames,
    'legal_plies': checkedPlies,
    'app_chess_package': '0.8.1',
    'terminations': terminations,
  }));
}
