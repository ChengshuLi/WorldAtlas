"""Experimental 1978 SK42 grid registration; no field or independent landmark certification."""
import json
import rasterio,numpy as np
from rasterio.control import GroundControlPoint
from rasterio.transform import from_gcps
from pyproj import Transformer,Geod
with rasterio.open('k38-108-vlasenko.jpg') as d:im=d.read()[:3].astype('int16')
b=im.max(axis=0)<125;rows=np.arange(950,1291);cols=np.arange(1860,2191)
V=[];H=[]
for east,x in [(8740000,1903),(8742000,2021),(8744000,2139)]:
 best=max((np.mean(b[rows,np.rint(i+k*(rows-1090)).astype(int)]),i,k) for i in np.arange(x-8,x+8,.25) for k in np.arange(-.05,.001,.0025));V.append((east,best[1],best[2],best[0]))
for north,y in [(4568000,969),(4566000,1089),(4564000,1209)]:
 best=max((np.mean(b[np.rint(i+k*(cols-2021)).astype(int),cols]),i,k) for i in np.arange(y-8,y+8,.25) for k in np.arange(0,.041,.0025));H.append((north,best[1],best[2],best[0]))
controls=[]
for e,x0,sv,_ in V:
 for n,y0,sh,_ in H:
  # x=x0+sv*(y-1090); y=y0+sh*(x-2021)
  x=(x0+sv*(y0-1090-sh*2021))/(1-sv*sh);y=y0+sh*(x-2021);controls.append((x,y,e,n))
train=[q for q in controls if q[3]!=4566000];test=[q for q in controls if q[3]==4566000];a=from_gcps([GroundControlPoint(row=y,col=x,x=e,y=n) for x,y,e,n in train]);inv=~a;to=Transformer.from_crs(4326,28408,always_xy=True);back=Transformer.from_crs(28408,4326,always_xy=True);geod=Geod(ellps='WGS84')
err=[geod.inv(*back.transform(e,n),*back.transform(*(a*(x,y))))[2] for x,y,e,n in test]
out={'controls':controls,'train_n':len(train),'heldout_n':len(test),'heldout_errors_m':err,'vertical_lines':V,'horizontal_lines':H,'warning':'Grid residuals validate fit to this scan only; 1942 datum transformation, digitization, map symbols and landform age are not independently verified.'}
for file,key in [('caucasus-line.json','source'),('east-connected-splice-cut-research.json','alternative'),('east-gap-exploratory-1.json','gap')]:
 pts=json.load(open(file))['coordinates'];out[key]=[inv*to.transform(*p) for p in pts if 47.8<p[0]<47.97 and 41.13<p[1]<41.23]
json.dump(out,open('east-1978-grid-georeference.json','w'),indent=2);print('grid heldout residual m',err);print('grid fit',a)
