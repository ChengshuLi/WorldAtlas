import unittest,tempfile,pathlib,json,hashlib
from export_adapter import boundary_records,load_pinned_snapshot
from regions import geometry_hash
class Export(unittest.TestCase):
 def setUp(self):
  src={'source_id':'raw','version':'1','sha256':'a'*64,'r2_bucket':'worldatlas','r2_key':'sources/raw','size_bytes':100};lin={**src,'kind':'raw','provider':'provider','source_uri':'https://example.org/raw','provenance':{'origin':'provider-original','representation':'provider_original'}};g={'type':'LineString','coordinates':[['0','0'],['1','1']]};h=geometry_hash({'type':'LineString','coordinates':[[0.,0.],[1.,1.]]});b={'decision_revision':'r','boundary_id':'b','method':'stored_linestring_v1','execution_status':'selected_for_research','coordinate_reference':'OGC:CRS84','geometry':g,'geometry_sha256':h,'geometry_hash_method':'binary64-sorted-compact-geojson-v1','provenance':{'source_refs':[{'source_id':'raw','version':'1'}],'source_relationships':[{'source_id':'raw','version':'1','relationship':'construction_input'}],'lineage_status':'incomplete'}}
  self.s={'source':'neon-export','schema':'worldatlas-geography-decision-draft-evidence-v1','serialization':'worldatlas-canonical-json-v1','decision_revision':{'id':'r','status':'draft','entity_revision':'e'},'entity_revision':{'id':'e','status':'draft'},'sources':[src],'source_lineage_assets':[lin],'source_lineage_dependencies':[],'mainland_boundaries':[b]}
 def test_valid_export(self):
  r,e,b,s=boundary_records(self.s);self.assertEqual((r,e),('r','e'));self.assertEqual(b[('boundary','b')]['geometry_sha256'],self.s['mainland_boundaries'][0]['geometry_sha256']);self.assertEqual(s[('raw','1')]['kind'],'raw')
 def test_local_preview_rejected(self):
  self.s['source']='local-preview-not-neon'
  with self.assertRaisesRegex(ValueError,'Neon combined export'):boundary_records(self.s)
 def test_missing_boundary_revision_rejected(self):
  del self.s['mainland_boundaries'][0]['decision_revision']
  with self.assertRaisesRegex(ValueError,'revision'):boundary_records(self.s)
 def test_duplicate_boundary_rejected(self):
  self.s['mainland_boundaries'].append(dict(self.s['mainland_boundaries'][0]))
  with self.assertRaisesRegex(ValueError,'duplicate'):boundary_records(self.s)
 def test_duplicate_source_rejected(self):
  self.s['sources'].append(dict(self.s['sources'][0]))
  with self.assertRaisesRegex(ValueError,'duplicate'):boundary_records(self.s)
 def test_raw_source_citation_required(self):
  self.s['mainland_boundaries'][0]['provenance']['source_refs']=[]
  with self.assertRaisesRegex(ValueError,'raw source references'):boundary_records(self.s)
 def test_raw_record_with_dependency_rejected(self):
  self.s['source_lineage_dependencies']=[{'source_id':'raw','version':'1','parent_source_id':'other','parent_version':'1'}]
  with self.assertRaisesRegex(ValueError,'pinned raw R2'):boundary_records(self.s)
 def test_missing_provider_origin_rejected(self):
  del self.s['source_lineage_assets'][0]['provenance']['origin']
  with self.assertRaisesRegex(ValueError,'provider original'):boundary_records(self.s)
 def test_nonoriginal_raw_rejected(self):
  self.s['source_lineage_assets'][0]['provenance']['representation']='derived'
  with self.assertRaisesRegex(ValueError,'provider original'):boundary_records(self.s)
 def test_derived_source_rejected(self):
  self.s['source_lineage_assets'][0]['kind']='derived'
  with self.assertRaisesRegex(ValueError,'pinned raw R2'):boundary_records(self.s)
 def test_supporting_evidence_preserves_qualification_without_claiming_original(self):
  p=self.s['mainland_boundaries'][0]['provenance'];p['source_relationships'][0]['relationship']='local_geographic_comparison_not_terrain_or_construction_proof'
  self.s['source_lineage_assets'][0]['provenance']={}
  _,_,b,_=boundary_records(self.s);ref=b[('boundary','b')]['qualified_source_refs'][0]
  self.assertEqual(ref['role'],'supporting_research_evidence');self.assertEqual(ref['relationship'],'local_geographic_comparison_not_terrain_or_construction_proof')
 def test_unknown_relationship_rejected(self):
  self.s['mainland_boundaries'][0]['provenance']['source_relationships'][0]['relationship']='unreviewed'
  with self.assertRaisesRegex(ValueError,'unsupported'):boundary_records(self.s)
 def test_relationship_set_mismatch_rejected(self):
  self.s['mainland_boundaries'][0]['provenance']['source_relationships'][0]['source_id']='different'
  with self.assertRaisesRegex(ValueError,'pinned raw R2'):boundary_records(self.s)
 def test_complete_lineage_cannot_rest_on_supporting_evidence(self):
  p=self.s['mainland_boundaries'][0]['provenance'];p['lineage_status']='complete';p['source_relationships'][0]['relationship']='local_geographic_comparison_not_terrain_or_construction_proof'
  with self.assertRaisesRegex(ValueError,'complete lineage requires'):boundary_records(self.s)
 def test_tampered_geometry_rejected(self):
  self.s['mainland_boundaries'][0]['geometry']['coordinates'][1]=['2','1']
  with self.assertRaisesRegex(ValueError,'geometry hash'):boundary_records(self.s)
 def test_snapshot_duplicate_key_rejected(self):
  with tempfile.TemporaryDirectory() as t:
   p=pathlib.Path(t)/'s';b=b'{"x":1,"x":2}';p.write_bytes(b)
   with self.assertRaisesRegex(ValueError,'duplicate JSON key'):load_pinned_snapshot(p,hashlib.sha256(b).hexdigest(),lambda:None)

class Routes(unittest.TestCase):
 def setUp(self):
  from regions import geometry_hash
  self.g={'type':'LineString','coordinates':[['0','0'],['1','1']]};h=geometry_hash({'type':'LineString','coordinates':[[0.,0.],[1.,1.]]});self.s={'stage1_source_inputs':[{'source_id':'raw','source_version':'1','decision_revision':'r','execution_status':'selected_for_research'}],'routes':[{'provenance':{'lineage_status':'incomplete','source_refs':[{'source_id':'raw','version':'1'}]},'route_id':'c','decision_revision':'r','execution_status':'selected_for_research','route_type':'stored_linestring_v1','role':'water_closure','closure_method':'physical_water_closure_v1','coordinate_reference':'OGC:CRS84','geometry_hash_method':'binary64-sorted-compact-geojson-v1','geometry_sha256':h,'geometry':self.g}]}
 def test_selected_route(self):
  from export_adapter import route_records
  self.assertEqual(route_records(self.s,'r',['c'])[('route','c')]['role'],'water_closure')
 def test_missing_selected_physical_source_rejected(self):
  from export_adapter import route_records
  self.s['stage1_source_inputs']=[]
  with self.assertRaisesRegex(ValueError,'closure source selection'):route_records(self.s,'r',['c'])
 def test_forged_route_reference_rejected(self):
  from export_adapter import route_records
  self.s['routes'][0]['provenance']['source_refs'][0]['version']='stale'
  with self.assertRaisesRegex(ValueError,'closure source selection'):route_records(self.s,'r',['c'])
 def test_old_ocean_method_not_inferred(self):
  from export_adapter import route_records
  self.s['routes'][0]['route_type']='wgs84_geodesic'
  with self.assertRaisesRegex(ValueError,'unsupported'):route_records(self.s,'r',['c'])
 def test_unchecked_connector_rejected(self):
  from export_adapter import route_records
  self.s['routes'][0]['role']='geographic_connector'
  with self.assertRaisesRegex(ValueError,'unsupported'):route_records(self.s,'r',['c'])
 def test_duplicate_route_rejected(self):
  from export_adapter import route_records
  self.s['routes'].append(dict(self.s['routes'][0]))
  with self.assertRaisesRegex(ValueError,'duplicate'):route_records(self.s,'r',['c'])


class SelectedRegions(unittest.TestCase):
 def test_unselected_or_unused_fails(self):
  from export_adapter import selected_regions
  s={'land_baseline_policy':{'decision_revision':'rev','execution_status':'selected_for_research','island_overrides':'none','region_ids':['r'],'boundary_ids':['b'],'route_ids':[]},'seed_regions':[{'region_id':'r','decision_revision':'rev','execution_status':'selected_for_research','segments':[{'kind':'boundary','id':'b','start':0,'end':2,'reverse':False}],'geometry_sha256':'a'*64,'geometry_hash_method':'binary64-sorted-compact-geojson-v1','witnesses':[]}],'routes':[]}
  out,recs=selected_regions(s,'rev',{('boundary','b'):{'id':'b'}});self.assertEqual(out[0]['revision_id'],'rev')
  s['land_baseline_policy']['decision_revision']='stale'
  with self.assertRaisesRegex(ValueError,'region policy'):selected_regions(s,'rev',{('boundary','b'):{'id':'b'}})
  s['land_baseline_policy']['decision_revision']='rev'
  s['land_baseline_policy']['boundary_ids']=['b','unused']
  with self.assertRaisesRegex(ValueError,'boundary set mismatch'):selected_regions(s,'rev',{('boundary','b'):{'id':'b'}})

if __name__=='__main__':unittest.main()
