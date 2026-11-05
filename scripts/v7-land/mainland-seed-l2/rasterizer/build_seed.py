#!/usr/bin/env /usr/bin/python3
"""Config-driven center-rasterized mainland seed, research only, no historical labels."""
import hashlib,json,math,os,shutil,subprocess,sys,time
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
 start=time.time();program_hashes={name:sha(HERE/name) for name in ('build_seed.py','seed_kernel.cpp')};config=Path(config).resolve(strict=True);raw=config.read_bytes();c=json.loads(raw);out=Path(output).resolve()
 required={'schema','grid','component_rows','component_runs','regions','rules','evidence','strip_rows'}
 if not required<=set(c) or set(c)-required-{'reserve_bytes'} or c['schema']!='direct-region-seed-research-v1':raise ValueError('invalid config')
 if sys.byteorder!='little':raise ValueError('little-endian host required')
 reserve=c.get('reserve_bytes',2*1024**3)
 if type(reserve) is not int or reserve<0:raise ValueError('invalid reserve')
 def check_space():
  if shutil.disk_usage(out.parent).free<reserve:raise ValueError('insufficient free space for reserve')
 check_space()
 g=c['grid'];
 if set(g)!={'width','height','west','north','step','crs'} or g['crs']!='EPSG:4326' or any(type(g[k]) is not int or g[k]<=0 for k in ('width','height')) or any(type(g[k]) not in (int,float) or not math.isfinite(g[k]) for k in ('west','north','step')) or g['step']<=0:raise ValueError('invalid grid')
 if g['west'] < -180 or g['west']+g['width']*g['step'] > 180+1e-9 or g['north']>90 or g['north']-g['height']*g['step'] < -90-1e-9:raise ValueError('grid outside WGS84 bounds')
 if type(c['strip_rows']) is not int or not 1<=c['strip_rows']<=1024:raise ValueError('invalid strip rows')
 if not isinstance(c['regions'],list) or len(c['regions'])>8 or not isinstance(c['rules'],list) or not c['rules'] or not isinstance(c['evidence'],list):raise ValueError('invalid arrays')
 pins=[c['component_rows'],c['component_runs']]+[r['geometry'] for r in c['regions']]+c['evidence']; paths=[pinned(p) for p in pins]
 if out.exists():raise ValueError('output exists')
 for p in [config]+paths+[HERE/'build_seed.py',HERE/'seed_kernel.cpp']:
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
 out.mkdir(mode=0o700,parents=False,exist_ok=False);rulepath=out/'rules.txt';rulepath.write_text(''.join('%s %s %s %s\n'%r for r in rules))
 # Compile an ephemeral program in the new isolated output directory, not in source.
 subprocess.run(['g++','-O3','-std=c++17',str(HERE/'seed_kernel.cpp'),'-o',str(out/'seed-kernel')],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 err=(out/'builder.log').open('wb');proc=subprocess.Popen([str(out/'seed-kernel'),str(paths[0]),str(paths[1]),str(rulepath),str(out/'rows.u32le'),str(out/'runs.u32le'),str(g['width']),str(g['height']),str(os.getpid())],stdin=subprocess.PIPE,stderr=err)
 try:
  for y in range(0,g['height'],c['strip_rows']):
   check_space()
   h=min(c['strip_rows'],g['height']-y);ds=gdal.GetDriverByName('MEM').Create('',g['width'],h,1,gdal.GDT_Byte);ds.SetGeoTransform((g['west'],g['step'],0,g['north']-y*g['step'],0,-g['step']))
   for i,layer in enumerate(layers):
    layer.ResetReading();gdal.RasterizeLayer(ds,[1],layer,burn_values=[1<<i],options=['MERGE_ALG=ADD'])
   proc.stdin.write(ds.ReadRaster())
  proc.stdin.close();rc=proc.wait();err.close()
  if rc:raise RuntimeError('kernel failed, see builder.log')
 except BaseException:
  if proc.poll() is None:proc.kill();proc.wait()
  try:proc.stdin.close()
  except (BrokenPipeError,OSError,ValueError):pass
  err.close();raise
 for x in pins:pinned(x)
 if config.read_bytes()!=raw:raise ValueError('config changed')
 if any(sha(HERE/name)!=digest for name,digest in program_hashes.items()):raise ValueError('program changed during build')
 with open(out/'builder.log','rb') as lf:logbytes=lf.read(1048577)
 if len(logbytes)>1048576:raise ValueError('rasterizer log exceeds bound')
 log=logbytes.decode('ascii')
 populations={};code_counts={}
 for line in log.splitlines():
  z=line.split()
  if len(z)==4 and z[0]=='RULE':
   root,inside,outside=map(int,z[1:]);
   if root in populations:raise ValueError('duplicate population record')
   populations[root]={'inside_cells':inside,'outside_cells':outside}
  elif len(z)==3 and z[0]=='CODE':
   code,count=map(int,z[1:]);
   if code in code_counts:raise ValueError('duplicate category count')
   code_counts[code]=count
  else:raise ValueError('invalid rasterizer population record')
 if set(populations)!={r[0] for r in rules} or set(code_counts)!=set(range(17,23)):raise ValueError('incomplete rasterizer population records')
 report={'schema':'direct-region-seed-research-report-v1','status':'unreviewed-research-not-published','method':'Per selected root, rasterize explicitly supplied valid polygon(s) at GDAL pixel centers and select configured inside/outside codes; unselected roots are zero. Source and closure evidence pins do not prove the supplied polygon derives from them.','tie_convention':'GDAL rasterization pixel-center convention for recorded GDAL version; exact-boundary behavior needs review.','grid':{k:g[k] for k in ('width','height','west','north','step')},'grid_crs':g['crs'],'component_rows_sha256':pins[0]['sha256'],'component_runs_sha256':pins[1]['sha256'],'output_rows_sha256':sha(out/'rows.u32le'),'output_runs_sha256':sha(out/'runs.u32le'),'reserve_bytes':reserve,'config_sha256':hashlib.sha256(raw).hexdigest(),'input_pins':pins,'program_sha256':{'builder':program_hashes['build_seed.py'],'kernel_source':program_hashes['seed_kernel.cpp'],'compiled_kernel':sha(out/'seed-kernel')},'outputs_sha256':{'rows':sha(out/'rows.u32le'),'runs':sha(out/'runs.u32le')},'rule_population':{str(k):v for k,v in populations.items()},'category_cell_counts':{str(k):v for k,v in code_counts.items()},'gdal_version':gdal.VersionInfo(),'elapsed_seconds':time.time()-start}
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':
 if len(sys.argv)!=3:raise SystemExit('usage: build_seed.py CONFIG NEW_OUTPUT_DIR')
 print(json.dumps(build(sys.argv[1],sys.argv[2]),indent=2))
