"""Exploratory DEM-cost joins; no watershed or source authority is implied."""
import argparse,heapq,json,math
from pathlib import Path
import numpy as np
import rasterio
from rasterio.windows import Window, transform as window_transform
from rasterio.features import rasterize
from scipy.ndimage import uniform_filter, minimum_filter
from shapely.geometry import LineString,Point,mapping
from shapely.ops import transform
from geodesic_line import GeodesicLine, GEOD

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--selected',required=True,help='WGS84 GeoJSON LineString geometry')
parser.add_argument('--candidate',required=True,help='WGS84 GeoJSON LineString geometry')
parser.add_argument('--dsm',required=True)
parser.add_argument('--mask',required=True)
parser.add_argument('--stack',required=True)
parser.add_argument('--output-dir',required=True,help='new directory for private research output')
parser.add_argument('--radius-pixels',type=int,default=60)
args=parser.parse_args()
if args.radius_pixels<10:parser.error('radius must be at least 10 pixels')
output=Path(args.output_dir)
output.mkdir(parents=False,exist_ok=False)
geo=json.load(open(args.selected))
candidate=json.load(open(args.candidate))
if geo.get('type')!='LineString' or candidate.get('type')!='LineString' or len(candidate.get('coordinates',[]))<2:
    parser.error('both inputs must be GeoJSON LineString geometries')
selected=GeodesicLine(geo['coordinates'])
with rasterio.open(args.dsm) as ds, rasterio.open(args.mask) as ms, rasterio.open(args.stack) as st:
    if ds.transform!=ms.transform or ds.transform!=st.transform or ds.shape!=ms.shape or ds.shape!=st.shape or ds.crs!=ms.crs or ds.crs!=st.crs or not ds.crs or ds.crs.to_epsg()!=4326:raise ValueError('aligned WGS84 DSM/MSK/STK tiles required')
    if abs(ds.transform.a-1/3600)>1e-10 or abs(ds.transform.e+1/3600)>1e-10 or ds.transform.b!=0 or ds.transform.d!=0:raise ValueError('original north-up 1-arcsecond grid required')
    if ds.nodata is None:raise ValueError('DSM nodata value required')
    for label,coord in [('start',candidate['coordinates'][0]),('end',candidate['coordinates'][-1])]:
        r,c=ds.index(*coord); radius=args.radius_pixels
        if r-radius<0 or c-radius<0 or r+radius>=ds.height or c+radius>=ds.width:raise ValueError('crop extends beyond source tile')
        win=Window(c-radius,r-radius,2*radius+1,2*radius+1)
        aff=window_transform(win,ds.transform)
        z=ds.read(1,window=win).astype('float64')
        valid=(ms.read(1,window=win)==0)&(st.read(1,window=win)>0)&(z!=ds.nodata)
        valid &= minimum_filter(valid.astype('uint8'),size=9,mode='constant',cval=0).astype(bool)
        tpi=z-uniform_filter(z,size=9,mode='nearest')
        source=(radius,radius)
        if not valid[source]:raise ValueError('invalid source neighborhood')
        # Only nearby selected line is targeted; a path may terminate anywhere
        # in this window. Raster targets are approximations to the actual line.
        targets=rasterize([(geo,1)],out_shape=z.shape,transform=aff,all_touched=True).astype(bool)&valid
        targets[source]=False
        if not targets.any():raise ValueError('no valid target')
        for penalty in (0,1,4):
            distances={source:0.0}; prev={}; todo=[(0.0,source)]
            while todo:
                cost,p=heapq.heappop(todo)
                if cost!=distances[p]:continue
                if targets[p]:break
                row,col=p
                x,y=rasterio.transform.xy(aff,row,col)
                for dr in (-1,0,1):
                    for dc in (-1,0,1):
                        if not (dr or dc):continue
                        nr,nc=row+dr,col+dc
                        if not (0<=nr<z.shape[0] and 0<=nc<z.shape[1] and valid[nr,nc]):continue
                        xx,yy=rasterio.transform.xy(aff,nr,nc)
                        _,_,edge=GEOD.inv(x,y,xx,yy)
                        if not math.isfinite(edge) or edge<=0:raise ValueError("invalid WGS84 pixel distance")
                        # TPI below surrounding 9x9 mean adds cost; capped.
                        edge*=1+penalty*min(3,max(0,-tpi[nr,nc])/10)
                        new=cost+edge; q=(nr,nc)
                        if new<distances.get(q,float('inf')):
                            distances[q]=new;prev[q]=p;heapq.heappush(todo,(new,q))
            else:raise ValueError('no path')
            path=[p]
            while path[-1]!=source:path.append(prev[path[-1]])
            path.reverse()
            coords=[rasterio.transform.xy(aff,row,col) for row,col in path]
            lengths=[GEOD.inv(*a,*b)[2] for a,b in zip(coords,coords[1:])]
            closest=selected.closest(coords[-1])
            along=closest['station_m'];distance=closest['distance_m']
            high=sum(1 for row,col in path if tpi[row,col]>0)
            result={'type':'LineString','coordinates':coords}
            with (output / ('join-%s-penalty%d.json'%(label,penalty))).open('x') as out:json.dump(result,out)
            print(label,'penalty',penalty,'pixels',len(path),'length_m',round(sum(lengths),1),'end_offset_m',round(distance,1),'selected_station_m',round(along,1),'closest_ambiguous',closest['ambiguous'],'positive_tpi',high,'/',len(path),flush=True)
