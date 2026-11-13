# Offline board recognition — evidence and reproduction

[Visual report and decision](REPORT.md)

We found no sufficiently reliable, open, lightweight recognition model for
shipping in Mobile Maia. Camera/image import is shelved. The study records
improvements as well as failures, without treating common-crop classification
as complete camera-scanner accuracy.

## Verify the recorded results

From this study directory, using Python 3's standard library:

```sh
python3 tools/verify_results.py
git diff --exit-code -- data/metrics.json data/per-photo.csv
```

The verifier expands every recorded FEN, recomputes each square disagreement,
checks error coordinates, verifies sample/unique-position counts, and rebuilds
both aggregate and per-photo results. It does not download models, rerun
inference or independently validate the original manual transcription.

## Regenerate the figures

Use a disposable environment outside source with `requirements-figures.txt`, then:

```sh
python3 tools/verify_results.py
MPLCONFIGDIR=/tmp/mobile-maia-recognition-matplotlib python3 tools/make_figures.py
```

The figures use the recorded results. Model-size comparison uses original file
bytes and the existing Maia model's LFS metadata, not downloaded Maia weights.
PNG figures render directly in GitHub; SVG equivalents remain available for export.

## Inference provenance

The app source under investigation was Preview commit
`f4dcc31fdef0bc4b33cc30639bb4db39393930d8`. The current model was the 835,655-byte
CrispChess model with SHA-256
`2408717e2e0e2ed438e2f9f89f85c2e544326cef34a0c91b95168bd17336df47`.

`data/source-pins.json` identifies the actual candidate files, original download
locations and hashes. Fenshot and Acuity were ordinary pinned Git files;
Fenify was an original GitHub release asset; only the chess position-model entry
was retrieved from the larger tsoj release ZIP using HTTP byte ranges. None of
these candidate downloads used Git LFS. The Tsoj checksum identifies the
extracted model, not a claimed verification of the entire release ZIP.

The private normalized inputs were 960 × 1280 lossless RGBA snapshots of the
supplied photos. Original files that had been moved remained available through
those exact retained pixel snapshots. Orientation corrections, common crop
quads and frame hashes are recorded. No board was flipped after inference merely
to obtain a better score. The first two inputs were development examples; the
additional ten photos contain eight unique positions and were assessed after
the preprocessing policy was frozen.

`tools/geometry.py` and `tools/preprocess.py` retain the frozen preprocessing
prototype. `tools/executed/` retains the inference harnesses and the Fenshot
preprocessing source used in the study, with machine-specific paths replaced by
portable labels. These are **source snapshots**, not a turnkey public benchmark:
the private RGBA inputs/manifests and downloaded model/source directories have
not been published. Refer to the pinned upstream projects for the remaining
training/model source. Do not run a model-fetching snapshot if downloads are
unwanted; the standard-library verifier above never fetches anything.

For a deliberate inference reconstruction, supply manifests containing
`id`, `expected`, `width`, `height`, and `rgba` (path to contiguous raw RGBA bytes)
in the harness directory; the common frames are 512 × 512. `test_fenshot.mjs`
uses `cases.json` for full photos or `frames.json` with `--frames`, the original
Fenshot model at `fenshot/chess-tiles-v2.onnx`, and a Python environment at
`runtime/bin/python`. The other snapshots document the exact per-model tensor
preparation/decoding. Replace `MODEL_DIRECTORY` with a deliberately supplied
model directory and place the pinned upstream sources where the scripts expect
them. Runtime versions are in `data/runtime-versions.json`. Tsoj's constructor
was changed only to avoid redundant ImageNet initialization downloads; strict
checkpoint loading matched all model keys.

Complete fresh inference is not publicly reproducible from this bundle alone
because the private input photos are omitted. The recorded scoring and figures
are reproducible without them. No model weights, full book pages, phone photos,
UI mockups, environments, credentials or private workstation paths are published.

## Attribution

Original Mobile Maia analysis, figures and verification code are under the
repository's AGPL-3.0-only licence. Fenshot preprocessing and the CrispChess
adaptation retain their MIT notices in `licenses/`; upstream licence copies for
the other tested projects are retained for provenance. Model grants remain an
independent distribution question as described in the report. No weights are
relicensed or redistributed by this publication.
