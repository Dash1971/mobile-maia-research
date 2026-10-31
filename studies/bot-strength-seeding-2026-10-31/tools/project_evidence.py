#!/usr/bin/env python3
"""Project saved original-segment evidence; never publish raw fitted weights/configs.

Run on a retained private evidence copy, not a service or database. Inputs are
read-only. Output must be new. This does not fit models or run chess inference.
"""
import argparse
from collections import defaultdict
import csv
import gzip
import hashlib
import json
from pathlib import Path
import shutil


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False)+'\n')


def write_jsonl(path, values):
    with path.open('wb') as raw, gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0) as compressed:
        for value in values:
            compressed.write((json.dumps(value, separators=(',', ':'), ensure_ascii=False)+'\n').encode())


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--secondary-private-artifact', type=Path, required=True)
    parser.add_argument('--summary', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args=parser.parse_args()
    evidence=args.evidence.resolve(); output=args.output.resolve()
    assert not output.exists() and evidence not in output.parents and output not in evidence.parents
    output.mkdir(parents=True)
    data=output/'data'; data.mkdir(); (data/'pgns').mkdir()
    read=lambda name: json.loads((evidence/name).read_text())
    checkpoint=read('checkpoint.json'); roster=read('combined-roster.json')
    primary=read('frozen-predictor.json')
    secondary=json.loads(args.secondary_private_artifact.read_text())
    assert primary['version']=='strength137-ridge-rbf-v1'
    assert secondary['version']=='strength137-ridge-rbf-effective-cv-v2'
    assert not checkpoint.get('failure') and checkpoint['latest']['closed'] and not checkpoint['latest']['games']
    records={r['id']:r for r in read('final-records.json')}
    events=[json.loads(line) for line in (evidence/'events.jsonl').read_text().splitlines()]
    admissions=[e for e in events if e['type']=='admission']
    moves=defaultdict(dict); acknowledgments=[]
    for event in events:
        if event['type']!='move': continue
        identity, ply, move=event['id'], event['ply'], event['move']
        assert ply not in moves[identity], 'Repeated acknowledgments must be investigated, not silently removed'
        moves[identity][ply]=move
        acknowledgments.append({'id':identity,'ply':ply,'move':move})
    games=[]
    assert len(admissions)==len(records)==checkpoint['latest']['admitted']
    for ordinal, event in enumerate(admissions,1):
        identity=event['id']; record=records[identity]
        assert record['state']=='finished' and record['result']['ratedUpdate'] is True
        assert set(moves[identity])==set(range(record['result']['plies']))
        assert all(event[k]==record[k] for k in ('white','black','speed'))
        games.append({'id':identity,'admissionOrdinal':ordinal,'segment':'original',
            'admittedAtUtc':event['at'],'stage':event['stage'],
            **{k:record[k] for k in ('white','black','speed','state','result')},
            'moves':[moves[identity][ply] for ply in range(record['result']['plies'])]})
        pgn=evidence/(identity+'.pgn')
        # Headers are public BOT-only games. No private fixture PGNs are accepted.
        text=pgn.read_text()
        assert '[Site "https://mutechess.org/game/'+identity+'"]' in text
        assert '[WhiteTitle "BOT"]' in text and '[BlackTitle "BOT"]' in text
        assert not any(marker in text for marker in ('/Users/','/home/','127.0.0.1','nsec1','BEGIN PRIVATE'))
        shutil.copyfile(pgn,data/'pgns'/pgn.name)
    write_jsonl(data/'games.jsonl.gz',games)
    write_jsonl(data/'acknowledged-moves.jsonl.gz',acknowledgments)
    for source,destination in [('combined-roster.json','configurations.json'),
            ('experiment-manifest.json','design-manifest.json'),
            ('training-ratings.json','frozen-training-perfs.json'),('final-ratings.json','final-native-perfs.json')]:
        shutil.copyfile(evidence/source,data/destination)
    write_json(data/'initial-native-perfs.json',checkpoint['initial']['ratings'])
    for name, model in [('frozen-predictions-v1.csv',primary),('frozen-predictions-v2.csv',secondary)]:
        with (data/name).open('w',newline='') as stream:
            writer=csv.writer(stream);writer.writerow(['id','speed','prediction'])
            for identity in sorted(records_id['id'] for records_id in roster):
                for speed in ('blitz','rapid'):
                    writer.writerow([identity,speed,repr(model['speeds'][speed]['predictions'][identity]['rating'])])
    with (data/'seed-baseline.csv').open('w',newline='') as stream:
        writer=csv.writer(stream);writer.writerow(['id','speed','prediction'])
        for bot in sorted(roster,key=lambda b:b['id']):
            for speed in ('blitz','rapid'):writer.writerow([bot['id'],speed,bot['ratings'][speed]['initial_rating']])
    # Only measured numeric fields; no process arguments, service configurations,
    # paths, environments or raw resource receipts enter this public projection.
    samples=[]
    for line in (evidence/'resources.jsonl').read_text().splitlines():
        row=json.loads(line)
        services={'worker':row['worker'],**row.get('services',{})}
        samples.append({'at':row['at'],'health':{k:v for k,v in row.get('health',{}).items() if k in ('status','ms')},
            'cgroups':{role:{k:v for k,v in props.items() if k in ('CPUUsageNSec','MemoryCurrent','MemoryPeak')}
                for role,props in services.items()}})
    write_jsonl(data/'resources-projection.jsonl.gz',samples)
    summary=json.loads(args.summary.read_text())
    write_json(data/'execution-summary.json',summary)
    shutil.copyfile(args.summary.parent/'ratings.csv',data/'ratings.csv')
    write_json(data/'projection-lineage.json',{
        'schema':'strength137-original-public-projection-v1',
        'rawPrimaryFitArtifactIncluded':False,'rawSecondaryFitArtifactIncluded':False,
        'rawSourceArtifacts':{name:hashlib.sha256((evidence/name).read_bytes()).hexdigest()
            for name in ('checkpoint.json','events.jsonl','resources.jsonl','supervisor.json','frozen-predictor.json',
                         'training-ratings.json','final-ratings.json','final-records.json')},
        'frozenPredictionExtraction':'All250 identities, both speeds; exact Python repr of saved rating predictions; coefficients omitted.',
        'seedBaselineDefinition':'Every identity uses configurations[].ratings[speed].initial_rating; unvalidated published starting prior, not a fitted model.',
        'scope':'Original public BOT-only segment. No private qualification games or human identifiers.'})
    print(json.dumps({'projectedGames':len(games),'acknowledgedMoves':len(acknowledgments),'modelsOrInferenceRun':False}))


if __name__=='__main__':main()
