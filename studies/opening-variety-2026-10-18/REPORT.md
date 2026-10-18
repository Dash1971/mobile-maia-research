# Opening variety and Top-P 0.95

**Study in progress.** All 3,000 full games are complete; opening rollouts and
the remaining quality diagnostics are still running. No default recommendation is finalized and no app settings have
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

## Completed 1600 quality diagnostic

The first rating's fixed diagnostic is complete: 60 positions, 30 with each
color to move and 20 each at moves 7, 13 and 21. Each legal move's child position
received a fresh 20,000-node Stockfish 18 search, with the terminal-position
exceptions defined in the protocol.

| Diagnostic | A: full sampling | C: Top-P 0.95 after opening |
| --- | ---: | ---: |
| Mean probability of a move >=100 cp below the best evaluated legal move | 23.85% | 22.48% |
| Mean probability of a move >=200 cp below the best evaluated legal move | 8.89% | 7.99% |

The paired difference in the >=200 cp measure is **−0.89 percentage points**,
with 95% bootstrap interval **−1.19 to −0.61 points** across the selected
positions. Expected evaluation loss is lower in 57 positions, higher in two,
and unchanged in one. Lower Top-P does not improve every position.

Six positions include mate-valued branches. Mapping these scores to roughly
±32,000 cp greatly inflates the mean expected-loss values (597.75 to 571.52 cp);
these are not typical game losses or a calibrated blunder rate. Fixed shallow
search, selected positions and the research evaluator's version also limit
generalization. B and C have the same distribution on these post-override
positions, so this diagnostic isolates the later Top-P change, not the effect
of the opening override itself.

See the [cached diagnostic summary](verification/fixed-quality-1600-preview.json)
and [per-position/move data](data/quality.jsonl). The full three-rating diagnostic
and audit remain pending.

## Protocol and reproduction

See the [frozen protocol](PROTOCOL.md), [pre-diagnostic addendum](DIAGNOSTIC_ADDENDUM.md)
and [reproduction guide](README.md). Research is tracked in
[Preview issue #155](https://github.com/Dash1971/maia-chess-android-preview/issues/155).
