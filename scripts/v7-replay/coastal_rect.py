"""Research 2-D rectangular certificates with exact WGS84 fallback."""
import math
import numpy as np
import shared_nearest as s
import coastal_core as core

def classify(water,x0,y0,bounds,w,h,step,pairs,tol,band,bandtol,idx,block=32):
 water=np.asarray(water)
 if water.ndim!=2 or water.dtype!=np.bool_:raise ValueError('boolean water grid required')
 nr,nc=water.shape
 if any(type(z) is not int for z in (x0,y0,w,h)) or not(0<w and 0<h and 0<=x0<=x0+nc<=w and 0<=y0<=y0+nr<=h and math.isfinite(step) and step>0 and abs(step*w-360)<=1e-8):raise ValueError('invalid grid')
 if type(block)!=int or block<=0 or not all(math.isfinite(z) and z>=0 for z in (tol,band,bandtol)):raise ValueError('invalid classification parameters')
 if nr and 90-(y0+nr-.5)*step < -90:raise ValueError('query latitude outside globe')
 xa,xb,ya,yb=bounds
 if any(type(z) is not int for z in bounds) or not (0<xb-xa<=w and 0<=ya<yb<=h and y0>=ya and y0+nr<=yb):raise ValueError('invalid crop')
 # Crop may wrap the antimeridian; place core in the same unwrapped copy.
 mapped=x0+math.ceil((xa-x0)/w)*w
 if mapped<xa or mapped+nc>xb:raise ValueError('query outside crop')
 if not nr or not nc:return np.zeros((nr,nc),dtype=np.uint8),{'bounded':0,'exact':0}
 # Summed area lets each rectangle skip land-only regions in constant time.
 sat=np.pad(np.cumsum(np.cumsum(water,axis=0,dtype=np.int64),axis=1,dtype=np.int64),((1,0),(1,0)))
 def wet(y0,y1,x0,x1):return sat[y1,x1]-sat[y0,x1]-sat[y1,x0]+sat[y0,x0]
 ys,xs=np.meshgrid(np.arange(0,nr,block),np.arange(0,nc,block),indexing='ij');a=ys.ravel();c=xs.ravel();b=np.minimum(a+block,nr);d=np.minimum(c+block,nc)
 mask=wet(a,b,c,d)>0;a,b,c,d=a[mask],b[mask],c[mask],d[mask]
 output=np.zeros(water.shape,dtype=np.uint8);available=[p for p in pairs if p[1] in idx];unresolved=[]
 while len(a):
  # Centers are midpoints between extreme grid-cell centers.
  ml=90-(y0+(a+b)/2)*step;mid=-180+(x0+(c+d)/2)*step;pts=s.unit(ml,mid)
  half_lat=(b-a-1)*step/2;half_lon=(d-c-1)*step/2
  # The linear lat/lon path is bounded by the maximum principal radius
  # and the maximum parallel radius attained within the rectangle.
  rmax=s.A/(1-s.F);closest_abs=np.maximum(0,np.abs(ml)-half_lat)
  radius=np.hypot(rmax*np.deg2rad(half_lat),rmax*np.cos(np.deg2rad(closest_abs))*np.deg2rad(half_lon))+.01
  lows=[];nearest=[]
  for _,lc,_ in available:
   data,tree=idx[lc];chord,ix=tree.query(pts,k=1,workers=1);lows.append(np.maximum(0,s.MIN_RADIUS*chord-.01));nearest.append((data,ix))
  lows=np.column_stack(lows) if lows else np.empty((len(mid),0));low=lows.min(axis=1) if lows.shape[1] else np.full(len(mid),np.inf)
  boundary=s.boundary_lower(ml,mid,bounds,w,h,step);outside=(low-radius>band+bandtol)&(boundary-radius>band+bandtol);inside=np.zeros(len(mid),dtype=bool)
  if available:
   active=~outside;highs=np.full(lows.shape,np.inf)
   for col,(data,ix) in enumerate(nearest):
    if np.any(active):
     dist=s.geodesic_distances(mid[active],ml[active],data['lon'][ix[active]],data['lat'][ix[active]])
     if np.any(~np.isfinite(dist)):raise ValueError('invalid inverse geodesic')
     highs[active,col]=dist+radius[active]+.000001
   winner=np.argmin(highs,axis=1);upper=highs[np.arange(len(mid)),winner];others=lows.copy();others[np.arange(len(mid)),winner]=np.inf
   inside=active&(upper<=band+bandtol)&(upper+tol<others.min(axis=1)-radius)&(upper+tol<boundary-radius)
   for k,(_,_,code) in enumerate(available):
    for i in np.flatnonzero(inside&(winner==k)):output[a[i]:b[i],c[i]:d[i]]=code
  pending=~(outside|inside);leaf=pending&(b-a==1)&(d-c==1)
  if np.any(leaf):unresolved.append((a[leaf],c[leaf]))
  pending &= ~leaf;a,b,c,d=a[pending],b[pending],c[pending],d[pending]
  if not len(a):break
  # Four children if both dimensions exceed one, two otherwise.
  ym=np.where(b-a>1,(a+b)//2,b);xm=np.where(d-c>1,(c+d)//2,d)
  aa=np.concatenate([a,a,ym,ym]);bb=np.concatenate([ym,ym,b,b]);cc=np.concatenate([c,xm,c,xm]);dd=np.concatenate([xm,d,xm,d]);valid=(aa<bb)&(cc<dd)
  aa,bb,cc,dd=aa[valid],bb[valid],cc[valid],dd[valid];valid=wet(aa,bb,cc,dd)>0;a,b,c,d=aa[valid],bb[valid],cc[valid],dd[valid]
 ny=np.concatenate([q[0] for q in unresolved]) if unresolved else np.empty(0,dtype=np.int64);nx=np.concatenate([q[1] for q in unresolved]) if unresolved else np.empty(0,dtype=np.int64)
 stats={'bounded':int(water.sum())-len(ny),'exact':0}
 if len(ny):
  lat=90-(y0+ny+.5)*step;lon=-180+(x0+nx+.5)*step
  codes,s0=core.classify(lat,lon,bounds,w,h,step,pairs,tol,band,bandtol,idx);output[ny,nx]=codes;stats['bounded']+=s0['bounded'];stats['exact']+=s0['exact']
 if stats['bounded']+stats['exact']!=int(water.sum()):raise RuntimeError('accounting mismatch')
 return output,stats
"""Research scanline extraction of orthogonal shoreline centers from RLE."""
import math
import numpy as np
import shared_nearest as s

def spans(grid,y,x0,x1,width):
 rows,runs=grid;first,last=int(rows[y]),int(rows[y+1]);ends=runs[2*first:2*last:2];vals=runs[2*first+1:2*last:2]
 if not len(ends) or int(ends[0])<=0 or int(ends[-1])!=width or np.any(ends[1:]<=ends[:-1]):raise ValueError('invalid RLE row')
 out_e=[];out_v=[];x=x0
 while x<x1:
  xm=x%width; take=min(x1-x,width-xm);stop=xm+take
  i=int(np.searchsorted(ends,xm,side='right'));j=int(np.searchsorted(ends,stop,side='left'))+1
  ee=np.minimum(ends[i:j].astype(np.int64),stop)-xm+x
  out_e.extend(ee.tolist());out_v.extend(vals[i:j].tolist());x+=take
 return np.asarray(out_e,dtype=np.int64),np.asarray(out_v,dtype=np.int64)

def centers_for_crop(physical,land,bounds,width,height,step,land_codes):
 x0,x1,y0,y1=bounds
 if not (0<=y0<y1<=height and 0<x1-x0<=width and math.isfinite(step) and step>0):raise ValueError('invalid crop')
 selected=np.zeros(23,dtype=bool);selected[land_codes]=True
 latitudes=[];longitudes=[];categories=[];count=0
 # full-width crops cannot be extended in the original crop helper, but this
 # span reader intentionally supports repeated wrapping for the side halo.
 def pget(y):
  e,v=spans(physical,y,x0-1,x1+1,width)
  if np.any((v!=1)&(v!=17)):raise ValueError('invalid physical or land row')
  return e,v
 prev=pget(y0-1) if y0>0 else None;cur=pget(y0);nxt=pget(y0+1) if y0+1<height else None
 for y in range(y0,y1):
  le,lv=spans(land,y,x0,x1,width)
  # Break at all changes in either adjacent physical row, current physical
  # row, or land category. Side halo endpoints are clipped out.
  breaks=[np.array([x0,x1]),le,cur[0]]
  if prev is not None:breaks.append(prev[0])
  if nxt is not None:breaks.append(nxt[0])
  b=np.unique(np.concatenate(breaks));b=b[(b>=x0)&(b<=x1)];starts=b[:-1];ends=b[1:]
  mv=cur[1][np.searchsorted(cur[0],starts,side='right')]
  cats=lv[np.searchsorted(le,starts,side='right')]
  bad=(mv==17)&((cats<17)|(cats>22))
  if np.any(bad):raise ValueError('invalid physical or land row')
  wet=np.zeros(len(starts),dtype=bool)
  for row in (prev,nxt):
   if row is not None:wet |= row[1][np.searchsorted(row[0],starts,side='right')]==1
  chosen=(mv==17)&selected[np.clip(cats,0,22)]&wet
  starts1=starts[chosen];ends1=ends[chosen]
  xx=np.concatenate([np.arange(a,b,dtype=np.int64) for a,b in zip(starts1,ends1)]) if len(starts1) else np.empty(0,dtype=np.int64)
  # Horizontal coast consists of the land cell on each wet/dry run boundary.
  ce,cv=cur; t=np.flatnonzero(cv[:-1]!=cv[1:]);boundary=ce[t]
  side=np.where(cv[t]==17,boundary-1,boundary);side=side[(side>=x0)&(side<x1)]
  if len(side):
   sc=lv[np.searchsorted(le,side,side='right')];side=side[selected[np.clip(sc,0,22)]]
   xx=np.union1d(xx,side)
  count+=len(xx)
  if len(xx):
   latitudes.append(np.full(len(xx),90-(y+.5)*step));longitudes.append(((-180+(xx+.5)*step+180)%360)-180)
   categories.append(lv[np.searchsorted(le,xx,side='right')].astype(np.uint8))
  prev,cur=cur,nxt
  nxt=pget(y+2) if y+2<height and y+1<y1 else None
 if not count:raise ValueError('no participant shorelines in crop')
 lat=np.concatenate(latitudes);lon=np.concatenate(longitudes);cat=np.concatenate(categories)
 return {'mids':s.unit(lat,lon),'lat':lat,'lon':lon,'category':cat}
