"""Synthetic contract tests for archive source policy and dispatch."""
import copy,hashlib,json,unittest
from pathlib import Path
from test_polygon_policy import TestPolygonPolicy
from test_land_archive_source import Contract as ArchiveFixture
import polygon_policy,polygon_loader
class ArchivePolicy(unittest.TestCase):
 def setUp(self):
  f=TestPolygonPolicy();f.setUp();self.s=f.s;self.s['polygon_affiliation_feature_refs']=[];self.s['features']=self.s['features'][:1];self.a=self.s['affiliations'][0];self.a['method']='osm_land_archive_component_intersection_v1';self.a['evidence']['selector']={'additional_feature_ids':[],'include_witnesses':[],'exclude_witnesses':[],'extractor_version':'osm-split-land-archive-v1'};self.feature=self.s['features'][0];self.feature['source_feature_id']='0';self.feature['evidence']={'source_format':'osm-split-land-shapefile','geometry_hash_method':'binary64-sorted-compact-geojson-v1'};self.asset=self.s['source_lineage_assets'][0];self.asset.update(source_uri='https://www.osmdata.org/download/land-polygons-split-4326.zip',provider='OpenStreetMap contributors; osmdata.openstreetmap.de, via unofficial North America mirror',license_name='Open Data Commons Open Database License 1.0',license_uri='https://opendatacommons.org/licenses/odbl/1-0/',attribution='© OpenStreetMap contributors, https://www.openstreetmap.org/copyright',provenance={'origin':'unofficial North America mirror of osmdata.openstreetmap.de','verification':'full R2 object readback SHA-256 and size match the locally retrieved archive'})
 def test_valid_policy(self):
  d=polygon_policy.adapt(self.s,{'a'});self.assertEqual(d['decisions'][0]['features'][0]['source_format'],'osm-split-land-shapefile');self.assertEqual(d['source_pins'][0]['validated_representation'],'provider_derived_unofficial_mirror')
 def test_invalid_origin_or_feature(self):
  for k,v in (('source_uri','https://evil.example/land-polygons-split-4326.zip'),('provider','OpenStreetMap'),('license_uri','https://evil.example/')):
   old=self.asset[k];self.asset[k]=v
   with self.subTest(k=k),self.assertRaises(ValueError):polygon_policy.adapt(self.s,{'a'})
   self.asset[k]=old
  for bad in ('-1','00','١'):
   self.feature['source_feature_id']=bad
   with self.subTest(bad=bad),self.assertRaises(ValueError):polygon_policy.adapt(self.s,{'a'})
 def test_mirror_cannot_claim_geojson_route(self):
  self.a['method']='component_intersection_v1';self.a['evidence']['selector'].pop('extractor_version');self.feature['evidence']={'selector_property':'id'}
  with self.assertRaisesRegex(ValueError,'mirror source requires'):polygon_policy.adapt(self.s,{'a'})
 def test_no_witness_or_wrong_extractor(self):
  sel=self.a['evidence']['selector'];sel['include_witnesses']=[{'lon':'0','lat':'0'}]
  with self.assertRaises(ValueError):polygon_policy.adapt(self.s,{'a'})
  sel['include_witnesses']=[];sel['extractor_version']='other'
  with self.assertRaises(ValueError):polygon_policy.adapt(self.s,{'a'})
class ArchiveLoader(unittest.TestCase):
 def test_real_dispatch_synthetic_archive(self):
  f=ArchiveFixture();f.setUp()
  try:
   feature={**f.feature,'source_format':'osm-split-land-shapefile','extractor_version':'osm-split-land-archive-v1'};pin={'path':str(f.zip),'shapefile_path':str(f.shp),'sha256':f.sha,'size_bytes':f.zip.stat().st_size};g,trace=polygon_loader.extract(feature,pin);self.assertEqual(g['type'],'Polygon');self.assertEqual(trace['source_feature_id'],'0')
   with self.assertRaises(ValueError):polygon_loader.extract(feature,{**pin,'sha256':'0'*64})
   with self.assertRaises(ValueError):polygon_loader.extract(feature,{k:v for k,v in pin.items() if k!='shapefile_path'})
  finally:f.tearDown()
if __name__=='__main__':unittest.main()

class ArchiveResolution(unittest.TestCase):
 def test_whole_source_intersection_dispatch(self):
  import struct,tempfile,zipfile
  from osgeo import ogr,osr
  import polygon_resolution,mixed_claims
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);u=lambda n,v:(p/n).write_bytes(struct.pack('<'+'I'*len(v),*v));u('pr',[0,3,4]);u('pv',[1024,1,1027,17,2048,1,2048,1]);u('cr',[0,2,2]);u('cv',[1024,1026,10,1026,1027,11]);sha=lambda f:hashlib.sha256(Path(f).read_bytes()).hexdigest();inputs={k:{'path':str(p/n),'sha256':sha(p/n)} for k,n in (('physical_rows','pr'),('physical_runs','pv'),('component_rows','cr'),('component_runs','cv'))}
   sub=p/'land-polygons-split-4326';sub.mkdir();shp=sub/'land_polygons.shp';ds=ogr.GetDriverByName('ESRI Shapefile').CreateDataSource(str(shp));sr=osr.SpatialReference();sr.ImportFromEPSG(4326);layer=ds.CreateLayer('land_polygons',sr,ogr.wkbPolygon);f=ogr.Feature(layer.GetLayerDefn());f.SetGeometry(ogr.CreateGeometryFromWkt('POLYGON ((0.01 89.72, 0.35 89.72, 0.35 89.99, 0.01 89.99, 0.01 89.72))'));layer.CreateFeature(f);ds=None;archive=p/'source.zip'
   with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
    for f in sub.iterdir():z.write(f,'land-polygons-split-4326/'+f.name)
   ds=ogr.Open(str(shp));row=ds.GetLayer(0).GetFeature(0);g=json.loads(row.GetGeometryRef().ExportToJson());ds=None;geometry_sha=hashlib.sha256(json.dumps(g,sort_keys=True,separators=(',',':')).encode()).hexdigest()
   fixture=ArchivePolicy();fixture.setUp();s=fixture.s;source=s['sources'][0];asset=s['source_lineage_assets'][0]
   for v in (source,asset):v['sha256']=sha(archive);v['size_bytes']=archive.stat().st_size
   s['features'][0]['geometry_sha256']=geometry_sha;s['entity_revision']={'id':'e'};s['category_bindings']=[{'entity_id':3,'code':19,'physical_class':'land'}];policy=polygon_policy.adapt(s,{'a'});files=[{**source,'path':str(archive),'shapefile_path':str(shp)}];grid={'width':2048,'height':2,'west':-180,'north':90,'step':360/2048};res=polygon_resolution.resolve(policy,s,files,grid,inputs);claim=res['claims'][0];self.assertEqual(claim['component_ids'],[10]);self.assertEqual(claim['entity_code'],19)
   compiled={'revision':'r','entity_revision':'e','affiliation_ids':['a'],'affiliation_entry_links':{'a':['entry']}};self.assertEqual(mixed_claims.combine(compiled,s,[res],{99})[10][0]['code'],19)
