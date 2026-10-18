# Opening variety and Top-P 0.95

**Study in progress.** The fixed primary contrast is complete; control matches,
lower/higher-rating comparisons, opening rollouts and quality diagnostics are
still running. No default recommendation is finalized and no app settings have
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

This establishes a strength gain in this fixed comparison. It does not yet
establish preservation of opening variety, a benefit at other conditioning
ratings, or that this is a better overall default for the intended human-like
playing experience. The remaining prespecified comparisons continue unchanged.

## Protocol and reproduction

See the [frozen protocol](PROTOCOL.md), [pre-diagnostic addendum](DIAGNOSTIC_ADDENDUM.md)
and [reproduction guide](README.md). Research is tracked in
[Preview issue #155](https://github.com/Dash1971/maia-chess-android-preview/issues/155).
