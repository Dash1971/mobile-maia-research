"""Build the changed-move catalog and diagrams from exact classifier output."""
import argparse
import base64
import hashlib
import json
import math
from pathlib import Path
import shutil

import chess
from PIL import Image, ImageDraw, ImageFont, PngImagePlugin

STUDY = Path(__file__).resolve().parents[1]
LABELS = {None: 'Unmarked', 'brilliant': 'Brilliant !!', 'interesting': 'Interesting !?', 'good': 'Good !'}
NAMES = {'byrne-fischer-1956': 'Byrne–Fischer, 1956', 'opera-1858': 'Opera game, 1858'}


def pv_san(fen, moves):
    board = chess.Board(fen)
    result = []
    for uci in moves:
        move = chess.Move.from_uci(uci)
        assert move in board.legal_moves, (fen, uci)
        prefix = f'{board.fullmove_number}.' if board.turn else (f'{board.fullmove_number}...' if not result else '')
        result.append(prefix + board.san(move))
        board.push(move)
    return ' '.join(result)


def export(raw, app):
    groups = {}
    for row in raw['native']:
        key = row['id']
        if key not in groups:
            groups[key] = {k: row[k] for k in ['id', 'san', 'uci', 'fenBefore', 'fenAfter']}
            groups[key].update({'dataset': 'native', 'game': NAMES[row['game']], 'variants': []})
        groups[key]['variants'].append(row)
    cases = sorted(groups.values(), key=lambda r: (r['game'], int(r['id'].split(':')[-1])))
    for row in raw['labeled']:
        cases.append({**{k: row[k] for k in ['id', 'san', 'uci', 'fenBefore', 'fenAfter', 'recordedBrilliant', 'features']}, 'dataset': 'labeled', 'game': 'Reference case ' + row['id'], 'variants': [row]})
    art = STUDY / 'artwork'
    art.mkdir(exist_ok=True)
    pieces = {}
    for p in sorted((app / 'third_party/chessground/assets/piece_sets/cburnett/2.0x').glob('*.webp')):
        shutil.copyfile(p, art / p.name)
        pieces[p.stem] = 'data:image/webp;base64,' + base64.b64encode(p.read_bytes()).decode()
    assert len(pieces) == 12
    source_hashes = {}
    paths = ['test/fixtures/brilly-exchange-parity.json', 'assets/classifiers/mute-exchange-model.json']
    paths += [f'test/fixtures/classification/{name}.json' for name in ['stockfish18-fast', 'stockfish18-balanced-thorough', 'stockfish-light-fast', 'stockfish-light-balanced-thorough']]
    for name in paths:
        source_hashes[name] = hashlib.sha256((app / name).read_bytes()).hexdigest()
    for idx, row in enumerate(cases):
        board = chess.Board(row['fenBefore'])
        move = chess.Move.from_uci(row['uci'])
        assert move in board.legal_moves
        assert board.san(move) == row['san']
        row['move'] = f'{board.fullmove_number}' + ('.' if board.turn else '...') + row['san']
        board.push(move)
        assert board.board_fen() == chess.Board(row['fenAfter']).board_fen()
        row['gained'] = any(v['new'] == 'brilliant' and v['old'] != 'brilliant' for v in row['variants'])
        row['file'] = f"{idx + 1:02d}-{'gained' if row['gained'] else 'lost'}"
        for v in row['variants']:
            v['engineMode'] = ('SF18' if 'stockfish18' in v.get('corpus', '') else 'SF Light') + ' · ' + v.get('quality', '').title() if row['dataset'] == 'native' else 'Reference window'
            v.pop('engine', None)
            v['beforeSan'] = [pv_san(row['fenBefore'], line['pv']) for line in v['beforeLines']]
            v['afterSan'] = pv_san(row['fenAfter'], v['afterLine']['pv'])
        row['defaultVariant'] = next(i for i, v in enumerate(row['variants']) if (v['old'] == 'brilliant') != (v['new'] == 'brilliant'))
    data = {'source': raw['appSource'], 'upstream': raw['modelSource'], 'cutoff': raw['cutoff'], 'counts': {'nativeSnapshots': 821, 'nativeRuns': 17, 'nativeAdded': 10, 'nativeRemoved': 6, 'nativeUnique': 4, 'labeledCases': 360, 'labeledAdded': 26, 'labeledRemoved': 3, 'recoveredLabels': 24, 'lostLabels': 1, 'addedOutsideLabels': 2, 'removedOutsideLabels': 2}, 'sourceSha256': source_hashes, 'cases': cases}
    (STUDY / 'data/changed-moves.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    return data, pieces


def diagram(row):
    image = Image.new('RGB', (960, 550), '#f8f7f4')
    draw = ImageDraw.Draw(image)
    title_font = ImageFont.load_default(size=24)
    font = ImageFont.load_default(size=19)
    small = ImageFont.load_default(size=16)
    variant = row['variants'][row['defaultVariant']]
    title = row['move'] + ' | ' + LABELS[variant['old']] + ' -> ' + LABELS[variant['new']]
    draw.text((24, 12), title, font=title_font, fill='#1e2724')
    for left, fen, label in [(40, row['fenBefore'], 'Before'), (528, row['fenAfter'], 'After')]:
        draw.text((left, 53), label, font=font, fill='#35423e')
        board = chess.Board(fen)
        top, step = 88, 48
        for square in chess.SQUARES:
            file, rank = chess.square_file(square), chess.square_rank(square)
            x, y = left + file * step, top + (7 - rank) * step
            color = '#f0d9b5' if (file + rank) % 2 else '#b58863'
            draw.rectangle((x, y, x + step, y + step), fill=color)
            if chess.square_name(square) in (row['uci'][:2], row['uci'][2:4]):
                overlay = Image.new('RGBA', (step, step), '#ddd13568')
                image.paste(overlay, (x, y), overlay)
            piece = board.piece_at(square)
            if piece:
                name = ('w' if piece.color else 'b') + piece.symbol().upper()
                art = Image.open(STUDY / 'artwork' / (name + '.webp')).convert('RGBA').resize((step, step), Image.Resampling.LANCZOS)
                image.paste(art, (x, y), art)
        for n in range(8):
            draw.text((left + n * step + 19, top + 389), 'abcdefgh'[n], font=small, fill='#35423e')
            draw.text((left - 22, top + n * step + 14), str(8 - n), font=small, fill='#35423e')
        a, b = row['uci'][:2], row['uci'][2:4]
        point = lambda sq: (left + ('abcdefgh'.index(sq[0]) + .5) * step, top + (8 - int(sq[1]) + .5) * step)
        x1, y1 = point(a)
        x2, y2 = point(b)
        theta = math.atan2(y2 - y1, x2 - x1)
        x2 -= 12 * math.cos(theta)
        y2 -= 12 * math.sin(theta)
        arrow = Image.new('RGBA', image.size)
        ad = ImageDraw.Draw(arrow)
        ad.line((x1, y1, x2, y2), fill='#196798ce', width=9)
        ad.polygon([(x2, y2), (x2 - 24 * math.cos(theta - .5), y2 - 24 * math.sin(theta - .5)), (x2 - 24 * math.cos(theta + .5), y2 - 24 * math.sin(theta + .5))], fill='#196798ce')
        image.paste(arrow, (0, 0), arrow)
    draw.text((24, 507), row['game'].replace('–', '-'), font=font, fill='#35423e')
    if row['dataset'] == 'labeled':
        draw.text((24, 531), 'Recorded label: ' + ('Brilliant' if row['recordedBrilliant'] else 'No Brilliant label'), font=small, fill='#35423e')
    meta = PngImagePlugin.PngInfo()
    meta.add_text('Artwork', 'Cburnett pieces by Colin M. L. Burnett, GPL-2.0-or-later. See THIRD_PARTY.md. Diagram composition generated by build_review.py.')
    image.save(STUDY / 'figures' / (row['file'] + '.png'), pnginfo=meta, optimize=True)


def report(data):
    lines = ['# Brilliant moves gained and lost', '', 'Preview 2.7 draft comparison · November 28, 2026', '',
             '## Mobile Maia engine tests', '',
             '**Four distinct moves account for 10 gained and 6 withdrawn awards across 821 recorded move snapshots.** Each diagram shows the actual before/after position. The arrow marks the played move.', '',
             'These reuse 17 recorded runs of six games, not 821 unique games. No new engine analysis was run for this review. Model scores are not probabilities.', '']
    for row in data['cases'][:4]:
        lines += [f"### {row['move']} — {'gained' if row['gained'] else 'lost'}", '', row['game'], '', f"![{row['move']} before and after](figures/{row['file']}.png)", '', '| Engine/mode | Previous | New | Model score |', '| --- | --- | --- | ---: |']
        for v in row['variants']:
            lines.append(f"| {v['engineMode']} | {LABELS[v['old']]} | {LABELS[v['new']]} | {format(v['score'], '.4f') if v['candidate'] else 'Gate not met'} |")
        if not row['gained']:
            lines += ['', 'The Exchange offer gate rejects this position: it does not leave a non-pawn piece capturable for a static-exchange gain of at least two pawns. Tree inference is not run; zero here is the no-candidate sentinel.']
        lines += ['']
    lines += ['## Labeled reference cases', '',
              'The selected 360-case regression subset contains 57 recorded Brilliant labels. It is not a held-out accuracy test. The new integration recovers 24 labels and loses one; it removes two previous outside-label awards and adds two different ones. “No Brilliant label” describes the fixture, not an independent judgment that the move is unworthy.', '']
    categories = [('Gained — recorded Brilliant label', True, True), ('Gained — outside recorded Brilliant labels', True, False), ('Lost — recorded Brilliant label', False, True), ('Lost — outside recorded Brilliant labels', False, False)]
    for name, gained, label in categories:
        rows = [r for r in data['cases'][4:] if r['gained'] == gained and r['recordedBrilliant'] == label]
        lines += ['<details>', f'<summary>{name} ({len(rows)})</summary>', '']
        for row in rows:
            v = row['variants'][0]
            lines += [f"### {row['move']} · `{row['id']}`", '', f"{LABELS[v['old']]} → {LABELS[v['new']]} · Model score {v['score']:.4f} · Cutoff {data['cutoff']:.4f}", '', f"![{row['move']}, case {row['id']}, before and after](figures/{row['file']}.png)", '']
        lines += ['</details>', '']
    lines += ['## Sources and reproduction', '',
              '[Complete positions, engine lines and scores](data/changed-moves.json) · [Reproduction](README.md) · [Artwork notices](THIRD_PARTY.md)', '',
              f"Application classifier: [Preview `{data['source'][:7]}`](https://github.com/Dash1971/maia-chess-android-preview/tree/{data['source']}). Model/reference: [Open Brilly Finder `{data['upstream'][:7]}`](https://github.com/Dash1971/open-brilly-finder/tree/{data['upstream']}).", '',
              'Only Brilliant-related changes are listed. Other retained awards and unchanged grades are outside this catalog. Graph evaluations are unchanged. Native mode rows include unchanged awards at the same four positions; Stockfish Light Opera-game runs were not recorded. Android qualification remains pending in Preview #284.', '']
    (STUDY / 'REPORT.md').write_text('\n'.join(lines))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw', type=Path, required=True)
    parser.add_argument('--app', type=Path, required=True)
    args = parser.parse_args()
    data, pieces = export(json.loads(args.raw.read_text()), args.app)
    for row in data['cases']:
        diagram(row)
    report(data)
    print(f"Verified and rendered {len(data['cases'])} legal before/after positions.")
