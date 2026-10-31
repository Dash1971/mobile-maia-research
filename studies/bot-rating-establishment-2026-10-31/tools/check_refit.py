#!/usr/bin/env python3
"""Reproduce the frozen training-only procedure without writing fitted weights.

No final ratings or game outcomes are read. No neural inference, service calls,
database writes, or test-guided selection takes place.
"""
import argparse
import csv
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = args.bundle.resolve()
    assert not args.output.exists(), 'Use a fresh output path'
    snapshot = root / 'data/frozen-training-perfs.json'
    source = root / 'tools/predictor_v2.py'
    snapshot_sha = hashlib.sha256(snapshot.read_bytes()).hexdigest()
    source_sha = hashlib.sha256(source.read_bytes()).hexdigest()
    assert snapshot_sha == 'eafdf58962686810a0938fde34272f11214e71f235158c422b4d6453b9cc42cc'
    assert source_sha == 'f35c16b5c504abc48ca0b9d7e15bf1f5720f7c271d3ca6a7716186c0152474b1'
    read = lambda name: json.loads((root / 'data' / name).read_text())
    roster = read('configurations.json')
    manifest = read('original-design-manifest.json')
    training = json.loads(snapshot.read_text())
    assert all(not training[b][s]['provisional'] for b in manifest['trainingIds'] for s in ('blitz', 'rapid'))
    spec = importlib.util.spec_from_file_location('frozen_v2', source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    fitted = module.fit(roster, manifest, training)
    with (root / 'data/frozen-predictions-v2.csv').open() as stream:
        reference = {(r['id'], r['speed']): float(r['prediction']) for r in csv.DictReader(stream)}
    assert set(reference) == {(b['id'], s) for b in roster for s in ('blitz', 'rapid')}
    maximum_difference = max(abs(fitted['speeds'][s]['predictions'][b]['rating'] - v)
                             for (b, s), v in reference.items())
    assert maximum_difference <= 1e-7, 'Inspect numerical environment; never replace the frozen reference'
    report = {'trainingSnapshotSha256': snapshot_sha, 'predictorSourceSha256': source_sha,
              'modelVersion': fitted['version'], 'numpyVersion': module.np.__version__,
              'heldoutOutcomesRead': False, 'fittedCoefficientsWritten': False,
              'neuralInferencePerformed': False, 'predictionTolerance': 1e-7,
              'maximumAbsolutePredictionDifference': maximum_difference,
              'selection': {s: {k: fitted['speeds'][s][k] for k in
                               ('complexity', 'penalty', 'configurationCvMae')}
                            for s in ('blitz', 'rapid')}}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'frozenProcedureReproduced': True, 'maximumDifference': maximum_difference}))


if __name__ == '__main__':
    main()
