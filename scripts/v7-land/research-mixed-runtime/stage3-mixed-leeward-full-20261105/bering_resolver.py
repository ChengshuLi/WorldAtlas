"""Research prototype: freshly resolve a two-source Aleutian group.

Caller must pre-verify this module and the supplied reviewed profiler, extractor,
and component-reader code; authenticate the selected snapshot, complete stream
lineage and protected witness/claim inputs; enforce an external process-group
RSS/host/disk/time watchdog. No saved root IDs, reference labels or V7 inputs.
"""
import hashlib,json,math,struct,zipfile
from pathlib import Path
from fractions import Fraction
REVIEWED_OPERATION_MANIFEST_SHA="141760e4b2a0b4a3b8006bcaf02758c726ca6def498c745cb728e9d18f93da65"
from osgeo import ogr,osr,gdal
import pyproj
from pyproj.enums import TransformDirection

def need(ok,msg):
 if not ok:raise ValueError(msg)
def pinned(spec,guard):
 need(isinstance(spec,dict) and set(spec)=={'path','sha256','size_bytes'} and type(spec['size_bytes']) is int and spec['size_bytes']>=0,'invalid pin');p=Path(spec['path']).resolve(strict=True);need(p.is_file() and p.stat().st_size==spec['size_bytes'],'input size mismatch');h=hashlib.sha256();n=0
 with p.open('rb') as f:
  while True:
   guard();b=f.read(1<<20)
   if not b:break
   n+=len(b);need(n<=spec['size_bytes'],'input grew while hashing');h.update(b)
 need(n==spec['size_bytes'] and h.hexdigest()==spec['sha256'],'input hash mismatch');return p
def bounded_read(path,spec,limit):
 need(spec['size_bytes']<=limit,'input too large')
 with Path(path).open('rb') as f:b=f.read(spec['size_bytes']+1)
 need(len(b)==spec['size_bytes'] and hashlib.sha256(b).hexdigest()==spec['sha256'],'bounded input mismatch');return b

def resolve(decision,inputs,grid,protected,existing_claims,guard,profiler,extractor,reader):
 need(isinstance(decision,dict) and decision.get('method')=='label_contained_ecoregion_contact_v1' and callable(guard) and callable(profiler) and callable(extractor) and hasattr(reader,'readrow') and hasattr(reader,'equal_coverage'),'invalid resolver contract')
 need(isinstance(inputs,dict) and set(inputs)=={'label','ecoregion','physical_rows','physical_runs','component_rows','component_runs'},'invalid input set');paths={k:pinned(v,guard) for k,v in inputs.items()};label=decision['label'];epa=decision['ecoregion'];sel=decision['selector'];decision_bytes=json.dumps(decision,sort_keys=True,separators=(',',':'),allow_nan=False).encode();manifest={'operations':sel['operations'],'operation_preference':sel['operation_preference'],'pyproj_version':sel['pyproj_version'],'proj_version':sel['proj_version']};digest=hashlib.sha256(json.dumps(manifest,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest();need(digest==sel['operation_manifest_sha256']==REVIEWED_OPERATION_MANIFEST_SHA,'operation manifest mismatch');need(sel['partial_root_behavior']=='exclude' and sel['protected_root_behavior']=='exclude' and sel['untested_or_boundary_behavior']=='exclude' and sel['contact_rule']=='at_least_one_strictly_inside_center','unsupported selection policy')
 for k,source in (('label',label['source']),('ecoregion',epa['source'])):need(inputs[k]['sha256']==source['sha256'] and inputs[k]['size_bytes']==source['size_bytes'],'selected source mismatch')
 need(pyproj.__version__==sel['pyproj_version'] and pyproj.proj_version_str==sel['proj_version'],'PROJ version mismatch');need(isinstance(protected,set) and all(type(x) is int and 0<=x<0xffffffff for x in protected) and isinstance(existing_claims,dict) and all(type(k) is int and 0<=k<0xffffffff for k in existing_claims),'invalid protected/claims')
 w=grid.get('width');h=grid.get('height');step=grid.get('step');west=grid.get('west');north=grid.get('north');need(type(w) is int and 1<w<=1000000 and type(h) is int and 0<h<=1000000 and type(step) in (int,float) and math.isfinite(step) and step>0 and west==-180 and north==90 and Fraction(step)==Fraction(360,w) and h*step<=180,'invalid grid')
 f=label['feature'];ev=f['evidence'];feature={'id_property':ev['selector_property'],'source_feature_id':f['source_feature_id'],'geometry_sha256':f['geometry_sha256']};geometry,trace=extractor(paths['label'],inputs['label']['sha256'],feature)
 doc=json.loads(bounded_read(paths['label'],inputs['label'],16<<20));matches=[v for v in doc['features'] if str(v['properties'].get(feature['id_property']))==feature['source_feature_id']];need(len(matches)==1 and all(matches[0]['properties'].get(k)==v for k,v in sel['label_expected_properties'].items()),'label identity mismatch');del doc,matches
 whole=ogr.CreateGeometryFromJson(json.dumps(geometry,allow_nan=False));need(whole is not None and not whole.IsEmpty() and whole.IsValid(),'invalid whole label geometry');parts=([geometry] if geometry['type']=='Polygon' else [{'type':'Polygon','coordinates':p} for p in geometry['coordinates']]);need(1<=len(parts)<=128,'invalid label parts');combined={}
 for part in parts:
  guard();report=profiler(part,grid,*(str(paths[k]) for k in ('physical_rows','physical_runs','component_rows','component_runs')),guard);need(isinstance(report,dict) and isinstance(report.get('rows'),list) and len(report['rows'])<=100000,'invalid profile rows');seen=set()
  for row in report['rows']:
   root=row.get('component_id_current_generation_only');inside=row.get('inside_polygon_cells');outside=row.get('outside_polygon_cells');total=row.get('total_land_cells');need(type(root) is int and 0<=root<0xffffffff and root not in seen and all(type(v) is int for v in (inside,outside,total)) and inside>0 and outside>=0 and inside+outside==total,'bad part profile');seen.add(root)
   if root not in combined:combined[root]={'total':total,'inside':inside};need(len(combined)<=100000,'root limit exceeded')
   else:need(combined[root]['total']==total,'part population mismatch');combined[root]['inside']+=inside;need(combined[root]['inside']<=total,'overlapping part counts')
 partial=sorted(k for k,v in combined.items() if v['inside']!=v['total']);protected_hits=sorted(set(combined)&protected);roots={k:v for k,v in combined.items() if v['inside']==v['total'] and k not in protected};need(roots,'no eligible roots');need(sum(v['total'] for v in roots.values())<=10000000,'aggregate root cell limit exceeded')
 contract=epa['contract'];
 with zipfile.ZipFile(paths['ecoregion']) as z:
  items=z.infolist();names=[i.filename for i in items];need(len(names)<=32 and len(set(names))==len(names) and all('/' not in n and '\\' not in n and n not in ('.','..') for n in names) and sum(i.file_size for i in items)<=8<<20 and all(contract['layer']+'.'+ext in names for ext in ('shp','shx','dbf','prj')) and z.testzip() is None,'unsafe or incomplete ecoregion ZIP')
 ogr.UseExceptions();gdal.UseExceptions();ds=ogr.Open('/vsizip/'+str(paths['ecoregion']),0);need(ds is not None,'cannot open ecoregion');layer=ds.GetLayerByName(contract['layer']);need(layer is not None,'missing ecoregion layer');srs=layer.GetSpatialRef();expected=osr.SpatialReference();expected.ImportFromEPSG(3338);need(srs is not None and bool(srs.IsSame(expected)),'ecoregion CRS mismatch');geoms=[];fids=set()
 for feature in layer:
  guard()
  if feature.GetField(contract['selector_property'])!=contract['selector_value']:continue
  need(feature.GetField(contract['name_property'])==contract['name_value'],'ecoregion name mismatch');g=feature.GetGeometryRef();fid=feature.GetFID();need(fid not in fids and g is not None and g.GetGeometryName() in ('POLYGON','MULTIPOLYGON') and not g.IsEmpty() and g.IsValid(),'bad ecoregion geometry');fids.add(fid);geoms.append((g.Clone(),g.GetEnvelope()));need(len(geoms)<=contract['expected_feature_count'],'excess ecoregion features')
 need(len(geoms)==contract['expected_feature_count'],'ecoregion feature count mismatch');ops=sel['operations'];byid={o['id']:(o,pyproj.Transformer.from_pipeline(o['pipeline'])) for o in ops};need(isinstance(sel['operation_preference'],list) and len(sel['operation_preference'])==2 and set(byid)==set(sel['operation_preference']) and len(byid)==len(ops)==2,'invalid operation selection');states={k:{'root':k,'cells':0,'label_inside':v['inside'],'inside':0,'outside':0,'boundary':0,'untested':0} for k,v in roots.items()}
 def within(lon,lat,a):return a['south']<=lat<=a['north'] and (a['west']<=lon<=a['east'] if a['west']<=a['east'] else lon>=a['west'] or lon<=a['east'])
 with open(paths['physical_rows'],'rb') as pr,open(paths['physical_runs'],'rb') as pv,open(paths['component_rows'],'rb') as cr,open(paths['component_runs'],'rb') as cv:
  for y in range(h):
   if y%32==0:guard()
   ps=reader.readrow(pr,pv,y,w,'physical');cs=reader.readrow(cr,cv,y,w,'component');reader.equal_coverage(ps,cs,w)
   for i,(a,b,root) in enumerate(cs):
    if i%1024==0:guard()
    if root not in states:continue
    v=states[root]
    for col in range(a,b):
     if col%1024==0:guard()
     v['cells']+=1;lon=west+(col+.5)*step;lat=north-(y+.5)*step;chosen=next((byid[k] for k in sel['operation_preference'] if within(lon,lat,byid[k][0]['area_bounds'])),None)
     if chosen is None:v['untested']+=1;continue
     x,z=chosen[1].transform(lon,lat,direction=TransformDirection.INVERSE,errcheck=True);need(math.isfinite(x) and math.isfinite(z),'nonfinite transform');pt=ogr.Geometry(ogr.wkbPoint);pt.AddPoint_2D(x,z);inside=False;touch=False
     for g,(xmin,xmax,ymin,ymax) in geoms:
      if xmin<=x<=xmax and ymin<=z<=ymax:
       if g.Contains(pt):inside=True;break
       if g.Touches(pt):touch=True
     v['inside' if inside else 'boundary' if touch else 'outside']+=1
 claims=[];excluded=[]
 for root,v in sorted(states.items()):
  need(v['cells']==roots[root]['total'] and v['inside']+v['outside']+v['boundary']+v['untested']==v['cells'],'root count mismatch');eligible=v['inside']>0 and v['boundary']==0 and v['untested']==0
  if eligible:
   target=decision['entity_id'];prior=existing_claims.get(root);need(prior is None or prior==target,'conflicting existing claim');claims.append({'component_id':root,'entity_id':target,'affiliation_id':decision['affiliation_id'],'same_target_overlap':prior==target})
  else:excluded.append(root)
 for k,spec in inputs.items():pinned(spec,guard)
 need(json.dumps(decision,sort_keys=True,separators=(',',':'),allow_nan=False).encode()==decision_bytes,'decision changed')
 return {'schema':'stage3-label-ecoregion-resolution-v1','status':'research-only','claims':claims,'root_counts':[states[k] for k in sorted(states)],'partial_label_roots_excluded':partial,'protected_roots_excluded':protected_hits,'no_contact_or_ambiguous_roots_excluded':excluded,'label_trace':trace,'ecoregion_feature_ids':sorted(fids),'operation_manifest_sha256':sel['operation_manifest_sha256'],'source_sha256':{k:inputs[k]['sha256'] for k in ('label','ecoregion')},'input_sha256':{k:inputs[k]['sha256'] for k in ('physical_rows','physical_runs','component_rows','component_runs')},'runtime':{'gdal':gdal.VersionInfo('--version'),'pyproj':pyproj.__version__,'proj':pyproj.proj_version_str},'limitations':['NE center coverage and coarse EPA contact do not prove whole-root island identity.','Operation bounding boxes screen candidates but do not prove exact area applicability; nominal accuracy is not a strict bound.','Current-generation roots are runtime evidence, never portable selectors.']}
