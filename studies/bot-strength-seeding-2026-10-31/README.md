# Maia bot-pool starting ratings — evidence and reproduction

[Read the report](REPORT.md). The completed study contains **2,623 public native
Blitz/Rapid games and 221,867 legal acknowledged plies**, including 623 held-out
matches. The primary and preregistered secondary predictors missed the practical
100-point native-label MAE target. All 50 held-out configurations remain
provisional; these results do not establish an absolute human Lichess scale.

The original segment completed normally. The conditionally authorized 377-game
tail did not start after isolated qualification startup failed. The no-tail
choice preceded offline evaluation; no model or simulation budget was tuned
from its test results. The original deadlines and dated amendment remain in
`provenance.json` and the report.

## Evidence map

- `provenance.json`, `ARTIFACT_SCHEMA.md`: source/model/freeze/split pins,
  publication-file hashes, execution limits and exact public data formats.
- `data/configurations.json`, `data/design-manifest.json`: 250 recorded policies,
  200 training identities/196 effective configurations, 50 distinct held-out
  configurations and no exact cross-split aliases.
- `data/initial-native-perfs.json`, `data/frozen-training-perfs.json`,
  `data/final-native-perfs.json`, `data/ratings.csv`: actual native ratings,
  uncertainty, counts and cohort changes. The training snapshot retains its
  original checksum; raw historical roster seeds remain separately identified.
- `data/games.jsonl.gz`, `data/pgns/`: 2,623 admitted game records and complete
  public BOT-versus-BOT PGNs. No private qualification games are included.
- `data/acknowledged-moves.jsonl.gz`: 221,867 projected acknowledgment rows,
  matching the final legal UCI sequences without duplicate game/ply entries.
- `data/frozen-predictions-v1.csv`, `data/frozen-predictions-v2.csv`,
  `data/seed-baseline.csv`: 500 identity/speed predictions per table. The baseline
  is each unchanged roster `initial_rating`, including historical seeds for
  original 44 opponents; it is not a corrected native pregame-rating forecast.
- `data/evaluation.json`: both procedures, seed baseline, exact denominators,
  MAE/configuration intervals, expected-score Brier/cross-entropy and coverage.
- `data/execution-summary.json`, `data/resources-projection.jsonl.gz`: unique-commit
  throughput, latency and scoped worker/native-service resource observations.
  The public-result verifier does not duplicate the separate capacity analysis.
- `data/operational-audits.json`: sanitized independent native count/cleanup
  observations and the unexecuted continuation's failure scope.
- `data/projection-lineage.json`, `tools/project_evidence.py`: extraction method,
  original artifact commitments and omitted-field descriptions. The projection
  utility requires operator-retained raw inputs and is not needed for cached
  public verification.
- `tools/predictor_v1.py`, `tools/predictor_v2.py`, `tools/check_refit.py`,
  `data/refit-verification.json`: exact pinned training procedures and their
  separate frozen-snapshot prediction-table reproduction.
- `verify_public.py`, `test_verify_public.py`, `requirements-verify.txt`: public
  checksum/game/metric verification and synthetic qualification.
- `figures/`, `tools/build_figures.py`, `requirements-figures.txt`: PNG/SVG
  figures and their reproducible metrics/source hashes.
- `SHA256SUMS`: publication checksums, excluding the checksum file itself.

## Cached verification

Use Python 3.12 in a disposable virtual environment and choose new output paths.
These commands require no ONNX Runtime, neural weights, engine search, database,
public-service connection or inference. Dependency installation is the only
package download; checks run from the recorded bundle.

```sh
python3.12 -m venv /tmp/mute-strength-verify
/tmp/mute-strength-verify/bin/python -m pip install -r requirements-verify.txt
PYTHONDONTWRITEBYTECODE=1 /tmp/mute-strength-verify/bin/python verify_public.py \
  --bundle . --output /tmp/mute-strength-cached \
  --check-reported --verify-pgn
```

The pinned cached environment is NumPy 2.3.5 and chess 1.11.2. The command verifies
publication/artifact checksums, the exact frozen training snapshot, prediction
coverage, split/freeze boundaries, native snapshot count reconciliation,
acknowledgment sequences and legal PGNs. It recomputes native-label errors,
configuration-bootstrap intervals and prospective score metrics for V1, V2 and
the explicit historical-seed baseline, comparing them with `data/evaluation.json`.
It writes `recomputed-evaluation.json` and `verification.json` only to the new
output directory. Reported numerical tolerances are absolute 1e-10 / relative 1e-12.

The original operational database audit is a distinct operator observation,
not something this offline verifier queries. Resource samples retain their
separate windows/scopes; sampled peaks exclude unrecorded processes and cannot
be treated as whole-machine peaks.

## Reexecute the fixed training procedures

```sh
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  /tmp/mute-strength-verify/bin/python tools/check_refit.py \
  --bundle . --output /tmp/mute-strength-refit.json
```

This script reads only the original frozen training snapshot, roster, split and
reference prediction tables. It runs both fixed training procedures before
comparing their 500 predicted values with the published tables. It does not
read final outcomes/ratings, choose using test error, write coefficients or
perform neural inference. The recorded check's maximum prediction differences
are about 2.8e-11 for V1 and zero for V2, below the declared 1e-7 tolerance. Small
numerical variation across linear-algebra providers is reported rather than
used to overwrite the frozen predictions.

The primary training implementation comes from Mute Chess
`f656d5c22b062646cc48c54feced50cb2c6710f6`; the preregistered effective-CV secondary
comes from `0e237532c4c0272026e6e2af60d35336cdf08ca3`. V1's identity-fold alias
limitation remains disclosed. Both fits use the same training snapshot, whose
SHA-256 is `4a88c1dd54420b81237f4323b52f328330bd46494866bc890daf9581522fe436`.

## Regenerate the figures

```sh
/tmp/mute-strength-verify/bin/python -m pip install -r requirements-figures.txt
PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR=/tmp/mute-strength-mpl \
  /tmp/mute-strength-verify/bin/python tools/build_figures.py \
  --study-dir . --output-dir /tmp/mute-strength-figures
```

Choose fresh scratch paths. The figures use the same recorded evaluations,
ratings and resource projections; `figures/figure-metrics.json` records their
calculated values and input hashes. Regeneration does not change game outcomes,
predictions or ratings.

## Scope, omissions and attribution

The bundle contains frozen prediction tables and reproducible training data/code,
not ONNX weights or fitted coefficient artifacts. The omitted primary artifact's
recorded hash is a provenance commitment; the public verifier explicitly does
not claim to hash absent bytes. Complete original per-game sampling seeds/policy
streams are not projected, so exact fresh neural replay of each sampled game is
outside the published reproduction. Legal recorded-game replay is provided.

The original adapter source declares ONNX Runtime 1.31.1, NumPy 2.5.4 and
chess 1.11.2. Those are source requirements, not a separately verified installed
inference environment; they differ from the pinned cached statistical/refit
runtime above.

Native Glicko/provisional rules remain authoritative. Low noisy-label MAE or RD
would not establish true strength or Lichess alignment; the observed target was
not met. No 10,000-account release, new common rating adjustment, production
capacity increase or further games follow from this report.

This is independent Mobile Maia/Mute Chess research. Preserve the repository's
[AGPL-3.0-only license](../../LICENSE), pinned Maia-derived code attribution and
third-party software/model terms. The [report](REPORT.md) links Lichess/Lila,
Maia/CSSLab and the relevant earlier Mobile Maia studies; project seeding choices
are not upstream recommendations.
