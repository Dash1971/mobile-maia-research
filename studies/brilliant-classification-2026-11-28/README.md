# Brilliant classification comparison — November 28, 2026

[Visual catalog: every gained and lost move](REPORT.md)

This records the exact old/new decisions behind [Preview PR #284](https://github.com/Dash1971/maia-chess-android-preview/pull/284), targeting 2.7. No model is trained or tuned here. No new Stockfish analysis, Android builds, Actions or LFS downloads were run.

| Evidence | Gained Brilliant | Lost Brilliant | Unique changed positions |
| --- | ---: | ---: | ---: |
| Mobile Maia engine fixtures: 821 move snapshots, 17 runs, six games | 10 | 6 | 4 |
| Selected labeled parity subset: 360 cases | 26 | 3 | 29 |

The native catalog includes all 21 available engine/mode snapshots at those four positions, including five unchanged awards. It does not fabricate the three missing Stockfish Light Opera-game runs. Its 16 changed snapshots reconcile with the original comparison. The labeled catalog contains 24 recovered labels, one lost label, two newly added outside-label awards and two removed outside-label awards.

## Pins

- App classifiers: [Preview `04e903b1e4abe635d2168d01b027ecc24f240651`](https://github.com/Dash1971/maia-chess-android-preview/tree/04e903b1e4abe635d2168d01b027ecc24f240651).
- Model/reference: [Open Brilly Finder `59cab58a8b63387d9775252f03a6875fe451f697`](https://github.com/Dash1971/open-brilly-finder/tree/59cab58a8b63387d9775252f03a6875fe451f697).
- Input hashes, FENs, UCI/SAN moves, root lines and model scores: [changed-moves.json](data/changed-moves.json).
- Model cutoff: `0.8193002847777424`. Model weights remain in the app/upstream repository; none are copied here.

## Reproduce

Use an existing Preview checkout at the exact pin and the shared Flutter SDK/package cache. This is host-only extraction; follow that checkout's disk and cleanup instructions. Python generation requires Pillow 12.1.0 and chess 1.11.2 in a disposable test environment, not in the app.

```sh
cd /path/to/pinned-preview
/path/to/shared/flutter/bin/flutter pub get --offline
python3 /path/to/this-study/tools/export_changes.py \
  --app /path/to/pinned-preview \
  --flutter /path/to/shared/flutter/bin/flutter \
  --output /path/to/task-scratch/raw.json
python3 /path/to/this-study/tools/build_review.py \
  --app /path/to/pinned-preview --raw /path/to/task-scratch/raw.json
```

The exporter runs both actual Dart classifiers, not a Python approximation. It asserts the 10/6 and 26/3 totals and the four labeled transition categories. The renderer independently checks all 33 played moves and resulting board positions using python-chess, converts legal PVs to SAN, and builds the catalog and before/after diagrams. The exporter removes its own temporary test file. Clean task-owned Flutter output and test environments afterwards; preserve shared caches and source.

## Interpretation

These are classifier decisions on recorded engine windows, not fresh Android results. The labeled subset is selected and includes development examples; it is not an independent holdout, and a missing Brilliant label is not a new human adjudication. Scores are not probabilities. No conclusion about population accuracy follows from these counts.

The native rows come from Stockfish 18 and Stockfish Light in the app's saved Fast/Balanced/Thorough traces. Sparse upstream windows are labeled separately and do not establish production search-convergence evidence. The app's confirmation and error-grade precedence remain in effect. Later engine output may produce different awards; Android performance/lifecycle qualification remains pending in the draft PR.

The new model's no-candidate sentinel is zero. For 19...Ne2+, the exchange gate fails and the trees are not evaluated; this is distinct from a computed model score of zero.

[Artwork and source notices](THIRD_PARTY.md). Original research tools/docs: AGPL-3.0-only. Third-party game records, labels and artwork retain their existing rights.
