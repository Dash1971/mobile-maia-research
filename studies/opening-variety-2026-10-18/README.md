# Opening variety and Top-P 0.95

This study compares the current 1.0/1.0 policy with 1.0/0.95, with and without
the first-five-moves opening override. It tracks
[Preview issue #155](https://github.com/Dash1971/maia-chess-android-preview/issues/155).
The [protocol](PROTOCOL.md) was committed before the main runs in
[`5b0133f`](https://github.com/Dash1971/mobile-maia-research/commit/5b0133f).
The [pre-diagnostic addendum](DIAGNOSTIC_ADDENDUM.md) spreads the quality
positions across moves 7, 13 and 21; it was committed before diagnostic runs or
match-result analysis, without changing the match/opening comparisons.

## Evidence and code

- `core.py`: current-board encoder, model hash checks, effective phase,
  legal-only inclusive nucleus sampling, and actual app draw rules.
- `run.py`: fixed 3,000-game match design and 5,400 matched opening rollouts.
- `analyze.py`: PGN reconstruction, game integrity, paired-cluster intervals,
  prospective-claim sensitivity and opening-family statistics.
- `quality.py`: fixed-budget evaluation of every legal move on 180
  deterministically selected positions; engine hash checked before execution.
- `verify_policy.py`: official-reference logits and encoder/distribution/
  fixed-draw selection checks using the pinned application code in Dart.
- `verify_dart_games.dart`: independent replay in the app's chess library.
- `verify_cached.py`: independent cached W/D/L, probability, diagnostic and
  opening-count checks, without neural-network inference.
- `source/`: public app code and lockfile pinned to Preview
  `3702f6f197135dbac9ae38a9aa9720e15c603e5c`.
- `environment.json`: frozen Python dependencies and Stockfish identity/hash.
  The diagnostic uses **Stockfish 18**, not the app's bundled Stockfish version.
- `data/`: durable JSONL match/rollout shards and per-shard receipts, opening
  labels, selected diagnostic inputs and per-move evaluations.
- `verification/`: policy parity, independent app replay and cached audit.

The model is the original 316,034,244-byte ONNX export with SHA-256
`3454b03ae78baa64a87b345fdb1a457265d912caec531039b074f07eda0d8010`.
Weights are not duplicated in this repository. Obtain them from the pinned
[application model](https://github.com/Dash1971/maia-chess-android-preview/blob/3702f6f197135dbac9ae38a9aa9720e15c603e5c/assets/models/maia3-79m.onnx)
using Git LFS. `core.py` rejects a different model hash.

## Recompute from recorded data

Use a disposable checkout or copy, keeping the original recorded files intact.
With Python 3.12.13:

```sh
python3.12 -m venv /tmp/maia-opening-study-venv
/tmp/maia-opening-study-venv/bin/python -m pip install -r requirements.lock
/tmp/maia-opening-study-venv/bin/python analyze.py
/tmp/maia-opening-study-venv/bin/python verify_cached.py
```

These commands recompute summaries and audit cached evidence. They require no
model weights or engine search. The full requirements include ONNX Runtime
because the shared modules import its types; the cached commands never create
an inference session. Summary regeneration is deterministic for the pinned
dependencies and bootstrap seeds.

`quality.py` also exposes `summarize(rows)` for recomputing the quality summary
from `data/quality.jsonl` without opening Stockfish or loading Maia.

## Repeat inference and matches

Use a separate scratch copy of the repository. Preserve the recorded `data/`
and `manifest.json` elsewhere, then start with an empty `data/` directory and
no manifest in that copy. Keep the source and protocol unchanged. The runner
records environment/source hashes and refuses to resume against a mismatched
manifest. Model files stay outside the study directory.

```sh
python run.py --model /path/to/maia3-79m.onnx --workers 6
python quality.py --model /path/to/maia3-79m.onnx --stockfish /path/to/stockfish-18 --workers 2
python analyze.py
python verify_cached.py
```

Both model Elo inputs equal the tested rating; history is off. Model inference
uses one CPU thread per worker. Parallel scheduling changes elapsed time and
cache-hit counts, but each game owns an explicitly recorded random stream.
Exact-match reproduction requires the pinned CPU arithmetic and environment;
other providers or library versions may change close numerical choices and
subsequent trajectories. Do not pool such runs silently with these measurements.

The quality runner requires the exact Stockfish binary hash in
`environment.json`. A rebuild on another platform is a new diagnostic
replication, not a byte-identical rerun. It clears engine search state before
each child position and records the actual nodes, depth and mate scores.
Stockfish 18's [Clear Hash handler calls `search_clear`, clearing the hash and
thread search state](https://github.com/official-stockfish/Stockfish/blob/sf_18/src/engine.cpp).
Use `--rating 1600` to evaluate that completed rating subset while other matches
continue; the full diagnostic command resumes the remaining fixed cases.

## Independent Dart checks

Use the pinned app dependency `chess` 0.8.1, whose source hashes are recorded in
`verification/dart-chess-source-hashes.json`. Supply the package configuration
from a checkout of the pinned application with dependencies resolved:

```sh
python verify_policy.py --model /path/to/maia3-79m.onnx --dart /path/to/dart --packages /path/to/app/.dart_tool/package_config.json
dart --packages=/path/to/app/.dart_tool/package_config.json verify_dart_games.dart data/matches-*.jsonl data/openings-*.jsonl
```

The generated sampler helper includes the pinned Dart encoder, legal-move
sampler and opening-phase class. It uses a fixed uniform draw to compare
distributions and selections; Python's seeded RNG algorithm does not pretend
to reproduce Dart's seeded random-number generator.

## Attribution and scope

Encoder/indexing and app-outcome research code build on the earlier
[sampling study](../maia3-sampling/README.md); its data and measured scripts
remain unmodified. Opening labels reuse that study's pinned Lichess CC0 opening
table. The report records the table checksum and classification limits.

This is independent Mobile Maia research, not an official Maia-team study or
a calibrated estimate of human Elo. It does not change application defaults,
model weights, saved games, or releases. Any default change requires a
separate application change and review.
