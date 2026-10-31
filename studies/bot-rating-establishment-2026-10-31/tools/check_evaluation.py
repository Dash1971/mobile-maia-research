#!/usr/bin/env python3
"""Recompute the fixed evaluator from public predictions and earned results.

This reconstructs the prediction-only input expected by the exact evaluator.
It never fits a model, reads coefficients, contacts a service or writes ratings.
"""
import argparse
import csv
import gzip
import importlib.util
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True


def compare(actual, expected, location='evaluation'):
    assert type(actual) is type(expected) or isinstance(actual, (int, float)) and isinstance(expected, (int, float)), location
    if isinstance(expected, dict):
        assert actual.keys() == expected.keys(), location
        for key in expected:
            compare(actual[key], expected[key], location + '.' + key)
    elif isinstance(expected, list):
        assert len(actual) == len(expected), location
        for i, (a, b) in enumerate(zip(actual, expected)):
            compare(a, b, location + '.' + str(i))
    elif isinstance(expected, float):
        assert abs(actual - expected) <= 1e-7, location
    else:
        assert actual == expected, location


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists(), 'Use a fresh output path'
    root = args.bundle.resolve()
    read = lambda name: json.loads((root / 'data' / name).read_text())
    manifest = read('original-design-manifest.json')
    ratings = read('final-native-perfs.json')
    model = {'version': 'strength137-ridge-rbf-effective-cv-v2',
             'speeds': {s: {'predictions': {}} for s in ('blitz', 'rapid')}}
    with (root / 'data/frozen-predictions-v2.csv').open() as stream:
        for row in csv.DictReader(stream):
            model['speeds'][row['speed']]['predictions'][row['id']] = {'rating': float(row['prediction'])}
    with gzip.open(root / 'data/games.jsonl.gz', 'rt') as stream:
        games = [json.loads(line) for line in stream if line.strip()]
    spec = importlib.util.spec_from_file_location('fixed_evaluator', root / 'tools/predictor_v2.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.evaluate(model, manifest, ratings, games)
    compare(result, read('evaluation.json'))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({'exactEvaluatorReproduced': True, 'modelFitPerformed': False,
                                     'neuralInferencePerformed': False, 'evaluation': result}, indent=2) + '\n')
    print(json.dumps({'exactEvaluatorReproduced': True, 'modelFitPerformed': False}))


if __name__ == '__main__':
    main()
