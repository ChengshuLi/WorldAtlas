"""Opt-in regional bridge for the research mixed driver; never publishes a map.

The driver passes its freshly executed resolver reports directly to this hook.
Every dependency, policy, pending inventory, line and source is pinned. An
incomplete pending inventory is allowed only for explicitly labelled profiling.
The existing writer still retains baseline values for held roots.
"""
import hashlib,importlib.util,json,sys
from pathlib import Path

def need(ok,msg):
 if not ok:raise ValueError(msg)

def file_sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  while True:
   b=f.read(1<<20)
   if not b:break
   h.update(b)
 return h.hexdigest()

def load_json(spec,limit=32<<20):
 need(isinstance(spec,dict) and set(spec)=={'path','sha256'},'invalid regional file pin')
 p=Path(spec['path']).resolve(strict=True);need(p.is_file() and file_sha(p)==spec['sha256'],'regional file pin mismatch: '+str(p))
 with p.open('rb') as f:b=f.read(limit+1)
 need(len(b)<=limit,'regional JSON exceeds limit');return json.loads(b)

def load_pinned_module(name,path,digest):
 module_name=('_worldatlas_regional_'+name+'_'+digest) if name in ('run_pair','component_index','satellite_index','regional_runtime') else name
 p=Path(path).resolve(strict=True);existing=sys.modules.get(module_name)
 if existing is not None:
  need(getattr(existing,'__file__',None) is not None and Path(existing.__file__).resolve()==p,'conflicting loaded regional module: '+name);return existing
 spec=importlib.util.spec_from_file_location(module_name,p);need(spec and spec.loader,'regional module unavailable: '+name)
 mod=importlib.util.module_from_spec(spec);sys.modules[module_name]=mod
 try:spec.loader.exec_module(mod)
 except BaseException:
  sys.modules.pop(module_name,None);raise
 return mod

def modules_from_pins(code,policy):
 required=['regional_rule','component_scan','replay_adapter','geonames_anchors','satellite_geodesic','regional_workflow','regional_group_convention','source_groups','adapter','live_driver','point_prototype','run_pair','land_archive_source','polygon_intersection']
 need(isinstance(code,dict) and set(code)==set(required),'regional runtime code pins incomplete')
 for name in required:
  s=code[name];need(isinstance(s,dict) and set(s)=={'path','sha256'},'invalid regional runtime pin')
  p=Path(s['path']).resolve(strict=True);need(p.is_file() and file_sha(p)==s['sha256'],'regional runtime code mismatch: '+name)
  expected=policy['evidence']['runtime_code_sha256'].get(name+'.py')
  if expected:need(s['sha256']==expected,'regional reviewed code mismatch: '+name)
 need(code['run_pair']['sha256']==policy['evidence']['wgs84_run_pair_sha256'] and code['point_prototype']['sha256']==policy['evidence']['point_prototype_sha256'],'WGS84 implementation pin mismatch')
 mods={}
 for name in required:
  # WGS84 pair implementations may coexist with Stage 2's independently
  # pinned implementation. Load the regional implementation by its own
  # content-addressed module name rather than replacing a process-global name.
  mods[name]=load_pinned_module(name,code[name]['path'],code[name]['sha256'])
 return mods

def prepare(cfg,compiled,snapshot,reports,grid,inputs,mainland_roots,mixed_claims,*,snapshot_sha256):
 """Resolve fresh reports and return claims, protected rows and audit evidence.

 cfg.pending_inventory_complete is an externally authenticated assertion, not
 something this helper can prove. False is permitted only for a profiling run,
 which must never be represented as final or accepted geography.
 """
 required={'policy','policy_canonical_sha256','line','pending','pending_inventory_complete','profiling_standin','sources','code'}
 need(isinstance(cfg,dict) and required<=set(cfg) and set(cfg)<=required|{'runtime'},'invalid regional request')
 need(type(cfg['pending_inventory_complete']) is bool and type(cfg['profiling_standin']) is bool and (cfg['pending_inventory_complete'] or cfg['profiling_standin']),'incomplete pending inventory requires profiling label')
 policy=load_json(cfg['policy']);line=load_json(cfg['line']);pending=load_json(cfg['pending'])
 need(isinstance(pending,list),'invalid pending inventory')
 need(policy.get('evidence',{}).get('decision_snapshot_sha256')==snapshot_sha256,'regional decision snapshot mismatch')
 mixed_path=Path(getattr(mixed_claims,'__file__','')).resolve(strict=True);mixed_sha=policy['evidence'].get('mixed_claims_sha256');need(mixed_path.is_file() and file_sha(mixed_path)==mixed_sha,'regional mixed claims code mismatch')
 mods=modules_from_pins(cfg['code'],policy)
 from osgeo import ogr
 def inside(geometry,lon,lat):
  g=ogr.CreateGeometryFromJson(json.dumps(geometry));p=ogr.Geometry(ogr.wkbPoint);p.AddPoint_2D(lon,lat);return bool(g.Contains(p))
 w=mods['regional_workflow'];s=mods['component_scan'];deps={'research':w.research,'verified_line':mods['regional_rule'].verified_line,'scan':s.scan,'buffered_bounds':w.buffered_bounds,'resolve_feature_windows':mods['source_groups'].resolve_feature_windows,'apply_groups':mods['regional_group_convention'].apply_groups,'resolve_with_mixed_replay':mods['replay_adapter'].resolve_with_mixed_replay,'collect_runs':s.collect_runs,'apply_satellites':mods['satellite_geodesic'].apply_satellites,'extract':mods['land_archive_source'].extract,'intersect':mods['polygon_intersection'].intersect,'point_inside':inside,'component_at':s.component_at,'run_pair':mods['run_pair'].run_pair,'mixed_claims':mixed_claims}
 runtime=None;runtime_specs=[]
 if 'runtime' in cfg:
  runtime_code=cfg['runtime'];need(isinstance(runtime_code,dict) and set(runtime_code)=={'component_index','satellite_index','regional_runtime'},'invalid regional runtime inventory')
  for name in ('component_index','satellite_index','regional_runtime'):
   spec=runtime_code[name];need(isinstance(spec,dict) and set(spec)=={'path','sha256'},'invalid equivalent runtime pin')
   path=Path(spec['path']).resolve(strict=True);need(path.is_file() and file_sha(path)==spec['sha256'],'equivalent runtime code mismatch: '+name)
   mods[name]=load_pinned_module(name,path,spec['sha256']);runtime_specs.append(spec)
  runtime=mods['regional_runtime'].prepare(mods,inputs,grid,runtime_code);deps.update(runtime['dependencies'])
 resolved=mods['live_driver'].resolve_live(policy,compiled,snapshot,reports,grid,inputs,cfg['sources'],line,snapshot_sha256=snapshot_sha256,policy_canonical_sha256=cfg['policy_canonical_sha256'],mainland_roots=set(mainland_roots),pending_claims=pending,deps=deps)
 # The driver must compare its own pinned snapshot with this value, not trust
 # the policy alone. All source/group evidence stays in the output report.
 b=resolved['writer_bridge'];provenance={'policy':cfg['policy'],'line':cfg['line'],'pending':cfg['pending'],'pending_inventory_complete':cfg['pending_inventory_complete'],'profiling_standin':cfg['profiling_standin'],'code':cfg['code'],'sources':cfg['sources'],'decision_snapshot_sha256':policy['evidence']['decision_snapshot_sha256'],'policy_canonical_sha256':cfg['policy_canonical_sha256']}
 if runtime:provenance['equivalent_runtime']=runtime['provenance']
 specs=[cfg['policy'],cfg['line'],cfg['pending'],{'path':str(mixed_path),'sha256':mixed_sha},*cfg['code'].values(),*runtime_specs]+[{'path':v['path'],'sha256':v['sha256']} for v in cfg['sources'].values()]
 def verify():
  if runtime:runtime['verify']()
  for x in specs:need(file_sha(Path(x['path']).resolve(strict=True))==x['sha256'],'regional input changed during run')
 return {'component_claims':b['component_claims'],'blocked_region_roots':b['blocked_region_roots'],'wrap_region_rows':mods['adapter'].protected_region_rows,'regional_result':resolved['regional_result'],'regional_proposal_trace':b['regional_proposal_trace'],'synthetic_affiliation_id':b['synthetic_affiliation_id'],'provenance':provenance,'input_paths':[x['path'] for x in specs]+[v['shapefile'] for v in cfg['sources'].values() if 'shapefile' in v],'verify':verify}
