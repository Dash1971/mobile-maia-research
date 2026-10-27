"""Draw the plain-language guide from recorded study results."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Circle

ROOT=Path(__file__).resolve().parent
D=json.loads((ROOT/'data/summary.json').read_text())
BG='#F6F4EE'; INK='#192F3E'; MUTED='#55636B'; BLUE='#4966AA'; TEAL='#138578'; AMBER='#B96328'; TRACK='#E7EAE7'; RED='#C65B4B'
plt.rcParams.update({'font.family':'DejaVu Sans','svg.fonttype':'none'})
def box(ax,x,y,w,h,fill,edge='none',radius=.02):
 ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle=f'round,pad=0,rounding_size={radius}',facecolor=fill,edgecolor=edge,linewidth=1.1))
def text(ax,x,y,s,size=16,color=INK,weight='normal',**kw):
 ax.text(x,y,s,fontsize=size,color=color,fontweight=weight,transform=ax.transAxes,**kw)
def save(fig,name):
 fig.savefig(ROOT/'figures'/f'{name}.png',dpi=160,facecolor=BG)
 fig.savefig(ROOT/'figures'/f'{name}.svg',facecolor=BG)
 plt.close(fig)
for elo in [1600,2600]:
 result=D['calibration'][f'{elo}-history-true']
 fig,ax=plt.subplots(figsize=(9,10.8));fig.subplots_adjust(0,0,1,1);ax.set(xlim=(0,1),ylim=(0,1));ax.axis('off');fig.patch.set_facecolor(BG)
 text(ax,.06,.945,f'Maia {elo}',30,weight='bold')
 text(ax,.06,.906,'What Maia expected. What actually happened.',17)
 text(ax,.06,.867,f"{result['n']} games • Points scored per 100 games",15,color=MUTED)
 for i,b in enumerate(result['bins']):
  y=.705-i*.133
  sparse=b['n']<30
  box(ax,.045,y,.91,.12,'#FFF6E9' if sparse else '#FFFFFF')
  text(ax,.065,y+.095,f"Forecasts in the {int(round(b['lower']*100))}–{int(round(b['upper']*100))}% range",13,weight='bold')
  text(ax,.93,y+.095,f"{b['n']} games"+(' · small group' if sparse else ''),11,color=AMBER if sparse else MUTED,ha='right')
  for label,value,color,by in [('Maia expected',b['meanPrediction'],BLUE,y+.063),('Players scored',b['meanActualScore'],TEAL,y+.025)]:
   text(ax,.065,by,label,13,color=MUTED,va='center')
   box(ax,.315,by-.01,.52,.02,TRACK,radius=.008)
   box(ax,.315,by-.01,.52*value,.02,color,radius=.008)
   text(ax,.92,by,str(round(value*100)),20,color=color,weight='bold',va='center',ha='right')
 if elo==1600:
  text(ax,.06,.125,'The broad picture lines up.',19,weight='bold')
  text(ax,.06,.091,'The five groups were within about 1–4 points of the forecast.',12,color=MUTED)
 else:
  text(ax,.06,.125,'One group stands out: 31 expected, 19 scored.',19,weight='bold')
  text(ax,.06,.091,'That group contains 78 games. The other four groups are much closer.',12,color=MUTED)
 text(ax,.06,.046,'White’s scores • Draw = ½ point • History on • No time forfeits',11,color=MUTED)
 text(ax,.06,.024,'Rounded averages, not exact forecasts. Uncertainty intervals are in the appendix.',10,color=MUTED)
 save(fig,f'visual-results-{elo}')

fig,ax=plt.subplots(figsize=(9,9));fig.subplots_adjust(0,0,1,1);ax.set(xlim=(0,1),ylim=(0,1));ax.axis('off');fig.patch.set_facecolor(BG)
text(ax,.06,.94,'Sometimes Maia disagrees with itself.',25,weight='bold')
text(ax,.06,.891,'We compared its score with an average of its predictions',15)
text(ax,.06,.858,'after every legal move, weighted by how likely each move was.',14)
text(ax,.06,.793,'Cases with a gap bigger than 10 percentage points',17,weight='bold')
for elo,x in [(1600,.06),(2600,.54)]:
 box(ax,x,.255,.4,.49,'#FFFFFF')
 text(ax,x+.025,.697,f'Maia {elo}',20,weight='bold')
 count=round(D['consistency'][str(elo)]['fractionAbove10']*100)
 text(ax,x+.025,.636,f'{count} out of 100',26,color=RED,weight='bold')
 for i in range(100):
  col=i%10;row=i//10
  ax.add_patch(Circle((x+.037+col*.036,.58-row*.030),.0105,facecolor=RED if i<count else '#DEE5E3',edgecolor='none'))
text(ax,.06,.213,'Each dot is one position. Red means a large disagreement.',12,color=MUTED)
text(ax,.06,.153,'Typical gap: about 4 points at both ratings.',18,weight='bold')
text(ax,.06,.104,'The same 100 positions were used at both ratings, with history on.',12,color=MUTED)
text(ax,.06,.073,'A disagreement does not tell us which estimate is closer to the truth.',11,color=MUTED)
text(ax,.06,.042,'This sample does not establish that one rating is more reliable.',11,color=MUTED)
save(fig,'visual-consistency')

# Concrete explanation of the unchanged consistency test, using the isolated Rd1 case.
case=json.loads((ROOT/'data/known-case-consistency.json').read_text())
s=next(x for x in case['summary'] if x['elo']==1600)
fig,ax=plt.subplots(figsize=(9,10.4));fig.subplots_adjust(0,0,1,1);ax.set(xlim=(0,1),ylim=(0,1));ax.axis('off');fig.patch.set_facecolor(BG)
text(ax,.06,.944,'One position. Two different answers.',25,weight='bold')
text(ax,.06,.902,'The Rd1 example, using Maia 1600. All scores are for White.',13,color=MUTED)
box(ax,.06,.727,.88,.126,'#FFFFFF')
text(ax,.085,.808,'1. Ask Maia about the position',18,weight='bold')
text(ax,.085,.760,'“How many points would White score?”',14,color=MUTED)
text(ax,.91,.760,f"{100*s['parentWhiteScore']:.1f}%",27,color=BLUE,weight='bold',ha='right')
text(ax,.06,.667,'2. Ask Maia about every possible next move',18,weight='bold')
box(ax,.06,.451,.42,.164,'#FFFFFF');box(ax,.52,.451,.42,.164,'#FFFFFF')
text(ax,.085,.573,'If White plays Rd1…',16,weight='bold')
text(ax,.085,.529,f"{100*s['rd1Probability']:.1f}% of predicted moves",12,color=MUTED)
text(ax,.085,.481,f"White’s score: {100*s['rd1WhiteScore']:.1f}%",18,color=TEAL,weight='bold')
text(ax,.545,.573,'The other 25 moves…',16,weight='bold')
text(ax,.545,.529,f"{100*(1-s['rd1Probability']):.1f}% of predicted moves",12,color=MUTED)
text(ax,.545,.481,f"Average score: {100*s['nonRd1ConditionalWhiteScore']:.1f}%",18,color=TEAL,weight='bold')
for x in [.27,.73]:
 ax.annotate('',xy=(.5,.356),xytext=(x,.438),arrowprops={'arrowstyle':'->','lw':1.6,'color':MUTED})
box(ax,.19,.247,.62,.104,'#E3EFEB')
text(ax,.5,.316,'Combine all 26 forecasts using their move chances',12,ha='center')
text(ax,.5,.268,f"White’s average score: {100*s['weightedChildWhiteScore']:.1f}%",23,color=TEAL,weight='bold',ha='center')
text(ax,.06,.180,f"That is a {abs(s['gapPercentagePoints']):.1f}-point mismatch.",22,color=RED,weight='bold')
text(ax,.06,.135,'Both answers describe the same starting position. They should',13)
text(ax,.06,.107,'roughly agree—but here, Maia’s own forecasts do not.',13)
text(ax,.06,.059,'This is a disagreement between predictions, not a count of bad moves or lost games.',10,color=MUTED)
text(ax,.06,.035,'This worked example is separate from the study’s 100-position consistency sample.',10,color=MUTED)
save(fig,'visual-worked-example')
