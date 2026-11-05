"""Compare gap and selected-line cross-profiles using clean unfilled Copernicus elevations."""
import json,math,numpy as np,rasterio
from collections import Counter
from geodesic_line import GeodesicLine,GEOD
from rasterio.transform import rowcol
paths=['copernicus90-n41e047-'+x+'.tif' for x in ('DEM','EDM','FLM','WBM')];ds=[rasterio.open(p) for p in paths];gap=GeodesicLine(json.load(open('east-gap-exploratory-1.json'))['coordinates'][::-1]);source=GeodesicLine(json.load(open('caucasus-line.json'))['coordinates']);results=[]
def profile(line,station):
 p=line.point(station);az=GEOD.inv(*line.point(station-25),*line.point(station+25))[0];z=[]
 for off in (-250,0,250):
  lon,lat=GEOD.fwd(*p,az+90,off)[:2];r,c=rowcol(ds[0].transform,lon,lat);v=[x.read(1,window=((r,r+1),(c,c+1)))[0,0].item() for x in ds];z.append(v)
 clean=all(np.isfinite(v[0]) and v[1:]==[1,2,0] for v in z); score=z[1][0]-max(z[0][0],z[2][0]);return clean,float(score)
for i in range(math.floor(gap.length/100)+1):
 s=i*100;p=gap.point(s);near=source.closest(p);results.append({'gap_station_m':s,'source_distance_m':near['distance_m'],'source_station_m':near['station_m'],'source_ambiguous':near['ambiguous'],'gap_profile':profile(gap,s),'source_profile':profile(source,near['station_m'])})
for label in ('gap_profile','source_profile'):
 good=[x[label][1] for x in results if x[label][0]]; print(label,'valid',len(good),'higher',sum(x>0 for x in good),'min/median/max',float(min(good)),float(np.median(good)),float(max(good)))
print('distance min/max',min(x['source_distance_m'] for x in results),max(x['source_distance_m'] for x in results),'nearest ties',sum(x['source_ambiguous'] for x in results));print('unique source points',len(set(round(x['source_station_m'],1) for x in results)));json.dump(results,open('east-gap-clean-source-comparison-results.json','w'),indent=2)
