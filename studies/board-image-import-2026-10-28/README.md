# Board-image import evidence and reproduction

[Report](REPORT.md) · [Input manifest](manifest.json) · [Model/code pins](pins.json) · [Per-image scores](evidence/results.csv) · [Errors](evidence/errors.json) · [Native parity checks](evidence/native-parity.json)

The study measures the pinned MIT model recommended for [Preview #179](https://github.com/Dash1971/maia-chess-android-preview/issues/179). It changes no application behavior and does not constitute release qualification.

## Sources and rights

- [CrispChess model, recognition code and notices](https://github.com/CrispStrobe/CrispChess/tree/0d01798daf9661076675f8505b4cc6995a6529da), MIT for the selected model and code; [training recipe and source attributions](https://github.com/CrispStrobe/CrispChess/blob/0d01798daf9661076675f8505b4cc6995a6529da/tool/board_vision/README.md).
- [Fenshot fixtures and their manifest](https://github.com/scoriiu/fenshot/tree/e2506a3964c0c70708583beee96a1e414361f529/packages/fenshot/tests/fixtures). The project is MIT; screenshots depict third-party sites and content. Evaluation does not establish a licence to bundle their images as application assets.
- [External diagram collection](https://github.com/tsoj/Chess_diagram_to_FEN/tree/3d751125357ebd47b91f6a8168e0b8d513fe7aae/resources): use the exact paths and hashes in `manifest.json`. The repository is MIT, but book/source-image rights must not be inferred solely from its code licence. Images are not redistributed here or used to train this experiment.
- [Published Mobile Maia screenshots](https://github.com/Dash1971/maia-chess-android/tree/0957d87d866ca42e9782151e2671e022e51f76d8/docs/screenshots). Readable labels were transcribed before inference; modal-obscured screens are rejection probes.

## Reproduce

Use Python 3.12 with the packages in `scripts/requirements.txt`, Dart 3.13.7, and network access for immutable source/model/image retrieval and the pinned Dart dependencies. Keep a virtual environment and all downloaded material in task-owned scratch. Budget less than 1 GiB for this experiment plus the workspace's required free-space reserve; no Flutter/Android build is needed.

```sh
python scripts/reproduce.py --work-dir /path/to/task-owned-scratch --dart /path/to/dart --parity
```

Run this from the study directory, or use an absolute path to the script. `--parity` requires native ONNX Runtime 1.24.3; omitting it still runs the complete Dart pipeline and crop diagnostics. Downloads are hash checked; the recognizer remains unmodified. The runner uses the committed Dart lockfile and downloads its MIT source licence alongside the fetched recognizer. Dependencies and source files are copied/fetched into scratch, not into the publication.

For a quick check of ordinary import, the arrow failure, wrong-board cropping and one diagram:

```sh
python scripts/reproduce.py --work-dir /path/to/task-owned-scratch --dart /path/to/dart --ids maia_analysis_score,maia_editor,fenshot_whole-screen-two-boards,tsoj_017,upstream_screen_chessnut --parity
```

The five-case reproduction command was run successfully against the publication scripts. The original full run processed all 190 rows, followed by 109 book-crop cases, one manually selected board crop and the 16-case native parity check. Full output files are retained below; the five-case smoke run does not replace those full-run observations.

Collect compact JSON/CSV outputs, then remove only the task-owned scratch, including downloaded models, RGBA buffers, dependency cache and temporary virtual environment. Do not put model weights or source images into this repository. Cleanup of the original experiment is recorded in `evidence/cleanup.json`.

## Evidence interpretation

- `evidence/results-all.jsonl`: 190 primary outputs in manifest order; all-square confidence and rectangles are retained. `found` means a grid was returned, not that a placement was correct.
- `evidence/results.csv`: strict and 180°-flip-tolerant correct-square counts for each positive image. Missing scores on rejection probes are intentional.
- `evidence/errors.json`: misread squares, expected/recognized classes and confidence, aligned to the better of the two orientations.
- `evidence/results-crop.jsonl`: the single manually framed two-board screenshot; selected rectangle is documented in the report and reproduction script.
- `evidence/results-book-crop.jsonl`: complete-image-bounds crop diagnostic on all 109 book inputs.
- `evidence/summary.json`: original per-source summaries plus byte-deduplicated external totals. `square_accuracy_found` excludes undetected boards; `all_squares` preserves the denominator for all positive inputs. The mixed total includes deliberately impossible piece grids, so it is not a product accuracy estimate.
- `evidence/native-parity.json`: 16 decoded-placement comparisons with ONNX Runtime 1.24.3 CPU. All matched; selected-probability deltas are recorded per input.

The published metadata contains no local input paths. Runtime-generated `*.local.json` files contain paths inside the chosen scratch and are not publication artifacts. Original study/reproduction code follows this repository's AGPL-3.0-only licence; upstream code, models and images retain their respective terms.
