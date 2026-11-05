"""Synthetic fixtures only: no project geography or source records."""
import copy, hashlib, json, tempfile, unittest
from pathlib import Path
import numpy as np
from selection import selected_cut
from boundary import select_witnesses, reject_center_hits, reject_terminal_near_land, resolve_fragments
from partition_core import rasterize_barriers
from cut_graph import partition

def add_synthetic_catalog(snapshot):
 snapshot.update({'schema':'worldatlas-geography-decision-draft-evidence-v1','serialization':'worldatlas-canonical-json-v1'})
 source={'source_id':'source','version':'test','sha256':'a'*64,'r2_bucket':'test-bucket','r2_key':'synthetic','size_bytes':1}
 snapshot['sources']=[source];snapshot['source_lineage_assets']=[{**source,'kind':'raw','provider':'test','source_uri':'synthetic:test','provenance':{'representation':'provider_original','origin':'synthetic'}}];snapshot['source_lineage_dependencies']=[]
 snapshot['mainland_boundaries'][0]['provenance']={'source_refs':[{'source_id':'source','version':'test'}],'lineage_status':'incomplete'}
 return snapshot

class DirectCoreTest(unittest.TestCase):
 def fixture(self):
  line={'type':'LineString','coordinates':[[0.0,-2.0],[0.0,2.0]]}
  h=hashlib.sha256(json.dumps(line,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
  snapshot={'source':'neon-export','decision_revision':{'id':'d','status':'draft','entity_revision':'e'},'entity_revision':{'id':'e','status':'draft'},
   'mainland_component_rules':[{'rule_id':'r','region_id':'z','group_id':'g','inside_entity_id':1,'outside_entity_id':2,'execution_status':'selected_for_research','decision_revision':'d'}],
   'seed_regions':[{'region_id':'z','execution_status':'selected_for_research','decision_revision':'d','segments':[{'kind':'boundary','id':'b','start':0,'end':2,'reverse':False}],'witnesses':[{'lon':-1,'lat':0,'inside':True},{'lon':1,'lat':0,'inside':False}]}],
   'mainland_boundaries':[{'boundary_id':'b','execution_status':'selected_for_research','decision_revision':'d','method':'stored_linestring_v1','coordinate_reference':'OGC:CRS84','geometry_hash_method':'binary64-sorted-compact-geojson-v1','geometry_sha256':h,'geometry':line}],
   'category_bindings':[{'entity_id':1,'physical_class':'land','code':31},{'entity_id':2,'physical_class':'land','code':32}]}
  grid={'width':4,'height':4,'west':-2,'north':2,'step':1};pins={'component_rows':'a'*64,'component_runs':'b'*64}
  w={'schema':'mainland-witness-resolution-v1','status':'selected-research-identity-claims-not-mainland-proof','snapshot_sha256':'c'*64,'decision_revision':'d','entity_revision':'e','grid':grid,'input_sha256':pins,'groups':[{'group_id':'g','role':'mainland','component_id_current_generation_only':7,'target_entity_ids':[1,2]}]}
  add_synthetic_catalog(snapshot);return snapshot,w,pins,grid
 def select(self,s,w,p,g):return selected_cut(s,w,'c'*64,p,'r','b',g)
 def test_component_reader_bounds_offsets_before_allocation(self):
  import struct
  from boundary import TripleRows
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'rows').write_bytes(b'\0'*24);(p/'runs').write_bytes(b'')
   with self.assertRaisesRegex(ValueError,'offset file size'):TripleRows(p/'rows',p/'runs',4,max_width=8)
   (p/'rows').write_bytes(struct.pack('<5I',0,9,9,9,9));(p/'runs').write_bytes(struct.pack('<27I',*([0,1,7]*9)))
   with self.assertRaisesRegex(ValueError,'span count exceeds width'):TripleRows(p/'rows',p/'runs',4,max_width=8)
 def test_bounded_documents_reject_oversized_before_parse(self):
  import run_direct
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'document';p.write_bytes(b'x'*5)
   with self.assertRaisesRegex(ValueError,'document too large'):run_direct.bounded(p,4)
   from types import SimpleNamespace
   from unittest.mock import patch
   with patch.object(run_direct.os,'fstat',return_value=SimpleNamespace(st_size=4)):
    with self.assertRaisesRegex(ValueError,'document too large'):run_direct.bounded(p,4)
   p.write_bytes(b'1234');self.assertEqual(run_direct.bounded(p,4),b'1234')
 def test_selected_and_dynamic_codes(self):
  s,w,p,g=self.fixture();result=self.select(s,w,p,g);self.assertEqual((result['inside_code'],result['outside_code'],result['component']),(31,32,7))
  seeds,checks,codes=select_witnesses(result['witnesses'],lambda lon,lat:(int(lon+2),int(2-lat)),lambda x,y:True,result['line'],31,32)
  self.assertEqual(seeds,{31:(1,2),32:(3,2)});self.assertEqual(codes,(31,32))
  reverse=list(reversed(result['line']));self.assertEqual(select_witnesses(result['witnesses'],lambda x,y:(int(x+2),int(2-y)),lambda x,y:True,reverse,31,32)[2],(32,31))
 def test_line_hash_lineage_and_review_fail_closed(self):
  s,w,p,g=self.fixture()
  for mutate in (lambda x:x['mainland_boundaries'][0]['geometry']['coordinates'][0].__setitem__(0,1),lambda x:x['mainland_component_rules'][0].__setitem__('execution_status','draft'),lambda x:x['seed_regions'][0]['segments'][0].__setitem__('end',1)):
   x=copy.deepcopy(s);mutate(x)
   with self.assertRaises(ValueError):self.select(x,w,p,g)
  x=copy.deepcopy(s);x['seed_regions'][0]['segments'].append({'kind':'boundary','id':'other','start':0,'end':2,'reverse':False})
  with self.assertRaisesRegex(ValueError,'exactly one'):self.select(x,w,p,g)
  x=copy.deepcopy(s);x['source_lineage_dependencies'].append({'source_id':'source','version':'test'})
  with self.assertRaisesRegex(ValueError,'derived source'):self.select(x,w,p,g)
  x=copy.deepcopy(s);x['source_lineage_assets'][0]['r2_key']='tampered'
  with self.assertRaisesRegex(ValueError,'R2 asset'):self.select(x,w,p,g)
  w=copy.deepcopy(w);w['input_sha256']['component_runs']='x'*64
  with self.assertRaisesRegex(ValueError,'lineage'):self.select(s,w,p,g)
 def test_ambiguity_and_cut_endpoints_fail_closed(self):
  with self.assertRaisesRegex(ValueError,'conflicting witness orientation'):
   select_witnesses([{'lon':-1,'lat':0,'inside':True},{'lon':-0.5,'lat':0,'inside':False}],lambda x,y:(int(x+2),1),lambda x,y:True,[[0,-2],[0,2]],31,32)
  with self.assertRaisesRegex(ValueError,'cell center'):reject_center_hits([[1.5,0],[1.5,4]],4,4)
  with self.assertRaisesRegex(ValueError,'endpoint too close'):reject_terminal_near_land([[1.5,1.5],[4,4]],4,4,lambda x,y:(x,y)==(1,1))
 def test_boundary_raster_work_limit_and_guard(self):
  calls=[]
  with self.assertRaisesRegex(ValueError,'work limit'):
   rasterize_barriers([[(0,0),(4,4)]],5,5,guard=lambda:calls.append(1),max_work=1)
  self.assertTrue(calls)
  with self.assertRaisesRegex(ValueError,'center-hit work limit'):
   reject_center_hits([[0,0],[4,4]],5,5,guard=lambda:None,max_work=1)
 def test_graph_guards_and_cell_conservation(self):
  cuts=rasterize_barriers([[(2,0),(2,4)]],4,4)
  with tempfile.TemporaryDirectory() as d:
   calls=[];out=Path(d)/'graph';r=partition(lambda y:[(1,3)],4,4,cuts,{31:(1,1),32:(2,1)},out,lambda:calls.append(1),max_nodes=100)
   self.assertEqual(r['selected_cells'],8);self.assertEqual(r['cells_by_code'],{31:4,32:4});self.assertEqual(r['residual_cells'],0);self.assertGreater(len(calls),1)
   with self.assertRaisesRegex(ValueError,'node limit'):partition(lambda y:[(1,3)],4,4,cuts,{31:(1,1),32:(2,1)},Path(d)/'limited',lambda:None,max_nodes=1)
 def test_random_graph_matches_independent_cell_bfs(self):
  import random
  from collections import deque
  from partition_core import CutEdges
  rng=random.Random(419);w,h=9,5
  for case in range(30):
   land={(x,y) for y in range(h) for x in range(w) if rng.random()<0.7};cuts=CutEdges()
   for y in range(h):
    for x in range(w-1):
     if rng.random()<0.2:cuts.add_h(y,x)
    if rng.random()<0.5:cuts.add_wrap(y)
   for y in range(h-1):
    for x in range(w):
     if rng.random()<0.2:cuts.add_v(y,x)
   def neighbours(x,y):
    if x and x-1 not in cuts.horizontal[y]:yield (x-1,y)
    if x<w-1 and x not in cuts.horizontal[y]:yield (x+1,y)
    if x==0 and y not in cuts.wrap:yield (w-1,y)
    if x==w-1 and y not in cuts.wrap:yield (0,y)
    if y and x not in cuts.vertical[y-1]:yield (x,y-1)
    if y<h-1 and x not in cuts.vertical[y]:yield (x,y+1)
   seen=set();components=[]
   for point in land:
    if point in seen:continue
    group={point};seen.add(point);q=deque([point])
    while q:
     for n in neighbours(*q.popleft()):
      if n in land and n not in seen:seen.add(n);group.add(n);q.append(n)
    components.append(group)
   if len(components)<2:continue
   seeds={31:next(iter(components[0])),32:next(iter(components[1]))}
   def intervals(y):
    xs=sorted(x for x,yy in land if yy==y);result=[]
    for x in xs:
     if result and result[-1][1]==x:result[-1]=(result[-1][0],x+1)
     else:result.append((x,x+1))
    return result
   with tempfile.TemporaryDirectory() as d:
    out=Path(d)/'out';partition(intervals,w,h,cuts,seeds,out,lambda:None,1000)
    def cells(prefix):
     offsets=np.fromfile(out/(prefix+'-rows.u32le'),dtype='<u4');spans=np.fromfile(out/(prefix+'-spans.u32le'),dtype='<u4').reshape(-1,3);result={}
     for y in range(h):
      for a,b,k in spans[offsets[y]:offsets[y+1]]:
       for x in range(int(a),int(b)):result[(x,y)]=int(k)
     return result
    labelled=cells('partition');residual=cells('residual')
    self.assertEqual({p for p,k in labelled.items() if k==31},components[0]);self.assertEqual({p for p,k in labelled.items() if k==32},components[1]);self.assertEqual(set(residual),land-components[0]-components[1])
 def test_residual_cannot_guess_disconnected_or_endpoint(self):
  cuts=rasterize_barriers([[(2,0),(2,4)]],4,4)
  with self.assertRaisesRegex(ValueError,'does not touch'):resolve_fragments({1:[(0,0)]},cuts,[[0,-2],[0,2]],-2,2,1,4,4,lambda x,y:True,side_codes=(31,32))

class DriverTest(unittest.TestCase):
 def test_strict_json_rejects_duplicate_and_nonfinite(self):
  import run_direct
  with self.assertRaisesRegex(ValueError,'duplicate JSON key'):run_direct.strict_json('{"a":1,"a":2}')
  with self.assertRaisesRegex(ValueError,'nonfinite JSON number'):run_direct.strict_json('{"a":NaN}')
 def test_synthetic_fresh_build_and_tamper_rejection(self):
  import builtins, io
  from unittest.mock import patch
  import run_direct
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);inp=root/'input';inp.mkdir()
   rows=inp/'rows';spans=inp/'spans';np.array([0,0,1,2,2],dtype='<u4').tofile(rows);np.array([[3,5,7]]*2,dtype='<u4').tofile(spans)
   sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
   grid={'width':8,'height':4,'west':-180,'north':90,'step':45}
   line={'type':'LineString','coordinates':[[0.0,90.0],[0.0,-90.0]]};lh=hashlib.sha256(json.dumps(line,sort_keys=True,separators=(',',':')).encode()).hexdigest()
   snap={'source':'neon-export','decision_revision':{'id':'d','status':'draft','entity_revision':'e'},'entity_revision':{'id':'e','status':'draft'},'mainland_component_rules':[{'rule_id':'r','region_id':'z','group_id':'g','inside_entity_id':1,'outside_entity_id':2,'execution_status':'selected_for_research','decision_revision':'d'}], 'seed_regions':[{'region_id':'z','execution_status':'selected_for_research','decision_revision':'d','segments':[{'kind':'boundary','id':'b','start':0,'end':2,'reverse':False}],'witnesses':[{'lon':-22.5,'lat':22.5,'inside':True},{'lon':22.5,'lat':22.5,'inside':False}]}], 'mainland_boundaries':[{'boundary_id':'b','execution_status':'selected_for_research','decision_revision':'d','method':'stored_linestring_v1','coordinate_reference':'OGC:CRS84','geometry_hash_method':'binary64-sorted-compact-geojson-v1','geometry_sha256':lh,'geometry':line}], 'category_bindings':[{'entity_id':1,'physical_class':'land','code':31},{'entity_id':2,'physical_class':'land','code':32}]}
   add_synthetic_catalog(snap);sp=inp/'snapshot';sp.write_text(json.dumps(snap));witness={'schema':'mainland-witness-resolution-v1','status':'selected-research-identity-claims-not-mainland-proof','snapshot_sha256':sha(sp),'decision_revision':'d','entity_revision':'e','grid':grid,'input_sha256':{'component_rows':sha(rows),'component_runs':sha(spans)},'groups':[{'group_id':'g','role':'mainland','component_id_current_generation_only':7,'target_entity_ids':[1,2]}]};wp=inp/'witness';wp.write_text(json.dumps(witness))
   pins={k:{'path':str(v),'sha256':sha(v)} for k,v in {'snapshot':sp,'witness':wp,'component_rows':rows,'component_runs':spans}.items()}
   cfg={'schema':'direct-source-split-request-v1','grid':grid,'inputs':pins,'rule_id':'r','boundary_id':'b','limits':{'minimum_memory_kib':1887437,'minimum_free_bytes':2*1024**3,'max_rss_kib':870400,'max_nodes':100,'max_raster_work':10000,'max_residual_cells':10,'max_residual_segment_tests':100}};request=inp/'request';request.write_text(json.dumps(cfg))
   original_open=builtins.open
   def fake_open(path,*args,**kwargs):
    if str(path)=='/proc/meminfo':return io.StringIO('MemAvailable: 4000000 kB\n')
    return original_open(path,*args,**kwargs)
   with patch('builtins.open',side_effect=fake_open), patch.object(run_direct,'require_guardian'):
    result=run_direct.run(request,root/'out')
    self.assertEqual(result['selected_cells'],4);self.assertEqual(result['residual_cells'],0);self.assertFalse(result['publishable'])
    self.assertEqual(np.fromfile(root/'out/direct-spans.u32le',dtype='<u4').reshape(-1,3).tolist(),[[3,4,31],[4,5,32]]*2)
    spans.write_bytes(b'tampered')
    with self.assertRaisesRegex(ValueError,'input pin mismatch'):run_direct.run(request,root/'bad')
    self.assertFalse((root/'bad').exists())

if __name__ == '__main__':unittest.main()
