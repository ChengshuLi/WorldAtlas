"""Bind a selected Ural boundary to the independently replayed raw recipe.

The caller authenticates the fresh Neon snapshot and catalog. The recipe also
requires its separately pinned earlier Neon selector snapshot; this is a
structured input and does not assert historical construction provenance.
No region hash, route, decision, or map is changed by this gate.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile

from regions import SUPPORTING_RELATIONSHIPS, URAL_CONSTRUCTION_INPUTS, geometry_hash, points
from export_adapter import boundary_records, load_pinned_snapshot

BOUNDARY = 'ural_kara_coast_to_caspian'
GEOMETRY_SHA256 = '68390aa6ce5352226777adde3979315e1de85ca26d662c4b1c32610d1d73da66'
RECIPE_SNAPSHOT_SHA256 = '615bc1aaa67d099ebd140dc172fd54885d66e82ef595a57a97e5a284f483f7cc'
RECIPE_CODE = {
 'reproduce_raw_boundary.py':'c0c3736362a7c9bfc4c7526e1034543c63dafbb3cfcb9abab3be7046e277c561',
 'extract_watershed_selector.py':'802a78fb5690d800f1c7aca19806b6433a6361e8d48235fb7c0788baf0acbe79',
 'reproduce_arctic_gap_rasters.py':'944ed865fb2ff1ebc5f96a6f7cd451a1d94c4aecaffa7b54ffb157b4b4e5e9c5',
 'construct_arctic_gap_paths.py':'fba208929d37ac4ea17b2a80c2cfcc8c81fd5431aed2c55a9ec9a216aeb479ce',
 'construct_cop_spring_flow.py':'ed99aa6d9e8b982e5336b7b52a2dc2afcf15fdaed486f95d07b155fd74d24530',
 'trace_gap_raw_crossings.py':'2e632b3e64d3f7a88d7f06fd2b729da9f966406005bc0c64b6080f48ba49b25b',
 'check_raw_chord_coverage.py':'9f176d83b9783f95eb08959bf1a5f7711e064f827ccd0639389344f2c39b3dc1',
 'verify_raw_north_candidate.py':'ee6de46d4cbdb0e98d109a3d54db857cff8d0dc92cfb67c7e0c859b5e5842066',
 'assemble_raw_backed_candidate.py':'f64266f819744714a9b5081312be2f0d3b76d637339b194d7d50cc661ce6b443',
 'reconstruct_hybrid_osm.py':'da49e3b3e0c5155c39cf95967f5f0a1ac3d5f68d9d8f4429f840391e37de64bd'}
HELPERS={
 'terrain_basin_screen.py':('26a81f00180f2007cf8fdf0af796662eeaa3b057a1665392207054855cf001df','4b5acd6a6d0039b125bc9299b2f1007cf2432903762a49def9ee54fc4263a731'),
 'priority_d8.py':('884ce9f0d84a193ba82fa85dbd10b2d0894c2b6e389a6df05099146f1db8dd79','b7e8deef7289a1cd5cf38c16270e6ab32dd04c3141f0589a8ff364605497fc24'),
 'spring_connector_graph.py':('86204b914bce4fdf0ee03f71d169acb8d10e301e562ae5e49ef6a48ac42211e5','be147977fa1102b2578146a17724188f22de3a26c1f6e2f34061c9f093169579'),
 'spring_triple_route.py':('a553215f79cd64d11d2e67998977ced8be5f878cb4a5acd8ee7650841da1da9f','fe1acd1d9e7bc7d83120f5b8244d6454594fa166b75d58f953f566a5c2fbf287'),
 'projected_route.py':('e3c9ac7465fc5f14e9442f206e9cc9301f2630f3446feea9802797dcb3fce4ef','3cd363d478be84697c269a42463af6c50a3cd2fa659e3c443ee92393ed45703c')}
BOOTSTRAP=("import json,runpy,sys; paths=json.loads(sys.argv[1]); "
           "script=sys.argv[2]; sys.argv=sys.argv[2:]; "
           "sys.path[:0]=paths; runpy.run_path(script,run_name='__main__')")


def sha(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for block in iter(lambda:f.read(1048576),b''):h.update(block)
 return h.hexdigest()


def dependency_tree_sha256(root):
 """Hash regular files and directories without following symlinks or .pth files."""
 root=Path(root).resolve(strict=True)
 if not root.is_dir():raise ValueError('dependency root must be a directory')
 h=hashlib.sha256()
 for directory,dirs,files in os.walk(root,followlinks=False):
  dirs.sort();files.sort();base=Path(directory)
  for name in dirs+files:
   p=base/name;mode=p.lstat().st_mode;rel=p.relative_to(root).as_posix().encode('utf-8')
   if stat.S_ISDIR(mode):kind=b'D';digest=b''
   elif stat.S_ISREG(mode):kind=b'F';digest=bytes.fromhex(sha(p))
   else:raise ValueError('dependency tree contains symlink or non-regular file')
   h.update(kind+len(rel).to_bytes(8,'big')+rel+digest)
 return h.hexdigest()


def isolated_caller():
 return sys.flags.isolated==1 and sys.flags.no_site==1


def bind(boundaries,catalog,pin):
 """Replay the pinned recipe and require equality to the selected boundary.

 pin names the fresh snapshot and its hash, an explicitly pinned Python binary
 and ordered dependency-directory tree hashes, plus four existing directories:
 recipe_dir, inputs_dir, helpers_dir, and work_parent. Inputs include raw R2
 readbacks and the separately pinned historical selector snapshot. The caller
 must authenticate the fresh export; the gate independently parses its bytes.
 """
 key=('boundary',BOUNDARY)
 if key not in boundaries:
  if pin is not None:raise ValueError('Ural inputs supplied without selected boundary')
  return boundaries,None
 if not isolated_caller():raise ValueError('Ural gate requires an isolated no-site Python caller')
 if not isinstance(pin,dict) or set(pin)!={'recipe_dir','inputs_dir','helpers_dir','work_parent','snapshot','snapshot_sha256','python','dependency_dirs'}:raise ValueError('selected Ural boundary requires pinned recipe inputs')
 gate_path=Path(__file__).resolve();gate_sha=sha(gate_path)
 fresh=load_pinned_snapshot(pin['snapshot'],pin['snapshot_sha256'],lambda:None)
 fresh_revision,_,fresh_boundaries,fresh_catalog=boundary_records(fresh)
 if fresh_boundaries.get(key)!=boundaries[key]:raise ValueError('Ural selected record differs from pinned fresh snapshot')
 rec=boundaries[key]
 if rec.get('revision_id')!=fresh_revision:raise ValueError('Ural selected revision mismatch')
 selected={'type':'LineString','coordinates':[[float(x),float(y)] for x,y in points(rec.get('geometry'))]}
 if rec.get('geometry_sha256')!=GEOMETRY_SHA256 or geometry_hash(selected)!=GEOMETRY_SHA256:raise ValueError('selected Ural geometry mismatch')
 refs=rec.get('qualified_source_refs')
 if not isinstance(refs,list) or len(refs)<len(URAL_CONSTRUCTION_INPUTS):raise ValueError('Ural construction source set mismatch')
 seen=set();keys=set();source_pins=[];supporting=[]
 for ref in refs:
  rel=ref.get('relationship') if isinstance(ref,dict) else None
  if not isinstance(ref,dict) or set(ref)!={'source_id','version','relationship','role'}:raise ValueError('invalid Ural source reference')
  source_key=(ref['source_id'],ref['version'])
  if source_key in keys:raise ValueError('duplicate Ural source reference')
  keys.add(source_key)
  source=catalog.get((ref.get('source_id'),ref.get('version')))
  if not isinstance(source,dict) or source.get('kind')!='raw' or not re.fullmatch('[0-9a-f]{64}',str(source.get('sha256'))):raise ValueError('Ural source catalog mismatch')
  if fresh_catalog.get((ref.get('source_id'),ref.get('version')))!=source:raise ValueError('Ural catalog differs from pinned fresh snapshot')
  if rel in SUPPORTING_RELATIONSHIPS and ref.get('role')=='supporting_research_evidence':
   supporting.append({'source_id':ref['source_id'],'version':ref['version'],'relationship':rel,'catalog_sha256':source['sha256']});continue
  if rel not in URAL_CONSTRUCTION_INPUTS or rel in seen or ref.get('role')!='construction_input':raise ValueError('Ural construction source set mismatch')
  seen.add(rel);sid,digest,tile=URAL_CONSTRUCTION_INPUTS[rel]
  if ref.get('source_id')!=sid or source.get('sha256')!=digest:raise ValueError('Ural source catalog mismatch')
  if tile and (source.get('representation')!='manifest_of_raw_parts' or source.get('full_tile_sha256')!=tile):raise ValueError('Ural raw-tile manifest mismatch')
  entry={'source_id':sid,'version':ref['version'],'relationship':rel,'catalog_sha256':digest}
  if tile:entry.update(representation='manifest_of_raw_parts',raw_tile_sha256=tile)
  source_pins.append(entry)
 if seen!=set(URAL_CONSTRUCTION_INPUTS):raise ValueError('Ural construction source set mismatch')
 recipe=Path(pin['recipe_dir']).resolve(strict=True);inputs=Path(pin['inputs_dir']).resolve(strict=True)
 helpers=Path(pin['helpers_dir']).resolve(strict=True);work=Path(pin['work_parent']).resolve(strict=True)
 if not all(x.is_dir() for x in (recipe,inputs,helpers,work)):raise ValueError('Ural recipe paths must be directories')
 if any(work==p or work in p.parents or p in work.parents for p in (recipe,inputs,helpers)):raise ValueError('Ural work overlaps inputs')
 python_pin=pin['python'];deps=pin['dependency_dirs']
 if not isinstance(python_pin,dict) or set(python_pin)!={'path','sha256'} or not isinstance(deps,list) or not 1<=len(deps)<=8:raise ValueError('invalid Ural Python runtime pin')
 python=Path(python_pin['path']).resolve(strict=True)
 if not python.is_file() or sha(python)!=python_pin['sha256']:raise ValueError('Ural Python executable pin mismatch')
 dep_paths=[]
 for d in deps:
  if not isinstance(d,dict) or set(d)!={'path','sha256'}:raise ValueError('invalid Ural dependency pin')
  path=Path(d['path']).resolve(strict=True)
  if path in dep_paths or work==path or work in path.parents or path in work.parents:raise ValueError('invalid or overlapping Ural dependency path')
  if dependency_tree_sha256(path)!=d['sha256']:raise ValueError('Ural dependency tree pin mismatch')
  dep_paths.append(path)
 def capture_code():
  captured={}
  for name,digest in RECIPE_CODE.items():
   raw=(recipe/name).read_bytes()
   if len(raw)>1024*1024 or hashlib.sha256(raw).hexdigest()!=digest:raise ValueError('Ural recipe code pin mismatch: '+name)
   captured[name]=raw
  return captured
 captured=capture_code()
 helper_bytes={}
 for name,allowed in HELPERS.items():
  raw=(helpers/name).read_bytes();digest=hashlib.sha256(raw).hexdigest()
  if len(raw)>1024*1024 or digest not in allowed:raise ValueError('Ural helper pin mismatch: '+name)
  helper_bytes[name]=raw
 if sha(inputs/'review_snapshot.json')!=RECIPE_SNAPSHOT_SHA256:raise ValueError('Ural selector snapshot pin mismatch')
 with tempfile.TemporaryDirectory(prefix='ural-replay-',dir=work) as temp:
  private=Path(temp)/'recipe';private.mkdir();out=Path(temp)/'run'
  for name,raw in captured.items():(private/name).write_bytes(raw)
  private_helpers=Path(temp)/'helpers';private_helpers.mkdir()
  for name,raw in helper_bytes.items():(private_helpers/name).write_bytes(raw)
  private_deps=[]
  for index,(path,d) in enumerate(zip(dep_paths,deps)):
   dest=Path(temp)/('deps-'+str(index));shutil.copytree(path,dest,symlinks=True)
   if dependency_tree_sha256(dest)!=d['sha256']:raise ValueError('Ural captured dependency tree mismatch')
   private_deps.append(str(dest))
  home=Path(temp)/'home';home.mkdir()
  clean_env={'PATH':os.defpath,'LC_ALL':'C','HOME':str(home),'XDG_CONFIG_HOME':str(home),'XDG_CACHE_HOME':str(home),'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1','MKL_NUM_THREADS':'1','NUMEXPR_NUM_THREADS':'1'}
  cmd=[str(python),'-I','-S','-B','-c',BOOTSTRAP,json.dumps(private_deps),str(private/'reproduce_raw_boundary.py'),'--inputs',str(inputs),'--helpers',str(private_helpers),'--workdir',str(out),'--python-sha256',python_pin['sha256']]
  for path in private_deps:cmd.extend(['--dependency-dir',path])
  proc=subprocess.run(cmd,env=clean_env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
  if proc.returncode:raise ValueError('Ural raw recipe failed: '+proc.stderr[:4096].decode(errors='replace'))
  derived=out/'ural-raw-backed-continuous-cop-only.geometry.json'
  if not derived.is_file() or derived.stat().st_size>4*1024*1024:raise ValueError('invalid Ural recipe output')
  raw=derived.read_bytes();geom=json.loads(raw)
  if geometry_hash(geom)!=GEOMETRY_SHA256 or geom!=selected:raise ValueError('Ural raw recipe differs from selected boundary')
  if capture_code()!=captured or any((private/name).read_bytes()!=raw for name,raw in captured.items()):raise ValueError('Ural recipe code changed during replay')
  if any((helpers/name).read_bytes()!=raw or (private_helpers/name).read_bytes()!=raw for name,raw in helper_bytes.items()):raise ValueError('Ural helper changed during replay')
  if sha(python)!=python_pin['sha256'] or any(dependency_tree_sha256(path)!=d['sha256'] or dependency_tree_sha256(Path(copy))!=d['sha256'] for path,d,copy in zip(dep_paths,deps,private_deps)):raise ValueError('Ural Python runtime changed during replay')
  if sha(gate_path)!=gate_sha:raise ValueError('Ural gate code changed during replay')
  if sha(inputs/'review_snapshot.json')!=RECIPE_SNAPSHOT_SHA256:raise ValueError('Ural selector snapshot changed')
  if sha(pin['snapshot'])!=pin['snapshot_sha256']:raise ValueError('fresh selected snapshot changed during Ural replay')
  trace={'schema':'ural-source-replay-trace-v1','status':'verified','boundary_id':BOUNDARY,'selected_revision':fresh_revision,
         'selected_geometry_sha256':rec['geometry_sha256'],'derived_geometry_sha256':geometry_hash(geom),
         'geometry_file_sha256':hashlib.sha256(raw).hexdigest(),
         'selected_snapshot_sha256':pin['snapshot_sha256'],'selector_snapshot_sha256':RECIPE_SNAPSHOT_SHA256,'gate_code_sha256':gate_sha,'recipe_code_sha256':dict(RECIPE_CODE),
         'helper_sha256':{name:hashlib.sha256(raw).hexdigest() for name,raw in sorted(helper_bytes.items())},
         'python_sha256':python_pin['sha256'],'dependency_tree_sha256':[d['sha256'] for d in deps],
         'sources':sorted(source_pins,key=lambda x:(x['source_id'],x['version'])),
         'supporting_citations':sorted(supporting,key=lambda x:(x['source_id'],x['version'])),
         'method':'raw-hydrobasins-arcticdem-copernicus-osm-and-neon-selector-v1',
         'limitations':['The structured selector has incomplete historical lineage.','Modeled terrain, mapped spring and delta choices are not survey certification.','The outer caller, Python standard library and operating-system native libraries are part of the trusted runtime; the outer caller must pin its own code and dependencies.']}
 return boundaries,trace


def verify_trace(boundaries,catalog,pin,expected_trace):
 """Independently replay inputs and compare the whole previously recorded trace."""
 _,observed=bind(boundaries,catalog,pin)
 if observed is None or observed!=expected_trace:raise ValueError('Ural source replay trace mismatch')
 return observed
