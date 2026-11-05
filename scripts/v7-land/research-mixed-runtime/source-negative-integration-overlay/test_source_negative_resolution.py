import hashlib,json
from pathlib import Path
from unittest.mock import patch
import polygon_policy,polygon_resolution,mixed_claims
from test_polygon_resolution import ResolveTests

class SourceNegativeTests(ResolveTests):
 def setup_negative(self):
  g={'type':'MultiPolygon','coordinates':[[[[-105,55],[-5,55],[-5,89],[-105,89],[-105,55]]],[[[5,55],[110,55],[110,89],[5,89],[5,55]]]]};self.file.write_text(json.dumps({'type':'FeatureCollection','features':[{'type':'Feature','properties':{'id':'f'},'geometry':g}]}));h=hashlib.sha256(self.file.read_bytes()).hexdigest()
  for z in (self.snap['sources'][0],self.snap['source_lineage_assets'][0],self.sources[0]):z['sha256']=h;z['size_bytes']=self.file.stat().st_size
  self.snap['features'][0]['geometry_sha256']=hashlib.sha256(json.dumps(g,sort_keys=True,separators=(',',':')).encode()).hexdigest();a=self.snap['affiliations'][0];a['method']='component_containment_excluding_source_v1';a['evidence']['selector']['additional_feature_ids']=['negative']
  pdf=Path(self.t.name)/'negative.pdf';pdf.write_bytes(b'%PDF-fake');digest=hashlib.sha256(pdf.read_bytes()).hexdigest();src={'source_id':'gov','version':'v','sha256':digest,'r2_bucket':'bucket','r2_key':'gov','size_bytes':pdf.stat().st_size};asset={**src,'kind':'raw','provider':'U.S. Government Publishing Office','source_uri':'https://www.govinfo.gov/content/pkg/example/pdf/example.pdf','license_name':'reuse unknown','license_uri':'https://www.govinfo.gov/','attribution':'provider','provenance':{'representation':'provider_original'}};self.snap['sources'].append(src);self.snap['source_lineage_assets'].append(asset);self.sources.append({**src,'path':str(pdf)})
  negative={'type':'Polygon','coordinates':[[[0,55],[110,55],[110,89],[0,89],[0,55]]]};gh=hashlib.sha256(json.dumps(negative,sort_keys=True,separators=(',',':')).encode()).hexdigest();e={'source_format':'federal-register-pdf-rectangle-v1','geometry_hash_method':'binary64-sorted-compact-geojson-v1','geometry':negative,'rectangle_extraction':{'page':1,'crop':{'x':0,'y':0,'width':100,'height':100},'heading':'A','next_heading':'B'}};self.snap['features'].append({'feature_id':'negative','source_id':'gov','source_version':'v','source_feature_id':'unit','geometry_sha256':gh,'evidence':e});self.snap['polygon_affiliation_feature_refs']=[{'affiliation_id':'a','role':'additional_polygon','feature_id':'negative'}];self.policy=polygon_policy.adapt(self.snap,{'a'});return negative
 def test_source_exclusion_selects_whole_positive_minus_negative(self):
  negative=self.setup_negative()
  with patch('federal_register_rectangle.extract_pdf_rectangle',return_value=negative):r=self.runv()
  claim=r['claims'][0];self.assertEqual(claim['component_ids'],[10]);self.assertEqual(claim['source_negative_filter']['excluded_roots'],[11]);self.assertEqual(claim['source_negative_filter']['selected_count'],1);self.assertEqual(claim['source_negative_filter']['excluded_count'],1);self.assertEqual(claim['containment']['stage'],'positive_full_center_before_exclusion');self.assertEqual(claim['source_negative_intersection']['selected_components'],1)
  compiled={'revision':'r','entity_revision':'e','affiliation_ids':['a'],'affiliation_entry_links':{'a':['entry']}};self.assertIn(10,mixed_claims.combine(compiled,self.snap,[r],{99}))
 def test_exclusion_source_must_be_pinned_and_official(self):
  self.setup_negative();self.snap['source_lineage_assets'][-1]['source_uri']='https://example.com/fake.pdf'
  with self.assertRaisesRegex(ValueError,'invalid Federal Register source'):polygon_policy.adapt(self.snap,{'a'})
 def test_exclusion_fk_must_match(self):
  self.setup_negative();self.snap['polygon_affiliation_feature_refs']=[]
  with self.assertRaisesRegex(ValueError,'polygon FK/selector mismatch'):polygon_policy.adapt(self.snap,{'a'})
 def test_excluding_all_fails_closed(self):
  self.setup_negative();negative={'type':'Polygon','coordinates':[[[-100,55],[79,55],[79,89],[-100,89],[-100,55]]]}
  f=self.snap['features'][-1];f['evidence']['geometry']=negative;f['geometry_sha256']=hashlib.sha256(json.dumps(negative,sort_keys=True,separators=(',',':')).encode()).hexdigest();self.policy=polygon_policy.adapt(self.snap,{'a'})
  with patch('federal_register_rectangle.extract_pdf_rectangle',return_value=negative):
   with self.assertRaisesRegex(ValueError,'empty source exclusion or selection'):self.runv()
 def test_source_tamper_fails_closed(self):
  self.setup_negative();Path(self.sources[-1]['path']).write_bytes(b'altered')
  with self.assertRaisesRegex(ValueError,'source pin mismatch'):self.runv()
 def test_structured_geometry_hash_must_match(self):
  self.setup_negative();self.snap['features'][-1]['evidence']['geometry']['coordinates'][0][0][0]=1
  with self.assertRaisesRegex(ValueError,'structured exclusion geometry hash mismatch'):polygon_policy.adapt(self.snap,{'a'})
 def test_pdf_geometry_must_match_structured_evidence(self):
  self.setup_negative();wrong={'type':'Polygon','coordinates':[[[1,55],[110,55],[110,89],[1,89],[1,55]]]}
  with patch('federal_register_rectangle.extract_pdf_rectangle',return_value=wrong):
   with self.assertRaisesRegex(ValueError,'structured exclusion geometry/source mismatch'):self.runv()
 def test_negative_boundary_center_fails_closed(self):
  self.setup_negative();bad={'type':'Polygon','coordinates':[[[18,55],[110,55],[110,89],[18,89],[18,55]]]};f=self.snap['features'][-1];f['evidence']['geometry']=bad;f['geometry_sha256']=hashlib.sha256(json.dumps(bad,sort_keys=True,separators=(',',':')).encode()).hexdigest();self.policy=polygon_policy.adapt(self.snap,{'a'})
  with patch('federal_register_rectangle.extract_pdf_rectangle',return_value=bad):
   with self.assertRaisesRegex(ValueError,'boundary crosses grid cell center'):self.runv()
