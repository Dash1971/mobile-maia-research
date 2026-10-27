import 'dart:convert';
import 'dart:io';
import 'dart:math' as math;
import 'lib/board_recognizer.dart';

Future<void> main(List<String> args) async {
  final cases = jsonDecode(File(args[0]).readAsStringSync()) as List;
  final modelBytes = File(args[1]).readAsBytesSync();
  final output = File(args[2]).openWrite();
  final modelLoad = Stopwatch()..start();
  final recognizer = BoardRecognizer(modelBytes);
  modelLoad.stop();
  stderr.writeln('model load ms: ${modelLoad.elapsedMilliseconds}');
  for (final c in cases) {
    final bytes = File(c['rgba_path']).readAsBytesSync();
    final watch = Stopwatch()..start();
    final row = <String, dynamic>{'id': c['id'], 'mode': args.length > 3 ? args[3] : 'auto'};
    try {
      final crop = row['mode'] == 'crop' && c['crop'] != null
          ? BoardRect((c['crop'][0] as num).toDouble(), (c['crop'][1] as num).toDouble(),
              (c['crop'][2] as num).toDouble(), (c['crop'][3] as num).toDouble())
          : null;
      final r = await recognizer.recognize(bytes, c['width'], c['height'], crop: crop);
      row.addAll({'found': true, 'placement': r.placement,
        'squares': r.squares, 'confidence': r.confidence, 'flipped': r.flipped,
        'rect': [r.rect.left, r.rect.top, r.rect.width, r.rect.height],
        'problems': r.problems,
        'minimum_confidence': r.confidence.reduce(math.min)});
    } on BoardNotFoundException {
      row['found'] = false;
    } catch (e, stack) {
      row['error'] = '$e';
      stderr.writeln('$e\n$stack');
    }
    watch.stop();
    row['elapsed_ms'] = watch.elapsedMicroseconds / 1000.0;
    output.writeln(jsonEncode(row));
    await output.flush();
    stderr.writeln('${c['index']} ${c['id']} found=${row['found']} ms=${row['elapsed_ms']}');
  }
  recognizer.dispose();
  await output.close();
}
