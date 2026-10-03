#!/usr/bin/env python3
"""Screen exact shared source/current edge segments for all issue 491 locations."""
import gzip,hashlib,json,pathlib,struct
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[2]
scope=json.loads((HERE/'scope.json').read_text());assigned=set(scope['member_location_ids'])
raw=gzip.decompress((HERE.parent/'regional-review-b2e551685bf2e064/sources/geoboundaries-COL-ADM2-2020.geojson.gz').read_bytes());doc=json.loads(raw)
byshape={f['properties']['shapeID']:f for f in doc['features']}
allfeatures={};parts=json.loads((ROOT/'data/world-index.json').read_text())['parts']
for name in parts:
 for f in json.loads((ROOT/'data'/name).read_text())['features']:allfeatures[f['properties']['id']]=f
sel={i:allfeatures[i] for i in assigned}; loc_by_shape={f['properties']['metadata']['original_id']:i for i,f in allfeatures.items() if f['properties'].get('metadata',{}).get('source_id')=='gb:COL:ADM2'}
shape_by_location={i:sel[i]['properties']['metadata']['original_id'] for i in assigned}
def polygons(g):return [g['coordinates']] if g['type']=='Polygon' else g['coordinates']
def edge(a,b):
 if a==b:return None
 lo,hi=(a,b) if a<b else (b,a)
 return struct.pack('>4d',lo[0],lo[1],hi[0],hi[1])
def edges(g):
 for poly in polygons(g):
  for ring in poly:
   for j,a in enumerate(ring):
    k=edge(tuple(a),tuple(ring[(j+1)%len(ring)]))
    if k is not None:yield k
source_targets={}
for lid in sorted(assigned):
 sid=shape_by_location[lid]
 for k in set(edges(byshape[sid]['geometry'])):source_targets.setdefault(k,set()).add(lid)
source_neighbors={i:set() for i in assigned}
for f in doc['features']:
 sid=f['properties']['shapeID']; neighbor_sid=None
 for k in edges(f['geometry']):
  for lid in source_targets.get(k,()):
   if shape_by_location[lid]!=sid:source_neighbors[lid].add(sid)
current_targets={}
for lid in sorted(assigned):
 for k in set(edges(sel[lid]['geometry'])):current_targets.setdefault(k,set()).add(lid)
current_neighbors={i:set() for i in assigned}; current_meta={}
for fid,f in allfeatures.items():
 p=f['properties'];matched=set()
 for k in edges(f['geometry']):matched.update(current_targets.get(k,()))
 if matched:
  current_meta[fid]={'name':p['name'],'parent_id':p.get('parent_id'),'source_id':p.get('metadata',{}).get('source_id')}
  for lid in matched:
   if fid!=lid:current_neighbors[lid].add(fid)
rows={};pairs_source=set();pairs_current=set()
for lid in sorted(assigned):
 src_ids=source_neighbors[lid]; src_atlas={loc_by_shape[s] for s in src_ids if s in loc_by_shape}; cur_ids=current_neighbors[lid]
 src_inside=src_atlas & assigned; cur_inside=cur_ids & assigned
 for n in src_inside:pairs_source.add(tuple(sorted((lid,n))))
 for n in cur_inside:pairs_current.add(tuple(sorted((lid,n))))
 rows[lid]={'name':sel[lid]['properties']['name'],'source_neighbor_shape_ids':sorted(src_ids),'source_neighbor_atlas_ids':sorted(src_atlas),'current_shared_edge_neighbor_ids':sorted(cur_ids),'current_external_neighbors':[{'id':n,**current_meta[n]} for n in sorted(cur_ids) if n not in assigned],'assigned_internal_source_neighbors':sorted(src_inside),'assigned_internal_current_neighbors':sorted(cur_inside),'assigned_internal_neighbor_graph_difference':{'source_missing_in_current':sorted(src_inside-cur_inside),'current_missing_in_source':sorted(cur_inside-src_inside)}}
result={'issue':491,'method':{'source':'Exact shared undirected consecutive coordinate segments in all 1,122 retained geoBoundaries ADM2 source features; report immediate neighbors for the 190 assigned sourceIDs.','current':'Exact shared undirected consecutive coordinate segments in current Atlas polygons; scan all world-index features to identify every exact-segment contact with the 194 assigned polygons.','interpretation':'This detects exact common segments only. It can miss shared borders represented with different vertex splits, contact only at points, unsplit overlaps, or water/island relationships. A graph difference is a candidate for review, not proof of a boundary error.'},'source_uncompressed_sha256':hashlib.sha256(raw).hexdigest(),'assigned_count':len(assigned),'whole_colombia_source_count':len(doc['features']),'whole_atlas_location_count':len(allfeatures),'source_assigned_internal_neighbor_pair_count':len(pairs_source),'current_assigned_internal_neighbor_pair_count':len(pairs_current),'assigned_internal_pair_graph_differences':len(pairs_source.symmetric_difference(pairs_current)),'source_pairs_missing_current':[list(x) for x in sorted(pairs_source-pairs_current)],'current_pairs_missing_source':[list(x) for x in sorted(pairs_current-pairs_source)],'per_location':rows,'limitations':['Segment equality is an exact-coordinate screen, not a full polygon overlay or shared-boundary certification.','Current adjacent-unit findings are context only; no parent, geometry or neighboring region is changed.','The region-wide shared edge network and any cross-region consistency claim remain for #489/affected owners.']}
(HERE/'neighbor-screen.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ('assigned_count','whole_colombia_source_count','whole_atlas_location_count','source_assigned_internal_neighbor_pair_count','current_assigned_internal_neighbor_pair_count','assigned_internal_pair_graph_differences')},indent=2))
