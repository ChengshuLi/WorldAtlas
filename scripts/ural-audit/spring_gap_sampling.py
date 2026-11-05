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
    ecef=Transformer.from_crs(4979,4978,always_xy=True)
    def xyz(points):
        v=np.asarray(points);return np.column_stack(ecef.transform(v[:,0],v[:,1],np.zeros(len(v))))
    tree=cKDTree(xyz(selected));_,indexes=tree.query(xyz(interface),k=min(8,len(selected)))
    indexes=np.asarray(indexes).reshape(len(interface),-1);candidates=[]
    for i,near in enumerate(indexes):
        for j in near:
            d=G.inv(*interface[i],*selected[int(j)])[2];candidates.append((d,i,int(j)))
    d,i,j=min(candidates)
    return {'retained_point':list(selected[j]),'interface_point':list(interface[i]),'sampled_gap_wgs84_m':d,'sample_step_m':step,'retained_samples':len(selected),'interface_samples':len(interface),'method':'sample each line in longitude/latitude, preselect nearest WGS84 ECEF candidates, measure final gaps with WGS84 inverse geodesic','caveat':'Sampled estimate, not an exact continuous geodesic minimum. Source and modeled lines are approximate; not a route approval.'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--source-sha',required=True);p.add_argument('--mask');p.add_argument('--mask-sha');p.add_argument('--basin',nargs=3,action='append',required=True);p.add_argument('--bounds',nargs=4,type=float,required=True);p.add_argument('--retained',required=True);p.add_argument('--retained-sha',required=True);p.add_argument('--root',type=int,action='append',required=True);p.add_argument('--resolution',type=float,default=30);p.add_argument('--step',type=float,default=15);p.add_argument('--output',required=True);a=p.parse_args()
    if len(a.root)!=3 or len(set(a.root))!=3 or a.resolution<=0 or bool(a.mask)!=bool(a.mask_sha):raise ValueError('invalid roots, resolution or mask')
    with open(a.retained,'rb') as f:
        if digest_file(f)!=a.retained_sha:raise ValueError('retained excerpt hash mismatch')
    labels,t,geo,unknown=basin_labels(a.source,a.source_sha,a.mask,a.mask_sha,a.basin,a.bounds,a.root,a.resolution)
    result=sampled_gap(labels,t,geo,json.load(open(a.retained)),a.bounds,a.step);result.update({'source_sha256':a.source_sha,'retained_sha256':a.retained_sha,'bounds':a.bounds,'root_order':a.root,'unclassified_valid':unknown,'status':'preliminary: underlying D8 geographic-distance conversion pending'})
    with open(a.output,'x') as f:json.dump(result,f,indent=2)
    print(json.dumps(result))
