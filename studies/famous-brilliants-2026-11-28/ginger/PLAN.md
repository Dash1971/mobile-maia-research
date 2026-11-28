# Ginger comparison — sample fixed before analysis

Goal: check whether Open Brilly Finder recovers more Chess.com Brilliant moves
on games outside its published development data.

## Sample

Start at [Ginger_GM's Brilliant Moves gallery](https://www.chess.com/member/Ginger_GM/stats/all-brilliant-moves),
with its displayed 90-day range, on November 28, 2026. The page reports 168
Brilliant moves. Take its first 30 distinct games in display order, retaining
all gallery cards for each of those games. This gives 36 reference moves.
Selection is fixed before running either Mobile Maia detector.

Exclude any selected game appearing in the pinned public development gallery
or candidate table. Also exclude the entire game if **any** of its mainline
position-and-move pairs matches any published candidate row, including
training and held-out rows. Normalize away move counters and non-capturable
en-passant targets. Do not replace excluded games.

This removes three games because of repeated opening positions and moves,
leaving **27 games, 32 gallery Brilliants, and 1,837 mainline moves**, dated
November 5–27, 2026. No selected game appears in the original development
collection; no position-and-move pair in the retained games appears in the
published candidate table. Ginger_GM does not appear as either player in the
original 7,019-game gallery collection. These statements concern the public
corpus at the pinned source commit, not unknown or unpublished data.

- [Original 30-game selection](gallery-selection.json)
- [All overlap results, exclusions and source hashes](overlap-audit.json)
- [Eligible games and reference moves](games.json)
- [Legal, unannotated PGN sample](games.pgn)

The access probe, game 188137226842, is not in the sample. Signed-in Game
Review access was verified on that game before selection. It showed no
Brilliant moves for either side. No account settings were changed.

## Comparison protocol

Use the same app, engine, model, cutoff and Fast-analysis configuration as
the preceding online comparison:

- App: 096591bd8d42759e5a3f3a288d56d7c93245d6d1.
- Model source: open-brilly-finder at
  59cab58a8b63387d9775252f03a6875fe451f697.
- Model SHA-256:
  992a792a646b11e612486c4fe26796fc38ee47f395f2220b00d26db65ba1e27d.
- Cutoff: 0.8193002847777424, unchanged.
- Stockfish 18, Fast, depth 12 / 500 ms, one thread, 64 MiB hash,
  two root lines; fresh engine/session per game. Retain the ordinary six-search-unit
  confirmation policy for each detector. Feed identical baseline searches to both.
- Analyze every mainline position. Primary scoring counts only Ginger's moves.
  Report matching gallery Brilliants, misses, total awards and awards outside
  the gallery labels, overall and per game. Retain every disagreement.
- Do not tune the model, cutoff, sample or confirmation policy after seeing results.

The reference is the gallery snapshot. A fresh Game Review may disagree with
it; record any later review labels separately rather than silently replacing
the frozen gallery labels. Gallery-only evaluation measures recovery of those
labels. An award outside the gallery is a disagreement, not proof of a false
positive. This selected set cannot estimate precision across ordinary games
or all players.

No classifier comparison has been run for this sample yet. No Android builds,
GitHub Actions, LFS downloads, model downloads or retraining are required for
sample preparation. The overlap check reads ordinary public Git blobs and
Chess.com's unauthenticated public November archive.

## Reproduction

`tools/prepare_ginger.py` reads the frozen gallery selection plus a task-owned
scratch directory containing the source files named in `overlap-audit.json`:
`candidates.csv.gz`, `ginger-november.json`, and `sources.json`. It downloads
the pinned development gallery as an ordinary Git blob if absent, audits every
mainline move, and writes the selected PGN, game metadata and audit. It needs
Python and python-chess, and never accesses browser credentials.
