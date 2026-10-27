"""Append the fixed 275-game supplement; preserve initial predictions and diagnostic."""
from pathlib import Path
import argparse,collections,json,math,shutil,time
import numpy as np
from study import ROOT,MODEL_HASH,SOURCE_HASH,Model,digest,read_rows,write_rows,board_from_row

p=argparse.ArgumentParser();p.add_argument('--model',type=Path,required=True);a=p.parse_args()
data=ROOT/'data';initial=read_rows(data/'sample.jsonl');oldpred=read_rows(data/'predictions.jsonl')
assert collections.Counter(r['elo'] for r in initial)=={1600:500,2600:225},'Run initial study first; expansion is not applied twice'
assert len(oldpred)==1450
for name in ['sample.jsonl','predictions.jsonl','selection.json','summary.json','run.json']:
 shutil.copyfile(data/name,data/('initial-'+name))
supp=read_rows(data/'supplement-games.jsonl');assert len(supp)==275
additional=[]
for g in supp:
 r=g['selectedPosition'].copy();r['sourceKind']=g['sourceKind'];r['sourceFile']=g['sourceFile'];r['consistency']=False
 assert r['elo']==2600 and r['termination']=='Normal'
 assert all(2500<=r[k]<=2700 for k in ['whiteElo','blackElo'])
 assert r['game']==g['game-id'] and r['result']==g['result']
 board_from_row(r);additional.append(r)
assert len({r['game'] for r in initial+additional})==1000
model=Model(a.model);pred=[];start=time.monotonic()
for i,r in enumerate(additional):
 for enabled in [True,False]:
  _,v=model.predict(r['history'],2600,enabled)
  pred.append(dict(game=r['game'],elo=2600,history=enabled,actualWhiteScore=r['actualWhiteScore'],**v))
 if (i+1)%25==0:print('Additional games',i+1,'/',len(additional),flush=True)
sample=initial+additional;write_rows(data/'sample.jsonl',sample);write_rows(data/'predictions.jsonl',oldpred+pred)
selection=json.loads((data/'initial-selection.json').read_text());selection['initialCounts']=selection.pop('counts');selection['counts']={'1600_selected_games':500,'2600_selected_games':500,'initial_2600':225,'supplement_2600':275,'timeForfeitGames':0};selection['supplementSourceManifest']='supplement-sources.json'
rows=[r for r in sample if r['elo']==2600]
selection['coverage']['2600']={'games':500,'termination':dict(collections.Counter(r['termination'] for r in rows)),'results':dict(collections.Counter(r['result'] for r in rows)),'timeControls':dict(collections.Counter(r['timeControl'] for r in rows)),'sideToMove':dict(collections.Counter(r['history'][-1].split()[1] for r in rows)),'stages':dict(collections.Counter('11-20' if r['ply']//2+1<=20 else '21-40' if r['ply']//2+1<=40 else '41+' for r in rows)),'whiteRatingRange':[min(r['whiteElo'] for r in rows),max(r['whiteElo'] for r in rows)],'blackRatingRange':[min(r['blackElo'] for r in rows),max(r['blackElo'] for r in rows)],'meanWhiteRating':float(np.mean([r['whiteElo'] for r in rows])),'meanBlackRating':float(np.mean([r['blackElo'] for r in rows])),'sourceCounts':dict(collections.Counter(r.get('sourceKind','initial-allie-test') for r in rows))}
selection['sampleSha256']=digest(data/'sample.jsonl');selection['protocolSha256']=digest(ROOT/'PROTOCOL.md');(data/'selection.json').write_text(json.dumps(selection,indent=2))
run=json.loads((data/'initial-run.json').read_text());run.update(sampleSha256=digest(data/'sample.jsonl'),protocolSha256=digest(ROOT/'PROTOCOL.md'),stage='expanded: initial predictions retained, 275 additional games inferred',expansionScriptSha256=digest(Path(__file__)),collectorScriptSha256=digest(ROOT/'collect_supplement.py'),expansionSeconds=time.monotonic()-start,initialRun='initial-run.json',supplementSources='supplement-sources.json')
run['files']={name:digest(data/name) for name in ['sample.jsonl','predictions.jsonl','consistency.jsonl','supplement-games.jsonl','supplement-sources.json']};(data/'run.json').write_text(json.dumps(run,indent=2))
# Keep the stage difference visible; no new fitted model or calibration transform.
comparison={}
for label,group in [('original225',initial[500:]),('additional275',additional),('combined500',rows)]:
 ids={r['game'] for r in group};matched=[r for r in oldpred+pred if r['elo']==2600 and r['history'] and r['game'] in ids];assert len(matched)==len(group)
 y=np.array([r['actualWhiteScore'] for r in matched]);q=np.array([r['whiteScore'] for r in matched]);comparison[label]={'games':len(matched),'meanPrediction':float(q.mean()),'meanActualScore':float(y.mean()),'mse':float(np.mean((q-y)**2)),'baselineMse':float(np.mean((.5-y)**2)),'whiteBias':float(np.mean(q-y))}
(data/'expansion-comparison.json').write_text(json.dumps(comparison,indent=2));print(json.dumps(comparison,indent=2))
