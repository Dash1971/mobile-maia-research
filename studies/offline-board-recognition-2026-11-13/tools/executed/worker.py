import sys,json
from pathlib import Path
import numpy as np
import onnxruntime as ort
session=ort.InferenceSession(sys.argv[1],providers=['CPUExecutionProvider'])
assert ort.__version__=='1.24.3'
print(json.dumps({'ready':True,'inputs':[(x.name,x.shape) for x in session.get_inputs()],'metadata':session.get_modelmeta().custom_metadata_map}),flush=True)
for line in sys.stdin:
 try:
  request=json.loads(line);x=np.fromfile(request['file'],dtype='<f4').reshape(64,1024)
  output=session.run(['probs'],{'tiles':x})[0]
  print(json.dumps({'id':request['id'],'probs':output.flatten().astype(float).tolist()}),flush=True)
 except Exception as e:print(json.dumps({'error':str(e)}),flush=True)
