"""Cross-check selected observations against the pinned source without inference."""
import argparse, hashlib, json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);args=p.parse_args()
raw=args.source.read_bytes();assert hashlib.sha256(raw).hexdigest()=='a6014de8ef861b2ee23a84d7ce824e644390577a000350fad06bd995bcddab0d'
source={g['game-id']:g for g in map(json.loads,raw.splitlines())}
rows=[json.loads(x) for x in (ROOT/'data/sample.jsonl').read_text().splitlines()]
for r in rows:
 g=source[r['game']];ply=r['ply'];moves=g['moves-uci'].split();seconds=g['moves-seconds'];base,inc=map(int,g['time-control'].split('+'))
 assert r['prefixUci']==moves[:ply] and r['playedUci']==moves[ply]
 assert r['result']==g['result'] and r['termination']==g['termination']=='Normal'
 assert r['actualWhiteScore']=={'1-0':1,'0-1':0,'1/2-1/2':.5}[g['result']]
 assert r['whiteElo']==int(g['white-elo']) and r['blackElo']==int(g['black-elo'])
 assert g['event'].startswith('Rated Blitz')
 assert r['timeControl']==g['time-control']
 for j in range(ply+1):
  before=[base+len(seconds[c:j:2])*inc-sum(seconds[c:j:2]) for c in [0,1]]
  assert min(before)>=30 and before[j%2]-seconds[j]>=30
  if j==ply:
   assert before==r['clocksBefore'] and before[j%2]-seconds[j]==r['moverClockAfterThink']
report={'status':'pass','selectedGames':len(rows),'scope':'Independent direct-source comparison of results, ratings, normal termination, game prefixes and every clock threshold through the sampled move. No inference.','sourceSha256':hashlib.sha256(raw).hexdigest(),'sampleSha256':hashlib.sha256((ROOT/'data/sample.jsonl').read_bytes()).hexdigest()}
(ROOT/'data/source-crosscheck.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
