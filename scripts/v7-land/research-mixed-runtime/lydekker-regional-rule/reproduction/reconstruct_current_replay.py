#!/usr/bin/env python3
"""Reconcile individually completed resolver reports to the current snapshot.

Read-only research: archived resolutions, not a fresh re-execution of all sources.
All roots are scoped to the pinned physical generation. No grid is built.
"""
import collections,hashlib,importlib.util,json,sys,zipfile
from pathlib import Path
R=Path.cwd();D=R/'regional-lydekker-rule-work'; sys.path.insert(0,str(D))
from component_scan import component_at
P=R/'pr4-mixed-runtime-preserve-20261105/scripts/v7-land/research-mixed-runtime/stage3-mixed-leeward-full-20261105'

def loadmod(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
mixed=loadmod('mixed',R/'aegean-archive-containment-integrated-20261105/group-label-multipolygon-prototype/mixed_claims.py');contract=loadmod('contract',P/'decision_contract.py')
def H(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(8<<20),b''):h.update(b)
 return h.hexdigest()
def J(p):return json.loads(Path(p).read_bytes())
pins={
'bacan-nusaraloid-research-20261105/snapshot163.raw.json':'bbc672cd2741aaca309adc91d6a018faaee683f67ab34ab95cf71f367d964e66',
'indonesia-bacan-cluster-20261105/snapshot164.raw.json':'a7066f7d54ecfb202f32109f0bfe2900675107185ae310b1d74cf887df860c76',
'lydekker-line-research-20261105/snapshot165.raw.json':'6c9a21945dbc04450e4e45ede5e3dd01ef2879308a78d2c43552e889873d0b80',
'bacan-group-inventory-20261105/snapshot166.raw.json':'62e64497831a6769738594b8fef9c61786eb78f4479de3d87fbc29892522f065',
 'tobelo-whole-group-20261105/snapshot167.raw.json':'8d07f6925fe69463c262282bda0d166f5b04c58cdf1649f391cb39c48ff1ce85',
'shared-regional-replay-20261105/snapshot168.raw.json':'0a473f7c3f8fa2278db9edc67efc91e7854fa7bb6bd217b8c3e55615127c058f',
'kai-tayandu-group-20261105/snapshot169.raw.json':'6d111e78b43de4562d0f6bfad6284dcce9b8c10b6e1be2806a4797b8fc33f8fa',
'shared-regional-replay-20261105/snapshot170.raw.json':'30d04b428b5b20f626410d7c349a83363fa13dd2f99b87aa59cfdb3aa26625e1',
'combined-draft163-admin-output-20261105/report.json':'45b4e2930b95e7cef396c410a090719ae9f8908126c55fba203320619f7fb8d2',
'lydekker-kokara-preview165-retry-output-20261105/report.json':'c37bcb0752711892033cce936a287598a4160d78acb8d6826b64d376541b7594',
'indonesia-bacan-cluster-20261105/resolver-actual164.json':'eb94536a33f6d684edb902df93f4a259f621d1a6cef6758b0ffc64b315c43722',
'bacan-group-inventory-20261105/resolver-actual166.json':'3b0ba87a5f420c168ee02dc1b27c8bce8b2658d553f87fdc5a40f5d3a7eb00aa',
'tobelo-whole-group-20261105/resolver-actual167-v3.json':'09302cc2a21d8b65459474e962af9cf4e89abfc1dbbc1c0f9f13cc56abe81715',
'shared-regional-replay-20261105/resolver-actual168.json':'0dbb1cc003ad200b59f13374c2ad8181a2d4b20925133586969a54f74b7d1a11',
'shared-regional-replay-20261105/resolver-joronga-actual170.json':'410b936f019bf44d09776e43a9edbe96baf957a4c89c4bc4898e9bd4ba18ff3a',
'kai-tayandu-group-20261105/resolver-actual169.json':'7c958a9ed3b565452ced091bb4bd7fd407750d8891f1671b0c9876470254cc1d',
'fresh-witness-output-20261104/resolution.json':'27ec973caf3eedb267e2c0277a710dceef04254075f81b689f5762d513d88ea5',
'indonesia-geonames-research-20261105/r2-readback.zip':'2a1966f22f1eda5b099270b8382b93fe347a81b3f858b891349da7d4c9fe3718'}
assert all(H(R/p)==h for p,h in pins.items());current=J(R/'shared-regional-replay-20261105/snapshot170.raw.json')
# Earlier selected rows and all of their source references remain byte-equivalent
# semantically, apart from the expanded Joronga affiliation, resolved at 170.
def norm(o):
 if isinstance(o,dict):return {k:norm(v) for k,v in o.items() if k!='decision_revision'}
 if isinstance(o,list):return [norm(x) for x in o]
 return o
def key(o):return json.dumps(norm(o),sort_keys=True,separators=(',',':'))
for i in range(7):
 old=J(R/list(pins)[i]); assert old['decision_revision']['id'].endswith(str(163+i))
 for k,v in old.items():
  if isinstance(v,list):
   if k=='affiliations' and i>=5:v=[x for x in v if x['affiliation_id']!='joronga-study-named-source-group-asia']
   assert not (collections.Counter(map(key,v))-collections.Counter(map(key,current[k]))), (i,k)
# Compile current selected policy against pinned baseline and supported methods.
cfg=J(R/'combined-draft163-admin-input-20261105/config.json');stage=cfg['stage2']
for k in ('snapshot','report'):assert H(stage[k]['path'])==stage[k]['sha256']
base=J(stage['snapshot']['path']); report=J(stage['report']['path'])
methods={'geonames_zip_line_side_component_v1','osm_admin_group_containment_v1','osm_reef_envelope_component_containment_v1','source_point_named_region_component_v1','osm_api_node_named_region_component_v1','osm_api_island_node_group_component_v1','geonames_zip_island_named_region_component_v1','geonames_zip_named_list1_component_v1','geonames_zip_airport_named_region_component_v1','component_intersection_v1','osm_relation_component_intersection_v1','component_containment_v1','component_containment_excluding_source_v1','osm_archipelago_component_intersection_v1','osm_archipelago_component_containment_v1','osm_archipelago_anchored_rings_intersection_v1','osm_way_component_containment_v1','osm_relation_component_containment_v1','osm_land_archive_component_intersection_v1','osm_land_archive_component_containment_v1','label_contained_ecoregion_contact_v1'}
compiled=contract.compile_policy(current,base,report,cfg['policy_pins'],methods)
old=J(R/'combined-draft163-admin-output-20261105/report.json'); reports=[]
for typ in ('point_resolution','polygon_resolution','bering_resolution'):
 rep=old[typ].copy();rep['revision']=compiled['revision']; reports.append(rep)
added=[]
for path in ('indonesia-bacan-cluster-20261105/resolver-actual164.json','bacan-group-inventory-20261105/resolver-actual166.json','tobelo-whole-group-20261105/resolver-actual167-v3.json','kai-tayandu-group-20261105/resolver-actual169.json','shared-regional-replay-20261105/resolver-joronga-actual170.json'):
 x=J(R/path);assert x['status'].startswith('passed') and x.get('synthetic') is not True;added.append(x['claim'])
x=J(R/'shared-regional-replay-20261105/resolver-actual168.json');assert x['status'].startswith('passed');added += [c for aid,c in x['claims'].items() if aid!='joronga-study-named-source-group-asia']
assert len(added)==8 and len({x['affiliation_id'] for x in added})==8
reports[1]['claims']=reports[1]['claims']+added
pt=J(R/'lydekker-kokara-preview165-retry-output-20261105/report.json');aid='list1-moluccas-geonames-island-1639785-asia';match=[c for c in pt['claims'] if c['affiliation_id']==aid];assert len(match)==1
# Independently recheck exact GeoNames source record and component witness.
c=match[0];z=zipfile.ZipFile(R/'indonesia-geonames-research-20261105/r2-readback.zip');lines=[l.decode().split('\t') for l in z.read('ID.txt').splitlines() if l.startswith(b'1639785\t')];assert len(lines)==1 and lines[0][1]=='Pulau Kokara Besar' and lines[0][6:9]==['T','ISL','ID'] and [float(lines[0][5]),float(lines[0][4])]==c['geonames_extraction']['geometry']['coordinates']
rows={'path':str(R/'fresh-components-output-20261104/rows.u32le'),'sha256':'4beda178bfc7beeb2d30cbdfa5901a48f9a41bb82c69e534d4c8cddfdb09aea7'};runs={'path':str(R/'fresh-components-output-20261104/runs.u32le'),'sha256':'18d7f36fa22c5728662cdd40487bf684108da030c074fec6d22ac378d0df0961'};grid=pt['grid'];assert component_at(rows,runs,grid,*c['geonames_extraction']['geometry']['coordinates'])==c['component_id']
reports[0]['claims']=reports[0]['claims']+match
w=J(R/'fresh-witness-output-20261104/resolution.json');assert w['input_sha256']['component_rows']==rows['sha256'] and w['input_sha256']['component_runs']==runs['sha256'];protected={x['component_id_current_generation_only'] for x in w['groups'] if x['role']=='mainland' or x['group_id']=='sentinel-new-guinea'}
claims=mixed.combine(compiled,current,reports,protected)
assert len(compiled['affiliation_ids'])==384 and all(H(R/p)==h for p,h in pins.items())
out={'status':'current-snapshot-archived-resolver-reconciliation-research-only','revision':compiled['revision'],'snapshot_sha256':pins['shared-regional-replay-20261105/snapshot170.raw.json'],'compiled':compiled,'reports':reports,'protected_roots':sorted(protected),'claims':claims,'input_sha256':pins,'limitations':['Composes previously executed resolver reports after checking selected-row and source-reference continuity; not a fresh execution of every source resolver.','The current unresolved pending-group set has not been fully authenticated.','Source and physical mask may share lineage; named polygon and group interpretation remains subject to source limitations.','No geographic decision selection or map build.']}
p=D/'reconstructed-current-selected170.json';assert not p.exists();p.write_text(json.dumps(out,sort_keys=True,indent=2)+'\n');print('claims',len(claims),'affiliations',len(compiled['affiliation_ids']),'sha256',H(p))
