import 'dart:convert';
import 'dart:io';
import 'package:chess/chess.dart' as chess;
import 'package:flutter_test/flutter_test.dart';
import 'package:maia_chess/main.dart';
import 'package:maia_chess/src/brilliant_exchange.dart';
import 'open_brilly_integration_test.dart' as fixture;

String san(String fen, String uci) {
  final p = chess.Chess.fromFEN(fen);
  if (!p.move({'from':uci.substring(0,2),'to':uci.substring(2,4),if(uci.length==5)'promotion':uci[4]})) throw StateError('Illegal $uci');
  return p.getHistory({'verbose':true}).cast<Map<String,dynamic>>().last['san'] as String;
}
Map<String,Object?> line(StockfishLine l) => {'cpWhite':l.evaluation,'mateWhite':l.mate,'pv':l.moves};
void main() {
 test('extract every gained and lost Brilliant from exact production classifiers', () {
  final model=BrilliantExchangeModel.fromJson(fixture.modelJson);
  final native=<Map<String,Object?>>[];
  for(final file in ['stockfish18-fast','stockfish18-balanced-thorough','stockfish-light-fast','stockfish-light-balanced-thorough']) {
   final data=jsonDecode(File('test/fixtures/classification/$file.json').readAsStringSync());
   for(final dynamic run in data['runs']) {
    final pos=(run['positions'] as List).cast<String>(), moves=(run['moves'] as List).cast<String>();
    final scores=<StockfishReview>[];
    for(final dynamic row in run['scores']) {
     final lines=[for(final dynamic l in row['lines']) StockfishLine(evaluation:l['cp'] as int,mate:l['mate'] as int?,moves:(l['moves'] as List).cast<String>())];
     scores.add(StockfishReview(row['cp'] as int,lines.isEmpty?'(none)':lines.first.moves.first,mate:row['mate'] as int?,lines:lines));
    }
    final old={for(final m in MoveClassifier.classify(scores:scores,positions:pos,uciMoves:moves)) m.ply:m.classification};
    final next={for(final m in MoveClassifier.classify(scores:scores,positions:pos,uciMoves:moves,exchangeModelJson:fixture.modelJson)) m.ply:m.classification};
    for(var ply=1;ply<=moves.length;ply++) {

     final decision=MoveClassifier.exchangeDecision(BrilliantExchange(model),pos,moves,ply,scores[ply-1],scores[ply]);
     native.add({'id':'${run['name']}:$ply','game':run['name'],'corpus':file,'engine':data['engine'],'quality':run['quality'],'ply':ply,'uci':moves[ply-1],'san':san(pos[ply-1],moves[ply-1]),'fenBefore':pos[ply-1],'fenAfter':pos[ply],'old':old[ply]?.name,'new':next[ply]?.name,'candidate':decision.candidate,'score':decision.score,'beforeLines':scores[ply-1].lines.take(2).map(line).toList(),'afterLine':scores[ply].lines.isEmpty?null:line(scores[ply].lines.first)});
    }
   }
  }
  final changedIds=native.where((x)=>(x['old']=='brilliant')!=(x['new']=='brilliant')).map((x)=>x['id']).toSet();
  native.removeWhere((x)=>!changedIds.contains(x['id']));
  final labeled=<Map<String,Object?>>[];
  for(final row in fixture.rows) {
   final w=fixture.window(row), cache=<String,int>{};
   final old={for(final m in MoveClassifier.classify(scores:w.scores,positions:w.positions,uciMoves:w.moves,materialCache:cache))m.ply:m.classification};
   final next={for(final m in MoveClassifier.classify(scores:w.scores,positions:w.positions,uciMoves:w.moves,materialCache:cache,exchangeModelJson:fixture.modelJson))m.ply:m.classification};
   if((old[2]==MoveClassification.brilliant)==(next[2]==MoveClassification.brilliant)) continue;
   final decision=MoveClassifier.exchangeDecision(BrilliantExchange(model),w.positions,w.moves,2,w.scores[1],w.scores[2]);
   labeled.add({'id':row['key'],'san':row['san'],'uci':row['uci'],'fenBefore':row['fenBefore'],'fenAfter':row['fenAfter'],'old':old[2]?.name,'new':next[2]?.name,'recordedBrilliant':row['label'],'candidate':decision.candidate,'score':decision.score,'referenceScore':row['score'],'features':{for(final k in ['hang_see','hang_type','rank','cp_loss','wc_loss','net','qs_net6','hang_is_moved'])k:row['features'][k]},'beforeLines':w.scores[1].lines.map(line).toList(),'afterLine':line(w.scores[2].lines.first)});
  }
  expect(native.where((x)=>x['new']=='brilliant'&&x['old']!='brilliant').length,10);
  expect(native.where((x)=>x['old']=='brilliant'&&x['new']!='brilliant').length,6);
  expect(native.map((x)=>x['id']).toSet().length,4);
  expect(labeled.where((x)=>x['new']=='brilliant').length,26);
  expect(labeled.where((x)=>x['old']=='brilliant').length,3);
  expect(labeled.where((x)=>x['new']=='brilliant'&&x['recordedBrilliant']==true).length,24);
  expect(labeled.where((x)=>x['new']=='brilliant'&&x['recordedBrilliant']==false).length,2);
  expect(labeled.where((x)=>x['old']=='brilliant'&&x['recordedBrilliant']==true).length,1);
  expect(labeled.where((x)=>x['old']=='brilliant'&&x['recordedBrilliant']==false).length,2);
  File(const String.fromEnvironment('BRILLY_REVIEW_OUTPUT')).writeAsStringSync(const JsonEncoder.withIndent('  ').convert({'appSource':'04e903b1e4abe635d2168d01b027ecc24f240651','modelSource':'59cab58a8b63387d9775252f03a6875fe451f697','cutoff':model.cutoff,'native':native,'labeled':labeled})+'\n');
 });
}
