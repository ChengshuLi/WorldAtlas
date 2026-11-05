# Synthetic fixtures only; no project geographic records.
import copy,unittest
import named_identity as n

def fixture():
 g={'type':'Polygon','coordinates':[[[0,0],[4,0],[4,4],[0,4],[0,0]]]};f={'type':'Feature','properties':{'id':5,'name':'Example','class':'Island'},'geometry':g};src={'type':'FeatureCollection','features':[f]};point={'type':'Point','coordinates':[2,2]};spec={'method':'raw_named_polygon_contains_point_v1','identity_feature_id':'5','identity_id_property':'id','identity_name_property':'name','identity_class_property':'class','identity_class_value':'Island','identity_geometry_sha256':n.geom_hash(g)};return src,point,spec
class IdentityTests(unittest.TestCase):
 def setUp(self):self.src,self.pt,self.spec=fixture()
 def test_strict_containment(self):self.assertTrue(n.check(self.src,self.pt,'Example',self.spec)['strict_contains'])
 def test_crs84_accepted(self):
  self.src['crs']={'type':'name','properties':{'name':'urn:ogc:def:crs:OGC:1.3:CRS84'}};self.assertEqual(n.check(self.src,self.pt,'Example',self.spec)['identity_source_crs'],'OGC:CRS84')
 def test_unsupported_crs_rejected(self):
  self.src['crs']={'type':'name','properties':{'name':'EPSG:3857'}}
  with self.assertRaisesRegex(ValueError,'source CRS'):n.check(self.src,self.pt,'Example',self.spec)
 def test_nested_feature_crs_rejected(self):
  self.src['features'][0]['crs']={'type':'name','properties':{'name':'EPSG:3857'}}
  with self.assertRaisesRegex(ValueError,'nested feature CRS'):n.check(self.src,self.pt,'Example',self.spec)
 def test_nested_geometry_crs_rejected(self):
  self.src['features'][0]['geometry']['crs']={'type':'name','properties':{'name':'EPSG:3857'}};self.spec['identity_geometry_sha256']=n.geom_hash(self.src['features'][0]['geometry'])
  with self.assertRaisesRegex(ValueError,'nested geometry CRS'):n.check(self.src,self.pt,'Example',self.spec)
 def test_boundary_rejected(self):
  self.pt['coordinates']=[0,2]
  with self.assertRaisesRegex(ValueError,'strictly inside'):n.check(self.src,self.pt,'Example',self.spec)
 def test_outside_rejected(self):
  self.pt['coordinates']=[9,2]
  with self.assertRaisesRegex(ValueError,'strictly inside'):n.check(self.src,self.pt,'Example',self.spec)
 def test_duplicate_id_rejected(self):
  self.src['features'].append(copy.deepcopy(self.src['features'][0]))
  with self.assertRaisesRegex(ValueError,'unique'):n.check(self.src,self.pt,'Example',self.spec)
 def test_wrong_name_rejected(self):
  with self.assertRaisesRegex(ValueError,'name or class mismatch'):n.check(self.src,self.pt,'Wrong',self.spec)
 def test_wrong_class_rejected(self):
  self.src['features'][0]['properties']['class']='Island group'
  with self.assertRaisesRegex(ValueError,'name or class mismatch'):n.check(self.src,self.pt,'Example',self.spec)
 def test_hash_mismatch_rejected(self):
  self.spec['identity_geometry_sha256']='0'*64
  with self.assertRaisesRegex(ValueError,'hash mismatch'):n.check(self.src,self.pt,'Example',self.spec)
 def test_invalid_self_intersection_rejected(self):
  g=self.src['features'][0]['geometry'];g['coordinates']=[[[0,0],[4,4],[0,4],[4,0],[0,0]]];self.spec['identity_geometry_sha256']=n.geom_hash(g)
  with self.assertRaisesRegex(ValueError,'invalid identity polygon'):n.check(self.src,self.pt,'Example',self.spec)
 def test_antimeridian_rejected(self):
  g=self.src['features'][0]['geometry'];g['coordinates']=[[[179,0],[-179,0],[-179,4],[179,4],[179,0]]];self.spec['identity_geometry_sha256']=n.geom_hash(g)
  with self.assertRaisesRegex(ValueError,'antimeridian'):n.check(self.src,self.pt,'Example',self.spec)
 def test_unsupported_selector_rejected(self):
  self.spec['extra']='x'
  with self.assertRaisesRegex(ValueError,'selector'):n.check(self.src,self.pt,'Example',self.spec)
if __name__=='__main__':unittest.main()
