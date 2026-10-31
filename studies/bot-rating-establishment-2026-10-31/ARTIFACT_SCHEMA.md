# Published evidence schema

This bundle describes the completed `r20261031n163` follow-up. The earlier
`r20261031p137` study and its publication remain separate and unchanged.

| File | Meaning |
| --- | --- |
| `provenance.json` | Source/model/roster/split commitments, approved limits, observed execution, freeze and cleanup scope |
| `data/configurations.json` | The exact 250-policy roster; model conditioning inputs are not earned ratings |
| `data/original-design-manifest.json` | Exact original source manifest bytes; its historical dates remain intact |
| `data/establishment-manifest.json` | Follow-up run/profile, limits, split and original commitments |
| `data/initial-native-perfs.json` | Actual earned native ratings at this run's start, including previous history |
| `data/frozen-training-perfs.json` | Exact drained freeze snapshot; the fit selects only the 200 training identities |
| `data/final-native-perfs.json` | Final native rating, live rating deviation, volatility, total games and provisional flag for 250 × 2 cells |
| `data/native-progress.jsonl.gz` | Irregular timestamped native observations, completed count, epoch and full perfs; no invented intermediate ratings |
| `data/epoch-events.jsonl.gz` | Recorded phase transitions, freeze and goal events |
| `data/games.jsonl.gz` | 826 admissions with ordinals, seats, speed, epoch, event order, whitelisted policies, final native result and UCI moves |
| `data/pgns/` | Every corresponding public BOT game PGN, checked against seats, native result, clocks and acknowledged moves |
| `data/acknowledged-moves.jsonl.gz` | 71,287 unique game/ply/UCI acknowledgments and whitelisted timing fields |
| `data/ratings.csv` | 500 initial/final bot-speed rows, total and new-run counts, earned changes, cohort and native flags |
| `data/frozen-predictions-v2.csv` | 500 frozen estimates: `id,speed,prediction`; no fitted coefficients |
| `data/evaluation.json` | Exact unchanged fixed evaluator result; configuration counts use total native games |
| `data/execution-summary.json` | Observed 826 finishes, speed/epoch counts, windows and stop reason |
| `data/native-count-audit.json` | Sanitized independent native per-bot/speed count reconciliation |
| `data/operational-audits.json` | Whitelisted independent cleanup, native-flag, health and security observations |
| `data/resources-projection.jsonl.gz` | Worker and six service cgroups; numeric/string counters and missing values retained |
| `data/integrity-lineage.json` | Input commitments, extraction/verifier source hashes and the core public projection hashes |
| `data/refit-verification.json` | Exact training-only numerical reproduction receipt; no outcome-based fitting |
| `audit-report.json` | Public integrity verifier's recomputed completion, replay, count and freeze results |
| `figures/figure-metrics.json` | Technical figure input hashes, resource arithmetic, exclusions and conditional capacity scenarios |
| `figures/reader-figure-metrics.json` | Input hashes and measured values used by the illustrated public report |
| `SHA256SUMS` | All published study artifacts except this checksum file itself |

The raw driver freeze includes all 250 native perf rows. Only the fixed 200
training IDs enter fitting or cross-validation; the 50 test labels are excluded.
All 349 training admissions and finishes precede the freeze and the first new
test admission. Test policies were observed in the earlier phase, so this is a
follow-up precision study rather than a fresh blind test.

The exact roster retains historical descriptive metadata. The runtime
`personality.history` value and validated per-game policy snapshots specify the
fixed history setting used here; an older `history_policy` description does not
override them.

Native perf `games` is lifetime history. New-run exposure comes from this run's
admissions and final results. A new identity never receives another account's
earned counts, uncertainty or established flag. Native establishment is the
unrounded live RD rule, strictly below 110; raw database RD and rounded API RD
must not be substituted for the native provisional flag.

Resource rows contain no process invocation identifiers. CPU arithmetic accepts
only adjacent active samples with numeric nondecreasing counters and intervals
up to 30 seconds. It assumes continuity between those samples; this projection
cannot independently prove process identity continuity. Sampled totals omit
GIF, Cloudflared, isolation and operating-system/other host activity. Capacity
scenarios are workload assumptions, not measured VPS limits or admission changes.

`project_evidence.py` documents the whitelist from retained private evidence.
`verify_public.py` independently checks the public projections, PGNs, policies,
native counts, freeze and goal without those private inputs. The omitted fitted
artifact is identified by a recorded hash; public verification does not pretend
to check absent bytes. `tools/check_refit.py` instead reproduces the frozen
prediction table from the exact public training snapshot without writing fitted
coefficients. `tools/check_evaluation.py` uses public tables and results without
fitting. Neural weights, sampling seeds, private paths/environments, credentials,
raw database documents, backups and ciphertext are excluded.
