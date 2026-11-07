#!/usr/bin/env python3
"""Reconstruct the selected OSM main-stream route; retain the reviewed north.

This is a research audit, not a full raw-source derivation or a selection update.
"""
import argparse,collections,hashlib,json,math,xml.etree.ElementTree as ET
from pathlib import Path

def sha(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def geom_sha(g):return hashlib.sha256(json.dumps(g,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def reconstruct(snapshot,osm,river_start):
 found=[b for b in snapshot['mainland_boundaries'] if b.get('boundary_id')=='ural_kara_coast_to_caspian' and b.get('execution_status')=='selected_for_research']
 if len(found)!=1:raise ValueError('selected boundary missing or ambiguous')
 b=found[0];g=b['geometry'];ref=g['coordinates']
 if b.get('decision_revision')!=snapshot.get('decision_revision',{}).get('id') or b.get('coordinate_reference')!='OGC:CRS84' or b.get('geometry_hash_method')!='binary64-sorted-compact-geojson-v1':raise ValueError('unsupported selected revision, CRS or hash method')
 source_id='osm-ural-river-relation-214415-full';version='snapshot-2026-11-05-v122-89cef99ad92b'
 links=[x for x in b.get('provenance',{}).get('source_refs',[]) if x.get('source_id')==source_id and x.get('version')==version]
 sources=[x for x in snapshot.get('sources',[]) if x.get('source_id')==source_id and x.get('version')==version]
 if len(links)!=1 or len(sources)!=1 or sha(osm)!=sources[0].get('sha256') or Path(osm).stat().st_size!=sources[0].get('size_bytes'):raise ValueError('OSM input does not match selected source link')
 if g.get('type')!='LineString' or geom_sha(g)!=b['geometry_sha256']:raise ValueError('selected geometry checksum mismatch')
 if type(river_start) is not int or not 1<=river_start<len(ref)-1:raise ValueError('invalid reviewed river start')
 root=ET.parse(osm).getroot();rels=[r for r in root.findall('relation') if r.get('id')=='214415']
 if len(rels)!=1:raise ValueError('missing or ambiguous relation 214415')
 if rels[0].get('version')!='122':raise ValueError('unexpected relation version')
 members=[m.get('ref') for m in rels[0].findall('member') if m.get('type')=='way' and m.get('role')=='main_stream']
 if not members or len(members)!=len(set(members)):raise ValueError('missing or duplicate main-stream ways')
 nodes=root.findall('node');ways=root.findall('way');nd={n.get('id'):n for n in nodes};wd={w.get('id'):w for w in ways}
 if len(nd)!=len(nodes) or len(wd)!=len(ways):raise ValueError('duplicate node or way id')
 adj=collections.defaultdict(list);edges=set()
 for wid in members:
  if wid not in wd:raise ValueError('missing main-stream way')
  ids=[n.get('ref') for n in wd[wid].findall('nd')]
  if len(ids)<2 or any(x not in nd for x in ids):raise ValueError('missing main-stream node')
  for a,z in zip(ids,ids[1:]):
   edge=tuple(sorted((a,z)))
   if a==z or edge in edges:raise ValueError('duplicate or degenerate main-stream edge')
   edges.add(edge);adj[a].append(z);adj[z].append(a)
 ends=[n for n,v in adj.items() if len(v)==1]
 if len(ends)!=2 or any(len(v)>2 for v in adj.values()):raise ValueError('main-stream is not a single unbranched chain')
 def point(n):
  v=[float(nd[n].get('lon')),float(nd[n].get('lat'))]
  if not all(math.isfinite(x) for x in v) or not (-180<=v[0]<180 and -90<=v[1]<=90):raise ValueError('invalid WGS84 coordinate')
  return v
 start=[n for n in ends if point(n)==ref[river_start]]
 if len(start)!=1:raise ValueError('reviewed river start is not a unique OSM endpoint')
 path=[];previous=None;current=start[0]
 while current is not None:
  path.append(current)
  if len(path)>len(adj):raise ValueError('cycle in main stream')
  nxt=[n for n in adj[current] if n!=previous];previous,current=current,(nxt[0] if len(nxt)==1 else None)
 if len(path)!=len(adj) or len(set(path))!=len(adj) or len(edges)!=len(path)-1:raise ValueError('disconnected or cyclic main stream')
 river=[point(n) for n in path]
 springs=[x.get('ref') for x in rels[0].findall('member') if x.get('type')=='node' and x.get('role')=='spring'];mouths=[x.get('ref') for x in rels[0].findall('member') if x.get('type')=='node' and x.get('role')=='mouth']
 if len(springs)!=1 or springs[0]!=path[0] or len(mouths)!=1 or mouths[0] not in path:raise ValueError('OSM spring/mouth roles are missing or inconsistent with the route')
 import pyproj
 geod=pyproj.Geod(ellps='WGS84');mi=path.index(mouths[0]);downstream=math.fsum(geod.inv(*a,*z)[2] for a,z in zip(river[mi:],river[mi+1:]))
 if not math.isfinite(downstream):raise ValueError('invalid WGS84 segment distance')
 hybrid={'type':'LineString','coordinates':ref[:river_start]+river};same=hybrid==g
 return hybrid,{'schema':'ural-hybrid-river-reconstruction-v1','status':'partial-research-only','publishable':False,'selected_geometry_sha256':b['geometry_sha256'],'candidate_geometry_sha256':geom_sha(hybrid),'matches_selected_geometry':same,'river_start_zero_based':river_start,'retained_northern_vertices':river_start,'osm_main_stream_vertices':len(river),'osm_main_stream_edges':len(edges),'osm_main_stream_way_count':len(members),'relation_version':rels[0].get('version'),'source_id':source_id,'source_version':version,'source_r2_bucket':sources[0]['r2_bucket'],'source_r2_key':sources[0]['r2_key'],'osm_start_node_id':path[0],'osm_end_node_id':path[-1],'tagged_mouth_node_id':mouths[0],'tagged_mouth_route_index_zero_based':mi,'tagged_mouth_lonlat':river[mi],'downstream_edge_count':len(river)-mi-1,'downstream_wgs84_geodesic_segment_sum_m':downstream,'distance_method':'WGS84 inverse geodesic per consecutive source vertex pair; summed using math.fsum','pyproj_version':pyproj.__version__,'proj_version':pyproj.proj_version_str,'retained_north_last_coordinate':ref[river_start-1],'osm_start_coordinate':river[0],'osm_end_coordinate':river[-1],'contains_ural_caspian_canal_way_977035398':'977035398' in members,'join_policy':'Retain selected northern vertices and existing connecting edge; use the selected river start only to orient the source main-stream chain.','limitations':['Northern divide, terrain-derived gaps, spring connector and connecting edge remain retained selected geometry, not reconstructed from raw sources.','Current OSM capture is research evidence; it does not establish historical source bytes, the principal headwater, or geographic correctness. The main-stream route includes the Ural-Caspian canal and the mapped mouth-role discrepancy is unresolved.','Caspian closure and raster cell classification require separate validation.','The supplied selection attestation is hash-pinned but must be independently authenticated and refreshed before integration.','Downstream length sums WGS84 geodesic segments between source vertices; it approximates the coordinate-linear path and has no formal error bound.']}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--snapshot',required=True);p.add_argument('--snapshot-sha256',required=True);p.add_argument('--osm',required=True);p.add_argument('--osm-sha256',required=True);p.add_argument('--river-start',required=True,type=int);p.add_argument('--selection-attestation',required=True);p.add_argument('--selection-attestation-sha256',required=True);p.add_argument('--report',required=True);p.add_argument('--geometry-output');a=p.parse_args()
 for f,h in ((a.snapshot,a.snapshot_sha256),(a.osm,a.osm_sha256),(a.selection_attestation,a.selection_attestation_sha256)):
  if sha(f)!=h:raise ValueError('input checksum mismatch: '+f)
 with open(a.snapshot) as f:snapshot=json.load(f)
 selection=json.loads(Path(a.selection_attestation).read_bytes());code_hash=sha(__file__)
 g,r=reconstruct(snapshot,a.osm,a.river_start)
 if selection.get('schema')!='neon-current-boundary-selection-attestation-v1' or selection.get('project_id')!='wild-cherry-46472487' or selection.get('branch_id')!='br-shy-mountain-arsff6zb' or selection.get('database')!='worldatlas' or selection.get('boundary_id')!='ural_kara_coast_to_caspian' or selection.get('boundary_sha256')!=r['selected_geometry_sha256'] or selection.get('boundary_status')!='selected_for_research' or selection.get('snapshot_sha256')!=a.snapshot_sha256:raise ValueError('selection attestation mismatch')
 r['inputs']={'snapshot_sha256':a.snapshot_sha256,'osm_sha256':a.osm_sha256,'selection_attestation_sha256':a.selection_attestation_sha256};r['code_sha256']=code_hash
 if sha(__file__)!=code_hash:raise ValueError('implementation changed')
 for f,h in ((a.snapshot,a.snapshot_sha256),(a.osm,a.osm_sha256),(a.selection_attestation,a.selection_attestation_sha256)):
  if sha(f)!=h:raise ValueError('input changed: '+f)
 if a.geometry_output:
  with open(a.geometry_output,'x') as f:json.dump(g,f,sort_keys=True,separators=(',',':'),allow_nan=False);f.write('\n')
 with open(a.report,'x') as f:json.dump(r,f,sort_keys=True,indent=2);f.write('\n')
 print(json.dumps({'status':r['status'],'candidate_geometry_sha256':r['candidate_geometry_sha256'],'matches_selected_geometry':r['matches_selected_geometry'],'river_edges':r['osm_main_stream_edges']}))
if __name__=='__main__':main()
