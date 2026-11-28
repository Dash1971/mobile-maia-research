"""Convert the frozen Ginger PGNs to the unchanged native study runner schema."""
import io
import json
from pathlib import Path
import chess
import chess.pgn

ROOT=Path(__file__).resolve().parents[1]

def build():
    frozen=json.loads((ROOT/'ginger/games.json').read_text())
    source=io.StringIO((ROOT/'ginger/games.pgn').read_text())
    result=[]
    for meta in frozen:
        game=chess.pgn.read_game(source)
        assert game is not None and not game.errors
        assert game.headers['Link'].rsplit('/',1)[-1]==meta['game_id']
        board=game.board()
        positions=[board.fen()]
        moves,sans,scope=[],[],[]
        ginger=meta['ginger_color']=='white'
        for ply,move in enumerate(game.mainline_moves(),1):
            if board.turn==ginger:scope.append(ply)
            sans.append(board.san(move));moves.append(move.uci())
            board.push(move);positions.append(board.fen())
        assert len(moves)==meta['plies']
        for ref in meta['reference_moves']:
            ply=ref['ply']
            assert ply in scope and moves[ply-1]==ref['uci'] and sans[ply-1]==ref['san']
            assert positions[ply-1].split()[:3]==ref['fen_before'].split()[:3]
        result.append({'id':meta['game_id'],'account':'Ginger_GM','headers':dict(game.headers),
                       'positions':positions,'moves':moves,'sans':sans,'scoredPlies':scope,
                       'strictBrilliants':meta['reference_moves'],'otherAnnotations':[],
                       'galleryBrilliants':[r['ply'] for r in meta['reference_moves']],
                       'modelRelationship':'No game or mainline position/move match in the pinned public development gallery/candidate table.'})
    assert chess.pgn.read_game(source) is None
    assert len(result)==27 and sum(len(g['moves']) for g in result)==1837
    return result

if __name__=='__main__':
    games=build()
    (ROOT/'ginger/runner-input.json').write_text(json.dumps(games,ensure_ascii=False,separators=(',',':'))+'\n')
    print(f"Prepared {len(games)} games, {sum(len(g['positions']) for g in games)} positions, {sum(len(g['scoredPlies']) for g in games)} Ginger moves.")
