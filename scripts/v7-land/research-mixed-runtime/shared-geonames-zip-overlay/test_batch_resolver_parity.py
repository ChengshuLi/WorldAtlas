"""Small two-component integration parity against the pinned original resolver."""
import copy, hashlib, importlib.util, io, json, unittest, zipfile
from pathlib import Path
from unittest.mock import patch
import resolve
from test_geonames_integration import GeoNamesIntegration
from test_resolve import put,packed
class BatchResolverParity(GeoNamesIntegration):
 def test_two_geo_points_same_zip_equal_original(self):
  d=self.fixture(); p=self.p
  # Two valid GeoNames points in separate components but one pinned source ZIP.
  def row(rid,name,lon): return '\t'.join([rid,name,name,'','22.5',str(lon),'T','ISL','ZZ','','','','','','0','','','Pacific/Test','2020-01-01'])+'\n'
  b=io.BytesIO()
  with zipfile.ZipFile(b,'w',compression=zipfile.ZIP_DEFLATED) as z:z.writestr('ZZ.txt',row('123','Test place',-112.5)+row('456','Second place',-67.5))
  zpin=put(p/'source.zip',b.getvalue());self.req['source_files'][0].update(zpin)
  for a in d['sources']+d['source_lineage_assets']:
   if a['source_id']=='p':a['sha256']=zpin['sha256'];a['size_bytes']=len(b.getvalue())
  identity=json.loads((p/'identity.txt').read_bytes());identity['features'][0]['geometry']['coordinates']=[[[-150,0],[-50,0],[-50,45],[-150,45],[-150,0]]];ip=put(p/'identity.txt',identity);self.req['source_files'][1].update(ip)
  for a in d['sources']+d['source_lineage_assets']:
   if a['source_id']=='i':a['sha256']=ip['sha256'];a['size_bytes']=(p/'identity.txt').stat().st_size
  d['features'][1]['geometry_sha256']=resolve.geometry_sha(identity['features'][0]['geometry'])
  f=copy.deepcopy(d['features'][0]);f.update(feature_id='f2',source_feature_id='456',geometry_sha256=resolve.geometry_sha({'type':'Point','coordinates':[-67.5,22.5]}));d['features'].append(f)
  a=copy.deepcopy(d['affiliations'][0]);a.update(affiliation_id='b',feature_id='f2');a['evidence']['selector']['point_name']='Second place';d['affiliations'].append(a);d['affiliation_feature_refs'].append({'affiliation_id':'b','role':'identity_polygon','feature_id':'identity-feature'});self.req['snapshot']=put(p/'combined.json',d)
  cr=put(p/'cr',packed('<I',[(0,),(2,),(4,),(6,),(8,)]));cs=put(p/'cs',packed('<III',[(1,2,7),(2,4,8)]*4));self.req['component_rows']=cr;self.req['component_runs']=cs;self.manifest['pins']['component_rows']=cr;self.manifest['pins']['component_runs']=cs;self.req['component_manifest']=put(p/'manifest',self.manifest)
  optimized=resolve.resolve(self.req);self.assertEqual([x['component_id'] for x in optimized['claims']],[7,8])
  oldpath=Path.cwd()/'lydekker-line-runtime-prototype-20261105/point-integration/point-component-prototype/resolve.py'
  # Test is launched from repo root with prototype directory in sys.path.
  spec=importlib.util.spec_from_file_location('old_point_resolver',oldpath);old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old);req=copy.deepcopy(self.req);req['resolver_sha256']=old.digest(oldpath);req['geonames_extractor_sha256']=old.digest(oldpath.with_name('geonames_extract.py'))
  with patch.object(old,'available_memory_kib',return_value=4000000):baseline=old.resolve(req)
  def semantic(claims):return [{k:v for k,v in c.items() if k!='identity_memory_monitor'} for c in claims]
  self.assertEqual(semantic(optimized['claims']),semantic(baseline['claims']))
if __name__=='__main__':unittest.main()
