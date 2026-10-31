# How we rate the bots in Mute Chess

![Lichess as the starting reference, games as the test, and Glicko as the rating system.](figures/reader-cover.png)

[Mute Chess](https://mutechess.org) brings Maia opponents into the Lichess playing
experience. Our goal is straightforward: **a rating here should mean roughly
the same playing strength as it does on Lichess**, at the same time control.

Maia's settings let us create many different opponents. This report explains
how we turn those settings into useful ratings—and how that research supports
a much larger bot pool.

## 1. How did we come up with the bot ratings?

**We started with Lichess, then let the bots earn their ratings through games.**

Public Maia3-79M accounts on Lichess supplied our starting reference. We checked
their sampling settings and adjusted the starting estimates to account for
the difference between those settings and ours. The
[source record](../bot-strength-seeding-2026-10-31/REPORT.md#why-these-starting-priors-require-a-test)
documents that reference and adjustment.

We then played **3,449 recorded rated games** across a varied reference roster,
using the **native Lichess Glicko-2 rating system**. Each bot kept its assigned
Maia input, Temperature, Top-P and move-history setting. Games changed their
ratings in the normal way; we retained their existing results and histories.

The result is **250 reference opponents with established ratings in both Blitz
and Rapid**. Their measured ratings cover roughly **800–3,000 in Blitz** and
**800–2,800 in Rapid**. This gives us evidence about actual playing policies,
rather than assuming that Maia's input of “1600” automatically produces a
1600-rated opponent.

## 2. Are they close to Lichess ratings?

**They have a Lichess-based starting anchor, and keeping that correspondence is
a central goal of the site.** The games refine the relative strength of the
opponents around that anchor.

That gives us a reasoned starting point, not a guarantee that a Mute Chess
rating already equals a human's Lichess rating. Some reference bots still have
relatively short histories. Playing only one another also cannot reveal a
shared offset affecting the whole pool.

We will monitor ratings as people play, compare further Lichess evidence as it
becomes available, and document any adjustments. **Established means the native
rating system has enough confidence to remove its provisional mark; ratings
can still change with more games.**

## 3. How do the engine settings affect strength?

**The Maia input sets the broad strength level. Sampling settings can make the
same model considerably stronger.**

| Setting | What it does | What our evidence supports |
| --- | --- | --- |
| **Maia input** | Chooses the level of human play the model tries to imitate. | Higher inputs generally produced stronger opponents. Input and earned rating are different numbers. |
| **Temperature** | Lower values favor the model's most likely moves more strongly. | Lowering it substantially improved results in our controlled comparisons. |
| **Top-P** | Removes unlikely moves from the available choices. | Narrowing the choices improved results, including the small change from 1.00 to 0.95. |
| **Argmax** | Always chooses the most likely legal move. | It was about 320 match-Elo stronger than full sampling in the controlled 1600-input comparison. |
| **Move history** | Gives Maia previous positions as well as the current board. | We found no useful extra rating adjustment for history in the prediction checks, so the simple formula below leaves it out. This does not establish that history can never affect strength. |

![Controlled comparisons: Top-P 0.95 adds about 71 match-Elo, Top-P 0.90 about 131, Temperature 0.50 about 271, and argmax about 318, relative to full sampling in the tested setting.](figures/reader-sampling.png)

These comparisons hold the **79M model and 1600 input fixed**, with history off.
They measure gains against full sampling, not absolute human ratings. The whiskers
show 95% uncertainty intervals. Settings interact: their gains should not be
added together or assumed identical at every Maia input.
[Controlled sampling results](../maia3-sampling/strength.md) ·
[Top-P 0.95 comparison](../maia3-sampling/followup/strength/SUMMARY.md)

Our broader bot pool tests many combinations of these settings. The chart below
shows the resulting native ratings, including the remaining variation between
opponents.

![Higher Maia inputs generally produce higher playing ratings, with a substantial spread from settings and rating uncertainty.](figures/reader-settings.png)

## From this research to a 10,000-bot pool

**We plan to expand the roster to 10,000 identities, each with persistent
settings and an assigned rating calibrated from this reference.** A new name
does not require another tournament to rediscover the strength of an already
measured playing policy.

The plan is to present those calibrated bot ratings without a provisional
starter mark. This is an assignment based on the policy's evidence; it does
not mean that every new identity has already played its own calibration games.
We will preserve that distinction in the data, and games will continue to
update ratings through Glicko. The expanded roster has not been activated yet.

### A simple rating formula

For an already measured policy, its established reference rating is the most
direct starting point. For other combinations, this is a **rough catalog-planning
approximation**, guided by the reference ratings and the controlled sampling
results:

```text
Assigned rating ≈ 1575 + 0.73 × (Maia input − 1600)
                      + 320 × (1 − Temperature³ × Top-P⁵)
```

The first part sets the broad level; the second adds a sampling adjustment
that rises toward 320 as choices become more concentrated. There is no history
bonus or penalty. Blitz and Rapid retain separate reference ratings; the
[method note](CATALOG-METHOD.md) gives the separate-speed versions and derivation.
This smooth approximation is a proposed way to fill gaps between measured
settings, not a new law of chess strength.

For example, at input 1600 it gives approximately **1575 with full sampling**,
**1650 at Temperature 1 / Top-P 0.95**, and **1895 with argmax**. We prefer direct
reference evidence where it is available rather than forcing every bot onto
the same smooth curve.

### A pool shaped like Lichess

Most identities should sit in the busy middle of the rating range, with fewer
at either extreme. The illustration below uses Lichess's weekly Blitz
distribution to propose an allocation—not an equal number of bots at every
Maia input.

![Proposed allocation of 10,000 identities: most around the middle of the Lichess Blitz distribution and a small strong tail.](figures/reader-roster.png)

| Assigned rating band | Proposed identities |
| --- | ---: |
| 600–999 | 1,230 |
| 1,000–1,399 | 3,140 |
| 1,400–1,799 | 3,460 |
| 1,800–2,199 | 1,850 |
| 2,200–2,599 | 310 |
| 2,600–3,000 | 10 |
| **Total** | **10,000** |

This is a rounded planning illustration based on the
[Lichess Blitz distribution](https://lichess.org/stat/rating/distribution/blitz)
observed on October 31, 2026 UTC. It excludes the below-600 share and caps the
top band for the proposed catalog. Rapid needs its own distribution; one
allocation does not reproduce both speed categories.

**The desired range is 600–3,000; the evidence does not yet cover every part of
it equally.** The full-sampling 600-input reference finished around 800–900, and
the smooth formula does not itself reach either target edge. Some measured
Blitz opponents reached roughly 3,000. Extending the roster down to genuine 600-strength opponents needs weaker
playing policies and calibration at that end of the range.

The practical result is a measured reference for a much larger, varied pool,
with ratings that can improve as people play. **The Lichess correspondence
remains the goal throughout.**

---

[Data and reproduction](README.md) · [Catalog formula and chart sources](CATALOG-METHOD.md) ·
[All reference settings](data/configurations.json) · [Earned ratings](data/ratings.csv)

Built on [Lichess/Lila](https://github.com/lichess-org/lila),
[Maia/CSSLab](https://github.com/CSSLab/maia3), and earlier Mobile Maia and
[En Croissant](https://github.com/franciscoBSalgueiro/en-croissant) work.
This is independent project research, not an upstream endorsement.
