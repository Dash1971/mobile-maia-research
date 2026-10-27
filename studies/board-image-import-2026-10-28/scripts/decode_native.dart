import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';
import 'lib/board_recognizer.dart';

void main(List<String> args) {
  final rows = jsonDecode(File(args[0]).readAsStringSync()) as List;
  final reference = <String, dynamic>{};
  for (final line in File(args[1]).readAsLinesSync()) {
    final r = jsonDecode(line);
    reference[r['id']] = r;
  }
  final checks = <Map<String, dynamic>>[];
  for (final row in rows) {
    final probs = Float64List.fromList((row['probs'] as List).cast<num>().map((n) => n.toDouble()).toList());
    final choice = decodeSquares(probs);
    final squares = [for (final c in choice) boardSquareClasses[c]];
    final r = BoardRecognition(rect: const BoardRect(0, 0, 8, 8), squares: squares,
        confidence: [for (int i=0; i<64; i++) probs[13*i+choice[i]]], flipped: false);
    final result = looksFlipped(squares) ? r.rotated() : r;
    checks.add({'id': row['id'], 'native_placement': result.placement,
      'matches_dart_placement': result.placement == reference[row['id']]['placement'],
      'max_selected_probability_difference': row['max_selected_probability_difference']});
  }
  stdout.writeln(jsonEncode(checks));
  if (checks.any((r) => r['matches_dart_placement'] != true)) exitCode = 1;
}
