> **Historical planning note.** This is the earlier 1 November proposal, preserved
> for its derivation and numerical checks. The prepared catalog instead uses
> [exact measured-policy reuse](CATALOG-METHOD.md), with a supported offering
> beginning around 800. Its old allocation and lower-edge target below are
> historical choices, not the current roster or an activation record.

# A compact approximation for the planned bot catalog

**Status: posthoc catalog-planning method, 1 November 2026.** This note explains
a proposed approximation for assigning ratings to a future catalog of 10,000
bots. It does not replace the original frozen predictor or change any recorded
games, earned ratings, rating deviations or account histories.

## The proposed approximation

Let **C** be the shared self/opponent conditioning input, **T** Temperature and
**P** Top-P. For a compact catalog estimate, use:

```text
Assigned rating ≈ 1575 + 0.73 × (C − 1600) + 320 × (1 − T³ × P⁵)
```

The first two terms describe the broad relationship between conditioning and
the reference ratings. The last term is a smooth approximation to the strength
benefit of concentrating move choices. Either T = 0 or P = 0 gives the same
320-point contribution, consistent with those settings selecting argmax after
the opening override. This is a practical approximation, **not a universal Elo
law** or evidence that the effects of separate controls can be added.

The supported reference domain is Maia3-79M, equal self/opponent conditioning
inputs from 600 to 2600, and T/P from 0 to 1. The recorded policies generally use
full sampling for the first five full moves, followed by the assigned settings;
full sampling throughout is equivalent regardless of that cutoff. The equation
averages over the reference set's recorded history modes. It should not be
extended to other checkpoints, different opening rules, independent opponent
conditioning, or other speed categories without evidence.

## Where the sampling curve comes from

The constants 320, 3 and 5 were chosen for this approximation to roughly follow
earlier controlled sampling results. They are **design constants**, not
parameters fitted by the script to the current reference ratings. These earlier
comparisons used the same 79M model, both conditioning inputs at 1600 and model
history off. All numbers below compare against full sampling, T = 1 / P = 1.

| Setting | Measured relative matchup Elo, 95% interval | Approximation's contribution |
| --- | ---: | ---: |
| T = 1, P = 0.95 | +71.0 [52.2, 90.3] | +72.4 |
| T = 0.5, P = 1 | +271.4 [226.7, 322.7] | +280.0 |
| T = 1, P = 0.9 | +130.9 [92.5, 171.3] | +131.0 |
| Argmax | +317.8 [284.9, 354.5] | +320.0 |

The 0.95 result is the 1,200-game follow-up's primary actual-app-draw endpoint:
[follow-up summary](../maia3-sampling/followup/strength/SUMMARY.md) and
[recorded primary results](../maia3-sampling/followup/strength/results-primary.json).
The other three figures use the earlier study's standard prospective-claim draw
endpoint: [primary and single-control results](../maia3-sampling/strength.md).
They are different experiments and are not pooled into a common estimate.
Their paired draw-rule sensitivities retain the same broad conclusions.

These are relative performance differences against a particular opponent under
fixed conditions. They do not establish absolute human Lichess ratings or a
constant bonus at every conditioning input. In particular, extending one smooth
curve over the whole catalog is a modeling choice. For another measured check,
T = 0.5 / P = 0.9 gained 268.4 points [235.4, 303.6] in the earlier standard-rule
comparison; the curve gives 296.4. Its convenience comes with approximation
error.

The [opening study](../opening-variety-2026-10-18/REPORT.md) separately measured
+75.3 points [47.2, 104.4] for full sampling through the first five moves followed
by T = 1 / P = 0.95, against full sampling throughout, at conditioning 1600.
Its comparisons did not establish a strength gain from the opening override
itself, nor equivalence with continuously using 0.95.

## Fitting the conditioning baseline

The supporting calculation uses the original split in
[original-design-manifest.json](data/original-design-manifest.json), the settings
in [configurations.json](data/configurations.json), and only the original 200
training identities' labels in
[frozen-training-perfs.json](data/frozen-training-perfs.json).
For each speed, it subtracts the fixed sampling contribution and fits an affine
conditioning baseline by weighted least squares. Weights are
`1 / (RD² + 50²)`, retaining the original predictor's weighting convention.

This gives:

```text
Blitz ≈ 1576.11468 + 0.74776429 × (C − 1600) + 320 × (1 − T³ × P⁵)
Rapid ≈ 1570.94885 + 0.71459805 × (C − 1600) + 320 × (1 − T³ × P⁵)
```

The public equation uses convenient rounded midpoints of those two baseline
fits. It is a shared catalog estimate; the reference accounts still have
separate earned Blitz and Rapid ratings.

Five deterministic cross-validation folds group equivalent conditioning,
sampling and opening configurations. History-on/off counterparts remain in the
same fold. The baseline is refitted within each fold; the sampling curve stays
fixed. No candidate curves or exponents are selected by this script.

| Descriptive check, rating points | Blitz | Rapid |
| --- | ---: | ---: |
| Training mean absolute error, separate speed fits | 99.4 | 95.8 |
| Training grouped cross-validation mean absolute error | 100.3 | 96.3 |
| Comparison with final ratings of the 50 known held-out configurations | 102.9 | 118.1 |
| Same comparison for the rounded shared equation | 102.0 | 118.2 |

The last two rows use [final-native-perfs.json](data/final-native-perfs.json)
**after fitting**. This is a posthoc comparison with already-known
configurations, not a fresh blind test. The equation was developed after the
studies; neither these figures nor the training cross-validation turn it into
the original prospective predictor. The original
[predictor](tools/predictor_v2.py), [saved predictions](data/frozen-predictions-v2.csv)
and [evaluation](data/evaluation.json) remain separate evidence.

The labels themselves are uncertain native Glicko-2 estimates and share the
pool's inherited anchor. The generated accounts also started from a heuristic
that already combined conditioning and sampling settings. Consequently, a good
fit to these labels is not independent proof of the true effects of every
setting. The calculations do not supply per-bot confidence bounds or establish
that the new approximation is superior to the original model.

## Why history has no separate term

We omit history from the catalog approximation as a simplifying design choice.
Adding one history term to the same fixed-curve model gives descriptive
coefficients of approximately +2 points in Blitz and +19 in Rapid. Grouped
training cross-validation error changes from 100.33 to 100.56 in Blitz and
96.29 to 96.36 in Rapid. Thus this particular predictive check gives no useful
improvement from including history.

This is **not proof of zero effect**, an equivalence test, or a causal estimate.
The earlier [history study](../move-history-2026-10-09/REPORT.md) measured better
human-move prediction and increased copying on a particular opening path; it
explicitly did not establish a full-game Elo change. Omitting a term here does
not erase those behavioral findings or establish that history is irrelevant to
every policy.

## Assigned ratings, coverage and Lichess comparison

The planned 10,000-bot catalog would use **assigned nonprovisional catalog
ratings** as a future product policy. That would make the displayed catalog
labels available without a separate tournament for every new name. It would
not transfer another account's earned game count, low RD or native established
status. No account flags, rating records or production behavior are changed by
this note or its script.

The inherited rating scale is approximately tied to historical Lichess
Maia3-79M accounts. The [anchor provenance](../bot-strength-seeding-2026-10-31/REPORT.md#why-these-starting-priors-require-a-test)
records the reference sampling-policy correction and the already-applied
75-point adjustment. Do not subtract that adjustment again from earned labels.
Bot-only games improve relative standings within the pool, but cannot by
themselves establish exact agreement with human Lichess ratings. Native
nonprovisional status also does not guarantee a permanently stable rating or a
particular error bound.

The current 250-reference set spans **771–3043 Blitz** and **835–2813 Rapid**.
The rounded equation gives **845 at C = 600 with full sampling**, and **2625 at
C = 2600 with argmax**. Individual observed ratings extend beyond those fitted
central estimates. A desired catalog range of roughly **600–3000** is therefore
a coverage target, not a demonstrated pair of equation endpoints. The lowest
target band remains to be calibrated; stretching the equation to force those
edges would also change its relationship to the inherited rating scale.

The reference roster was deliberately designed, not sampled from a future
population of 10,000 bots. It therefore does not determine the number of catalog
bots in each rating band. Any proposed allocation should be labeled as a
product choice and shown separately from a histogram of measured reference
ratings.

## Distribution source and reproduction

The [reader chart source record](data/reader-chart-sources.json) preserves the
rounded cumulative percentages transcribed from the official
[Lichess weekly Blitz distribution](https://lichess.org/stat/rating/distribution/blitz),
observed on 31 October 2026 UTC. The page reported 731,403 weekly players. Its
visible tooltips gave shares below ratings 600, 1000, 1400, 1800, 2200 and 2600
of 0.8%, 13.0%, 44.1%, 78.4%, 96.8% and 99.9%, respectively. These are saved
rounded observations, not a downloaded raw histogram; the live weekly page
will change. Reconstruction from the saved values is reproducible, while an
independent recovery of the exact historical page is not supplied here.

Subtracting adjacent cumulative percentages, with 100% as the final endpoint,
gives band shares of 12.2%, 31.1%, 34.3%, 18.4%, 3.1% and 0.1%. Excluding the
below-600 share leaves a **99.2% normalization denominator**. Allocate 1,000
units of ten identities in proportion to those shares: take each whole-unit
floor, then give the remaining units to the largest fractional remainders.
This yields **1,230, 3,140, 3,460, 1,850, 310 and 10** identities, totaling
10,000. Equal remainders retain ascending band order.

The final source share is open-ended at 2600 and above. Assigning it to the
catalog's 2600–3000 band is a planning cap, not a measurement that nobody lies
above 3000. The allocation describes a proposed catalog, not measured bot
counts or an activated roster, and a Rapid allocation requires its own source.

[The historical reader figure generator](https://github.com/Dash1971/mobile-maia-research/blob/d12f93536442c636d56ec23313e89807a2771467/studies/bot-rating-establishment-2026-10-31/tools/build_reader_figures.py) reconstructs this
largest-remainder allocation, checks it against the saved counts, and records
input hashes in the [historical reader-figure-metrics.json](https://github.com/Dash1971/mobile-maia-research/blob/d12f93536442c636d56ec23313e89807a2771467/studies/bot-rating-establishment-2026-10-31/figures/reader-figure-metrics.json).
To reproduce that former chart, use the study directory at commit
`d12f93536442c636d56ec23313e89807a2771467`, install its plotting dependencies,
and run `python3 tools/build_reader_figures.py` there. The current generator
instead renders the generated catalog described in [CATALOG-METHOD.md](CATALOG-METHOD.md). The sampling
chart's source values and distinct draw endpoints are retained in the same
reader chart source record. The scatter plots use the unchanged final native
ratings and conditioning settings; every reference uses equal self/opponent
conditioning inputs. Its color scale, `1 − Temperature × Top-P`, is a descriptive
settings indicator, not the catalog formula's sampling adjustment or a measured
causal effect.

## Reproduce the calculation

From this study directory, with Python 3 and its standard library:

```sh
python3 tools/public_rating_approximation.py
```

The script prints the coefficients, descriptive checks, history sensitivity,
observed ranges and input SHA-256 hashes as JSON. Optionally save a **new** file:

```sh
python3 tools/public_rating_approximation.py --output catalog-approximation-audit.json
```

An existing output file is not overwritten. The script reads published data
only; it needs no model weights, dependencies, network access, inference or new
games. It does not modify its inputs or any original prediction artifacts.
