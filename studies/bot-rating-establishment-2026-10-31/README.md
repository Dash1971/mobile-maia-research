# Bot rating estimates: data and reproduction

The [public report](REPORT.md) explains how Mute Chess uses a varied Maia
reference pool to estimate starting ratings for new bots. This guide contains
the exact settings, recorded results and reproduction steps behind that article.
The original prediction evaluation remains in the evidence below. The generated 10,000-identity catalog and its actual allocation have a separate
[method note](CATALOG-METHOD.md). The roster is now live; a separate
[sanitized deployment record](data/catalog-2026-11-01/deployment-status.json)
documents the verified initial state.

## Method reference

| Detail | Recorded method |
| --- | --- |
| Model and input range | Maia3-79M; both conditioning inputs equal the bot's fixed 600–2600 setting |
| Varied controls | Persistent Temperature/Top-P in 0–1, fixed history on/off, and recorded opening rules |
| Opening behavior | Preserve the original policies; generated configurations use full sampling for five full moves before their assigned settings |
| Rating anchor | Historical Lichess Maia3-79M account evidence, with the earlier sampling-policy baseline correction already retained in earned ratings |
| Earned ratings | Native Lichess Glicko-2; RD strictly below 110 is nonprovisional; no forced flags, copied counts or reseeding |
| Fit and check groups | Fixed 200 training /50 test identities; equivalent effective policies share cross-validation groups |
| Frozen procedure | `strength137-ridge-rbf-effective-cv-v2`; weighted ridge, fixed additive/interaction candidates and penalty grid; training-only selection |
| Prediction freeze | Exact drained snapshot after all 400 training bot/speed ratings were established, before the 477 new test games |
| Test interpretation | Previously observed configurations; inherited training histories include earlier test results; this is not a new blind validation |
| Timing | Added human timing waits disabled for study games; native clocks retained; production timing personalities unchanged |

The exact anchor and sampling-adjustment provenance, run chronology, source
pins, native criterion and capacity observations remain in the
[original technical record](https://github.com/Dash1971/mobile-maia-research/blob/896eeffe9af20531c688ec71e9e28e0c978bbe90/studies/bot-rating-establishment-2026-10-31/REPORT.md),
[provenance](provenance.json) and recorded data below. The earlier
[2,623-game dataset](../bot-strength-seeding-2026-10-31/README.md) is preserved
separately; together with this guide's 826-game dataset it provides the 3,449
published games cited in the article. The baseline retains older earned history
as well. No new games or rating writes accompany this rewrite. The historical [catalog-planning approximation](PLANNING-APPROXIMATION.md) is a
separate posthoc calculation. The live implementation reuses exact measured
policies; neither changes the original frozen procedure or its predictions.

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
- `figures/`, `tools/build_figures.py`, `tools/build_reader_figures.py` and
  `requirements-figures.txt`: technical and reader-facing PNG/SVG figures with
  reproducible metrics/input hashes.
- `CATALOG-METHOD.md`, `data/catalog-2026-11-01/` and
  `tools/audit_catalog_allocation.py`: pinned generated catalog manifest, dated
  source frequencies, file hashes and independent policy/allocation audit.
- `PLANNING-APPROXIMATION.md`, `tools/public_rating_approximation.py` and
  `data/reader-chart-sources.json`: preserved historical planning approximation,
  history sensitivity, controlled sampling sources and former illustrative allocation.
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
PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR=/tmp/mute-night163-mpl \
  /tmp/mute-night163-verify/bin/python /tmp/mute-night163-figures/tools/build_reader_figures.py
```

The figure scripts use saved public projections and cited source measurements,
perform no fit or inference, and
record input hashes/derived metrics. CPU estimates are conditional on continuous
counters; the projection lacks independent process identity timestamps. Reply
throughput is workload-specific, and capacity scenarios do not change the normal
production cap of 2.

## Using the reference and its limits

The live catalog reuses measured policies for 9,750 new identities while
preserving all 250 original accounts. New accounts were initialized with RD 100
and zero completed games, making those ratings nonprovisional under native
rules without inventing earned history. They display a Research-seeded label.
The separate deployment verification confirmed the initial native records;
this publication and its offline audit do not provision accounts. The [catalog note](CATALOG-METHOD.md)
explains the exact reuse rule, supported range and actual distribution.

Audit the copied source records and aggregate allocation with no dependencies:

```sh
python3 tools/audit_catalog_allocation.py
```

These are previously observed test configurations, not a fresh blind test.
Native establishment improves relative rating precision but does not independently
prove absolute human Lichess alignment. Source dependency declarations are not
proof of the installed inference environment. No original fitted-model artifact, neural weights,
private environments/keys, database dump or backup ciphertext are published.
Original sampling seeds are omitted, so exact fresh neural replay of sampled
trajectories is outside this cached reproduction.

Preserve the repository's [AGPL-3.0-only license](../../LICENSE) and applicable
third-party terms. Attribution and pinned application sources are in the report.
