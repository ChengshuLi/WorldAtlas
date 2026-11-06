"""Real OSM point resolver -> reviewed point validator -> mixed claim handoff.

The polygon report is deliberately synthetic. This does not establish a real
source selection or substitute for the full-source integration test.
"""
import importlib.util,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
P=ROOT/'geonames-point-integration-20261105/point-component-prototype';sys.path.insert(0,str(P));import resolve
from test_group_integration import GroupIntegrationTests
from test_resolve import put
import mixed_claims
spec=importlib.util.spec_from_file_location('reviewed_node_claim_validator',ROOT/'geonames-point-claim-validator-20261105/point_claim_validator.py');point_validator=importlib.util.module_from_spec(spec);spec.loader.exec_module(point_validator)
class RealPointHandoff(unittest.TestCase):
 def test_real_resolver_point_plus_polygon(self):
  fixture=GroupIntegrationTests('test_group_end_to_end');fixture.setUp();self.addCleanup(fixture.doCleanups);d=fixture.group_fixture();d['affiliations'].append({'affiliation_id':'poly','method':'component_intersection_v1','entity_id':42,'scope':'land','relationship':'affiliation'});fixture.req['snapshot']=put(fixture.p/'combined.json',d);actual=resolve.resolve(fixture.req)
  compiled={'revision':'draft-1','entity_revision':'ent-1','affiliation_ids':['a','poly'],'affiliation_entry_links':{'a':['point-entry'],'poly':['polygon-entry']}};partial={**compiled,'affiliation_ids':['a']};verified=point_validator.claims_for(partial,d,actual);self.assertEqual(verified[7][0]['affiliation_id'],'a');self.assertEqual(actual['claims'][0]['identity_scope'],'island_group');self.assertEqual(actual['claims'][0]['group_identity'],'Test group')
  polygon={'schema':'source-polygon-component-report-v1','status':'research-only-not-a-build','revision':'draft-1','entity_revision':'ent-1','claims':[{'affiliation_id':'poly','method':'component_intersection_v1','entity_id':42,'entity_code':18,'component_ids':[8]}]};mixed=mixed_claims.combine(compiled,d,[actual,polygon],{99});self.assertEqual(set(mixed),{7,8});self.assertEqual(mixed[7][0]['entry_ids'],['point-entry']);self.assertEqual(mixed[8][0]['entry_ids'],['polygon-entry'])
if __name__=='__main__':unittest.main()
