"""Synthetic closed-way contract; no project geography."""
import copy,hashlib,json,tempfile,unittest
from pathlib import Path
from polygon_policy import adapt
from polygon_loader import extract
from test_polygon_policy import TestPolygonPolicy
from test_osm_closed_way import WayTest
class WayPolicy(unittest.TestCase):
 def setUp(self):
  f=TestPolygonPolicy();f.setUp();self.s=f.s;self.s['polygon_affiliation_feature_refs']=[];self.s['features']=self.s['features'][:1];self.a=self.s['affiliations'][0];self.a['method']='osm_way_component_containment_v1';self.a['evidence']['selector']={'additional_feature_ids':[],'include_witnesses':[],'exclude_witnesses':[],'way_version':'2','extractor_version':'osm-closed-way-map-export-v1','expected_identity_tags':{'name':'Demo','place':'islet','natural':'coastline'}};self.feature=self.s['features'][0];self.feature['source_feature_id']='7';self.asset=self.s['source_lineage_assets'][0];self.asset.update(source_uri='https://www.openstreetmap.org/export/finish',provider='OpenStreetMap contributors',license_name='ODbL 1.0',license_uri='https://www.openstreetmap.org/copyright',attribution='© OpenStreetMap contributors');proof={'status':'verified','method':'full-byte-compare',**{k:self.asset[k] for k in ('sha256','size_bytes','r2_bucket','r2_key')}};self.feature['evidence']={'source_format':'osm-xml','way_version':'2','geometry_hash_method':'binary64-sorted-compact-geojson-v1','osm_map_export':{'request_method':'POST','bounds':{'minlon':'0','minlat':'0','maxlon':'0.1','maxlat':'0.1'}},'r2_verification':proof}
 def test_valid_policy(self):
  d=adapt(self.s,{'a'})['decisions'][0];self.assertEqual(d['method'],'osm_way_component_containment_v1');self.assertEqual(d['features'][0]['source_class'],'island')
 def test_bad_source_origin_or_custody_rejected(self):
  for k,v in (('provider','evil'),('source_uri','https://evil.example/export/finish'),('license_uri','https://evil.example/'),('attribution','unrelated')):
   old=self.asset[k];self.asset[k]=v
   with self.subTest(k=k),self.assertRaises(ValueError):adapt(self.s,{'a'})
   self.asset[k]=old
  for k,v in (('status','unverified'),('sha256','0'*64),('size_bytes',11),('r2_bucket','other'),('r2_key','other')):
   proof=self.feature['evidence']['r2_verification'];old=proof[k];proof[k]=v
   with self.subTest(k=k),self.assertRaises(ValueError):adapt(self.s,{'a'})
   proof[k]=old
 def test_bad_selector_rejected(self):
  sel=self.a['evidence']['selector'];sel['include_witnesses']=[{'lon':'0','lat':'0'}]
  with self.assertRaisesRegex(ValueError,'containment requires'):adapt(self.s,{'a'})
  sel['include_witnesses']=[];sel['expected_identity_tags']['place']='archipelago'
  with self.assertRaisesRegex(ValueError,'way selector'):adapt(self.s,{'a'})
class WayLoader(unittest.TestCase):
 def test_actual_loader_with_synthetic_pinned_export(self):
  f=WayTest();f.setUp()
  try:
   feature={'source_format':'osm-xml','source_class':'island','extractor_version':'osm-closed-way-map-export-v1','source_feature_id':'7','way_version':'2','expected_identity_tags':f.tags,'map_export_bounds':f.bounds,'geometry_sha256':f.geom};pin={'path':str(f.p),'sha256':f.sha,'size_bytes':f.p.stat().st_size};g,t=extract(feature,pin);self.assertEqual(g['type'],'MultiPolygon');self.assertEqual(t['way_id'],'7')
   pin['sha256']='0'*64
   with self.assertRaisesRegex(ValueError,'source hash mismatch'):extract(feature,pin)
  finally:f.doCleanups()

class WayResolution(unittest.TestCase):
 def test_source_way_selects_only_wholly_covered_component(self):
  import struct,polygon_resolution,mixed_claims
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);u=lambda n,v:(p/n).write_bytes(struct.pack('<'+'I'*len(v),*v));u('pr',[0,3,4]);u('pv',[1024,1,1027,17,2048,1,2048,1]);u('cr',[0,2,2]);u('cv',[1024,1026,10,1026,1027,11]);sha=lambda f:hashlib.sha256(Path(f).read_bytes()).hexdigest();inputs={k:{'path':str(p/n),'sha256':sha(p/n)} for k,n in (('physical_rows','pr'),('physical_runs','pv'),('component_rows','cr'),('component_runs','cv'))}
   raw='''<osm><bounds minlon="0" minlat="89.7" maxlon="0.4" maxlat="90"/><node id="1" visible="true" lon="0.01" lat="89.72"/><node id="2" visible="true" lon="0.35" lat="89.72"/><node id="3" visible="true" lon="0.35" lat="89.99"/><node id="4" visible="true" lon="0.01" lat="89.99"/><way id="7" version="2" visible="true"><nd ref="1"/><nd ref="2"/><nd ref="3"/><nd ref="4"/><nd ref="1"/><tag k="name" v="Demo"/><tag k="place" v="islet"/><tag k="natural" v="coastline"/></way></osm>''';f=p/'source.osm';f.write_text(raw);fixture=WayPolicy();fixture.setUp();s=fixture.s;source=s['sources'][0];asset=s['source_lineage_assets'][0]
   for v in (source,asset):v['sha256']=sha(f);v['size_bytes']=f.stat().st_size
   evidence=s['features'][0]['evidence'];evidence['r2_verification'].update(sha256=sha(f),size_bytes=f.stat().st_size);evidence['osm_map_export']['bounds']={'minlon':'0','minlat':'89.7','maxlon':'0.4','maxlat':'90'};geom={'type':'MultiPolygon','coordinates':[[[[.01,89.72],[.35,89.72],[.35,89.99],[.01,89.99],[.01,89.72]]]]};s['features'][0]['geometry_sha256']=hashlib.sha256(json.dumps(geom,sort_keys=True,separators=(',',':')).encode()).hexdigest();s['entity_revision']={'id':'e'};s['category_bindings']=[{'entity_id':3,'code':19,'physical_class':'land'}];policy=adapt(s,{'a'});files=[{**source,'path':str(f)}];grid={'width':2048,'height':2,'west':-180,'north':90,'step':360/2048};res=polygon_resolution.resolve(policy,s,files,grid,inputs);claim=res['claims'][0];self.assertEqual(claim['component_ids'],[10]);self.assertEqual(claim['containment']['selected_cells'],2);self.assertEqual(claim['entity_code'],19)
   compiled={'revision':'r','entity_revision':'e','affiliation_ids':['a'],'affiliation_entry_links':{'a':['entry']}};self.assertEqual(mixed_claims.combine(compiled,s,[res],{99})[10][0]['code'],19)

if __name__=='__main__':unittest.main()
