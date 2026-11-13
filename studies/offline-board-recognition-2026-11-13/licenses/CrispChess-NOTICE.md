# CrispChess diagram recognition attribution

Only the MIT screenshot/diagram model and adapted diagram preprocessing/decoding are included. No physical-board photo classifiers, engines, fonts or training images are included.

Source: https://github.com/CrispStrobe/CrispChess/tree/0d01798daf9661076675f8505b4cc6995a6529da

The following upstream training-source attribution is preserved verbatim:

## Piece themes

Piece SVG themes are from [Lichess](https://github.com/lichess-org/lila):

| Theme | Author | License |
|-------|--------|---------|
| Chessnut | [Alexis Luengas](https://github.com/LexLuengas/chessnut-pieces) | Apache-2.0 |
| Rhosgfx | [RhosGFX](https://rhosgfx.itch.io/) | CC0 1.0 |
| Fantasy | [Maurizio Monge](https://github.com/maurimo/chess-art) | MIT |
| Spatial | [Maurizio Monge](https://github.com/maurimo/chess-art) | MIT |
| Celtic | [Maurizio Monge](https://github.com/maurimo/chess-art) | MIT |
| Kiwen Suwi | [neverRare](https://github.com/neverRare) | CC BY 4.0 |
| Totoy | Kosal Sen | CC BY 4.0 |
| Papercut | [Nikolay Anzarov](https://nikoichu.itch.io/) | CC BY 4.0 |

Authors and licences as listed in Lichess's
[COPYING.md](https://github.com/lichess-org/lila/blob/master/COPYING.md).

## Board-scanning model

`assets/models/board_squares.onnx` was trained for this app from scratch
(`tool/board_vision/`) and is MIT like the app. Its training images are
synthetic, rendered from permissively licensed sources only — no copyleft,
share-alike or non-commercial source, no photographs or third-party datasets:

| Source | Author | Licence |
|--------|--------|---------|
| the eight piece themes above | as above | as above |
| [Firi](https://github.com/jfaure/Firi-pieceset) pieces | James Faure | CC BY 4.0 |
| DejaVu Sans / Serif (chess glyphs, labels) | DejaVu fonts team, Bitstream | Bitstream Vera licence |
| [Noto Sans Symbols 2](https://github.com/notofonts/symbols) | The Noto Project Authors | SIL OFL 1.1 |
| [JuliaMono](https://github.com/cormullion/juliamono) | The JuliaMono Project Authors | SIL OFL 1.1 |
| [Fairfax HD](https://github.com/kreativekorp/open-relay) | Kreative Software | SIL OFL 1.1 |
| [GNU Unifont](https://unifoundry.com/unifont/) 15.1.05 | Roman Czyborra, Paul Hardy et al. | SIL OFL 1.1 (upstream dual licence; the OFL option is used) |
