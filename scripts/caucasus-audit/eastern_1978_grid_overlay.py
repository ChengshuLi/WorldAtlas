"""Preview registration from manually read SK42 grid intersections, not a survey."""
import json
from rasterio.control import GroundControlPoint
from rasterio.transform import from_gcps
from pyproj import Transformer,Geod
GCP=[(1903,1087,8740000,4566000),(2021,1089,8742000,4566000),(1901,1207,8740000,4564000)]
a=from_gcps([GroundControlPoint(row=y,col=x,x=e,y=n) for x,y,e,n in GCP]);inv=~a;w2=Transformer.from_crs(4326,28408,always_xy=True);tw=Transformer.from_crs(28408,4326,always_xy=True);g=Geod(ellps='WGS84');out={}
for file,name in [('caucasus-line.json','source'),('east-connected-splice-cut-research.json','alternative'),('east-gap-exploratory-1.json','gap')]:
 pts=json.load(open(file))['coordinates'];out[name]=[inv*w2.transform(*p) for p in pts if 47.8<p[0]<47.97 and 41.13<p[1]<41.23]
out['gcps']=GCP;out['warning']='Manually read 2km SK42 grid; EPSG28408->WGS84 transform, unverified datum operation and independent controls; preview only.'
json.dump(out,open('east-1978-grid-overlay-provisional.json','w'));print('affine',a)
