#!/usr/bin/env python3
"""Reader-facing figures from recorded evidence; no inference or model fitting.

Uses the off-white, navy, teal and blue visual language of this repository's
sampling guide and score-reliability report. Original technical figures and
all measured data remain unchanged.
"""
import csv
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'figures'
BG, INK, MUTED = '#F6F4EE', '#192F3E', '#55636B'
TEAL, BLUE, TRACK = '#138578', '#4966AA', '#E7EAE7'
plt.rcParams.update({'font.family': 'DejaVu Sans', 'svg.fonttype': 'none',
                     'text.color': INK, 'axes.labelcolor': INK,
                     'xtick.color': MUTED, 'ytick.color': MUTED})


def read(name):
    return json.loads((ROOT / 'data' / name).read_text())


def box(ax, x, y, width, height, color='white'):
    ax.add_patch(FancyBboxPatch((x, y), width, height,
        boxstyle='round,pad=0,rounding_size=.018', facecolor=color, edgecolor='none'))


def text(ax, x, y, value, size=15, color=INK, weight='normal', **kwargs):
    ax.text(x, y, value, fontsize=size, color=color, fontweight=weight,
            transform=ax.transAxes, **kwargs)


def page(width, height):
    fig, ax = plt.subplots(figsize=(width, height))
    fig.subplots_adjust(0, 0, 1, 1)
    fig.patch.set_facecolor(BG)
    ax.set(xlim=(0, 1), ylim=(0, 1))
    ax.axis('off')
    return fig, ax


def save(fig, name):
    fig.savefig(OUT / (name + '.png'), dpi=170, facecolor=BG)
    fig.savefig(OUT / (name + '.svg'), facecolor=BG, metadata={'Date': None})
    plt.close(fig)


def style_chart(ax):
    ax.set_facecolor('white')
    ax.spines[['top', 'right']].set_visible(False)
    ax.spines[['bottom', 'left']].set_color('#CAD3CF')
    ax.tick_params(labelsize=10, length=3)
    ax.grid(alpha=.25, color='#CAD3CF')
    ax.set_axisbelow(True)


def main():
    OUT.mkdir(exist_ok=True)
    roster = read('configurations.json')
    final = read('final-native-perfs.json')
    manifest = read('original-design-manifest.json')
    evaluation = read('evaluation.json')
    with (ROOT / 'data/frozen-predictions-v2.csv').open() as stream:
        predictions = {(r['id'], r['speed']): float(r['prediction']) for r in csv.DictReader(stream)}
    assert len(roster) == 250 and len(manifest['trainingIds']) == 200 and len(manifest['heldoutIds']) == 50
    assert all(not perf[s]['provisional'] for perf in final.values() for s in ('blitz', 'rapid'))

    fig, ax = page(9, 10.8)
    text(ax, .06, .948, 'MOBILE MAIA RESEARCH  /  MUTE CHESS', 12, TEAL, 'bold')
    ax.plot([.06, .14], [.902, .902], color=TEAL, linewidth=4)
    text(ax, .06, .823, 'How we give Maia bots', 32, weight='bold')
    text(ax, .06, .766, 'a starting rating', 32, weight='bold')
    text(ax, .06, .705, 'Different settings. Different playing strengths.', 17, MUTED)
    stats = [('250', 'reference bots'), ('200 + 50', 'learn + check'), ('~116', 'points of average error')]
    for x, (number, label) in zip((.06, .36, .66), stats):
        box(ax, x, .528, .28, .128)
        text(ax, x + .02, .592, number, 28, TEAL, 'bold')
        text(ax, x + .02, .55, label, 11, MUTED)
    text(ax, .06, .472, 'THE METHOD', 12, TEAL, 'bold')
    steps = [
        ('1', 'Start from Lichess', 'Use observed Maia account ratings as the starting anchor.'),
        ('2', 'Measure a varied reference pool', 'Let fixed bot settings earn ratings through played games.'),
        ('3', 'Estimate ratings for new names', 'Use the reference data to choose an informed starting rating.'),
    ]
    for index, (number, title, detail) in enumerate(steps):
        y = .357 - index * .112
        box(ax, .06, y, .88, .092, '#E7EFEB')
        text(ax, .082, y + .044, number, 25, TEAL, 'bold', va='center')
        text(ax, .145, y + .059, title, 16, weight='bold')
        text(ax, .145, y + .025, detail, 11, MUTED)
    text(ax, .06, .066, 'Blitz and Rapid • Maia3-79M • Fixed history and sampling settings', 10, MUTED)
    text(ax, .06, .039, 'Average error describes the checked estimates, not a guarantee for every bot.', 10, MUTED)
    save(fig, 'reader-cover')

    fig, canvas = page(10, 7.8)
    text(canvas, .06, .926, 'Settings change the strength we measure', 25, weight='bold')
    text(canvas, .06, .871, 'Bots at the same Maia skill setting can earn different ratings.', 15, MUTED)
    for index, (speed, color) in enumerate((('blitz', BLUE), ('rapid', TEAL))):
        ax = fig.add_axes([.085 + index * .465, .245, .405, .50])
        style_chart(ax)
        ax.scatter([b['conditioning_self'] for b in roster],
                   [final[b['id']][speed]['rating'] for b in roster],
                   s=21, color=color, alpha=.6, linewidths=0)
        ax.set(xlabel='Maia skill input', ylabel='Rating earned in the bot pool',
               xlim=(500, 2700), ylim=(600, 3200), xticks=[600, 1200, 1800, 2600])
        ax.set_title(speed.title(), color=color, fontsize=17, fontweight='bold', pad=14)
    text(canvas, .06, .12, 'Each dot is one of the 250 reference bots.', 15, weight='bold')
    text(canvas, .06, .072, 'Temperature, Top-P and move-history input also vary. The dots show their combined results.', 11, MUTED)
    text(canvas, .06, .037, 'These are earned Mute Chess ratings, starting from a Lichess-informed anchor.', 11, MUTED)
    save(fig, 'reader-settings')

    fig, canvas = page(10, 8.8)
    text(canvas, .06, .936, 'How close were the starting estimates?', 27, weight='bold')
    text(canvas, .06, .886, '50 test settings • Estimates compared with ratings earned through games', 13, MUTED)
    for x, speed, color in ((.06, 'blitz', BLUE), (.52, 'rapid', TEAL)):
        box(canvas, x, .734, .42, .108)
        mae = evaluation['speeds'][speed]['nativeRatingMae']
        text(canvas, x + .025, .795, f'{speed.title()}: {mae:.0f} points', 23, color, 'bold')
        text(canvas, x + .025, .758, 'average absolute rating error', 11, MUTED)
    ax = fig.add_axes([.12, .245, .78, .405])
    style_chart(ax)
    for speed, color, marker in (('blitz', BLUE, 'o'), ('rapid', TEAL, '^')):
        ids = sorted(manifest['heldoutIds'])
        ax.scatter([final[b][speed]['rating'] for b in ids], [predictions[b, speed] for b in ids],
                   color=color, marker=marker, s=37, alpha=.8, label=speed.title(), linewidths=0)
    ax.plot([700, 3100], [700, 3100], color=MUTED, linestyle='--', linewidth=1)
    ax.set(xlabel='Rating earned through games', ylabel='Estimated starting rating',
           xlim=(700, 3100), ylim=(700, 3100))
    ax.legend(frameon=False, fontsize=11)
    text(canvas, .06, .155, 'Closer to the dashed line means a closer estimate.', 16, weight='bold')
    text(canvas, .06, .105, 'Individual errors can be larger than the average. Use estimates as starting ratings.', 11, MUTED)
    text(canvas, .06, .069, 'Test settings were seen in earlier work; this is a follow-up check, not a fresh blind test.', 10, MUTED)
    text(canvas, .06, .035, 'The comparison does not independently establish the human Lichess rating scale.', 10, MUTED)
    save(fig, 'reader-predictions')

    inputs = ('configurations.json', 'final-native-perfs.json', 'original-design-manifest.json',
              'evaluation.json', 'frozen-predictions-v2.csv')
    metrics = {'referenceBots': len(roster), 'trainingBots': 200, 'testBots': 50,
        'meanAbsoluteError': {s: evaluation['speeds'][s]['nativeRatingMae'] for s in ('blitz', 'rapid')},
        'finalEstablishedBotSpeedRatings': 500, 'fitOrInferencePerformed': False,
        'inputsSha256': {n: hashlib.sha256((ROOT / 'data' / n).read_bytes()).hexdigest() for n in inputs}}
    (OUT / 'reader-figure-metrics.json').write_text(json.dumps(metrics, indent=2) + '\n')
    print(json.dumps(metrics))


if __name__ == '__main__':
    main()
