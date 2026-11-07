import rasterio,numpy as np
from rasterio.control import GroundControlPoint
from rasterio.transform import from_gcps
from pyproj import Transformer,Geod
with rasterio.open('klukhor-k37-036.jpg') as d:im=d.read()[:3].astype('int16')
b=im.max(axis=0)<140;rows=np.arange(570,900);cols=np.arange(1750,2070);V=[];H=[]
for e,x in [(7732000,1800),(7734000,1920),(7736000,2040)]:
 best=max((np.mean(b[rows,np.rint(i+k*(rows-730)).astype(int)]),i,k) for i in np.arange(x-12,x+12,.25) for k in np.arange(-.06,.061,.0025));V.append((e,best[1],best[2],best[0]))
for n,y in [(4796000,608),(4794000,730),(4792000,850)]:
 best=max((np.mean(b[np.rint(i+k*(cols-1920)).astype(int),cols]),i,k) for i in np.arange(y-12,y+12,.25) for k in np.arange(-.06,.061,.0025));H.append((n,best[1],best[2],best[0]))
print('lines',V,H)
controls=[]
for e,x0,sv,_ in V:
 for n,y0,sh,_ in H:
  x=(x0+sv*(y0-730-sh*1920))/(1-sv*sh);y=y0+sh*(x-1920);controls.append((x,y,e,n))
a=from_gcps([GroundControlPoint(row=y,col=x,x=e,y=n) for x,y,e,n in controls if n!=4794000]);inv=~a;back=Transformer.from_crs(28407,4326,always_xy=True);tr=Transformer.from_crs(4326,28407,always_xy=True);geod=Geod(ellps='WGS84')
for x,y,e,n in controls:
 if n==4794000:print('heldout',geod.inv(*back.transform(e,n),*back.transform(*(a*(x,y))))[2])
for p in [(41.86776667,43.24428333),(41.86458768,43.24570022)]:print(p,'pixel',inv*tr.transform(*p))
print('affine',a)
