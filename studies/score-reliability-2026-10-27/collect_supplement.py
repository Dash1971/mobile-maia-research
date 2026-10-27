"""Collect the fixed 2022 supplement without model inference (Python 3.14+).

Example:
  python collect_supplement.py --original /path/allie-test.jsonl --scratch /path/scratch

Downloads the 12 pinned ALLIE validation files and equal compressed prefixes of
all 12 official 2022 archives. Start at 8 MiB/month; expand every month to 16,
then 32 MiB only if fewer than 154 raw eligible games exist. Only missing byte
ranges are fetched. Complete games precede the final [Event boundary; discard
the final possibly incomplete game. All 121 eligible validation games precede
154 hash-selected raw games. No game scores or model predictions are consulted.
"""
from pathlib import Path
import argparse, codecs, collections, hashlib, io, json, math, re, shutil, sys, urllib.request
from compression import zstd
import chess
import chess.pgn

REV = '990f79105b1f08a8fd367fcb10c5e18c69436e30'
ORIGINAL_HASH = 'a6014de8ef861b2ee23a84d7ce824e644390577a000350fad06bd995bcddab0d'
HF = 'https://huggingface.co/datasets/yimingzhang/allie-data'
LICHESS = 'https://database.lichess.org/standard/'
SEED = 2026102701
ROOT = Path(__file__).resolve().parent
MIB = 1024**2
ARCHIVE_SHA256 = {'lichess_db_standard_rated_2022-01.pgn.zst': '357ca508333bbc24d1ab59c66bcfdcc7ccd511f8fdd71d71dee63682e921b03d', 'lichess_db_standard_rated_2022-02.pgn.zst': 'f4bc07104e26268f3149813f361d89e8dff1b933812166aed6384b155d60507b', 'lichess_db_standard_rated_2022-03.pgn.zst': '6250b831ecdabec60944dba40b5b43a39a34a424162e4ae2a31a4b3e4f17ed0f', 'lichess_db_standard_rated_2022-04.pgn.zst': 'c217bff9ebd3c247bd72d7a2d897d394a2c0d122296a03400ec9d9479d11dc8c', 'lichess_db_standard_rated_2022-05.pgn.zst': '9db080a7cdd3e124606f9ca6cfd88985b3077b9028cbd2987d3df7ddddf297e0', 'lichess_db_standard_rated_2022-06.pgn.zst': '089943f8aa408be0b8f4cd074f12511efc176f1220cd478a09cf70af015befc4', 'lichess_db_standard_rated_2022-07.pgn.zst': 'a2c873a53ca52143b0846494fdedba1369d4fc5ceb86c78320f17cedeed80634', 'lichess_db_standard_rated_2022-08.pgn.zst': '72a8b82d5ec2955aa32ffbc68171a55fe2faed32f613eae7df1a2bf8ee6c9fcf', 'lichess_db_standard_rated_2022-09.pgn.zst': 'dc731788e6d9dd677f0f97197462cc38d9223ae3f48b8f0402c1724f04d6f3ed', 'lichess_db_standard_rated_2022-10.pgn.zst': '96a173e5e5e3ee46cf165972e3f44b48fbb99c095287cf7be12c5835f54317c2', 'lichess_db_standard_rated_2022-11.pgn.zst': 'bfeddb57347dc57b729cd3f678cec666a27bcab72fbbdb8280e420377a20d3dc', 'lichess_db_standard_rated_2022-12.pgn.zst': '75f892445b4f0ed2668a2137b9d57b3cbb1e828208f67d473c59ae743dd04b61'}
PREFIX_8MIB_SHA256 = {'lichess_db_standard_rated_2022-01.pgn.zst': 'adf90bc7fef0f2d9a59985345fab7afd6932c97575329498801f15ab78e8ff15', 'lichess_db_standard_rated_2022-02.pgn.zst': '201976cea2c2d6a7792a56cdac08230706e4339a61f3c2fdd850418be9aec2f9', 'lichess_db_standard_rated_2022-03.pgn.zst': '2d5f12ed55e425156a488464065f4b63c20f15beaa1c907eb801acd80dcf3306', 'lichess_db_standard_rated_2022-04.pgn.zst': 'bd068987e023aa733265ed7fb1e71e6a8daf2f156160955880fbf14c03fd6622', 'lichess_db_standard_rated_2022-05.pgn.zst': '9de7da404dd540170bc24135f86f1f5ea757ece1c8bf8651d0edc90e391cc42b', 'lichess_db_standard_rated_2022-06.pgn.zst': '6688b0285d411f5685033a55e366fa80df6299f8317fe73f2f30ebfd6cfcbd4e', 'lichess_db_standard_rated_2022-07.pgn.zst': 'bfb5769ad27ee3a96088be144634f46da3958ee066ea51966607b1f237950a33', 'lichess_db_standard_rated_2022-08.pgn.zst': '728ccf7a478e67b707001768acbb95059d701450c0c05613aa42dff2728ae88f', 'lichess_db_standard_rated_2022-09.pgn.zst': '7b102358d56c7d4f69857f163b6464db262c9f23b00fb05aea5ddb59596c69fd', 'lichess_db_standard_rated_2022-10.pgn.zst': '5b2d27bebc81ec98030ed57da47efaa8a30a54dfaa3ef33e95a31beaed0e24aa', 'lichess_db_standard_rated_2022-11.pgn.zst': '76947581c78c49c45889e98a324a68ac7049f01bdf69a940c2249d8e264ff0ba', 'lichess_db_standard_rated_2022-12.pgn.zst': 'd853f927fed17d54a4b301e0de6603a6720b48c4785fd8f0bdf59909ffea42ca'}

def digest(data): return hashlib.sha256(data).hexdigest()
def priority(kind, gid, *rest): return digest('|'.join(map(str, [SEED, kind, gid, *rest])).encode())
def read_rows(p): return [json.loads(line) for line in p.read_text().splitlines()]
def get(url, headers=None, method=None):
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers or {}, method=method), timeout=120) as r:
        return r.read(), dict(r.headers), r.status

def ensure_disk(path):
    free = shutil.disk_usage(path).free
    if free < 11*1024**3: raise RuntimeError('Stop: less than 10 GiB reserve plus 1 GiB expected growth')
    return free

def eligibility(g):
    """Independently replay the original study's target-2600 eligibility."""
    try: ratings = [int(g[s+'-elo']) for s in ['white','black']]
    except (KeyError, TypeError, ValueError): return 'missing_ratings', None
    if not all(2500 <= r <= 2700 for r in ratings): return 'outside_band', None
    if not g['event'].startswith('Rated Blitz') or g['termination'] != 'Normal' or g['result'] not in ['1-0','0-1','1/2-1/2']:
        return 'event_or_result_excluded', None
    try:
        base, inc = map(int, g['time-control'].split('+')); assert base > 0 and inc >= 0
        moves, secs = g['moves-uci'].split(), g['moves-seconds']; assert len(moves) == len(secs)
        assert all(isinstance(t,(int,float)) and math.isfinite(t) and t >= 0 for t in secs)
    except (KeyError, TypeError, ValueError, AssertionError): return 'invalid_clocks', None
    board = chess.Board(); clocks = [float(base)]*2; allowed = True; candidates = []; fens = [board.fen(en_passant='fen')]
    for ply, (uci, spent) in enumerate(zip(moves,secs)):
        try: move = chess.Move.from_uci(uci)
        except ValueError: return 'illegal_replay', None
        if move not in board.legal_moves: return 'illegal_replay', None
        side = ply % 2
        if min(clocks) < 30 or clocks[side] - spent < 30: allowed = False
        if allowed and board.fullmove_number >= 11 and not board.is_game_over(claim_draw=False):
            candidates.append({'ply':ply,'history':fens[-8:].copy(),'prefixUci':moves[:ply],'playedUci':uci,'clocksBefore':clocks.copy(),'moverClockAfterThink':clocks[side]-spent})
        clocks[side] += inc - spent; board.push(move); fens.append(board.fen(en_passant='fen'))
    result = board.outcome(claim_draw=False)
    if result is not None and result.result() != g['result']: return 'contradictory_result', None
    if not candidates: return 'no_eligible_position', None
    chosen=min(candidates,key=lambda r:priority('position',g['game-id'],r['ply']))
    chosen.update(game=g['game-id'],elo=2600,whiteElo=ratings[0],blackElo=ratings[1],result=g['result'],actualWhiteScore={'1-0':1.,'0-1':0.,'1/2-1/2':.5}[g['result']],termination=g['termination'],timeControl=g['time-control'],eligiblePositions=len(candidates),consistency=False)
    return 'eligible', chosen

def validate_unique(rows):
    assert len(rows) == len({g['game-id'] for g in rows}), 'Duplicate selected ID'
    assert len(rows) == len({g['moves-uci'] for g in rows}), 'Duplicate selected exact move sequence'

def monthly(scratch, original):
    raw, _, _ = get('https://huggingface.co/api/datasets/yimingzhang/allie-data/tree/'+REV+'?recursive=true&expand=false')
    files = [x for x in json.loads(raw) if re.fullmatch(r'lichess-2022-blitz-sampled/2022-\d\d-val.jsonl',x['path'])]
    assert len(files) == 12
    ids = {g['game-id'] for g in original}; seqs = {g['moves-uci'] for g in original}
    records=[]; sources=[]; counts=collections.Counter(); all_val=[]
    for x in sorted(files,key=lambda x:x['path']):
        url=HF+'/resolve/'+REV+'/'+x['path']; p=scratch/Path(x['path']).name
        if not p.exists():
            ensure_disk(scratch); b,_,_=get(url); p.write_bytes(b)
        b=p.read_bytes(); assert len(b)==x['size'] and digest(b)==x['lfs']['oid'], 'Pinned validation bytes mismatch'
        rows=[json.loads(s) for s in b.splitlines()]; all_val.extend(rows); local=collections.Counter()
        for g in rows:
            counts['rows']+=1;local['rows']+=1
            if g['game-id'] in ids or g['moves-uci'] in seqs:
                counts['duplicates']+=1;local['duplicates']+=1;continue
            ids.add(g['game-id']);seqs.add(g['moves-uci'])
            status, detail=eligibility(g); counts[status]+=1;local[status]+=1
            if status=='eligible': records.append(dict(g,sourceKind='allie-validation',sourceFile=x['path'],source={'kind':'allie-validation','path':x['path'],'revision':REV},selectedPosition=detail))
        sources.append({'url':url,'path':x['path'],'revision':REV,'bytes':len(b),'sha256':digest(b),'counts':dict(local)})
    assert len(records)==121, 'Unexpected validation cohort; investigate before inference'
    print('Validation: 121 eligible new games',flush=True)
    return records,all_val,sources,dict(counts)

def decompress_prefix(data):
    chunks=[]
    while data:
        d=zstd.ZstdDecompressor();chunks.append(d.decompress(data))
        if not d.eof: break
        data=d.unused_data
    return codecs.getincrementaldecoder('utf-8')().decode(b''.join(chunks), final=False)

HEADER = re.compile(r'^\[([^ ]+) "(.*)"\]$', re.M)
def normalize_pgn(text):
    game=chess.pgn.read_game(io.StringIO(text))
    if game is None or game.errors: raise ValueError('Invalid PGN replay')
    if game.headers.get('SetUp')=='1' or 'FEN' in game.headers or game.headers.get('Variant','Standard')!='Standard': raise ValueError('Nonstandard start')
    h=game.headers; base,inc=map(int,h['TimeControl'].split('+')); clocks=[base,base];moves=[];seconds=[]
    for ply,node in enumerate(game.mainline()):
        clock=node.clock()
        if clock is None or not math.isfinite(clock) or clock<0: raise ValueError('Missing/invalid clock')
        clock=int(clock) # Match the official ALLIE process-lichess.py convention.
        side=ply%2;seconds.append(clocks[side]-clock+inc);clocks[side]=clock;moves.append(node.move.uci())
    return {'game-id':h['Site'],'moves-uci':' '.join(moves),'moves-seconds':seconds,'event':h['Event'],'result':h['Result'],'white-elo':h['WhiteElo'],'black-elo':h['BlackElo'],'termination':h['Termination'],'time-control':h['TimeControl'],'opening':h.get('Opening',''),'utc-date':h.get('UTCDate'),'utc-time':h.get('UTCTime')}

def raw_pool(scratch, prefix_bytes, excluded, checksums):
    ids={g['game-id'] for g in excluded};seqs={g['moves-uci'] for g in excluded};pool=[];sources=[]
    for month in range(1,13):
        ensure_disk(scratch); name=f'lichess_db_standard_rated_2022-{month:02d}.pgn.zst';url=LICHESS+name;p=scratch/(name+'.prefix')
        have=p.stat().st_size if p.exists() else 0
        assert have<=prefix_bytes, 'Scratch contains a larger prefix than requested'
        response_headers={}; response_method='GET'; response_purpose='prefix-download'
        sidecar=p.with_name(p.name+'.http.json')
        if have<prefix_bytes:
            b,response_headers,status=get(url,{'Range':f'bytes={have}-{prefix_bytes-1}'})
            assert status==206, 'Range ignored; refusing full archive download'
            cr=response_headers.get('Content-Range') or response_headers.get('content-range')
            assert cr and cr.startswith(f'bytes {have}-{prefix_bytes-1}/') and len(b)==prefix_bytes-have, 'Unexpected range'
            with p.open('ab') as f:f.write(b)
        b=p.read_bytes();assert len(b)==prefix_bytes
        if prefix_bytes == 8*MIB: assert digest(b)==PREFIX_8MIB_SHA256[name], 'Pinned archive prefix bytes mismatch'
        # Preserve actual response metadata across cached reproduction runs.
        # The first collection's GET headers were lost by an earlier cached
        # rerun, so recover response identity truthfully with ranged HEAD.
        if not response_headers and sidecar.exists():
            cached=json.loads(sidecar.read_text())
            assert cached['url']==url and cached['prefixSha256']==digest(b)
            response_headers=cached['headers'];response_method=cached['method'];response_purpose=cached['purpose']
        elif not response_headers:
            _,response_headers,status=get(url,{'Range':f'bytes=0-{prefix_bytes-1}'},method='HEAD')
            cr=response_headers.get('Content-Range') or response_headers.get('content-range')
            assert status==206 and cr and cr.startswith(f'bytes 0-{prefix_bytes-1}/'), 'Cached range identity revalidation failed'
            assert int(response_headers.get('Content-Length') or response_headers.get('content-length'))==prefix_bytes
            response_method='HEAD';response_purpose='cached-prefix-revalidation; initial GET response headers unavailable'
        identity={k:v for k,v in response_headers.items() if k.lower() in ['content-range','content-length','last-modified','etag','date']}
        sidecar.write_text(json.dumps({'url':url,'prefixSha256':digest(b),'method':response_method,'purpose':response_purpose,'status':206,'headers':identity},indent=2)+'\n')
        text=decompress_prefix(b);starts=[m.start() for m in re.finditer(r'^\[Event ',text,re.M)]
        counts=collections.Counter();dates=[]
        for first,last in zip(starts,starts[1:]):
            block=text[first:last];h=dict(HEADER.findall(block));counts['complete_games']+=1
            # Headers can reject non-target games without parsing their moves.
            try: rating_match=all(2500<=int(h[s+'Elo'])<=2700 for s in ['White','Black'])
            except (KeyError,TypeError,ValueError):counts['missing_ratings']+=1;continue
            if not rating_match:counts['outside_band']+=1;continue
            counts['rating_matches']+=1
            if not h.get('Event','').startswith('Rated Blitz') or h.get('Termination')!='Normal' or h.get('Result') not in ['1-0','0-1','1/2-1/2']:
                counts['event_or_result_excluded']+=1;continue
            if h.get('Site') in ids:counts['duplicate_id']+=1;continue
            try:g=normalize_pgn(block)
            except (ValueError,KeyError,TypeError,AssertionError):counts['invalid_pgn_or_clocks']+=1;continue
            if g['moves-uci'] in seqs:counts['duplicate_sequence']+=1;continue
            ids.add(g['game-id']);seqs.add(g['moves-uci'])
            status,detail=eligibility(g);counts[status]+=1
            if status=='eligible':
                dates.append(g['utc-date']);pool.append(dict(g,sourceKind='lichess-archive-prefix',sourceFile=name,source={'kind':'lichess-archive-prefix','archive':name,'prefixBytes':prefix_bytes},selectedPosition=detail))
        source={'url':url,'archive':name,'publishedArchiveSha256':checksums[name],'prefixBytes':len(b),'prefixSha256':digest(b),'decodedBytes':len(text.encode()),'counts':dict(counts),'eligibleDateRange':[min(dates),max(dates)] if dates else None,'trailingGameDiscarded':bool(starts)}
        source.update(http=identity,responseMethod=response_method,responsePurpose=response_purpose,responseStatus=206)
        sources.append(source);print(f'{name}: {counts["complete_games"]} complete; {counts["eligible"]} eligible; cumulative {len(pool)}',flush=True)
    validate_unique(pool)
    return pool,sources

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--original',type=Path,required=True);parser.add_argument('--scratch',type=Path,required=True);parser.add_argument('--out',type=Path,default=ROOT/'data');args=parser.parse_args()
    args.scratch.mkdir(parents=True,exist_ok=True);before=ensure_disk(args.scratch)
    b=args.original.read_bytes();assert digest(b)==ORIGINAL_HASH,'Wrong original source';original=[json.loads(s) for s in b.splitlines()]
    val,all_val,val_sources,val_counts=monthly(args.scratch,original)
    sums,_,_=get(LICHESS+'sha256sums.txt');checksums={parts[1]:parts[0] for line in sums.decode().splitlines() if len(parts:=line.split())==2}
    assert all(checksums.get(name)==sha for name,sha in ARCHIVE_SHA256.items()), 'Published archive checksum changed; investigate before collection'
    stages=[]
    for size in [8*MIB,16*MIB,32*MIB]:
        pool,sources=raw_pool(args.scratch,size,original+all_val,checksums)
        stages.append({'prefixBytesPerMonth':size,'eligibleRawGames':len(pool),'sources':sources})
        if len(pool)>=154:break
    assert len(pool)>=154,'Maximum prefix budget exhausted with insufficient games'
    raw_selected=sorted(pool,key=lambda g:priority('game',g['game-id']))[:154]
    records=sorted(val,key=lambda g:priority('game',g['game-id']))+raw_selected
    assert len(records)==275;validate_unique(records)
    assert not ({g['game-id'] for g in records}&{g['game-id'] for g in original})
    assert not ({g['moves-uci'] for g in records}&{g['moves-uci'] for g in original})
    assert all(eligibility(g)[0]=='eligible' for g in records)
    args.out.mkdir(parents=True,exist_ok=True);out=args.out/'supplement-games.jsonl'
    out.write_text(''.join(json.dumps(g,separators=(',',':'),allow_nan=False)+'\n' for g in records))
    report={'schemaVersion':1,'sourceRevision':REV,'originalSourceSha256':ORIGINAL_HASH,'selectionSeed':SEED,'selection':'All 121 eligible validation games; 154 raw games by ascending SHA256 of 2026102701|game|<game-id> after all 12 equal prefixes. Position by original position hash. No model inference.','clockConversion':'Integer node.clock() as in official ALLIE process-lichess.py: seconds = previous remaining - integer post-move clock + increment; begin each side at base time.','upstreamProcessingCode':'https://github.com/ippolito-cmu/allie/blob/fcaf285a48d0f3f0df0e2d2666bbca32b720d884/src/data/process-lichess.py','license':'Underlying Lichess exports CC0; pinned ALLIE repository has no explicit dataset/annotation license metadata. No Stockfish annotations used.','validationSources':val_sources,'validationCounts':val_counts,'rawStages':stages,'selectedGames':len(records),'selectedValidationGames':len(val),'selectedRawGames':len(raw_selected),'selectedIds':{'validation':[g['game-id'] for g in records if g['source']['kind']=='allie-validation'],'raw':[g['game-id'] for g in raw_selected]},'outputSha256':digest(out.read_bytes()),'collectorSha256':digest(Path(__file__).read_bytes()),'python':sys.version.split()[0],'chess':chess.__version__,'diskFreeBefore':before,'diskFreeAfter':ensure_disk(args.scratch),'limitations':['Expansion follows inspection of the original 225-game results; disclose this sequential augmentation.','Raw prefixes concentrate the first part of each month, rather than sampling the full annual population.','Distinct games can share players and positions; game bootstrap does not capture all dependence.','2022 precedes the declared Maia-3 training window but ALLIE is an established benchmark; development exposure and position overlap are not ruled out.'],'deduplication':'Exact game ID and exact complete UCI move sequence against all 18,239 original games and every monthly validation row; across eligible raw candidates and all selected supplement records. Raw headers prefilter the requested rating/event/termination cohort before move normalization.'}
    (args.out/'supplement-sources.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'selected':len(records),'validation':len(val),'raw':len(raw_selected),'rawPool':len(pool),'prefixBytesPerMonth':size,'outputSha256':report['outputSha256']}),flush=True)

if __name__=='__main__':main()
