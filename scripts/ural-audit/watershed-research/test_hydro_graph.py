import hashlib,math,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
import hydro_graph as h

def poly(archive,rid,bas,coords):return (archive,rid,bas,[coords])
def distance(a,b):return math.hypot(a[0]-b[0],a[1]-b[1])

class SharedEdges(unittest.TestCase):
 def setUp(self):
  self.bbox=(-1,-1,4,4)
  self.a=poly('x',1,10,[(0,0),(1,0),(1,1),(0,1),(0,0)])
  self.b=poly('x',2,20,[(1,0),(2,0),(2,1),(1,1),(1,0)])
 def test_shared_edge_snap_and_route(self):
  graph,info=h.build_graph([self.a,self.b],{10},{20},self.bbox)
  self.assertEqual(info['shared_AB_segments'],1);self.assertEqual(info['components'],1)
  a,da=h.snap(graph,(1,0),0,distance);b,db=h.snap(graph,(1,1),0,distance)
  path,length=h.route(graph,a,b,distance);self.assertEqual(path,[(1.,0.),(1.,1.)]);self.assertEqual(length,1);self.assertEqual((da,db),(0,0))
 def test_missing_or_overlapping_sides_fail(self):
  with self.assertRaisesRegex(h.AuditError,'missing'):h.build_graph([self.a,self.b],{10,11},{20},self.bbox)
  with self.assertRaisesRegex(h.AuditError,'disjoint'):h.build_graph([self.a,self.b],{10},{10},self.bbox)
 def test_different_segmentation_does_not_forge_shared_edge(self):
  b=poly('x',2,20,[(1,0),(2,0),(2,1),(1,1),(1,.5),(1,0)])
  with self.assertRaisesRegex(h.AuditError,'no exact cross-side'):h.build_graph([self.a,b],{10},{20},self.bbox)
 def test_duplicate_nonmanifold_and_closed_loop_fail(self):
  duplicate=poly('z',3,20,[(1,0),(1,1),(1.5,1.5),(1,0)])
  with self.assertRaisesRegex(h.AuditError,'nonmanifold'):h.build_graph([self.a,self.b,duplicate],{10},{20},self.bbox)
  other=poly('x',2,20,self.a[3][0])
  with self.assertRaisesRegex(h.AuditError,'cross-label basin geometry'):h.build_graph([self.a,other],{10},{20},self.bbox)
 def test_disconnected_interfaces_fail_with_diagnostics(self):
  a2=poly('x',3,10,[(0,2),(1,2),(1,3),(0,3),(0,2)])
  b2=poly('x',4,20,[(1,2),(2,2),(2,3),(1,3),(1,2)])
  with self.assertRaises(h.AuditError) as c:h.build_graph([self.a,self.b,a2,b2],{10},{20},self.bbox,distance)
  self.assertEqual(c.exception.diagnostics['components'],2)
  self.assertEqual(c.exception.diagnostics['nearest_component_endpoint_gap']['wgs84_m'],1)
 def test_snap_limit_and_equidistant_fail(self):
  graph,_=h.build_graph([self.a,self.b],{10},{20},self.bbox)
  with self.assertRaisesRegex(h.AuditError,'maximum'):h.snap(graph,(3,3),.1,distance)
  with self.assertRaisesRegex(h.AuditError,'ambiguous'):h.snap(graph,(1,.5),1,distance)
 def test_equal_paths_rejected(self):
  a=(0.,0.);b=(1.,1.);c=(1.,-1.);d=(2.,0.)
  graph={a:{b,c},b:{a,d},c:{a,d},d:{b,c}}
  with self.assertRaisesRegex(h.AuditError,'equal-length'):h.route(graph,a,d,distance)
 def test_bbox_cannot_create_clipped_edges(self):
  with self.assertRaisesRegex(h.AuditError,'no exact cross-side'):h.build_graph([self.a,self.b],{10},{20},(-1,.1,3,.9))
 def test_archive_hash_enforced(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'a.zip';p.write_bytes(b'archive');digest=hashlib.sha256(b'archive').hexdigest();h.verify_pin(p,digest)
   p.write_bytes(b'changed')
   with self.assertRaisesRegex(h.AuditError,'checksum'):h.verify_pin(p,digest)
 def test_bbox_rejects_nonlocal_wrap_and_nonfinite(self):
  h.validate_bbox((-5,-5,25,25))
  for b in [(-180,-1,180,1),(170,-1,-170,1),(0,0,31,1),(0,0,1,float('nan'))]:
   with self.subTest(b=b),self.assertRaises(h.AuditError):h.validate_bbox(b)
 def test_ring_rejects_nonfinite_and_antimeridian_jump(self):
  for ring in [[(0,0),(1,0),(1,float('nan')),(0,0)],[(-179,0),(179,0),(179,1),(-179,0)]]:
   with self.subTest(ring=ring),self.assertRaises(h.AuditError):h.validate_rings([ring])
 def test_feature_vertex_and_graph_limits(self):
  with patch.object(h,'MAX_FEATURES',1),self.assertRaisesRegex(h.AuditError,'feature limit'):h.build_graph([self.a,self.b],{10},{20},self.bbox)
  with patch.object(h,'MAX_VERTICES',4),self.assertRaisesRegex(h.AuditError,'vertex limit'):h.build_graph([self.a,self.b],{10},{20},self.bbox)
  with patch.object(h,'MAX_GRAPH_SEGMENTS',0),self.assertRaisesRegex(h.AuditError,'segment limit'):h.build_graph([self.a,self.b],{10},{20},self.bbox)
 def test_zip_component_and_total_limits(self):
  with tempfile.TemporaryDirectory() as d:
   zpath=Path(d)/'a.zip'
   with zipfile.ZipFile(zpath,'w') as z:
    for ext in h.COMPONENT_LIMITS:z.writestr('x'+ext,b'abc')
   with zipfile.ZipFile(zpath) as z,patch.object(h,'MAX_ARCHIVE_UNCOMPRESSED',11),self.assertRaisesRegex(h.AuditError,'uncompressed'):h.extract_components(z,Path(d)/'out')
   with zipfile.ZipFile(zpath) as z,patch.dict(h.COMPONENT_LIMITS,{'.shp':2}),self.assertRaisesRegex(h.AuditError,'component exceeds'):h.extract_components(z,Path(d)/'out')

if __name__=='__main__':unittest.main()
