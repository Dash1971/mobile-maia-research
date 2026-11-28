"""Render actual frozen chess positions; no classifier results are read.

SPDX-License-Identifier: AGPL-3.0-only
draw_pair() is also usable for extra-award review cases. The caller supplies the
caption; the renderer never assigns or infers a model grade.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import unicodedata

import chess
from PIL import Image, ImageDraw, ImageFont, PngImagePlugin

STUDY = Path(__file__).resolve().parents[1]
ARTWORK = STUDY / 'artwork'
FIGURES = STUDY / 'figures'
NAVY = '#152f50'
BLUE = '#315f9f'
INK = '#172f4c'
MUTED = '#506079'
PAPER = '#f6f8fb'
LIGHT = '#f0d9b5'
DARK = '#b58863'

SHORT_NAMES = {
    'opera-1858': 'The Opera Game',
    'byrne-fischer-1956': 'Byrne - Fischer',
    'immortal-1851': 'The Immortal Game',
    'evergreen-1852': 'The Evergreen Game',
    'rotlewi-rubinstein-1907': 'Rotlewi - Rubinstein',
    'levitsky-marshall-1912': 'Levitsky - Marshall',
    'lasker-thomas-1912': 'Lasker - Thomas',
    'kasparov-topalov-1999': 'Kasparov - Topalov',
    'short-timman-1991': 'Short - Timman',
}


def ascii_text(value: str) -> str:
    replacements = {'\u2013': '-', '\u2014': '-', '\u2019': "'", '\u2018': "'", '\u2192': '->', '\u2026': '...'}
    for before, after in replacements.items():
        value = value.replace(before, after)
    return unicodedata.normalize('NFKD', value).encode('ascii', 'replace').decode()


def font(size: int, serif: bool = False):
    """Use the host's normal font when present, or Pillow's bundled fallback."""
    name = 'Georgia.ttf' if serif else 'Arial.ttf'
    candidates = [Path('/System/Library/Fonts/Supplemental') / name]
    if serif:
        candidates += [Path('/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf')]
    else:
        candidates += [Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')]
    for path in candidates:
        if path.is_file():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default(size=size)


def ensure_artwork(source: Path | None = None) -> None:
    ARTWORK.mkdir(parents=True, exist_ok=True)
    if source is not None:
        for side in 'wb':
            for role in 'KQRBNP':
                name = side + role + '.webp'
                shutil.copyfile(source / name, ARTWORK / name)
    assert len(list(ARTWORK.glob('*.webp'))) == 12, 'Provide the twelve pinned Cburnett WebP assets.'


def fitted(draw, text, width, size, *, serif=False, minimum=18):
    text = ascii_text(text)
    while size > minimum and draw.textbbox((0, 0), text, font=font(size, serif))[2] > width:
        size -= 1
    selected = font(size, serif)
    if draw.textbbox((0, 0), text, font=selected)[2] > width:
        raise ValueError('Caption is too long; provide a shorter caption.')
    return text, selected


def wrapped(draw, text, *, width, selected_font):
    lines, line = [], ''
    for word in ascii_text(text).split():
        attempt = (line + ' ' + word).strip()
        if line and draw.textbbox((0, 0), attempt, font=selected_font)[2] > width:
            lines.append(line)
            line = word
        else:
            line = attempt
    if line:
        lines.append(line)
    return lines


def _board(image, fen, uci, left, top, square, *, coords_color=INK, arrow_color=(49, 95, 159, 190)):
    draw = ImageDraw.Draw(image)
    board = chess.Board(fen)
    move = chess.Move.from_uci(uci)
    for sq in chess.SQUARES:
        file, rank = chess.square_file(sq), chess.square_rank(sq)
        x, y = left + file * square, top + (7 - rank) * square
        draw.rectangle((x, y, x + square - 1, y + square - 1), fill=LIGHT if (file + rank) % 2 else DARK)
        if sq in [move.from_square, move.to_square]:
            tint = Image.new('RGBA', (square, square), '#e3d75262')
            image.paste(tint, (x, y), tint)
        piece = board.piece_at(sq)
        if piece:
            name = ('w' if piece.color else 'b') + piece.symbol().upper()
            icon = Image.open(ARTWORK / (name + '.webp')).convert('RGBA')
            icon = icon.resize((square, square), Image.Resampling.LANCZOS)
            image.paste(icon, (x, y), icon)
    label_font = font(max(16, square // 3))
    for n in range(8):
        letter = 'abcdefgh'[n]
        box = draw.textbbox((0, 0), letter, font=label_font)
        draw.text((left + n * square + (square - box[2]) / 2, top + 8 * square + 7), letter, font=label_font, fill=coords_color)
        number = str(8 - n)
        box = draw.textbbox((0, 0), number, font=label_font)
        draw.text((left - box[2] - 10, top + n * square + (square - (box[3] - box[1])) / 2 - box[1]), number, font=label_font, fill=coords_color)
    xy = lambda sq: (left + (chess.square_file(sq) + .5) * square, top + (7 - chess.square_rank(sq) + .5) * square)
    x1, y1 = xy(move.from_square)
    x2, y2 = xy(move.to_square)
    theta = math.atan2(y2 - y1, x2 - x1)
    # Stop just before the center so the destination piece remains recognizable.
    x2 -= square * .18 * math.cos(theta)
    y2 -= square * .18 * math.sin(theta)
    overlay = Image.new('RGBA', image.size)
    ad = ImageDraw.Draw(overlay)
    ad.line((x1, y1, x2, y2), fill=arrow_color, width=max(7, square // 6))
    tip = square * .43
    ad.polygon([(x2, y2), (x2 - tip * math.cos(theta - .55), y2 - tip * math.sin(theta - .55)), (x2 - tip * math.cos(theta + .55), y2 - tip * math.sin(theta + .55))], fill=arrow_color)
    image.paste(overlay, (0, 0), overlay)


def _save(image, output, *, source_label, fen_before, fen_after, uci):
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    meta = PngImagePlugin.PngInfo()
    meta.add_text('Artwork', 'Cburnett by Colin M. L. Burnett, GPL-2.0-or-later. See THIRD_PARTY.md. Piece arrangement and diagrams: draw_figures.py.')
    meta.add_text('Position', json.dumps({'before': fen_before, 'after': fen_after, 'uci': uci}))
    meta.add_text('Caption', ascii_text(source_label))
    image.save(output, pnginfo=meta, optimize=True)


def draw_pair(fen_before: str, fen_after: str, uci: str, label: str, subtitle: str, output: Path | str, *, annotation: str = 'Source !! landmark') -> Path:
    """Create a readable 960x550 before/after pair for any actual played move."""
    before, after = chess.Board(fen_before), chess.Board(fen_after)
    move = chess.Move.from_uci(uci)
    assert move in before.legal_moves, (fen_before, uci)
    expected = before.copy()
    expected.push(move)
    assert expected.board_fen() == after.board_fen(), (uci, fen_after)
    assert (expected.turn, expected.castling_rights, expected.ep_square) == (after.turn, after.castling_rights, after.ep_square), (uci, fen_after)
    image = Image.new('RGB', (960, 550), PAPER)
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 960, 5), fill=BLUE)
    title, selected = fitted(draw, label, 912, 28, serif=True)
    draw.text((24, 15), title, font=selected, fill=INK)
    for left, name in [(40, 'Before'), (528, 'After')]:
        draw.text((left, 57), name, font=font(19), fill=MUTED)
    _board(image, fen_before, uci, 40, 88, 48)
    _board(image, fen_after, uci, 528, 88, 48)
    line, selected = fitted(draw, subtitle, 912, 19)
    draw.text((24, 505), line, font=selected, fill=INK)
    line, selected = fitted(draw, annotation, 912, 16, minimum=16)
    draw.text((24, 530), line, font=selected, fill=MUTED)
    output = Path(output)
    _save(image, output, source_label=label + ' / ' + annotation, fen_before=fen_before, fen_after=fen_after, uci=uci)
    return output


def draw_hero(game: dict, output: Path | str) -> Path:
    """Actual Opera Game board before 16.Qb8+; no model result or fictional art."""
    anchor = next(a for a in game['strictBrilliants'] if a['san'] == 'Qb8+')
    ply = anchor['ply']
    before, after, uci = game['positions'][ply - 1], game['positions'][ply], game['moves'][ply - 1]
    board = chess.Board(before)
    assert board.san(chess.Move.from_uci(uci)) == 'Qb8+'
    image = Image.new('RGB', (1280, 720), NAVY)
    draw = ImageDraw.Draw(image)
    draw.text((48, 75), 'THE OPERA GAME / 1858', font=font(21), fill='#a8c7eb')
    draw.text((44, 145), '16.Qb8+!!', font=font(66, serif=True), fill='#f8fbff')
    for i, text in enumerate(['Offer the queen.', 'Draw the knight away.', 'Mate with the rook.']):
        draw.text((48, 263 + i * 42), text, font=font(29, serif=True), fill='#e7eff9')
    draw.text((48, 466), '16...Nxb8  17.Rd8#', font=font(25), fill='#a8c7eb')
    draw.text((48, 618), 'A published !! landmark', font=font(19), fill='#e7eff9')
    draw.text((48, 648), 'Before the queen sacrifice', font=font(18), fill='#a8c7eb')
    _board(image, before, uci, 704, 80, 64, coords_color='#dce9f8', arrow_color=(41, 93, 159, 210))
    output = Path(output)
    _save(image, output, source_label='Opera Game16.Qb8+!! / before move / source landmark', fen_before=before, fen_after=after, uci=uci)
    return output


def render_landmarks(games: list[dict]) -> list[dict]:
    FIGURES.mkdir(parents=True, exist_ok=True)
    manifest = []
    for game in games:
        for anchor in game['strictBrilliants']:
            ply = anchor['ply']
            before, after, uci = game['positions'][ply - 1], game['positions'][ply], game['moves'][ply - 1]
            assert chess.Board(before).san(chess.Move.from_uci(uci)) == anchor['san']
            name = f"{game['id']}-{ply:03d}.png"
            label = SHORT_NAMES[game['id']] + ' | ' + anchor['move'] + '!!'
            year = game['headers'].get('Date', '')[:4]
            subtitle = SHORT_NAMES[game['id']] + ', ' + year
            draw_pair(before, after, uci, label, subtitle, FIGURES / name)
            manifest.append({'game': game['id'], 'ply': ply, 'move': anchor['move'], 'file': name, 'kind': 'published !! landmark', 'sha256': hashlib.sha256((FIGURES / name).read_bytes()).hexdigest()})
    assert len(manifest) == 14, 'The frozen sample has fourteen primary anchors.'
    opera = next(g for g in games if g['id'] == 'opera-1858')
    draw_hero(opera, FIGURES / 'hero-opera.png')
    (FIGURES / 'manifest.json').write_text(json.dumps({'landmarks': manifest, 'hero': 'hero-opera.png', 'positionsVerified': len(manifest)}, indent=2) + '\n')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--games', type=Path, default=STUDY / 'data/games.json')
    parser.add_argument('--artwork-source', type=Path)
    args = parser.parse_args()
    source = args.artwork_source
    if source is None and not (ARTWORK / 'wK.webp').exists():
        source = STUDY.parents[2] / 'preview/third_party/chessground/assets/piece_sets/cburnett/2.0x'
    ensure_artwork(source)
    rows = render_landmarks(json.loads(args.games.read_text()))
    print(f'Rendered {len(rows)} verified before/after pairs and one actual-position Opera hero.')
