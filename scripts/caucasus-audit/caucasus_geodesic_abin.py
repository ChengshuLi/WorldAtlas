"""Rebuild the approved Abin divide from pinned OSM and JAXA sources."""
import argparse,hashlib,json,xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
import numpy as np,rasterio
from rasterio.windows import Window,transform as window_transform
from rasterio.features import rasterize
from shapely.geometry import LineString,Point,mapping
from shapely.ops import unary_union,linemerge,substring
from seeded_flow_basins import flow_graph,trace_to_seeds
from osm_water_graph import WaterGraph
from geodesic_line import GEOD,GeodesicLine

def main():
 p=argparse.ArgumentParser()
 for n in ('recipe','osm','tile-dir','baseline','anapa','output','report'):p.add_argument('--'+n,required=True)
 a=p.parse_args();recipe=json.loads(Path(a.recipe).read_text());decision=recipe['abin'];root=ET.parse(a.osm).getroot();nodes={n.get('id'):(float(n.get('lon')),float(n.get('lat'))) for n in root.findall('node')};names={int(k):set(v) for k,v in decision['seed_names'].items()};items={1:[],2:[]};graph=WaterGraph(a.osm)
 for w in root.findall('way'):
  tags={x.get('k'):x.get('v') for x in w.findall('tag')};ids=[n.get('ref') for n in w.findall('nd')]
  if tags.get('waterway') not in ('river','stream') or len(ids)<2 or not all(i in nodes for i in ids):continue
  found=set(graph.downstream_names(ids[-1]));found.add(tags.get('name'));matched=[k for k,v in names.items() if found & v]
  if len(matched)==1:items[matched[0]].append((mapping(LineString([nodes[i] for i in ids])),1))
 base=Path(a.tile_dir)/'N044E038'/'ALPSMLC30_N044E038_';paths=[str(base)+x+'.tif' for x in ('DSM','MSK','STK')]
 with rasterio.open(paths[0]) as ds,rasterio.open(paths[1]) as ms,rasterio.open(paths[2]) as st:
  x0,y0,x1,y1=decision['bounds'];r0,c0=ds.index(x0,y1);r1,c1=ds.index(x1,y0);win=Window(c0,r0,c1-c0+1,r1-r0+1);aff=window_transform(win,ds.transform);z=ds.read(1,window=win);mask=ms.read(1,window=win);stack=st.read(1,window=win);valid=(((mask==0)&(stack>0))|(mask==48))&(z!=ds.nodata)
  ar=rasterize(items[1],out_shape=z.shape,transform=aff,all_touched=True).astype(bool);br=rasterize(items[2],out_shape=z.shape,transform=aff,all_touched=True).astype(bool);seed=np.zeros(z.shape,dtype='uint8');seed[ar&~br&valid]=1;seed[br&~ar&valid]=2;_,flow=flow_graph(z,valid,aff,ds.crs);labels,stats=trace_to_seeds(flow,valid,seed)
  h,w=z.shape;edges=[]
  for dr,dc in ((0,1),(1,0)):
   aa=labels[:h-dr,:w-dc];bb=labels[dr:,dc:]
   for r,c in np.argwhere(((aa==1)&(bb==2))|((aa==2)&(bb==1))):
    u,v=(aff*(int(c)+1,int(r)),aff*(int(c)+1,int(r)+1)) if dc else (aff*(int(c),int(r)+1),aff*(int(c)+1,int(r)+1));edges.append(LineString([u,v]))
 merged=linemerge(unary_union(edges));parts=list(merged.geoms) if hasattr(merged,'geoms') else [merged];parts.sort(key=lambda g:GeodesicLine(list(g.coords)).length,reverse=True);interface=parts[decision['interface_rank']];baseline=LineString(json.loads(Path(a.baseline).read_text())['geometry']['coordinates']);cross=baseline.intersection(interface);points=[x for x in getattr(cross,'geoms',[cross]) if x.geom_type=='Point'];chosen=[]
 for anchor in decision['prior_anchors']:
  ranked=sorted([(GEOD.inv(*anchor,x.x,x.y)[2],x) for x in points],key=lambda v:v[0]);
  if not ranked or ranked[0][0]>200:raise ValueError('Abin join not found near approved anchor')
  near=[x for d,x in ranked[1:] if d-ranked[0][0]<=0.02]
  if any(GEOD.inv(ranked[0][1].x,ranked[0][1].y,x.x,x.y)[2]>0.02 for x in near):raise ValueError('ambiguous Abin joins')
  chosen.append(ranked[0][1])
 start,end=chosen;cut=substring(interface,interface.project(start),interface.project(end));src=LineString(json.loads(Path(a.anapa).read_text())['coordinates']);gsrc=GeodesicLine(list(src.coords));d0=gsrc.closest((start.x,start.y))['distance_m'];d1=gsrc.closest((end.x,end.y))['distance_m']
 if max(d0,d1)>0.02:raise ValueError('Abin joins not on Anapa source')
 i,j=src.project(start),src.project(end)
 if not i<j:raise ValueError('Abin join order')
 pre=substring(src,0,i);post=substring(src,j,src.length);line=LineString(list(pre.coords)+list(cut.coords)[1:]+list(post.coords)[1:])
 if not line.is_simple or line.coords[0]!=src.coords[0] or line.coords[-1]!=src.coords[-1]:raise ValueError('Abin topology')
 raw=json.dumps(mapping(line),sort_keys=True,separators=(',',':'),allow_nan=False).encode();Path(a.output).write_bytes(raw);info={'geometry_sha256':hashlib.sha256(raw).hexdigest(),'vertices':len(line.coords),'join_distance_m':[d0,d1],'seed_counts':[int((seed==k).sum()) for k in (1,2)],'flow_stats':stats,'label_counts':{str(k):int((labels==k).sum()) for k in (1,2,3)}};Path(a.report).write_text(json.dumps(info,indent=2)+'\n');print(json.dumps(info),flush=True)
if __name__=='__main__':main()
