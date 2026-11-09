import unittest
from test_polygon_policy import TestPolygonPolicy
from test_polygon_loader import LoaderTests
from polygon_policy import adapt
from polygon_loader import extract
class ArchipelagoPolicyTests(TestPolygonPolicy):
 def setup_group(self):
  a=self.s['affiliations'][0];a['method']='osm_archipelago_component_intersection_v1';a['evidence']['selector']={'additional_feature_ids':[],'include_witnesses':[],'exclude_witnesses':[],'relation_version':'53','extractor_version':'osm-multipolygon-outer-v4','expected_identity_tags':{'name':'Obi Islands','place':'archipelago'}};self.s['polygon_affiliation_feature_refs']=[];f=self.s['features'][0];f['source_feature_id']='5231220';f['evidence']={'source_format':'osm-xml','relation_version':'53','geometry_hash_method':'binary64-sorted-compact-geojson-v1'};self.s['source_lineage_assets'][0]['source_uri']='https://api.openstreetmap.org/api/0.6/relation/5231220/full'
 def test_archipelago_contract(self):
  self.setup_group();x=adapt(self.s,{'a'})['decisions'][0];self.assertEqual(x['features'][0]['source_class'],'archipelago');self.assertEqual(x['method'],'osm_archipelago_component_intersection_v1')
 def test_wrong_tags_and_uri_and_witness_fail(self):
  self.setup_group();a=self.s['affiliations'][0];a['evidence']['selector']['expected_identity_tags']['place']='island'
  with self.assertRaises(ValueError):adapt(self.s,{'a'})
  a['evidence']['selector']['expected_identity_tags']['place']='archipelago';self.s['source_lineage_assets'][0]['source_uri']='https://example.com/not-official'
  with self.assertRaises(ValueError):adapt(self.s,{'a'})
  self.s['source_lineage_assets'][0]['source_uri']='https://api.openstreetmap.org/api/0.6/relation/5231220/full';a['evidence']['selector']['include_witnesses']=[{'lon':'1','lat':'2'}]
  with self.assertRaises(ValueError):adapt(self.s,{'a'})
class ArchipelagoLoaderTests(LoaderTests):
 def test_archipelago_tag_handoff(self):
  import hashlib
  xml=self.xml.replace('<tag k="type" v="multipolygon"/>','<tag k="type" v="multipolygon"/><tag k="name" v="Obi Islands"/><tag k="place" v="archipelago"/>');self.p.write_text(xml);self.pin['size_bytes']=self.p.stat().st_size;self.pin['sha256']=hashlib.sha256(self.p.read_bytes()).hexdigest();self.f.update(source_class='archipelago',extractor_version='osm-multipolygon-outer-v4',expected_identity_tags={'name':'Obi Islands','place':'archipelago'});self.assertEqual(extract(self.f,self.pin)[1]['verified_identity_tags']['place'],'archipelago');self.f['expected_identity_tags']['place']='island'
  with self.assertRaises(ValueError):extract(self.f,self.pin)
if __name__=='__main__':unittest.main()

from test_mixed_driver import DriverTests,js
import json
from pathlib import Path
class GroupOuterDriverTests(DriverTests):
 def group(self):
  reqpath=Path(self.cfg['point_request']['path']);req=json.loads(reqpath.read_text());sp=Path(req['snapshot']['path']);snap=json.loads(sp.read_text());a=snap['affiliations'][1];a['method']='osm_archipelago_component_intersection_v1';a['evidence']['selector']={'additional_feature_ids':[],'include_witnesses':[],'exclude_witnesses':[],'relation_version':'10','extractor_version':'osm-multipolygon-outer-v4','expected_identity_tags':{'name:en':'Obi Islands','place':'archipelago'}};f=snap['features'][0];f.update(source_feature_id='5231220',evidence={'source_format':'osm-xml','relation_version':'10','geometry_hash_method':'binary64-sorted-compact-geojson-v1'});snap['source_lineage_assets'][0]['source_uri']='https://api.openstreetmap.org/api/0.6/relation/5231220/full';req['snapshot']=js(sp,snap);self.point['snapshot_sha256']=req['snapshot']['sha256'];self.cfg['point_request']=js(reqpath,req);self.poly['claims'][0]['method']='osm_archipelago_component_intersection_v1'
 def test_group_reaches_mixed_writer(self):
  self.group();self.runv();r=json.loads((self.b/'out/report.json').read_text());self.assertEqual(r['polygon_resolution']['claims'][0]['method'],'osm_archipelago_component_intersection_v1');self.assertEqual(r['writer']['changed_cells'],6)
 def test_group_mainland_rejected(self):
  self.group();self.poly['claims'][0]['component_ids']=[99]
  with self.assertRaisesRegex(ValueError,'mainland'):self.runv()
