// SPDX-License-Identifier: AGPL-3.0-only
// Run with the pinned app's shared Flutter host-test environment. No Android.
import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:maia_chess/main.dart';
import 'package:maia_chess/src/brilliant_exchange.dart';
import 'package:shared_preferences/shared_preferences.dart';

class StudyEngine implements StockfishEngineHandle {
  StudyEngine(this.process) {
    output = process.stdout
        .transform(utf8.decoder)
        .transform(const LineSplitter())
        .asBroadcastStream();
  }
  final Process process;
  late final Stream<String> output;
  final commands = <String>[];
  int threads = 0;
  int searches = 0;
  @override
  Stream<String> get stdout => output;
  @override
  set stdin(String command) {
    commands.add(command);
    if (command.startsWith('setoption name Threads value '))
      threads = int.parse(command.split(' ').last);
    if (command.startsWith('go ')) {
      if (threads != 1)
        throw StateError('Research batch searched with $threads threads');
      searches++;
    }
    process.stdin.writeln(command);
  }

  @override
  Future<void> dispose() async {
    stdin = 'quit';
    await process.exitCode.timeout(const Duration(seconds: 5));
    await process.stdin.close();
  }
}

Map<String, Object?> lineJson(StockfishLine line) => {
  'cp': line.evaluation,
  'mate': line.mate,
  'moves': line.moves,
};
Map<String, Object?> reviewJson(StockfishReview score) => {
  'cp': score.evaluation,
  'mate': score.mate,
  'bestMove': score.bestMove,
  'lines': score.lines.map(lineJson).toList(),
  'evidence': score.evidence == null
      ? null
      : {
          'quality': score.evidence!.quality?.name,
          'complete': score.evidence!.complete,
          'depth': score.evidence!.depth,
          'nodes': score.evidence!.nodes,
          'timeMs': score.evidence!.timeMs,
          'reset': score.evidence!.reset,
          'previousLines': score.evidence!.previousLines.map(lineJson).toList(),
        },
};
List<Map<String, Object?>> labelsJson(List<ClassifiedMove> labels) => [
  for (final l in labels)
    {
      'ply': l.ply,
      'label': l.classification.name,
      'reliable': l.annotationReliable,
    },
];

Future<({List<ClassifiedMove> labels, Map<String, int> cache})> classify(
  List<StockfishReview> scores,
  List<String> positions,
  List<String> moves,
  String? model, {
  bool reliable = true,
  Map<String, int>? cache,
}) async {
  final job = MoveClassifier.startOffMainIsolate(
    scores: scores,
    positions: positions,
    uciMoves: moves,
    exchangeModelJson: model,
    requireReliableComparisons: reliable,
    materialCache: cache,
  );
  try {
    final labels = await job.result;
    return (labels: labels, cache: job.materialCache);
  } finally {
    await job.terminated;
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  test('fixed famous-game study using actual app analyzer and both classifiers', () async {
    SharedPreferences.setMockInitialValues({});
    final env = Platform.environment;
    final input = jsonDecode(
      File(env['BRILLY_STUDY_INPUT']!).readAsStringSync(),
    ) as Map<String, dynamic>;
    final modelJson = File(
      '${env['BRILLY_APP_ROOT']}/assets/classifiers/mute-exchange-model.json',
    ).readAsStringSync();
    final model = BrilliantExchangeModel.fromJson(modelJson);
    final output = File(env['BRILLY_STUDY_OUTPUT']!);
    final runs = <Map<String, Object?>>[];
    final data = <String, Object?>{
      'schema': 1,
      'appSource': input['appSource'],
      'planCommit': input['planCommit'],
      'modelSource': input['modelSource'],
      'modelSha256': input['modelSha256'],
      'engine': input['engine'],
      'threads': 1,
      'hashMiB': 64,
      'multiPV': 2,
      'cutoff': model.cutoff,
      'runs': runs,
    };
    void checkpoint() {
      final temp = File('${output.path}.tmp');
      temp.writeAsStringSync(jsonEncode(data));
      temp.renameSync(output.path);
    }

    final qualities = GameAnalysisQuality.values.where(
      (q) => input['qualities'] == null || (input['qualities'] as List).contains(q.name),
    ).toList();
    if (env['BRILLY_STUDY_RESUME'] == '1' && output.existsSync()) {
      final previous = jsonDecode(output.readAsStringSync()) as Map<String, dynamic>;
      for (final key in data.keys.where((key) => key != 'runs')) {
        expect(previous[key], data[key], reason: 'Resume provenance: $key');
      }
      final keys = <String>{};
      for (final dynamic run in previous['runs']) {
        final game = (input['games'] as List).singleWhere((g) => g['id'] == run['game']);
        expect(qualities.map((q) => q.name), contains(run['quality']));
        expect((run['scores'] as List).length, (game['positions'] as List).length);
        expect(keys.add('${run['game']}:${run['quality']}'), isTrue);
        runs.add((run as Map).cast<String, Object?>());
      }
      stdout.writeln('RESUME ${runs.length} completed game/mode runs with matching provenance');
    }
    for (final dynamic game in input['games']) {
      final positions = (game['positions'] as List).cast<String>();
      final moves = (game['moves'] as List).cast<String>();
      for (final quality in qualities) {
        if (runs.any((r) => r['game'] == game['id'] && r['quality'] == quality.name)) continue;
        final engines = <StudyEngine>[];
        final analyzer = StockfishAnalyzer.withFactory(() async {
          final engine = StudyEngine(
            await Process.start(env['BRILLY_STOCKFISH']!, []),
          );
          engines.add(engine);
          return engine;
        });
        final watch = Stopwatch()..start();
        try {
          final session = Object(), scope = MaiaInferenceScope();
          final scores = <StockfishReview>[];
          for (var i = 0; i < positions.length; i++) {
            final s = await analyzer.evaluate(
              positions[i],
              scope: scope,
              background: true,
              gameAnalysisQuality: quality,
              analysisSession: session,
            );
            if (s.lines.isNotEmpty) {
              expect(s.evidence?.complete, isTrue);
              expect(s.evidence?.quality, quality);
              expect(s.evaluation, s.lines.first.evaluation);
              expect(s.mate, s.lines.first.mate);
            }
            scores.add(s);
            if (i % 20 == 0)
              stdout.writeln(
                'SEARCH ${game['id']} ${quality.name} $i/${positions.length}',
              );
          }
          final baseMs = watch.elapsedMilliseconds;
          final run = <String, Object?>{
            'game': game['id'],
            'quality': quality.name,
            'baselineMs': baseMs,
            'scores': scores.map(reviewJson).toList(),
          };
          final interesting = <int>{
            for (final dynamic a in game['strictBrilliants']) a['ply'] as int,
            for (final dynamic a in game['otherAnnotations']) a['ply'] as int,
          };
          for (final algorithm in ['old', 'new']) {
            final value = algorithm == 'new' ? modelJson : null;
            final started = watch.elapsedMilliseconds;
            final provisional = await classify(
              scores,
              positions,
              moves,
              value,
              reliable: false,
            );
            final requested = MoveClassifier.confirmationPlies(
              scores: scores,
              positions: positions,
              uciMoves: moves,
              classifiedMoves: provisional.labels,
            );
            final priorSearches = engines.fold<int>(
              0,
              (n, e) => n + e.searches,
            );
            final confirmed = await analyzer.confirmAnnotations(
              quality: quality,
              scores: scores,
              positions: positions,
              uciMoves: moves,
              classifiedMoves: provisional.labels,
              scope: scope,
              isCurrent: () => true,
            );
            final labels = await classify(
              confirmed,
              positions,
              moves,
              value,
              cache: provisional.cache,
            );
            for (var i = 0; i < scores.length; i++) {
              expect(confirmed[i].evaluation, scores[i].evaluation);
              expect(confirmed[i].mate, scores[i].mate);
              expect(
                confirmed[i].lines.map(lineJson).toList(),
                scores[i].lines.map(lineJson).toList(),
              );
            }
            final confirmations = <String, Object?>{};
            for (var i = 0; i < confirmed.length; i++) {
              final c = confirmed[i].annotationConfirmation;
              if (c == null) continue;
              confirmations['${i + 1}'] = {
                'before': reviewJson(c.before),
                'after': reviewJson(c.after),
                if (c.beforePrevious != null)
                  'beforePrevious': reviewJson(c.beforePrevious!),
              };
            }
            run[algorithm] = {
              'provisional': labelsJson(provisional.labels),
              'final': labelsJson(labels.labels),
              'confirmationRequested': requested,
              'confirmationSearches':
                  engines.fold<int>(0, (n, e) => n + e.searches) -
                  priorSearches,
              'confirmations': confirmations,
              'classificationAndConfirmationMs':
                  watch.elapsedMilliseconds - started,
            };
            interesting.addAll(
              provisional.labels
                  .where(
                    (l) => l.classification == MoveClassification.brilliant,
                  )
                  .map((l) => l.ply),
            );
            interesting.addAll(
              labels.labels
                  .where(
                    (l) => l.classification == MoveClassification.brilliant,
                  )
                  .map((l) => l.ply),
            );
          }
          final exchange = BrilliantExchange(model);
          run['modelDecisions'] = {
            for (final ply in (interesting.toList()..sort()))
              '$ply': (() {
                final d = MoveClassifier.exchangeDecision(
                  exchange,
                  positions,
                  moves,
                  ply,
                  scores[ply - 1],
                  scores[ply],
                );
                return {
                  'candidate': d.candidate,
                  'score': d.score,
                  'brilliant': d.brilliant,
                };
              })(),
          };
          run['totalMs'] = watch.elapsedMilliseconds;
          run['searchCount'] = engines.fold<int>(0, (n, e) => n + e.searches);
          runs.add(run);
          checkpoint();
          stdout.writeln(
            'DONE ${game['id']} ${quality.name} old=${((run['old'] as Map)['final'] as List).where((l) => l['label'] == 'brilliant').map((l) => l['ply']).toList()} new=${((run['new'] as Map)['final'] as List).where((l) => l['label'] == 'brilliant').map((l) => l['ply']).toList()} total=${watch.elapsedMilliseconds}ms',
          );
        } finally {
          await analyzer.close();
        }
      }
    }
    expect(runs, hasLength((input['games'] as List).length * qualities.length));
  }, timeout: const Timeout(Duration(minutes: 120)));
}
