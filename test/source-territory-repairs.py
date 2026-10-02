"""Meaningful migration gates for identity unions and exact territorial replacement."""
import copy, gzip, hashlib, importlib.util, json, pathlib, sys, tempfile, unittest
from shapely.geometry import box, mapping
from shapely import union_all
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
spec=importlib.util.spec_from_file_location('repairs',ROOT/'scripts/apply-source-territory-repairs.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class RepairTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.tmp.name)
  self.units={};previous=None
  for tier in reversed(m.TIERS[1:]):
   self.units[tier]={'id':tier,'level':tier,'name':tier,'parent_id':previous,'metadata':{}};previous=tier
  self.units['unused']={'id':'unused','level':'province','name':'unused','parent_id':'area','metadata':{}}
  small=box(12,41,12.0001,41.0001);full=box(12,41,12.002,41.002);world=box(11.99,40.99,12.01,41.01)
  self.features=[]
  for id,g in [('A',box(0,0,1,1)),('B',box(1,0,2,1)),('VAT+00?',small),('atlas:location:ITA:SLL:1209',world.difference(small))]:
   self.features.append({'type':'Feature','properties':{'id':id,'name':id,'parent_id':'province','reference_owner':'Original','metadata':{'reference_owner_id':'owner:original'}},'geometry':mapping(g)})
  union=union_all([m.geometry(f['geometry']) for f in self.features[:2]])
  m.write(self.root/'union.json.gz',{'type':'Feature','properties':{'id':'A'},'geometry':mapping(union)})
  replacement={'VAT+00?':full,'atlas:location:ITA:SLL:1209':world.difference(full)}
  m.write(self.root/'vatican.json.gz',{'type':'FeatureCollection','features':[{'properties':{'id':id},'geometry':mapping(g)} for id,g in replacement.items()]})
  (self.root/'source.json').write_text('{}')
  def before(f):return {'id':f['properties']['id'],'geometry_sha256':m.digest(m.geometry(f['geometry'])),'direct_records':{'entity_history_sourced':1}}
  self.report={'union_proposals':[{'proposal_id':'merge','classification':'artificial-reference-owner-partition','status':'exact-union-ready','source_identity':'source:A','rationale':'Exact named source unit','before':[before(f) for f in self.features[:2]],'after':{'retained_id':'A','geometry_sha256':m.digest(union),'geometry_file':'union.json.gz','geometry_file_sha256':m.sha(self.root/'union.json.gz')},'other_location_overlaps':[],'modern_reference_owner':{'winner':{'owner_id':'owner:winner','name':'Winner','share':.8}}}], 'vatican_restoration':{'proposal_id':'vatican','classification':'cartographic-placeholder-replaced-with-full-named-territory-source','source':{'path':'source.json','file_sha256':m.sha(self.root/'source.json'),'geometry_sha256':m.digest(full),'entity_id':'osm:relation:36989','url':'https://example.test/source','license':'ODbL','attribution':'OSM contributors'},'before':[before(f) for f in self.features[2:]],'after':[{'id':id,'geometry_sha256':m.digest(g)} for id,g in replacement.items()],'geometry_file':'vatican.json.gz','geometry_file_sha256':m.sha(self.root/'vatican.json.gz'),'modern_reference_owner':{'winner':{'owner_id':'owner:Q237','name':'Vatican'}},'diagnosis':'Pinned complete territory'}}
  m.write(self.root/'data/source-territory-splits.json.gz',self.report)
 def tearDown(self):self.tmp.cleanup()
 def stage(self):return m.stage_repairs(self.features,self.units,self.report,self.root)
 def test_identity_union_replacement_and_archives(self):
  before,after,units,r=self.stage();self.assertEqual(r['removed_ids'],['B']);self.assertEqual(r['changed_ids'],['A','VAT+00?','atlas:location:ITA:SLL:1209']);self.assertEqual(len(r['archives']),4)
  self.assertEqual({f['properties']['id'] for f in after},{'A','VAT+00?','atlas:location:ITA:SLL:1209'});self.assertNotIn('unused',units)
  self.assertTrue(all(not x['history_transfer'] for x in r['relationships']));self.assertEqual(before,self.features)
  self.assertEqual(m.area(union_all([m.geometry(f['geometry']) for f in after]).symmetric_difference(union_all([m.geometry(f['geometry']) for f in before]))),0)
 def test_owner_does_not_choose_parent(self):
  _,after,_,_=self.stage();a=next(f for f in after if f['properties']['id']=='A')
  self.assertEqual(a['properties']['reference_owner'],'Winner');self.assertEqual(a['properties']['parent_id'],'province')
 def test_disputed_reference_not_overridden_by_source_owner(self):
  proposal=self.report['union_proposals'][0]
  proposal['modern_reference_owner']={'status':'disputed','winner':None,'conflicts':[{'owner_ids':['owner:a','owner:b']}]}
  proposal['reference_source_record_majority']={'winner':{'owner_id':'owner:a','name':'A'}}
  _,after,_,_=self.stage();a=next(f for f in after if f['properties']['id']=='A')
  self.assertIsNone(a['properties']['reference_owner']);self.assertIsNone(a['properties']['metadata']['reference_owner_id'])
 def test_unrelated_identity_and_geometry_preserved_exactly(self):
  untouched={'type':'Feature','properties':{'id':'C','name':'C','parent_id':'province','reference_owner':'Other','metadata':{'nested':{'note':'untouched'}}},'geometry':mapping(box(5,5,6,6))}
  self.features.append(untouched)
  _,after,_,r=self.stage();self.assertEqual(next(f for f in after if f['properties']['id']=='C'),untouched);self.assertEqual(r['reused_ids'],['C'])
 def test_reject_stale_original(self):
  self.features[0]['geometry']=mapping(box(0,0,.9,1))
  with self.assertRaisesRegex(ValueError,'Stale repair'):self.stage()
 def test_reject_changed_proposal_source(self):
  (self.root/'union.json.gz').write_bytes(b'changed')
  with self.assertRaisesRegex(ValueError,'file hash'):self.stage()
 def test_reject_changed_osm_source(self):
  (self.root/'source.json').write_text('changed')
  with self.assertRaisesRegex(ValueError,'OSM source'):self.stage()
 def test_reject_union_growth(self):
  p=self.report['union_proposals'][0];g=box(0,0,3,1);m.write(self.root/'union.json.gz',{'geometry':mapping(g)})
  p['after'].update(geometry_file_sha256=m.sha(self.root/'union.json.gz'),geometry_sha256=m.digest(g))
  with self.assertRaisesRegex(ValueError,'preserve inspected'):self.stage()
 def test_numerical_seam_exact_difference(self):
  g=box(0,0,.00001,.00001);neighbor=box(.0000099,0,.00002,.00001);overlap=m.area(g.intersection(neighbor));self.assertLess(overlap,1)
  p={'status':'blocked-neighbor-overlap','other_location_overlaps':[{'id':'N','area_km2':overlap/1e6}]};by={'N':{'properties':{'name':'Neighbor'},'geometry':mapping(neighbor)}}
  revised,receipt=m.resolve_seams(g,p,by);self.assertEqual(m.area(revised.intersection(neighbor)),0);self.assertEqual(len(receipt),1)
  self.assertEqual(m.area(union_all([g,neighbor]).symmetric_difference(union_all([revised,neighbor]))),0)
 def test_large_overlap_not_numerical(self):
  g=box(0,0,1,1);p={'status':'blocked-neighbor-overlap','other_location_overlaps':[{'id':'N','area_km2':1}]};by={'N':{'properties':{'name':'N'},'geometry':mapping(g)}}
  with self.assertRaisesRegex(ValueError,'sub-square'):m.resolve_seams(g,p,by)
 def test_incomplete_parent_chain_fails(self):
  del self.units['area']
  with self.assertRaisesRegex(ValueError,'Incomplete'):self.stage()
 def test_global_audit_detects_containment_and_crossing(self):
  values=[{'properties':{'id':id},'geometry':mapping(g)} for id,g in [('A',box(0,0,2,2)),('B',box(.5,.5,1,1)),('C',box(1,1,3,3)),('D',box(3,0,4,1))]]
  r=m.overlap_audit(values);self.assertEqual({tuple(x['ids']) for x in r['positive_pairs']},{('A','B'),('A','C')});self.assertEqual(r['invalid_ids'],[])

if __name__=='__main__':unittest.main()
