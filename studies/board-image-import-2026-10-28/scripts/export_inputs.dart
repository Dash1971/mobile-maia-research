import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';
import 'lib/board_recognizer.dart';

void main(List<String> args) {
  final cases = jsonDecode(File(args[0]).readAsStringSync()) as List;
  final out = Directory(args[1])..createSync(recursive: true);
  final records = <Map<String, dynamic>>[];
  for (final c in cases) {
    final gray = GrayImage.fromRgba(File(c['rgba_path']).readAsBytesSync(), c['width'], c['height']);
    final crop = c['crop'];
    final rect = crop == null ? locateBoardGray(gray) : BoardRect(
        (crop[0] as num).toDouble(), (crop[1] as num).toDouble(),
        (crop[2] as num).toDouble(), (crop[3] as num).toDouble());
    if (rect == null) {
      records.add({'id': c['id'], 'found': false});
      continue;
    }
    final input = Float32List(64 * 32 * 32);
    for (int r = 0; r < 8; r++) {
      for (int col = 0; col < 8; col++) {
        cellInput(gray, rect.left + col * rect.width / 8, rect.top + r * rect.height / 8,
            rect.width / 8, rect.height / 8, input, (r * 8 + col) * 32 * 32);
      }
    }
    final f = File('${out.path}/${c['id']}.f32');
    f.writeAsBytesSync(input.buffer.asUint8List());
    records.add({'id': c['id'], 'found': true, 'input': f.path,
      'rect': [rect.left, rect.top, rect.width, rect.height]});
  }
  File('${out.path}/inputs.json').writeAsStringSync(jsonEncode(records));
}
