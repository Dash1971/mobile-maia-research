"""Render the guide from archived study summaries. No model runs or network.

Run from any directory after installing requirements.txt. This only writes
figures/ and figure-values.json beside this script; study evidence is untouched.
"""
import json
import os
from pathlib import Path
os.environ.setdefault('MPLCONFIGDIR', '/tmp/mobile-maia-guide-mpl')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RESULTS = json.loads((ROOT / 'studies/opening-variety-2026-10-18/results.json').read_text())
BG, INK, GREEN, MUTED, PALE, GRAY = '#f5f7f3', '#20372c', '#287f61', '#53665d', '#dceadf', '#c4cdc6'
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 12,
    'figure.facecolor': BG, 'axes.facecolor': BG, 'text.color': INK,
    'axes.labelcolor': INK, 'xtick.color': MUTED, 'ytick.color': INK,
    'svg.fonttype': 'none', 'axes.spines.top': False, 'axes.spines.right': False})
OUT = HERE / 'figures'
OUT.mkdir(exist_ok=True)
def save(fig, name):
    for ext in ('png', 'svg'):
        fig.savefig(OUT / f'{name}.{ext}', dpi=170, facecolor=BG)
    plt.close(fig)

def panel(ax, x, y, w, h, color):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.012,rounding_size=0.025',facecolor=color,edgecolor='none'))

fig = plt.figure(figsize=(11, 5.9)); ax=fig.add_axes((0,0,1,1)); ax.axis('off')
ax.text(.055,.91,'MOBILE MAIA  /  PROPOSED 2.5 DEFAULTS',fontsize=11,color=MUTED,weight='bold')
ax.text(.055,.80,'A wide opening.',fontsize=32,weight='bold')
ax.text(.055,.70,'A more selective middlegame.',fontsize=28,weight='bold')
panel(ax,.055,.22,.405,.35,PALE);panel(ax,.535,.22,.405,.35,INK)
ax.text(.08,.51,'MOVES 1–5 · BOTH SIDES',fontsize=11,weight='bold',color=GREEN)
ax.text(.08,.405,'1.0  /  1.0',fontsize=32,weight='bold')
ax.text(.08,.29,'Temperature / Top-P\nKeep the full mix of human moves.',fontsize=12,linespacing=1.6)
ax.annotate('',xy=(.522,.395),xytext=(.475,.395),arrowprops={'arrowstyle':'->','color':GREEN,'lw':2})
ax.text(.56,.51,'FROM MOVE 6',fontsize=11,weight='bold',color='#b5d8c4')
ax.text(.56,.405,'1.0  /  0.95',fontsize=32,weight='bold',color='white')
ax.text(.56,.29,'Temperature / Top-P\nTrim the least likely tail.',fontsize=12,color='white',linespacing=1.6)
ax.text(.055,.12,'Max variety in opening: ON',fontsize=14,weight='bold')
ax.text(.055,.065,'A Mobile Maia design choice, supported by our tests—not an official Maia-team recommendation.',fontsize=10,color=MUTED)
save(fig,'opening-switch')

fig,ax=plt.subplots(figsize=(11,5.9));fig.subplots_adjust(left=.16,right=.72,top=.74,bottom=.22)
ratings=('600','1600','2400'); records=[RESULTS['matches'][r]['C-A'] for r in ratings]
for y,(rating,d) in enumerate(zip(ratings,records)):
    lo,hi=[v*100 for v in d['score_95_ci']];v=d['score']*100
    ax.plot([lo,hi],[y,y],color=GREEN,lw=3,solid_capstyle='round')
    ax.scatter([v],[y],s=100,color=GREEN,zorder=3)
    ax.text(1.05,y,f'{v:.1f}%  ·  {d["games"]} games',transform=ax.get_yaxis_transform(),va='center',ha='left',fontsize=12)
ax.axvline(50,color=GRAY,lw=1.5,linestyle='--');ax.set_xlim(40,72);ax.set_ylim(2.7,-.7)
ax.set_yticks(range(3),labels=[f'Maia {r}' for r in ratings]);ax.set_xticks([40,50,60,70],labels=['40%','50%','60%','70%'])
ax.set_xlabel('Score against Temperature 1.0 / Top-P 1.0',labelpad=12)
for spine in ('left','right','top'):ax.spines[spine].set_visible(False)
ax.spines['bottom'].set_color(GRAY);ax.tick_params(axis='y',length=0,pad=15)
fig.text(.055,.91,'A stronger opponent in the main comparison',fontsize=23,weight='bold')
fig.text(.055,.83,'Opening variety ON + Top-P 0.95 · 79M model · history OFF',fontsize=12,color=MUTED)
fig.text(.055,.09,'50% = even match. Draws count as half a point. Lines show paired 95% intervals.',fontsize=11,color=MUTED)
fig.text(.055,.045,'The 600 result is inconclusive. These scores are not human Elo ratings.',fontsize=11,color=MUTED)
save(fig,'match-scores')

arms=RESULTS['openings']['by_rating']['1600']['arms']
counts=[arms[a]['24']['all_rollouts']['families_carried']['unique'] for a in ('A','B','C')]
assert counts==[70,59,70]
fig,ax=plt.subplots(figsize=(11,5.9));fig.subplots_adjust(left=.34,right=.93,top=.72,bottom=.27)
labels=['1.0 / 1.0 throughout','Top-P 0.95 throughout','Opening variety ON\nthen Top-P 0.95']
ax.barh(range(3),counts,color=[GRAY,GRAY,GREEN],height=.55)
for i,v in enumerate(counts):ax.text(v+1,i,str(v),va='center',fontsize=17,weight='bold')
ax.set_yticks(range(3),labels=labels);ax.set_xlim(0,80);ax.set_ylim(2.65,-.65);ax.set_xticks([0,20,40,60,80]);ax.set_xlabel('Distinct broad opening families',labelpad=10)
for spine in ('left','right','top'):ax.spines[spine].set_visible(False)
ax.spines['bottom'].set_color(GRAY);ax.tick_params(axis='y',length=0,pad=18)
fig.text(.055,.91,'Keep the measured broad opening mix',fontsize=23,weight='bold')
fig.text(.055,.83,'1,000 rollouts per setting · rating 1600 · through 12 full moves',fontsize=12,color=MUTED)
fig.text(.055,.12,'Opening labels are coarse and carried forward after leaving the table.',fontsize=11,color=MUTED)
fig.text(.055,.07,'Matching family counts does not prove equal variety in every sideline.',fontsize=11,color=MUTED)
save(fig,'opening-mix')

# Illustrative probabilities, explicitly not a measured chess position.
probs=[60,25,8,4,2,1];cut=4;kept=sum(probs[:cut]);assert kept>=95 and sum(probs[:cut-1])<95
fig,ax=plt.subplots(figsize=(11,6.3));fig.subplots_adjust(left=.12,right=.95,top=.70,bottom=.29)
ax.bar(range(6),probs,color=[GREEN]*4+[GRAY]*2,width=.65)
for i,v in enumerate(probs):ax.text(i,v+1,f'{v}%',ha='center',fontsize=14,weight='bold')
ax.set_ylim(0,70);ax.set_yticks([0,20,40,60],labels=['0%','20%','40%','60%']);ax.set_xticks(range(6),labels=['Move A','Move B','Move C','Move D','Move E','Move F'])
for spine in ('left','right','top'):ax.spines[spine].set_visible(False)
ax.spines['bottom'].set_color(GRAY);ax.tick_params(axis='both',length=0,pad=8)
fig.text(.055,.91,'95% is a target—not a per-move cutoff',fontsize=23,weight='bold')
fig.text(.055,.83,'Top-P 0.95 · illustrative example · Temperature already applied',fontsize=12,color=MUTED)
fig.text(.12,.16,'A + B + C = 93% → still below the target',fontsize=13)
fig.text(.12,.10,'Add D → 97% kept. E + F → 3% excluded.',fontsize=13,weight='bold',color=GREEN)
fig.text(.12,.045,'D stays despite being below 5%. The kept moves are then rescaled to total 100%.',fontsize=11,color=MUTED)
save(fig,'top-p-example')
values={'source':'studies/opening-variety-2026-10-18/results.json',
        'match_scores':{r:{k:RESULTS['matches'][r]['C-A'][k] for k in ('games','wins','draws','losses','score','score_95_ci')} for r in ratings},
        'opening_family_counts_1600':dict(zip(('A','B','C'),counts)),
        'illustration':{'probabilities_percent':probs,'kept_percent':kept,'excluded_percent':100-kept}}
(HERE/'figure-values.json').write_text(json.dumps(values,indent=2)+'\n')
print('Rendered four evidence-linked figures; original study evidence unchanged.')
