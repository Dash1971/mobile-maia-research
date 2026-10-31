# Method for the generated 10,000-bot catalog

**Status: generated and prepared for deployment, 1 November 2026; activation
pending.** The owner approved a 10,000-identity roster using supported Maia
policies, with new assigned nonprovisional ratings and truthful zero-game
counts. This note records the prepared implementation from
[Mute Chess PR #174](https://github.com/Dash1971/mute-chess/pull/174), pinned to
[commit 7b8f5d4](https://github.com/Dash1971/mute-chess/tree/7b8f5d4625c77a6ff7e30985f6d6b1904cc26a93).
It does not claim a live deployment or create new game evidence.

The earlier smooth formula and illustrative allocation are preserved in the
[historical planning note](PLANNING-APPROXIMATION.md). They are not the method
used to assign this generated roster. The original study's frozen predictor,
training snapshot, predictions, evaluation and game data remain unchanged.

## Reuse the same measured policy

The generator preserves the original 250 reference identities and adds 9,750
new ones. It uses their [recorded settings](data/configurations.json) and
[final native perfs](data/final-native-perfs.json), without fitting another
strength predictor or playing new games.

An effective policy includes equal self/opponent conditioning inputs,
Temperature, Top-P, opening behavior and model-history mode. Both zero
Temperature and zero Top-P select argmax, so their redundant slider values are
canonicalized to the same policy. Full sampling throughout makes an opening
cutoff immaterial. Other opening overrides remain part of the policy.

For policy `p` and speed `s`, the assigned rating is:

```text
R(p, s) = Σ [reference rating(i, s) / RD(i, s)²]
          ──────────────────────────────────────
                    Σ [1 / RD(i, s)²]

The sums include reference accounts i using the same effective policy p.
```

A policy with one reference uses that account's recorded rating. When several
accounts share the policy, inverse-RD-squared weighting supplies a descriptive
central estimate. It does not make those accounts independent replicates or
supply a new confidence interval. The prepared allocation uses 202 distinct
measured policies, with separate Blitz and Rapid estimates for each.

History is retained when matching a measured policy; there is no universal
history bonus or penalty. The earlier compact-formula checks found no useful
predictive improvement from a separate history term, but did not establish
zero causal effect. The [history study](../move-history-2026-10-09/REPORT.md)
remains evidence about prediction and copying behavior, not an equivalence test
of full-game strength.

New identities keep the selected conditioning, sampling, opening and history
settings. Human timing on/off and one of five timing styles are assigned by the
application's existing deterministic identity hash. The calibration games had
added timing waits disabled. Thus the assignment reuses measured move-policy
strength; it does not newly validate every timing personality or clock control.

## Initialization and supported range

The approved new-account policy initializes **RD 100, native default volatility
and zero completed games**. Native Glicko's RD-below-110 criterion makes those
assigned perfs nonprovisional. The choice of RD 100 is an explicit product
initialization policy, not a measured posterior uncertainty for each new
identity. Games and inactivity continue to affect native ratings and RD; no
permanent established flag is imposed.

The existing 250 accounts retain their earned perfs, settings and histories.
The generation does not copy their game counts or RD into the new accounts,
reset existing ratings, or change human initialization and rating semantics.
Native provisioning and the complete per-account data are reviewed in the
pinned application source; this publication audits the saved research inputs
and aggregate allocation, not the live database.

The supported offering is approximately **800–3,000 Blitz and 800–2,800 Rapid**.
New templates whose estimated rating is below 800 in either speed are excluded,
not clipped upward. Preserved references include one Blitz rating below 800.
The prepared roster ranges are:

| Scope | Blitz | Rapid |
| --- | ---: | ---: |
| All 10,000 identities, including preserved references | 771.06–3042.93 | 835.43–2813.15 |
| The 9,750 new assigned identities | 815.95–2756.96 | 835.43–2593.93 |

The strongest tail therefore includes existing earned identities. There is no
rating bonus for character names, and no stretching of the strength scale to
force an endpoint. The earlier lower-edge planning target is retired; this
release offers the supported policy range.

The inherited scale remains approximately anchored to historical Lichess
Maia3-79M accounts. The [anchor record](../bot-strength-seeding-2026-10-31/REPORT.md#why-these-starting-priors-require-a-test)
documents the sampling-policy correction and already-applied 75-point
translation. It must not be applied again. Closed-pool games refine relative
standings but cannot independently remove a shared error in human Lichess
alignment.

## Other speed categories

Bullet starts from the measured Blitz estimate plus a historical
Bullet-minus-Blitz difference from the nearest reliable conditioning family.
Classical uses the corresponding Rapid-to-Classical difference. A reliable
family has established ratings, RD at most 110 and at least 30 games in both
categories. Sparse upper families therefore fall back to a lower reliable
family. The application records the selected reference account for each new
identity.

UltraBullet uses the Blitz proxy and Correspondence the Rapid proxy. These are
explicitly unvalidated transfers, not additional measured calibration or a
claim that every speed has the same population distribution. All new assigned
categories use the owner-approved initialization above; existing unplayed
categories are not reseeded. See the pinned application's
[catalog method](https://github.com/Dash1971/mute-chess/blob/7b8f5d4625c77a6ff7e30985f6d6b1904cc26a93/docs/catalog-roster.md)
and [dated cross-speed references](https://github.com/Dash1971/mute-chess/blob/7b8f5d4625c77a6ff7e30985f6d6b1904cc26a93/docs/data/lichess-maia-adjustment-reference-2026-10-30.json).

## Distribution and reproduction

The allocation uses archived official weekly Lichess
[Blitz](https://lichess.org/stat/rating/distribution/blitz) and
[Rapid](https://lichess.org/stat/rating/distribution/rapid) frequency snapshots
retrieved on **30 October 2026 at 04:46 UTC**. The source has 97 buckets beginning
at rating 400, in steps of 25. The [source record](data/catalog-2026-11-01/distribution-source.json)
identifies the dates, player totals and original HTML hashes; the saved
[Blitz](data/catalog-2026-11-01/distribution-blitz.json) and
[Rapid](data/catalog-2026-11-01/distribution-rapid.json) frequencies make the
allocation calculations reproducible. The live weekly pages will change.

Conditioning each frequency distribution on ratings of 800 or above leaves
704,902 Blitz players and 504,854 Rapid players. The algorithm allocates new
identities to measured **joint Blitz/Rapid policy vectors**, minimizing a greedy
squared cumulative-distribution objective at 1000, 1400, 1800, 2200 and 2600.
Both speeds receive equal weight. A small repeat-count penalty spreads ties
among templates; a public SHA-256 seed order breaks exact ties. This is a
reproducible allocation heuristic, not a claim of globally optimal matching.

The 250 preserved ratings contribute to the achieved distribution. No speed's
rating is reassigned independently just to fit its histogram. The resulting
counts are:

| Band | Blitz | Rapid |
| --- | ---: | ---: |
| Below 1,000, mostly 800–999 | 920 | 1,191 |
| 1,000–1,399 | 3,237 | 3,689 |
| 1,400–1,799 | 3,582 | 3,471 |
| 1,800–2,199 | 1,926 | 1,499 |
| 2,200–2,599 | 320 | 136 |
| 2,600+ | 15 | 14 |
| **Total** | **10,000** | **10,000** |

The maximum cumulative mismatch at those boundaries is **0.00473 percentage
points Blitz** and **0.11940 Rapid**. Retaining all original accounts prevents
an exact match to Rapid's small upper tail. Counts describe this prepared
roster, not 10,000 independent observations or an activated population.

The [application manifest](data/catalog-2026-11-01/catalog-manifest.json) records
template counts, assigned ratings, source policies, both distributions and the
strongest 20 identities in each speed. It is copied byte-for-byte from the
pinned preparation commit. [Source provenance](data/catalog-2026-11-01/source-provenance.json)
records every copied file's SHA-256, the original research input hashes, the
application commit and the complete generated roster's hash. The full identity
list remains in the [application source](https://github.com/Dash1971/mute-chess/blob/7b8f5d4625c77a6ff7e30985f6d6b1904cc26a93/lila-adapter/catalog-roster.json)
rather than being duplicated here.

Run the independent standard-library audit from this study directory:

```sh
python3 tools/audit_catalog_allocation.py
```

It checks source hashes, exact reference-policy means, the lower bound, totals,
per-speed distributions and assigned initialization metadata. It does not
inspect live accounts or independently reimplement the application's complete
identity generation. To reproduce that generator and its identity/personality
checks, use the pinned application source and its documented Node commands.

With the publication's plotting dependencies installed,
`python3 tools/build_reader_figures.py` regenerates the reader figures and
records input hashes in [reader-figure-metrics.json](figures/reader-figure-metrics.json).
The sampling chart still uses the unchanged controlled comparisons in
[reader-chart-sources.json](data/reader-chart-sources.json); its former
illustrative allocation is retained as historical evidence. The scatter plots
use the original native perfs. The color `1 − Temperature × Top-P` describes
settings, not a measured causal effect or the implemented rating rule.

No neural inference, new games, rating writes, runtime deployment or capacity
increase accompanies this research publication. Activation requires the
application's verified-main release and separate live provisioning audit.
