# Ginger analysis-mode follow-up — November 28, 2026

Validate the same 27-game Ginger sample in Balanced and Thorough, using the
actual Mobile Maia analyzer and classifiers. Keep all 32 captured gallery
labels, all 922 Ginger moves, the original exclusion audit, model and cutoff.
The sample was frozen before the original Fast comparison at
`6844202bf606211c11a27b777560cf009293f30f`.

Use the unchanged application implementation at
`096591bd8d42759e5a3f3a288d56d7c93245d6d1` and its existing native study runner.
Balanced requests depth 14 / 1,000 ms; Thorough depth 16 / 1,500 ms. Each search
uses one thread, 64 MiB hash and MultiPV 2. Normal within-session hash reuse,
previous-iteration checks, deeper confirmations and six-search-unit budget stay
unchanged. Both classifiers receive the same baseline evidence for each mode.
No depth floor, forced hash clearing, MultiPV change, retraining or cutoff tuning.

Retain the previously published Fast run as the baseline; do not substitute a
fresh favorable run. Count final awards on Ginger's moves only, gallery matches,
awards outside the gallery, and labels gained/lost. Compare baseline model scores
on the common captured targets, record completed search depths and confirmation
usage, and inspect any unconfirmed Brilliant left outside the confirmation budget.

Run sequentially on desktop Stockfish 18 with the same pinned binary as Fast.
The harness now permits 120 minutes and can resume completed game/mode
checkpoints only after checking matching source/model/engine provenance. These
are operational harness changes, not changes to engine or classification policy.

This extends a selected brilliants sample. It tests mode behavior and recovery
of the frozen labels; it does not establish precision across ordinary games,
calibrate the model score or measure Android performance. No Android builds,
GitHub Actions, LFS downloads or website deployment.
