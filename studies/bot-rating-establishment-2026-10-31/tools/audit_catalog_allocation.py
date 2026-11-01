#!/usr/bin/env python3
"""Check the initial catalog allocation against unchanged published evidence.

Standard library only. Reads saved files; no fit, inference, games or network.
The complete identity list and application generator remain at the pinned source.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEEDS = ('blitz', 'rapid')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def json_digest(value):
    # Reproduce the generator's JSON.stringify checksum, preserving key order.
    return digest(json.dumps(value, separators=(',', ':'), ensure_ascii=False).encode())


def policy(bot):
    t, p = bot['temperature_after_opening'], bot['top_p_after_opening']
    assert bot['conditioning_self'] == bot['conditioning_opponent']
    assert 600 <= bot['conditioning_self'] <= 2600 and 0 <= t <= 1 and 0 <= p <= 1
    opening = bot['opening']['full_moves'] or 0
    if t == 1 and p == 1:
        opening = 0
    if t == 0 or p == 0:
        t, p = 0, 0
    return [bot['conditioning_self'], t, p, opening, bot['personality']['history']]


def audit_catalog(root=ROOT):
    directory = root / 'data' / 'catalog-2026-11-01'
    read = lambda name: json.loads((directory / name).read_bytes())
    provenance = read('source-provenance.json')
    manifest = read('catalog-manifest.json')
    for item in provenance['copiedArtifacts']:
        assert digest((directory / item['localFile']).read_bytes()) == item['sha256']
    for item in provenance['referenceInputs']:
        assert digest((directory / item['publishedFile']).read_bytes()) == item['publishedSha256']
    roster = json.loads((root / 'data/configurations.json').read_bytes())
    perfs = json.loads((root / 'data/final-native-perfs.json').read_bytes())
    assert len(roster) == len(perfs) == manifest['preserved'] == 250
    assert json_digest(roster) == manifest['referenceRosterSha256']
    assert json_digest(perfs) == manifest['referencePerfsSha256']
    assert manifest['total'] == 10000 and manifest['added'] == 9750
    assert manifest['assignedRd'] == 100 and manifest['assignedGameCount'] == 0
    by_id = {bot['id']: bot for bot in roster}
    assert set(by_id) == set(perfs)
    assert all(not perf[s]['provisional'] and 0 < perf[s]['rd'] < 110
               for perf in perfs.values() for s in SPEEDS)
    counts = manifest['templateCounts']
    assert len(counts) == manifest['usedPolicies']
    assert sum(t['count'] for t in counts) == 9750
    assert len({t['key'] for t in counts}) == len(counts)
    for template in counts:
        assert isinstance(template['count'], int) and template['count'] > 0
        ids = template['sourceIds']
        assert ids and len(set(ids)) == len(ids)
        assert all(policy(by_id[identity]) == json.loads(template['key']) for identity in ids)
        for speed in SPEEDS:
            weights = [1 / perfs[identity][speed]['rd'] ** 2 for identity in ids]
            expected = sum(perfs[identity][speed]['rating'] * weight
                           for identity, weight in zip(ids, weights)) / sum(weights)
            assert math.isclose(expected, template['ratings'][speed], abs_tol=1e-8)
            assert expected >= 800
    thresholds = manifest['distribution']['thresholds']
    assert thresholds == [1000, 1400, 1800, 2200, 2600]
    source = read('distribution-source.json')
    results = {}
    for speed in SPEEDS:
        frequencies = read(f'distribution-{speed}.json')['freq']
        metadata = source['pools'][speed]
        assert len(frequencies) == metadata['buckets']
        assert sum(frequencies) == metadata['players']
        histogram = [(metadata['bucketStart'] + i * metadata['bucketStep'], n)
                     for i, n in enumerate(frequencies)]
        denominator = sum(n for rating, n in histogram if rating >= 800)
        targets = [sum(n for rating, n in histogram if 800 <= rating < edge) / denominator
                   for edge in thresholds]
        target_record = manifest['distribution']['target'][speed]
        assert denominator == target_record['includedSourcePlayers']
        assert all(math.isclose(a, b, abs_tol=1e-12)
                   for a, b in zip(targets, target_record['cdf']))
        original = [perfs[bot['id']][speed]['rating'] for bot in roster]
        cdf_counts = [sum(value < edge for value in original)
                      + sum(t['count'] for t in counts if t['ratings'][speed] < edge)
                      for edge in thresholds]
        endpoints = [0, *cdf_counts, 10000]
        bands = [b - a for a, b in zip(endpoints, endpoints[1:])]
        achieved = manifest['distribution']['achieved'][speed]
        assert bands == achieved['bandCounts'] and sum(bands) == 10000
        error = max(abs(count / 10000 - target) * 100
                    for count, target in zip(cdf_counts, targets))
        assert math.isclose(error, achieved['maxCdfMismatchPercentagePoints'], abs_tol=1e-12)
        new_ratings = [t['ratings'][speed] for t in counts]
        assert math.isclose(min(new_ratings), manifest['ranges'][speed]['newMin'], abs_tol=1e-8)
        assert math.isclose(max(new_ratings), manifest['ranges'][speed]['newMax'], abs_tol=1e-8)
        results[speed] = {'bandCounts': bands, 'includedSourcePlayers': denominator,
                         'maxCdfMismatchPercentagePoints': error,
                         'allRosterRange': [min(original + new_ratings), max(original + new_ratings)],
                         'newAssignedRange': [min(new_ratings), max(new_ratings)]}
    return {'status': 'passed', 'total': 10000, 'preserved': 250, 'added': 9750,
            'usedMeasuredPolicies': len(counts), 'assignedRd': 100, 'assignedGameCount': 0,
            'activation': 'not evaluated; this offline audit does not inspect live accounts',
            'scope': 'Source hashes, reference-policy means and aggregate allocation; '
                     'full identity/personality/native provisioning checks belong to pinned application source',
            'sourceCommit': provenance['sourceCommit'], 'speeds': results,
            'inferenceOrGamesPerformed': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, default=ROOT)
    args = parser.parse_args()
    print(json.dumps(audit_catalog(args.bundle), indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
