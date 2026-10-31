#!/usr/bin/env python3
"""Rebuild static research figures from public evidence; no fits or network."""
import csv
import gzip
import hashlib
import json
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'figures'
SPEEDS = ('blitz', 'rapid')
COLORS = {'blitz': '#0072B2', 'rapid': '#D55E00'}


def read(name):
    return json.loads((ROOT / 'data' / name).read_text())


def lines(name):
    with gzip.open(ROOT / 'data' / name, 'rt') as stream:
        return [json.loads(line) for line in stream if line.strip()]


def utc(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp()


def save(fig, name):
    fig.savefig(OUT / (name + '.png'), dpi=180, facecolor='white')
    fig.savefig(OUT / (name + '.svg'), metadata={'Date': None}, facecolor='white')
    plt.close(fig)


def main():
    OUT.mkdir(exist_ok=True)
    plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False})
    progress = lines('native-progress.jsonl.gz')
    final = read('final-native-perfs.json')
    initial = read('initial-native-perfs.json')
    configs = read('configurations.json')
    manifest = read('original-design-manifest.json')
    evaluation = read('evaluation.json')
    start = utc(progress[0]['at'])
    end = utc(progress[-1]['at'])
    metrics = {'observedProgressWindowSeconds': end - start}

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.7), layout='constrained')
    fig.suptitle('250 bots: all Blitz and Rapid ratings established')
    for speed in SPEEDS:
        count = [sum(not v[speed]['provisional'] for v in row['ratings'].values()) for row in progress]
        axes[0].step([(utc(row['at']) - start) / 60 for row in progress], count,
                     where='post', label=speed.title(), color=COLORS[speed])
        axes[1].scatter([v[speed]['rd'] for v in initial.values()],
                        [final[b][speed]['rd'] for b in initial], s=16,
                        alpha=.65, label=speed.title(), color=COLORS[speed])
    axes[0].set(xlabel='Minutes after first native snapshot', ylabel='Nonprovisional accounts',
                ylim=(0, 260), title='Observed progress; no interpolated ratings')
    axes[0].axhline(250, color='#666666', linestyle=':', linewidth=1)
    axes[0].legend(frameon=False)
    axes[1].axhline(110, color='#666666', linestyle='--', linewidth=1, label='Provisional boundary')
    axes[1].set(xlabel='Initial native rating deviation', ylabel='Final native rating deviation',
                title='All 500 final deviations are below 110')
    axes[1].legend(frameon=False, fontsize=8)
    for ax in axes:
        ax.grid(alpha=.15)
    save(fig, 'rating-establishment')

    fig, axes = plt.subplots(1, 2, figsize=(11, 5.2), layout='constrained')
    fig.suptitle('A varied reference pool and an approximate settings-to-rating mapping')
    with (ROOT / 'data/frozen-predictions-v2.csv').open() as stream:
        predictions = {(r['id'], r['speed']): float(r['prediction']) for r in csv.DictReader(stream)}
    for speed, marker in (('blitz', 'o'), ('rapid', '^')):
        axes[0].scatter([b['conditioning_self'] for b in configs],
                        [final[b['id']][speed]['rating'] for b in configs],
                        marker=marker, s=15, alpha=.5, color=COLORS[speed], label=speed.title())
        ids = sorted(manifest['heldoutIds'])
        actual = [final[b][speed]['rating'] for b in ids]
        predicted = [predictions[b, speed] for b in ids]
        axes[1].scatter(actual, predicted, marker=marker, s=24, alpha=.8, color=COLORS[speed],
                        label=f"{speed.title()}: MAE {evaluation['speeds'][speed]['nativeRatingMae']:.0f}")
    axes[0].set(xlabel='Fixed Maia conditioning input', ylabel='Final earned native rating',
                title='All 250 policies; sampling and history also vary')
    axes[1].plot([600, 3200], [600, 3200], color='#666666', linestyle='--', linewidth=1)
    axes[1].set(xlabel='Final earned native test rating', ylabel='Prediction frozen before new test games',
                title='50 previously observed test configurations per speed')
    for ax in axes:
        ax.legend(frameon=False, fontsize=8)
        ax.grid(alpha=.15)
    save(fig, 'settings-and-ratings')

    resources = lines('resources-projection.jsonl.gz')
    roles = ('worker', 'app', 'adapter', 'ws', 'mongo', 'redis', 'gateway')
    valid = []
    for row in resources:
        if not start <= row['at'] / 1000 <= end:
            continue
        groups = row['cgroups']
        if all(groups[r].get('ActiveState') == 'active' for r in roles) and all(str(groups[r].get(k, '')).isdigit() for r in roles
               for k in ('MemoryCurrent', 'CPUUsageNSec')):
            valid.append(row)
    times = np.array([r['at'] / 1000 for r in valid])
    memory = np.array([[int(r['cgroups'][role]['MemoryCurrent']) for role in roles] for r in valid]) / 2**30
    # Pair only adjacent original observations, not across missing samples.
    pairs, durations, masked = [], [], 0
    by_time = {r['at']: r for r in valid}
    pair_times = []
    for a, b in zip(resources, resources[1:]):
        if a['at'] not in by_time or b['at'] not in by_time:
            masked += 1
            continue
        dt = (b['at'] - a['at']) / 1000
        delta = np.array([int(b['cgroups'][r]['CPUUsageNSec']) - int(a['cgroups'][r]['CPUUsageNSec']) for r in roles])
        if dt <= 0 or dt > 30 or (delta < 0).any():
            masked += 1
            continue
        pairs.append(delta / 1e9 / dt)
        durations.append(dt)
        pair_times.append((b['at'] / 1000 - start) / 60)
    cpu = np.array(pairs)
    means = np.average(cpu, weights=durations, axis=0)
    moves = lines('acknowledged-moves.jsonl.gz')
    q = len(moves) / (end - start)
    metrics['capacity'] = {'recordedRoles': list(roles), 'wholeHostMeasured': False,
        'samplesWithAllSevenValid': len(valid), 'maskedIntervals': masked,
        'validIntervalSeconds': sum(durations), 'maximumAcceptedIntervalSeconds': 30,
        'cpuCounterContinuityCondition': 'Adjacent active numeric nondecreasing counters; no PID or invocation IDs in resource projection. Continuity between samples is assumed, not independently proved by this file.',
        'workerMeanLogicalCores': float(means[0]),
        'sevenGroupMeanLogicalCores': float(means.sum()),
        'workerMaximumSampledCurrentGiB': float(memory[:, 0].max()),
        'sevenGroupMaximumSampledCurrentGiB': float(memory.sum(axis=1).max()),
        'uniqueAcknowledgedMoves': len(moves), 'observedMovesPerSecond': q,
        'illustrative20PercentHeadroomMovesPerSecond': q * .8,
        'illustrativeBotReplyRequestIntervalSecondsPerHumanGame': [2, 5, 10],
        'illustrativeActiveHumanGames': [q * .8 * seconds for seconds in (2, 5, 10)],
        'omissions': ['GIF', 'Cloudflared', 'isolation service', 'operating system and other host activity'],
        'interpretation': 'Measured game-serving throughput. Scenarios assume one bot reply request per active human game per stated interval, with no analysis traffic; they are not a VPS benchmark or admission setting.'}
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8), layout='constrained')
    fig.suptitle('Measured server load during the completed 826-game run')
    axes[0].plot(pair_times, cpu.sum(axis=1), linewidth=.7, color='#666666', label='Seven sampled service groups')
    axes[0].plot(pair_times, cpu[:, 0], linewidth=.8, color=COLORS['blitz'], label='Study worker group')
    axes[0].set(xlabel='Minutes after first native snapshot', ylabel='Logical CPU cores',
                ylim=(0, 5), title=f'Workers {means[0]:.2f} mean; sampled total {means.sum():.2f}')
    axes[1].plot((times - start) / 60, memory.sum(axis=1), color='#666666', linewidth=.8,
                 label='Seven sampled service groups')
    axes[1].plot((times - start) / 60, memory[:, 0], color=COLORS['blitz'], linewidth=.8,
                 label='Study worker group')
    axes[1].set(xlabel='Minutes after first native snapshot', ylabel='Sampled current memory (GiB)',
                ylim=(0, 3.3), title=f'Sampled combined maximum {memory.sum(axis=1).max():.2f} GiB')
    for ax in axes:
        ax.grid(alpha=.15)
        ax.legend(frameon=False, fontsize=8)
    save(fig, 'measured-capacity')

    inputs = ['native-progress.jsonl.gz', 'initial-native-perfs.json', 'final-native-perfs.json',
              'configurations.json', 'original-design-manifest.json', 'evaluation.json',
              'frozen-predictions-v2.csv', 'resources-projection.jsonl.gz', 'acknowledged-moves.jsonl.gz']
    metrics['inputsSha256'] = {name: hashlib.sha256((ROOT / 'data' / name).read_bytes()).hexdigest() for name in inputs}
    (OUT / 'figure-metrics.json').write_text(json.dumps(metrics, indent=2) + '\n')
    print(json.dumps({'figures': 3, 'metrics': metrics['capacity']}))


if __name__ == '__main__':
    main()
