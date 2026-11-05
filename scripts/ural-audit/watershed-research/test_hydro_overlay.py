import math,unittest
try:
 import shapely
 from shapely.geometry import Polygon
 HAS_SHAPELY=hasattr(shapely,'normalize')
except ImportError:HAS_SHAPELY=False
import hydro_overlay as h

def distance(a,b):return math.hypot(a[0]-b[0],a[1]-b[1])

@unittest.skipUnless(HAS_SHAPELY,'requires Shapely 2')
class OverlayTest(unittest.TestCase):
 def setUp(self):
  self.a=Polygon([(0,0),(1,0),(1,2),(0,2)])
  self.b=Polygon([(1,0),(2,0),(2,2),(1,2),(1,1)])
  self.box=(-.5,-.5,3,4)
 def test_mismatched_vertex_segmentation_nodes_shared_edge(self):
  graph,stats=h.overlay_graph([('e',1,10,self.a),('s',2,20,self.b)],{10},{20},self.box,distance)
  self.assertEqual(stats['components'],1);self.assertEqual(stats['shared_noded_segments'],2)
  path,length=h.route(graph,(1.,0.),(1.,2.),distance);self.assertEqual(path,[(1.,0.),(1.,1.),(1.,2.)]);self.assertEqual(length,2)
 def test_same_side_regional_duplicate_is_counted_not_double_graph(self):
  reversed_polygon=Polygon(list(self.a.exterior.coords)[::-1])
  graph,stats=h.overlay_graph([('e',1,10,self.a),('s',3,10,reversed_polygon),('s',2,20,self.b)],{10},{20},self.box,distance)
  self.assertEqual(stats['duplicate_same_side_polygons'],1);self.assertEqual(stats['components'],1)
 def test_cross_label_overlapping_polygons_fail(self):
  with self.assertRaisesRegex(h.AuditError,'area overlap'):h.overlay_graph([('e',1,10,self.a),('s',2,20,self.a)],{10},{20},self.box,distance)
 def test_unknown_polygon_touching_interface_fails_closed(self):
  unknown=Polygon([(1,1),(1.2,1),(1.2,1.2),(1,1.2)])
  with self.assertRaisesRegex(h.AuditError,'unknown-side polygon touches'):h.overlay_graph([('e',1,10,self.a),('s',2,20,self.b),('x',3,30,unknown)],{10},{20},self.box,distance)
 def test_separated_components_diagnosed_no_gap_bridge(self):
  a2=Polygon([(0,3),(1,3),(1,4),(0,4)]);b2=Polygon([(1,3),(2,3),(2,4),(1,4)])
  with self.assertRaises(h.AuditError) as c:h.overlay_graph([('e',1,10,self.a),('s',2,20,self.b),('e',3,10,a2),('s',4,20,b2)],{10},{20},(-.5,-.5,3,5),distance)
  self.assertEqual(c.exception.diagnostics['components'],2);self.assertEqual(c.exception.diagnostics['nearest_component_endpoint_gap']['wgs84_m'],1)
@unittest.skipUnless(HAS_SHAPELY,'requires Shapely 2, pyshp and pyproj')
class RealArchiveCLI(unittest.TestCase):
 def test_shapefile_zip_to_research_route(self):
  import hashlib,json,os,subprocess,sys,tempfile,zipfile
  from pathlib import Path
  import shapefile
  from pyproj import CRS
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp);base=p/'basins';w=shapefile.Writer(str(base),shapeType=shapefile.POLYGON);w.field('HYBAS_ID','N',size=12,decimal=0);w.field('MAIN_BAS','N',size=12,decimal=0)
   w.poly([[(0,0),(0,2),(1,2),(1,0),(0,0)]]);w.record(1,10)
   w.poly([[(1,0),(1,2),(2,2),(2,0),(1,0)]]);w.record(2,20);w.close();base.with_suffix('.prj').write_text(CRS.from_epsg(4326).to_wkt())
   archive=p/'source.zip'
   with zipfile.ZipFile(archive,'w') as z:
    for ext in ('.shp','.shx','.dbf','.prj'):z.write(base.with_suffix(ext),'basins'+ext)
   digest=hashlib.sha256(archive.read_bytes()).hexdigest();out=p/'out.json';tool=Path(h.__file__)
   cmd=[sys.executable,str(tool),'--archive',str(archive),digest,'--bbox','-0.5','-0.5','2.5','2.5','--side-a','10','--side-b','20','--start','1','0','--end','1','2','--max-snap-m','1','--output',str(out)]
   r=subprocess.run(cmd,capture_output=True,text=True,env=os.environ.copy());self.assertEqual(r.returncode,0,r.stderr);report=json.loads(out.read_bytes());self.assertEqual(report['status'],'research-only');self.assertFalse(report['publishable']);self.assertEqual(report['diagnostics']['components'],1);self.assertEqual(len(report['geometry']['coordinates']),2)
if __name__=='__main__':unittest.main()
