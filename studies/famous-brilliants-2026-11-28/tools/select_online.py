"""Freeze a deterministic sample from the pinned public online-game collection."""
import argparse
import csv
import gzip
import hashlib
import json
from pathlib import Path

import chess.pgn

ROOT = Path(__file__).resolve().parents[1]
ACCOUNTS = ['hansen', 'KNVB', 'nelsi', 'GothamChess', 'Hikaru', 'MagnusCarlsen', 'Witty_Alien']
SALT = 'mobile-maia-online-brilliant-27-v1:'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--upstream', type=Path, required=True)
    args = p.parse_args()
    data = args.upstream / 'studies/brilliant-exchange-2026-11-22/data'
    with gzip.open(data / 'chesscom-review-moves.csv.gz', 'rt') as f:
        rows = list(csv.DictReader(f))
    reviews = {}
    for row in rows:
        reviews.setdefault(row['game_id'], {})[int(row['ply'])] = row
    with (data / 'heldout-outcomes.csv').open() as f:
        heldout = {r['game_id'] for r in csv.DictReader(f)}
    pool = {a: [] for a in ACCOUNTS}
    normalized, excluded = [], []
    pgn = args.upstream / 'studies/brilliant-selective-2026-11-06/data/seven-accounts-last-12-months-chesscom-brilliants.pgn'
    with pgn.open() as f:
        while (g := chess.pgn.read_game(f)) is not None:
            account = g.headers.get('BrilliantAccounts')
            gid = g.headers.get('Link', '').split('/')[-1]
            if account not in pool or gid not in reviews:
                continue
            if account == 'Witty_Alien' and gid not in heldout:
                continue
            nodes = list(g.mainline())
            if g.errors or not nodes or set(reviews[gid]) != set(range(1, len(nodes) + 1)):
                continue
            mismatch = False
            for i, n in enumerate(nodes, 1):
                actual, recorded = n.move.uci(), reviews[gid][i]['uci']
                if actual == recorded:
                    continue
                if n.move.promotion and len(recorded) == 4 and actual[:4] == recorded:
                    normalized.append({'gameId':gid,'ply':i,'recorded':recorded,'legalPGN':actual})
                else:
                    excluded.append({'gameId':gid,'reason':'PGN/review UCI mismatch','ply':i})
                    mismatch = True
                    break
            if mismatch:
                continue
            key = hashlib.sha256((SALT + gid).encode()).hexdigest()
            pool[account].append((key, gid, g))
    selected, factual = [], []
    for account in ACCOUNTS:
        assert len(pool[account]) >= 6
        for rank, (key, gid, g) in enumerate(sorted(pool[account])[:6], 1):
            board = g.board()
            moves, sans, positions, gallery = [], [], [board.fen()], []
            for ply, node in enumerate(g.mainline(), 1):
                moves.append(node.move.uci()); sans.append(board.san(node.move))
                if chess.pgn.NAG_BRILLIANT_MOVE in node.nags:
                    gallery.append(ply)
                board.push(node.move); positions.append(board.fen())
            color = 'white' if g.headers['White'].lower() == account.lower() else 'black'
            own = [i for i in range(1, len(moves)+1) if (i % 2 == 1) == (color == 'white')]
            labels = reviews[gid]
            targets = [{'ply': i, 'san': sans[i-1]} for i in own if labels[i]['chesscom_class'] == 'brilliant']
            headers = {k: g.headers[k] for k in ['Event','Site','Date','White','Black','Result','WhiteElo','BlackElo','TimeControl','Link'] if k in g.headers}
            game = {'id': 'online-' + gid, 'gameId': gid, 'account': account, 'accountColor': color,
                    'sampleRank': rank, 'selectionHash': key, 'headers': headers,
                    'moves': moves, 'sans': sans, 'positions': positions,
                    'scoredPlies': own, 'strictBrilliants': targets, 'otherAnnotations': [],
                    'galleryBrilliants': [i for i in gallery if i in own],
                    'reviewLabels': {str(i): labels[i]['chesscom_class'] for i in own},
                    'modelRelationship': 'upstream-held-out-game' if gid in heldout else 'upstream-development-game'}
            selected.append(game)
            clean = chess.pgn.Game()
            clean.headers.clear(); clean.headers.update(headers)
            clean.headers['Annotator'] = 'Recorded Chess.com Game Review, November 22, 2026; account moves only'
            clean.headers['ScoredAccount'] = account
            cursor = clean
            for i, uci in enumerate(moves, 1):
                cursor = cursor.add_variation(chess.Move.from_uci(uci))
                if i in own and labels[i]['chesscom_class'] == 'brilliant':
                    cursor.nags.add(chess.pgn.NAG_BRILLIANT_MOVE)
            factual.append(clean.accept(chess.pgn.StringExporter(headers=True, variations=False, comments=False)))
    out = ROOT / 'online'
    (out / 'games.json').write_text(json.dumps(selected, ensure_ascii=False, separators=(',', ':')) + '\n')
    (out / 'games.pgn').write_text('\n\n'.join(factual) + '\n\n')
    (out / 'selection.json').write_text(json.dumps({'upstreamCommit':'59cab58a8b63387d9775252f03a6875fe451f697',
        'salt':SALT,'rule':'Six lowest SHA-256(salt + numeric game ID) per account among fully reviewed, legal, move-matched games. A missing promotion suffix in review UCI is resolved from the legal PGN. Witty_Alien limited to upstream held-out games. No filtering on classifier outcomes.',
        'reviewUCINormalizations':normalized,'excludedMismatches':excluded,
        'primaryMode':'fast','primaryReference':'Recorded Chess.com Game Review November 22, 2026; scored account moves only',
        'accounts':{a:{'eligible':len(pool[a]),'selected':6} for a in ACCOUNTS},
        'gameIds':[g['gameId'] for g in selected], 'games':len(selected),
        'plies':sum(len(g['moves']) for g in selected), 'scoredMoves':sum(len(g['scoredPlies']) for g in selected),
        'reviewBrilliants':sum(len(g['strictBrilliants']) for g in selected),
        'galleryBrilliants':sum(len(g['galleryBrilliants']) for g in selected)},indent=2)+'\n')
    print((out / 'selection.json').read_text())


if __name__ == '__main__':
    main()
