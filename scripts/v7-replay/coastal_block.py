"""Conservatively certify coastal row blocks beyond a WGS84 distance band."""
import math
import numpy as np
import shared_nearest as s
import coastal_core as core

def block_classify(lat,lon,bounds,w,h,step,pairs,tol,band,bandtol,idx,block=64,return_stats=False):
 lat=np.asarray(lat,dtype=np.float64);lon=np.asarray(lon,dtype=np.float64)
 if lat.ndim!=1 or lon.shape!=lat.shape or np.any(~np.isfinite(lat)) or np.any(~np.isfinite(lon)) or np.any(np.abs(lat)>90) or np.any(np.abs(lon)>180):raise ValueError('invalid query coordinates')
 if not math.isfinite(tol) or tol<0 or not math.isfinite(band) or band<0 or not math.isfinite(bandtol) or bandtol<0:raise ValueError('invalid distances')
 x0,x1,y0,y1=bounds
 if any(type(z) is not int for z in (x0,x1,y0,y1,w,h)) or not (0<w and 0<h and 0<x1-x0<=w and 0<=y0<y1<=h and math.isfinite(step) and step>0):raise ValueError('invalid crop or grid')
 if abs(step*w-360)>1e-8:raise ValueError('step does not match world width')
 if type(block)!=int or block<=0:raise ValueError('invalid block size')
 n=len(lat);out=np.zeros(n,dtype=np.uint8)
 if not n:return (out,{'bounded':0,'exact':0}) if return_stats else out
 y=(90-lat)/step;x=(lon+180)/step;x=x+np.ceil((x0-x)/w)*w
 if np.any(y<y0-1e-8) or np.any(y>y1+1e-8) or np.any(x<x0-1e-8) or np.any(x>x1+1e-8):raise ValueError('query lies outside crop')
 starts=np.arange(0,n,block,dtype=np.int64);ends=np.minimum(starts+block,n)
 # Rows have a fixed latitude and monotonically increasing longitudes.
 if not np.all(lat==lat[0]) or np.any(np.diff(lon)<0):raise ValueError('single monotone row required')
 mid=(lon[starts]+lon[ends-1])/2.; ml=np.full(len(mid),lat[0]);pts=s.unit(ml,mid)
 available=[p for p in pairs if p[1] in idx];lows=[];nearest=[]
 for _,lc,_ in available:
  data,tree=idx[lc];chord,ix=tree.query(pts,k=1,workers=1);angle=2*np.arcsin(np.clip(chord/2,0,1));lows.append(np.maximum(0,s.MIN_RADIUS*angle-.001));nearest.append((data,ix))
 lows=np.column_stack(lows) if lows else np.empty((len(mid),0))
 low=lows.min(axis=1) if lows.shape[1] else np.full(len(mid),np.inf)
 # Length of a path along the parallel is a conservative upper bound on the
 # ellipsoidal geodesic from midpoint to every cell in that block.
 phi=math.radians(float(lat[0]));ecc2=s.F*(2-s.F);parallel_radius=s.A*math.cos(phi)/math.sqrt(1-ecc2*math.sin(phi)**2)
 radius=parallel_radius*np.deg2rad(np.maximum(mid-lon[starts],lon[ends-1]-mid))+0.01
 boundary=s.boundary_lower(ml,mid,bounds,w,h,step)
 outside=(low-radius>band+bandtol)&(boundary-radius>band+bandtol)
 inside=np.zeros(len(mid),dtype=bool);winner=np.zeros(len(mid),dtype=np.int64)
 if available:
  active=~outside;highs=np.full(lows.shape,np.inf)
  for col,(data,ix) in enumerate(nearest):
   if np.any(active):
    d=s.geodesic_distances(mid[active],ml[active],data['lon'][ix[active]],data['lat'][ix[active]])
    if np.any(~np.isfinite(d)):raise ValueError('invalid inverse geodesic')
    highs[active,col]=d+radius[active]+.000001
  winner=np.argmin(highs,axis=1);upper=highs[np.arange(len(mid)),winner];others=lows.copy();others[np.arange(len(mid)),winner]=np.inf
  inside=active&(upper<=band+bandtol)&(upper+tol<others.min(axis=1)-radius)&(upper+tol<boundary-radius)
  for i,(_,_,code) in enumerate(available):
   rows=np.flatnonzero(inside&(winner==i))
   for j in rows:out[starts[j]:ends[j]]=code
 skip=outside|inside
 need=np.repeat(~skip,ends-starts);q=np.flatnonzero(need)
 stats={'bounded':n-len(q),'exact':0}
 if len(q):
  assigned,base_stats=core.classify(lat[q],lon[q],bounds,w,h,step,pairs,tol,band,bandtol,idx);out[q]=assigned
  stats['bounded']+=base_stats['bounded'];stats['exact']+=base_stats['exact']
 if stats['bounded']+stats['exact']!=n:raise RuntimeError('block accounting mismatch')
 return (out,stats) if return_stats else out
