# Public-result verification schema

`verify_public.py` reads a saved publication bundle, verifies its checksums and
public projections, and recomputes the recorded prediction-table metrics. It
does **not** load fitted regression artifacts, fit regressions, run inference,
connect to a database or inspect a live service. No resource/capacity summarizer
is duplicated here.

`provenance.json` records the completed study's source, freeze, accounting and
artifact hashes. Its `status` is `final`: the original segment is complete,
although it reached only 623 of the intended 1,000 validation games. Exact data
filenames are recorded through `dataFiles`.

## Required layout

At bundle root, supply `provenance.json`. Its `schemaVersion` is
`mute-strength-public-results-v1`, `status` is `final`, and
`fullPrimaryFitArtifactIncluded` is `false`.

| `dataFiles` role | Default path | Format |
| --- | --- | --- |
| `configurations` | `data/configurations.json` | Original combined-roster JSON array, preserving fields/order/numeric meaning for its manifest digest |
| `designManifest` | `data/design-manifest.json` | Original experiment manifest, including the unchanged original deadlines and split |
| `initialPerfs` | `data/initial-native-perfs.json` | Actual checkpoint initial rating map, not roster seeds |
| `frozenTrainingPerfs` | `data/frozen-training-perfs.json` | Exact original training-snapshot bytes; SHA must remain `4a88…` |
| `finalPerfs` | `data/final-native-perfs.json` | Final native rating map |
| `games` | `data/games.jsonl.gz` | Public game projections, sorted by original admission ordinal |
| `primaryPredictions` | `data/frozen-predictions-v1.csv` | Frozen V1 predictions, all250 identities ×2 speeds |
| `secondaryPredictions` | `data/frozen-predictions-v2.csv` | Preregistered V2 predictions, the same250 ×2 pairs |
| `seedBaseline` | `data/seed-baseline.csv` | Recorded roster `initial_rating`, with explicitly declared scope/definition |
| `acknowledgments` (optional) | `data/acknowledged-moves.jsonl.gz` | One sanitized row per acknowledged submission: `id`, `ply`, `move` |
| `reportedEvaluation` (optional until generated) | `data/evaluation.json` | Exact recomputed evaluation object used for `--check-reported` |

JSONL may be plain `.jsonl` or gzip `.jsonl.gz`. The verifier reads both directly;
it never extracts archives. For deterministic archive generation use gzip
`mtime=0`. CSV is UTF-8 with headers `id,speed,prediction`; retain sufficient
precision to round-trip the original floating-point prediction. Extra CSV
columns may document extraction/uncertainty but are not used as fit weights.

Native perf maps are flat objects keyed by roster ID. Each identity has exactly
`blitz` and `rapid`, each containing at least `rating`, `rd`, `games`,
`provisional`. Retain original volatility as appropriate. Native game counts
must be monotonic across initial/frozen/final maps. The frozen snapshot can
include held-out perf rows, but fitting never uses those rows.

The seed baseline scope is either:

- `all-identities-native-label-and-outcome`: all250 ×2 baseline rows, exactly
  each roster `ratings[speed].initial_rating`; both MAE and outcome metrics are
  recomputed. This publication uses this scope.
- `heldout-native-label-only`: only50 ×2 rows and only native-label metrics.

`seedBaselineDefinition` must state the method explicitly. Original44 historical
seeds differ from their corrected/earned native starting ratings, so the all-ID
seed outcome forecast is a historical-seed reference, not an optimized native
pregame forecast. Do not silently apply another−75 correction to its inputs.

## Game and acknowledgment rows

One game row, in admission order:

```json
{
  "id": "PUBLIC_GAME_ID",
  "segment": "original",
  "admissionOrdinal": 2001,
  "stage": "validation",
  "white": "PUBLIC_BOT_ID",
  "black": "PUBLIC_BOT_ID",
  "speed": "blitz",
  "admittedAtUtc": "SOURCE_ADMISSION_EVENT_TIMESTAMP",
  "state": "finished",
  "result": {
    "status": "mate",
    "winner": "black",
    "plies": 4,
    "ratedUpdate": true
  },
  "moves": ["f2f3", "e7e5", "g2g4", "d8h4"]
}
```

This example describes field types, not a real study game. `winner` is `white`,
`black` or JSON null. Finished records require a complete UCI move list matching
`plies`. Other allowed final accounting states are `aborted` and `unfinished`;
they do not become fabricated rated results. Extra native result fields may be
retained. `admittedAtUtc` is the recorded driver's admission observation, not an
assertion of an exact native creation timestamp.

Admission ordinals are unique/consecutive starting at1. Original stage thresholds
are200/2000/3000. Pre-freeze games use the allowed training/original identities;
validation games have exactly one held-out and one training participant.
`predictionFreeze` must precede the first held-out admission and match its exact
recorded ordinal/timestamp and model-artifact hash.

Acknowledgment rows preserve `id`, zero-based pre-move `ply`, and UCI `move`.
Repeated identical rows remain visible as duplicate counts; conflicting moves
at a game/ply fail. Finished-game unique sequences must exactly match their
public move lists. This verifies published acknowledgment projections; their
extraction from immutable operational events is documented separately.

## Provenance and checksum fields

- `expectedCounts`: the population counts recorded in provenance. Effective policy
  aliases canonicalize zero endpoints and ineffective full-sampling opening
  overrides. The actual design has200 training identities/196 effective policies,
  50 unique held-out policies and zero exact cross-split aliases.
- `sourcePins`: original source commit, secondary-procedure commit, optional
  continuation commit, ONNX hash, omitted full primary-fit artifact hash and
  exact frozen-training snapshot hash. Recorded source pins do not imply that
  the verifier fetched GitHub or authenticated a remote release.
- `secondaryFitTrainingSnapshotSha256`: must equal the primary training snapshot
  pin. This is a declared lineage check; deterministic refit is a separate step.
- `bootstrap`: method `numpy-default_rng-configuration-bootstrap`, seed137,
  1000 replicates, NumPy version`2.3.5`. This is the cached-statistics runtime,
  not an invented claim about the original ONNX inference environment.
- `segments`: actual worker windows and source commits; `admittedAtStart`,
  segment-local `admitted`, and `finished`/`aborted`/`unfinished` counts. Tail
  offsets are global and tail admissions can contain only validation games.
  An unstarted candidate is not a segment. This completed study has only the
  original segment; the377-game candidate did not start.
- `timingAmendment`: retain the dated authorization and original/amended limits,
  plus the no-continuation decision before evaluation. The public verifier checks
  the declared prospective time ordering; source receipts provide authority.
- `artifacts`: map every referenced relative file path to its actual SHA-256.
  Additional sanitized data/source/figure files may be included. Never list ONNX,
  checkpoint weights, fitted coefficients, private environments or credentials.
- `SHA256SUMS`: cover `provenance.json` and every declared artifact, excluding
  the checksum file itself. This is mandatory with `--check-reported`.

For `--verify-pgn`, expand/publicly provide one finished-game PGN at
`pgnDirectory/<id>.pgn` and include each in `artifacts`/`SHA256SUMS`. No PGN
archive extraction is performed by the verifier. Legal replay uses chess1.11.2,
checks the UCI sequence/result, and verifies mate/stalemate endpoints. Other
native termination semantics and database persistence retain their separate
independent audit receipts.

## Populate and verify without circular hashes

1. Build the public projections/tables/snapshots and reviewed provenance. Hash
   them into `artifacts`; retain extraction/source lineage and excluded-field
   notes. Change `status` to `final` only for an actual final evidence bundle.
2. Run without `--check-reported` to compute deterministic metric JSON into a
   **new separate** scratch directory. No fit or model-file read occurs.
3. Copy `recomputed-evaluation.json` into the bundle as `data/evaluation.json`;
   add the `reportedEvaluation` role and its hash. Rebuild `SHA256SUMS` covering
   updated provenance and all artifacts.
4. Run the final cached check:

```sh
python -m pip install -r requirements-verify.txt
python verify_public.py --bundle /path/to/public-study \
  --output /path/to/new-verification --check-reported --verify-pgn
```

The outputs are `recomputed-evaluation.json` and `verification.json`. Metrics
match the original evaluator's sorted held-out order, NumPy bootstrap, White
score convention and finite-probability clipping. Comparison tolerances are
absolute`1e-10` and relative`1e-12`. Original native-label coverage and actual
held-out study appearances/RD/nonprovisional coverage are reported separately.

The receipt explicitly says the omitted full primary-fit artifact bytes were
**not** verified, and that no regression fit or inference occurred. It also
distinguishes public snapshot reconciliation from live database auditing and
public frozen-table reproduction from reexecuting the service or proving a
regression's training history.

## Synthetic qualification

`test_verify_public.py` generates isolated synthetic files and checks checksums,
metric reproduction, missing/duplicate predictions, frozen snapshot replacement,
native count deficits, policy aliases, segment offsets, model-byte claims,
acknowledgments, CLI output and optional legal PGN replay. Supplying a read-only
`MAIA_EVALUATOR_SOURCE` path also compares every speed metric and nondegenerate
bootstrap interval exactly with that pinned evaluator, including draw targets.
It calls only its `evaluate` function; it never calls `fit` or loads real data.

```sh
python -m unittest -v test_verify_public.py
```

The final report describes the scientific limits beyond these consistency
checks. Passing this verifier does not establish absolute Lichess alignment or
turn uncertain native estimates into true-strength measurements.
