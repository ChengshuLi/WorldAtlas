"""Actual label-aware source -> policy -> loader -> component -> mixed writer fixture.
Stage2 validation and unrelated point resolution are intentionally mocked.
"""
import hashlib,json,unittest
from pathlib import Path
from unittest.mock import patch
import apply_selected_mixed as driver
from test_mixed_driver import DriverTests,js
class LabelOuterReal(unittest.TestCase):
 def test_actual_label_source_and_writer(self):
  t=DriverTests();t.setUp();self.addCleanup(t.doCleanups)
  raw=b'<osm><node id="1" lon="0" lat="55"/><node id="2" lon="100" lat="55"/><node id="3" lon="100" lat="89"/><node id="4" lon="0" lat="89"/><node id="99" version="1" lon="50" lat="70"><tag k="note" v="label"/></node><way id="10"><nd ref="1"/><nd ref="2"/><nd ref="3"/><nd ref="4"/><nd ref="1"/></way><relation id="20" version="4"><member type="way" ref="10" role="outer"/><member type="node" ref="99" role="label"/><tag k="type" v="multipolygon"/><tag k="place" v="archipelago"/><tag k="name" v="Demo"/></relation></osm>'
  src=t.src/'group.osm';src.write_bytes(raw);h=hashlib.sha256(raw).hexdigest();ring=[[0.,55.],[100.,55.],[100.,89.],[0.,89.],[0.,55.]];gh=hashlib.sha256(json.dumps({'type':'MultiPolygon','coordinates':[[ring]]},sort_keys=True,separators=(',',':')).encode()).hexdigest()
  reqpath=Path(t.cfg['point_request']['path']);req=json.loads(reqpath.read_text());sp=Path(req['snapshot']['path']);snap=json.loads(sp.read_text())
  for x in (snap['sources'][0],snap['source_lineage_assets'][0]):x.update(sha256=h,size_bytes=len(raw))
  snap['source_lineage_assets'][0]['source_uri']='https://api.openstreetmap.org/api/0.6/relation/20/full';snap['features'][0].update(source_feature_id='20',geometry_sha256=gh,evidence={'source_format':'osm-xml','relation_version':'4','geometry_hash_method':'binary64-sorted-compact-geojson-v1'});a=snap['affiliations'][1];a['method']='osm_archipelago_component_intersection_v1';a['evidence']['selector']={'additional_feature_ids':[],'include_witnesses':[],'exclude_witnesses':[],'relation_version':'4','extractor_version':'osm-multipolygon-outer-label-v1','expected_identity_tags':{'name':'Demo','place':'archipelago'},'label_node_id':'99','label_node_version':'1','expected_label_tags':{'note':'label'}}
  req['snapshot']=js(sp,snap);t.point['snapshot_sha256']=req['snapshot']['sha256'];t.cfg['point_request']=js(reqpath,req);t.cfg['polygon_source_files']=[{'source_id':'raw','version':'v','path':str(src),'sha256':h,'size_bytes':len(raw)}];js(t.cfgpath,t.cfg)
  class Validator:
   @staticmethod
   def validate(*a):return {'status':'diagnostic-candidate-bound'}
  class Resolver:
   def resolve(self,r):return t.point
   def lineage_specs(self,m):return []
  class PointValidator:
   @staticmethod
   def claims_for(*a):return {}
  def module(name,path):return {'stage2_candidate_validator':Validator,'stage3_point_resolver':Resolver(),'reviewed_point_claim_validator':PointValidator}[name]
  with patch.object(driver,'loadmodule',side_effect=module):driver.run(t.cfgpath)
  out=json.loads((t.b/'out/report.json').read_text());claim=out['polygon_resolution']['claims'][0];self.assertEqual(claim['component_ids'],[11]);self.assertEqual(claim['source_features'][0]['verified_label_tags'],{'note':'label'});self.assertEqual(out['writer']['polygon_root_statistics']['poly']['11']['applied_cells'],3)
if __name__=='__main__':unittest.main()
