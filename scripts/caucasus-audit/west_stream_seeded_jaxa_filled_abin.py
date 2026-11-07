"""Private source-seeded western divide experiment; no selection implied."""
import xml.etree.ElementTree as ET
from collections import Counter
import numpy as np,rasterio
from rasterio.windows import Window,transform as window_transform
from rasterio.features import rasterize
from shapely.geometry import LineString,mapping
from seeded_flow_basins import flow_graph,trace_to_seeds
from osm_water_graph import WaterGraph
root=ET.parse('west-habl-combined.osm').getroot();nodes={n.attrib['id']:(float(n.attrib['lon']),float(n.attrib['lat'])) for n in root.findall('node')}
groups={1:{'Афипс','Левый Афипс','Шебш','Широкая Балка','Убин','Большой Хабль','Малый Хабль','Абин','Адегой'},2:{'Левая Щель','Вулан','Пшада','Папай'}};items={1:[],2:[]};ambiguous=0
graph=WaterGraph('west-habl-combined.osm')
for w in root.findall('way'):
 t={x.attrib['k']:x.attrib['v'] for x in w.findall('tag')};ids=[n.attrib['ref'] for n in w.findall('nd')]
 if t.get('waterway') not in ('river','stream') or len(ids)<2 or not all(i in nodes for i in ids):continue
 names=set(graph.downstream_names(ids[-1]));names.add(t.get('name'))
 matched=[group for group,n in groups.items() if names & n]
 if len(matched)==1:items[matched[0]].append((mapping(LineString([nodes[i] for i in ids])),1))
 elif len(matched)>1:ambiguous+=1
print('ambiguous ways',ambiguous,flush=True)
print('ways', {k:len(v) for k,v in items.items()},flush=True)
base='original/N044E038/ALPSMLC30_N044E038_'
with rasterio.open(base+'DSM.tif') as ds,rasterio.open(base+'MSK.tif') as ms,rasterio.open(base+'STK.tif') as st:
 r0,c0=ds.index(38.26,44.80);r1,c1=ds.index(38.70,44.46);win=Window(c0,r0,c1-c0+1,r1-r0+1);aff=window_transform(win,ds.transform);z=ds.read(1,window=win)
 mask=ms.read(1,window=win);stack=st.read(1,window=win);valid=(((mask==0)&(stack>0))|(mask==48))&(z!=ds.nodata)
 a=rasterize(items[1],out_shape=z.shape,transform=aff,all_touched=True).astype(bool);b=rasterize(items[2],out_shape=z.shape,transform=aff,all_touched=True).astype(bool);seed=np.zeros(z.shape,dtype='uint8');seed[a&~b&valid]=1;seed[b&~a&valid]=2
 print('shape',z.shape,'valid',int(valid.sum()),'seeds',int((seed==1).sum()),int((seed==2).sum()),'conflicts',int((a&b).sum()),flush=True)
 filled,graph=flow_graph(z,valid,aff,ds.crs);labels,stats=trace_to_seeds(graph,valid,seed);print('labels',dict(Counter(int(x) for x in labels[valid])),'stats',stats,flush=True)
 h,w=z.shape;edges=[]
 for dr,dc in ((0,1),(1,0)):
  aa=labels[:h-dr,:w-dc];bb=labels[dr:,dc:];hits=((aa==1)&(bb==2))|((aa==2)&(bb==1))
  for r,c in np.argwhere(hits):edges.append((int(r),int(c),dr,dc))
 print('adjacent north-south edges',len(edges),flush=True)
 np.savez_compressed('west-stream-seeded-jaxa-product-filled-abin-output.npz',labels=labels,seeds=seed,affine=np.array(tuple(aff)),boundary=np.array(edges,dtype='int32'))
