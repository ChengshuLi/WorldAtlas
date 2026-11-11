"""Regenerate approved Caucasus drainage labels from verified R2-readback inputs.

The input directory is produced by caucasus_geodesic_prepare.py. Model labels
are research routing outputs, not independently validated watersheds.
"""
import argparse,json,xml.etree.ElementTree as ET
from collections import defaultdict,deque
from pathlib import Path
import numpy as np,rasterio
from rasterio.features import rasterize
from rasterio.merge import merge
from rasterio.windows import from_bounds,transform
from shapely.geometry import LineString,mapping
from seeded_flow_basins import flow_graph,trace_to_seeds

MODELS={}

def ancestors(ids,reverse):
 seen=set(ids);todo=deque(ids)
 while todo:
  for v in reverse[todo.popleft()]:
   if v not in seen:seen.add(v);todo.append(v)
 return seen

def model(root,name):
 c=MODELS[name];doc=ET.parse(str(root/c['osm'])).getroot();nodes={n.get('id'):(float(n.get('lon')),float(n.get('lat'))) for n in doc.findall('node')};ways={};reverse=defaultdict(set)
 for w in doc.findall('way'):
  tags={x.get('k'):x.get('v') for x in w.findall('tag')};ids=[x.get('ref') for x in w.findall('nd')]
  if tags.get('waterway') not in ('river','stream') or len(ids)<2 or any(i not in nodes for i in ids):continue
  ways[w.get('id')]=ids
  for a,b in zip(ids,ids[1:]):reverse[b].add(a)
 reach=[]
 for group in c['groups']:
  v=set()
  for wid in group:v.update(ancestors(ways[wid],reverse))
  reach.append(v)
 shapes=[[],[]]
 for ids in ways.values():
  matches=[i for i,r in enumerate(reach) if ids[-1] in r]
  if len(matches)==1:shapes[matches[0]].append((mapping(LineString([nodes[i] for i in ids])),1))
 rasters=[]
 for kind,nodata in [('DSM',-9999),('MSK',255)]:
  paths=[root/'original'/t/('ALPSMLC30_'+t+'_'+kind+'.tif') for t in c['tiles']]
  ds=[rasterio.open(str(x)) for x in paths]
  try:
   if len(ds)>1:
    arr,aff=merge(ds,bounds=tuple(c['bounds']),nodata=nodata);data=arr[0];crs=ds[0].crs;nodata_value=nodata
   else:
    win=from_bounds(*c['bounds'],transform=ds[0].transform).round_offsets().round_lengths();aff=transform(win,ds[0].transform);data=ds[0].read(1,window=win);crs=ds[0].crs;nodata_value=ds[0].nodata
   rasters.append((data,aff,crs,nodata_value))
  finally:
   for d in ds:d.close()
 z,aff,crs,nodata=rasters[0];mask,maff,mcrs,_=rasters[1]
 if aff!=maff or crs!=mcrs or z.shape!=mask.shape:raise ValueError('unaligned terrain')
 valid=np.isfinite(z)&(z!=nodata)&np.isin(mask,c['masks']);m=[rasterize(v,out_shape=z.shape,transform=aff,all_touched=True).astype(bool) for v in shapes];seed=np.zeros(z.shape,dtype='uint8');seed[m[0]&~m[1]&valid]=1;seed[m[1]&~m[0]&valid]=2
 print(name,'shape',z.shape,'ways',list(map(len,shapes)),'seed counts',[int((seed==i).sum()) for i in (1,2)],flush=True)
 _,graph=flow_graph(z,valid,aff,crs);labels,stats=trace_to_seeds(graph,valid,seed);out=root/(name+'-labels.npz');np.savez_compressed(str(out),labels=labels,seeds=seed,affine=np.array(tuple(aff)));print(name,'done',stats,flush=True)

def main():
 p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--recipe',required=True);p.add_argument('--models',nargs='*');a=p.parse_args();root=Path(a.input).resolve();recipe=json.loads(Path(a.recipe).read_text());MODELS.update(recipe['models'])
 for name in (a.models or list(MODELS)):
  if name not in MODELS:raise ValueError('unknown model '+name)
  model(root,name)
if __name__=='__main__':main()
