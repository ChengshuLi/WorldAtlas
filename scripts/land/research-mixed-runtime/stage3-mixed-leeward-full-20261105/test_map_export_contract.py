import copy,hashlib,json,tempfile,unittest
from pathlib import Path
from test_polygon_policy import TestPolygonPolicy
from polygon_policy import adapt
from polygon_loader import extract
B={'minlon':'0','minlat':'0','maxlon':'0.1','maxlat':'0.1'}
class PolicyContract(unittest.TestCase):
 def setUp(self):
  f=TestPolygonPolicy();f.setUp();self.s=f.s;self.s['polygon_affiliation_feature_refs']=[];a=self.s['affiliations'][0];a.update(method='osm_archipelago_component_intersection_v1');a['evidence']['selector']={'additional_feature_ids':[],'include_witnesses':[],'exclude_witnesses':[],'relation_version':'2','extractor_version':'osm-multipolygon-outer-v4','expected_identity_tags':{'name':'Demo','place':'archipelago'}};self.s['features']=self.s['features'][:1];self.s['features'][0].update(source_feature_id='9',evidence={'source_format':'osm-xml','relation_version':'2','geometry_hash_method':'binary64-sorted-compact-geojson-v1'});self.asset=self.s['source_lineage_assets'][0];self.asset.update(source_uri='https://www.openstreetmap.org/export/finish',provider='OpenStreetMap',license_name='ODbL 1.0',license_uri='https://opendatacommons.org/licenses/odbl/1-0/',attribution='© OpenStreetMap contributors');self.s['features'][0]['evidence']['r2_verification']={'status':'verified','method':'full-byte-compare',**{k:self.asset[k] for k in ('sha256','size_bytes','r2_bucket','r2_key')}};self.asset['provenance']['osm_map_export']={'request_method':'POST','bounds':dict(B)}
 def test_valid_export(self):self.assertEqual(adapt(self.s,{'a'})['decisions'][0]['features'][0]['map_export_bounds'],B)
 def test_reject_host_path_query_and_bad_method(self):
  for u in ['https://evil.example/export/finish','http://www.openstreetmap.org/export/finish','https://www.openstreetmap.org/export/finish?q=1','https://www.openstreetmap.org/else']:
   self.asset['source_uri']=u
   with self.subTest(url=u),self.assertRaises(ValueError):adapt(self.s,{'a'})
  self.asset['source_uri']='https://www.openstreetmap.org/export/finish';self.asset['provenance']['osm_map_export']['request_method']='GET'
  with self.assertRaises(ValueError):adapt(self.s,{'a'})
 def test_reject_missing_custody_or_provider(self):
  for k in ('provider','license_name','license_uri','attribution'):
   old=self.asset[k];self.asset[k]='other'
   with self.subTest(field=k),self.assertRaises(ValueError):adapt(self.s,{'a'})
   self.asset[k]=old
  proof=self.s['features'][0]['evidence']['r2_verification']
  for k in tuple(proof):
   old=proof[k];proof[k]=None
   with self.subTest(proof=k),self.assertRaises(ValueError):adapt(self.s,{'a'})
   proof[k]=old
  proof['status']='not verified'
  with self.assertRaises(ValueError):adapt(self.s,{'a'})
 def test_reject_bad_bounds(self):
  for b in [{},dict(B,minlon='NaN'),dict(B,maxlon='-1'),dict(B,maxlon='10',maxlat='10'),dict(B,minlon=0)]:
   self.asset['provenance']['osm_map_export']['bounds']=b
   with self.subTest(bounds=b),self.assertRaises(ValueError):adapt(self.s,{'a'})
 def test_relation_full_back_compat(self):
  self.asset['source_uri']='https://api.openstreetmap.org/api/0.6/relation/9/full';del self.asset['provenance']['osm_map_export'];f=adapt(self.s,{'a'})['decisions'][0]['features'][0];self.assertNotIn('map_export_bounds',f)
class LoaderContract(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.p=Path(self.t.name)/'raw.osm';self.xml='<osm><bounds minlon="0" minlat="0" maxlon="0.1" maxlat="0.1"/><node id="1" visible="true" lon="0.02" lat="0.02"/><node id="2" visible="true" lon="0.08" lat="0.02"/><node id="3" visible="true" lon="0.08" lat="0.08"/><way id="7" visible="true"><nd ref="1"/><nd ref="2"/><nd ref="3"/><nd ref="1"/></way><relation id="9" version="2" visible="true"><member type="way" ref="7" role="outer"/><tag k="type" v="multipolygon"/><tag k="name" v="Demo"/><tag k="place" v="archipelago"/></relation></osm>';self.write(self.xml);g={'type':'MultiPolygon','coordinates':[[[[.02,.02],[.08,.02],[.08,.08],[.02,.02]]]]};self.f={'source_format':'osm-xml','source_class':'archipelago','extractor_version':'osm-multipolygon-outer-v4','source_feature_id':'9','relation_version':'2','geometry_sha256':hashlib.sha256(json.dumps(g,sort_keys=True,separators=(',',':')).encode()).hexdigest(),'expected_identity_tags':{'name':'Demo','place':'archipelago'},'map_export_bounds':dict(B)}
 def write(self,xml):self.p.write_text(xml);self.pin={'path':str(self.p),'sha256':hashlib.sha256(self.p.read_bytes()).hexdigest(),'size_bytes':self.p.stat().st_size}
 def runextract(self):return extract(self.f,self.pin)
 def test_valid(self):self.assertEqual(self.runextract()[1]['outer_ring_count'],1)
 def test_missing_duplicate_wrong_bounds(self):
  e='<bounds minlon="0" minlat="0" maxlon="0.1" maxlat="0.1"/>'
  for x in [self.xml.replace(e,''),self.xml.replace(e,e+e),self.xml.replace('maxlon="0.1"','maxlon="0.09"')]:
   self.write(x)
   with self.subTest(xml=x[:80]),self.assertRaises(ValueError):self.runextract()
 def test_geometry_outside_bbox(self):
  x=self.xml.replace('lon="0.08"','lon="0.11"');self.write(x);g={'type':'MultiPolygon','coordinates':[[[[.02,.02],[.11,.02],[.11,.08],[.02,.02]]]]};self.f['geometry_sha256']=hashlib.sha256(json.dumps(g,sort_keys=True,separators=(',',':')).encode()).hexdigest()
  with self.assertRaisesRegex(ValueError,'outside export'):self.runextract()
 def test_source_hash_checked_during_bounds_read(self):
  self.pin['sha256']='0'*64
  with self.assertRaisesRegex(ValueError,'map export source hash mismatch'):self.runextract()
 def test_nonvisible_rejected(self):
  self.write(self.xml.replace('visible="true"','visible="false"',1))
  with self.assertRaisesRegex(ValueError,'non-visible'):self.runextract()
 def test_same_size_source_mutation_between_passes(self):
  from unittest.mock import patch
  import polygon_loader
  original=polygon_loader.validate_map_export_bounds
  def mutate_after_bounds(*args):
   result=original(*args);before=self.p.read_text();after=before.replace('Demo','Damo');assert len(before)==len(after);self.p.write_text(after);return result
  with patch.object(polygon_loader,'validate_map_export_bounds',side_effect=mutate_after_bounds):
   with self.assertRaisesRegex(ValueError,'hash mismatch'):extract(self.f,self.pin)
 def test_doctype_rejected(self):
  self.write('<!DOCTYPE osm [<!ENTITY x "oops">]>'+self.xml)
  with self.assertRaises(ValueError):self.runextract()
 def test_map_requires_archipelago_v4(self):
  self.f['source_class']='island'
  with self.assertRaises(ValueError):self.runextract()
if __name__=='__main__':unittest.main()
