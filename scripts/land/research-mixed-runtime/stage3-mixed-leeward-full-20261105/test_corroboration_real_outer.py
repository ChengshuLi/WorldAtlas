"""Synthetic real selector -> source-backed corroboration -> writer handoff.
Stage2 validation and unrelated point resolution remain mocked.
"""
import hashlib,json,unittest
from pathlib import Path
from unittest.mock import patch
import apply_selected_mixed as driver
from test_corroboration_outer import CorroborationOuter
from test_mixed_driver import js
class CorroborationRealOuter(unittest.TestCase):
 def test_real_polygon_and_corroboration_to_writer(self):
  t=CorroborationOuter();t.setUp();self.addCleanup(t.doCleanups);t.setup_corroboration()
  g={'type':'Polygon','coordinates':[[[0,55],[100,55],[100,89],[0,89],[0,55]]]};gh=hashlib.sha256(json.dumps(g,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest();data=json.dumps({'type':'FeatureCollection','features':[{'type':'Feature','properties':{'id':'f'},'geometry':g}]}).encode();p=t.src/'selector.geojson';p.write_bytes(data);h=hashlib.sha256(data).hexdigest()
  reqpath=Path(t.cfg['point_request']['path']);req=json.loads(reqpath.read_text());sp=Path(req['snapshot']['path']);snap=json.loads(sp.read_text())
  for name in ('sources','source_lineage_assets'):next(x for x in snap[name] if x['source_id']=='raw').update(sha256=h,size_bytes=len(data))
  next(x for x in snap['features'] if x['feature_id']=='f')['geometry_sha256']=gh;req['snapshot']=js(sp,snap);t.point['snapshot_sha256']=req['snapshot']['sha256'];t.cfg['point_request']=js(reqpath,req);t.cfg['polygon_source_files']=[{'source_id':'raw','version':'v','path':str(p),'sha256':h,'size_bytes':len(data)}];js(t.cfgpath,t.cfg)
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
  out=json.loads((t.b/'out/report.json').read_text());self.assertEqual(out['polygon_resolution']['claims'][0]['component_ids'],[11]);trace=out['administrative_corroboration'];self.assertEqual([(x['total_cells'],x['covered_centers'],x['outside_centers']) for x in trace['affiliations'][0]['rows']],[(3,3,0)]);self.assertEqual(out['writer']['polygon_root_statistics']['poly']['11']['applied_cells'],3)
if __name__=='__main__':unittest.main()
