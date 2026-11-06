import copy,hashlib,json,unittest
from unittest.mock import patch
from test_land_archive_contract import ArchivePolicy
from test_polygon_resolution import ResolveTests
import polygon_policy,polygon_resolution,mixed_claims
class ArchiveContainmentPolicy(ArchivePolicy):
 def setUp(self):
  super().setUp();self.a['method']='osm_land_archive_component_containment_v1'
 def test_valid_policy(self):
  d=polygon_policy.adapt(self.s,{'a'});self.assertEqual(d['decisions'][0]['method'],self.a['method']);self.assertEqual(d['decisions'][0]['features'][0]['source_format'],'osm-split-land-shapefile')
 def test_reject_extra_source(self):
  a=self.a;a['evidence']['selector']['additional_feature_ids']=['other'];self.s['polygon_affiliation_feature_refs']=[{'affiliation_id':'a','role':'additional_polygon','feature_id':'other'}]
  with self.assertRaises(ValueError):polygon_policy.adapt(self.s,{'a'})
class ArchiveContainmentResolution(ResolveTests):
 def configure(self,geometry):
  # Synthetic pinned source and streams, actual intersection and all-center selector.
  a=self.snap['affiliations'][0];a['method']='osm_land_archive_component_containment_v1';a['evidence']['selector']['extractor_version']='osm-split-land-archive-v1';f=self.snap['features'][0];f['source_feature_id']='0';f['evidence']={'source_format':'osm-split-land-shapefile','geometry_hash_method':'binary64-sorted-compact-geojson-v1'};asset=self.snap['source_lineage_assets'][0];asset.update(source_uri='https://www.osmdata.org/download/land-polygons-split-4326.zip',provider='OpenStreetMap contributors; osmdata.openstreetmap.de, via unofficial North America mirror',license_name='Open Data Commons Open Database License 1.0',license_uri='https://opendatacommons.org/licenses/odbl/1-0/',attribution='© OpenStreetMap contributors, https://www.openstreetmap.org/copyright',provenance={'origin':'unofficial North America mirror of osmdata.openstreetmap.de','verification':'full R2 object readback SHA-256 and size match the locally retrieved archive'});self.policy=polygon_policy.adapt(self.snap,{'a'});self.geom=geometry
 def result(self):
  with patch.object(polygon_resolution.polygon_loader,'extract_land_many',side_effect=lambda features,source:[(self.geom,{'source_feature_id':f['source_feature_id']}) for f in features]):return self.runv()
 def test_partial_main_excluded_full_fragment_selected(self):
  self.configure({'type':'Polygon','coordinates':[[[-105,55],[40,55],[40,89],[-105,89],[-105,55]]]});claim=self.result()['claims'][0];self.assertEqual(claim['component_ids'],[10]);self.assertEqual(claim['containment']['excluded_partial_components'],[{'component_id_evidence_only':11,'inside_cells':1,'whole_cells':3}]);compiled={'revision':'r','entity_revision':'e','affiliation_ids':['a'],'affiliation_entry_links':{'a':['entry']}};self.assertEqual(mixed_claims.combine(compiled,self.snap,[self.result()],{99})[10][0]['code'],19)
 def test_no_fully_covered_component_fails(self):
  self.configure({'type':'Polygon','coordinates':[[[-68,55],[-30,55],[-30,89],[-68,89],[-68,55]]]})
  with self.assertRaisesRegex(ValueError,'no wholly covered components'):self.result()
 def test_multipolygon_fails_closed(self):
  self.configure({'type':'MultiPolygon','coordinates':[[[[-105,55],[40,55],[40,89],[-105,89],[-105,55]]]]})
  with self.assertRaisesRegex(ValueError,'invalid containment polygon'):self.result()
