from pathlib import Path
import json,hashlib,urllib.request,time
import torch
from torchvision import transforms
from PIL import Image
p=Path(__file__).resolve().parent;model=p/'fenify/model.pt';url='https://github.com/notnil/fenify/releases/download/v2023-07-10/models_2023-07-10-chessboard-2D-balanced-fen-cpu.pt';digest=hashlib.sha256();size=0
with urllib.request.urlopen(url) as r,model.open('wb') as f:
 while data:=r.read(1024*1024):f.write(data);digest.update(data);size+=len(data)
assert size==127147094
pin='e9a4fd252ea4be322c560a9b78a2b9da31f49735';files=[dict(path=name,url=f'https://raw.githubusercontent.com/notnil/fenify/{pin}/{name}',bytes=(p/'fenify'/name).stat().st_size,sha256=hashlib.sha256((p/'fenify'/name).read_bytes()).hexdigest()) for name in ['LICENSE','README.md','src/board_predictor.py']];files.append(dict(path='model.pt',url=url,bytes=size,sha256=digest.hexdigest()));(p.parent/'evidence/fenify-pin.json').write_text(json.dumps(dict(commit=pin,files=files),indent=2))
torch.set_num_threads(4);net=torch.jit.load(str(model),map_location='cpu');net.eval();pre=transforms.Compose([transforms.Grayscale(num_output_channels=3),transforms.Resize((300,300)),transforms.ToTensor(),transforms.Normalize(mean=[.485,.456,.406],std=[.229,.224,.225])]);classes='.PNBRQKpnbrqk';out=[]
def expand(fen):return [x for c in fen.replace('/','') for x in (['.']*int(c) if c.isdigit() else [c])]
def fen(sq):
 rows=[]
 for rank in range(7,-1,-1):
  row='';n=0
  for piece in sq[rank*8:(rank+1)*8]:
   if piece=='.':n+=1
   else:
    if n:row+=str(n);n=0
    row+=piece
  if n:row+=str(n)
  rows.append(row)
 return '/'.join(rows)
with torch.no_grad():
 for c in json.loads((p/'frames.json').read_text()):
  img=Image.open(p/(c['id']+'-frame.png')).convert('RGB');x=pre(img).unsqueeze(0);t=time.perf_counter();y=net(x).squeeze(0);elapsed=time.perf_counter()-t;placement=fen([classes[i] for i in y.argmax(dim=1).tolist()]);g=expand(placement);truth=expand(c['expected']);r=dict(id=c['id'],placement=placement,correct=sum(a==b for a,b in zip(g,truth)),elapsedSeconds=elapsed,errors=[dict(square='abcdefgh'[i%8]+str(8-i//8),actual=a,expected=b) for i,(a,b) in enumerate(zip(g,truth)) if a!=b]);out.append(r);print(c['id'],r['correct'],placement,round(elapsed,3),flush=True)
(p.parent/'evidence/fenify-framed.json').write_text(json.dumps(out,indent=2)+'\n')
