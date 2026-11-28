# Famous-game Brilliant study

[Read the visual report](REPORT.md) · [Frozen plan](PLAN.md) · [Game scores](data/games.pgn)

Nine famous games, 492 mainline plies from the published scores, fourteen published `!!` landmarks. Every
position was freshly analyzed in all three Mobile Maia modes: **27 runs and
1,503 baseline positions**. Both actual Dart classifiers received the same
baseline Stockfish output, then used their normal independent confirmation
checks and final confidence policy.

| Mode | Previous landmarks | Open Brilly Finder landmarks | Previous total awards | New total awards |
| --- | ---: | ---: | ---: | ---: |
| Fast — primary | 9/14 | 10/14 | 19 | 20 |
| Balanced | 8/14 | 10/14 | 16 | 19 |
| Thorough | 9/14 | 11/14 | 19 | 20 |

**A modest gain, with an unresolved regression.** The new classifier recovers
the Immortal Game's 22.Qf6+ and Marshall's 23...Qg3 in every mode, but loses the
Evergreen Game's 20.Rxe7+ in every mode. It does not warrant an unqualified
replacement sign-off. Open Brilly Finder remains a draft aiming for Mobile
Maia 2.7; the regression and wider quality checks need review before promotion.

## Provenance

- App: Preview [`096591bd8d42759e5a3f3a288d56d7c93245d6d1`](https://github.com/Dash1971/maia-chess-android-preview/tree/096591bd8d42759e5a3f3a288d56d7c93245d6d1), proposed integration in [#284](https://github.com/Dash1971/maia-chess-android-preview/pull/284).
- Pre-analysis plan/registry/runner: commit `52065e0c57b788875687f41ace29cb252c92b242`. No model or threshold changes were made after seeing results.
- Open Brilly Finder: revision `59cab58a8b63387d9775252f03a6875fe451f697`; model SHA-256 `992a792a646b11e612486c4fe26796fc38ee47f395f2220b00d26db65ba1e27d`; fixed cutoff `0.8193002847777424`. No model weights are copied here.
- Installed Homebrew Stockfish 18, macOS ARM64. Binary 113,875,192 bytes; SHA-256 `ae4c93fa9676ca7750d0714342fd8a5b1d018000fc6e0f6cedf112067b5ef374`. No engine binary is distributed.
- One search thread, 64 MiB hash, MultiPV2, fresh engine/session per game/mode. Fast depth 12/500 ms; Balanced depth 14/1000 ms; Thorough depth 16/1500 ms. Achieved depths, nodes and times are recorded; time caps can change results across hosts.

The native runner uses `StockfishAnalyzer.evaluate`, `confirmationPlies`,
`confirmAnnotations`, and both actual `MoveClassifier` paths from the pinned
app. It does not replace them with a research approximation. It asserts that
confirmation never changes baseline graph scores/PVs and searches use one
thread. Worker parsing and feature extraction remain off the UI isolate.

## Data map

- [Annotation registry](data/annotation-registry.json): fixed landmarks, ordinary/dubious marks, source scopes and historical caveats.
- [Legal games](data/games.json) and [fact-only PGN](data/games.pgn): all moves/positions in the published scores, without copied source commentary or variations.
- [Source receipts](data/game-score-sources.json) and [access/normalization record](data/annotation-access-receipt.json): URLs, download hashes where available, and disclosed source typos/access limits. The receipt's original registry hash identifies the contributing source collection; the combined nine-game registry is fixed in the plan commit above.
- [Full engine evidence](data/engine-runs.json): completed current/prior snapshots, all provisional/final labels, independent confirmations and timing.
- [Summary](data/summary.json) and [viewer dataset](web/results.json): derived counts and every awarded/source-listed review position.
- [Editorial conclusions](data/editorial.json): interpretation kept separate from measurements.
- `figures/`: actual before/after boards for every frozen landmark, plus an Opera hero. [Artwork notices](THIRD_PARTY.md).

Sources are human judgments, not objective binary truth. Source scopes include
visible prose and finishing fragments; absent marks are not negative labels.
Opera/Fischer were already development examples, and training membership was
not audited. Short–Timman is a prespecified quiet-brilliance stress case. These
selected games establish neither a population accuracy nor a false-positive
rate. Extra awards remain visible; source! becoming model!! is described as a
generous promotion. The model score is not a probability.

## Shared search-evidence diagnostic

A post-run inspection also found Opera15.Bxd7+ graded Blunder in Fast and
Mistake in Balanced by **both** classifiers; Thorough leaves it unmarked.
Balanced recommends Bxd7+ before the move (+6.39), then evaluates the resulting
position at +3.10. Thorough gives +8.32/+8.47. This is inconsistent shallow
search evidence, separate from the proposed Brilliant model. The viewer includes
this post-run diagnostic without adding it to the fourteen frozen landmarks.
Non-Brilliant grade accuracy is not validated by this study.

## Reproduce

Use an existing Preview checkout at the app pin above, its shared Flutter SDK,
and a Stockfish 18 executable. Follow that checkout's disk and cleanup rules.
Preparing packages from an existing cache uses `flutter pub get --offline`.
No Android build, Gradle or LFS materialization is needed. A fresh source
checkout should use `GIT_LFS_SKIP_SMUDGE=1`; the small classifier JSON is an
ordinary Git asset. Python tools require `chess==1.11.2` and `Pillow==12.1.0`
in one disposable environment, not in the app.

```sh
python tools/run_study.py --app /path/to/pinned-preview \
  --flutter /path/to/shared/flutter/bin/flutter \
  --stockfish /path/to/stockfish18 --output /path/to/task-scratch/engine-runs.json
python tools/summarize.py --runs /path/to/task-scratch/engine-runs.json
python tools/draw_figures.py --help
python tools/build_article.py
python tools/check_study.py
```

The runner does not download tools/models or edit application source. It creates
one temporary input beside the requested output and runs the external Dart host
test. Follow the original cleanup procedure for task-owned Flutter output and
the disposable environment afterwards. Preserve the shared SDK, caches and
other work. No APKs, environments, SDK copies or private local paths belong in
this repository. The website has its own web-only publication workflow and
does not publish this draft Android feature.

Fresh time-limited analysis need not be byte-identical on another host. The
paired classifiers must still share exactly the same baseline evidence. Keep
the original recorded output when rerunning; do not overwrite it merely to
obtain a more favorable table.
