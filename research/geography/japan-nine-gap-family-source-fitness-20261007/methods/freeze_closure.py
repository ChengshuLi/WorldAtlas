"""Freeze exact local code, inputs and runtime before the two full overlays."""
import hashlib,importlib.metadata,json,pathlib,subprocess,sys,platform
from pyproj import datadir
import pyproj,shapely,numpy
ROOT=pathlib.Path(__file__).resolve().parents[1];REPO=ROOT.parents[2];BASE='cbae22cc877f6f8a70650069d91d2b34240582f7'
def sha(b):return hashlib.sha256(b).hexdigest()
def canon(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()+b'\n'
def git(*args):return subprocess.check_output(['git','-C',str(REPO),*args])
def sha_path(p):
 h=hashlib.sha256();n=0
 with p.open('rb') as f:
  for block in iter(lambda:f.read(1024*1024),b''):h.update(block);n+=len(block)
 return n,h.hexdigest()
def baseline_descriptor(path):
 if path.startswith('/') or '\\' in path or any(x in ('','.','..') for x in path.split('/')):raise ValueError('unsafe baseline path')
 tree=git('ls-tree','-z',BASE,'--',path).decode().rstrip('\0')
 if not tree or '\t' not in tree:raise ValueError('missing baseline file '+path)
 meta,name=tree.split('\t',1);mode,kind,oid=meta.split()
 if mode not in ('100644','100755') or kind!='blob' or name!=path:raise ValueError('baseline evidence is not a unique ordinary file '+path)
 b=git('cat-file','blob',oid)
 if len(b)>33554432:raise ValueError('baseline ordinary file size bound '+path)
 result={'path':path,'bytes':len(b),'sha256':sha(b),'hash_kind':'file-bytes'}
 if path.endswith('.gz'):
  import gzip
  decoded=gzip.decompress(b)
  if len(decoded)>33554432:raise ValueError('baseline decoded file size bound '+path)
  result.update(uncompressed_bytes=len(decoded),uncompressed_sha256=sha(decoded))
 return result
scope=json.loads((ROOT/'inputs/immutable-scope-and-inputs.json').read_bytes())
phys=json.loads((ROOT/'inputs/existing-physical-row-scope.json').read_bytes())
paths=set()
for x in scope['complete_routing_body_slices']:paths.add(x['path'])
for x in scope['source_payloads']:paths.add(x.get('payload_path') or x['logical_path'])
for x in scope['complete_world_parts']:
 if x['path'] in ('data/geography/part-11.json','data/geography/part-12.json'):paths.add(x['path'])
for x in phys['selected_whole_rows']:paths.add(x['existing_output_path'])
paths.update([
 'data/world-index.json','data/administrative-sources.json','scripts/administrative.py',
 'coordination/engineering/original-geography-source-corpus-20261006/catalogue.json',
 'coordination/engineering/global-actionability-routing-20261007/input-config.json',
 'coordination/engineering/global-actionability-routing-20261007/results/report.json',
 'coordination/engineering/global-physical-comparison-20261006/README.md',
 'coordination/engineering/global-physical-comparison-20261006/input-config.json',
 'coordination/engineering/global-physical-comparison-20261006/evidence-quality.json'])
cat=json.loads((REPO/'coordination/engineering/original-geography-source-corpus-20261006/catalogue.json').read_bytes())
product=next(x for x in cat['products'] if x['key']=='gb:JPN:ADM2')
for part in product['parts']:paths.add(part['path'])
baseline=[baseline_descriptor(p) for p in sorted(paths)]
code_paths=['research/geography/japan-nine-gap-family-source-fitness-20261007/methods/producer.py','research/geography/japan-nine-gap-family-source-fitness-20261007/methods/mlit_shapefile.py','research/geography/japan-nine-gap-family-source-fitness-20261007/methods/restore_mlit_source.py','research/geography/japan-nine-gap-family-source-fitness-20261007/methods/run_once.py']
code=[]
for p in code_paths:
 b=(REPO/p).read_bytes();code.append({'path':p,'bytes':len(b),'sha256':sha(b)})
candidate_paths=[]
for subdir in ('inputs','sources','receipts'):
 for p in sorted((ROOT/subdir).rglob('*')):
  if p.is_file() and p.name!='runtime-freeze.json':candidate_paths.append(p.relative_to(ROOT).as_posix())
candidate=[]
for rel in candidate_paths:
 p=ROOT/rel;b=p.read_bytes()
 if len(b)>33554432:raise ValueError('candidate ordinary input bound '+rel)
 candidate.append({'path':'research/geography/japan-nine-gap-family-source-fitness-20261007/'+rel,'bytes':len(b),'sha256':sha(b)})
# Pin the exact external source archive but keep its 242 MB body restoration-only.
archive=REPO/'.cache/source-downloads/N03-170101_GML.zip';n,h=sha_path(archive)
mlit=json.loads((ROOT/'sources/mlit/n03-2017-source-manifest.json').read_bytes())
if n!=mlit['http_content_length'] or h!=mlit['archive_sha256']:raise ValueError('external complete MLIT archive differs')
# Binary/package/data file closure for the bundled runtime used by the full executions.
runtime_files=[]
def add_runtime(path):
 p=pathlib.Path(path).resolve()
 if not p.is_file():return
 b=p.read_bytes();runtime_files.append({'path':str(p.resolve()),'bytes':len(b),'sha256':sha(b)})
for p in [sys.executable,shapely.__file__,shapely.lib.__file__,pyproj.__file__,numpy.__file__,pathlib.Path(datadir.get_data_dir())/'proj.db']:
 add_runtime(p)
for package in [pathlib.Path(shapely.__file__).parent,pathlib.Path(pyproj.__file__).parent,pathlib.Path(numpy.__file__).parent]:
 for p in package.rglob('*'):
  if p.is_file() and '__pycache__' not in p.parts and p.suffix in ('.so','.dylib','.py','.json','.csv','.txt','.dat','.db'):
   add_runtime(p)
for parent in set([pathlib.Path(shapely.__file__).parent.parent,pathlib.Path(pyproj.__file__).parent.parent,pathlib.Path(numpy.__file__).parent.parent]):
 for libdir in parent.glob('*.libs'):
  for p in libdir.rglob('*'):
   if p.is_file():add_runtime(p)
# Stable file list, avoiding duplicate canonical paths.
runtime_files=list({x['path']:x for x in runtime_files}.values());runtime_files.sort(key=lambda x:x['path'])
freeze={'schema':'japan-nine-source-overlay-freeze-v1','data_baseline_commit':BASE,'code_files':code,'candidate_inputs':candidate,'baseline_inputs':baseline,'external_inputs':[{'path':'.cache/source-downloads/N03-170101_GML.zip','bytes':n,'sha256':h,'restoration_only':True}],
 'runtime':{'python_version':sys.version,'python_executable':str(pathlib.Path(sys.executable).resolve()),'platform':platform.platform(),'shapely':shapely.__version__,'geos':shapely.geos_version_string,'pyproj':pyproj.__version__,'proj':pyproj.proj_version_str,'numpy':numpy.__version__,'proj_data_directory':datadir.get_data_dir(),'proj_network':'OFF during runs','files':runtime_files,'file_count':len(runtime_files)},
 'scope':{'families':len(scope['families']),'components':len(scope['components']),'contacts':len(scope['contacts']),'category_counts':scope['category_counts'],'scope_sha256':sha((ROOT/'inputs/immutable-scope-and-inputs.json').read_bytes())},'comparison':'Complete exact source-relative overlays for 28 whole candidate polygons and 21 whole current contacts against complete geoBoundaries full/simplified products and spatially selected native N03 2017 SHP polygons; GSHHG output reused, not recomputed.'}
(ROOT/'inputs/runtime-freeze.json').write_bytes(canon(freeze))
print(json.dumps({'baseline_files':len(baseline),'baseline_bytes':sum(x['bytes'] for x in baseline),'candidate_files':len(candidate),'code_files':len(code),'runtime_files':len(runtime_files),'freeze_bytes':(ROOT/'inputs/runtime-freeze.json').stat().st_size,'external_archive_sha256':h},ensure_ascii=False))
