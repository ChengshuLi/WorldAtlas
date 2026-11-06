"""Regression: real outer driver must route selected anchors into polygon policy."""
import json
from pathlib import Path
from unittest.mock import patch
import apply_selected_mixed as driver
from test_mixed_driver import DriverTests,js
class AnchorOuterRouteTests(DriverTests):
 def test_anchor_method_reaches_polygon_resolution(self):
  reqpath=Path(self.cfg['point_request']['path']);req=json.loads(reqpath.read_text());sp=Path(req['snapshot']['path']);snap=json.loads(sp.read_text());a=snap['affiliations'][1];a['method']='osm_archipelago_anchored_rings_intersection_v1';a['evidence']['selector']={'additional_feature_ids':[],'include_witnesses':[],'exclude_witnesses':[],'relation_version':'13','extractor_version':'osm-anchored-outer-rings-v1','expected_identity_tags':{'name':'Dodecanese','place':'archipelago'},'anchors':[{'node_id':'4','node_version':'1','way_id':'7','expected_tags':{'name':'Rhodos','amenity':'ferry_terminal'},'geometry_sha256':'c'*64}]};snap['features'][0].update(source_feature_id='20',evidence={'source_format':'osm-xml','relation_version':'13','geometry_hash_method':'binary64-sorted-compact-geojson-v1'});snap['source_lineage_assets'][0]['source_uri']='https://api.openstreetmap.org/api/0.6/relation/20/full';req['snapshot']=js(sp,snap);self.point['snapshot_sha256']=req['snapshot']['sha256'];self.cfg['point_request']=js(reqpath,req);self.poly['claims'][0]['method']='osm_archipelago_anchored_rings_intersection_v1';js(self.cfgpath,self.cfg);calls=[]
  class Validator:
   @staticmethod
   def validate(*a):return {'status':'diagnostic-candidate-bound'}
  class Resolver:
   def resolve(s,r):return self.point
   def lineage_specs(s,m):return []
  class PointValidator:
   @staticmethod
   def claims_for(*args):return {}
  def module(name,path):return Validator if name=='stage2_candidate_validator' else (PointValidator if name=='reviewed_point_claim_validator' else Resolver())
  def resolve(policy,*args):
   calls.extend(policy['decisions']);self.assertEqual([x['affiliation_id'] for x in calls],['poly']);self.assertEqual(calls[0]['method'],'osm_archipelago_anchored_rings_intersection_v1');return self.poly
  with patch.object(driver,'loadmodule',side_effect=module),patch.object(driver.polygon_resolution,'resolve',side_effect=resolve):driver.run(self.cfgpath)
  self.assertEqual(len(calls),1);r=json.loads((self.b/'out/report.json').read_text());self.assertEqual(r['polygon_resolution']['claims'][0]['method'],'osm_archipelago_anchored_rings_intersection_v1')
