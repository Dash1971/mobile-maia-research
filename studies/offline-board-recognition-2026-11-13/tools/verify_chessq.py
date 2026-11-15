#!/usr/bin/env python3
"""Independently recompute published ChessQ scores using no ML or downloads."""
import csv
import hashlib
import json
import math
from pathlib import Path

from verify_results import expand, score

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data/chessq'
MODELS = ['v4_fp16', 'v4_int8', 'v5_int8']
ROUTES = ['full_photo', 'common_crop']


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    original = json.loads((ROOT / 'data/predictions.json').read_text())
    truth = {r['id']: r['expected'] for r in original}
    frames = {r['id']: r for r in json.loads((ROOT / 'data/frame-hashes.json').read_text())}
    ids = list(truth)
    assert len(ids) == 12 and len(set(truth.values())) == 10
    protocol = json.loads((DATA / 'protocol.json').read_text())
    frozen = json.loads((DATA / 'fp16-protocol.json').read_text())
    assert protocol['previousProtocolSha256'] == digest(DATA / 'fp16-protocol.json')
    assert protocol['previousPredictionSha256'] == digest(DATA / 'fp16-predictions.json')
    assert protocol['truthSha256'] == frozen['truthSha256'] == digest(ROOT / 'data/predictions.json')
    assert frozen['geometrySha256'] == digest(ROOT / 'tools/geometry.py')
    assert protocol['inputs'] == frozen['inputs']
    for row in protocol['inputs']:
        assert row['expected'] == truth[row['id']]
        assert row['commonFrameRgbaSha256'] == frames[row['id']]['rgbaSha256']
    assert len(protocol['tensorHashes']) == 24
    assert {(r['id'],r['route']) for r in protocol['tensorHashes']} == {(i,r) for i in ids for r in ROUTES}
    for r in protocol['tensorHashes']:
        assert len(r['float32NchwSha256']) == 64

    predictions = json.loads((DATA / 'predictions.json').read_text())
    assert len(predictions) == 72
    expected_keys = {(m,i,r) for m in MODELS for i in ids for r in ROUTES}
    lookup = {(r['model'],r['id'],r['route']):r for r in predictions}
    assert len(lookup) == 72 and set(lookup) == expected_keys
    previous = {(r['id'],r['route']):r for r in json.loads((DATA / 'fp16-predictions.json').read_text())}
    assert len(previous) == 24
    for row in predictions:
        assert row['expected'] == truth[row['id']]
        score(row, truth[row['id']])
        assert math.isfinite(row['inferenceSeconds']) and row['inferenceSeconds'] >= 0
        if row['model'] == 'v4_fp16':
            assert row['placement'] == previous[row['id'],row['route']]['placement']
        if row['model'] == 'v5_int8':
            direction = row['direction']
            assert abs(math.hypot(direction['cos'],direction['sin'])-1) < 1e-4
            assert direction['view'] == ('black' if direction['cos'] < math.cos(math.radians(100)) else 'white')

    metrics = {}
    for model in MODELS:
        metrics[model] = {}
        for route in ROUTES:
            rows = [lookup[model,i,route] for i in ids]
            wrong = [score(row,truth[row['id']]) for row in rows]
            metrics[model][route] = dict(photos=len(rows), exactBoards=wrong.count(0),
                                         wrongSquares=sum(wrong),
                                         meanInferenceSeconds=sum(r['inferenceSeconds'] for r in rows)/len(rows))
    expected = {'v4_fp16':[(10,2),(10,3)], 'v4_int8':[(10,2),(10,2)], 'v5_int8':[(7,18),(9,16)]}
    for model in MODELS:
        assert [(metrics[model][r]['exactBoards'],metrics[model][r]['wrongSquares']) for r in ROUTES] == expected[model]
    recorded = json.loads((DATA / 'metrics.json').read_text())
    for model in MODELS:
        for route in ROUTES:
            assert recorded[model][route] == metrics[model][route]
    (DATA / 'metrics.json').write_text(json.dumps(metrics,indent=2)+'\n')
    with (DATA / 'per-photo.csv').open('w',newline='') as file:
        writer = csv.writer(file,lineterminator='\n')
        writer.writerow(['photo','route','V4_FP16_wrong','V4_INT8_wrong','V5_INT8_wrong','V5_view'])
        for ident in ids:
            for route in ROUTES:
                writer.writerow([ident,route]+[64-lookup[m,ident,route]['correct'] for m in MODELS]
                                +[lookup['v5_int8',ident,route]['direction']['view']])
    assert all(lookup['v4_int8',i,'full_photo']['placement'] == lookup['v4_fp16',i,'full_photo']['placement'] for i in ids)
    cap21 = lookup['v5_int8','cap21','full_photo']
    assert expand(cap21['placement']) == expand(truth['cap21'])[::-1]
    assert cap21['direction']['view'] == 'black'

    pins = json.loads((DATA / 'model-pins.json').read_text())
    assert {(r['version'],r['bytes'],r['sha256']) for r in pins} == {
        ('v4',41370398,'89d75e343c5d98f235855a67588efb469a4e7cff1e003ee6b6ee0de67732ae1f'),
        ('v5',35905331,'334c8b19b4f3fd92e95f74ec75e0e34e86e5c95bcd7c090c972d126497bd5da3')}
    assert frozen['modelBytes'] == 63147914
    assert frozen['modelSha256'] == 'fd269bcfdefe6208b75490d7ac72524c0970f8212470a88012ce755b5f092d10'
    apk = json.loads((DATA / 'apk-size-assessment.json').read_text())
    excluded = sum(v['compressedBytes'] for k,v in apk['nativeLibrariesByAbi'].items() if k != 'arm64-v8a')
    assert excluded == apk['otherAbiPayloadBytes'] == 101008848
    assert apk['apkBytes']-excluded == apk['arm64OnlyPayloadEstimateBytes'] == 355780484
    assert apk['arm64PlusV4Int8EstimateBytes'] == 355780484+41370398
    for line in (ROOT / 'SHA256SUMS').read_text().splitlines():
        expected_hash,relative = line.split('  ',1)
        assert digest(ROOT / relative) == expected_hash, relative
    print('ChessQ evidence verified: 72 records, 12 photos / 10 positions, exact FP16 replay, metrics, size estimates and checksums.')


if __name__ == '__main__':
    main()
