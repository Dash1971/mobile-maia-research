# Maia expected-score reliability: preregistered lightweight protocol

Dated 27 October 2026, before inference on the study sample. The earlier Rd1
example is already known and is not part of the random sample.

## Questions and scope

1. Do predicted expected game scores agree with recorded human results?
2. Do parent scores agree with the policy-weighted scores of every legal child?

Model: bundled Maia-3 79M ONNX, SHA-256
`3454b03ae78baa64a87b345fdb1a457265d912caec531039b074f07eda0d8010`.
Value channels are loss/draw/win for the side to move. Score is
`P(win) + 0.5 P(draw)`, complemented on Black's turn to express White's score.
Both Elo inputs are fixed to the tested rating, 1600 or 2600. History on is
primary; history off is a paired sensitivity for human-outcome prediction only.
Use actual eight-position history, each board oriented for its own side to move,
and append each candidate child before rebuilding its history tensor.

## Source and selection, fixed before seeing predictions

Use the existing ALLIE 2022 annotated blitz file at Hugging Face dataset
`yimingzhang/allie-data`, revision `990f79105b1f08a8fd367fcb10c5e18c69436e30`,
`lichess-2022-blitz-test/2022-test-annotated.jsonl`, SHA-256
`a6014de8ef861b2ee23a84d7ce824e644390577a000350fad06bd995bcddab0d`.
Do not download additional games or widen bands based on results.

Targets: 500 distinct games with both ratings in [1500,1700], and 250
with both in [2500,2700]. These are approximate online-blitz cohorts, not FIDE
ratings or exact equal-rated samples. Include only rated blitz, Normal or Time forfeit
termination, standard-start games, known result, valid nonnegative per-move
seconds, and replayable legal moves. Deduplicate by game ID and exact move
sequence before selection. Reject contradictions between an automatic final
board result and the supplied game result. Resignations need not end in mate.
Report attrition, actual rating ranges, time controls, side-to-move and stage
counts. If eligibility leaves fewer than a target, use all and report shortage.

Reconstruct clocks from base time, move seconds and increments. A position is
eligible from full move 11 onwards, before an actually recorded move, nonterminal,
and before the first occasion that either pre-move clock or the mover's
post-think/pre-increment clock is below 30 seconds. This filters the sampled
position, not all future time pressure. Never use future moves in model inputs.

Choose games by ascending SHA-256 of `2026102701|game|<game-id>`, then one
eligible position per selected game by ascending hash of
`2026102701|position|<game-id>|<zero-based-ply>`. This yields one observation
per game without selecting on model scores or results. Use final White result
as 1, 0.5, or 0. Calibration applies to this source/selection, not all chess.

## Human-result metrics

Primary history-on, separate by target rating:
- Calibration in fixed score bins [0,.2), [.2,.4), [.4,.6), [.6,.8), [.8,1].
  Plot actual mean prediction against actual mean result, with game counts and
  95% bootstrap intervals. Mark bins with fewer than 30 games as sparse.
- Mean squared prediction error, compared with the same games' constant-0.5
  baseline (draws therefore contribute zero to that baseline's error).
- Mean prediction minus mean result (White-score bias).

5,000 game bootstrap replicates, seed 2026102702; use paired resampling for
prediction-minus-result, MSE-minus-baseline and history-on-minus-off error.
Bin intervals resample games within fixed bins; show observed-result and
calibration-gap intervals. These are descriptive, not a multiple-testing
significance exercise. Treat the percent reduction in MSE as a descriptive
comparison, not an accuracy percentage. Do not label expected-score MSE as
binary-win accuracy or multiclass WDL Brier score.

Repeat the same games/positions with history off and report paired differences.
Also report history-on MSE/bias/calibration for Normal-ending games only, as a
secondary sensitivity; never substitute this for the primary all-outcome sample.
Do not select a preferred setting solely from isolated significant-looking bins.
No fitting, recalibration, Stockfish tournament or parameter sweep.

## Internal consistency

Select 50 positions per cohort from the primary sample by ascending SHA-256 of
`2026102703|consistency|<game-id>` (or all if fewer). Evaluate all 100 identical
positions at both 1600 and 2600 with history on. Full legal softmax, equivalent
to T=1/Top-P=1; no truncated candidates. Child values use White's perspective;
terminal children use the actual result, with raw model value retained separately.

Residual = sum(policy probability * child White score) - parent White score.
Report signed mean, median absolute gap, 90th-percentile absolute gap, and
fractions above 5/10 percentage points. Include 95% bootstrap intervals, seeded
2026102704, resampling within source cohort to preserve the designed 50/50 mix.
Also tabulate each source cohort. These are local self-consistency diagnostics,
not evidence that the weighted value is the correct real-world forecast.

## Interpretation, verification and publication

Check every policy sums to one, legal candidate coverage, Black perspective,
terminal handling, and exact history-window construction. Reproduce the known
Rd1 parent/child scores as a sanity check but exclude it from headline results.
An independent reviewer checks metrics against recorded rows. Retain data/model/
script hashes, package versions, selection IDs, compact per-position outputs and
all child probabilities/values. No model weights, credentials or private paths.

Use ordinary CPU inference; no app edits, APK builds or CI. Publish only in
`Dash1971/mobile-maia-research`: a short plain-language report, two main
calibration charts, consistency summary, reproducible scripts and compact data.
State training-period/source-overlap limits, approximate rating match, sample
uncertainty and limited generalizability. Do not turn two diagnostics into an
invented overall trust score. Clean task-owned environment/bulk files after
verification, preserving compact results and shared models.

## Pre-inference amendment (27 October 2026)

An independent source review found only 228 Normal-ending games near 2600, versus
305 when time forfeits are included, before position eligibility. Before selecting
positions or running predictions, include both Normal and Time forfeit results.
This also avoids conditioning the primary sample on a future ending: the clock
filter applies at the sampled position, and later flag losses are human outcomes.
Keep Normal-only results as a sensitivity. No band widening or additional games.
Game bootstrap treats distinct games as sampling units; repeat-player dependence
cannot be assessed because the source omits player identities.
