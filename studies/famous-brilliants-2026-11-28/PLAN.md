# Famous games: analysis plan

Frozen November 28, 2026, before collecting new engine or classifier results.

## Question

Does the proposed Open Brilly Finder integration identify celebrated moves more consistently than Mobile Maia’s existing En Croissant-derived classifier, without merely adding more awards everywhere?

## Fixed sample and references

Eight games: the Opera Game; Byrne–Fischer1956; the Immortal Game; the Evergreen Game; Rotlewi–Rubinstein1907; Levitsky–Marshall1912; Edward Lasker–George Thomas1912; Kasparov–Topalov1999.

The [frozen annotation registry](data/annotation-registry.json) specifies13 published!! landmarks, exact sources, source scope and separately noted!/? markings. The registry is fixed before results. Source scopes include explicit prose and published finishing fragments; it is not a claim to have exhaustively extracted inaccessible embedded boards. Legal move scores will be verified before engine collection; historical date/notation ambiguities remain recorded.

Opera and Fischer were already examined during development. The other six were chosen for their famous sacrifices, not sampled randomly. Model training membership is not audited. This is an exploratory, selected showcase, not a held-out population accuracy estimate.

## Fixed comparison

- Pin actual Preview classifiers and Open Brilly Finder model; do not retrain, tune thresholds or alter app rules after seeing results.
- Use installed Stockfish18, one thread, MultiPV2 and64MiB hash. Clear the session before each game/mode; keep the app’s normal within-game behavior.
- Run every position of every game through the actual Dart StockfishAnalyzer in Fast(depth12/500ms), Balanced(depth14/1000ms) and Thorough(depth16/1500ms). Preserve exact completed snapshots and previous iterations; fail on missing usable evidence.
- Give old and new classifiers the same baseline evaluations. Run their actual provisional classification, bounded annotation-confirmation searches and final confidence policy separately. Record raw/provisional and final labels rather than hiding confidence-related misses.
- Primary comparison: final Fast awards at the13 frozen landmarks. Balanced and Thorough are prespecified sensitivity checks, not opportunities to select the most flattering run.
- Secondary comparisons: per-game total Brilliant awards, all gained/lost/retained awards, awards at source! moves, and awards outside the recorded source marks. Missing human annotations are not negative labels and cannot be counted as false positives.
- Record timing, source/model/engine hashes, all labels and achieved evidence. Classification workers stay off the UI thread. Do not claim Android latency/memory qualification from host tests.

## Reporting rule

Report every game and every frozen landmark, including misses and regressions. Draw diagrams from actual legal positions. Explain why each discussed move matters in original prose; link the annotator rather than copying long commentary.

Call the result an improvement on this sample only if the actual recovery/retention evidence supports it across the prespecified modes and additional awards survive a transparent review. If the evidence is mixed or worse, publish that conclusion and revisit the proposed integration rather than writing a success story. Never equate these awards with exact reproduction of a private commercial classifier or a universal measure of chess beauty.

The feature is a Preview draft aiming for Mobile Maia2.7, not released functionality. No Android builds or LFS downloads. Website publication uses the existing web-only GitHub Pages workflow.
