"""Trace JAXA modeled runoff on both sides of the unclassified connector."""
import json,math
import numpy as np,rasterio
from affine import Affine
from rasterio.windows import Window
from pyproj import Geod
from seeded_flow_basins import flow_graph
from geodesic_line import GeodesicLine
D=np.load('klukhor-jaxa-product-broad-downstream-research.npz');labels=D['labels'];seeds=D['seeds'];aff=Affine(*D['affine'][:6]);inv=~aff;h,w=labels.shape;base='original/N043E041/ALPSMLC30_N043E041_'
with rasterio.open(base+'DSM.tif') as ds,rasterio.open(base+'MSK.tif') as ms,rasterio.open(base+'STK.tif') as st:
 x,y=aff*(0,0);r,c=ds.index(x+ds.transform.a/2,y+ds.transform.e/2);window=Window(c,r,w,h);z=ds.read(1,window=window);m=ms.read(1,window=window);stk=st.read(1,window=window);valid=(((m==0)&(stk>0))|(m==48))&(z!=ds.nodata);_,graph=flow_graph(z,valid,aff,ds.crs)
line=GeodesicLine(json.load(open('klukhor-north-gap-0-research.json'))['coordinates']);G=Geod(ellps='WGS84')
for station in (50,100,150,200,250,300):
 p=line.point(station);az=G.inv(*line.point(station-40),*line.point(station+40))[0]
 for offset in (-200,-100,100,200):
  xy=G.fwd(*p,az+90,offset)[:2];col,row=inv*xy;row,col=math.floor(row),math.floor(col);start=(row,col);seen=set();cur=row*w+col;steps=0;status=''
  while 0<=cur<h*w and cur not in seen:
   seen.add(cur);r,c=divmod(cur,w)
   if seeds[r,c]:status='seed '+str(seeds[r,c]);break
   nxt=int(graph[r,c]);steps+=1
   if nxt<0:status='edge';break
   cur=nxt
  if not status:status='cycle or invalid'
  lon,lat=aff*(c+.5,r+.5);print(json.dumps({'station_m':station,'offset_m':offset,'start_label':int(labels[start]),'status':status,'steps':steps,'outlet':[round(lon,6),round(lat,6)]}))
