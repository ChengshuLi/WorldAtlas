import hashlib,json,struct,tempfile,unittest,zipfile,importlib.util
from pathlib import Path
from osgeo import ogr,osr
P=Path(__file__).parent;spec=importlib.util.spec_from_file_location('generic_audit',P/'generic_audit.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
class Tests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.r=Path(self.t.name);folder=self.r/'land-polygons-split-4326';folder.mkdir();shape=folder/'land_polygons.shp';driver=ogr.GetDriverByName('ESRI Shapefile');ds=driver.CreateDataSource(str(shape));srs=osr.SpatialReference();srs.ImportFromEPSG(4326);ly=ds.CreateLayer('land_polygons',srs,ogr.wkbPolygon)
  for x,y in [(1,3),(3,2)]:
   ring=ogr.Geometry(ogr.wkbLinearRing)
   for a,b in [(x,y),(x+1,y),(x+1,y+1),(x,y+1),(x,y)]:ring.AddPoint_2D(a,b)
   poly=ogr.Geometry(ogr.wkbPolygon);poly.AddGeometry(ring);f=ogr.Feature(ly.GetLayerDefn());f.SetGeometry(poly);ly.CreateFeature(f)
  ly=None;ds=None;archive=self.r/'source.zip'
  with zipfile.ZipFile(archive,'w') as z:
   for suffix in ('shp','shx','dbf','prj'):z.write(folder/('land_polygons.'+suffix),'land-polygons-split-4326/land_polygons.'+suffix)
  profile=self.r/'profile.json';profile.write_text(json.dumps({'items':[{'id':'1','name':'A','point':[1.5,3.5],'root_evidence_only':10,'cells':1},{'id':'2','name':'B','point':[3.5,2.5],'root_evidence_only':11,'cells':1}]}));rows=self.r/'rows';runs=self.r/'runs';rows.write_bytes(struct.pack('<7I',0,0,0,1,2,2,2));runs.write_bytes(struct.pack('<6I',1,2,10,3,4,11));loader=P/'land_archive_source.py'
  def pin(p):p=p.resolve();return {'path':str(p),'sha256':mod.sha(p)}
  self.q={'schema':'point-root-source-containment-request-v1','point_profile':pin(profile),'archive':pin(archive),'materialized_shapefile':str(shape),'component_rows':pin(rows),'component_runs':pin(runs),'archive_loader':pin(loader),'grid':{'width':6,'height':6,'west':0,'north':6,'step':1},'scan_rows':[1,5],'output':str(self.r/'out.json')};profile_data=json.loads(profile.read_text());profile_data.update(grid=self.q['grid'],component_rows_sha256=self.q['component_rows']['sha256'],component_runs_sha256=self.q['component_runs']['sha256']);profile.write_text(json.dumps(profile_data));self.q['point_profile']['sha256']=mod.sha(profile);self.req=self.r/'request.json'
 def tearDown(self):self.t.cleanup()
 def runq(self):self.req.write_text(json.dumps(self.q));return mod.run(self.req)
 def test_full_two_islands(self):
  self.runq();d=json.loads((self.r/'out.json').read_text());self.assertEqual([x['inside_source_polygon_centers'] for x in d['results']],[1,1]);self.assertEqual([x['outside_source_polygon_centers'] for x in d['results']],[0,0])
 def test_duplicate_root_rejected(self):
  p=Path(self.q['point_profile']['path']);v=json.loads(p.read_text());v['items'][1]['root_evidence_only']=10;p.write_text(json.dumps(v));self.q['point_profile']['sha256']=mod.sha(p)
  with self.assertRaisesRegex(ValueError,'duplicate'):self.runq()
 def test_bad_pin_rejected(self):
  self.q['point_profile']['sha256']='bad'
  with self.assertRaisesRegex(ValueError,'pin'):self.runq()
 def test_oversized_request_rejected(self):
  self.req.write_bytes(b' '*((1<<20)+1))
  with self.assertRaisesRegex(ValueError,'size'):mod.run(self.req)
 def test_oversized_profile_rejected(self):
  p=Path(self.q['point_profile']['path']);p.write_bytes(b' '*((8<<20)+1));self.q['point_profile']['sha256']=mod.sha(p)
  with self.assertRaisesRegex(ValueError,'size'):self.runq()
 def test_oversized_rows_rejected(self):
  p=Path(self.q['component_rows']['path']);p.write_bytes(p.read_bytes()+b'x');self.q['component_rows']['sha256']=mod.sha(p);profile=Path(self.q['point_profile']['path']);v=json.loads(profile.read_text());v['component_rows_sha256']=self.q['component_rows']['sha256'];profile.write_text(json.dumps(v));self.q['point_profile']['sha256']=mod.sha(profile)
  with self.assertRaisesRegex(ValueError,'size'):self.runq()
 def test_nonfinite_origin_rejected(self):
  self.q['grid']['west']=float('nan')
  with self.assertRaisesRegex(ValueError,'grid'):self.runq()
 def test_grid_binding_rejected(self):
  self.q['grid']['west']=3
  with self.assertRaisesRegex(ValueError,'profile grid'):self.runq()
 def test_component_binding_rejected(self):
  self.q['component_runs']['sha256']='0'*64
  with self.assertRaisesRegex(ValueError,'profile grid'):self.runq()
 def test_scan_edge_rejected(self):
  self.q['scan_rows']=[2,5]
  with self.assertRaisesRegex(ValueError,'scan edge'):self.runq()
if __name__=='__main__':unittest.main()
