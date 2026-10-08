#!/usr/bin/env python3
"""Freeze whole-file input/code/runtime pins and bounded Arctic phase reservations."""
from __future__ import annotations
import argparse, hashlib, json, subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
PACKET=Path(__file__).resolve().parent
PREFIX='research/geography/arctic-seven-source-fit-20261008/'
BASELINE_SOURCE='960ba2f4fef0fc9881b8a106a944e6e3874e98c9'
SCOPE_MANIFEST_COMMIT='66ceaf821ec2b9b6ed1bb25bc7ed31a2a2ab6ecf'
SCOPE_MANIFEST_SHA256='573f4047e7e022e741c41acb35f5534ed7e25f5faf6801eb8e86f5c2aa70cc66'
RUNTIME='research/geography/arctic-seven-source-fit-20261008/runtime-lock.json'
NATIVE_RUNTIME='research/geography/arctic-seven-source-fit-20261008/native-tools-lock-r10.json'
NATIVE_CHECKER='research/geography/arctic-seven-source-fit-20261008/native-tools-lock-r10.sh'
CODE=[
 'scripts/evidence/immutable.py','scripts/evidence/geometry.py','scripts/ellipsoidal_area.py',
 PREFIX+'source_phase_runtime.py',PREFIX+'prepare_sources.py',PREFIX+'scan_neighbors.py',
 PREFIX+'reproduce_fit.py',PREFIX+'run_source_phase.py',
]
NATIVE_SCRIPT=PREFIX+'native_archive_extract.sh'

def sha(raw):return hashlib.sha256(raw).hexdigest()
GIT_EXECUTABLE=None
def git(*args):
 global GIT_EXECUTABLE
 if GIT_EXECUTABLE is None:
  lock=json.loads((ROOT/NATIVE_RUNTIME).read_text())
  GIT_EXECUTABLE=lock['commands']['git']
  row=next(x for x in lock['files'] if x['path']==GIT_EXECUTABLE and x['kind']=='executable')
  path=Path(GIT_EXECUTABLE)
  if path.is_symlink() or not path.is_file() or path.stat().st_size!=row['bytes'] or sha(path.read_bytes())!=row['sha256']:
   raise ValueError('Pinned native Git executable drift')
 return subprocess.check_output([GIT_EXECUTABLE,'-C',str(ROOT),*args],stderr=subprocess.PIPE)
def descriptor(commit,path,expected=None,verify_materialized=False):
 raw=git('show',f'{commit}:{path}')
 row={'path':path,'bytes':len(raw),'sha256':sha(raw),'hash_kind':'file-bytes'}
 if expected and (row['bytes']!=expected['bytes'] or row['sha256']!=expected['sha256']):
  raise ValueError('Execution commit no longer contains issue-pinned source bytes: '+path)
 materialized=ROOT/path
 if verify_materialized:
  raw_local=materialized.read_bytes()
  if len(raw_local)!=row['bytes'] or sha(raw_local)!=row['sha256']:
   raise ValueError('Materialized code/lock differs from exact execution commit: '+path)
 elif materialized.is_file() and not materialized.is_symlink():
  raw_local=materialized.read_bytes()
  if len(raw_local)!=row['bytes'] or sha(raw_local)!=row['sha256']:
   raise ValueError('Materialized source differs from exact execution commit: '+path)
 return row
def main():
 parser=argparse.ArgumentParser(); parser.add_argument('--execution-commit',required=True)
 parser.add_argument('--plan-output',default=PREFIX+'phase-plan-r10.json'); args=parser.parse_args()
 if not __import__('re').fullmatch('[a-f0-9]{40}',args.execution_commit):
  raise ValueError('Execution commit must be a full immutable 40-character Git SHA')
 manifest_raw=git('show',f'{SCOPE_MANIFEST_COMMIT}:{PREFIX}evidence-quality.json')
 if sha(manifest_raw)!=SCOPE_MANIFEST_SHA256:raise ValueError('Issue #1481 scope manifest whole-file pin mismatch')
 manifest=json.loads(manifest_raw)
 issue_pins={row['path']:row for row in manifest['baseline']['files']}
 archive_paths=[f'data/semantic-evidence/part-{i:02}.bin' for i in range(6)]
 source_registry=descriptor(args.execution_commit,'data/semantic-sources.json',issue_pins['data/semantic-sources.json'])
 registry=json.loads(git('show',f"{args.execution_commit}:data/semantic-sources.json"))
 archive_rows={x['path'].removeprefix(''):x for x in registry['archive_parts']}
 archive_pins=[]
 for path in archive_paths:
  key=path.removeprefix('data/')
  expected=archive_rows.get(key)
  if not expected:raise ValueError('Archive part absent from immutable semantic registry: '+path)
  row=descriptor(args.execution_commit,path,{'bytes':8388608 if path.endswith(('00.bin','01.bin','02.bin','03.bin','04.bin')) else 3658640,'sha256':expected['sha256']})
  archive_pins.append(row)
 sources=[]
 for path,row in issue_pins.items():sources.append(descriptor(args.execution_commit,path,row))
 for row in archive_pins:
  if row['path'] not in {x['path'] for x in sources}:sources.append(row)
 native_member=descriptor(args.execution_commit,PREFIX+'sources/aafc-ecoregions.native.geojson',
  {'bytes':2756674,'sha256':'a565563a6aef794df831dc9251fb4108018e20a4f0172acbc36b599f9b7f4abf'})
 if native_member['path'] not in {x['path'] for x in sources}:sources.append(native_member)
 runtime=descriptor(args.execution_commit,RUNTIME,verify_materialized=True)
 native_runtime=descriptor(args.execution_commit,NATIVE_RUNTIME,verify_materialized=True)
 native_checker=descriptor(args.execution_commit,NATIVE_CHECKER,verify_materialized=True)
 runtime_lock=json.loads(git('show',f'{args.execution_commit}:{RUNTIME}'))
 runtime_total=runtime_lock['total_bytes']
 native_lock=json.loads(git('show',f'{args.execution_commit}:{NATIVE_RUNTIME}'))
 native_runtime_total=native_lock['total_bytes']
 runner=descriptor(args.execution_commit,PREFIX+'run_source_phase.py',verify_materialized=True)
 code_rows=[descriptor(args.execution_commit,path,verify_materialized=True) for path in CODE]
 native_script=descriptor(args.execution_commit,NATIVE_SCRIPT,verify_materialized=True)
 all_rows={}
 for row in sources+code_rows+[runtime,native_runtime,native_checker,native_script]:
  if row['path'] in all_rows and all_rows[row['path']]!=row:raise ValueError('Conflicting whole-file pins')
  all_rows[row['path']]=row
 part_paths=[f'data/geography/part-{i}.json' for i in range(34)]+[
  'data/geography/source-restoration-additions.json','data/geography/macro-loose-ends-v5-additions.json']
 code_paths=[x['path'] for x in code_rows]
 def phase(name,vintage,entry,args,base_paths,out_names,decoded=0,scratch=0,out_reserve=1_000_000,predecessors=(),candidate_paths=(),required=()):
  return {'name':name,'vintage':vintage,'owned_path':'research/geography/arctic-seven-source-fit-20261008/',
   'entry_module':entry,'entry_args':args,'baseline_paths':list(dict.fromkeys(base_paths+[RUNTIME,NATIVE_RUNTIME])),
   'code_paths':code_paths,'modules':{'source_phase_runtime':PREFIX+'source_phase_runtime.py',
    'prepare_sources':PREFIX+'prepare_sources.py','scan_neighbors':PREFIX+'scan_neighbors.py',
   'reproduce_fit':PREFIX+'reproduce_fit.py','evidence.geometry':'scripts/evidence/geometry.py',
    'ellipsoidal_area':'scripts/ellipsoidal_area.py'},
   'required_import_roots':list(required),'decoded_source_bytes':decoded,
   'native_runtime_bytes':native_runtime_total,'runtime_bytes':runtime_total,
  'native_tools_lock_revalidation_bytes':native_runtime['bytes'],
   'scratch_reserved_bytes':scratch,'output_reserved_bytes':out_reserve,
   'output_names':list(out_names)+['execution-receipt.json'],'predecessors':list(predecessors),
   'candidate_paths':list(candidate_paths), 'kind':'python'}
 # Streamed native extraction has a smaller, separately pinned native runtime.
 native_phase={'name':'native-archive-extract','kind':'native-shell','vintage':'r10-native-extract',
  'owned_path':'research/geography/arctic-seven-source-fit-20261008/',
  'baseline_paths':archive_paths+['data/semantic-sources.json',PREFIX+'sources/aafc-ecoregions.native.geojson',NATIVE_RUNTIME],
  'code_paths':[NATIVE_SCRIPT,NATIVE_CHECKER],
  'decoded_source_bytes':162109440,'scratch_reserved_bytes':4*1024*1024,
  'output_reserved_bytes':65536,'output_names':['native-archive-extraction.json','execution-receipt.json'],
  'native_runtime_bytes':native_runtime_total,'archive_read_multiplicity':1,'registry_read_multiplicity':10}
 phases=[native_phase,
  phase('retired-context','r10-retired','prepare_sources',[],
   ['data/semantic-sources.json','coordination/engineering/eastern-two-gap-repair-20261007/input-index.json']+
   [f'coordination/engineering/eastern-two-gap-repair-20261007/inputs/i{i:03}.bin.gz' for i in range(47,54)]+
   [PREFIX+'sources/aafc-ecoregions.native.geojson'],
   ['source-custody-phase2.json','retired-member-context-phase2.json'],
   decoded=56672580,scratch=56672580,out_reserve=2*1024*1024,
   predecessors=[{'path':'research/geography/arctic-seven-source-fit-20261008/vintages/r10-native-extract/native-archive-extraction.json','alias':PREFIX+'native-archive-extraction.json','phase':'native-archive-extract','max_bytes':65536}],
   required=['gzip']),
 ]
 index=json.loads(git('show',f'{args.execution_commit}:data/world-index.json'))
 if len(index['parts'])!=36 or len(set(index['parts']))!=36:raise ValueError('Expected the complete 36-part immutable world index')
 for label,selected in zip('abcd',[index['parts'][i*9:(i+1)*9] for i in range(4)]):
  phases.append(phase('neighbor-scan-'+label,'r10-scan-'+label,'scan_neighbors',[label],
   ['data/world-index.json','coordination/engineering/eastern-two-gap-repair-20261007/run-two/full-four-family-context.json.gz']+
   ['data/'+x for x in selected],['neighbor-scan-'+label+'.json'],
   decoded=383582,scratch=64*1024*1024,out_reserve=8*1024*1024,required=['shapely']))
 fit_base=['data/world-index.json','data/hierarchy.json','data/geography/part-29.json',
  'data/regional-review/regional-review-a9f03b364bdefa4a/sources/aafc-terrestrial-ecoregions-v2.2.geojson',
  'data/regional-review/regional-review-a9f03b364bdefa4a/sources/aafc-ecoprovinces-baseline-arcgis-layer0.geojson',
  'coordination/engineering/eastern-two-gap-repair-20261007/run-two/full-four-family-context.json.gz',
  PREFIX+'sources/aafc-ecoregions.native.geojson']
 phases.append(phase('source-fit','r10-fit','reproduce_fit',[],fit_base,
  ['candidate-decisions.json','proposed-additions.geojson','positive-control.json','negative-control.json'],
  decoded=383582,scratch=40*1024*1024,out_reserve=24*1024*1024,
  predecessors=[
   {'path':'research/geography/arctic-seven-source-fit-20261008/vintages/r10-native-extract/native-archive-extraction.json','alias':PREFIX+'native-archive-extraction.json','phase':'native-archive-extract','max_bytes':65536},
   {'path':'research/geography/arctic-seven-source-fit-20261008/vintages/r10-retired/retired-member-context-phase2.json','alias':PREFIX+'retired-member-context-phase2.json','phase':'retired-context','max_bytes':2*1024*1024},
   {'path':'research/geography/arctic-seven-source-fit-20261008/vintages/r10-scan-a/neighbor-scan-a.json','alias':PREFIX+'neighbor-scan-a.json','phase':'neighbor-scan-a','max_bytes':2*1024*1024},
   {'path':'research/geography/arctic-seven-source-fit-20261008/vintages/r10-scan-b/neighbor-scan-b.json','alias':PREFIX+'neighbor-scan-b.json','phase':'neighbor-scan-b','max_bytes':2*1024*1024},
   {'path':'research/geography/arctic-seven-source-fit-20261008/vintages/r10-scan-c/neighbor-scan-c.json','alias':PREFIX+'neighbor-scan-c.json','phase':'neighbor-scan-c','max_bytes':2*1024*1024},
   {'path':'research/geography/arctic-seven-source-fit-20261008/vintages/r10-scan-d/neighbor-scan-d.json','alias':PREFIX+'neighbor-scan-d.json','phase':'neighbor-scan-d','max_bytes':2*1024*1024}],
  required=['shapely','pyproj','numpy']))
 plan={'version':1,'baseline_source_commit':BASELINE_SOURCE,'execution_commit':args.execution_commit,
  'cap_bytes':256*1024*1024,'receipt_reserve_bytes':4096,
  'original_scope_pins':[{'path':path,'bytes':row['bytes'],'sha256':row['sha256']} for path,row in issue_pins.items()],
  'baseline_files':list(all_rows.values()),'runtime':{'lock_path':RUNTIME,'lock_sha256':runtime['sha256']},
  'native_tools_lock_sha256':native_runtime['sha256'],
  'runner':runner,'candidate_scope':{'component_count':7,'world_index_part_count':36,'active_feature_count':49625},
  'phases':phases}
 raw=(json.dumps(plan,sort_keys=True,ensure_ascii=False,separators=(',',':'))+'\n').encode()
 target=ROOT/args.plan_output
 if target.is_symlink():raise ValueError('Phase plan destination must be ordinary')
 if target.exists():
  if target.read_bytes()!=raw:raise FileExistsError('Frozen phase plan differs; preserve it and use a fresh reviewed execution vintage')
 else:target.write_bytes(raw)
 print(json.dumps({'status':'phase-plan-built','execution_commit':args.execution_commit,'sha256':sha(raw),
  'baseline_pins':len(all_rows),'phase_count':len(phases),'phase_prospective_bytes':{
  p['name']:(sum(all_rows[x]['bytes'] for x in p['baseline_paths']+p['code_paths'])+
  len(raw)*(5 if p.get('kind')=='native-shell' else 1)+p.get('native_tools_lock_revalidation_bytes',0)+p.get('runtime_bytes',0)+p.get('native_runtime_bytes',0)+p['decoded_source_bytes']+
    p['scratch_reserved_bytes']+p['output_reserved_bytes']+
    sum(x.get('max_bytes',0)+20480 for x in p.get('predecessors',[]))+4096+
    (sum(all_rows[x]['bytes'] for x in archive_paths) if p.get('archive_read_multiplicity')==2 else 0)+
    (all_rows['data/semantic-sources.json']['bytes']*(p['registry_read_multiplicity']-1) if p.get('registry_read_multiplicity') else 0)+
    (2*sum(all_rows[x]['bytes'] for x in p['code_paths'])+all_rows[NATIVE_RUNTIME]['bytes'] if p.get('kind')=='native-shell' else 0))
   for p in phases},'native_shell_extract_required':True},sort_keys=True))

if __name__=='__main__':main()
