from pathlib import Path
import csv
import hashlib
import json
import os

STUDY = Path(__file__).resolve().parents[1]
HERE = STUDY / 'data/chessq'
FIGURES = STUDY / 'figures'
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

rows = json.loads((HERE / 'predictions.json').read_text())
metrics = json.loads((HERE / 'metrics.json').read_text())
runtime = json.loads((HERE / 'runtime.json').read_text())
protocol = json.loads((HERE / 'protocol.json').read_text())
models = ['v4_fp16', 'v4_int8', 'v5_int8']
labels = ['V4 FP16 · 63.1 MB', 'V4 INT8 · 41.4 MB', 'V5 INT8 · 35.9 MB']
sizes = [63147914, 41370398, 35905331]
ids = [v['id'] for v in protocol['inputs']]


def expand(fen):
    out = [v for c in fen.split()[0].replace('/', '')
           for v in (['.']*int(c) if c.isdigit() else [c])]
    assert len(out) == 64
    return out


assert len(rows) == 72
assert len({(r['model'],r['id'],r['route']) for r in rows}) == 72
lookup = {(r['model'],r['id'],r['route']): r for r in rows}
for model in models:
    for route in ['full_photo','common_crop']:
        selected = [r for r in rows if r['model']==model and r['route']==route]
        errors = []
        for row in selected:
            n = sum(a!=b for a,b in zip(expand(row['placement']),expand(row['expected'])))
            assert n == len(row['errors']) and row['correct'] == 64-n
            errors.append(n)
        assert sum(errors)==metrics[model][route]['wrongSquares']
        assert sum(n==0 for n in errors)==metrics[model][route]['exactBoards']

plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,
                     'axes.spines.right':False,'savefig.facecolor':'white','svg.fonttype':'none'})
fig,axes = plt.subplots(1,2,figsize=(10.5,3.8))
colors = ['#77838e','#1d7965','#9ba3aa']
for ax,route,title in zip(axes,['full_photo','common_crop'],['Full photos','Identical board crops']):
    vals = [metrics[m][route]['exactBoards'] for m in models]
    bars = ax.barh(labels[::-1],vals[::-1],color=colors[::-1])
    ax.bar_label(bars,labels=[f'{v}/12' for v in vals[::-1]],padding=5)
    ax.set_xlim(0,13);ax.set_xticks([0,3,6,9,12]);ax.spines['left'].set_visible(False)
    ax.tick_params(axis='y',length=0);ax.set_title(title,loc='left',pad=14)
    ax.set_xlabel('Photos with all 64 squares correct')
fig.suptitle('ChessQ Lite · smaller ONNX models versus the 63 MB original',fontsize=15,x=.02,ha='left',y=1.04)
fig.text(.02,-.035,'12 frozen photos · 10 unique positions · identical input tensors · CPU only',fontsize=10,color='#4b555d')
fig.tight_layout(w_pad=2.5)
fig.savefig(FIGURES/'chessq-accuracy-comparison.png',dpi=170,bbox_inches='tight');plt.close(fig)

fig,ax=plt.subplots(figsize=(9.8,5.6))
columns=[(m,route) for route in ['full_photo','common_crop'] for m in models]
grid=[[64-lookup[m,ident,route]['correct'] for m,route in columns] for ident in ids]
image=ax.imshow(grid,cmap='YlOrRd',vmin=0,vmax=max(5,max(max(r) for r in grid)),aspect='auto')
for i,row in enumerate(grid):
    for j,n in enumerate(row):ax.text(j,i,str(n),ha='center',va='center',color='#17212b' if n<4 else 'white')
ax.set_xticks(range(6),['V4 FP16\nFull','V4 INT8\nFull','V5 INT8\nFull','V4 FP16\nCrop','V4 INT8\nCrop','V5 INT8\nCrop'])
ax.set_yticks(range(12),['Original book' if i=='book' else 'Monitor photo' if i=='screen' else i for i in ids])
ax.tick_params(length=0);ax.set_title('Wrong squares per photo · zero is an exact board',loc='left',pad=16)
ax.axvline(2.5,color='#777777',lw=1)
fig.colorbar(image,ax=ax,label='Wrong squares / 64')
fig.tight_layout();fig.savefig(FIGURES/'chessq-per-photo-errors.png',dpi=170,bbox_inches='tight');plt.close(fig)

# These cases were failures in the previous probe, chosen before this run.
pieces=dict(zip('KQRBNPkqrbnp','♔♕♖♗♘♙♚♛♜♝♞♟'))
fig,axes=plt.subplots(2,4,figsize=(12.8,7))
for row,ident in enumerate(['book','cap24']):
    expected=lookup['v4_fp16',ident,'full_photo']['expected']
    panels=[('Reference',expected)]+[(label.split(' · ')[0],lookup[m,ident,'full_photo']['placement']) for m,label in zip(models,labels)]
    for ax,(title,fen) in zip(axes[row],panels):
        got,truth=expand(fen),expand(expected)
        for i,piece in enumerate(got):
            r,c=divmod(i,8)
            ax.add_patch(plt.Rectangle((c,r),1,1,facecolor='#eee9dc' if (r+c)%2==0 else '#b0baa8'))
            if piece!='.':ax.text(c+.5,r+.48,pieces[piece],fontsize=22,ha='center',va='center',color='#111820')
            if piece!=truth[i]:ax.add_patch(plt.Rectangle((c+.035,r+.035),.93,.93,fill=False,edgecolor='#c42d35',linewidth=2.5))
        wrong=sum(a!=b for a,b in zip(got,truth))
        ax.set_xlim(0,8);ax.set_ylim(8,0);ax.set_aspect('equal')
        ax.set_xticks(np.arange(8)+.5,list('abcdefgh'));ax.set_yticks(np.arange(8)+.5,list('87654321'))
        ax.tick_params(length=0,labelsize=9);ax.set_title(f"{title}\n{wrong} wrong {'square' if wrong == 1 else 'squares'}",fontsize=11,pad=8)
    axes[row,0].set_ylabel('Original book' if ident=='book' else 'cap24',fontsize=11)
fig.suptitle('Full-photo outputs · red outlines mark errors',fontsize=16,y=1.01)
fig.tight_layout(w_pad=1.5,h_pad=2)
fig.savefig(FIGURES/'chessq-actual-recognition.png',dpi=170,bbox_inches='tight');plt.close(fig)
