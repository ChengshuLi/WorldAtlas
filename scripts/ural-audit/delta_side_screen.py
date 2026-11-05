#!/usr/bin/env python3
"""Count center-label differences on two sides of a supplied boundary; research only."""
import argparse, gzip, hashlib, json
import numpy as np
from shapely import contains_xy
from shapely.geometry import LineString, Point, box
from shapely.ops import split, transform
from pyproj import Transformer

def read_grid(path, expected):
    with (gzip.open(path,'rb') if path.endswith('.gz') else open(path,'rb')) as f: data=f.read()
    if hashlib.sha256(data).hexdigest()!=expected: raise ValueError('uncompressed grid checksum mismatch')
    return np.frombuffer(data,dtype='<u4')

def screen(rows,runs,line,bounds,witness_e,witness_a,crs,width,height,step):
    if len(rows)!=height+1 or rows[0]!=0 or rows[-1]*2!=len(runs) or np.any(rows[1:]<=rows[:-1]): raise ValueError('bad row index')
    runs=runs.reshape(-1,2); path=LineString(line); area=box(*bounds)
    if not path.is_simple: raise ValueError('boundary self-intersects')
    pieces=split(area,path)
    if len(pieces.geoms)!=2: raise ValueError('boundary must split box into exactly two polygons')
    ep=[p for p in pieces.geoms if p.contains(Point(*witness_e))]; ap=[p for p in pieces.geoms if p.contains(Point(*witness_a))]
    if len(ep)!=1 or len(ap)!=1 or ep[0].equals(ap[0]): raise ValueError('invalid side witnesses')
    ep,ap=ep[0],ap[0]; w,s,e,n=bounds
    x0=int((w+180)//step); x1=min(width-1,int((e+180)//step)+1)
    y0=int((90-n)//step); y1=min(height-1,int((90-s)//step)+1)
    if min(x0,y0)<0 or x1>=width or y1>=height: raise ValueError('box outside grid')
    proj=Transformer.from_crs(4326,crs,always_xy=True).transform; pl=transform(proj,path)
    found={'asia_labeled_europe':[], 'europe_labeled_asia':[]}; total_land=0; unassigned=0
    for y in range(y0,y1+1):
        xs=np.arange(x0,x1+1,dtype=np.int64); lons=-180+(xs+.5)*step; lat=90-(y+.5)*step
        row=runs[rows[y]:rows[y+1]]
        if not len(row) or row[-1,0]!=width or np.any(row[1:,0]<=row[:-1,0]): raise ValueError('invalid RLE row')
        vals=row[np.searchsorted(row[:,0],xs,side='right'),1]
        ie=contains_xy(ep,lons,lat); ia=contains_xy(ap,lons,lat)
        for key,mask in [('asia_labeled_europe',(vals==19)&ia),('europe_labeled_asia',(vals==18)&ie)]:
            for i in np.flatnonzero(mask):
                d=pl.distance(Point(*proj(float(lons[i]),float(lat))))
                found[key].append({'x':int(xs[i]),'y':int(y),'distance_m':float(d)})
        total_land+=int(np.count_nonzero((vals>=17)&(ie|ia)))
        unassigned+=int(np.count_nonzero((vals>=17)&(~ie)&(~ia)&(lons>w)&(lons<e)&(lat>s)&(lat<n)))
    summary={}
    for k,v in found.items():
        d=[a['distance_m'] for a in v]
        summary[k]={'count':len(v),'distance_quantiles_m':[round(float(x)) for x in np.quantile(d,[0,.25,.5,.75,.9,1])] if d else [],'over_500m':sum(x>500 for x in d),'over_1km':sum(x>1000 for x in d)}
    return {'land_centers':total_land,'unassigned_land_centers':unassigned,'summary':summary},found

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('rows','runs','rows-sha','runs-sha','line','crs','output'): p.add_argument('--'+name,required=True)
    p.add_argument('--bounds',type=float,nargs=4,required=True);p.add_argument('--europe-witness',type=float,nargs=2,required=True);p.add_argument('--asia-witness',type=float,nargs=2,required=True)
    p.add_argument('--width',type=int,required=True);p.add_argument('--height',type=int,required=True);p.add_argument('--step',type=float,required=True)
    a=p.parse_args(); rows=read_grid(a.rows,a.rows_sha);runs=read_grid(a.runs,a.runs_sha)
    line=json.load(open(a.line)); result,found=screen(rows,runs,line,a.bounds,a.europe_witness,a.asia_witness,a.crs,a.width,a.height,a.step)
    result.update({'rows_sha256':a.rows_sha,'runs_sha256':a.runs_sha,'line_file_sha256':hashlib.sha256(open(a.line,'rb').read()).hexdigest(),'bounds':a.bounds,'method':'cell-center two-sided planar split; draft diagnostic; no corrections','differences':found})
    with open(a.output,'x') as f: json.dump(result,f)
    print(json.dumps({k:v for k,v in result.items() if k!='differences'}))
if __name__=='__main__':main()
