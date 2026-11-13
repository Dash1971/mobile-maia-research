#!/usr/bin/env python3
"""Recompute every published score from recorded FEN placements; no ML/downloads."""
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODELS = ['current', 'acuity', 'fenshot', 'fenify', 'tsoj']
LABELS = ['Current CrispChess', 'Chess Acuity', 'Fenshot', 'Fenify', 'Chess diagram to FEN']
SIZES = [835655, 105472, 1289483, 127147094, 243873463]


def expand(placement):
    ranks = placement.split('/')
    assert len(ranks) == 8
    result = []
    for rank in ranks:
        squares = [x for c in rank for x in (['.'] * int(c) if c in '12345678' else [c])]
        assert len(squares) == 8 and all(c in '.PNBRQKpnbrqk' for c in squares)
        result.extend(squares)
    return result


def score(row, expected):
    got, truth = expand(row['placement']), expand(expected)
    errors = [{'square': 'abcdefgh'[i % 8] + str(8 - i // 8), 'actual': a, 'expected': b}
              for i, (a, b) in enumerate(zip(got, truth)) if a != b]
    assert row['correct'] == 64 - len(errors)
    assert [{k: e[k] for k in ['square', 'actual', 'expected']} for e in row['errors']] == errors
    return len(errors)


def main():
    cases = json.loads((ROOT / 'data/predictions.json').read_text())
    assert len(cases) == 12 and len({c['expected'] for c in cases}) == 10
    summary = []
    per_photo = []
    for model, label, size in zip(MODELS, LABELS, SIZES):
        errors = []
        for c in cases:
            row = c['current_on_common_crop'] if model == 'current' else c['models'][model]
            wrong = score(row, c['expected'])
            errors.append(wrong)
            per_photo.append({'case': c['id'], 'model': model, 'correct_squares': 64 - wrong,
                              'wrong_squares': wrong, 'placement': row['placement']})
        summary.append({'id': model, 'label': label, 'model_bytes': size,
                        'exact_boards': errors.count(0), 'photos': 12,
                        'wrong_squares': sum(errors), 'squares': 768})
    assert [(r['exact_boards'], r['wrong_squares']) for r in summary] == [
        (1, 79), (1, 344), (5, 52), (6, 19), (6, 46)]
    full = {}
    for key in ['current_full_photo', 'frozen_prototype_full_photo']:
        rows = [(c, c[key]) for c in cases]
        for c, r in rows:
            if r is not None:
                score(r, c['expected'])
        full[key] = {'exact': sum(r is not None and r['correct'] == 64 for _, r in rows),
                     'no_result': sum(r is None for _, r in rows)}
    fenshot = json.loads((ROOT / 'data/fenshot-end-to-end.json').read_text())
    for r, c in zip(fenshot, cases):
        assert r['id'] == c['id']
        if r['scan'] is not None:
            score({**r, 'placement': r['scan']['placement']}, c['expected'])
    full['fenshot_full_photo'] = {'exact': sum(r.get('correct') == 64 for r in fenshot),
                                 'no_result': sum(r['scan'] is None for r in fenshot)}
    report = {'common_crop': summary, 'full_photo': full, 'unique_positions': 10,
              'input_photos_public': False, 'android_performance_measured': False}
    (ROOT / 'data/metrics.json').write_text(json.dumps(report, indent=2) + '\n')
    with (ROOT / 'data/per-photo.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(per_photo[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(per_photo)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
