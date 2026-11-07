"""JAXA terrain profiles around Klukhor; empirical screen, not hydrologic validation."""
import json,numpy as np,rasterio
from collections import Counter
from geodesic_line import GeodesicLine,GEOD
p=(41+52/60+3.96/3600,43+14/60+39.42/3600);line=GeodesicLine(json.load(open('caucasus-line.json'))['coordinates']);near=line.closest(p);print('landmark',p,'closest',near)
base='original/N043E041/ALPSMLC30_N043E041_'
with rasterio.open(base+'DSM.tif') as z,rasterio.open(base+'MSK.tif') as m,rasterio.open(base+'STK.tif') as st:
 for dist in (100,250,500):
  c=Counter()
  for off in range(-1000,1001,100):
   s=near['station_m']+off;q=line.point(s);a=line.point(s-20);b=line.point(s+20);az=GEOD.inv(*a,*b)[0];coords=[GEOD.fwd(*q,az-90,dist)[:2],q,GEOD.fwd(*q,az+90,dist)[:2]];values=[];valid=True
   for point in coords:
    r,cc=z.index(*point);win=((r-1,r+2),(cc-1,cc+2));zz=z.read(1,window=win);mm=m.read(1,window=win);ss=st.read(1,window=win)
    if zz.shape!=(3,3) or not ((mm==0)&(ss>0)&(zz!=z.nodata)).all():valid=False;break
    values.append(int(zz[1,1]))
   if not valid:c['invalid']+=1;continue
   left,center,right=values
   label='center_high' if center>max(left,right) else ('center_low' if center<min(left,right) else 'mixed_or_tied')
   c[label]+=1
   if off in (-500,0,500):print('offset',off,'side_distance',dist,'heights',values,'class',label)
  print('distance',dist,'counts',dict(c))
