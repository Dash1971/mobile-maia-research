import sys,json,pathlib,time,importlib.util,hashlib
import torch,numpy as np
from PIL import Image
from torchvision.transforms import v2
root=pathlib.Path(__file__).resolve().parent;p=root/'tsoj';sys.path.insert(0,str(p));torch.set_num_threads(4)
# Complete released checkpoint is loaded strictly. Disable only the constructor's redundant ImageNet weight download.
model_file=p/'src/fen_recognition/model.py';source=model_file.read_text();needle='weights=models.ConvNeXt_Tiny_Weights.IMAGENET1K_V1';assert source.count(needle)==2
source=source.replace(needle,'weights=None');module=type(sys)('research_tsoj_model');exec(compile(source,str(model_file),'exec'),module.__dict__)
from src import common
model=module.BoardRec(game='chess');ckpt=next(p.glob('best_model_position_*.pth'));state=torch.load(ckpt,map_location='cpu',weights_only=True);print('checkpoint',len(state),flush=True);print(model.load_state_dict(state,strict=True),flush=True);model.eval()
resize=v2.Resize((256,256),interpolation=v2.InterpolationMode.BICUBIC);normalise=common.MinMaxMeanNormalization();cases=json.loads((root/'frames.json').read_text());out=[]
def expand(fen):return [x for c in fen.replace('/','') for x in (['.']*int(c) if c.isdigit() else [c])]
with torch.no_grad():
 for c in cases:
  img=Image.open(root/(c['id']+'-frame.png')).convert('RGB');x=normalise(resize(common.to_rgb_tensor(img)));t=time.perf_counter();y=model(x.unsqueeze(0)).squeeze(0).clamp(0,1);elapsed=time.perf_counter()-t;placement=common.tensor_to_position(y,'chess').piece_placement;truth=expand(c['expected']);got=expand(placement);r=dict(id=c['id'],placement=placement,correct=sum(a==b for a,b in zip(truth,got)),elapsedSeconds=elapsed,errors=[dict(square='abcdefgh'[i%8]+str(8-i//8),expected=a,actual=b) for i,(a,b) in enumerate(zip(truth,got)) if a!=b]);out.append(r);print(c['id'],r['correct'],placement,round(elapsed,3),flush=True)
(root.parent/'evidence/tsoj-framed.json').write_text(json.dumps(out,indent=2)+'\n')
