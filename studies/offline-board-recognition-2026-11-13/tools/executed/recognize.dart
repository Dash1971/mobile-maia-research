import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';
import 'original-recognition.dart' as vision;
void main(List<String> args) {
 final cases=jsonDecode(File(args[1]).readAsStringSync()) as List;
 final output=<Map<String,dynamic>>[];
 for(final row in cases) {
  if(args[0]=='export') {
   final rgba=File(row['rgba']).readAsBytesSync();
   final int w=row['width'],h=row['height'];
   final crop=row['crop'];
   var rect=crop==null ? vision.locateBoard(rgba,w,h) : vision.BoardRect((crop[0] as num).toDouble(),(crop[1] as num).toDouble(),(crop[2] as num).toDouble(),(crop[3] as num).toDouble());
   final rawRect=rect==null ? null : [rect.left,rect.top,rect.width,rect.height];
   if(crop==null && rect!=null) {
    final l=rect.left.clamp(0,w).toDouble(),t=rect.top.clamp(0,h).toDouble();
    final r=rect.right.clamp(0,w).toDouble(),b=rect.bottom.clamp(0,h).toDouble();
    rect=vision.BoardRect(l,t,r-l,b-t);
   }
   final out=<String,dynamic>{...row,'found':rect!=null,'rawRect':rawRect};
   if(rect!=null) {
    out['rect']=[rect.left,rect.top,rect.width,rect.height];
    final tensor=vision.prepareSquares(rgba,w,h,rect);
    File(row['tensor']).writeAsBytesSync(tensor.buffer.asUint8List());
   }
   output.add(out);
  }else{
   final logits=(jsonDecode(File(row['logits']).readAsStringSync()) as List).cast<num>().map((n)=>n.toDouble()).toList();
   final rect=row['rect'] as List;
   final result=vision.recognitionFromLogits(logits,vision.BoardRect(rect[0],rect[1],rect[2],rect[3]));
   output.add({...row,'placement':result.placement,'squares':result.squares,'confidence':result.confidence,'problems':result.problems});
  }
 }
 File(args[2]).writeAsStringSync(jsonEncode(output));
}
