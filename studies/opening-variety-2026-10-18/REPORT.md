# Opening variety and Top-P 0.95

Completed 18 October 2026: **3,000 full games, 5,400 opening rollouts and 180
quality positions**, using the pinned Maia-3 79M model. All 8,400 game/rollout
records and 404,780 plies passed independent replay in the app's chess library.

**Recommendation: propose Temperature 1.0 / Top-P 0.95 with Max variety in
opening enabled as a balanced default in a separate Preview change.** It
improves the primary match score, has no contrary cross-rating point estimate,
and preserves the measured broad opening mix. Keep 1.0/1.0 available for people
who want Maia's full, untrimmed probability distribution.

This is a choice about the desired playing experience, not proof of better
human-move fidelity. Opening-label resolution is limited, the 600 match is
inconclusive, and the five-move cutoff has not been optimized. No application
defaults, saved preferences or releases were changed by this research.

## Completed primary comparison

At rating input 1600 for both sides, compare current defaults (A: Temperature
1.0 / Top-P 1.0) with C (Temperature 1.0 / Top-P 0.95 and **Max variety in
opening** enabled). Both use the pinned Maia-3 79M model with history off.

| Result for C against A | Completed 600-game result |
| --- | ---: |
| Wins / draws / losses | 345 / 38 / 217 |
| Score, including half a point per draw | 60.67% |
| Paired-cluster 95% score interval | 56.75–64.58% |
| Relative matchup Elo | +75.3 |
| Paired-cluster 95% Elo interval | +47.2 to +104.4 |
| Artificial 400-ply cap draws | 0 |

The bootstrap resamples 300 reverse-color pairs, with 100,000 draws. The Elo
number is a transformation of this matchup score, **not a calibrated human
rating**. C scored 59.67% as White and 61.67% as Black.

All 600 games and 55,502 plies passed independent replay in the app's Dart
chess library, with matching legal moves, final positions, natural results and
termination reasons. See [the replay receipt](verification/fixed-primary-dart-replay.json)
and [the primary statistics](verification/fixed-primary-preview.json).

This supports a strength gain in this fixed comparison. It does not establish
preservation of opening variety or that this is a better overall default for
the intended human-like playing experience.

## Completed controls and cross-rating matches

B uses Temperature 1.0 / Top-P 0.95 throughout, with no opening override.
Each cell reports the first arm's score and paired-cluster 95% interval.

| Rating input | C against A | B against A | C against B | Games per comparison |
| --- | ---: | ---: | ---: | ---: |
| 600 | 55.00% (48.00–61.75%) | 63.75% (57.25–70.25%) | 48.50% (41.75–55.25%) | 200 |
| 1600 | 60.67% (56.75–64.58%) | 58.75% (54.92–62.50%) | 51.67% (47.92–55.42%) | 600 |
| 2400 | 64.00% (58.00–70.00%) | 61.50% (55.25–67.75%) | 48.00% (41.75–54.25%) | 200 |

The candidate's lower-rating interval includes 50%; that comparison is
inconclusive. The higher-rating comparison supports the primary direction.
The C–B intervals do not establish a strength advantage for the opening
override itself, nor do they establish equivalence between C and B.

All 3,000 games passed independent replay in the app's chess library, and none
reached the artificial 400-ply cap. The one observed tied nucleus boundary
passed [direct comparison against the pinned Dart sampler](verification/tie-investigation.json).
The [18-game seed-reproduction audit](verification/seeded-replay.json) also
reproduced every sampled move across all ratings and contrasts.

Using earlier prospective-claim draw endpoints changes 69 results across the
3,000 games. C–A scores become 55.00%, 60.42% and 63.00% at 600/1600/2400;
the direction is unchanged. The primary results use the app's actual draw
rules, not prospective claims. See [the sensitivity data](verification/claim-sensitivity.json).

## Opening mix and later divergence

These are equal-sized samples through 24 plies, carrying the last recognized
opening family forward after a line leaves the pinned Lichess table or ends
early. Each arm uses the same number of rollouts within its rating.
An effective family count is the exponential of Shannon entropy: it accounts
for concentration as well as the number of distinct labels.

| Rating | Rollouts per arm | A: distinct / effective families | B: distinct / effective families | C: distinct / effective families | C/A effective ratio (95% interval) |
| --- | ---: | ---: | ---: | ---: | ---: |
| 600 | 400 | 64 / 34.87 | 53 / 30.59 | 64 / 34.87 | 1.000 (1.000–1.000) |
| 1600 | 1,000 | 70 / 32.36 | 59 / 25.92 | 70 / 32.36 | 1.000 (1.000–1.000) |
| 2400 | 400 | 61 / 30.98 | 56 / 27.51 | 62 / 31.37 | 1.013 (1.000–1.027) |

The observed family ratios clear the prespecified 0.90 practical reference.
However, A and C have identical final family labels in 400/400, 1,000/1,000
and 398/400 paired rollouts. At the first two ratings, every paired bootstrap
resample therefore gives ratio 1. **Those degenerate intervals reflect coarse,
mostly early labels; they do not establish certainty about later variations
or population repertoire equivalence.**

All 1,800 A/C pairs match through the first ten plies, or an earlier common
termination, as required by the identical opening policy and matched random
streams. Agreement then falls. At 1600, 653/1,000 pairs agree through ply 12,
304 through ply 16, and only 71 through ply 24. At 600 and 2400, complete
24-ply/early-ended sequence agreement is 15/400 and 66/400. Divergence shows a
policy change; it does not itself measure population diversity loss.

At 1600, distinct exact prefixes are:

| Plies | A | B | C |
| --- | ---: | ---: | ---: |
| 8 | 975 | 948 | 975 |
| 10 | 997 | 991 | 997 |
| 12 | 1,000 | 999 | 1,000 |
| 16 | 1,000 | 1,000 | 1,000 |
| 24 | 1,000 | 1,000 | 1,000 |

Earlier terminal prefixes are marked and included. Repeated-prefix fractions
are 2.5%/5.2%/2.5% at ply 8 and 0.3%/0.9%/0.3% at ply 10 for A/B/C. Later
counts saturate the sample size, so they cannot resolve rare-variation loss.
Early terminations before ply 24 are 26/30/29 at 600, 9/13/10 at 1600 and
0/2/0 at 2400. Survivor-only counts and sample sizes are retained separately
in [the full results](results.json); the table above does not discard them.

The **post hoc** [ECO-resolution and coverage check](ANALYSIS_NOTE.md) gives
C/A effective-ECO ratios 1.000 (1.000–1.000), 1.000 (1.000–1.000), and 1.015
(0.989–1.030). This is also mostly insensitive at the lower two ratings. At
1600, B actually has 119 distinct ECO codes versus 117 for A and C, despite
having fewer broad families: no single label count captures every kind of
variety.

After ply 10, an exact table position is encountered in only 0/0/0 rollouts
at 600, 13/23/18 at 1600 and 47/73/52 at 2400 (A/B/C). None is an exact
table position at ply 24. No carried family is unclassified, but that does
**not** mean the games remain in known theory. The 3,810-row table includes
lines up to 36 plies; coverage and the carry rule limit the inference.

## Completed quality diagnostic

There are 60 positions per rating, 30 with each color to move and 20 each at
moves 7, 13 and 21. Each legal move's child position
received a fresh 20,000-node Stockfish 18 search, with the terminal-position
exceptions defined in the protocol.

| Rating input | A: probability of loss >=200 cp | C: probability of loss >=200 cp | C minus A, percentage points (95% interval) |
| --- | ---: | ---: | ---: |
| 600 | 21.69% | 20.76% | −0.93 (−1.17 to −0.70) |
| 1600 | 8.89% | 7.99% | −0.89 (−1.19 to −0.61) |
| 2400 | 5.81% | 5.46% | −0.34 (−0.55 to −0.16) |

Loss is measured against the best evaluated legal move in the same position.
The mean probability of loss >=100 cp also falls: 35.75% to 34.39% at 600,
23.85% to 22.48% at 1600, and 11.73% to 11.02% at 2400. Expected evaluation
loss is lower in 163 positions, higher in 12, and unchanged in five. Lower
Top-P does not improve every position.

Twenty positions include mate-valued branches (12/6/2 across the three
ratings). Mapping these scores to roughly ±32,000 cp inflates mean expected
loss; these values are not typical game losses or a calibrated blunder rate.
Fixed shallow search, selected positions and the research evaluator's version
also limit generalization. B and C have the same distribution on these post-override
positions, so this diagnostic isolates the later Top-P change, not the effect
of the opening override itself.

Top-P removes a mean 4.14%, 3.56% and 3.28% of raw probability at 600, 1600 and
2400 respectively. This changes Maia's distribution even where an evaluated
quality metric improves. No new human-move reference comparison was run.

See the [full diagnostic summary](quality-results.json),
[coverage](verification/quality-coverage.json) and
[per-position/move data](data/quality.jsonl): 5,824 legal child moves and about
115 million Stockfish nodes. The [independent cached audit](verification/cached-audit.json)
passed all recorded probability, loss and coverage checks.

## Method and limits

Both rating inputs equal the tested value. Matches start from the normal
position with no opening book, engine search, resignation, draw agreement or
time losses. A full-move number of 1–5 enables C's override for either color;
move 6 uses 1.0/0.95. This boundary is a project design choice, not a tested
optimum or an upstream recommendation.

The primary comparison was fixed before the runs. Other ratings, controls and
quality measures are secondary; their 95% intervals are nominal and do not
adjust for multiple comparisons. Reverse-color match pairs, rather than
individual games, are the bootstrap units. Quality comparisons are paired on
the same selected positions and do not represent all game positions.

This study generates new matches and opening samples; it does not pool them
with the earlier sampling study. The earlier work included other temperatures
and a 5M-model check, used 2,000 openings per sampled setting through eight full moves, and
had a 1,200-game 1.0/0.95 follow-up. Here the opening horizon is 12 full moves,
sample sizes vary by rating, and uncertainty respects reverse-color pairs.
The runner also consumes a random draw for a sole retained move, matching
the pinned app; earlier helper behavior could change subsequent seeded
trajectories. Numerical differences from the old study are not evidence of
a model change.

The model is Maia-3 **79M**, with history off and the current board repeated
in eight input slots. Results do not establish human rating calibration,
human-move fidelity, effects with history on, a universal Elo gain, or behavior
at untested rating inputs. The quality evaluator is Stockfish **18**, with
20,000 nodes per child; it is not the app's bundled engine. These diagnostics
do not model every repetition history or replace a deep tactical benchmark.
No temperature grid, alternative Top-P cutoff or opening boundary was
optimized in this experiment.

## Verification and compute

The [Dart replay receipt](verification/dart-game-replay.json) covers all 8,400
records and 404,780 legal plies, matching natural results and termination
reasons. The [cached audit](verification/cached-audit.json) independently
checks W/D/L, colors, all 180 diagnostic distributions, opening-table labels,
counts/entropies, matched prefixes and every observed tied nucleus boundary.
The [policy checks](verification/policy-parity.json) compare the pinned Dart
encoder and sampler with fixed draws and official-reference model logits.

[Collection receipts](verification/collection-summary.json) record 369,705
main model inference calls across six single-thread CPU workers. Shard elapsed
times sum to 9.90 worker-hours, including contention and overhead; this is not
CPU accounting or end-to-end wall time. Additional work includes the 180
quality-position inferences, 115,361,629 Stockfish nodes, seed reproduction,
parity checks and the tied-cutoff investigation. The run took roughly two
hours including setup and verification. Model weights are not republished.

## Protocol and reproduction

See the [frozen protocol](PROTOCOL.md), [pre-diagnostic addendum](DIAGNOSTIC_ADDENDUM.md)
[supplementary analysis note](ANALYSIS_NOTE.md), [reproduction guide](README.md)
and [file checksums](SHA256SUMS). Research is tracked in
[Preview issue #155](https://github.com/Dash1971/maia-chess-android-preview/issues/155).
