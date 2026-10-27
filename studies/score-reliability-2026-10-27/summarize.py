"""Summarize recorded predictions; no model inference or adaptive selection."""
from pathlib import Path
import csv, json, math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parent; DATA=ROOT/'data'; FIG=ROOT/'figures'
B=5000

def rows(path):return [json.loads(x) for x in path.read_text().splitlines()]
def interval(x):return [float(v) for v in np.quantile(x,[.025,.975])]
def write_csv(path, data):
    with path.open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)

def main():
    sample=rows(DATA/'sample.jsonl');pred=rows(DATA/'predictions.jsonl');cons=rows(DATA/'consistency.jsonl');bygame={r['game']:r for r in sample}
    assert len(pred)==2*len(sample) and len(cons)==2*sum(r['consistency'] for r in sample)
    rng=np.random.default_rng(2026102702);summary={'bootstrapReplicates':B,'calibration':{},'historyComparison':{},'consistency':{}}
    bin_rows=[];metric_rows=[]
    for elo in [1600,2600]:
        ps={enabled:sorted([r for r in pred if r['elo']==elo and r['history']==enabled],key=lambda r:r['game']) for enabled in [True,False]}
        assert [r['game'] for r in ps[True]]==[r['game'] for r in ps[False]]
        y=np.array([r['actualWhiteScore'] for r in ps[True]]);n=len(y);idx=rng.integers(0,n,size=(B,n));base=(.5-y)**2
        values={};errors={}
        for enabled in [True,False]:
            p=np.array([r['whiteScore'] for r in ps[enabled]]);err=(p-y)**2;errors[enabled]=err;values[enabled]=p
            mse=float(err.mean());baseline=float(base.mean());paired=err-base;bias=p-y
            bins=[];assign=np.minimum((p*5).astype(int),4)
            for k in range(5):
                mask=assign==k;count=int(mask.sum())
                if not count:
                    bins.append({'bin':k,'lower':k*.2,'upper':(k+1)*.2,'n':0});continue
                xp,yp=p[mask],y[mask];bi=rng.integers(0,count,size=(B,count))
                rr={'bin':k,'lower':k*.2,'upper':(k+1)*.2,'n':count,'meanPrediction':float(xp.mean()),'meanActualScore':float(yp.mean()),'actualScoreCI':interval(yp[bi].mean(axis=1)),'predictionMinusActual':float((xp-yp).mean()),'gapCI':interval((xp-yp)[bi].mean(axis=1)),'sparse':count<30};bins.append(rr)
                bin_rows.append({'elo':elo,'history':enabled,'binLow':rr['lower'],'binHigh':rr['upper'],'n':count,'predicted':rr['meanPrediction'],'actual':rr['meanActualScore'],'actualLow':rr['actualScoreCI'][0],'actualHigh':rr['actualScoreCI'][1],'gap':rr['predictionMinusActual'],'gapLow':rr['gapCI'][0],'gapHigh':rr['gapCI'][1],'sparse':rr['sparse']})
            result={'n':n,'meanPrediction':float(p.mean()),'meanActualScore':float(y.mean()),'mse':mse,'mseCI':interval(err[idx].mean(axis=1)),'baselineMse':baseline,'mseMinusBaseline':float(paired.mean()),'mseMinusBaselineCI':interval(paired[idx].mean(axis=1)),'mseReductionPercent':100*(1-mse/baseline),'whiteBias':float(bias.mean()),'whiteBiasCI':interval(bias[idx].mean(axis=1)),'bins':bins}
            key=f'{elo}-history-{str(enabled).lower()}';summary['calibration'][key]=result
            metric_rows.append({'elo':elo,'history':enabled,**{k:result[k] for k in ['n','meanPrediction','meanActualScore','mse','baselineMse','mseReductionPercent','whiteBias']}})
        difference=errors[True]-errors[False]
        summary['historyComparison'][str(elo)]={'onMinusOffMse':float(difference.mean()),'pairedCI':interval(difference[idx].mean(axis=1))}
    crng=np.random.default_rng(2026102704)
    for elo in [1600,2600]:
        rs=sorted([r for r in cons if r['elo']==elo],key=lambda r:(r['sourceElo'],r['game']))
        gaps=np.array([r['gap']*100 for r in rs]);sources=np.array([r['sourceElo'] for r in rs]);ab=np.abs(gaps)
        def metrics(g):
            a=np.abs(g)
            return {'n':len(g),'meanSignedGapPP':float(g.mean()),'medianAbsoluteGapPP':float(np.median(a)),'p90AbsoluteGapPP':float(np.quantile(a,.9)),'fractionAbove5':float(np.mean(a>5)),'fractionAbove10':float(np.mean(a>10)),'maxAbsoluteGapPP':float(a.max())}
        inds=[]
        for source in [1600,2600]:
            indices=np.flatnonzero(sources==source);inds.append(crng.choice(indices,size=(B,len(indices)),replace=True))
        ix=np.concatenate(inds,axis=1);bs=gaps[ix];ba=np.abs(bs)
        cis={'meanSignedGapPP':interval(bs.mean(axis=1)),'medianAbsoluteGapPP':interval(np.median(ba,axis=1)),'p90AbsoluteGapPP':interval(np.quantile(ba,.9,axis=1)),'fractionAbove5':interval((ba>5).mean(axis=1)),'fractionAbove10':interval((ba>10).mean(axis=1))}
        summary['consistency'][str(elo)]={**metrics(gaps),'CI':cis,'bySourceCohort':{str(source):metrics(gaps[sources==source]) for source in [1600,2600]}}
    (DATA/'summary.json').write_text(json.dumps(summary,indent=2))
    write_csv(DATA/'outcome-metrics.csv',metric_rows);write_csv(DATA/'calibration-bins.csv',bin_rows)
    write_csv(DATA/'consistency-summary.csv',[{'elo':r['elo'],'sourceElo':r['sourceElo'],'game':r['game'],'parentWhiteScore':r['parent']['whiteScore'],'weightedWhiteScore':r['weightedWhiteScore'],'gapPercentagePoints':r['gap']*100,'legalMoves':len(r['children'])} for r in cons])
    FIG.mkdir(exist_ok=True)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'none'})
    for elo in [1600,2600]:
        s=summary['calibration'][f'{elo}-history-true'];fig,ax=plt.subplots(figsize=(7.8,6.4));fig.patch.set_facecolor('#fafaf7');ax.set_facecolor('#fafaf7')
        ax.plot([0,100],[0,100],color='#79828c',linestyle='--',linewidth=1.5,label='Perfect agreement')
        for b in s['bins']:
            if not b['n']:continue
            x,y=100*b['meanPrediction'],100*b['meanActualScore'];low,high=[v*100 for v in b['actualScoreCI']]
            ax.errorbar(x,y,yerr=[[max(0,y-low)],[max(0,high-y)]],fmt='o',markersize=8,capsize=4,color='#126782',markerfacecolor='white' if b['sparse'] else '#126782',zorder=3)
            ax.annotate(f"n={b['n']}"+(' *' if b['sparse'] else ''),(x,y),xytext=(8,9),textcoords='offset points',fontsize=10)
        ax.set(xlim=(-2,102),ylim=(-2,102),xticks=range(0,101,20),yticks=range(0,101,20),xlabel="Maia's average predicted score for White (%)",ylabel='Actual points scored by White (%)')
        ax.grid(alpha=.15);ax.set_aspect('equal',adjustable='box');ax.legend(loc='upper left',frameon=False,fontsize=10)
        fig.suptitle(f'Maia {elo}: do the scores match human results?',fontsize=15,fontweight='bold',y=.98)
        fig.text(.5,.92,f"History on · {s['n']} games · one position per game",ha='center',fontsize=11)
        fig.text(.5,.025,'2022 normal-ending blitz games near the target rating. Draws count as half a point.\nBars: descriptive 95% game-bootstrap intervals. * Fewer than 30 games in a band.',ha='center',fontsize=9,color='#4a5158')
        fig.subplots_adjust(top=.87,bottom=.16,left=.13,right=.96)
        fig.savefig(FIG/f'calibration-{elo}.png',dpi=170);fig.savefig(FIG/f'calibration-{elo}.svg');plt.close(fig)
    print(json.dumps({k:v for k,v in summary.items() if k!='calibration'},indent=2))
    for k,v in summary['calibration'].items():print(k,json.dumps({a:b for a,b in v.items() if a!='bins'}))

if __name__=='__main__':main()
