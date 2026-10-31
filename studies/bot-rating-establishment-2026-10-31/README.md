# Established Maia bot ratings — evidence and reproduction

[Read the report](REPORT.md). The same 250 Mute Chess bots completed 826 additional
native rated games and finished nonprovisional in both Blitz and Rapid. Their
Lichess-derived priors and earned histories were retained. A fixed V2 prediction
freeze followed 349 training games and preceded 477 new test games. Frozen V2
average error against final native test labels was about 116 points per speed;
the 100-point target was not met. Native establishment and predictor accuracy
are different results. The original
[2,623-game report](../bot-strength-seeding-2026-10-31/REPORT.md) remains unchanged.

## Evidence map

- `data/configurations.json`, `data/original-design-manifest.json` and
  `data/establishment-manifest.json`: unchanged 250-policy roster and 200/50 split,
  exact original source-manifest bytes and the separate new-run limits.
- `data/initial-native-perfs.json`, `data/frozen-training-perfs.json` and
  `data/final-native-perfs.json`: actual earned native snapshots. The training
  snapshot retains its original checksum; V2 selects only the 200 training rows.
- `data/ratings.csv`, `data/native-progress.jsonl.gz`: all 500 bot/speed cells,
  native flags/RD/rating changes and NEW-run exposure, separate from total history.
- `data/games.jsonl.gz`, `data/pgns/` and
  `data/acknowledged-moves.jsonl.gz`: 826 new admissions/results, legally replayed
  public BOT PGNs and 71,287 unique acknowledged plies. No old/private/synthetic
  qualification games are included.
- `data/epoch-events.jsonl.gz`, `data/integrity-lineage.json`: training drain,
  freeze, first test admission, source/input commitments and projection hashes.
  The fitted artifact is omitted; its checksum is provenance, not verified bytes.
- `data/frozen-predictions-v2.csv`, `data/evaluation.json`: 500 frozen point
  predictions and the unchanged evaluator's metrics/denominators. Native RD is
  in the snapshot/ratings files; the private model's heuristic predictive SD is
  not a calibrated confidence bound.
- `data/native-count-audit.json`, `data/operational-audits.json` and
  `data/execution-summary.json`: independent native result reconciliation,
  sanitized final cleanup and actual execution accounting.
- `data/resources-projection.jsonl.gz`, `figures/figure-metrics.json`: recorded
  worker/sampled-service resources and explicit measurement windows/omissions.
- `verify_public.py`: strict saved-public-data integrity and full PGN/ACK replay.
- `tools/predictor_v2.py`, `tools/check_evaluation.py`, `tools/check_refit.py` and
  `data/refit-verification.json`: exact pinned procedure, evaluator reproduction
  and separate frozen-training-only numerical refit check.
- `figures/`, `tools/build_figures.py`, `requirements-figures.txt`: three PNG/SVG
  figure pairs and their reproducible metrics/input hashes.
- `SHA256SUMS`: publication-file checksums, excluding the checksum file itself.

## Cached verification

Use Python 3.12 in a disposable environment and fresh scratch output paths.
These checks need no ONNX weights/runtime, neural inference, database or live
service. Installing dependencies is the only package-download step.

```sh
python3.12 -m venv /tmp/mute-night163-verify
/tmp/mute-night163-verify/bin/python -m pip install -r requirements-verify.txt
PYTHONDONTWRITEBYTECODE=1 /tmp/mute-night163-verify/bin/python verify_public.py \
  --bundle . --output /tmp/mute-night163-integrity.json --require-checksums
PYTHONDONTWRITEBYTECODE=1 /tmp/mute-night163-verify/bin/python tools/check_evaluation.py \
  --bundle . --output /tmp/mute-night163-evaluation.json
```

The pinned cached numerical/chess environment uses NumPy 2.3.5 and chess 1.11.2
(`python-chess` package 1.999). Integrity checks include 826 unique games, legal
results, 71,287 unique ACKs, native count deltas, training 400 flags before the
freeze, final 500 flags and exact source/data commitments. The evaluator check
recomputes the original metrics from public frozen point predictions and final
results without fitting. These are public projection checks; independent live
native database/cleanup observations remain separately identified operator evidence.

## Refit only the frozen training snapshot

```sh
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  /tmp/mute-night163-verify/bin/python tools/check_refit.py \
  --bundle . --output /tmp/mute-night163-refit.json
```

The script verifies snapshot/source hashes, reads only the original frozen
snapshot/roster/split/reference predictions, and executes the unchanged V2
training procedure. It reads no final outcomes, writes no coefficients and
never changes native ratings. All 500 prediction values reproduced within 1e-7;
the recorded maximum difference was 3.18e-11. Small platform/linear-algebra
variation should be reported rather than used to overwrite frozen predictions.

## Regenerate figures in a scratch copy

The figure script writes `figures/` under its own bundle, so use a fresh scratch
copy to preserve the published reference files:

```sh
/tmp/mute-night163-verify/bin/python -m pip install -r requirements-figures.txt
cp -R . /tmp/mute-night163-figures
PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR=/tmp/mute-night163-mpl \
  /tmp/mute-night163-verify/bin/python /tmp/mute-night163-figures/tools/build_figures.py
```

The script uses saved public projections, performs no fit or inference, and
records input hashes/derived metrics. CPU estimates are conditional on continuous
counters; the projection lacks independent process identity timestamps. Reply
throughput is workload-specific, and capacity scenarios do not change the normal
production cap of 2.

## Using the reference and its limits

New names can reuse supported policy priors without each playing a calibration
tournament first. Each account retains its own native provisional mechanism and
earned history; another account's count/RD/established flag is not copied.
The report explains both the measured policy reference and fitted mapping's
error, rather than equating a conditioning input with playing Elo.

These are previously observed test configurations, not a fresh blind test.
Native establishment improves relative rating precision but does not independently
prove absolute human Lichess alignment. Source dependency declarations are not
proof of the installed inference environment. No coefficients, neural weights,
private environments/keys, database dump or backup ciphertext are published.
Original sampling seeds are omitted, so exact fresh neural replay of sampled
trajectories is outside this cached reproduction.

Preserve the repository's [AGPL-3.0-only license](../../LICENSE) and applicable
third-party terms. Attribution and pinned application sources are in the report.
