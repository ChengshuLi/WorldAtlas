"""Exact spherical point-to-grid-edge primitives adapted from the verified Chukchi workflow."""
import numpy as np
from scipy.spatial import cKDTree
R=6371008.8

def unit(lat,lon):
 lat=np.deg2rad(lat);lon=np.deg2rad(lon);c=np.cos(lat)
 return np.column_stack((c*np.cos(lon),c*np.sin(lon),np.sin(lat)))

def exact_distances(lat,lon,indices,data):
 """Exact minimum spherical arc distance to candidate meridian/parallel segments."""
 latp=np.deg2rad(np.asarray(lat,dtype=np.float64))[:,None]
 lonp=np.deg2rad(np.asarray(lon,dtype=np.float64))[:,None]
 kind=data['kind'][indices]
 lat0=np.deg2rad(data['lat0'][indices]);lat1=np.deg2rad(data['lat1'][indices])
 lon0=np.deg2rad(data['lon0'][indices]);lon1=np.deg2rad(data['lon1'][indices])
 # Meridians: optimize the spherical dot product over the latitude interval.
 dlon=(lonp-lon0+np.pi)%(2*np.pi)-np.pi
 A=np.sin(latp);B=np.cos(latp)*np.cos(dlon)
 opt=np.arctan2(A,B);lo=np.minimum(lat0,lat1);hi=np.maximum(lat0,lat1)
 phi=np.clip(opt,lo,hi);dot_m=A*np.sin(phi)+B*np.cos(phi)
 # Parallels: longitude is wrapped then clamped to the segment endpoints.
 midlon=(lon0+lon1)/2
 lon_unwrap=midlon+(lonp-midlon+np.pi)%(2*np.pi)-np.pi
 lam=np.clip(lon_unwrap,np.minimum(lon0,lon1),np.maximum(lon0,lon1))
 dot_p=np.sin(latp)*np.sin(lat0)+np.cos(latp)*np.cos(lat0)*np.cos(lonp-lam)
 dot=np.where(kind==0,dot_m,dot_p);dot=np.clip(dot,-1,1)
 angle=np.arctan2(np.sqrt(np.maximum(0,1-dot*dot)),dot)
 return angle*R

def nearest(points,lat,lon,data,tree=None,maxhalf=None,k0=16,tol_m=1e-5,workers=-1):
 """Certify nearest exact segment by a midpoint lower bound, growing k as needed.

    Returns exact distance, selected edge index, and max number of candidates queried.
    The caller must separately prove the loaded edge set includes all in-scope shores.
    """
 if tree is None: tree=cKDTree(data['mids'],compact_nodes=True,balanced_tree=True)
 if maxhalf is None:maxhalf=float(np.max(data['half_lengths']))
 n=len(points);best=np.full(n,np.inf);bestid=np.full(n,-1,dtype=np.int64);maxk=1
 if not len(data['mids']):return best,bestid,maxk
 k=min(k0,len(data['mids']));pending=np.arange(n)
 while len(pending):
  qk=min(k,len(data['mids']));chord,idx=tree.query(points[pending],k=qk,workers=workers)
  if qk==1:chord=chord[:,None];idx=idx[:,None]
  arc_mid=2*R*np.arcsin(np.clip(chord/2,0,1))
  ds=exact_distances(np.asarray(lat)[pending],np.asarray(lon)[pending],idx,data)
  # At a mathematically equal-distance vertex/parallel tie, prefer the lower
  # stable continent code.  A 10-micrometre tolerance is only numerical noise,
  # not a geographic fuzzy tie band.
  if 'category' in data:
   min_d=ds.min(axis=1); eligible=ds<=min_d[:,None]+tol_m
   cats=data['category'][idx]
   ranked=np.where(eligible,cats,255)
   best_cat=ranked.min(axis=1)
   ranked_dist=np.where(cats==best_cat[:,None],ds,np.inf)
   choice=np.argmin(ranked_dist,axis=1)
  else: choice=np.argmin(ds,axis=1)
  bd=ds[np.arange(len(pending)),choice];bi=idx[np.arange(len(pending)),choice]
  improve=bd<best[pending];best[pending[improve]]=bd[improve];bestid[pending[improve]]=bi[improve]
  maxk=max(maxk,qk)
  if qk>=len(data['mids']):break
  resolved=(arc_mid[:,-1]-maxhalf)>best[pending]+tol_m
  pending=pending[~resolved]
  if not len(pending):break
  k=min(qk*2,len(data['mids']))
 return best,bestid,maxk

def edge_data(parts):
 """Build a searchable midpoint set from tuples (lat0,lon0,lat1,lon1,kind[,category])."""
 if not parts:return {'mids':np.empty((0,3)),'lat0':np.empty(0),'lon0':np.empty(0),'lat1':np.empty(0),'lon1':np.empty(0),'kind':np.empty(0,dtype=np.uint8),'half_lengths':np.empty(0)}
 la0=np.concatenate([p[0] for p in parts]).astype(np.float64);lo0=np.concatenate([p[1] for p in parts]).astype(np.float64)
 la1=np.concatenate([p[2] for p in parts]).astype(np.float64);lo1=np.concatenate([p[3] for p in parts]).astype(np.float64)
 kind=np.concatenate([p[4] for p in parts]).astype(np.uint8)
 mids=unit((la0+la1)/2,(lo0+lo1)/2)
 latmid=(la0+la1)/2
 lengths=np.where(kind==0,np.abs(np.deg2rad(la1-la0))*R,np.abs(np.deg2rad(lo1-lo0))*R*np.cos(np.deg2rad(latmid)))
 data={'mids':mids,'lat0':la0,'lon0':lo0,'lat1':la1,'lon1':lo1,'kind':kind,'half_lengths':lengths/2}
 if len(parts[0])>5:data['category']=np.concatenate([p[5] for p in parts]).astype(np.uint8)
 if len(parts[0])>6:data['category_new']=np.concatenate([p[6] for p in parts]).astype(np.uint8)
 if len(parts[0])>7:data['core_segment']=np.concatenate([p[7] for p in parts]).astype(bool)
 return data
