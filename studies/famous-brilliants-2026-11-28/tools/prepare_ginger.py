#!/usr/bin/env python3
"""Freeze a gallery-selected sample and audit the pinned public development corpus.

Uses public, unauthenticated ordinary Git/API data. Does not run either detector.
"""
import argparse, collections, csv, gzip, hashlib, io, json, pathlib, re, urllib.request
import chess
import chess.pgn

PIN = '59cab58a8b63387d9775252f03a6875fe451f697'
BASE = f'https://raw.githubusercontent.com/Dash1971/open-brilly-finder/{PIN}/'
GALLERY_PATH = 'studies/brilliant-selective-2026-11-06/data/seven-accounts-last-12-months-chesscom-brilliants.pgn'

def digest(data):
    return hashlib.sha256(data).hexdigest()

def position(fen):
    # Normalize move counters and a non-capturable en-passant target away.
    return ' '.join(chess.Board(fen).fen(en_passant='legal').split()[:4])

def prepare(scratch, output):
    seed = json.loads((output/'gallery-selection.json').read_text())
    sources = json.loads((scratch/'sources.json').read_text())
    rows = list(csv.DictReader(io.StringIO(gzip.decompress((scratch/'candidates.csv.gz').read_bytes()).decode())))
    training = [r for r in rows if r['role'] == 'training']
    train_games = {r['game_id'] for r in training}
    candidate_games = {r['game_id'] for r in rows}
    train_keys = collections.defaultdict(list)
    dev_keys = collections.defaultdict(list)
    for r in rows:
        key = (position(r['fen_before']), r['uci'])
        record = {'game_id':r['game_id'],'ply':int(r['ply']),'role':r['role']}
        dev_keys[key].append(record)
        if r['role'] == 'training': train_keys[key].append(record)

    url = BASE+GALLERY_PATH
    gallery_cache = scratch/'development-gallery.pgn'
    if not gallery_cache.exists():
        gallery_cache.write_bytes(urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'MobileMaiaResearch/1.0'}),timeout=60).read())
    data = gallery_cache.read_bytes()
    assert not data.startswith(b'version https://git-lfs.github.com/')
    sources['development-gallery.pgn'] = {'url':url,'bytes':len(data),'sha256':digest(data)}
    # Headers identify gallery games even if none of their moves was a candidate.
    gallery_games = set()
    ginger_exposure = []
    gallery_records = 0
    for block in re.split(r'(?=\[Event ")',data.decode()):
        headers = dict(re.findall(r'^\[(\w+) "(.*)"\]$',block,re.M))
        link = headers.get('Link','')
        match = re.search(r'/(?:live|daily)/(\d+)' ,link)
        if not match: continue
        gid = match.group(1)
        gallery_records += 1
        gallery_games.add(gid)
        if any(headers.get(side,'').casefold() == 'ginger_gm' for side in ('White','Black')):
            ginger_exposure.append({'game_id':gid,'white':headers.get('White'),'black':headers.get('Black'),'has_training_candidate':gid in train_games})
    del data
    assert gallery_records == 7019, (gallery_records,len(gallery_games))
    archive = json.loads((scratch/'ginger-november.json').read_text())
    archived = {g['url'].rsplit('/',1)[-1]:g for g in archive['games']}
    results, kept, exclusions, all_pgn = [], [], [], []
    for gid, targets in seed['games']:
        source = archived.get(gid)
        if source is None:
            exclusions.append({'game_id':gid,'reason':'PGN not found in public November archive'})
            continue
        game = chess.pgn.read_game(io.StringIO(source['pgn']))
        assert game is not None and not game.errors, gid
        white = game.headers['White'].casefold() == 'ginger_gm'
        assert white or game.headers['Black'].casefold() == 'ginger_gm', gid
        board, reference, overlaps, other_dev = game.board(), [], [], []
        moves = list(game.mainline_moves())
        for ply, move in enumerate(moves,1):
            fen, san = board.fen(en_passant='fen'), board.san(move)
            key = (position(fen), move.uci())
            record = {'ply':ply,'san':san,'uci':move.uci()}
            if key in train_keys: overlaps.append(dict(record,matches=train_keys[key]))
            if key in dev_keys: other_dev.append(dict(record,matches=dev_keys[key]))
            if ply in targets:
                assert board.turn == white, (gid,ply,'target is not Ginger move')
                reference.append(dict(record,fen_before=fen,gallery_url=f'https://www.chess.com/analysis/game/live/{gid}?move={ply-1}'+('&flip=true' if not white else '')))
            board.push(move)
        assert len(reference) == len(targets), (gid,targets,len(moves))
        record = {'game_id':gid,'white':game.headers['White'],'black':game.headers['Black'],'date':game.headers['Date'],'plies':len(moves),'ginger_color':'white' if white else 'black','reference_moves':reference,'in_training_games':gid in train_games,'in_development_gallery':gid in gallery_games,'in_candidate_table':gid in candidate_games,'training_position_move_overlaps':overlaps,'all_development_position_move_overlaps':other_dev}
        results.append(record)
        # Deliberately strict: exclude a whole game if ANY played position/move
        # occurs among the published model-development candidates, not just a target.
        reasons=[]
        if gid in gallery_games or gid in candidate_games: reasons.append('published development game')
        if other_dev: reasons.append('published development candidate position/move')
        if reasons:
            exclusions.append({'game_id':gid,'reason':'; '.join(reasons)})
        else:
            kept.append(record)
            for node in game.mainline():
                node.comment = ''
                node.nags.clear()
            game.comment = ''
            game.headers['Link'] = source['url']
            all_pgn.append(game.accept(chess.pgn.StringExporter(headers=True,variations=False,comments=False)))
    pgn='\n\n'.join(all_pgn)+'\n'
    (output/'games.pgn').write_text(pgn)
    (output/'games.json').write_text(json.dumps(kept,indent=2)+'\n')
    audit={'upstream_pin':PIN,'normalization':'Legal chess position: piece placement, side to move, castling rights, legally available en-passant target; excludes halfmove/fullmove counters. Key includes played UCI move. Audit every mainline move against all public candidate rows, regardless of role.','candidate_rows':len(rows),'roles':dict(collections.Counter(r['role'] for r in rows)),'training_rows':len(training),'training_games':len(train_games),'published_gallery_records':gallery_records,'published_gallery_games':len(gallery_games),'ginger_in_original_gallery':ginger_exposure,'selected_games':len(seed['games']),'selected_gallery_moves':sum(len(x[1]) for x in seed['games']),'eligible_games':len(kept),'eligible_gallery_moves':sum(len(x['reference_moves']) for x in kept),'exclusions':exclusions,'games':results,'sources':sources,'outputs':{'games.pgn':digest(pgn.encode()),'games.json':digest((output/'games.json').read_bytes())}}
    (output/'overlap-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    print(json.dumps({k:v for k,v in audit.items() if k not in ('games','sources','outputs','normalization')},indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--scratch',type=pathlib.Path,required=True)
    p.add_argument('--output',type=pathlib.Path,required=True)
    args=p.parse_args()
    prepare(args.scratch,args.output)
