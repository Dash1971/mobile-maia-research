import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';
import 'original-recognition.dart' as vision;
void main(List<String> args) {
 final rows=jsonDecode(File(args[0]).readAsStringSync()) as List;
 const source='1KQRBNPkqrbnp';
 final results=<Map<String,dynamic>>[];
 for (final row in rows) {
  final probs=Float64List(64*13);
  for(var i=0;i<64;i++) {
   final src=(7-i~/8)*8+i%8;
   for(var j=0;j<13;j++) {
    final name=vision.boardSquareClasses[j];
    probs[i*13+j]=(row[src*13+source.indexOf(name=='.'?'1':name)] as num).toDouble();
   }
  }
  final choices=vision.decodeSquares(probs);
  final ranks=<String>[];
  for(var r=0;r<8;r++) {
   var rank='',empty=0;
   for(var f=0;f<8;f++) {
    final piece=vision.boardSquareClasses[choices[r*8+f]];
    if(piece=='.') {empty++;} else {if(empty>0) rank+='$empty';empty=0;rank+=piece;}
   }
   if(empty>0) rank+='$empty';
   ranks.add(rank);
  }
  results.add({'placement':ranks.join('/')});
 }
 File(args[1]).writeAsStringSync(jsonEncode(results));
}
