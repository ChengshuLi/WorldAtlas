#!/usr/bin/env python3
"""Compare named-point component centers with polygons from a pinned land archive.

Diagnostic only; never chooses geographic labels or writes a decision. Paths,
source pins, the point profile, geographic scan bounds and grid are supplied by
an external request. This script imports the separately reviewed archive loader.
"""
import argparse,hashlib,json,math,os,struct,tempfile,types
from pathlib import Path
from osgeo import ogr
ogr.UseExceptions()
def need(ok,msg):
 if not ok:raise ValueError(msg)
def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for block in iter(lambda:f.read(1<<20),b''):h.update(block)
 return h.hexdigest()
def bounded(path,limit):
 with Path(path).open('rb') as f:b=f.read(limit+1)
 need(len(b)<=limit,'input exceeds size limit');return b
def pinned(pin):
 need(isinstance(pin,dict) and set(pin)=={'path','sha256'},'invalid pin');p=Path(pin['path']).resolve(strict=True);need(p.is_file() and sha(p)==pin['sha256'],'input pin mismatch');return p
def run(request):
 reqpath=Path(request).resolve(strict=True);raw=bounded(reqpath,1<<20);q=json.loads(raw);need(q.get('schema')=='point-root-source-containment-request-v1','bad schema');p=pinned(q['point_profile']);profile_bytes=bounded(p,8<<20);need(hashlib.sha256(profile_bytes).hexdigest()==q['point_profile']['sha256'],'profile bytes changed');report=json.loads(profile_bytes);items=report.get('items');need(isinstance(items,list) and items,'empty point profile');
 need(len({x['id'] for x in items})==len(items) and len({x['root_evidence_only'] for x in items})==len(items),'duplicate point or root');grid=q['grid'];width,height=grid['width'],grid['height'];west,north,step=grid['west'],grid['north'],grid['step'];lo,hi=q['scan_rows'];need(type(width) is int and type(height) is int and 1<width<=1000000 and 1<height<=1000000 and type(lo) is int and type(hi) is int and 0<lo<hi<height and all(type(v) in (int,float) and math.isfinite(v) for v in (west,north,step)) and step>0,'invalid grid or scan rows');
 need(report.get('grid')==grid and report.get('component_rows_sha256')==q['component_rows']['sha256'] and report.get('component_runs_sha256')==q['component_runs']['sha256'],'point profile grid or component pin mismatch')
 points=[]
 for x in items:
  xy=x.get('point');need(isinstance(xy,list) and len(xy)==2 and all(type(v) in (int,float) and math.isfinite(v) for v in xy) and -180<=xy[0]<=180 and -90<=xy[1]<=90 and type(x.get('cells')) is int and x['cells']>0,'invalid point or component size');points.append(xy)
 archive=pinned(q['archive']);shapefile=Path(q['materialized_shapefile']).resolve(strict=True);rows=pinned(q['component_rows']);runs=pinned(q['component_runs']);loaderpath=pinned(q['archive_loader']);loader_bytes=bounded(loaderpath,1<<20);need(hashlib.sha256(loader_bytes).hexdigest()==q['archive_loader']['sha256'],'archive loader bytes changed');src=types.ModuleType('pinned_land_archive_loader');exec(compile(loader_bytes,str(loaderpath),'exec'),src.__dict__)
 ds=ogr.Open(str(shapefile),0);need(ds is not None and ds.GetLayerCount()==1,'invalid source layer');layer=ds.GetLayer(0);xs,ys=zip(*points);layer.SetSpatialFilterRect(min(xs)-.001,min(ys)-.001,max(xs)+.001,max(ys)+.001);matches={}
 for feature in layer:
  geom=feature.GetGeometryRef()
  for x in items:
   pt=ogr.Geometry(ogr.wkbPoint);pt.AddPoint_2D(*x['point'])
   if geom.Contains(pt):matches.setdefault(x['id'],[]).append(feature.GetFID())
 need(set(matches)=={x['id'] for x in items} and all(len(v)==1 for v in matches.values()),'each point must match exactly one source polygon')
 ids=sorted({str(v[0]) for v in matches.values()},key=int);geometry_hashes={}
 for id in ids:
  feature=layer.GetFeature(int(id));need(feature is not None,'selected feature missing');g=json.loads(feature.GetGeometryRef().ExportToJson());geometry_hashes[id]=hashlib.sha256(src.canonical(g)).hexdigest()
 layer=None;ds=None;selected=[{'source_feature_id':i,'geometry_sha256':geometry_hashes[i]} for i in ids];extracted=src.extract(archive,shapefile,q['archive']['sha256'],selected,lambda:None);polys={i:ogr.CreateGeometryFromJson(json.dumps(g)) for i,(g,_) in zip(ids,extracted)}
 byroot={x['root_evidence_only']:x for x in items};counts={k:{'inside':0,'outside':0} for k in byroot};data=bounded(rows,(height+1)*4);need(len(data)==(height+1)*4 and hashlib.sha256(data).hexdigest()==q['component_rows']['sha256'],'invalid or changed component row index');offsets=struct.unpack('<%dI'%(height+1),data);need(offsets[0]==0 and runs.stat().st_size==offsets[-1]*12 and all(0<=b-a<=width for a,b in zip(offsets,offsets[1:])),'invalid component offsets')
 with runs.open('rb') as f:
  for y in range(lo,hi):
   f.seek(offsets[y]*12);row=f.read((offsets[y+1]-offsets[y])*12);need(len(row)==(offsets[y+1]-offsets[y])*12,'truncated row')
   for a,b,root in struct.iter_unpack('<III',row):
    if root not in byroot:continue
    need(y not in (lo,hi-1) and 0<=a<b<=width,'root touches scan edge or invalid span');item=byroot[root];polygon=polys[str(matches[item['id']][0])];lat=north-(y+.5)*step
    for x in range(a,b):
     pt=ogr.Geometry(ogr.wkbPoint);pt.AddPoint_2D(west+(x+.5)*step,lat);counts[root]['inside' if polygon.Contains(pt) else 'outside']+=1
 output=[]
 for root,item in byroot.items():
  c=counts[root];need(c['inside']+c['outside']==item['cells'],'component size differs from profile');fid=str(matches[item['id']][0]);output.append({'point_id':item['id'],'point_name':item['name'],'component_id_current_generation_only':root,'cells':item['cells'],'source_feature_id':fid,'geometry_sha256':geometry_hashes[fid],'inside_source_polygon_centers':c['inside'],'outside_source_polygon_centers':c['outside']})
 for key in ('point_profile','archive','component_rows','component_runs','archive_loader'):pinned(q[key])
 need(bounded(reqpath,1<<20)==raw,'request changed');result={'schema':'named-island-land-source-containment-diagnostic-v1','status':'diagnostic-not-a-decision','request_sha256':hashlib.sha256(raw).hexdigest(),'code_sha256':sha(__file__),'source_archive_sha256':q['archive']['sha256'],'point_profile_sha256':q['point_profile']['sha256'],'archive_loader_sha256':q['archive_loader']['sha256'],'results':output,'limitations':['Source FIDs are specific to this exact archive.','Point-to-polygon association corroborates location, not the island name or offshore islet membership.','Common lineage may mean source geometry and component mask are not independent.','No per-cell decision is made.']};out=Path(q['output']).resolve();need(out.parent.is_dir() and not out.exists(),'output exists or parent missing');b=(json.dumps(result,indent=2,sort_keys=True)+'\n').encode();fd,tmp=tempfile.mkstemp(prefix='.containment-',dir=out.parent)
 try:
  with os.fdopen(fd,'wb') as f:f.write(b);f.flush();os.fsync(f.fileno())
  os.link(tmp,out);d=os.open(out.parent,os.O_RDONLY|os.O_DIRECTORY);os.fsync(d);os.close(d)
 finally:os.unlink(tmp)
 print(hashlib.sha256(b).hexdigest())
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('request');args=a.parse_args();run(args.request)
