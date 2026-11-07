"""Explore short JAXA ridge connectors; outputs are unselected hypotheses."""
import json,math
import numpy as np,rasterio
from affine import Affine
from rasterio.windows import Window
from rasterio.transform import rowcol,xy
from scipy.ndimage import uniform_filter
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra
from shapely.geometry import shape,LineString,mapping
from pyproj import Geod
from geodesic_line import GeodesicLine
D=np.load('klukhor-jaxa-product-broad-downstream-research.npz');labels=D['labels'];seeds=D['seeds'];aff=Affine(*D['affine'][:6]);source=GeodesicLine(json.load(open('caucasus-anapa-abin-combined-candidate.json'))['coordinates']);interface=shape(json.load(open('klukhor-jaxa-interface-research.json'))['features'][0]['geometry']);start=interface.coords[0];end=source.closest(start)['point'];ra,ca=rowcol(aff,*start);rb,cb=rowcol(aff,*end);pad=35;r0=max(0,min(ra,rb)-pad);r1=min(labels.shape[0],max(ra,rb)+pad+1);c0=max(0,min(ca,cb)-pad);c1=min(labels.shape[1],max(ca,cb)+pad+1);A=aff*Affine.translation(c0,r0);L=labels[r0:r1,c0:c1];S=seeds[r0:r1,c0:c1];h,w=L.shape
base='original/N043E041/ALPSMLC30_N043E041_'
with rasterio.open(base+'DSM.tif') as ds,rasterio.open(base+'MSK.tif') as ms,rasterio.open(base+'STK.tif') as st:
 x,y=A*(0,0);rr,cc=ds.index(x+ds.transform.a/2,y+ds.transform.e/2);window=Window(cc,rr,w,h);z=ds.read(1,window=window).astype(float);m=ms.read(1,window=window);stack=st.read(1,window=window);valid=((m==0)&(stack>0)|(m==48))&(z!=ds.nodata)&(S==0)
tpi=z-uniform_filter(z,size=9,mode='nearest');idx=np.arange(h*w).reshape(h,w);rows=[];cols=[];lengths=[];pen=[];r,c=np.indices((h,w));lon=A.c+(c+.5)*A.a;lat=A.f+(r+.5)*A.e;G=Geod(ellps='WGS84')
for dr in (-1,0,1):
 for dc in (-1,0,1):
  if not(dr or dc):continue
  a=(slice(max(0,-dr),min(h,h-dr)),slice(max(0,-dc),min(w,w-dc)));b=(slice(max(0,dr),min(h,h+dr)),slice(max(0,dc),min(w,w+dc)))
  ok=valid[a]&valid[b];rows.append(idx[a][ok]);cols.append(idx[b][ok]);lengths.append(G.inv(lon[a][ok],lat[a][ok],lon[b][ok],lat[b][ok])[2]);pen.append(np.minimum(5,np.maximum(0,-tpi[b][ok])/5))
rows=np.concatenate(rows);cols=np.concatenate(cols);lengths=np.concatenate(lengths);pen=np.concatenate(pen);src=(ra-r0)*w+(ca-c0);dst=(rb-r0)*w+(cb-c0);print('gap m',round(G.inv(*start,*end)[2]),'source_label',int(L[ra-r0,ca-c0]),'destination_label',int(L[rb-r0,cb-c0]),'valid',bool(valid[ra-r0,ca-c0]),bool(valid[rb-r0,cb-c0]))
for weight in (0,1,4):
 graph=coo_matrix((lengths*(1+weight*pen),(rows,cols)),shape=(h*w,h*w)).tocsr();dist,prev=dijkstra(graph,indices=src,directed=True,return_predecessors=True)
 if not np.isfinite(dist[dst]):print('weight',weight,'no path');continue
 path=[dst]
 while path[-1]!=src:path.append(int(prev[path[-1]]))
 path.reverse();coords=[tuple(start)]+[xy(A,t//w,t%w) for t in path]+[tuple(end)];g=LineString(coords);print('weight',weight,'path_m',round(GeodesicLine(coords).length),'simple',g.is_simple,'labels',dict(zip(*[list(map(int,v)) for v in np.unique([L[t//w,t%w] for t in path],return_counts=True)])));json.dump(mapping(g),open('klukhor-north-gap-%d-research.json'%weight,'w'))
