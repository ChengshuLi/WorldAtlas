#!/usr/bin/env python3
"""Compare exact source/current contacts across Bolivia's full 117-location scope."""
import gzip,hashlib,json,pathlib,struct
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[2]
scope=json.loads((HERE/'scope.json').read_text()); assigned=set(i for i in scope['member_location_ids'] if i.startswith('gb:BOL:ADM2:') or i.startswith('atlas:physical:'))
raw=gzip.decompress((HERE/'sources/geoboundaries-BOL-ADM2-2015.geojson.gz').read_bytes());doc=json.loads(raw); byshape={f['properties']['shapeID']:f for f in doc['features']}
allfeatures={}; parts=json.loads((ROOT/'data/world-index.json').read_text())['parts']
for name in parts:
 for f in json.loads((ROOT/'data'/name).read_text())['features']:allfeatures[f['properties']['id']]=f
sel={i:allfeatures[i] for i in assigned};
if len(sel)!=117:raise SystemExit(f'expected exact 117 Bolivia location scope, got {len(sel)}')
def polygons(g):return [g['coordinates']] if g['type']=='Polygon' else g['coordinates']
def edge(a,b):
 if a==b:return None
 lo,hi=(a,b) if a<b else (b,a);return struct.pack('>4d',lo[0],lo[1],hi[0],hi[1])
def edges(g):
 for poly in polygons(g):
  for ring in poly:
   for j,a in enumerate(ring):
    k=edge(tuple(a),tuple(ring[(j+1)%len(ring)]))
    if k is not None:yield k
# Map each original administrative province source ID to its one current unit or its ecoregion shards.
source_to_current={sid:[] for sid in byshape}
for fid,f in allfeatures.items():
 p=f['properties'];m=p.get('metadata',{})
 if m.get('source_id')=='gb:BOL:ADM2':source_to_current.setdefault(m.get('original_id'),[]).append(fid)
 for sid in m.get('source_member_ids',[]):
  if sid.startswith('gb:BOL:ADM2:'):source_to_current.setdefault(sid.rsplit(':',1)[1],[]).append(fid)
if any(not source_to_current.get(sid) for sid in byshape):raise SystemExit('a source ADM2 predecessor lacks a current direct/replacement ID')
source_targets={}
for sid,f in byshape.items():
 for k in set(edges(f['geometry'])):source_targets.setdefault(k,set()).add(sid)
source_neighbors={sid:set() for sid in byshape}
for f in doc['features']:
 sid=f['properties']['shapeID']
 for k in edges(f['geometry']):
  for n in source_targets.get(k,()):
   if sid!=n:source_neighbors[sid].add(n)
source_pairs=set()
for sid,ns in source_neighbors.items():
 for n in ns:source_pairs.add(tuple(sorted((sid,n))))
shape_for_current={}
for sid,ids in source_to_current.items():
 for i in ids:shape_for_current[i]=sid
current_targets={}
for lid in sorted(assigned):
 for k in set(edges(sel[lid]['geometry'])):current_targets.setdefault(k,set()).add(lid)
current_neighbors={i:set() for i in assigned}; current_meta={}; candidates={}
for fid,f in allfeatures.items():
 p=f['properties']; matched=set()
 for k in edges(f['geometry']):matched.update(current_targets.get(k,()))
 if matched:
  current_meta[fid]={'name':p['name'],'parent_id':p.get('parent_id'),'source_id':p.get('metadata',{}).get('source_id'),'metadata':p.get('metadata',{})}
  for lid in matched:
   if fid!=lid:current_neighbors[lid].add(fid)
current_pairs=set(); coarse_current=set()
for lid,ns in current_neighbors.items():
 ls=shape_for_current.get(lid)
 for n in ns:
  if n in assigned:
   current_pairs.add(tuple(sorted((lid,n))))
  nsid=shape_for_current.get(n)
  if ls and nsid and ls!=nsid:coarse_current.add(tuple(sorted((ls,nsid))))
rows={};
for lid in sorted(assigned):
 p=sel[lid]['properties'];m=p.get('metadata',{}); sid=(m.get('original_id') if m.get('source_id')=='gb:BOL:ADM2' else (m.get('source_member_ids') or [''])[0].rsplit(':',1)[-1])
 direct=sorted(n for n in current_neighbors[lid] if n in assigned)
 rows[lid]={'name':p['name'],'source_predecessor_id':sid,'source_predecessor_name':byshape[sid]['properties']['shapeName'],'source_predecessor_neighbors':sorted(source_neighbors[sid]),'current_exact_segment_neighbors':direct,'current_external_neighbors':[{'id':n,**current_meta[n]} for n in sorted(current_neighbors[lid]) if n not in assigned],'interpretation':'For physical ecoregion fragments, source neighbor list is the full predecessor province context and does not assert every listed neighbor touches this fragment; use derived-portion overlay and current per-fragment contacts for unit-specific assessment.' if lid.startswith('atlas:physical:') else 'Exact consecutive-coordinate segment graph; a missing exact segment is a screen lead, not a boundary correction.'}
result={'issue':490,'method':{'source':'Exact consecutive shared segments among all 110 retained 2015 BOL ADM2 features.','current':'Exact consecutive shared segments for every current feature in the complete 117-location Bolivia area; scan all 49,625 Atlas features for external contacts.','source_to_current':'The 108 directly matched province features map one-to-one; original Cordillera and Velasco features map to their 5 and 4 named physical-region portions respectively.','coarse_graph':'Compare source province neighbor graph with current adjacency after mapping every portion back to the two original province IDs; fragment-internal adjacencies are excluded from this administrative-level comparison and assessed separately by derived-portion audit.','limits':'Exact coordinate segmentation can miss near-coincident/simplified edges or mismatched vertex partitions. This screen does not certify cross-border sources, water/island completeness or whole-region adjacency.'},'source_sha256':hashlib.sha256(raw).hexdigest(),'assigned_count':len(assigned),'source_admin_count':len(doc['features']),'current_world_feature_count':len(allfeatures),'source_internal_neighbor_pair_count':len(source_pairs),'current_exact_internal_location_pair_count':len(current_pairs),'source_admin_coarse_pairs':len(source_pairs),'current_admin_coarse_pairs':len(coarse_current),'coarse_graph_difference_count':len(source_pairs.symmetric_difference(coarse_current)),'source_pairs_missing_current':[list(x) for x in sorted(source_pairs-coarse_current)],'current_pairs_missing_source':[list(x) for x in sorted(coarse_current-source_pairs)],'exact_internal_current_pairs':len(current_pairs),'per_location':rows,'limitations':['BOL source files cover 2015 ADM2 province features only and are not an official current cross-border land baseline.','The nine physical fragments have no administrative predecessor-level exact source geometry; their individual named physical adjacency is compared in derived-portion-audit.json.','A graph equality does not prove shared-border precision or land/island completeness.']}
(HERE/'neighbor-screen-bolivia.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:result[k] for k in ('assigned_count','source_admin_count','source_internal_neighbor_pair_count','current_exact_internal_location_pair_count','source_admin_coarse_pairs','current_admin_coarse_pairs','coarse_graph_difference_count','source_pairs_missing_current','current_pairs_missing_source')},ensure_ascii=False,indent=2))
