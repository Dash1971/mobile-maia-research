"""Reproduce the pinned board-image accuracy experiment; no model is committed."""
import argparse
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import urllib.request

from PIL import Image, ImageOps

STUDY = Path(__file__).resolve().parents[1]
SCRIPTS = STUDY / 'scripts'
BOOKS = {'external_1001', 'external_b-and-w-pdf', 'external_chess-puzzle-book',
         'external_combinations1a', 'external_critical-moments', 'external_imagination'}


def fetch(url, target, expected=None):
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists() or (expected and hashlib.sha256(target.read_bytes()).hexdigest() != expected):
        with urllib.request.urlopen(url, timeout=60) as response:
            data = response.read()
        if expected and hashlib.sha256(data).hexdigest() != expected:
            raise ValueError(f'Checksum mismatch: {url}')
        target.write_bytes(data)
    return target


def prepare(case, work):
    c = case.copy()
    suffix = Path(c['path']).suffix
    image = fetch(c['url'], work / 'images' / (c['id'] + suffix), c['image_sha256'])
    raw = work / 'rgba' / (c['id'] + '.rgba')
    raw.parent.mkdir(exist_ok=True)
    with Image.open(image) as source:
        im = ImageOps.exif_transpose(source).convert('RGBA')
        im = Image.alpha_composite(Image.new('RGBA', im.size, 'white'), im)
        assert im.size == (c['width'], c['height'])
        raw.write_bytes(im.tobytes())
    c['rgba_path'] = str(raw)
    return c


def expand(fen):
    squares = []
    for row in fen.split('/'):
        cells = []
        for ch in row:
            cells.extend(['.'] * int(ch) if ch.isdigit() else [ch])
        assert len(cells) == 8
        squares.extend(cells)
    assert len(squares) == 64
    return squares


def score(cases, results):
    labels = {c['id']: c for c in cases}
    groups = {}
    for r in results:
        c = labels[r['id']]
        g = groups.setdefault(c['group'], dict(inputs=0, positives=0, found=0,
            exact_without_flip=0, exact_after_flip=0, correct_squares=0,
            total_squares=0, errors_confident90=0, negative_rejected=0))
        g['inputs'] += 1
        if c['fen'] is None:
            g['negative_rejected'] += not r.get('found', False)
            continue
        g['positives'] += 1
        g['total_squares'] += 64
        if not r.get('found'):
            continue
        g['found'] += 1
        expected = expand(c['fen'])
        a = sum(x == y for x, y in zip(expected, r['squares']))
        b = sum(x == y for x, y in zip(expected, r['squares'][::-1]))
        pred = r['squares'][::-1] if b > a else r['squares']
        conf = r['confidence'][::-1] if b > a else r['confidence']
        g['exact_without_flip'] += a == 64
        g['exact_after_flip'] += max(a, b) == 64
        g['correct_squares'] += max(a, b)
        g['errors_confident90'] += sum(x != y and z >= .9 for x, y, z in zip(expected, pred, conf))
    return groups


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--work-dir', type=Path, required=True, help='Disposable scratch directory outside source')
    ap.add_argument('--dart', default='dart')
    ap.add_argument('--ids', help='Optional comma-separated case IDs for a quick reproduction check')
    ap.add_argument('--parity', action='store_true', help='Also cross-check native ONNX Runtime 1.24.3')
    args = ap.parse_args()
    work = args.work_dir.expanduser().resolve()
    if work == STUDY or STUDY in work.parents:
        ap.error('Keep downloaded models, images and environments outside the study/source directory')
    work.mkdir(parents=True, exist_ok=True)
    cases = json.loads((STUDY / 'manifest.json').read_text())
    if args.ids:
        ids = set(args.ids.split(','))
        assert ids <= {c['id'] for c in cases}, 'Unknown case ID'
        cases = [c for c in cases if c['id'] in ids]
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        local = list(pool.map(lambda c: prepare(c, work), cases))
    manifest = work / 'manifest.local.json'
    manifest.write_text(json.dumps(local))
    pins = json.loads((STUDY / 'pins.json').read_text())
    model = fetch(pins['model']['url'], work / 'board_squares.onnx', pins['model']['sha256'])
    assert model.stat().st_size == pins['model']['bytes']
    runner = work / 'runner'
    (runner / 'lib').mkdir(parents=True, exist_ok=True)
    fetch(pins['recognizer']['url'], runner / 'lib/board_recognizer.dart', pins['recognizer']['sha256'])
    license_url = pins['recognizer']['url'].rsplit('/lib/', 1)[0] + '/LICENSE'
    fetch(license_url, runner / 'UPSTREAM_LICENSE')
    for name in ['pubspec.yaml', 'pubspec.lock', 'run_benchmark.dart', 'export_inputs.dart', 'decode_native.dart']:
        shutil.copyfile(SCRIPTS / name, runner / name)
    env = dict(os.environ)
    env.setdefault('PUB_CACHE', str(work / 'pub-cache'))

    def dart(*cmd, output=None):
        subprocess.run([args.dart, *map(str, cmd)], cwd=runner, env=env, check=True, stdout=output)

    dart('pub', 'get', '--enforce-lockfile')
    auto_path = work / 'results-auto.jsonl'
    dart('run', 'run_benchmark.dart', manifest, model, auto_path)
    results = read_jsonl(auto_path)
    summaries = {'auto': score(cases, results)}
    for name, subset in [
        ('book-crop', [dict(c, crop=[0, 0, c['width'], c['height']]) for c in local if c['group'] in BOOKS]),
        ('two-board-crop', [dict(c, crop=[17, 128, 340, 340]) for c in local
                            if c['id'] == 'fenshot_whole-screen-two-boards'])]:
        if not subset:
            continue
        m = work / f'manifest-{name}.local.json'
        m.write_text(json.dumps(subset))
        out = work / f'results-{name}.jsonl'
        dart('run', 'run_benchmark.dart', m, model, out, 'crop')
        summaries[name] = score(subset, read_jsonl(out))
    if args.parity:
        import numpy as np
        import onnxruntime as ort
        if ort.__version__ != '1.24.3':
            raise RuntimeError('Native parity evidence is pinned to ONNX Runtime 1.24.3')
        selected = {0, 1, 5, 7, 9, 17, 32, 96, 103, 118, 143, 175, 176, 181, 183, 189}
        subset = [c for c in local if c['index'] in selected]
        m = work / 'manifest-parity.local.json'
        m.write_text(json.dumps(subset))
        inputs = work / 'parity-inputs'
        dart('run', 'export_inputs.dart', m, inputs)
        session = ort.InferenceSession(str(model), providers=['CPUExecutionProvider'])
        ref = {r['id']: r for r in results}
        native = []
        for c in json.loads((inputs / 'inputs.json').read_text()):
            if not c['found']:
                continue
            x = np.fromfile(c['input'], '<f4').reshape(64, 1, 32, 32)
            logits = session.run(['logits'], {'input': x})[0].astype(np.float64)
            e = np.exp(logits - logits.max(axis=1, keepdims=True))
            probs = e / e.sum(axis=1, keepdims=True)
            r = ref[c['id']]
            squares = r['squares'][::-1] if r['flipped'] else r['squares']
            confidence = r['confidence'][::-1] if r['flipped'] else r['confidence']
            chosen = probs[np.arange(64), ['.PNBRQKpnbrqk'.index(ch) for ch in squares]]
            native.append(dict(id=c['id'], probs=probs.ravel().tolist(),
                max_selected_probability_difference=float(np.max(np.abs(chosen-confidence)))))
        n = work / 'native-probabilities.json'
        n.write_text(json.dumps(native))
        with (work / 'native-parity.json').open('w') as out:
            dart('run', 'decode_native.dart', n, auto_path, output=out)
    (work / 'summary.json').write_text(json.dumps(summaries, indent=2) + '\n')
    print(json.dumps(summaries, indent=2))
    print(f'Results retained in {work}; delete this task-owned scratch after collecting compact evidence.')


if __name__ == '__main__':
    main()
