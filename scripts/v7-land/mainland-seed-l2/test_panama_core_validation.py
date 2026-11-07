"""Source-to-seed binding tests with a tiny OSM response archive."""
import hashlib, json, tempfile, unittest, zipfile
from pathlib import Path
from panama_core_validation import BOUNDARY, REGION, RELATION, SOURCE, validate_panama_source

class PanamaCoreValidation(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.archive=Path(self.tmp.name)/'source.zip'
  raw=json.dumps({'elements':[{'type':'node','id':1,'lon':0,'lat':0},{'type':'node','id':2,'lon':1,'lat':1},{'type':'way','id':3,'nodes':[1,2]}]}).encode()
  manifest={'start_node':1,'ways':[{'id':3,'file':'3.json','sha256':hashlib.sha256(raw).hexdigest()}]}
  with zipfile.ZipFile(self.archive,'w') as z:z.writestr('manifest.json',json.dumps(manifest));z.writestr('3.json',raw)
  self.digest=hashlib.sha256(self.archive.read_bytes()).hexdigest();geometry={'type':'LineString','coordinates':[[0.,0.],[1.,1.]]};self.ghash=hashlib.sha256(json.dumps(geometry,sort_keys=True,separators=(',',':')).encode()).hexdigest()
  self.ref={'source_id':SOURCE[0],'version':SOURCE[1]};source={**self.ref,'sha256':self.digest,'size_bytes':self.archive.stat().st_size,'r2_bucket':'worldatlas','r2_key':'sources/test'}
  lineage={**source,'kind':'raw','provider':'OSM','source_uri':'https://example.org','provenance':{'origin':'fixture','representation':'provider_original_bundle'}}
  boundary={'boundary_id':BOUNDARY,'decision_revision':'r','execution_status':'selected_for_research','geometry':geometry,'geometry_sha256':self.ghash,'provenance':{'source_refs':[self.ref],'source_relationships':[{**self.ref,'relationship':RELATION}]}}
  segment={'kind':'boundary','id':BOUNDARY,'start':0,'end':2,'reverse':False};self.trace={'boundary_id':BOUNDARY,'source_id':SOURCE[0],'source_version':SOURCE[1],'archive_sha256':self.digest,'geometry_sha256':self.ghash,'vertices':2,'method':'osm-way-full-chain-v1'}
  self.snapshot={'decision_revision':{'id':'r'},'land_baseline_policy':{'decision_revision':'r','execution_status':'selected_for_research','boundary_ids':[BOUNDARY],'region_ids':[REGION]},'mainland_boundaries':[boundary],'sources':[source],'source_lineage_assets':[lineage],'source_lineage_dependencies':[],'seed_regions':[{'region_id':REGION,'decision_revision':'r','execution_status':'selected_for_research','segments':[segment]}]}
  self.report={'decision_snapshot_sha256':'d'*64,'decision_revision':'r','input_sha256':{'panama_osm_archive':self.digest},'panama_source_trace':self.trace,'region_traces':[{'region_id':REGION,'input_trace':[{**segment,'geometry_sha256':self.ghash}]}]};self.pin={'path':str(self.archive),'sha256':self.digest}
 def validate(self):return validate_panama_source(self.snapshot,'d'*64,self.report,self.pin)
 def test_replays_selected_source_and_consumed_segment(self):self.assertEqual(self.validate(),self.trace)
 def test_rejects_wrong_archive_or_snapshot(self):
  self.archive.write_bytes(b'tampered')
  with self.assertRaises(ValueError):self.validate()
  self.report['decision_snapshot_sha256']='0'*64
  with self.assertRaisesRegex(ValueError,'snapshot'):self.validate()
 def test_rejects_missing_link_and_catalog_mismatch(self):
  self.snapshot['mainland_boundaries'][0]['provenance']['source_refs']=[]
  with self.assertRaisesRegex(ValueError,'source link'):self.validate()
  self.snapshot['mainland_boundaries'][0]['provenance']['source_refs']=[self.ref];self.snapshot['sources'][0]['r2_key']='wrong'
  with self.assertRaisesRegex(ValueError,'catalog mismatch'):self.validate()
 def test_rejects_spoofed_trace_and_unconsumed_line(self):
  self.report['panama_source_trace']={**self.trace,'geometry_sha256':'0'*64}
  with self.assertRaisesRegex(ValueError,'source trace'):self.validate()
  self.report['panama_source_trace']=self.trace;self.report['region_traces'][0]['input_trace'][0]['end']=1
  with self.assertRaisesRegex(ValueError,'executed Panama'):self.validate()
 def test_rejects_changed_selected_geometry(self):
  self.snapshot['mainland_boundaries'][0]['geometry']['coordinates'][1][0]=2
  with self.assertRaisesRegex(ValueError,'geometry hash'):self.validate()

if __name__=='__main__':unittest.main()
