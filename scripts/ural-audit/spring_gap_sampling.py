#!/usr/bin/env python3
"""Sample geodesic gaps between selected mountain line and modeled interface."""
import argparse,json,math
import numpy as np
from pyproj import Geod,Transformer
from scipy.spatial import cKDTree
from shapely.geometry import LineString,box
from spring_connector_graph import basin_labels
from terrain_basin_screen import digest_file

G=Geod(ellps='WGS84')
SEARCH_CUSHION_M=.001  # Tested floating-point margin, not a formal proof.

def closest_sampled_pair(selected,interface):
    """WGS84 nearest sampled pair, using ECEF chord only as a lower bound."""
    s=np.asarray(selected,dtype=float);q=np.asarray(interface,dtype=float)
    if (s.ndim!=2 or q.ndim!=2 or s.shape[1:]!=(2,) or q.shape[1:]!=(2,) or not len(s) or not len(q)
            or not np.isfinite(s).all() or not np.isfinite(q).all()
            or np.any(np.abs(s[:,0])>180) or np.any(np.abs(q[:,0])>180)
            or np.any(np.abs(s[:,1])>90) or np.any(np.abs(q[:,1])>90)):
        raise ValueError('invalid sampled geographic points')
    ecef=Transformer.from_crs(4979,4978,always_xy=True)
    def xyz(points):return np.column_stack(ecef.transform(points[:,0],points[:,1],np.zeros(len(points))))
    sxyz=xyz(s);qxyz=xyz(q)
    if not np.isfinite(sxyz).all() or not np.isfinite(qxyz).all():raise ValueError('invalid ECEF samples')
    tree=cKDTree(sxyz);_,first=tree.query(qxyz,k=1,workers=1);first=np.asarray(first,dtype=np.int64)
    _,_,initial=G.inv(q[:,0],q[:,1],s[first,0],s[first,1]);initial=np.asarray(initial)
    if not np.isfinite(initial).all() or np.any(initial<0):raise ValueError('invalid WGS84 sample distances')
    i=int(np.argmin(initial));best=(float(initial[i]),i,int(first[i]))
    for i,point in enumerate(qxyz):
        # A straight ECEF chord cannot exceed the surface geodesic. Any pair
        # capable of improving the incumbent must lie within this chord ball.
        radius=np.nextafter(best[0]+SEARCH_CUSHION_M,math.inf)
        ids=tree.query_ball_point(point,radius,workers=1)
        if not ids:continue
        ids=np.asarray(sorted(ids),dtype=np.int64)
        _,_,dist=G.inv(np.full(len(ids),q[i,0]),np.full(len(ids),q[i,1]),s[ids,0],s[ids,1]);dist=np.asarray(dist)
        if not np.isfinite(dist).all() or np.any(dist<0):raise ValueError('invalid WGS84 sample distances')
        k=int(np.argmin(dist));candidate=(float(dist[k]),i,int(ids[k]))
        if candidate<best:best=candidate
    return best


def densify(line,step):
    result=[]
    for a,b in zip(line,line[1:]):
        length=G.inv(*a,*b)[2];n=max(1,math.ceil(length/step))
        result.extend([(a[0]+(b[0]-a[0])*i/n,a[1]+(b[1]-a[1])*i/n) for i in range(n)])
    result.append(tuple(line[-1]));return result


def sampled_gap(labels,t,to_geo,retained,bounds,step):
    if step<=0:raise ValueError('positive sampling step required')
    h,w=labels.shape;clipped=LineString(retained).intersection(box(*bounds));parts=list(clipped.geoms) if hasattr(clipped,'geoms') else [clipped]
    selected=[]
    for part in parts:
        if part.is_empty:continue
        if part.geom_type!='LineString':raise ValueError('unexpected clipped retained geometry')
        selected.extend(densify(list(part.coords),step))
    if not selected:raise ValueError('retained line does not cross scope')
    edges=[]
    a,b=labels[:,:-1],labels[:,1:];rs,cs=np.where(((a==1)&(b==2))|((a==2)&(b==1)))
    edges.extend([((int(r),int(c+1)),(int(r+1),int(c+1))) for r,c in zip(rs,cs)])
    a,b=labels[:-1,:],labels[1:,:];rs,cs=np.where(((a==1)&(b==2))|((a==2)&(b==1)))
    edges.extend([((int(r+1),int(c)),(int(r+1),int(c+1))) for r,c in zip(rs,cs)])
    interface=[]
    for a,b in edges:
        x=to_geo.transform(*(t*(a[1],a[0])));y=to_geo.transform(*(t*(b[1],b[0])));interface.extend(densify([x,y],step))
    if not interface:raise ValueError('modeled interface absent')
    d,i,j=closest_sampled_pair(selected,interface)
    return {'retained_point':list(selected[j]),'interface_point':list(interface[i]),'sampled_gap_wgs84_m':d,'sample_step_m':step,'retained_samples':len(selected),'interface_samples':len(interface),'method':'sample coordinate-linear lines; use an ECEF chord lower bound to retain potentially closer pairs and WGS84 inverse geodesics for final ranking','caveat':'Sampled estimate, not an exact continuous geodesic minimum; sample step is a target, not a proven maximum spacing. The 1 mm floating-point search cushion is an engineering guard, not a formal proof. Source and modeled lines are approximate; not a route approval.'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--source-sha',required=True);p.add_argument('--mask');p.add_argument('--mask-sha');p.add_argument('--basin',nargs=3,action='append',required=True);p.add_argument('--bounds',nargs=4,type=float,required=True);p.add_argument('--retained',required=True);p.add_argument('--retained-sha',required=True);p.add_argument('--root',type=int,action='append',required=True);p.add_argument('--resolution',type=float,default=30);p.add_argument('--step',type=float,default=15);p.add_argument('--output',required=True);a=p.parse_args()
    if len(a.root)!=3 or len(set(a.root))!=3 or a.resolution<=0 or bool(a.mask)!=bool(a.mask_sha):raise ValueError('invalid roots, resolution or mask')
    with open(a.retained,'rb') as f:
        if digest_file(f)!=a.retained_sha:raise ValueError('retained excerpt hash mismatch')
    labels,t,geo,unknown=basin_labels(a.source,a.source_sha,a.mask,a.mask_sha,a.basin,a.bounds,a.root,a.resolution)
    result=sampled_gap(labels,t,geo,json.load(open(a.retained)),a.bounds,a.step);result.update({'source_sha256':a.source_sha,'retained_sha256':a.retained_sha,'bounds':a.bounds,'root_order':a.root,'unclassified_valid':unknown,'status':'preliminary WGS84 sampled research; not approved'})
    with open(a.output,'x') as f:json.dump(result,f,indent=2)
    print(json.dumps(result))

