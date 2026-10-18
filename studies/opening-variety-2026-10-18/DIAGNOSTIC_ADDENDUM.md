# Pre-diagnostic sampling addendum

The original protocol's first-eligible scan of plies 12, 24 and 40 would select
ply 12 whenever it could select any position. That would concentrate the quality
diagnostic at the start of move 7 rather than cover later play.

This addendum is committed before any Stockfish diagnostic runs or match-result
analysis. Only completion counts, an early rule-replay receipt and mean game
length were inspected; no W/D/L totals, profile scores or opening metrics were
examined to choose this change. It does not change the match or opening design,
their sample sizes, seeds, primary contrast or the statistical decision criteria.

Replace the position-selection sentence with:

For each rating, traverse C–A games in game-index order. A reverse-color pair's
base ply is **(12, 24, 40)[pair index modulo 3]**. Add **pair index modulo 2**
to that base so positions alternate between White and Black to move. Select the first game in that
pair that has a nonterminal position at the target ply and at least one later
move. Take at most one position per pair, stopping at 60 positions per rating.
If a pair ends too early in both games, skip it rather than substitute a shorter
ply. Record any shortfall rather than change the budget. The positions need not
be exactly balanced across target plies because some games end before the target.

The target plies are 12/13, 24/25 and 40/41: moves 7, 13 and 21 for either
color, all after the opening override has ended. Record the realized color
counts as well as ply counts. Each
selected FEN is evaluated for every legal move using the already pinned engine
and 20,000-node budget. All other diagnostic metrics, bootstrap settings and
limitations in the original protocol remain unchanged. Record this addendum's
SHA-256 in the diagnostic input manifest.
