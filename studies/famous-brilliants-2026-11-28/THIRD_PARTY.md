# Source and artwork notices

The frozen sources and public game scores are recorded with this study's data and methods. Published annotation symbols are observations of the chosen source, not new ownership claims over those sources. No copyrighted annotation prose, source-page screenshots or model weights are incorporated into the diagrams.

## Cburnett pieces

The twelve `artwork/*.webp` files are Cburnett by Colin M. L. Burnett, licensed under **GPL-2.0-or-later**. These are unchanged 2× WebP assets from the pinned [Mobile Maia chessground copy](https://github.com/Dash1971/maia-chess-android-preview/tree/04e903b1e4abe635d2168d01b027ecc24f240651/third_party/chessground/assets/piece_sets/cburnett/2.0x). The [Lichess copying notice](https://github.com/Dash1971/maia-chess-android-preview/blob/04e903b1e4abe635d2168d01b027ecc24f240651/third_party/chessground/notices/lila-COPYING.md) identifies this set's author and license; preferred SVG originals are available in the [Lichess Cburnett source directory](https://github.com/lichess-org/lila/tree/master/public/piece/cburnett).

`tools/draw_figures.py` resizes and arranges those assets over board squares, adds coordinate labels and a move arrow, and renders actual before/after positions from the frozen PGN scores. Its source is included. The hero is the actual Opera Game position before 16.Qb8+, with a move arrow. Classical diagrams identify the published `!!` moves; the two online illustrations explicitly distinguish recorded Chess.com review labels from the measured Mobile Maia awards.

## Online game records and labels

The 42 online scores and recorded labels are factual research excerpts from
the pinned [Open Brilly Finder collection](https://github.com/Dash1971/open-brilly-finder/tree/59cab58a8b63387d9775252f03a6875fe451f697).
`online/source-receipts.json` records the exact source paths, sizes and hashes.
The PGNs contain legal game moves and observed annotation symbols, without
copied third-party commentary. Player identities and links identify the public
games; they do not imply player endorsement of Mobile Maia or the study.

Piece artwork and the PNG diagrams retain GPL-2.0-or-later. See [GPL-2.0.txt](GPL-2.0.txt). Original report text and rendering tool code retain the repository's AGPL-3.0-only license. The renderer uses normal host fonts where available, with Pillow's bundled fallback; no font binaries or Python environments are redistributed.
