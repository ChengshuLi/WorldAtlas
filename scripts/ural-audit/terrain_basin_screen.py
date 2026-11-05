#!/usr/bin/env python3
"""Screen a selected line against a local DEM D8/HydroBASINS outlet crosswalk."""
import argparse,hashlib,json,os,zipfile
import numpy as np
import rasterio,shapefile
from shapely.geometry import Point,LineString,shape
from shapely.strtree import STRtree
from pyproj import Transformer
from rasterio.warp import transform_bounds
from priority_d8 import drainage

def digest_file(f):
    h=hashlib.sha256()
    for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()

def checked_shapes(archive,expected,shp,bbox):
    with open(archive,'rb') as f:
        if digest_file(f)!=expected:raise ValueError('basin archive checksum mismatch')
    stem=os.path.splitext(os.path.basename(shp))[0]
    with zipfile.ZipFile(archive) as z:
        for ext in ('.shp','.shx','.dbf'):
            path=os.path.splitext(shp)[0]+ext;names=[x for x in z.namelist() if os.path.basename(x)==stem+ext]
            if len(names)!=1:raise ValueError('missing shapefile part')
            with z.open(names[0]) as a,open(path,'rb') as b:
                if digest_file(a)!=digest_file(b):raise ValueError('extracted shapefile differs from archive')
    r=shapefile.Reader(shp);features=[]
    for sr in r.iterShapeRecords(bbox=bbox):
        rec=sr.record.as_dict();features.append((shape(sr.shape.__geo_interface__),int(rec['MAIN_BAS'])))
    return features

def screen(dem,dem_sha,basins,line,west,east,offsets,spacing):
    with open(dem,'rb') as f:
        if digest_file(f)!=dem_sha:raise ValueError('crop checksum mismatch')
    with rasterio.open(dem) as ds:
        z=ds.read(1).astype('float64');valid=np.isfinite(z);trans=ds.transform;crs=ds.crs
        if crs is None or trans.a<=0 or trans.e>=0 or abs(trans.a+trans.e)>1e-9 or trans.b or trans.d:raise ValueError('expected square north-up metric grid')
        bounds=transform_bounds(crs,'EPSG:4326',*ds.bounds,densify_pts=21)
    west=set(west);east=set(east)
    if not west or not east or west&east:raise ValueError('invalid root groups')
    features=[]
    for archive,sha,shp in basins:features.extend(checked_shapes(archive,sha,shp,bounds))
    if not features:raise ValueError('no source basins overlap crop')
    geoms=[x[0] for x in features];tree=STRtree(geoms);root_ids=[x[1] for x in features]
    roots,_,_=drainage(z,valid,trans.a);h,w=z.shape;outlet_ids=np.unique(roots[roots>=0]);to_geo=Transformer.from_crs(crs,4326,always_xy=True).transform;to_metric=Transformer.from_crs(4326,crs,always_xy=True).transform
    classifications=np.zeros(h*w,dtype=np.uint8);outlet_stats={'west':0,'east':0,'unknown':0,'conflict':0}
    for index in outlet_ids:
        row,col=divmod(int(index),w);x,y=rasterio.transform.xy(trans,row,col);point=Point(*to_geo(x,y));hits={root_ids[i] for i in tree.query(point) if geoms[i].covers(point)}
        hasw=bool(hits&west);hase=bool(hits&east)
        if hasw and hase:outlet_stats['conflict']+=1
        elif hasw:classifications[index]=1;outlet_stats['west']+=1
        elif hase:classifications[index]=2;outlet_stats['east']+=1
        else:outlet_stats['unknown']+=1
    labels=np.zeros((h,w),dtype=np.uint8);ok=roots>=0;labels[ok]=classifications[roots[ok]]
    route=LineString([to_metric(*p) for p in line]);station_distances=np.arange(0,route.length+0.001,spacing);counts={str(o):{} for o in offsets};details=[]
    for dist in station_distances:
        mid=route.interpolate(dist);l=route.interpolate(max(0,dist-5));r=route.interpolate(min(route.length,dist+5));dx=r.x-l.x;dy=r.y-l.y;norm=np.hypot(dx,dy)
        if norm==0:raise ValueError('undefined tangent')
        station={'distance_m':float(dist),'point_lonlat':list(to_geo(mid.x,mid.y)),'pairs':{}}
        for off in offsets:
            pair=[]
            for sign in (-1,1):
                x=mid.x-sign*off*dy/norm;y=mid.y+sign*off*dx/norm;row,col=rasterio.transform.rowcol(trans,x,y)
                pair.append(int(labels[row,col]) if 0<=row<h and 0<=col<w else -1)
            key='-'.join(map(str,pair));c=counts[str(off)];c[key]=c.get(key,0)+1
            station['pairs'][str(off)]=pair
        details.append(station)
    return {'dem_sha256':dem_sha,'shape':[h,w],'valid_cells':int(valid.sum()),'unrouted_valid_cells':int(np.count_nonzero(valid&(roots<0))),'outlets':outlet_stats,'label_cell_counts':{'west':int((labels==1).sum()),'east':int((labels==2).sum()),'unknown_valid':int((valid&(labels==0)).sum())},'line_length_m':route.length,'stations':len(station_distances),'offset_pair_counts':counts,'station_details':details,'note':'Local DSM D8 and basin-root model; pair labels -1=outside crop, 0=masked or unclassified, 1=west group, 2=east group. No boundary selection is implied.'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--dem',required=True);p.add_argument('--dem-sha',required=True);p.add_argument('--basin',nargs=3,action='append',required=True,metavar=('ZIP','SHA','SHP'));p.add_argument('--line',required=True);p.add_argument('--west-root',type=int,action='append',required=True);p.add_argument('--east-root',type=int,action='append',required=True);p.add_argument('--offset',type=float,action='append',required=True);p.add_argument('--spacing',type=float,default=250);p.add_argument('--output',required=True)
    a=p.parse_args()
    if a.spacing<=0 or any(x<=0 for x in a.offset):raise ValueError('invalid spacing/offset')
    result=screen(a.dem,a.dem_sha,a.basin,json.load(open(a.line)),a.west_root,a.east_root,a.offset,a.spacing)
    with open(a.output,'x') as f:json.dump(result,f)
    print(json.dumps(result))
