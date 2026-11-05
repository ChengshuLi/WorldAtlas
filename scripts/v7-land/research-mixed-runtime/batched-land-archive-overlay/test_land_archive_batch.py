import hashlib,json,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
from osgeo import ogr,osr
import polygon_loader,polygon_resolution
class BatchLoader(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();root=Path(self.tmp.name);sub=root/'land-polygons-split-4326';sub.mkdir();self.shp=sub/'land_polygons.shp';ds=ogr.GetDriverByName('ESRI Shapefile').CreateDataSource(str(self.shp));sr=osr.SpatialReference();sr.ImportFromEPSG(4326);layer=ds.CreateLayer('land_polygons',sr,ogr.wkbPolygon)
  for dx in (0,2):
   f=ogr.Feature(layer.GetLayerDefn());f.SetGeometry(ogr.CreateGeometryFromWkt(f'POLYGON (({dx} 0,{dx} 1,{dx+1} 1,{dx+1} 0,{dx} 0))'));layer.CreateFeature(f)
  ds=None;self.zip=root/'source.zip'
  with zipfile.ZipFile(self.zip,'w',zipfile.ZIP_DEFLATED) as z:
   for p in sub.iterdir():z.write(p,'land-polygons-split-4326/'+p.name)
  self.sha=hashlib.sha256(self.zip.read_bytes()).hexdigest();ds=ogr.Open(str(self.shp));layer=ds.GetLayer(0);self.features=[]
  for i in (0,1):
   row=layer.GetFeature(i);g=json.loads(row.GetGeometryRef().ExportToJson());h=hashlib.sha256(json.dumps(g,sort_keys=True,separators=(',',':')).encode()).hexdigest();self.features.append({'source_feature_id':str(i),'geometry_sha256':h,'source_format':'osm-split-land-shapefile','extractor_version':'osm-split-land-archive-v1'})
  ds=None;self.pin={'path':str(self.zip),'shapefile_path':str(self.shp),'sha256':self.sha,'size_bytes':self.zip.stat().st_size}
 def tearDown(self):self.tmp.cleanup()
 def test_two_features_same_pass_and_reverse_order(self):
  out=polygon_loader.extract_land_many(self.features[::-1],self.pin,lambda:None);self.assertEqual([t['source_feature_id'] for g,t in out],['1','0']);self.assertEqual([t['geometry_sha256'] for g,t in out],[f['geometry_sha256'] for f in self.features[::-1]])
 def test_bad_feature_aborts_entire_batch(self):
  fs=[dict(f) for f in self.features];fs[1]['geometry_sha256']='0'*64
  with self.assertRaisesRegex(ValueError,'geometry hash mismatch'):polygon_loader.extract_land_many(fs,self.pin,lambda:None)
 def test_duplicate_feature_and_bad_source_rejected(self):
  with self.assertRaisesRegex(ValueError,'duplicate'):polygon_loader.extract_land_many([self.features[0]]*2,self.pin,lambda:None)
  with self.assertRaises(ValueError):polygon_loader.extract_land_many(self.features,{**self.pin,'sha256':'0'*64},lambda:None)
class BatchResolution(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.p=Path(self.tmp.name);self.file=self.p/'pin';self.file.write_text('pin');h=hashlib.sha256(b'pin').hexdigest();self.inputs={k:{'path':str(self.file),'sha256':h} for k in ('physical_rows','physical_runs','component_rows','component_runs')};self.source={'source_id':'s','version':'v','path':str(self.file),'sha256':h,'size_bytes':3};self.grid={'width':10};self.f=[{'feature_id':f'f{i}','source_id':'s','source_version':'v','source_feature_id':str(i),'source_format':'osm-split-land-shapefile','extractor_version':'osm-split-land-archive-v1'} for i in (1,2)];self.d={'affiliation_id':'a','entity_id':4,'method':'osm_land_archive_component_intersection_v1','features':self.f,'include_witnesses':[],'exclude_witnesses':[],'decision_limitations':[]};self.policy={'schema':'stage3-polygon-decisions-v1','status':'requires-source-resolution','revision':'r','source_pins':[self.source],'decisions':[self.d]};self.snapshot={'decision_revision':{'id':'r'},'entity_revision':{'id':'e'},'category_bindings':[{'physical_class':'land','entity_id':4,'code':20}]}
 def tearDown(self):self.tmp.cleanup()
 def test_batches_one_source_in_order(self):
  extracted=[({'type':'Polygon','coordinates':[]},{'n':1}),({'type':'Polygon','coordinates':[]},{'n':2})]
  with patch.object(polygon_loader,'extract_land_many',return_value=extracted) as batch,patch.object(polygon_loader,'extract',side_effect=AssertionError('unexpected individual extraction')),patch.object(polygon_resolution.polygon_intersection,'intersect',return_value=([10,11],{'per_feature_root_inside_cells':[{'10':1},{'11':1}]})):
   r=polygon_resolution.resolve(self.policy,self.snapshot,[self.source],self.grid,self.inputs,lambda:None)
  self.assertEqual(batch.call_count,1);self.assertEqual([x['feature_id'] for x in r['claims'][0]['source_features']],['f1','f2']);self.assertEqual([x['n'] for x in r['claims'][0]['source_features']],[1,2])
 def test_duplicates_fall_back_without_changing_prior_behavior(self):
  self.f[1]['source_feature_id']='1'
  with patch.object(polygon_loader,'extract_land_many',side_effect=AssertionError('unexpected batch')),patch.object(polygon_loader,'extract',return_value=({'type':'Polygon','coordinates':[]},{})) as individual,patch.object(polygon_resolution.polygon_intersection,'intersect',return_value=([10],{'per_feature_root_inside_cells':[{'10':1},{'10':1}]})):
   polygon_resolution.resolve(self.policy,self.snapshot,[self.source],self.grid,self.inputs,lambda:None)
  self.assertEqual(individual.call_count,2)
 def test_batch_wrong_count_fails_closed(self):
  with patch.object(polygon_loader,'extract_land_many',return_value=[]),self.assertRaisesRegex(ValueError,'count mismatch'):polygon_resolution.resolve(self.policy,self.snapshot,[self.source],self.grid,self.inputs,lambda:None)
if __name__=='__main__':unittest.main()
