"""Assemble approved source-derived interfaces using WGS84 join selection."""
import argparse,hashlib,json
from pathlib import Path
from affine import Affine
import numpy as np
from shapely.geometry import LineString,Point,mapping
from shapely.ops import unary_union,linemerge,substring
from geodesic_line import GEOD,GeodesicLine

def interface(path):
 p=np.load(str(path));labels=p['labels'];aff=Affine(*p['affine'][:6]);h,w=labels.shape;edges=[]
 for dr,dc in ((0,1),(1,0)):
  a=labels[:h-dr,:w-dc];b=labels[dr:,dc:]
  for r,c in np.argwhere(((a==1)&(b==2))|((a==2)&(b==1))):
   u,v=(aff*(int(c)+1,int(r)),aff*(int(c)+1,int(r)+1)) if dc else (aff*(int(c),int(r)+1),aff*(int(c)+1,int(r)+1));edges.append(LineString([u,v]))
 if not edges:raise ValueError('no modeled interface')
 merged=linemerge(unary_union(edges));parts=list(merged.geoms) if hasattr(merged,'geoms') else [merged]
 return sorted(parts,key=lambda g:GeodesicLine(list(g.coords)).length,reverse=True)

def main():
 p=argparse.ArgumentParser();p.add_argument('--baseline',required=True);p.add_argument('--models',required=True);p.add_argument('--recipe',required=True);p.add_argument('--output',required=True);p.add_argument('--report',required=True);a=p.parse_args();recipe=json.loads(Path(a.recipe).read_text());
 if recipe.get('schema')!='caucasus-approved-wgs84-recipe-v2':raise ValueError('bad recipe')
 src=LineString(json.loads(Path(a.baseline).read_text())['coordinates']);ends=(src.coords[0],src.coords[-1]);report=[];outdir=Path(a.output).parent
 for choice in recipe['corrections']:
  name=choice['model'];parts=interface(Path(a.models)/(name+'-labels.npz'));rank=choice['component_rank'];model=parts[rank];hits=src.intersection(model);points=[hits] if hits.geom_type=='Point' else [g for g in getattr(hits,'geoms',[]) if g.geom_type=='Point']
  if len(points)<2:raise ValueError(name+': insufficient exact source intersections')
  selected=[]
  for anchor in (choice['start_anchor'],choice['end_anchor']):
   ranked=sorted([(GEOD.inv(*anchor,p.x,p.y)[2],p) for p in points],key=lambda x:x[0]);
   if ranked[0][0]>1:raise ValueError(name+': approved join displaced more than one meter')
   near=[p for d,p in ranked[1:] if d-ranked[0][0]<=0.02]
   if any(GEOD.inv(ranked[0][1].x,ranked[0][1].y,p.x,p.y)[2]>0.02 for p in near):raise ValueError(name+': ambiguous distinct joins')
   selected.append(ranked[0])
  (d0,p0),(d1,p1)=selected;i,j=src.project(p0),src.project(p1)
  if not i<j:raise ValueError(name+': reversed or duplicate joins')
  pre=substring(src,0,i);post=substring(src,j,src.length);cut=substring(model,model.project(p0),model.project(p1));precoords=list(pre.coords);cc=list(cut.coords);postcoords=list(post.coords)
  precoords[-1]=cc[0]=(p0.x,p0.y);cc[-1]=postcoords[0]=(p1.x,p1.y);combined=LineString(precoords+cc[1:]+postcoords[1:])
  if not cut.is_simple or not combined.is_simple or (combined.coords[0],combined.coords[-1])!=ends:raise ValueError(name+': topology mismatch')
  data=json.dumps(mapping(LineString(cc)),sort_keys=True,separators=(',',':'),allow_nan=False).encode();(outdir/(name+'-wgs84-cut.json')).write_bytes(data);report.append({'model':name,'source_join_displacement_m':[d0,d1],'cut_sha256':hashlib.sha256(data).hexdigest(),'vertices':len(cc),'components':len(parts)});src=combined;(outdir/(name+'-wgs84-full.json')).write_text(json.dumps(mapping(src),sort_keys=True,separators=(',',':')));print(name,'join shift m',round(d0,6),round(d1,6),'vertices',len(cc),flush=True)
 raw=json.dumps(mapping(src),sort_keys=True,separators=(',',':'),allow_nan=False).encode();Path(a.output).write_bytes(raw);result={'geometry_sha256':hashlib.sha256(raw).hexdigest(),'vertices':len(src.coords),'corrections':report};Path(a.report).write_text(json.dumps(result,indent=2)+'\n');print('complete',json.dumps(result),flush=True)
if __name__=='__main__':main()
