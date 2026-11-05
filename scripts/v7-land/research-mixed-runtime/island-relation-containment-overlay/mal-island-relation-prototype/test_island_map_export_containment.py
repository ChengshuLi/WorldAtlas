import copy,unittest
from test_map_export_contract import PolicyContract,LoaderContract,B
from polygon_policy import adapt
from polygon_loader import extract
class IslandPolicy(PolicyContract):
 def setUp(self):
  super().setUp();a=self.s['affiliations'][0];a['method']='osm_relation_component_containment_v1';a['evidence']['selector']['expected_identity_tags']['place']='island';self.asset.update(provider='OpenStreetMap contributors',license_uri='https://www.openstreetmap.org/copyright');self.s['features'][0]['evidence']['osm_map_export']=self.asset['provenance'].pop('osm_map_export')
 def test_valid_export(self):
  d=adapt(self.s,{'a'})['decisions'][0];self.assertEqual(d['features'][0]['map_export_bounds'],B);self.assertEqual(d['features'][0]['source_class'],'island')
 def test_reject_wrong_export_data(self):
  f=self.s['features'][0]['evidence'];orig=copy.deepcopy(f)
  for key in ('r2_verification','osm_map_export'):
   del f[key]
   with self.subTest(field=key),self.assertRaises(ValueError):adapt(self.s,{'a'})
   f.update(copy.deepcopy(orig))
  for u in ('https://evil.example/export/finish','http://www.openstreetmap.org/export/finish','https://www.openstreetmap.org/export/finish?q=x','https://api.openstreetmap.org/api/0.6/relation/9/full'):
   self.asset['source_uri']=u
   with self.subTest(url=u),self.assertRaises(ValueError):adapt(self.s,{'a'})
 def test_reject_non_island_or_witness(self):
  s=self.s['affiliations'][0]['evidence']['selector'];s['expected_identity_tags']['place']='archipelago'
  with self.assertRaises(ValueError):adapt(self.s,{'a'})
  s['expected_identity_tags']['place']='island';s['include_witnesses']=[{'x':1}]
  with self.assertRaises(ValueError):adapt(self.s,{'a'})
 # Parent variants use a different provenance layout; covered by the dedicated tests here.
 test_reject_host_path_query_and_bad_method=None
 test_reject_missing_custody_or_provider=None
 test_reject_bad_bounds=None
 test_relation_full_back_compat=None
class IslandLoader(LoaderContract):
 def setUp(self):
  super().setUp();self.xml=self.xml.replace('v="archipelago"','v="island"');self.write(self.xml);self.f['source_class']='island';self.f['expected_identity_tags']['place']='island'
 def test_map_requires_archipelago_v4(self):
  self.assertEqual(self.runextract()[1]['outer_ring_count'],1)
  self.f['extractor_version']='osm-multipolygon-outer-v3'
  with self.assertRaises(ValueError):self.runextract()
if __name__=='__main__':unittest.main()
class IslandResolution(unittest.TestCase):
 def test_only_whole_components_and_mixed_claim(self):
  import hashlib,json,tempfile,struct,polygon_resolution,mixed_claims
  from pathlib import Path
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);u=lambda n,v:(p/n).write_bytes(struct.pack('<'+'I'*len(v),*v));u('pr',[0,3,4]);u('pv',[1024,1,1027,17,2048,1,2048,1]);u('cr',[0,2,2]);u('cv',[1024,1026,10,1026,1027,11]);sha=lambda f:hashlib.sha256(Path(f).read_bytes()).hexdigest();inputs={k:{'path':str(p/n),'sha256':sha(p/n)} for k,n in (('physical_rows','pr'),('physical_runs','pv'),('component_rows','cr'),('component_runs','cv'))}
   raw='''<osm><bounds minlon="0" minlat="89.7" maxlon="0.4" maxlat="90"/><node id="1" visible="true" lon="0.01" lat="89.72"/><node id="2" visible="true" lon="0.35" lat="89.72"/><node id="3" visible="true" lon="0.35" lat="89.99"/><node id="4" visible="true" lon="0.01" lat="89.99"/><way id="7" visible="true"><nd ref="1"/><nd ref="2"/><nd ref="3"/><nd ref="4"/><nd ref="1"/></way><relation id="9" version="2" visible="true"><member type="way" ref="7" role="outer"/><tag k="type" v="multipolygon"/><tag k="name" v="Demo"/><tag k="place" v="island"/></relation></osm>''';f=p/'source.osm';f.write_text(raw);fixture=IslandPolicy();fixture.setUp();s=fixture.s;source=s['sources'][0];asset=s['source_lineage_assets'][0]
   for v in (source,asset):v['sha256']=sha(f);v['size_bytes']=f.stat().st_size
   evidence=s['features'][0]['evidence'];evidence['r2_verification'].update(sha256=sha(f),size_bytes=f.stat().st_size);evidence['osm_map_export']['bounds']={'minlon':'0','minlat':'89.7','maxlon':'0.4','maxlat':'90'};geom={'type':'MultiPolygon','coordinates':[[[[.01,89.72],[.35,89.72],[.35,89.99],[.01,89.99],[.01,89.72]]]]};s['features'][0]['geometry_sha256']=hashlib.sha256(json.dumps(geom,sort_keys=True,separators=(',',':')).encode()).hexdigest();s['entity_revision']={'id':'e'};s['category_bindings']=[{'entity_id':3,'code':19,'physical_class':'land'}];policy=adapt(s,{'a'});files=[{**source,'path':str(f)}];grid={'width':2048,'height':2,'west':-180,'north':90,'step':360/2048};res=polygon_resolution.resolve(policy,s,files,grid,inputs,lambda:None);claim=res['claims'][0];self.assertEqual(claim['component_ids'],[10]);self.assertEqual(claim['containment']['selected_cells'],2);compiled={'revision':'r','entity_revision':'e','affiliation_ids':['a'],'affiliation_entry_links':{'a':['entry']}};self.assertEqual(mixed_claims.combine(compiled,s,[res],{99})[10][0]['code'],19)
class IslandNegativePolicy(unittest.TestCase):
 def fixture(self):
  f=IslandPolicy();f.setUp();return f
 def test_all_custody_fields_and_providers(self):
  for key in ('status','method','sha256','size_bytes','r2_bucket','r2_key'):
   f=self.fixture();f.s['features'][0]['evidence']['r2_verification'][key]=None
   with self.subTest(key=key),self.assertRaises(ValueError):adapt(f.s,{'a'})
  for key in ('provider','license_name','license_uri','attribution'):
   f=self.fixture();f.asset[key]='other'
   with self.subTest(key=key),self.assertRaises(ValueError):adapt(f.s,{'a'})
 def test_invalid_bounds_and_request(self):
  for bounds in ({},dict(B,minlon='NaN'),dict(B,maxlon='-1'),dict(B,maxlon='10',maxlat='10'),dict(B,minlon=0)):
   f=self.fixture();f.s['features'][0]['evidence']['osm_map_export']['bounds']=bounds
   with self.subTest(bounds=bounds),self.assertRaises(ValueError):adapt(f.s,{'a'})
  f=self.fixture();f.s['features'][0]['evidence']['osm_map_export']['request_method']='GET'
  with self.assertRaises(ValueError):adapt(f.s,{'a'})
 def test_extractor_identity_and_witness_policies(self):
  for mutation in ('extractor','relation_version','extra','witness','name','place'):
   f=self.fixture();sel=f.s['affiliations'][0]['evidence']['selector']
   if mutation=='extractor':sel['extractor_version']='osm-multipolygon-outer-v3'
   if mutation=='relation_version':sel['relation_version']='0'
   if mutation=='extra':sel['additional_feature_ids']=['other']
   if mutation=='witness':sel['exclude_witnesses']=[{'x':1}]
   if mutation=='name':sel['expected_identity_tags'].pop('name')
   if mutation=='place':sel['expected_identity_tags']['place']='archipelago'
   with self.subTest(mutation=mutation),self.assertRaises(ValueError):adapt(f.s,{'a'})
