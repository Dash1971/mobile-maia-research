# Maia score reliability — evidence and reproduction

[Visual guide](REPORT.md) · [Detailed results and limitations](APPENDIX.md) · [Fixed protocol and pre-inference amendments](PROTOCOL.md)

This small study tests the bundled Maia-3 79M expected-score output at fixed
1600/1600 and 2600/2600 inputs. It measures human-result prediction on one position
per game and self-consistency across every legal move. It does not change the app,
recalibrate the model, estimate playing Elo, or claim that model scores are exact
winning probabilities.

## What is included

- `study.py`: deterministic game/position selection and CPU inference.
- `summarize.py`: metrics, descriptive bootstrap intervals and original charts.
- `build_visuals.py`: the simpler visual guide, drawn from the same recorded
  summary without changing any measurements.
- `audit.py`, `audit.json`: independent numerical checks on recorded outputs.
- `audit_source.py`, `data/source-crosscheck.json`: direct-source checks of
  actual results, ratings, normal termination, prefixes and clock eligibility.
- `data/sample.jsonl`: 725 selected positions, their prior moves/history, public
  game identities, rating/result and clock metadata. No player handles are used.
- `data/predictions.jsonl`: all history-on/off expected scores and loss/draw/win
  model outputs, plus input tensor hashes.
- `data/consistency.jsonl`: parent outcomes, every legal candidate's probability,
  child outcome, terminal override and the complete weighted calculation for
  100 positions at each rating.
- `data/summary.json`: aggregate numbers and uncertainty intervals.
- `data/calibration-bins.csv`, `data/outcome-metrics.csv`,
  `data/consistency-summary.csv`: spreadsheet-readable summaries.
- `data/selection.json`: eligibility/attrition and actual cohort coverage.
- `data/run.json`: model, source, input and executable hashes and runtime versions.
- `data/known-case-sanity.json`: the earlier Rd1 example, isolated from the random
  sample. Eight parent/child/rating/history scores match the earlier reproduction.
- `data/known-case-consistency.json`: retained earlier all-26-move calculation
  for the isolated Rd1 illustration; its weighted sums are checked in
  `data/known-case-calculation-check.json`.
- `figures/`: static PNG and SVG charts.
- `SHA256SUMS`: published file checksums, excluding this checksum file itself.

The protocol was committed before study predictions. The first eligibility
amendment proposed including future time forfeits; the user's explicit correction
superseded it before inference. **All 725 selected games have Normal termination.**
The requested 250-game high-rating target was reduced to all 225 eligible games;
the rating band was not widened. Details remain in the protocol history.

## Source provenance and attribution

Source: [ALLIE 2022 annotated test games](https://huggingface.co/datasets/yimingzhang/allie-data/tree/990f79105b1f08a8fd367fcb10c5e18c69436e30/lichess-2022-blitz-test),
revision `990f79105b1f08a8fd367fcb10c5e18c69436e30`, file
`lichess-2022-blitz-test/2022-test-annotated.jsonl`.

- Download: [pinned annotated file](https://huggingface.co/datasets/yimingzhang/allie-data/resolve/990f79105b1f08a8fd367fcb10c5e18c69436e30/lichess-2022-blitz-test/2022-test-annotated.jsonl).
- Size: 44,727,605 bytes; 18,239 source games.
- SHA-256: `a6014de8ef861b2ee23a84d7ce824e644390577a000350fad06bd995bcddab0d`.

Underlying [Lichess database exports](https://database.lichess.org/) are CC0. The
pinned ALLIE repository supplies no license metadata for its annotations; we do
not invent an annotation license. This study publishes derived selected records
and research outputs with attribution, not the full annotated source file.
Original research code/report text follows this repository's AGPL-3.0-only license;
third-party material retains its own terms.

The [official Maia3-79M model card](https://huggingface.co/UofTCSSLab/Maia3-79M/blob/a107d6ceb7b298cb04ae1da4edffe2939858b894/README.md)
states a January 2023–July 2025 training window. The
[Maia-3 paper, section 4.1](https://openreview.net/pdf?id=2ltBRzEHyd), identifies
ALLIE 2022 as its evaluation source. These games precede the declared training
window, but this is an established benchmark, not a new untouched holdout.
Repeated positions or development exposure cannot be ruled out from dates alone.

Model used: the app's 316,034,244-byte ONNX, SHA-256
`3454b03ae78baa64a87b345fdb1a457265d912caec531039b074f07eda0d8010`.
The [pinned app model reference](https://github.com/Dash1971/maia-chess-android-preview/blob/e1688ddb8e404716961824dfc9e51d992b238a16/assets/models/maia3-79m.onnx)
and [exporter](https://github.com/Dash1971/maia-chess-android-preview/blob/e1688ddb8e404716961824dfc9e51d992b238a16/tool/export_maia3_onnx.py)
identify the artifact. Do not substitute a Git LFS pointer file for model bytes.
The official checkpoint is pinned at model revision
`a107d6ceb7b298cb04ae1da4edffe2939858b894`, SHA-256
`3fc6181d5db789b45a15305732148757ae74efa3e0028e81ba335b462dac45c2`;
the model card declares AGPLv3. Model weights are not included here.

The [official UCI implementation](https://github.com/CSSLab/maia3/blob/1e13597c42d4858b7cfd7cfdae01e297263364b2/maia3/uci.py)
defines loss/draw/win relative to the side to move. The
[official website calculation](https://github.com/CSSLab/maia-platform-frontend/blob/a6e52f5c811ee18863cb2f0e81f2433a5b9905de/src/lib/engine/maia.ts#L272)
uses win plus half draw and converts to White's perspective. This study follows
that definition. Both model ratings are the target rating, not each player's
exact recorded rating. History follows the app's validated eight-board encoder.

## Reproduce

Run from this study directory. Use a temporary environment outside the repository
and supply the verified source/model files from outside the repository. The
recorded run used Python 3.14 and CPU ONNX Runtime; package pins are in
`requirements.txt`. No GPU, Stockfish, Android build or app test suite is required.

```sh
python3 -m venv /tmp/maia-score-reproduction
/tmp/maia-score-reproduction/bin/pip install -r requirements.txt
/tmp/maia-score-reproduction/bin/python study.py select --source /path/to/2022-test-annotated.jsonl
/tmp/maia-score-reproduction/bin/python study.py infer --model /path/to/maia3-79m.onnx
/tmp/maia-score-reproduction/bin/python summarize.py
/tmp/maia-score-reproduction/bin/python build_visuals.py
/tmp/maia-score-reproduction/bin/python audit_source.py --source /path/to/2022-test-annotated.jsonl
/tmp/maia-score-reproduction/bin/python audit.py --source /path/to/2022-test-annotated.jsonl --model /path/to/maia3-79m.onnx
```

Selection and inference overwrite the corresponding data files. To inspect the
published measurements without inference, run only `summarize.py` and `audit.py`. Omitting the audit source/model arguments
checks recorded hashes and calculations; supplying them also verifies the actual
source/model bytes, as done for the published audit.
The source/model hashes are enforced. Minor floating-point differences across
runtime/platform versions may change final digits; they do not justify changing
the sample, thresholds, or interpretation.

5000 bootstrap repetitions operate at game level, with paired resampling for
history and baseline comparisons. The consistency bootstrap preserves its
50/50 source-cohort mix. Calibration bins are fixed before inference; bands under
30 games are marked sparse. Intervals are descriptive and do not account for
unknown repeat-player dependence or all possible benchmark-selection effects.

A game score is 1 for a win, 0.5 for a draw, and 0 for a loss. Squared-error
reduction is a comparison against the same sample's always-50% forecast, not a
percentage of correctly predicted winners. The weighted child forecast is another
model-derived estimate, not ground truth. Histories and positions are fixed before
inference; the known Rd1 example is never pooled into study results.
