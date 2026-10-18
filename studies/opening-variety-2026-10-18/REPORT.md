# Opening variety and Top-P 0.95

**Study in progress.** All 3,000 full games and the 180-position quality
diagnostic are complete; opening rollouts are still running. No default
recommendation is finalized and no app settings have
changed. This draft will be replaced by the full report after the fixed design
and independent checks finish.

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
115 million Stockfish nodes. The final independent cached audit remains pending.

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
and a 5M-model check, used 2,000 opening samples through eight full moves, and
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

## Protocol and reproduction

See the [frozen protocol](PROTOCOL.md), [pre-diagnostic addendum](DIAGNOSTIC_ADDENDUM.md)
and [reproduction guide](README.md). Research is tracked in
[Preview issue #155](https://github.com/Dash1971/maia-chess-android-preview/issues/155).
