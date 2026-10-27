# Screenshot and chess-diagram import: pinned MIT model accuracy

28 October 2026 · Independent Mobile Maia experiment for [Preview #179](https://github.com/Dash1971/maia-chess-android-preview/issues/179)

The 0.84 MB MIT model is a useful candidate for **assisted import with correction**, but this experiment does not support treating it as reliable automatic import for arbitrary chess diagrams. Clear screenshots often worked. Book fonts, arrows and ambiguous board selection caused important failures. The earlier licensing recommendation is separate from this accuracy assessment.

## What was tested

The exact `board_squares.onnx` from CrispChess revision `0d01798daf9661076675f8505b4cc6995a6529da`:

- 835,655 bytes; SHA-256 `2408717e2e0e2ed438e2f9f89f85c2e544326cef34a0c91b95168bd17336df47`.
- [Explicit MIT notice for these weights](https://github.com/CrispStrobe/CrispChess/blob/0d01798daf9661076675f8505b4cc6995a6529da/NOTICE.md#board-scanning-model).
- Unmodified [board detection, preprocessing, decoder and orientation heuristic](https://github.com/CrispStrobe/CrispChess/blob/0d01798daf9661076675f8505b4cc6995a6529da/lib/vision/board_recognizer.dart), including the upstream postprocessing that discourages back-rank pawns and duplicate kings. There was no retraining or threshold tuning.
- Primary inference used the source-pinned Dart interpreter. A separate native ONNX Runtime **1.24.3 CPU** cross-check covered 16 varied inputs, including the Mobile Maia arrow failure: **16/16 decoded placements matched**. Maximum difference in selected-square probability was `2.588350429599817e-06` across 1,024 compared square outputs. This validates the cross-check cases, not numerical parity on every possible input.

The run processed **190 input files**, representing **181 distinct file hashes**: 178 distinct positive images and three distinct negative/occluded inputs. Seven positive images are the model author's synthetic regression fixtures, reported separately. Nine identical files occur across the external collections; the manifest preserves those rows for provenance, and aggregate external summaries deduplicate them.

Sources were selected before viewing inference results: the eight labeled Fenshot screenshot examples and its no-board example; all 126 `resources/fen_images` and 41 labeled `real_use_cases_chess` images from the pinned diagram repository; all seven upstream sanity fixtures. Five published Mobile Maia screenshots and two modal-obscured screenshots were added to examine actual app inputs. Mobile Maia screenshot labels were transcribed from the visible position before running recognition on them.

## Main observed results

“Completely correct” means **all 64 squares**, not merely the presence of both kings or a high average confidence. Screenshot rows below match the canonical labeled orientation without a manual flip. The book collection does not specify orientation uniformly, so its score accepts a 180° flip; in this run the 36 exact book results also matched without an extra flip.

| Input group | Completely correct boards | Correct squares | Observed limitations |
|---|---:|---:|---|
| Actual Mobile Maia screenshots | **1/5 (20.0%)** | **316/320 (98.8%)** | One underlying position across five UI variants; all four arrowed analysis views gained one false piece. |
| Independent Fenshot screenshot/diagram examples | **6/8 (75.0%)** | **473/512 (92.4%)** | Wrong board selected in one composite; unusual Horsey style misread in another. Five distinct positions, with the Italian opening repeated across styles. |
| Regular cropped Lichess boards from the external collection | **10/10 (100%)** | **640/640 (100%)** | Small convenience set; seven additional deliberately impossible piece grids are separate stress cases. |
| Book/scanned diagrams, six source groups | **36/109 (33.0%)** | **6,771/6,976 (97.1%)** | 104 distinct labeled placements; results vary sharply by print/font style. |

The model's own seven synthetic regression fixtures were **7/7 exact**. The single external no-board image and both modal-obscured Mobile Maia screenshots were rejected, **3/3**. Three negative cases do not establish a general false-positive rate.

The book breakdown shows the generalization gap:

| Diagram source group | Exact boards | Square accuracy |
|---|---:|---:|
| `1001` | 5/7 | 99.6% |
| `b-and-w-pdf` | 5/15 | 98.9% |
| `chess-puzzle-book` | 9/28 | 98.1% |
| `combinations1a` | 17/36 | 99.1% |
| `critical-moments` | 0/6 | 89.1% |
| `imagination` | 0/17 | 91.2% |

Of the 109 book diagrams, 42 needed exactly one square corrected. Thus **78/109 (71.6%)** were either correct or within one correction; the remaining 31 needed between two and nine corrections. The largest recorded confusion was white pawn → white bishop, occurring 66 times. These statistics describe the labeled convenience corpus, not all books or a probability for a future user's image.

The additional 41 mixed real-use inputs, including full pages, multi-board composites, photographed screens, unusual notation and one impossible piece grid, produced 40 detections and 15 exact placements allowing a flip (14 without). This deliberately mixed collection is a secondary stress diagnostic, not a clean in-scope accuracy estimate. Full per-case results and groups are retained in the evidence.

## Concrete failures and crop diagnostics

**Analysis arrows can become pieces.** The [Mobile Maia analysis screenshot](https://raw.githubusercontent.com/Dash1971/maia-chess-android/0957d87d866ca42e9782151e2671e022e51f76d8/docs/screenshots/20261027_v1_stable_2_5_analysis_score.png) shows the position after `1. e4 e5 2. Nf3`. Recognition introduced a white queen on empty **c6**, where a blue move arrow crosses the board. The same error occurred in its light, dark and black appearance variants, with false-queen confidence approximately 81–82%. The [editor screenshot of that placement](https://raw.githubusercontent.com/Dash1971/maia-chess-android/0957d87d866ca42e9782151e2671e022e51f76d8/docs/screenshots/20261027_v1_stable_2_5_editor.png), without those arrows, was exact. This is a paired diagnostic, not a controlled proof that every difference between the two screens has been isolated.

**Board selection needs user control.** In Fenshot's `whole-screen-two-boards.png`, automatic detection selected the large empty result board instead of the smaller intended board. Manually framing the intended board with rectangle `[17, 128, 340, 340]` recovered the exact placement, improving that one case from 33/64 to 64/64 correct squares. This makes the independent screenshot set 7/8 exact *after that one manual crop*, not 7/8 automatically.

**Cropping alone does not solve the book problem.** As a diagnostic, each of the 109 already framed book images was supplied using its complete image bounds as an explicit crop. The result was **33/109 exact**, versus 36/109 automatically; square accuracy was 6,785/6,976 (97.3%). Full-image bounds are not independently annotated perfect square boundaries, so this is not a classifier-only oracle benchmark. It does show that bypassing automatic selection in that simple way did not rescue most print failures.

**Confidence and basic legality are insufficient safeguards.** Of 205 erroneous book squares, 39 had selected-class confidence at least 90%. The false queen in Mobile Maia had no upstream `problems` flag and exceeded the upstream 60% uncertainty threshold. Users must review the placement; highlighting only low-confidence squares would miss some errors. The wrong-board and Horsey examples did trigger basic placement warnings, which are useful but do not replace review.

## Implication for #179

Proceed only as an **assistive prototype**, with a board-selection/crop control, orientation control, editable placement and explicit confirmation before handing the result to analysis or play. Keep the agreed bundled offline model and image-picker scope. Native ONNX compatibility appears practical from the desktop cross-check; Android integration and device performance remain untested.

Before calling broad screenshot/diagram import ready, improve and remeasure overlay handling, print/font generalization and wrong-board selection. A larger fresh set of clear in-scope screenshots and diagrams should be reserved from any tuning. Published baseline inputs must not become the sole evidence after training against their failures. The findings do not justify adding general physical-board photo support.

## Limits and provenance

- These are actual measurements, not the author's claimed training/test accuracy. They are not a random sample of screenshots or books, and repeated positions/styles are not independent observations.
- The source filenames/manifests provide the external placement labels. They were structurally checked and duplicate-image labels checked for consistency, but every external square was not independently relabeled. Mobile Maia's five readable screenshots share one manually checked position.
- The external diagram collection is already referenced by CrispChess's own real-evaluation harness. It is an external regression corpus, **not a blind holdout**, even though the documented model training uses synthetic renders.
- Seven external cropped Lichess inputs deliberately contain multiple kings and/or back-rank pawns. Their poor results are reported as stress cases rather than used to describe normal screenshot quality. The mixed real-use group includes another multiple-king input and challenging captures beyond the proposed clear-image scope.
- Only piece placement was scored. Side to move, castling rights, en-passant rights and move counters cannot be recovered reliably from one diagram.
- This was a macOS ARM64 desktop run, not an Android build, phone benchmark, APK-size measurement or end-to-end Mobile Maia feature test. Single-pass JIT timings are retained as diagnostics and should not be used as mobile latency estimates.
- No model or third-party source image is redistributed with this study. Immutable URLs, image hashes, labels, source pins, outputs and reproduction code are provided in the [reproduction guide](README.md).
