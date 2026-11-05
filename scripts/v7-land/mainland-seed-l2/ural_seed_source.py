"""Bind a selected Ural boundary to the independently replayed raw recipe.

The caller authenticates the fresh Neon snapshot and catalog. The recipe also
requires its separately pinned earlier Neon selector snapshot; this is a
structured input and does not assert historical construction provenance.
No region hash, route, decision, or map is changed by this gate.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from regions import URAL_CONSTRUCTION_INPUTS, geometry_hash, points

BOUNDARY = 'ural_kara_coast_to_caspian'
GEOMETRY_SHA256 = '68390aa6ce5352226777adde3979315e1de85ca26d662c4b1c32610d1d73da66'
RECIPE_SNAPSHOT_SHA256 = '615bc1aaa67d099ebd140dc172fd54885d66e82ef595a57a97e5a284f483f7cc'
RECIPE_CODE = {
 'reproduce_raw_boundary.py':'d07dff4e9155c5a66bde7b27b68ebe5633f523e8933d96470a079606fd6ba7a7',
 'extract_watershed_selector.py':'802a78fb5690d800f1c7aca19806b6433a6361e8d48235fb7c0788baf0acbe79',
 'reproduce_arctic_gap_rasters.py':'944ed865fb2ff1ebc5f96a6f7cd451a1d94c4aecaffa7b54ffb157b4b4e5e9c5',
 'construct_arctic_gap_paths.py':'fba208929d37ac4ea17b2a80c2cfcc8c81fd5431aed2c55a9ec9a216aeb479ce',
 'construct_cop_spring_flow.py':'ed99aa6d9e8b982e5336b7b52a2dc2afcf15fdaed486f95d07b155fd74d24530',
 'trace_gap_raw_crossings.py':'2e632b3e64d3f7a88d7f06fd2b729da9f966406005bc0c64b6080f48ba49b25b',
 'check_raw_chord_coverage.py':'9f176d83b9783f95eb08959bf1a5f7711e064f827ccd0639389344f2c39b3dc1',
 'verify_raw_north_candidate.py':'ee6de46d4cbdb0e98d109a3d54db857cff8d0dc92cfb67c7e0c859b5e5842066',
 'assemble_raw_backed_candidate.py':'f64266f819744714a9b5081312be2f0d3b76d637339b194d7d50cc661ce6b443',
 'reconstruct_hybrid_osm.py':'da49e3b3e0c5155c39cf95967f5f0a1ac3d5f68d9d8f4429f840391e37de64bd'}


def sha(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for block in iter(lambda:f.read(1048576),b''):h.update(block)
 return h.hexdigest()


def bind(boundaries,catalog,pin):
 """Replay the pinned recipe and require equality to the selected boundary.

 pin names four existing directories: recipe_dir, inputs_dir, helpers_dir,
 and work_parent. Inputs include raw R2 readbacks and review_snapshot.json.
 The pinned runner independently validates their expected content.
 """
 key=('boundary',BOUNDARY)
 if key not in boundaries:
  if pin is not None:raise ValueError('Ural inputs supplied without selected boundary')
  return boundaries,None
 if not isinstance(pin,dict) or set(pin)!={'recipe_dir','inputs_dir','helpers_dir','work_parent'}:raise ValueError('selected Ural boundary requires pinned recipe inputs')
 rec=boundaries[key]
 selected={'type':'LineString','coordinates':[[float(x),float(y)] for x,y in points(rec.get('geometry'))]}
 if rec.get('geometry_sha256')!=GEOMETRY_SHA256 or geometry_hash(selected)!=GEOMETRY_SHA256:raise ValueError('selected Ural geometry mismatch')
 refs=rec.get('qualified_source_refs')
 if not isinstance(refs,list) or len(refs)!=len(URAL_CONSTRUCTION_INPUTS):raise ValueError('Ural construction source set mismatch')
 seen=set()
 for ref in refs:
  rel=ref.get('relationship') if isinstance(ref,dict) else None
  if rel not in URAL_CONSTRUCTION_INPUTS or rel in seen or ref.get('role')!='construction_input':raise ValueError('Ural construction source set mismatch')
  seen.add(rel);sid,digest,tile=URAL_CONSTRUCTION_INPUTS[rel]
  source=catalog.get((ref.get('source_id'),ref.get('version')))
  if ref.get('source_id')!=sid or not isinstance(source,dict) or source.get('kind')!='raw' or source.get('sha256')!=digest:raise ValueError('Ural source catalog mismatch')
  if tile and (source.get('representation')!='manifest_of_raw_parts' or source.get('full_tile_sha256')!=tile):raise ValueError('Ural raw-tile manifest mismatch')
 if seen!=set(URAL_CONSTRUCTION_INPUTS):raise ValueError('Ural construction source set mismatch')
 recipe=Path(pin['recipe_dir']).resolve(strict=True);inputs=Path(pin['inputs_dir']).resolve(strict=True)
 helpers=Path(pin['helpers_dir']).resolve(strict=True);work=Path(pin['work_parent']).resolve(strict=True)
 if not all(x.is_dir() for x in (recipe,inputs,helpers,work)):raise ValueError('Ural recipe paths must be directories')
 if any(work==p or work in p.parents or p in work.parents for p in (recipe,inputs,helpers)):raise ValueError('Ural work overlaps inputs')
 def capture_code():
  captured={}
  for name,digest in RECIPE_CODE.items():
   raw=(recipe/name).read_bytes()
   if len(raw)>1024*1024 or hashlib.sha256(raw).hexdigest()!=digest:raise ValueError('Ural recipe code pin mismatch: '+name)
   captured[name]=raw
  return captured
 captured=capture_code()
 if sha(inputs/'review_snapshot.json')!=RECIPE_SNAPSHOT_SHA256:raise ValueError('Ural selector snapshot pin mismatch')
 with tempfile.TemporaryDirectory(prefix='ural-replay-',dir=work) as temp:
  private=Path(temp)/'recipe';private.mkdir();out=Path(temp)/'run'
  for name,raw in captured.items():(private/name).write_bytes(raw)
  proc=subprocess.run([sys.executable,str(private/'reproduce_raw_boundary.py'),'--inputs',str(inputs),'--helpers',str(helpers),'--workdir',str(out)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
  if proc.returncode:raise ValueError('Ural raw recipe failed: '+proc.stderr[:4096].decode(errors='replace'))
  derived=out/'ural-raw-backed-continuous-cop-only.geometry.json'
  if not derived.is_file() or derived.stat().st_size>4*1024*1024:raise ValueError('invalid Ural recipe output')
  raw=derived.read_bytes();geom=json.loads(raw)
  if geometry_hash(geom)!=GEOMETRY_SHA256 or geom!=selected:raise ValueError('Ural raw recipe differs from selected boundary')
  if capture_code()!=captured or any((private/name).read_bytes()!=raw for name,raw in captured.items()):raise ValueError('Ural recipe code changed during replay')
  if sha(inputs/'review_snapshot.json')!=RECIPE_SNAPSHOT_SHA256:raise ValueError('Ural selector snapshot changed')
  trace={'boundary_id':BOUNDARY,'geometry_sha256':GEOMETRY_SHA256,'geometry_file_sha256':hashlib.sha256(raw).hexdigest(),
         'selector_snapshot_sha256':RECIPE_SNAPSHOT_SHA256,'recipe_code_sha256':dict(RECIPE_CODE),
         'source_count':len(seen),'method':'raw-hydrobasins-arcticdem-copernicus-osm-and-neon-selector-v1',
         'limitations':['The structured selector has incomplete historical lineage.','Modeled terrain, mapped spring and delta choices are not survey certification.']}
 return boundaries,trace
