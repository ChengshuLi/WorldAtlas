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

def file_sha(p,guard):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  while True:
   guard();b=f.read(1<<20)
   if not b:break
   h.update(b)
 return h.hexdigest()

def load_json(spec,guard,limit=32<<20):
 need(isinstance(spec,dict) and set(spec)=={'path','sha256'},'invalid regional file pin')
 p=Path(spec['path']).resolve(strict=True);need(p.is_file() and file_sha(p,guard)==spec['sha256'],'regional file pin mismatch: '+str(p))
 with p.open('rb') as f:b=f.read(limit+1)
 need(len(b)<=limit,'regional JSON exceeds limit');return json.loads(b)

def modules_from_pins(code,policy,guard):
 required=['regional_rule','component_scan','replay_adapter','geonames_anchors','satellite_geodesic','regional_workflow','regional_group_convention','source_groups','adapter','live_driver','point_prototype','run_pair','land_archive_source','polygon_intersection']
 need(isinstance(code,dict) and set(code)==set(required),'regional runtime code pins incomplete')
 for name in required:
  s=code[name];need(isinstance(s,dict) and set(s)=={'path','sha256'},'invalid regional runtime pin')
  p=Path(s['path']).resolve(strict=True);need(p.is_file() and file_sha(p,guard)==s['sha256'],'regional runtime code mismatch: '+name)
  expected=policy['evidence']['runtime_code_sha256'].get(name+'.py')
  if expected:need(s['sha256']==expected,'regional reviewed code mismatch: '+name)
 need(code['run_pair']['sha256']==policy['evidence']['wgs84_run_pair_sha256'] and code['point_prototype']['sha256']==policy['evidence']['point_prototype_sha256'],'WGS84 implementation pin mismatch')
 mods={}
 for name in required:
  p=Path(code[name]['path']).resolve(strict=True);existing=sys.modules.get(name)
  if existing is not None:
   need(getattr(existing,'__file__',None) is not None and Path(existing.__file__).resolve()==p,'conflicting loaded regional module: '+name);mods[name]=existing;continue
  spec=importlib.util.spec_from_file_location(name,p);need(spec and spec.loader,'regional module unavailable: '+name)
  mod=importlib.util.module_from_spec(spec);sys.modules[name]=mod
  try:spec.loader.exec_module(mod)
  except BaseException:
   sys.modules.pop(name,None);raise
  mods[name]=mod
 return mods

def prepare(cfg,compiled,snapshot,reports,grid,inputs,mainland_roots,mixed_claims,guard,*,snapshot_sha256):
 """Resolve fresh reports and return claims, protected rows and audit evidence.

 cfg.pending_inventory_complete is an externally authenticated assertion, not
 something this helper can prove. False is permitted only for a profiling run,
 which must never be represented as final or accepted geography.
 """
 need(isinstance(cfg,dict) and set(cfg)=={'policy','policy_canonical_sha256','line','pending','pending_inventory_complete','profiling_standin','sources','code'},'invalid regional request')
 need(type(cfg['pending_inventory_complete']) is bool and type(cfg['profiling_standin']) is bool and (cfg['pending_inventory_complete'] or cfg['profiling_standin']),'incomplete pending inventory requires profiling label')
 policy=load_json(cfg['policy'],guard);line=load_json(cfg['line'],guard);pending=load_json(cfg['pending'],guard)
 need(isinstance(pending,list),'invalid pending inventory')
 need(policy.get('evidence',{}).get('decision_snapshot_sha256')==snapshot_sha256,'regional decision snapshot mismatch')
 mods=modules_from_pins(cfg['code'],policy,guard)
 from osgeo import ogr
 def inside(geometry,lon,lat):
  g=ogr.CreateGeometryFromJson(json.dumps(geometry));p=ogr.Geometry(ogr.wkbPoint);p.AddPoint_2D(lon,lat);return bool(g.Contains(p))
 w=mods['regional_workflow'];s=mods['component_scan'];deps={'research':w.research,'verified_line':mods['regional_rule'].verified_line,'scan':s.scan,'buffered_bounds':w.buffered_bounds,'resolve_feature_windows':mods['source_groups'].resolve_feature_windows,'apply_groups':mods['regional_group_convention'].apply_groups,'resolve_with_mixed_replay':mods['replay_adapter'].resolve_with_mixed_replay,'collect_runs':s.collect_runs,'apply_satellites':mods['satellite_geodesic'].apply_satellites,'extract':mods['land_archive_source'].extract,'intersect':mods['polygon_intersection'].intersect,'point_inside':inside,'component_at':s.component_at,'run_pair':mods['run_pair'].run_pair,'guard':guard,'mixed_claims':mixed_claims}
 resolved=mods['live_driver'].resolve_live(policy,compiled,snapshot,reports,grid,inputs,cfg['sources'],line,snapshot_sha256=snapshot_sha256,policy_canonical_sha256=cfg['policy_canonical_sha256'],mainland_roots=set(mainland_roots),pending_claims=pending,deps=deps)
 # The driver must compare its own pinned snapshot with this value, not trust
 # the policy alone. All source/group evidence stays in the output report.
 b=resolved['writer_bridge'];provenance={'policy':cfg['policy'],'line':cfg['line'],'pending':cfg['pending'],'pending_inventory_complete':cfg['pending_inventory_complete'],'profiling_standin':cfg['profiling_standin'],'code':cfg['code'],'sources':cfg['sources'],'decision_snapshot_sha256':policy['evidence']['decision_snapshot_sha256'],'policy_canonical_sha256':cfg['policy_canonical_sha256']}
 specs=[cfg['policy'],cfg['line'],cfg['pending'],*cfg['code'].values()]+[{'path':v['path'],'sha256':v['sha256']} for v in cfg['sources'].values()]
 def verify():
  for x in specs:need(file_sha(Path(x['path']).resolve(strict=True),guard)==x['sha256'],'regional input changed during run')
 return {'component_claims':b['component_claims'],'blocked_region_roots':b['blocked_region_roots'],'wrap_region_rows':mods['adapter'].protected_region_rows,'regional_result':resolved['regional_result'],'regional_proposal_trace':b['regional_proposal_trace'],'synthetic_affiliation_id':b['synthetic_affiliation_id'],'provenance':provenance,'input_paths':[x['path'] for x in specs]+[v['shapefile'] for v in cfg['sources'].values() if 'shapefile' in v],'verify':verify}
