#!/usr/bin/env python3
"""Compare selected river coordinates to a byte-pinned OSM relation snapshot.

OSM history only establishes that the *current captured elements* were already
visible at the cutoff when each timestamp and the relation history support it;
it does not establish the atlas construction source or geographic correctness.
"""
import argparse,collections,datetime,hashlib,json,xml.etree.ElementTree as ET

def digest(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def verify(snapshot,osm,history,boundary_id,river_start,cutoff):
 def ts(value):
  if not isinstance(value,str) or not value.endswith('Z'):raise ValueError('timestamp must be UTC ISO 8601')
  try:return datetime.datetime.fromisoformat(value[:-1]+'+00:00')
  except ValueError:raise ValueError('invalid UTC timestamp') from None
 parse_time=ts;limit=parse_time(cutoff)
 b=[x for x in snapshot['mainland_boundaries'] if x.get('boundary_id')==boundary_id]
 if len(b)!=1:raise ValueError('selected boundary is missing or ambiguous')
 g=b[0]['geometry'];actual=hashlib.sha256(json.dumps(g,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
 if actual!=b[0]['geometry_sha256']:raise ValueError('selected geometry hash mismatch')
 coords=g['coordinates'][river_start:]
 if len(coords)<2:raise ValueError('invalid river start')
 root=ET.parse(osm).getroot();relations=[x for x in root.findall('relation') if x.get('id')=='214415']
 if len(relations)!=1:raise ValueError('missing/duplicate relation')
 rel=relations[0];members=[e.get('ref') for e in rel.findall('member') if e.get('type')=='way' and e.get('role')=='main_stream']
 if not members or len(members)!=len(set(members)):raise ValueError('missing or duplicate main-stream members')
 ways={e.get('id'):e for e in root.findall('way')};nodes={e.get('id'):e for e in root.findall('node')}
 if len(ways)!=len(root.findall('way')) or len(nodes)!=len(root.findall('node')):raise ValueError('duplicate way/node')
 source_edges=collections.Counter();used_nodes=set();late_ways=[];late_nodes=[];adj=collections.defaultdict(list)
 def coord(n):
  x=nodes[n]
  return (float(x.attrib['lon']),float(x.attrib['lat']))
 def edge(a,b):return tuple(sorted((a,b)))
 for wid in members:
  if wid not in ways:raise ValueError('main-stream way missing')
  w=ways[wid];ts=w.get('timestamp')
  if not ts or parse_time(ts)>limit:late_ways.append(wid)
  ids=[e.attrib['ref'] for e in w.findall('nd')]
  if len(ids)<2 or any(i not in nodes for i in ids):raise ValueError('missing main-stream nodes')
  used_nodes.update(ids)
  for x,y in zip(ids,ids[1:]):
   source_edges[edge(coord(x),coord(y))]+=1;adj[x].append(y);adj[y].append(x)
 for n in used_nodes:
  ts=nodes[n].get('timestamp')
  if not ts or parse_time(ts)>limit:late_nodes.append(n)
 selected_edges=collections.Counter(edge(tuple(a),tuple(b)) for a,b in zip(coords,coords[1:]))
 endpoints=[n for n,v in adj.items() if len(v)==1];branch_nodes=[n for n,v in adj.items() if len(v)>2];path=[]
 if len(endpoints)==2 and not branch_nodes:
  previous=None;current=endpoints[0]
  while current is not None and len(path)<=len(adj):
   path.append(current);nxt=[x for x in adj[current] if x!=previous]
   previous,current=current,(nxt[0] if len(nxt)==1 else None)
 chain_ok=len(path)==len(adj)==len(used_nodes) and len(set(path))==len(path)
 ordered=[coord(n) for n in path] if chain_ok else []
 ordered_match=ordered==[tuple(c) for c in coords] or ordered==[tuple(c) for c in reversed(coords)]
 hist=ET.parse(history).getroot();versions=[x for x in hist.findall('relation') if x.get('id')=='214415' and x.get('timestamp') and parse_time(x.get('timestamp'))<=limit]
 if not versions:raise ValueError('relation history has no version at cutoff')
 latest=max(versions,key=lambda x:x.get('timestamp'))
 relation_matches=(latest.get('version')==rel.get('version') and latest.get('visible','true')=='true')
 return {'boundary_id':boundary_id,'geometry_sha256':actual,'river_start_zero_based':river_start,'river_vertex_count':len(coords),'selected_edge_count':sum(selected_edges.values()),'main_stream_way_count':len(members),'main_stream_node_count':len(used_nodes),'node_chain_connected':chain_ok,'branch_node_count':len(branch_nodes),'endpoint_node_count':len(endpoints),'ordered_coordinates_match':ordered_match,'source_edge_count':sum(source_edges.values()),'edge_multisets_equal':source_edges==selected_edges,'selected_minus_source':sum((selected_edges-source_edges).values()),'source_minus_selected':sum((source_edges-selected_edges).values()),'current_relation_version':rel.get('version'),'current_relation_timestamp':rel.get('timestamp'),'cutoff':cutoff,'latest_history_version_at_cutoff':latest.get('version'),'latest_history_timestamp_at_cutoff':latest.get('timestamp'),'history_relation_version_matches':relation_matches,'main_stream_ways_after_cutoff_or_missing_timestamp':len(late_ways),'main_stream_nodes_after_cutoff_or_missing_timestamp':len(late_nodes),'limitations':['Exact coordinate-edge equality does not establish that these were the original construction bytes.','Timestamp and relation history are OSM metadata evidence, not independent survey or geographic authority.','No terrain-derived sections or headwater connector are verified by this river-only test.']}
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--snapshot',required=True);p.add_argument('--snapshot-sha256',required=True);p.add_argument('--osm',required=True);p.add_argument('--osm-sha256',required=True);p.add_argument('--history',required=True);p.add_argument('--history-sha256',required=True);p.add_argument('--boundary-id',default='ural_kara_coast_to_caspian');p.add_argument('--river-start',type=int,default=4969);p.add_argument('--cutoff',default='2026-11-02T00:00:00Z');a=p.parse_args()
 for path,expected in ((a.snapshot,a.snapshot_sha256),(a.osm,a.osm_sha256),(a.history,a.history_sha256)):
  if digest(path)!=expected:raise ValueError('input checksum mismatch: '+path)
 with open(a.snapshot) as f:s=json.load(f)
 result=verify(s,a.osm,a.history,a.boundary_id,a.river_start,a.cutoff);print(json.dumps(result,indent=2))
 if not result['edge_multisets_equal'] or not result['node_chain_connected'] or not result['ordered_coordinates_match']:raise SystemExit(1)
