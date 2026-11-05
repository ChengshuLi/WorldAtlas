#!/usr/bin/env python3
"""Construct an exploratory nearest-join ridge alternative and count enclosed land centers."""
import argparse, gzip, hashlib, json, xml.etree.ElementTree as ET
import numpy as np
from shapely import contains_xy
from shapely.geometry import Point, LineString
from shapely.ops import substring, polygonize, transform, unary_union
from pyproj import Transformer
from projected_route import ProjectedRoute

def verified(path, expected, compressed=False):
    with (gzip.open(path,'rb') if compressed else open(path,'rb')) as f: data=f.read()
    if hashlib.sha256(data).hexdigest()!=expected: raise ValueError('input checksum mismatch')
    return data

def compare(ridge,selected,project,inverse,rows,runs,width,height,step,crs):
    line=LineString([project(*p) for p in selected]); mapped=LineString([project(*p) for p in ridge]); a=Point(line.coords[0]); b=Point(line.coords[-1])
    if not line.is_simple or not mapped.is_simple: raise ValueError('non-simple input')
    route=ProjectedRoute(ridge,crs)
    join_a,xy_a,_=route.nearest(*selected[0]);join_b,xy_b,_=route.nearest(*selected[-1])
    # project() supplies a coordinate parameter to substring, not a geographic distance.
    sub=substring(mapped,mapped.project(Point(*xy_a)),mapped.project(Point(*xy_b)))
    if sub.geom_type!='LineString' or sub.length==0: raise ValueError('degenerate mapped segment')
    alt=LineString([a.coords[0]]+list(sub.coords)+[b.coords[0]])
    if not alt.is_simple: raise ValueError('non-simple alternative')
    polygons=list(polygonize(unary_union([line,alt])))
    if not polygons: raise ValueError('no enclosed comparison area')
    lobes=[]
    for projected in polygons:
        poly=transform(inverse,projected);w,s,e,n=poly.bounds; cells=[]
        for y in range(max(0,int((90-n)//step)),min(height-1,int((90-s)//step)+1)+1):
            xs=np.arange(max(0,int((w+180)//step)),min(width-1,int((e+180)//step)+1)+1,dtype=np.int64)
            lat=90-(y+.5)*step;lons=-180+(xs+.5)*step; row=runs[rows[y]:rows[y+1]]
            if not len(row) or row[-1,0]!=width or np.any(row[1:,0]<=row[:-1,0]): raise ValueError('invalid grid row')
            vals=row[np.searchsorted(row[:,0],xs,side='right'),1]
            cells.extend([[int(xs[i]),int(y)] for i in np.flatnonzero(contains_xy(poly,lons,lat)&(vals==17))])
        lobes.append({'area_m2':round(projected.area),'land_center_cells':cells})
    coords=[list(inverse(x,y)) for x,y in alt.coords];coords[0]=selected[0];coords[-1]=selected[-1]
    ridge_geo=[list(inverse(x,y)) for x,y in sub.coords]
    return {'ridge_length_m':ProjectedRoute(ridge_geo,crs).length,'alternative_length_m':ProjectedRoute(coords,crs).length,'start_join_m':join_a,'end_join_m':join_b,'coordinates':coords,'lobes':lobes,'distance_method':'WGS84 geodesic numerical nearest joins and chord-sum path length along projected-linear geometry; numerical estimates, not certified nearest or exact path length'}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('osm','osm-sha','way-id','selected','rows','rows-sha','runs','runs-sha','crs','output'): p.add_argument('--'+name,required=True)
    p.add_argument('--width',type=int,required=True);p.add_argument('--height',type=int,required=True);p.add_argument('--step',type=float,required=True)
    a=p.parse_args(); root=ET.fromstring(verified(a.osm,a.osm_sha)); nodes={n.get('id'):(float(n.get('lon')),float(n.get('lat'))) for n in root.findall('node')};way=root.find("way[@id='"+a.way_id+"']")
    if way is None: raise ValueError('way missing')
    ridge=[nodes[n.get('ref')] for n in way.findall('nd')]; selected=json.load(open(a.selected)); rows=np.frombuffer(verified(a.rows,a.rows_sha,True),'<u4');runs=np.frombuffer(verified(a.runs,a.runs_sha,True),'<u4').reshape(-1,2)
    if len(rows)!=a.height+1 or rows[0]!=0 or rows[-1]!=len(runs) or np.any(rows[1:]<=rows[:-1]): raise ValueError('invalid grid index')
    fwd=Transformer.from_crs(4326,a.crs,always_xy=True).transform; inv=Transformer.from_crs(a.crs,4326,always_xy=True).transform
    result=compare(ridge,selected,fwd,inv,rows,runs,a.width,a.height,a.step,a.crs)
    result.update({'way_id':a.way_id,'way_version':way.get('version'),'osm_sha256':a.osm_sha,'rows_sha256':a.rows_sha,'runs_sha256':a.runs_sha,'selected_file_sha256':hashlib.sha256(open(a.selected,'rb').read()).hexdigest(),'method':'WGS84 numerical nearest ridge joins and coordinate-topology polygonized difference; exploratory only'})
    with open(a.output,'x') as f:json.dump(result,f)
    print(json.dumps({'ridge_length_m':result['ridge_length_m'],'alternative_length_m':result['alternative_length_m'],'start_join_m':result['start_join_m'],'end_join_m':result['end_join_m'],'land_counts':[len(x['land_center_cells']) for x in result['lobes']]}))
if __name__=='__main__':main()

