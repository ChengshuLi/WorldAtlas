#!/usr/bin/env python3
"""Inspect geodesic cross-sections against three modeled basin groups."""
import argparse, collections, json
from pyproj import Transformer
from rasterio.transform import rowcol
from spring_connector_graph import basin_labels
from spring_join_profile import station_points


def classify_pairs(labels,t,a,b,offset,n):
    tx=Transformer.from_crs(4326,32640,always_xy=True)
    def group(p):
        r,c=rowcol(t,*tx.transform(*p))
        return int(labels[r,c]) if 0<=r<labels.shape[0] and 0<=c<labels.shape[1] else -1
    length,centers,left,right=station_points(a,b,n,offset)
    return {'length_wgs84_m':length,'center_groups':dict(collections.Counter(str(group(c)) for c in centers)),
            'left_right_pairs':dict(collections.Counter(str(group(l))+':'+str(group(r)) for l,r in zip(left,right)))}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--source-sha',required=True);p.add_argument('--mask');p.add_argument('--mask-sha');p.add_argument('--basin',nargs=3,action='append',required=True);p.add_argument('--bounds',nargs=4,type=float,required=True);p.add_argument('--start',nargs=2,type=float,required=True);p.add_argument('--end',nargs=2,type=float,required=True);p.add_argument('--root',type=int,action='append',required=True);p.add_argument('--resolution',type=float,default=30);p.add_argument('--stations',type=int,default=19);p.add_argument('--offset',type=float,action='append',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    if len(a.root)!=3 or len(set(a.root))!=3 or a.resolution<=0 or bool(a.mask)!=bool(a.mask_sha):raise ValueError('three distinct roots, positive resolution, paired mask and hash required')
    labels,t,_,unknown=basin_labels(a.source,a.source_sha,a.mask,a.mask_sha,a.basin,a.bounds,a.root,a.resolution)
    result={'source_sha256':a.source_sha,'mask_sha256':a.mask_sha,'bounds':a.bounds,'root_order':a.root,'resolution_m':a.resolution,'unclassified_valid':unknown,'start':a.start,'end':a.end,'stations':a.stations,'offsets':{str(o):classify_pairs(labels,t,a.start,a.end,o,a.stations) for o in a.offset},'caveat':'Local model-class sensitivity; points in the same root can cross subbasins; not a surveyed divide.'}
    with open(a.output,'x') as f:json.dump(result,f,indent=2)
    print(json.dumps(result))
