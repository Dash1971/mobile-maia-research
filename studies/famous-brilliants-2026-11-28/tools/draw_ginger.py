"""Render a compact chart from verified Ginger results; no inference or tuning."""
import json
from pathlib import Path
from PIL import Image,ImageDraw,PngImagePlugin
from draw_figures import font

ROOT=Path(__file__).resolve().parents[1]

def draw():
    data=json.loads((ROOT/'ginger/summary.json').read_text());t=data['totals']
    im=Image.new('RGB',(1280,880),'#111a20');d=ImageDraw.Draw(im)
    ink='#edf2f4';muted='#bccbd4';blue='#81bdff';orange='#f1b356'
    d.text((60,38),'MOBILE MAIA RESEARCH',font=font(20),fill=muted)
    d.text((60,84),'Finding Ginger’s brillies',font=font(50),fill=ink)
    d.text((60,153),'27 games · 32 Chess.com gallery brillies · Fast analysis',font=font(26),fill=muted)
    y=220
    for label,key,color in [('En Croissant (adapted)','oldHits',blue),('Open Brilly Finder','newHits',orange)]:
        n=t[key];pct=n/32*100
        d.text((60,y),label,font=font(30),fill=ink)
        score=f'{n} / 32  ({pct:.1f}%)'
        box=d.textbbox((0,0),score,font=font(30));d.text((1220-(box[2]-box[0]),y),score,font=font(30),fill=color)
        d.rounded_rectangle((60,y+52,1220,y+106),radius=7,fill='#283945')
        if n:d.rounded_rectangle((60,y+52,60+1160*n/32,y+106),radius=7,fill=color)
        y+=160
    d.line((60,560,1220,560),fill='#40505c',width=2)
    d.text((60,588),'GALLERY LABELS',font=font(20),fill=muted)
    d.text((60,627),f'{t["gainedTargets"]} gained · {t["lostTargets"]} lost',font=font(36),fill=ink)
    d.text((680,588),'AWARDS OUTSIDE THE GALLERY',font=font(20),fill=muted)
    d.text((680,630),f'Adapted: {t["oldOutside"]}   Open Brilly: {t["newOutside"]}',font=font(30),fill=ink)
    d.text((60,735),'No matching games or played position/move pairs in the published candidate data.',font=font(23),fill=muted)
    d.text((60,780),'Gallery-selected sample: measures recovery of these labels, not overall precision.',font=font(23),fill=muted)
    d.text((60,826),'Same engine searches. Model and cutoff unchanged. No Android builds or Actions.',font=font(20),fill=muted)
    meta=PngImagePlugin.PngInfo();meta.add_text('Source','summary.json, derived from recorded app-native Fast analysis');meta.add_text('Plan',data['planCommit'])
    im.save(ROOT/'ginger/comparison.png',pnginfo=meta,optimize=True)
    print('Rendered verified counts to ginger/comparison.png')

if __name__=='__main__':draw()
