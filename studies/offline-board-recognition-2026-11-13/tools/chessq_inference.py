"""Frozen-photo comparison of installed V4 FP16 and Lichess V4/V5 INT8.

All models receive the exact same tensor, using the previous upstream V4
torchvision preprocessing. Desktop CPU experiment, not Android qualification.
"""
from pathlib import Path
import argparse
import gc
import hashlib
import json
import math
import os
import platform
import resource
import sys
import time
import types

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--input-dir', type=Path, required=True, help='Private normalized PNGs named book.png, screen.png, cap03.png, etc.')
parser.add_argument('--models-dir', type=Path, required=True, help='Local ONNX files matching data/chessq/model-pins.json; nothing is downloaded.')
parser.add_argument('--fp16', type=Path, required=True, help='Original local V4 Safetensors file with the recorded hash.')
parser.add_argument('--upstream', type=Path, required=True, help='Explicitly supplied JSeytre/chessqueries f5aaaf38212cc7839b03ccf383455053905b3f7e source.')
parser.add_argument('--output-dir', type=Path, required=True, help='New task-owned directory outside the repository for fresh outputs.')
args = parser.parse_args()
STUDY = Path(__file__).resolve().parents[1]
REPOSITORY = STUDY.parents[1]
HERE = STUDY / 'data/chessq'
INPUTS = args.input_dir.resolve()
MODELS = args.models_dir.resolve()
UPSTREAM = args.upstream.resolve()
FP16 = args.fp16.resolve()
OUTPUT = args.output_dir.resolve()
if OUTPUT == REPOSITORY or REPOSITORY in OUTPUT.parents:
    parser.error('--output-dir must be outside the repository')
OUTPUT.mkdir(parents=True, exist_ok=False)
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'

import cv2
import numpy as np
from PIL import Image
import onnxruntime as ort
import torch
import torchvision
import timm

ort.disable_telemetry_events()
for name in ['chessqueries', 'chessqueries.models', 'chessqueries.data']:
    module = types.ModuleType(name)
    module.__path__ = [str(UPSTREAM / name.replace('.', '/'))]
    sys.modules[name] = module
from chessqueries.models.checkpoint import load_safetensors_model
from chessqueries.data.transforms import build_transform
sys.path.insert(0, str(STUDY / 'tools'))
from geometry import warp


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def expand(fen):
    out = [v for c in fen.split()[0].replace('/', '')
           for v in (['.'] * int(c) if c.isdigit() else [c])]
    assert len(out) == 64
    return out


def placement(labels):
    symbols = '.PNBRQKpnbrqk'
    rows = []
    for rank in range(8):
        row = ''; empty = 0
        for label in labels[rank * 8:(rank + 1) * 8]:
            if label == 0:
                empty += 1
            else:
                if empty:
                    row += str(empty); empty = 0
                row += symbols[label]
        if empty:
            row += str(empty)
        rows.append(row)
    return '/'.join(rows)


torch.set_num_threads(4)
torch.set_num_interop_threads(1)
torch.manual_seed(0)
transform = build_transform(644, train=False)
frozen = json.loads((HERE / 'fp16-protocol.json').read_text())
assert sha(FP16) == frozen['modelSha256']
assert sha(STUDY / 'data/predictions.json') == frozen['truthSha256']
assert sha(STUDY / 'tools/geometry.py') == frozen['geometrySha256']
for rel, digest in frozen['sourceFiles'].items():
    assert sha(UPSTREAM / rel) == digest
frames = {r['id']: r for r in json.loads((STUDY / 'data/frame-hashes.json').read_text())}
pins = json.loads((HERE / 'model-pins.json').read_text())
for pin in pins:
    assert sha(MODELS / pin['filename']) == pin['sha256']

# Check the same numeric preprocessing reference used in the prior experiment.
y, x = np.mgrid[0:800, 0:1000]
synthetic = np.stack([(x*7+y*3)%256, (x*11+y*13)%256, (x*17+y*19)%256], axis=-1).astype('uint8')
ref = transform(torch.from_numpy(synthetic).permute(2, 0, 1).float())
checks = json.loads((HERE / 'preprocessing-reference.json').read_text())['checks']
for check in checks:
    assert abs(ref[check['channel'], check['y'], check['x']].item()-check['expected']) < 1e-5
del ref, synthetic, x, y

prepared = []
tensor_hashes = []
for case in frozen['inputs']:
    path = INPUTS / (case['id'] + '.png')
    assert sha(path) == case['sourcePngSha256']
    rgba = np.array(Image.open(path).convert('RGBA'))
    rectified = warp(rgba, frames[case['id']]['quad'])
    assert hashlib.sha256(rectified.tobytes()).hexdigest() == case['commonFrameRgbaSha256']
    for route, array in [('full_photo', rgba[:,:,:3]), ('common_crop', rectified[:,:,:3])]:
        array = np.ascontiguousarray(array)
        tensor = transform(torch.from_numpy(array).permute(2,0,1).float()).unsqueeze(0).contiguous()
        prepared.append((case['id'], route, case['expected'], tensor))
        tensor_hashes.append(dict(id=case['id'], route=route,
                                  float32NchwSha256=hashlib.sha256(tensor.numpy().tobytes()).hexdigest()))
(OUTPUT / 'protocol.json').write_text(json.dumps({
    'previousProtocolSha256': sha(HERE / 'fp16-protocol.json'),
    'previousPredictionSha256': sha(HERE / 'fp16-predictions.json'),
    'sourceCommit': frozen['sourceCommit'], 'truthSha256': frozen['truthSha256'],
    'inputs': frozen['inputs'], 'tensorHashes': tensor_hashes,
    'preprocessing': 'Same upstream torchvision 0.23 antialiased bilinear resize to 644 and ImageNet normalization as prior FP16 experiment; identical cached tensors for all models.',
    'scoring': 'Every one of 64 squares must match; fixed full-photo and common-crop routes, no prediction-guided choice of route, rotation or crop.',
    'runtime': 'CPU only; 4 intra-op threads and 1 inter-op thread; ONNX graph optimizations enabled.',
    'v5Direction': 'Recorded separately using Lichess cos(100 degrees) threshold; does not rotate or alter scored FEN placement.'
}, indent=2)+'\n')

previous = {(r['id'], r['route']): r for r in json.loads((HERE / 'fp16-predictions.json').read_text())}
records = []
runtimes = []
for model_id in ['v4_fp16', 'v4_int8', 'v5_int8']:
    start = time.perf_counter()
    if model_id == 'v4_fp16':
        model = load_safetensors_model(FP16, device='cpu').float().eval()
        info = {'model': model_id, 'bytes': FP16.stat().st_size, 'sha256': sha(FP16)}
        with torch.inference_mode():
            model(torch.zeros(1, 3, 644, 644))
    else:
        pin = next(p for p in pins if p['version'] == model_id[:2])
        options = ort.SessionOptions()
        options.intra_op_num_threads = 4
        options.inter_op_num_threads = 1
        options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        model = ort.InferenceSession(str(MODELS / pin['filename']),
                                     sess_options=options, providers=['CPUExecutionProvider'])
        info = {'model': model_id, 'bytes': pin['bytes'], 'sha256': pin['sha256'],
                'providers': model.get_providers(),
                'inputs': [{'name': v.name, 'shape': v.shape, 'type': v.type} for v in model.get_inputs()],
                'outputs': [{'name': v.name, 'shape': v.shape, 'type': v.type} for v in model.get_outputs()]}
        model.run(None, {model.get_inputs()[0].name: np.zeros((1,3,644,644),dtype=np.float32)})
    info['loadAndWarmupSeconds'] = time.perf_counter()-start
    runtimes.append(info)
    print('LOADED', model_id, info, flush=True)
    for ident, route, expected, tensor in prepared:
        start = time.perf_counter()
        direction = None
        if model_id == 'v4_fp16':
            with torch.inference_mode():
                logits = model(tensor)[0].numpy()
        else:
            values = model.run(None, {model.get_inputs()[0].name: tensor.numpy()})
            outputs = dict(zip([v.name for v in model.get_outputs()], values))
            logits = outputs['logits'][0]
            if 'direction' in outputs:
                cos, sin = outputs['direction'][0].tolist()
                assert math.isfinite(cos) and math.isfinite(sin)
                direction = {'cos':cos, 'sin':sin,
                             'view':'black' if cos < np.float32(math.cos(math.radians(100))) else 'white'}
        elapsed = time.perf_counter()-start
        assert logits.shape == (64, 13) and np.isfinite(logits).all()
        labels = logits.argmax(axis=-1)
        fen = placement(labels)
        truth = expand(expected)
        got = expand(fen)
        stable = logits-logits.max(axis=-1,keepdims=True)
        probabilities = np.exp(stable)/np.exp(stable).sum(axis=-1,keepdims=True)
        errors = [dict(square='abcdefgh'[i%8]+str(8-i//8), expected=e, actual=a,
                       predictedProbability=float(probabilities[i,labels[i]]))
                  for i,(e,a) in enumerate(zip(truth,got)) if e != a]
        row = dict(model=model_id, id=ident, route=route, expected=expected,
                   placement=fen, correct=64-len(errors), errors=errors,
                   inferenceSeconds=elapsed, direction=direction)
        if model_id == 'v4_fp16':
            assert fen == previous[ident,route]['placement'], (ident,route,fen)
        records.append(row)
        (OUTPUT / 'predictions.json').write_text(json.dumps(records,indent=2)+'\n')
        print(model_id, ident, route, row['correct'], fen, round(elapsed,3), flush=True)
    del model
    gc.collect()

metrics = {}
for ident in ['v4_fp16', 'v4_int8', 'v5_int8']:
    metrics[ident] = {}
    for route in ['full_photo', 'common_crop']:
        selected = [r for r in records if r['model'] == ident and r['route'] == route]
        metrics[ident][route] = dict(photos=len(selected), exactBoards=sum(r['correct']==64 for r in selected),
                                     wrongSquares=sum(64-r['correct'] for r in selected),
                                     meanInferenceSeconds=sum(r['inferenceSeconds'] for r in selected)/len(selected))
runtime = dict(python=sys.version, platform=platform.platform(), machine=platform.machine(),
               torch=torch.__version__, torchvision=torchvision.__version__, timm=timm.__version__,
               onnxruntime=ort.__version__, numpy=np.__version__, opencv=cv2.__version__,
               threads=4, maxProcessRssBytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
               models=runtimes, fp16ControlMatchesPrevious24Placements=True)
(OUTPUT / 'metrics.json').write_text(json.dumps(metrics,indent=2)+'\n')
(OUTPUT / 'runtime.json').write_text(json.dumps(runtime,indent=2)+'\n')
print(json.dumps(metrics,indent=2),flush=True)
