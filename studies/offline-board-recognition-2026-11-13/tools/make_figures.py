#!/usr/bin/env python3
"""Publication figures from frozen measurements, not generated example results."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from verify_results import expand

ROOT = Path(__file__).resolve().parents[1]
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11,
                     'svg.fonttype': 'none', 'svg.hashsalt': 'mobile-maia-board-recognition-2026-11-13', 'axes.spines.top': False,
                     'axes.spines.right': False, 'savefig.facecolor': 'white'})
cases = json.loads((ROOT / 'data/predictions.json').read_text())
metrics = json.loads((ROOT / 'data/metrics.json').read_text())['common_crop']
out = ROOT / 'figures'
out.mkdir(exist_ok=True)


def save(fig, name):
    fig.savefig(out / (name + '.svg'), bbox_inches='tight', metadata={'Date': None})
    fig.savefig(out / (name + '.png'), bbox_inches='tight', dpi=160)
    plt.close(fig)


fig, ax = plt.subplots(figsize=(10, 3.7))
labels = ['Current CrispChess', 'Chess Acuity', 'Fenshot', 'Fenify', 'Chess diagram to FEN']
values = [r['exact_boards'] for r in metrics]
bars = ax.barh(labels[::-1], values[::-1], color='#316b93')
ax.bar_label(bars, labels=[f'{n}/12' for n in values[::-1]], padding=6)
ax.set_xlim(0, 12)
ax.set_xticks(range(0, 13, 2))
ax.set_xlabel('Photos with all 64 squares correct — identical automatic crops')
ax.set_title('Better classifiers, still too many incomplete positions', loc='left', pad=15)
ax.spines['left'].set_visible(False)
ax.tick_params(axis='y', length=0)
ax.xaxis.grid(True, alpha=.15)
ax.set_axisbelow(True)
save(fig, 'exact-boards')

fig, ax = plt.subplots(figsize=(10, 4.1))
labels = ['Chess Acuity', 'Current CrispChess', 'Fenshot', 'Fenify', 'Chess diagram to FEN',
          'Existing Maia 79M (context)']
sizes = [105472, 835655, 1289483, 127147094, 243873463, 316034244]
colors = ['#316b93'] * 5 + ['#8a8a8a']
y = np.arange(len(labels))
ax.scatter(np.array(sizes) / 1e6, y, c=colors, s=65)
for i, size in enumerate(sizes):
    ax.annotate(f'{size / 1e6:.2f} MB', (size / 1e6, i), xytext=(8, 0),
                textcoords='offset points', va='center')
ax.set_xscale('log')
ax.set_xlim(.07, 1800)
ax.set_xticks([.1, 1, 10, 100, 1000], ['0.1', '1', '10', '100', '1,000'])
ax.set_yticks(y, labels)
ax.invert_yaxis()
ax.set_xlabel('Original model file size, decimal MB — logarithmic scale')
ax.set_title('Recognition must fit beside an already large Maia model', loc='left', pad=15)
ax.spines['left'].set_visible(False)
ax.tick_params(axis='y', length=0)
ax.xaxis.grid(True, alpha=.15)
save(fig, 'model-size')

fig, ax = plt.subplots(figsize=(10, 5))
keys = ['current', 'acuity', 'fenshot', 'fenify', 'tsoj']
data = [[64 - (c['current_on_common_crop'] if key == 'current' else c['models'][key])['correct']
         for key in keys] for c in cases]
im = ax.imshow(data, cmap='YlOrRd', vmin=0, vmax=64, aspect='auto')
for i, row in enumerate(data):
    for j, value in enumerate(row):
        ax.text(j, i, str(value), ha='center', va='center', color='white' if value > 35 else '#161616')
ax.set_xticks(range(5), ['Current', 'Acuity', 'Fenshot', 'Fenify', 'Diagram to FEN'])
ax.set_yticks(range(12), [c['label'] for c in cases])
ax.tick_params(length=0)
ax.set_title('Wrong squares per photo — zero is an exact board', loc='left', pad=15)
fig.colorbar(im, ax=ax, label='Wrong squares / 64', ticks=[0, 16, 32, 48, 64])
save(fig, 'per-photo-errors')

case = next(c for c in cases if c['id'] == 'cap19')
fenify_bad = next(c for c in cases if c['id'] == 'cap06')
pieces = dict(zip('KQRBNPkqrbnp', '♔♕♖♗♘♙♚♛♜♝♞♟'))
panels = [(case, case['current_on_common_crop'], 'Current: cap19'),
          (case, case['models']['fenify'], 'Fenify: cap19'),
          (fenify_bad, fenify_bad['models']['fenify'], 'Fenify: cap06 — still wrong')]
fig, axes = plt.subplots(1, 3, figsize=(12, 4.5))
for ax, (c, row, title) in zip(axes, panels):
    got, truth = expand(row['placement']), expand(c['expected'])
    for i, piece in enumerate(got):
        r, col = divmod(i, 8)
        ax.add_patch(plt.Rectangle((col, r), 1, 1, facecolor='#ececec' if (r + col) % 2 == 0 else '#bababa'))
        if piece != '.':
            ax.text(col + .5, r + .5, pieces[piece], fontsize=25, ha='center', va='center', color='#151515')
        if piece != truth[i]:
            ax.add_patch(plt.Rectangle((col + .04, r + .04), .92, .92, fill=False,
                                      edgecolor='#bd3b23', linewidth=2))
    ax.set_xlim(0, 8); ax.set_ylim(8, 0); ax.set_aspect('equal')
    ax.set_xticks(np.arange(8) + .5, list('abcdefgh'))
    ax.set_yticks(np.arange(8) + .5, list('87654321'))
    ax.tick_params(length=0)
    ax.set_title(title + f"\n{row['correct']}/64 correct", fontsize=11)
fig.suptitle('Recorded recognition outputs · outlined squares differ from the manual reference', y=1.01)
save(fig, 'actual-positions')
