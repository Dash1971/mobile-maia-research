import cv2
import numpy as np
from geometry import candidates, warp

def automatic(a):
 cs=candidates(a)
 if not cs or cs[0]['score'][0]<12:return None
 c=cs[0];rectified=warp(a,c['quad'])
 # A monochrome page and a coloured on-screen board need different contrast
 # handling. The decision uses only input pixels, never a position label.
 chroma=float(np.median(np.ptp(rectified[:,:,:3].astype(float),axis=2)))
 if chroma<12:
  gray=cv2.cvtColor(rectified,cv2.COLOR_RGBA2GRAY)
  threshold,img=cv2.threshold(gray,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)
  prepared=cv2.cvtColor(img,cv2.COLOR_GRAY2RGBA)
  mode='monochrome Otsu';level=float(threshold)
 else:
  prepared=rectified;mode='original colour';level=None
 return dict(quad=c['quad'].tolist(),grid_score=c['score'],chroma=chroma,preprocessing=mode,threshold=level,rectified=rectified,prepared=prepared)

