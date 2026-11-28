# Online-game comparison — fixed before analysis

Goal: test whether Open Brilly Finder helps Mobile Maia recognize more
Brilliant moves than its existing En Croissant-derived rules in online games.

The earlier nine-game classics study remains unchanged. This extension adds
42 games from the pinned Open Brilly Finder public collection: six each from
hansen, KNVB, nelsi, GothamChess, Hikaru, MagnusCarlsen and Witty_Alien.

## Selection

Use the fully recorded November 22 Chess.com reviews. Require a legal game,
complete per-move review labels, and matching moves; resolve a missing promotion
suffix in the review table only from the legal PGN. Restrict Witty_Alien to
games in the upstream held-out outcome table. Within each account, select the
six lowest SHA-256 values of `mobile-maia-online-brilliant-27-v1:` plus the
numeric game ID. `selection.json` records the exact sample and exclusions.
Do not filter by the Mobile Maia classifier results or substitute games later.

## Comparison

- Analyze every mainline position afresh using the same pinned Mobile Maia
  analyzer and two classifiers used in the classics study.
- Prespecified mode: Fast, Stockfish 18, depth 12 / 500 ms, one thread,
  64 MiB hash, two root lines. Start a fresh engine/session per game.
- Feed identical baseline scores to both classifiers. Each keeps its ordinary
  evidence checks and six-search-unit confirmation budget. Do not change the
  model, cutoff, grading precedence or confirmation policy.
- Primary scoring: **only the selected account's moves**, against its recorded
  November 22 Chess.com Game Review labels. Report total Brilliant awards,
  matching Brilliant labels, misses and awards outside those labels, both
  overall and by account. Report gallery-label agreement separately.
- Show all game-level results and added/withdrawn awards. Choose two Chessbrah
  illustrations from the completed sample, clearly as illustrations rather
  than additional tests; prioritize newly recovered reference Brilliants.

## Interpretation

These games were collected because their accounts had gallery Brilliants. All
seven accounts are titled players. Six accounts were development accounts for
the published model, and other Witty_Alien games were used in training. The
sample is a deployment comparison, not an independent generalization test,
a random sample of ordinary players, or a population accuracy estimate.

An award outside the recorded labels is a disagreement, not automatically a
bad chess move. Report it beside the recovered labels; more badges alone are
not evidence of better recognition. Keep the classics' Evergreen regression
visible. A release decision may accept that trade-off, but cannot erase it.

No Android builds, Android Actions, LFS downloads or model training. Website
publication uses its existing web-only Pages workflow. Retain raw evidence,
legal PGNs, immutable pins and reproduction tools in the research repository.
