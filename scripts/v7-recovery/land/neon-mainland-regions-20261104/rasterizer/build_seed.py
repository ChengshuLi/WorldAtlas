#!/usr/bin/env /usr/bin/python3
"""Config-driven center-rasterized mainland seed, research only, no historical labels."""
import hashlib,json,math,os,shutil,sys,threading,time,types
from collections import deque
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from pathlib import Path
from osgeo import gdal,ogr,osr

gdal.UseExceptions();ogr.UseExceptions()
HERE=Path(__file__).resolve().parent

def witness_boundary_ambiguous(geom, lon, lat):
 """Reject an axis-aligned numeric uncertainty box touching the boundary.

 This is a coordinate precision guard, not a geographic-distance measure.
 The square contains the former coordinate-space epsilon disk, so it never
 weakens the previous near-boundary rejection (and can reject extra corners).
 """
 if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in (lon,lat)):raise ValueError('invalid witness coordinates')
 epsilon=1e-12
 left=math.nextafter(lon-epsilon,-math.inf);right=math.nextafter(lon+epsilon,math.inf)
 bottom=math.nextafter(lat-epsilon,-math.inf);top=math.nextafter(lat+epsilon,math.inf)
 ring=ogr.Geometry(ogr.wkbLinearRing)
 for x,y in ((left,bottom),(right,bottom),(right,top),(left,top),(left,bottom)):
  ring.AddPoint_2D(x,y)
 box=ogr.Geometry(ogr.wkbPolygon);box.AddGeometry(ring)
 return bool(geom.Boundary().Intersects(box))

def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def pinned(x):
 if set(x)!={'path','sha256'}:raise ValueError('pin needs path and sha256')
 p=Path(x['path']).resolve(strict=True)
 if not p.is_file() or sha(p)!=x['sha256']:raise ValueError('input pin mismatch: '+str(p))
 return p
def build(config,output):
 start=time.time();program_hashes={name:sha(HERE/name) for name in ('build_seed.py','seed_runtime.py')};config=Path(config).resolve(strict=True);raw=config.read_bytes();c=json.loads(raw);out=Path(output).absolute();out=out.parent.resolve()/out.name
 required={'schema','grid','component_rows','component_runs','regions','rules','evidence','strip_rows'}
 if not required<=set(c) or set(c)-required-{'reserve_bytes','workers'} or c['schema']!='direct-region-seed-research-v1':raise ValueError('invalid config')
 if sys.byteorder!='little':raise ValueError('little-endian host required')
 reserve=c.get('reserve_bytes',2*1024**3)
 if type(reserve) is not int or reserve<0:raise ValueError('invalid reserve')
 def check_space():
  if shutil.disk_usage(out.parent).free<reserve:raise ValueError('insufficient free space for reserve')
 check_space()
 g=c['grid'];
 if set(g)!={'width','height','west','north','step','crs'} or g['crs']!='EPSG:4326' or any(type(g[k]) is not int or not 0<g[k]<=0xffffffff for k in ('width','height')) or any(type(g[k]) not in (int,float) or not math.isfinite(g[k]) for k in ('west','north','step')) or g['step']<=0:raise ValueError('invalid grid')
 if g['west'] < -180 or g['west']+g['width']*g['step'] > 180+1e-9 or g['north']>90 or g['north']-g['height']*g['step'] < -90-1e-9:raise ValueError('grid outside WGS84 bounds')
 if type(c['strip_rows']) is not int or not 1<=c['strip_rows']<=1024:raise ValueError('invalid strip rows')
 if not isinstance(c['regions'],list) or len(c['regions'])>8 or not isinstance(c['rules'],list) or not c['rules'] or not isinstance(c['evidence'],list):raise ValueError('invalid arrays')
 pins=[c['component_rows'],c['component_runs']]+[r['geometry'] for r in c['regions']]+c['evidence']; paths=[pinned(p) for p in pins]
 if os.path.lexists(out):raise ValueError('output exists')
 for p in [config]+paths+[HERE/'build_seed.py',HERE/'seed_runtime.py']:
  parent=p.parent.resolve()
  if out==parent or out in parent.parents or parent in out.parents:raise ValueError('output/input directories overlap')
 regionids={};datasets=[];layers=[]
 for i,region in enumerate(c['regions']):
  if set(region)!={'id','geometry','witnesses'} or not isinstance(region['id'],str) or not region['id'] or region['id'] in regionids or not isinstance(region['witnesses'],list):raise ValueError('invalid region')
  ds=ogr.Open(str(paths[2+i]));
  if ds is None or ds.GetLayerCount()!=1:raise ValueError('geometry must have exactly one layer')
  layer=ds.GetLayer(0)
  actual=layer.GetSpatialRef();expected=osr.SpatialReference();expected.ImportFromEPSG(4326)
  if actual is None:raise ValueError('polygon CRS missing; WGS84 required')
  actual=actual.Clone();actual.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER);expected.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
  if not actual.IsSame(expected):raise ValueError('polygon CRS must be WGS84')
  if layer.GetFeatureCount()!=1:raise ValueError('geometry must have exactly one feature')
  layer.ResetReading();f=layer.GetNextFeature();geom=f.GetGeometryRef()
  if geom is None or ogr.GT_Flatten(geom.GetGeometryType()) not in (ogr.wkbPolygon,ogr.wkbMultiPolygon) or not geom.IsValid():raise ValueError('invalid polygon')
  for witness in region['witnesses']:
   if set(witness)!={'lon','lat','inside'} or type(witness['inside']) is not bool:raise ValueError('invalid witness')
   p=ogr.Geometry(ogr.wkbPoint);p.AddPoint_2D(witness['lon'],witness['lat'])
   if witness_boundary_ambiguous(geom,witness['lon'],witness['lat']) or bool(geom.Contains(p))!=witness['inside']:raise ValueError('witness fails')
  regionids[region['id']]=1<<i;datasets.append(ds);layers.append(layer)
 seen=set();rules=[]
 for rule in c['rules']:
  if set(rule)!={'component_id','region_id','inside_code','outside_code'}:raise ValueError('invalid rule keys')
  root,region,inside,outside=rule['component_id'],rule['region_id'],rule['inside_code'],rule['outside_code']
  if type(root) is not int or root<0 or root>0xffffffff or root in seen or type(inside) is not int or type(outside) is not int or not 17<=inside<=22 or not 17<=outside<=22:raise ValueError('invalid root/code')
  if region is None:
   if inside!=outside:raise ValueError('whole component requires equal codes')
   bit=0
  elif region in regionids:bit=regionids[region]
  else:raise ValueError('missing region')
  seen.add(root);rules.append((root,bit,inside,outside))
 # Every worker owns its OGR handles; no layer cursor crosses a thread.
 workers=c.get('workers',len(os.sched_getaffinity(0)) if hasattr(os,'sched_getaffinity') else (os.cpu_count() or 1))
 if type(workers) is not int or workers<1:raise ValueError('invalid raster workers')
 runtime=types.ModuleType('worldatlas_seed_runtime');runtime.__file__=str(HERE/'seed_runtime.py');runtime_source=(HERE/'seed_runtime.py').read_bytes()
 if hashlib.sha256(runtime_source).hexdigest()!=program_hashes['seed_runtime.py']:raise ValueError('runtime source changed')
 exec(compile(runtime_source,runtime.__file__,'exec'),runtime.__dict__)
 index=runtime.RuleIndex(rules)
 if paths[0].stat().st_size!=(g['height']+1)*4 or paths[1].stat().st_size%12:raise ValueError('invalid component array size')
 offsets=np.memmap(paths[0],mode='r',dtype='<u4');count=paths[1].stat().st_size//12
 if int(offsets[0])!=0 or int(offsets[-1])!=count or np.any(offsets[1:]<offsets[:-1]):raise ValueError('invalid component offsets')
 records=np.memmap(paths[1],mode='r',dtype='<u4',shape=(count,3)) if count else np.empty((0,3),dtype='<u4')
 local=threading.local()
 def raster(y):
  h=min(c['strip_rows'],g['height']-y)
  bits=index.required_bits(records[int(offsets[y]):int(offsets[y+h])])
  if bits==0:return y,np.zeros((h,g['width']),dtype=np.uint8),bits
  if not hasattr(local,'datasets'):local.datasets={}
  ds=gdal.GetDriverByName('MEM').Create('',g['width'],h,1,gdal.GDT_Byte)
  # Preserve original global-grid origin, dimensions and center arithmetic.
  ds.SetGeoTransform((g['west'],g['step'],0,g['north']-y*g['step'],0,-g['step']))
  for i in range(len(c['regions'])):
   if not bits & (1<<i):continue
   if i not in local.datasets:
    local.datasets[i]=ogr.Open(str(paths[2+i]))
    if local.datasets[i] is None:raise ValueError('cannot reopen geometry')
   source=local.datasets[i]
   layer=source.GetLayer(0);layer.ResetReading()
   if gdal.RasterizeLayer(ds,[1],layer,burn_values=[1<<i],options=['MERGE_ALG=ADD'])!=0:raise ValueError('rasterization failed')
  mask=ds.ReadAsArray();ds=None
  return y,mask,bits
 def ordered_strips():
  positions=iter(range(0,g['height'],c['strip_rows']))
  with ThreadPoolExecutor(max_workers=workers) as executor:
   pending=deque()
   for _ in range(workers):
    y=next(positions,None)
    if y is None:break
    pending.append(executor.submit(raster,y))
   while pending:
    yield pending.popleft().result()
    y=next(positions,None)
    if y is not None:pending.append(executor.submit(raster,y))
 out.mkdir(mode=0o700,parents=False,exist_ok=False)
 inside=np.zeros(len(rules),dtype=np.uint64);outside=inside.copy();categories=np.zeros(6,dtype=np.uint64);total=0;burns=0;strips=0
 with (out/'rows.u32le').open('xb') as rowout,(out/'runs.u32le').open('xb') as runout:
  rowout.write(np.asarray([0],dtype='<u4').tobytes())
  for y,mask,bits in ordered_strips():
   strips+=1;burns+=bits.bit_count()
   check_space();h=len(mask);lo,hi=int(offsets[y]),int(offsets[y+h])
   pairs,counts,ri,ro,cc=index.strip(mask,offsets[y:y+h+1].astype(np.int64)-lo,records[lo:hi])
   cumulative=np.cumsum(counts,dtype=np.uint64)+total
   if int(cumulative[-1])>0xffffffff:raise ValueError('too many output runs')
   rowout.write(cumulative.astype('<u4').tobytes());runout.write(pairs.tobytes())
   total=int(cumulative[-1]);inside+=ri;outside+=ro;categories+=cc
 if np.any(inside+outside==0):raise ValueError('selected root missing')
 populations={root:{'inside_cells':int(inside[i]),'outside_cells':int(outside[i])} for i,(root,_,_,_) in enumerate(rules)}
 code_counts={code:int(categories[code-17]) for code in range(17,23)}
 for x in pins:pinned(x)
 if config.read_bytes()!=raw:raise ValueError('config changed')
 if any(sha(HERE/name)!=digest for name,digest in program_hashes.items()):raise ValueError('program changed during build')
 report={'schema':'direct-region-seed-research-report-v2','status':'unreviewed-research-not-published','method':'Per selected root, rasterize explicitly supplied valid polygon(s) at GDAL pixel centers and select configured inside/outside codes; unselected roots are zero. Source and closure evidence pins do not prove the supplied polygon derives from them.','tie_convention':'GDAL rasterization pixel-center convention for recorded GDAL version; exact-boundary behavior needs review.','grid':{k:g[k] for k in ('width','height','west','north','step')},'grid_crs':g['crs'],'component_rows_sha256':pins[0]['sha256'],'component_runs_sha256':pins[1]['sha256'],'output_rows_sha256':sha(out/'rows.u32le'),'output_runs_sha256':sha(out/'runs.u32le'),'reserve_bytes':reserve,'config_sha256':hashlib.sha256(raw).hexdigest(),'input_pins':pins,'program_sha256':{'builder':program_hashes['build_seed.py'],'runtime_source':program_hashes['seed_runtime.py']},'outputs_sha256':{'rows':sha(out/'rows.u32le'),'runs':sha(out/'runs.u32le')},'rule_population':{str(k):v for k,v in populations.items()},'category_cell_counts':{str(k):v for k,v in code_counts.items()},'execution':{'api':'osgeo.gdal + NumPy','workers':workers,'strip_rows':c['strip_rows'],'strips':strips,'polygon_burns':burns,'possible_polygon_burns':strips*len(c['regions'])},'gdal_version':gdal.VersionInfo(),'elapsed_seconds':time.time()-start}
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':
 if len(sys.argv)!=3:raise SystemExit('usage: build_seed.py CONFIG NEW_OUTPUT_DIR')
 print(json.dumps(build(sys.argv[1],sys.argv[2]),indent=2))
