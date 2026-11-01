#!/usr/bin/env python3
"""Public explanation charts; saved measurements only, no neural inference.

The catalog distribution is the initial allocation, not a live rating feed. The sampling effects are
controlled earlier match results; the native ratings are the unchanged pool
snapshot. These distinct sources are never pooled into a causal effect.
"""
import hashlib
import json
from pathlib import Path

from audit_catalog_allocation import audit_catalog

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.patches import FancyBboxPatch

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'figures'
BG, INK, MUTED = '#F6F4EE', '#192F3E', '#55636B'
TEAL, BLUE, TRACK = '#138578', '#4966AA', '#E7EAE7'
plt.rcParams.update({'font.family': 'DejaVu Sans', 'svg.fonttype': 'none',
                     'text.color': INK, 'axes.labelcolor': INK,
                     'xtick.color': MUTED, 'ytick.color': MUTED,
                     'svg.hashsalt': 'mute-chess-rating-reader-v2'})


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
    svg = OUT / (name + '.svg')
    fig.savefig(svg, facecolor=BG, metadata={'Date': None})
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines()) + '\n')
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
    roster, final = read('configurations.json'), read('final-native-perfs.json')
    sources = read('reader-chart-sources.json')
    assert len(roster) == 250
    assert all(not perf[s]['provisional'] for perf in final.values() for s in ('blitz', 'rapid'))
    catalog = audit_catalog(ROOT)

    fig, ax = page(10, 8.6)
    text(ax, .06, .94, 'MOBILE MAIA RESEARCH  /  MUTE CHESS', 12, TEAL, 'bold')
    ax.plot([.06, .14], [.885, .885], color=TEAL, linewidth=4)
    text(ax, .06, .80, 'How we rate our', 36, weight='bold')
    text(ax, .06, .724, 'Maia opponents', 36, weight='bold')
    text(ax, .06, .651, 'A familiar rating. A varied opponent pool.', 19, MUTED)
    for x, number, label in ((.06, 'Lichess', 'the starting reference'),
                             (.36, '3,449', 'recorded rated games'),
                             (.66, 'Glicko-2', 'native rating updates')):
        box(ax, x, .468, .28, .12)
        text(ax, x+.02, .524, number, 26, TEAL, 'bold')
        text(ax, x+.02, .49, label, 11, MUTED)
    for i, (title, detail) in enumerate((
        ('Start from observed Lichess Maia ratings', 'Account for the sampling settings those opponents use.'),
        ('Measure what our settings actually do', 'Fixed policies play rated games; results determine their standings.'),
        ('Build a much larger, calibrated roster', 'Reuse policy evidence for new names, then keep learning from games.'))):
        y=.323-i*.105
        box(ax, .06, y, .88, .09, '#E7EFEB')
        text(ax, .08, y+.046, str(i+1), 24, TEAL, 'bold', va='center')
        text(ax, .14, y+.056, title, 15, weight='bold')
        text(ax, .14, y+.022, detail, 10.5, MUTED)
    text(ax, .06, .047, 'The goal: Mute Chess strength should correspond as closely as possible to Lichess.', 11, MUTED)
    save(fig, 'reader-cover')

    fig, canvas = page(10, 7.6)
    text(canvas, .06, .93, 'Fewer unlikely moves. Stronger play.', 27, weight='bold')
    text(canvas, .06, .866, 'Controlled matches at Maia input 1600 • Same 79M model • History off', 13, MUTED)
    ax=fig.add_axes([.30, .24, .61, .53]); style_chart(ax)
    comps = sources['sampling']['comparisons']
    for i, c in enumerate(comps):
        y=3-i; color=TEAL if i < 2 else BLUE
        ax.barh(y, c['gain'], color=color, alpha=.13, height=.55)
        ax.errorbar(c['gain'], y, xerr=[[c['gain']-c['low']], [c['high']-c['gain']]],
                    fmt='o', color=color, capsize=6, markersize=8, linewidth=2)
        ax.text(c['high']+8, y, f"+{c['gain']:.0f}", va='center', fontsize=15, color=color, fontweight='bold')
    ax.set(yticks=[3,2,1,0], yticklabels=[c['label'] for c in comps], xlim=(0,415),
           ylim=(-.6,3.6), xlabel='Match-Elo gain relative to full sampling (T 1 / P 1)')
    ax.tick_params(axis='y', labelsize=12)
    text(canvas, .06, .137, 'Small changes matter: Top-P 0.95 gained about 70 match-Elo.', 16, weight='bold')
    text(canvas, .06, .083, 'Dots show measured gains; whiskers show 95% intervals. Separate comparisons, 300–1,200 games each.', 10.5, MUTED)
    text(canvas, .06, .043, 'These are relative match results, not absolute human ratings. Slider effects are not additive.', 10.5, MUTED)
    save(fig, 'reader-sampling')

    fig, canvas=page(10,8.5)
    text(canvas,.06,.94,'Maia input is a guide—not a playing rating',25,weight='bold')
    text(canvas,.06,.883,'The reference pool shows the strength of many fixed combinations.',14,MUTED)
    strength=[]
    for b in roster:
        personality=b.get('personality', {})
        t=personality.get('temperature', b.get('temperature_after_opening',1))
        p=personality.get('topP', b.get('top_p_after_opening',1))
        strength.append(1-float(t)*float(p))
    for i,speed in enumerate(('blitz','rapid')):
        ax=fig.add_axes([.085+i*.465,.25,.405,.50]);style_chart(ax)
        sc=ax.scatter([b['conditioning_self'] for b in roster], [final[b['id']][speed]['rating'] for b in roster],
                      c=strength,cmap='viridis',norm=Normalize(0,1),s=25,alpha=.8,linewidths=0)
        ax.set(xlabel='Maia input',ylabel='Earned Mute Chess rating',xlim=(500,2700),ylim=(600,3200),xticks=[600,1200,1800,2600])
        ax.set_title(speed.title(),fontsize=17,color=INK,fontweight='bold',pad=12)
    cax=fig.add_axes([.31,.155,.38,.018]);cb=fig.colorbar(sc,cax=cax,orientation='horizontal',ticks=[0,1])
    cb.ax.set_xticklabels(['Full sampling','More concentrated']);cb.outline.set_visible(False)
    text(canvas,.06,.065,'Each dot is one opponent. Settings and remaining rating uncertainty both contribute to the spread.',10.5,MUTED)
    text(canvas,.06,.03,'Native Glicko-2 ratings, starting from the Lichess-informed reference. Color uses 1 − Temperature × Top-P.',10,MUTED)
    save(fig,'reader-settings')

    fig,canvas=page(10,8.5)
    text(canvas,.06,.94,'A busy middle. A small strong tail.',27,weight='bold')
    text(canvas,.06,.885,'Initial rating distribution for 10,000 opponents',14,MUTED)
    ax=fig.add_axes([.23,.27,.66,.52]);style_chart(ax)
    labels=['Below 1,000*','1,000–1,399','1,400–1,799','1,800–2,199','2,200–2,599','2,600+']
    for speed,offset,color in [('blitz',-.18,TEAL),('rapid',.18,BLUE)]:
        counts=catalog['speeds'][speed]['bandCounts']
        positions=[i+offset for i in range(6)]
        ax.barh(positions,counts,color=color,height=.30,label=speed.title())
        for y,count in zip(positions,counts):
            ax.text(count+55,y,f'{count:,}',va='center',fontsize=11,fontweight='bold',color=color)
    ax.set(yticks=range(6),yticklabels=labels,xlim=(0,4200),xlabel='Bot identities per speed at initialization')
    ax.invert_yaxis();ax.tick_params(axis='y',labelsize=12)
    ax.legend(loc='lower right',frameon=False,fontsize=12)
    text(canvas,.06,.17,'Both ratings come from the same measured playing policy.',15,weight='bold')
    text(canvas,.06,.118,'Weekly Lichess Blitz and Rapid snapshots, October 30, 2026; target distributions restricted to 800+.',10,MUTED)
    text(canvas,.06,.076,'250 earned reference ratings + 9,750 assigned starting ratings. New accounts begin with zero games.',10,MUTED)
    text(canvas,.06,.035,'* Mostly 800–999. One preserved Blitz reference is below 800. Ratings change as opponents play.',10,MUTED)
    save(fig,'reader-roster')

    inputs=('configurations.json','final-native-perfs.json','reader-chart-sources.json',
            'catalog-2026-11-01/catalog-manifest.json','catalog-2026-11-01/source-provenance.json',
            'catalog-2026-11-01/distribution-blitz.json','catalog-2026-11-01/distribution-rapid.json',
            'catalog-2026-11-01/distribution-source.json')
    metrics={'referenceBots':250,'finalEstablishedBotSpeedRatings':500,'generatedCatalogCount':catalog['total'],
      'generatedBandCounts':{s:catalog['speeds'][s]['bandCounts'] for s in ('blitz','rapid')},
      'catalogSourceCommit':catalog['sourceCommit'],'distributionScope':'initial catalog allocation; not a live rating feed',
      'newAssignedRd':catalog['assignedRd'],'newAssignedGameCount':catalog['assignedGameCount'],
      'samplingEffects':[c['gain'] for c in comps], 'neuralInferencePerformed':False,
      'inputsSha256':{n:hashlib.sha256((ROOT/'data'/n).read_bytes()).hexdigest() for n in inputs}}
    (OUT/'reader-figure-metrics.json').write_text(json.dumps(metrics,indent=2)+'\n')
    print(json.dumps(metrics))

if __name__=='__main__':
    main()
