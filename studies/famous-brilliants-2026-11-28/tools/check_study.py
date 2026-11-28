"""Check all games, recorded evidence, published totals and figure integrity."""
import hashlib
import json
from pathlib import Path
import re

import chess
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def main():
    games = json.loads((ROOT / 'data/games.json').read_text())
    raw = json.loads((ROOT / 'data/engine-runs.json').read_text())
    public = json.loads((ROOT / 'web/results.json').read_text())
    assert len(games) == 9 and len(raw['runs']) == 27
    assert len({(r['game'], r['quality']) for r in raw['runs']}) == 27
    assert sum(len(g['moves']) for g in games) == 492
    assert sum(len(g['strictBrilliants']) for g in games) == 14
    by = {g['id']: g for g in games}
    for game in games:
        board = chess.Board(game['positions'][0])
        for i, uci in enumerate(game['moves']):
            move = chess.Move.from_uci(uci)
            assert move in board.legal_moves
            assert board.san(move) == game['sans'][i]
            board.push(move)
            assert board.fen() == game['positions'][i + 1]
        for a in game['strictBrilliants'] + game['otherAnnotations']:
            assert game['sans'][a['ply'] - 1] == a['san']
    positions = 0
    for run in raw['runs']:
        game = by[run['game']]
        assert len(run['scores']) == len(game['positions'])
        positions += len(run['scores'])
        for fen, score in zip(game['positions'], run['scores']):
            board = chess.Board(fen)
            if not score['lines']:
                assert board.is_game_over()
                continue
            assert score['evidence']['complete']
            assert score['evidence']['quality'] == run['quality']
            assert score['cp'] == score['lines'][0]['cp']
            assert score['mate'] == score['lines'][0]['mate']
            roots = [line['moves'][0] for line in score['lines']]
            assert len(set(roots)) == len(roots)
            for line in score['lines']:
                trial = board.copy()
                for uci in line['moves']:
                    move = chess.Move.from_uci(uci)
                    assert move in trial.legal_moves, (run['game'], fen, uci)
                    trial.push(move)
        for algorithm in ('old', 'new'):
            assert run[algorithm]['confirmationSearches'] <= 6
            provisional = {l['ply'] for l in run[algorithm]['provisional'] if l['label'] == 'brilliant'}
            final = {l['ply'] for l in run[algorithm]['final'] if l['label'] == 'brilliant'}
            assert final <= provisional
    assert positions == 1503
    for game in public['games']:
        for case in game['cases']:
            for mode in case['modes'].values():
                if mode['candidate'] is None and mode['new'] not in ('blunder', 'mistake', 'dubious'):
                    assert 'not recorded' in mode['reason']
    expected = {'fast': (9, 10, 19, 20), 'balanced': (8, 10, 16, 19), 'thorough': (9, 11, 19, 20)}
    for q, values in expected.items():
        total = public['totals'][q]
        assert tuple(total[k] for k in ('oldHits', 'newHits', 'oldAwards', 'newAwards')) == values
        sums = [sum(g['stats'][q][key] for g in public['games']) for key in ('oldHits', 'newHits', 'oldAwards', 'newAwards')]
        assert tuple(sums) == values
    manifest = json.loads((ROOT / 'figures/manifest.json').read_text())
    for file in (ROOT / 'figures').glob('*.png'):
        with Image.open(file) as im:
            im.verify()
    images = re.findall(r'!\[[^\]]*\]\(([^)]+)\)', (ROOT / 'REPORT.md').read_text())
    assert len(images) == 14
    assert all((ROOT / image).is_file() for image in images)
    imports = json.loads((ROOT / 'web/website-files.json').read_text())
    for row in imports['files']:
        content = (ROOT / row['source']).read_bytes()
        assert len(content) == row['bytes']
        assert hashlib.sha256(content).hexdigest() == row['sha256']
    for path in ROOT.rglob('*'):
        if path.is_file() and path.suffix in ('.json', '.md', '.py', '.dart', '.js', '.html'):
            assert re.search(r'/Users/[A-Za-z0-9_.-]+/', path.read_text()) is None, path
    print('PASS: 9 legal games,492 moves,14 fixed landmarks,27 complete runs,1503 baseline positions; all PVs, totals, diagrams and publication hashes verified.')


if __name__ == '__main__':
    main()
