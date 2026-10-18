# Supplementary opening-label resolution check

Added after inspecting the completed 1600 opening sample (1,000 rollouts per
arm), while the fixed lower/higher-rating collection continued. The full
match results and quality diagnostic were also known. No lower/higher-rating
opening diversity results were inspected to choose this check.

The prespecified carried-family C/A ratio was exactly 1, with a paired
bootstrap interval of [1, 1]. Broad family labels agreed for every matched
A/C rollout even though only 71 of 1,000 complete move sequences agreed.
This exposes a resolution limit: an early broad label can remain unchanged
after the policy switch and after a line leaves the opening database.

Keep the original family metric, bootstrap, practical reference and all
recorded runs unchanged. Add **supplementary, post hoc** comparisons using
the same table's finer ECO codes, with the same last-recognized-label carry
rule, equal rollout counts and 2,000 paired bootstrap replicates (seed
48,000,100,000 plus rating). Also report matched prefix agreement at the
prespecified depths and first-divergence counts. These are resolution and
policy-change diagnostics, not replacement success criteria or measures of
human-move fidelity. Divergence between paired paths does not itself imply
reduced population diversity.

A degenerate interval for a coarse label must not be presented as certainty
that later variations or the complete human-like move distribution are
preserved. No additional games, seeds or model inference are selected by this
analysis.

The finer 1600 ECO result was also insensitive: 999 of 1,000 paired final
codes agreed, and both arms had 117 distinct codes with identical effective
counts. Record exact opening-table matches at each depth and rollouts with
any match after ply 10 as a further descriptive coverage check. This exposes
the effect of carrying an early label after leaving the database; it is not
an additional success criterion. The pinned table has 3,810 rows and includes
lines beyond move 10, so its input is not deliberately truncated at the
override boundary.
