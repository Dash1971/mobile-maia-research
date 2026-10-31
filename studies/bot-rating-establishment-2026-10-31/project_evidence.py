#!/usr/bin/env python3
"""Audit a retained final evidence copy and export whitelisted public research data.

No service, network, database, inference or fit operation exists in this script.
Never copy private fitted artifacts, raw Mongo records, environments or backups.
"""
import argparse
from collections import Counter
import csv
import datetime as dt
import gzip
import hashlib
import json
import math
from pathlib import Path
import re
import shutil

from verify_public import RUN, MAIN, MODEL, ROSTER, ORIGINAL, PREDICTOR, SPEEDS, read, loads, sha, digest, require, perfs, flags, policy, verify

REQUIRED = ('checkpoint.json','events.jsonl','supervisor.json','resources.jsonl','combined-roster.json',
    'experiment-manifest.json','original-experiment-manifest.json','establishment-manifest.json','initial-ratings.json',
    'training-ratings.json','frozen-predictor.json','establishment-freeze.json','final-ratings.json',
    'final-records.json','establishment-final.json','heldout-evaluation.json','public-bot-perfs-before.json')


def write(path, value):
    Path(path).write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n')


def write_rows(path, values):
    with Path(path).open('wb') as raw, gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0) as compressed:
        for value in values: compressed.write((json.dumps(value,separators=(',',':'),ensure_ascii=False,allow_nan=False)+'\n').encode())


def moment(value):
    return dt.datetime.fromisoformat(value.replace('Z','+00:00')).timestamp()


def clean(value):
    if isinstance(value,str):
        require(not any(mark in value for mark in ('/Users/','/home/','/etc/','/srv/','/opt/','/private/','nsec1','BEGIN PRIVATE KEY')),
                'Private path/key marker in public projection')
    elif isinstance(value,list):
        for item in value: clean(item)
    elif isinstance(value,dict):
        for key,item in value.items():
            require(key not in ('coefficients','ADAPTER_TOKEN','privateKey','ciphertext','environment'), 'Private field in public projection')
            clean(item)
    elif isinstance(value,float): require(math.isfinite(value),'Nonfinite public projection')


def scalar(value):
    if isinstance(value,dict):
        require(len(value)==1 and next(iter(value)) in ('$numberLong','$numberInt','$numberDouble'), 'Unsupported BSON numeric wrapper')
        value=next(iter(value.values()))
    number=float(value);require(math.isfinite(number),'Nonfinite native scalar')
    return int(number) if number.is_integer() else number


def check_native(path, raw, bots, initial, final, records, counts):
    receipt=read(path);proof=receipt['proof'];expected={bot['username'].lower():bot['id'] for bot in bots}
    users={row['_id']:row for row in receipt['users']};actual={row['_id']:row for row in receipt['perfs']}
    before={row['_id']:row for row in read(raw/'public-bot-perfs-before.json')}
    require(set(users)==set(actual)==set(before)==set(expected) and len(users)==250,'Independent native roster/perf set differs')
    require(all(row.get('noSweatBot') is True and row.get('enabled') is True and row.get('title')=='BOT' and row.get('noSweatSeedVersion')
                for row in users.values()),'Independent native BOT identity metadata differs')
    require(receipt['otherPublicGames']==[],'Non-study public activity requires separate attribution; do not silently drop it')
    native_records={row['id']:row for row in receipt['records']};require(native_records==records,'Native DB study records differ from driver records')
    games={row['_id']:row for row in receipt['games']};require(set(games)==set(records),'Native persisted game IDs differ')
    for game_id,game in games.items():
        record=records[game_id]
        require(game['ra'] is True and scalar(game['s'])>25 and scalar(game['t'])==record['result']['plies'] and
            game['us']==[next(b['username'].lower() for b in bots if b['id']==record[side]) for side in ('white','black')],
            'Native game rated/state/plies/seats differ')
    for username,identity in expected.items():
        for speed in SPEEDS:
            require(scalar(before[username][speed]['nb'])==initial[identity][speed]['games'] and
                scalar(actual[username][speed]['nb'])==final[identity][speed]['games'] and
                scalar(actual[username][speed]['nb'])-scalar(before[username][speed]['nb'])==counts[(identity,speed)],
                'Independent per-bot/speed native counts differ')
            require(scalar(actual[username][speed]['gl']['r'])==final[identity][speed]['rating'],'Persisted native final rating differs')
        for speed in ('ultraBullet','bullet','classical','correspondence'):
            require(before[username].get(speed)==actual[username].get(speed),'An untargeted speed perf changed')
    for key,value in {'run':RUN,'nativeUsers':250,'nativePerfs':250,'nativeStudyRecords':826,'nativeGame5Records':826,
        'activeOwnedNativeGames':0,'activeOwnedStudyRecords':0,'ratedResults':826,'ratedPlayerCountIncrements':1652,
        'perBotSpeedCountsMatch':True,'otherPublicGamesDuringRun':0,'otherSpeedPerfsUnchanged':True,
        'nativeNonprovisionalBlitz':250,'nativeNonprovisionalRapid':250,'nativeBotsEstablishedBoth':250,'apiStatus':200}.items():
        require(proof[key]==value,'Independent native proof differs: '+key)
    api={row['id']:row for row in receipt['nativeApi']};require(set(api)==set(expected),'Independent native API population differs')
    require(all(api[u]['perfs'][s].get('prov',False) is False and api[u]['perfs'][s]['games']==final[i][s]['games']
                for u,i in expected.items() for s in SPEEDS),'Independent native API flags/counts differ')
    return {key:proof[key] for key in ('observedAtUtc','run','nativeUsers','nativePerfs','nativeStudyRecords','nativeGame5Records',
        'activeOwnedNativeGames','activeOwnedStudyRecords','ratedResults','ratedPlayerCountIncrements','perBotSpeedCountsMatch',
        'otherPublicGamesDuringRun','otherSpeedPerfsUnchanged','nativeNonprovisionalBlitz','nativeNonprovisionalRapid','nativeBotsEstablishedBoth','apiStatus')}


def audit(raw, output, native_audit=None):
    raw=Path(raw).resolve();output=Path(output).resolve()
    require(not output.exists() and raw not in output.parents and output not in raw.parents,'Fresh separate output required')
    for name in REQUIRED:
        require((raw/name).is_file() and not (raw/name).is_symlink(),'Missing/linked retained input: '+name)
    blobs={name:(raw/name).read_bytes() for name in REQUIRED}
    require(blobs['events.jsonl'].endswith(b'\n'),'Final event stream has an incomplete trailing row')
    checkpoint=loads(blobs['checkpoint.json']);bots=loads(blobs['combined-roster.json']);bot_map={b['id']:b for b in bots}
    manifest=loads(blobs['original-experiment-manifest.json']);metadata=loads(blobs['establishment-manifest.json'])
    require(sha(raw/'original-experiment-manifest.json')==ORIGINAL and digest(bots)==ROSTER and len(bot_map)==250,'Original source/roster commitment differs')
    require(loads(blobs['experiment-manifest.json'])==manifest,'Driver original manifest changed logical contents')
    training=set(manifest['trainingIds']);heldout=set(manifest['heldoutIds'])
    require(metadata['originalManifestSha256']==ORIGINAL and metadata['combinedRosterSha256']==ROSTER and
        metadata['trainingIds']==manifest['trainingIds'] and metadata['heldoutIds']==manifest['heldoutIds'],'New manifest split/hash differs')
    initial=loads(blobs['initial-ratings.json']);frozen=loads(blobs['training-ratings.json']);final=loads(blobs['final-ratings.json'])
    for values in (initial,frozen,final):perfs(values,bot_map)
    last=checkpoint['latest'];established=loads(blobs['establishment-final.json']);freeze=loads(blobs['establishment-freeze.json'])
    require(checkpoint['run']==RUN and checkpoint['main']==MAIN and checkpoint['publicRatings'] is True and not checkpoint.get('failure') and
        last['runId']==RUN and last['profile']=='rating-establishment-v1' and last['publicRatings'] is True and last['closed'] is True and
        last['admitted']==826 and last['games']==[] and last['publicGames']==0,'Final native/driver checkpoint is not cleanly closed')
    require(initial==checkpoint['initial']['ratings'] and final==last['ratings'] and checkpoint['establishment']==established and
        established['epoch']=='complete' and established['modelFrozen'] is True and established['trainingRemaining']==established['heldoutRemaining']==0 and
        established['remaining']==[] and established['freeze']==freeze and established['metadata']==metadata,'Final establishment evidence differs')
    require(flags(final)=={'blitz':250,'rapid':250},'Final500 native flags not reached')
    model=loads(blobs['frozen-predictor.json'])
    require(freeze['admitted']==349 and freeze['modelSha256']==sha(raw/'frozen-predictor.json') and
        freeze['trainingSnapshotSha256']==sha(raw/'training-ratings.json') and freeze['predictorSourceSha256']==PREDICTOR and
        model['version']==metadata['procedure']==freeze['modelVersion']=='strength137-ridge-rbf-effective-cv-v2' and
        model['rosterSha256']==ROSTER and model['trainingIds']==manifest['trainingIds'] and model['heldoutIds']==manifest['heldoutIds'],
        'Frozen V2 model/snapshot/source commitment differs')
    require(all(not frozen[i][s]['provisional'] for i in training for s in SPEEDS),'Training400 not established at freeze')
    events=[loads(line) for line in blobs['events.jsonl'].splitlines()]
    require(all(moment(a['at'])<=moment(b['at']) for a,b in zip(events,events[1:])),'Event clock order regressed')
    kinds=Counter(e['type'] for e in events)
    require(kinds['start']==kinds['end']==kinds['predictions-frozen']==kinds['establishment-goal-reached']==1 and
        kinds['admission']==kinds['finish']==826 and not any(kinds[k] for k in ('failure','checkpoint-error','stop-error')),'Driver event accounting/failure differs')
    start=events[0];end=events[-1]
    require(start['type']=='start' and end['type']=='end' and not end.get('failure') and start['ratings']==initial and
        start['rosterSha256']==ROSTER and start['modelSha256']==MODEL and start['predictorSourceSha256']==PREDICTOR and
        start['profile']=='rating-establishment-v1' and start['workerCount']==2 and start['maximumConcurrency']==22 and
        start['maximumAdmitted']==3000 and start['admittedAtStart']==0 and start['clocks']=={'blitz':'5+3','rapid':'10+5'},'Start/end fixed scope differs')
    freeze_index,freeze_event=next((i,e) for i,e in enumerate(events) if e['type']=='predictions-frozen')
    require(all(freeze_event[k]==v for k,v in freeze.items()) and freeze_event['modelFrozen'] is True,'Freeze receipt/event differ')
    admissions=[(i,e) for i,e in enumerate(events) if e['type']=='admission'];finishes={}
    for i,event in enumerate(events):
        if event['type']=='finish':require(event['id'] not in finishes,'Duplicate finish ID');finishes[event['id']]=(i,event)
    records_list=loads(blobs['final-records.json']);records={r['id']:r for r in records_list}
    require(len(records)==len(records_list)==826 and records=={r['id']:r for r in last['records']} and
        set(records)==set(finishes)=={e['id'] for _,e in admissions},'Unique admission/finish/native record sets differ')
    games=[];counts=Counter()
    for ordinal,(index,event) in enumerate(admissions,1):
        gid=event['id'];record=records[gid];finish_index,finish=finishes[gid]
        require(all(record[k]==event[k]==finish[k] for k in ('white','black','speed')) and
            record['result']==finish['result'] and record['state']==finish['state']=='finished' and record['result']['ratedUpdate'] is True,
            'Admission/finish/native record differs')
        projected={k:record[k] for k in ('id','white','black','speed','state','result')}
        projected.update(runId=RUN,admissionOrdinal=ordinal,admittedAtUtc=event['at'],finishedAtUtc=finish['at'],
            admissionEventIndex=index,finishEventIndex=finish_index,epoch=event['stage'],modelFrozen=event['modelFrozen'])
        policies={}
        for side in ('white','black'):
            wrapper=event['policies'][side];prod=dict(wrapper['production']);seed=prod.pop('samplingSeed')
            require(re.fullmatch(r'[0-9a-f]{32}',seed) and wrapper['runId']==RUN and wrapper['addedHumanWait'] is False and wrapper['rated'] is True,
                    'Study sampling seed/no-wait policy differs')
            policy(prod,bot_map[event[side]])
            policies[side]={k:wrapper[k] for k in ('version','runId','addedHumanWait','rated')};policies[side]['production']=prod
            counts[(event[side],event['speed'])]+=1
        projected['policies']=policies;games.append(projected)
    acknowledgments=[];moves={gid:{} for gid in records};progress=[];epochs=[];known_epoch='training';model_frozen=False
    for index,event in enumerate(events):
        kind=event['type']
        if kind=='move':
            gid,ply=event['id'],event['ply'];require(gid in moves and ply not in moves[gid],'Unknown/duplicate ACK position')
            moves[gid][ply]=event['move']
            row={k:event[k] for k in ('id','ply','move','worker','inferenceMs','totalMs','beforeCommitMs','turnToCommitMs','addedWaitMs','concurrency')}
            row.update(at=event['at'],eventIndex=index);acknowledgments.append(row)
        elif kind=='ratings':
            perfs(event['ratings'],bot_map)
            progress.append({'at':event['at'],'eventIndex':index,'completed':event['completed'],'epoch':known_epoch,
                'modelFrozen':model_frozen,'ratings':event['ratings']})
        elif kind in ('establishment-epoch','predictions-frozen','establishment-goal-reached'):
            if kind=='predictions-frozen':model_frozen=True;known_epoch='heldout'
            else:known_epoch=event['epoch']
            row={k:event[k] for k in ('epoch','modelFrozen','trainingRemaining','heldoutRemaining','admitted') if k in event}
            row.update(type=kind,at=event['at'],eventIndex=index);epochs.append(row)
    for game in games:
        values=moves[game['id']];require(set(values)==set(range(game['result']['plies'])),'Incomplete ACK sequence')
        game['moves']=[values[i] for i in range(len(values))]
    goal=next(e for e in events if e['type']=='establishment-goal-reached')
    require(goal['epoch']=='complete' and goal['trainingRemaining']==goal['heldoutRemaining']==0 and goal['remaining']==[] and
        goal['at']==established['goalReachedAtUtc'],'Goal event/final native status differ')
    supervisor=loads(blobs['supervisor.json'])
    require(supervisor['run']==RUN and supervisor['commit']==MAIN and supervisor['profile']=='rating-establishment-v1' and
        supervisor['reason']=='completed' and supervisor['configurationRestored'] is True and supervisor['continuation'] is None and
        supervisor['inferenceBudget']=={'workers':2,'cpu':'400%','memory':'2000M'},'Supervisor did not record normal restored completion')
    require(all(moment(e['at'])<supervisor['admissionEnd']/1000 for _,e in admissions) and
        moment(end['at'])<=supervisor['deadline']/1000,'Dated admission/hard stop exceeded')
    evaluation=loads(blobs['heldout-evaluation.json']);clean(evaluation)
    require(set(evaluation)=={'version','evaluatorVersion','targetMae','speeds','noisyLabelTargetMet','interpretation'} and
        evaluation['version']==evaluation['evaluatorVersion']==model['version'],'Fixed evaluator/version shape differs')
    for speed in SPEEDS:
        require(set(evaluation['speeds'][speed])=={'configurations','nativeRatingMae','configurationBootstrapMae95','medianNativeRd',
            'frozenOutcomeGames','brier','expectedScoreCrossEntropy','meetsNoisyLabelMaeTarget','details'},'Unexpected evaluation fields')
        for detail in evaluation['speeds'][speed]['details']:
            require(set(detail)=={'id','prediction','nativeRating','rd','nativeGames','absoluteError'} and detail['id'] in heldout,
                'Unexpected evaluation detail fields')
    native=check_native(native_audit,raw,bots,initial,final,records,counts) if native_audit else {'present':False,'reason':'Independent native receipt not supplied'}
    output.mkdir(parents=True);data=output/'data';data.mkdir();(data/'pgns').mkdir()
    for src,dst in [('combined-roster.json','configurations.json'),('original-experiment-manifest.json','original-design-manifest.json'),
        ('establishment-manifest.json','establishment-manifest.json'),('initial-ratings.json','initial-native-perfs.json'),
        ('training-ratings.json','frozen-training-perfs.json'),('final-ratings.json','final-native-perfs.json'),('heldout-evaluation.json','evaluation.json')]:
        clean(loads(blobs[src]));(data/dst).write_bytes(blobs[src])
    for game in games:
        pgn=raw/(game['id']+'.pgn');require(pgn.is_file() and not pgn.is_symlink(),'Missing/linked final PGN')
        clean(pgn.read_text());shutil.copyfile(pgn,data/'pgns'/pgn.name)
    for name,values in [('games',games),('acknowledged-moves',acknowledgments),('native-progress',progress),('epoch-events',epochs)]:
        clean(values);write_rows(data/(name+'.jsonl.gz'),values)
    resources=[]
    for line in blobs['resources.jsonl'].splitlines():
        row=loads(line);groups={'worker':row['worker'],**row.get('services',{})}
        projected={'at':row['at'],'health':{k:v for k,v in row.get('health',{}).items() if k in ('status','ms')},
            'cgroups':{role:{k:v for k,v in props.items() if k in ('CPUUsageNSec','MemoryCurrent','MemoryPeak','ActiveState','ExecMainStatus')}
                for role,props in groups.items() if role in ('worker','app','adapter','ws','mongo','redis','gateway')}}
        if 'mongo' in row:projected['mongo']={'storage':row['mongo']['storage'],'ops':{k:v for k,v in row['mongo']['ops'].items()
            if k in ('insert','query','update','delete','getmore','command')}}
        clean(projected);resources.append(projected)
    write_rows(data/'resources-projection.jsonl.gz',resources)
    with (data/'frozen-predictions-v2.csv').open('w',newline='') as stream:
        writer=csv.writer(stream);writer.writerow(['id','speed','prediction'])
        for identity in sorted(bot_map):
            for speed in SPEEDS:
                value=model['speeds'][speed]['predictions'][identity]['rating'];require(math.isfinite(value),'Nonfinite frozen prediction')
                writer.writerow([identity,speed,repr(value)])
    fields=['id','cohort','speed','recordedRosterSeed','initialNativeRating','finalNativeRating','ratingChangeThisRun','absoluteRatingChange',
        'initialRd','finalRd','initialGames','finalGames','nativeGamesAdded','studyRatedAppearances','studyAdmissions','admittedAsWhite','admittedAsBlack',
        'initialProvisional','finalProvisional']
    with (data/'ratings.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader()
        for identity in sorted(bot_map):
            for speed in SPEEDS:
                a,b=initial[identity][speed],final[identity][speed]
                writer.writerow({'id':identity,'cohort':'original44' if identity in manifest['existingIds'] else 'heldout50' if identity in heldout else 'new156',
                    'speed':speed,'recordedRosterSeed':bot_map[identity]['ratings'][speed]['initial_rating'],
                    'initialNativeRating':a['rating'],'finalNativeRating':b['rating'],'ratingChangeThisRun':b['rating']-a['rating'],
                    'absoluteRatingChange':abs(b['rating']-a['rating']),'initialRd':a['rd'],'finalRd':b['rd'],'initialGames':a['games'],'finalGames':b['games'],
                    'nativeGamesAdded':b['games']-a['games'],'studyRatedAppearances':counts[(identity,speed)],'studyAdmissions':counts[(identity,speed)],
                    'admittedAsWhite':sum(g['white']==identity and g['speed']==speed for g in games),
                    'admittedAsBlack':sum(g['black']==identity and g['speed']==speed for g in games),
                    'initialProvisional':a['provisional'],'finalProvisional':b['provisional']})
    summary={'schemaVersion':'night163-execution-projection-v1','run':RUN,'main':MAIN,'workerStartedAtUtc':start['at'],'workerEndedAtUtc':end['at'],
        'goalReachedAtUtc':goal['at'],'reason':'completed','configurationRestoredRecorded':True,'admitted':826,'finishedRated':826,
        'aborted':0,'unfinished':0,'trainingFinishedBeforeFreeze':349,'heldoutFollowupGames':sum(g['epoch']=='heldout' for g in games),
        'initialNonprovisional':flags(initial),'finalNonprovisional':flags(final),'uniqueAcknowledgedPlies':len(acknowledgments),
        'resourceSamples':len(resources),'nativeProgressSamples':len(progress),'noFurtherGamesAuthorizedByPublication':True}
    write(data/'execution-summary.json',summary);write(data/'native-count-audit.json',native)
    lineage={'schemaVersion':'night163-public-integrity-v1','run':RUN,'main':MAIN,'modelSha256':MODEL,
        'freeze':{**freeze,'eventIndex':freeze_index,'eventAtUtc':freeze_event['at']},'goalReachedAtUtc':goal['at'],
        'rawFittedArtifactIncluded':False,'rawSamplingSeedsIncluded':False,'rawNativeDatabaseDocumentsIncluded':False,
        'rawSourceArtifacts':{name:sha(raw/name) for name in REQUIRED},'nativeReceiptSha256':sha(native_audit) if native_audit else None,
        'extractorSourceSha256':sha(Path(__file__)),'publicVerifierSourceSha256':sha(Path(__file__).with_name('verify_public.py')),
        'omissions':'No environment, credentials, private keys, raw DB documents, fitted coefficients, neural weights, backup paths or ciphertext.',
        'artifacts':{str(p.relative_to(output)):sha(p) for p in sorted(data.rglob('*')) if p.is_file()}}
    clean(lineage);write(data/'integrity-lineage.json',lineage)
    report=verify(output);write(output/'audit-report.json',report)
    shutil.copyfile(Path(__file__).with_name('verify_public.py'),output/'verify_public.py')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--native-audit',type=Path)
    args=parser.parse_args();report=audit(args.evidence,args.output,args.native_audit)
    print(json.dumps({k:report[k] for k in ('finishedRatedGames','uniqueVerifiedPlies','finalNonprovisional','fitOrInferencePerformed')}))
