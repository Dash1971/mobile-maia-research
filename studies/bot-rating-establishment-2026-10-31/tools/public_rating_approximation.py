#!/usr/bin/env python3
"""Audit a posthoc catalog-planning approximation using published data only.

Python standard library only. No inference, new games, network access, or edits
of source data. This is not the original frozen predictor or a fresh blind test.
"""
import argparse
import hashlib
import json
from pathlib import Path
from statistics import mean

STUDY = Path(__file__).resolve().parents[1]
FORMULA = "1575 + 0.73*(conditioning - 1600) + 320*(1 - temperature**3 * top_p**5)"


def sampling_bonus(bot):
    """Fixed design curve informed by earlier controlled 1600/history-off tests."""
    return 320 * (1 - bot['temperature_after_opening'] ** 3
                  * bot['top_p_after_opening'] ** 5)


def features(bot, history=False):
    row = [1., (bot['conditioning_self'] - 1600) / 1000]
    return row + [float(bot['personality']['history'])] if history else row


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def weighted_fit(x, y, weights):
    """Solve the small weighted least-squares normal equations with pivoting."""
    n = len(x[0])
    matrix = [[sum(w * row[i] * row[j] for row, w in zip(x, weights))
               for j in range(n)]
              + [sum(w * row[i] * target
                     for row, target, w in zip(x, y, weights))]
              for i in range(n)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(matrix[r][col]))
        matrix[col], matrix[pivot] = matrix[pivot], matrix[col]
        if abs(matrix[col][col]) < 1e-12:
            raise ValueError('Singular design matrix')
        scale = matrix[col][col]
        matrix[col] = [value / scale for value in matrix[col]]
        for row in range(n):
            if row != col:
                factor = matrix[row][col]
                matrix[row] = [a - factor * b
                               for a, b in zip(matrix[row], matrix[col])]
    return [matrix[i][-1] for i in range(n)]


def fold(bot):
    # Equivalent argmax aliases and full-sampling opening aliases stay together.
    # Omitting history also keeps on/off counterparts in the same fold.
    t, p = bot['temperature_after_opening'], bot['top_p_after_opening']
    if t == 0 or p == 0:
        t, p = 0., 0.
    opening = 0 if t == 1 and p == 1 else bot['opening']['full_moves']
    key = (bot['conditioning_self'], bot['conditioning_opponent'], t, p, opening)
    digest = hashlib.sha256(('public-method-descriptive-v1:'
                             + json.dumps(key, separators=(',', ':'))).encode())
    return int(digest.hexdigest()[:8], 16) % 5


def fit_and_cv(bots, ratings, speed, history=False):
    x = [features(bot, history) for bot in bots]
    bonus = [sampling_bonus(bot) for bot in bots]
    y = [ratings[bot['id']][speed]['rating'] for bot in bots]
    weights = [1 / (ratings[bot['id']][speed]['rd'] ** 2 + 50 ** 2)
               for bot in bots]
    target = [rating - adjustment for rating, adjustment in zip(y, bonus)]
    beta = weighted_fit(x, target, weights)
    errors = []
    folds = [fold(bot) for bot in bots]
    for k in range(5):
        tr = [i for i, value in enumerate(folds) if value != k]
        va = [i for i, value in enumerate(folds) if value == k]
        fitted = weighted_fit([x[i] for i in tr], [target[i] for i in tr],
                              [weights[i] for i in tr])
        errors.extend(abs(dot(x[i], fitted) + bonus[i] - y[i]) for i in va)
    return {
        'coefficients': beta,
        'trainingMae': mean(abs(dot(row, beta) + adjustment - rating)
                            for row, adjustment, rating in zip(x, bonus, y)),
        'trainingGroupedCvMae': mean(errors),
    }


def approximate(bot):
    return 1575 + .73 * (bot['conditioning_self'] - 1600) + sampling_bonus(bot)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=STUDY / 'data',
                        help='Directory containing the published input JSON files')
    parser.add_argument('--output', type=Path,
                        help='Optional new JSON output; defaults to stdout')
    args = parser.parse_args()
    names = ('configurations.json', 'original-design-manifest.json',
             'frozen-training-perfs.json', 'final-native-perfs.json')
    inputs = {name: (args.data / name).read_bytes() for name in names}
    roster, manifest, frozen, final = [json.loads(inputs[name]) for name in names]
    train_ids, test_ids = set(manifest['trainingIds']), set(manifest['heldoutIds'])
    if len(train_ids) != 200 or len(test_ids) != 50 or train_ids & test_ids:
        raise ValueError('Expected the original disjoint 200/50 identity split')
    training = [bot for bot in roster if bot['id'] in train_ids]
    known_test = [bot for bot in roster if bot['id'] in test_ids]
    if len(training) != 200 or len(known_test) != 50:
        raise ValueError('Incomplete published configuration coverage')
    result = {
        'status': 'Posthoc catalog-planning approximation; not a replacement '
                  'frozen predictor, causal slider law, or fresh blind validation',
        'formula': FORMULA,
        'samplingCurve': '320, 3 and 5 are fixed design constants informed by '
                         'earlier controlled experiments, not fitted here',
        'fit': 'Only the affine conditioning baseline is fitted to the original '
               '200 frozen training labels; weights=1/(RD^2+50^2)',
        'crossValidation': 'Five deterministic folds grouped by effective '
                           'conditioning/sampling/opening configuration; '
                           'history counterparts remain in the same fold',
        'knownTestCaveat': 'The 50 configurations were already known from the '
                           'earlier study; their comparison is descriptive',
        'inputSha256': {name: hashlib.sha256(data).hexdigest()
                        for name, data in inputs.items()},
        'speeds': {},
        'roundedFormulaEndpoints': {'conditioning600_full': 845,
                                    'conditioning2600_argmax': 2625},
    }
    for speed in ('blitz', 'rapid'):
        fit = fit_and_cv(training, frozen, speed)
        history_fit = fit_and_cv(training, frozen, speed, history=True)
        beta = fit['coefficients']
        fit['knownTestMae'] = mean(abs(dot(features(bot), beta) + sampling_bonus(bot)
                                       - final[bot['id']][speed]['rating'])
                                  for bot in known_test)
        fit['roundedFormulaKnownTestMae'] = mean(
            abs(approximate(bot) - final[bot['id']][speed]['rating'])
            for bot in known_test)
        fit['historySensitivity'] = {
            'additiveHistoryCoefficient': history_fit['coefficients'][-1],
            'withHistoryTrainingCvMae': history_fit['trainingGroupedCvMae'],
            'withoutHistoryTrainingCvMae': fit['trainingGroupedCvMae'],
            'interpretation': 'A descriptive predictive sensitivity, not an '
                              'equivalence test or causal history-effect estimate',
        }
        values = [final[bot['id']][speed]['rating'] for bot in roster]
        fit['observedNativeRatingRange'] = [min(values), max(values)]
        result['speeds'][speed] = fit
    payload = json.dumps(result, indent=2, allow_nan=False) + '\n'
    if args.output:
        # Avoid overwriting raw evidence or previously saved results by mistake.
        with args.output.open('x', encoding='utf-8') as output:
            output.write(payload)
    else:
        print(payload, end='')


if __name__ == '__main__':
    main()
