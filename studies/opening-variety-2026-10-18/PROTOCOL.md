# Opening-variety sampling comparison — 18 October 2026

This protocol is frozen before the main outcome-generating runs. It addresses
[Preview issue #155](https://github.com/Dash1971/maia-chess-android-preview/issues/155).
No app settings or releases are changed by the experiment.

## Inputs and conditions

Pin Preview `3702f6f197135dbac9ae38a9aa9720e15c603e5c`, Maia-3 79M ONNX
SHA-256 `3454b03ae78baa64a87b345fdb1a457265d912caec531039b074f07eda0d8010`
(316,034,244 bytes), CPU ONNX Runtime 1.30.0, Python 3.12.13, numpy 2.5.3,
python-chess package 1.999 / chess module 1.11.2. History is off: repeat the
current side-oriented board in all eight input slots. Both Elo inputs use the
tested rating (600, 1600, or 2400). No opening book, search, resignation,
draw agreement, time losses, or forced opening moves influence the matches.

| Arm | Temperature | Top-P | Opening override |
| --- | ---: | ---: | --- |
| A | 1.0 | 1.0 | Off; current default |
| B | 1.0 | 0.95 | Off; control |
| C | 1.0 | 0.95 | On; 1/1 through full move 5, configured pair from move 6 |

The override uses the actual FEN full-move number for both colors, not a
middlegame classifier. Its cutoff is a design choice, not a proven optimum.
Python RNG streams are explicitly recorded; they need not match Dart's seed
algorithm. Compare probability distributions and selections with fixed uniform
draws against the pinned Dart sampler. Consume a uniform draw even for a sole
retained move. Count cutoff ties, because Dart/Python sorting can order equal
weights differently; investigate any encountered boundary tie before accepting
its effect on the study. Verify official model logits and phase boundaries.

## Fixed match design

At 1600, play 600 games per unordered pair: C–A, B–A, C–B (1,800 total).
At 600 and 2400, play 200 games per pair (1,200 additional games).
Total: **3,000 games**, starting from the standard position.

Consecutive games form a reverse-color pair. Within the pair, RNG streams
belong to the profile, using seed
`18_000_000_000 + rating*1_000_000 + pair_index*100_000 + pair_number*10`
for the first arm, and plus one for the second. Pairs have independent streams;
do not treat the two games within a pair as independent bootstrap units.

End on the app's actual threefold raw-FEN repetition, halfmove clock >=100,
checkmate, stalemate, or insufficient material; cap at 400 plies and label cap
draws explicitly. Claimable future draws do not end the game. Preserve full
move sequences, seeds, results, termination, and final FEN; replay every game.
Also compute prospective-claim endpoints from the sampled prefixes as a
sensitivity, without replacing the primary result.

The predeclared primary contrast is C–A at 1600. Other matchups and ratings are
secondary robustness/attribution analyses. Report W/D/L, color-specific scores,
relative matchup Elo `400*log10(score/(1-score))`, and 95% percentile intervals
from **100,000 paired-cluster bootstrap draws** (seed 38,000,000,000 plus rating
and contrast index). Report cap-draw sensitivity. No early stopping or outcome-
dependent expansion. A relative score is not a calibrated human Elo rating.

## Opening rollouts

At 1600, generate **1,000 rollouts per arm**; at 600 and 2400, **400 per arm**
(5,400 total), each up to **24 plies** or actual game termination. Use identical
per-color random streams across arms for each rollout index: seed
`28_000_000_000 + rating*1_000_000 + index*10` for White, plus one for Black.
These matched streams make A and C identical through ply 10; verify that fact
for every rollout rather than infer later repertoire preservation from it.

Label positions using the existing study's pinned Lichess opening table
(`../maia3-sampling/openings/source/lichess_openings.tsv`, SHA recorded in the
analysis receipt). Carry the last recognized family forward, but report
unclassified fraction, early terminations, and classification limits. No book
guides the rollouts. At plies **8, 10, 12, 16, 24**, report exact-line diversity,
unique families, effective families (2^Shannon entropy), concentration of the
most common family, and repeated exact-line fraction at equal sample sizes.
Pair-bootstrap the C/A effective-family ratio at ply 24 with **2,000** replicates
and independently recorded seed. Ratios based on finite samples are descriptive;
do not infer human opening fidelity solely from these model-only counts.

## Objective-quality diagnostic

Before reading outcomes, deterministically take **60 positions per rating**
from A–C matches, using game order then plies 12, 24, and 40, at most one position
per reverse-color pair (first eligible position). If fewer exist, record the
shortfall. On the same positions compare the effective A/B/C distributions.
At these post-override positions B and C must have identical distributions.

For every legal move, evaluate the resulting child with pinned installed
Stockfish, **20,000 nodes**, one thread, Hash 32 MiB, fresh search state per
move. Record engine identity, binary hash, raw score/depth/nodes and all legal
move values. Score from the original mover's perspective; terminal checkmate
is +32,000 cp and immediate draws zero. Report expected evaluation loss against
the best evaluated legal move, plus mass on moves >=100 and >=200 cp worse.
Mate-score mapping and fixed shallow node budgets limit these diagnostics.
Treat this as a paired, secondary mechanical-risk comparison, not proof of
full-game strength or playing style. Bootstrap mean differences across positions
within each rating (10,000 replicates). Pin the engine before running diagnostics.

## Decision and publication

Keep defaults unchanged during research. Recommend a candidate only if the
primary score improvement is supported by its interval, lower/higher ratings
do not reveal a material contrary pattern, and opening diversity is reasonably
preserved beyond the override. Use a **0.90 effective-family C/A ratio** as a
predeclared practical reference, not a universal definition of acceptable chess.
Report uncertainty, including failure to establish non-inferiority, rather than
equating no significant difference with equivalence. Separate an optional
stronger-play profile from the philosophical choice of full human-distribution
sampling. An inconclusive result is a valid recommendation to retain defaults.

Publish scripts, protocol, inputs, raw games/rollouts, PGNs, diagnostic values,
manifests, verification and report in the research repository. Exclude model
weights, machine-specific paths, environments and credentials. Preserve earlier
studies unmodified; explain changed sampling draw consumption, paired design,
sample counts and runtime before comparing historical numbers. App documentation
gets only a brief finding and link. Any actual default/help change is separate.
