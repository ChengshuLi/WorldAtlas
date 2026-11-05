import rasterio,numpy as np
from rasterio.control import GroundControlPoint
from rasterio.transform import from_gcps
from pyproj import Transformer,Geod
with rasterio.open('jvari-k38-053.jpg') as d: im=d.read()[:3].astype('int16')
b=im.max(axis=0)<125;rows=np.arange(1050,1351);cols=np.arange(2150,2461);V=[];H=[]
for e,x in [(8454000,2220),(8456000,2338),(8458000,2457)]:
 best=max((np.mean(b[rows,np.rint(i+k*(rows-1200)).astype(int)]),i,k) for i in np.arange(x-12,x+12,.25) for k in np.arange(-.05,.051,.0025));V.append((e,best[1],best[2],best[0]))
for n,y in [(4710000,1080),(4708000,1199),(4706000,1318)]:
 best=max((np.mean(b[np.rint(i+k*(cols-2320)).astype(int),cols]),i,k) for i in np.arange(y-12,y+12,.25) for k in np.arange(-.05,.051,.0025));H.append((n,best[1],best[2],best[0]))
print('lines',V,H)
controls=[]
for e,x0,sv,_ in V:
 for n,y0,sh,_ in H:
  x=(x0+sv*(y0-1200-sh*2320))/(1-sv*sh);y=y0+sh*(x-2320);controls.append((x,y,e,n))
a=from_gcps([GroundControlPoint(row=y,col=x,x=e,y=n) for x,y,e,n in controls if n!=4708000]);inv=~a;back=Transformer.from_crs(28408,4326,always_xy=True);tr=Transformer.from_crs(4326,28408,always_xy=True);geod=Geod(ellps='WGS84')
for x,y,e,n in controls:
 if n==4708000:print('heldout',geod.inv(*back.transform(e,n),*back.transform(*(a*(x,y))))[2])
for p in [(44.455110995,42.508090947),(44.45332,42.50435),(44.431,42.521)]:print(p,'pixel',inv*tr.transform(*p))
print('affine',a)
# Coordinates are plotted only for visual inspection, not used to change geometry.
import json,xml.etree.ElementTree as ET
root=ET.parse('jvari-osm-map.xml').getroot()
nodes={v.get('id'):(float(v.get('lon')),float(v.get('lat'))) for v in root.findall('node')}
def convert(points):
 return [inv*tr.transform(*xy) for xy in points if 44.40<xy[0]<44.49 and 42.48<xy[1]<42.53]
out={'selected':convert(json.load(open('caucasus-line.json'))['coordinates'])}
for way in root.findall('way'):
 if way.get('id') in ('83809279','97503816'):
  out[way.get('id')]=convert([nodes[v.get('ref')] for v in way.findall('nd')])
json.dump(out,open('jvari-historical-overlay-research.json','w'))
