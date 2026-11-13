import cv2
import numpy as np

def order_quad(points):
 p=np.asarray(points,dtype=np.float32).reshape(4,2)
 # Convex cyclic order, then top-left; clockwise image order.
 center=p.mean(axis=0);p=p[np.argsort(np.arctan2(p[:,1]-center[1],p[:,0]-center[0]))]
 p=np.roll(p,-np.argmin(p.sum(axis=1)),axis=0)
 return p

def warp(a,q,size=512):
 return cv2.warpPerspective(a,cv2.getPerspectiveTransform(order_quad(q),np.float32([[0,0],[size,0],[size,size],[0,size]])),(size,size),flags=cv2.INTER_LINEAR,borderMode=cv2.BORDER_REPLICATE)

def grid_score(warped):
 gray=cv2.cvtColor(warped,cv2.COLOR_RGBA2GRAY)
 step=gray.shape[0]/8
 tones=np.empty((8,8))
 for r in range(8):
  for c in range(8):
   patches=[]
   for y in [.13,.87]:
    for x in [.13,.87]:
     xx=int((c+x)*step);yy=int((r+y)*step);rad=max(1,int(step*.045))
     patches.append(float(np.mean(gray[max(0,yy-rad):yy+rad+1,max(0,xx-rad):xx+rad+1])))
   tones[r,c]=np.median(patches)
 parity=np.fromfunction(lambda r,c:1-2*((r+c)%2),(8,8))
 sign=1 if (tones*parity).sum()>0 else -1
 hs=(tones[:,:-1]-tones[:,1:])*parity[:,:-1]*sign
 vs=(tones[:-1,:]-tones[1:,:])*parity[:-1,:]*sign
 medians=np.r_[np.median(hs,axis=1),np.median(vs,axis=0)]
 return float(np.min(medians)),float(np.median(medians))

def candidates(a):
 rgb=a[:,:,:3];gray=cv2.cvtColor(rgb,cv2.COLOR_RGB2GRAY)
 masks=[cv2.Canny(cv2.GaussianBlur(gray,(3,3),0),40,100)]
 masks.append(cv2.morphologyEx(masks[0],cv2.MORPH_CLOSE,np.ones((3,3),np.uint8)))
 for block in [31,61]:masks.append(cv2.adaptiveThreshold(gray,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY,block,5))
 out=[]
 for mask in masks:
  contours,_=cv2.findContours(mask,cv2.RETR_LIST,cv2.CHAIN_APPROX_SIMPLE)
  for cont in contours:
   area=cv2.contourArea(cont)
   if area<a.shape[0]*a.shape[1]*.015:continue
   per=cv2.arcLength(cont,True)
   for ratio in [.01,.02,.035,.05]:
    poly=cv2.approxPolyDP(cont,ratio*per,True)
    if len(poly)!=4 or not cv2.isContourConvex(poly):continue
    q=order_quad(poly); sides=np.linalg.norm(np.roll(q,-1,axis=0)-q,axis=1)
    if min(sides)<min(a.shape[:2])/10 or max(sides)/min(sides)>1.8:continue
    if any(np.max(np.abs(q-p['quad']))<10 for p in out):continue
    w=warp(a,q);score=grid_score(w)
    out.append(dict(quad=q,score=score,area=float(area)))
 return sorted(out,key=lambda x:(x['score'][0],x['score'][1]),reverse=True)
