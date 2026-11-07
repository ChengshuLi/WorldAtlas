"""Research screen of unselected gap using raw DEM samples, no flow-seed assumptions."""
import json,math
import numpy as np,rasterio
from collections import Counter
from geodesic_line import GeodesicLine,GEOD
from rasterio.transform import rowcol
p=['copernicus90-n41e047-'+x+'.tif' for x in ['DEM','EDM','FLM','WBM']]; ds=[rasterio.open(x) for x in p];assert all(d.crs.to_epsg()==4326 and d.transform==ds[0].transform for d in ds)
line=GeodesicLine(json.load(open('east-gap-exploratory-1.json'))['coordinates'][::-1]);out=[]
for k in range(math.floor(line.length/100)+1):
 s=100*k;a=line.point(max(0,s-25));b=line.point(min(line.length,s+25));p=line.point(s);az=GEOD.inv(*a,*b)[0];samples=[]
 for offset in (-500,-250,-100,0,100,250,500):
  lon,lat=GEOD.fwd(*p,az+90,offset)[:2];r,c=rowcol(ds[0].transform,lon,lat); z,edm,flm,wbm=[d.read(1,window=((r,r+1),(c,c+1)))[0,0].item() for d in ds];samples.append({'offset':offset,'z':z,'mask':[edm,flm,wbm],'clean':bool(np.isfinite(z) and edm==1 and flm==2 and wbm==0)})
 out.append({'s':s,'samples':samples})
for d in (100,250,500):
 valid=[row for row in out if all(row['samples'][i]['clean'] for i in (3,{100:2,250:1,500:0}[d],{100:4,250:5,500:6}[d]))]
 counts=Counter(('center_higher_both' if row['samples'][3]['z']>row['samples'][{100:2,250:1,500:0}[d]]['z'] and row['samples'][3]['z']>row['samples'][{100:4,250:5,500:6}[d]]['z'] else 'other') for row in valid)
 print('offset',d,'clean_triples',len(valid),'counts',dict(counts),'of',len(out))
print('clean counts by offset',{offset:sum(r['samples'][j]['clean'] for r in out) for j,offset in enumerate((-500,-250,-100,0,100,250,500))})
json.dump(out,open('east-gap-clean-cross-profile-results.json','w'),indent=2)
