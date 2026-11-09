import hashlib,json
from pathlib import Path
from test_mixed_driver import DriverTests,js
import corroboration_adapter as adapter,corroboration_source as source
class CorroborationOuter(DriverTests):
 def setup_corroboration(self):
  g={'type':'Polygon','coordinates':[[[0,60,0],[110,60,0],[110,80,0],[0,80,0],[0,60,0]]]};gh=hashlib.sha256(json.dumps(g,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest();doc={'type':'FeatureCollection','crs':source.CRS,'features':[{'type':'Feature','properties':{'cistat':'1','nome':'ONE'},'geometry':g}]};data=json.dumps(doc).encode();p=self.src/'admin.geojson';p.write_bytes(data);h=hashlib.sha256(data).hexdigest();pin={'source_id':'admin','version':'v','sha256':h,'r2_bucket':'bucket','r2_key':'admin','size_bytes':len(data)};asset={**pin,'kind':'raw','source_uri':adapter.OFFICIAL_URI,'provider':'regional','attribution':'authority','license_name':'Unspecified','provenance':{'representation':'worker_reported_provider_response','original_http_metadata':'headers and capture timestamp not retained'}}
  reqp=Path(self.cfg['point_request']['path']);req=json.loads(reqp.read_text());sp=Path(req['snapshot']['path']);snap=json.loads(sp.read_text());snap['schema']='worldatlas-geography-decision-draft-evidence-v2';snap['sources'].append(pin);snap['source_lineage_assets'].append(asset);snap['features'].append({'feature_id':'admin-feature','source_id':'admin','source_version':'v','source_feature_id':'1','geometry_sha256':gh,'evidence':{'source_format':'geojson','selector_property':'cistat','expected_name':'ONE','coordinate_method':source.METHOD,'geometry_hash_method':source.HASH_METHOD}});snap['affiliations'][1]['evidence']['polygon_corroboration_mode']='administrative_geometry_v1';snap['polygon_corroboration_refs']=[{'decision_revision':'r','affiliation_id':'poly','selected_feature_id':'f','corroborating_feature_id':'admin-feature'}];req['snapshot']=js(sp,snap);self.point['snapshot_sha256']=req['snapshot']['sha256'];self.cfg['point_request']=js(reqp,req);self.cfg['corroboration_source_files']=[{**pin,'path':str(p)}];self.poly['claims'][0]['source_features']=[{'feature_id':'f','source_id':'raw','source_version':'v','geometry_sha256':'b'*64,'source_sha256':'a'*64}]
 def test_v3_standalone_rejects_unsupported_source_flags(self):
  import polygon_policy
  self.setup_corroboration();req=json.loads(Path(self.cfg['point_request']['path']).read_text());snap=json.loads(Path(req['snapshot']['path']).read_text());snap.update(schema='worldatlas-geography-decision-draft-evidence-v3',ecoregion_source_refs=[],unsupported_affiliation_source_ref_table_present=False,unsupported_point_methods_present=False,affiliation_source_refs=[]);policy=polygon_policy.adapt(snap,{'poly'});adapter.adapt(snap,policy)
  for key in ('unsupported_affiliation_source_ref_table_present','unsupported_point_methods_present'):
   snap[key]=True
   with self.assertRaisesRegex(ValueError,'unsupported affiliation-source table status'):adapter.adapt(snap,policy)
   snap[key]=False
 def test_real_corroboration_reaches_writer_report(self):
  self.setup_corroboration();self.runv();report=json.loads((self.b/'out/report.json').read_text());trace=report['administrative_corroboration'];self.assertEqual(trace['status'],'research-evidence-not-a-selector');self.assertEqual(trace['affiliations'][0]['rows'][0]['total_cells'],3);self.assertEqual(trace['affiliations'][0]['rows'][0]['covered_centers'],3);self.assertEqual(report['writer']['changed_cells'],6)
 def test_unverified_stream_lineage_stops_before_output(self):
  self.setup_corroboration();self.poly['input_sha256']['physical_rows']='0'*64
  with self.assertRaisesRegex(ValueError,'polygon resolution'):self.runv()
  self.assertFalse((self.b/'out').exists())
 def test_administrative_source_not_polygon_source(self):
  self.setup_corroboration();self.cfg['polygon_source_files']=[self.cfg['corroboration_source_files'][0]]
  with self.assertRaisesRegex(ValueError,'paths overlap'):self.runv()
  self.assertFalse((self.b/'out').exists())
if __name__=='__main__':__import__('unittest').main()
