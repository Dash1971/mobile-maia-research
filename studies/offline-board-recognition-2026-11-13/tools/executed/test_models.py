from pathlib import Path
import json,subprocess
import numpy as np,onnxruntime as ort
from PIL import Image
from ai_edge_litert.interpreter import Interpreter
base=Path(__file__).resolve().parent;ev=base.parent/'evidence'
frames=json.loads((base/'frames.json').read_text());classes='.PNBRQKpnbrqk'
def expand(fen):return [x for row in fen.split('/') for c in row for x in (['.']*int(c) if c.isdigit() else [c])]
def placement(squares):
 rows=[]
 for r in range(8):
  out='';n=0
  for p in squares[r*8:r*8+8]:
   if p=='.':n+=1
   else:
    if n:out+=str(n);n=0
    out+=p
  if n:out+=str(n)
  rows.append(out)
 return '/'.join(rows)
def score(c,squares):
 truth=expand(c['expected']);return dict(id=c['id'],placement=placement(squares),correct=sum(a==b for a,b in zip(squares,truth)),errors=[dict(square=chr(97+i%8)+str(8-i//8),actual=p,expected=truth[i]) for i,p in enumerate(squares) if p!=truth[i]])
interp=Interpreter(model_path=str(base/'acuity/tiles.tflite'));interp.allocate_tensors();inp=interp.get_input_details()[0];out=interp.get_output_details()[0]
acuity=[]
for c in frames:
 board=Image.open(base/(c['id']+'-frame.png')).convert('RGB');tiles=np.stack([np.asarray(board.crop((col*64,r*64,(col+1)*64,(r+1)*64)).resize((32,32),Image.Resampling.LANCZOS),dtype=np.float32) for r in range(8) for col in range(8)])
 interp.set_tensor(inp['index'],tiles);interp.invoke();logits=interp.get_tensor(out['index']);squares=[classes[i] for i in logits.argmax(axis=1)];result=score(c,squares);acuity.append(result);print('Acuity',c['id'],result['correct'],result['placement'],flush=True)
(ev/'acuity-framed.json').write_text(json.dumps(acuity,indent=2)+'\n')
# Existing recognizer on the identical automatically rectified board frames.
cases=[dict(**c,crop=[0,0,512,512],tensor=str(base/(c['id']+'.f32')),logits=str(base/(c['id']+'.logits.json'))) for c in frames]
manifest=base/'crisp-manifest.json';manifest.write_text(json.dumps(cases));dart='dart'
subprocess.run([dart,str(base/'recognize.dart'),'export',str(manifest),str(base/'crisp-export.json')],check=True)
records=json.loads((base/'crisp-export.json').read_text());session=ort.InferenceSession('MODEL_DIRECTORY/board_squares.onnx',providers=['CPUExecutionProvider'])
for c in records:
 x=np.fromfile(c['tensor'],dtype='<f4').reshape(64,1,32,32);logits=session.run(['logits'],{'input':x})[0];Path(c['logits']).write_text(json.dumps(logits.flatten().astype(float).tolist()))
(base/'crisp-decode.json').write_text(json.dumps(records));subprocess.run([dart,str(base/'recognize.dart'),'decode',str(base/'crisp-decode.json'),str(base/'crisp-decoded.json')],check=True)
crisp=[]
for c in json.loads((base/'crisp-decoded.json').read_text()):
 result=score(c,c['squares']);crisp.append(result);print('Crisp',c['id'],result['correct'],result['placement'],flush=True)
(ev/'crisp-framed.json').write_text(json.dumps(crisp,indent=2)+'\n')
