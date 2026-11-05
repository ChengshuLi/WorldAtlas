import importlib.util,json,tempfile,unittest
from pathlib import Path
p=Path(__file__).with_name('ural-reconstruct-hybrid.py');sp=importlib.util.spec_from_file_location('hybrid',p);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
class Hybrid(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.osm=Path(self.tmp.name)/'source.osm';self.raw='<osm><node id="1" lon="0" lat="0"/><node id="2" lon="1" lat="0"/><node id="3" lon="2" lat="0"/><way id="5"><nd ref="3"/><nd ref="2"/><nd ref="1"/></way><relation id="214415" version="122"><member type="way" ref="5" role="main_stream"/></relation></osm>';self.osm.write_text(self.raw);g={'type':'LineString','coordinates':[[-1.,1.],[0.,0.],[1.,0.],[2.,0.]]};source={'source_id':'osm-ural-river-relation-214415-full','version':'snapshot-2026-11-05-v122-89cef99ad92b','r2_bucket':'worldatlas','r2_key':'source.osm','sha256':m.sha(self.osm),'size_bytes':self.osm.stat().st_size};self.snapshot={'decision_revision':{'id':'draft'},'sources':[source],'mainland_boundaries':[{'boundary_id':'ural_kara_coast_to_caspian','execution_status':'selected_for_research','decision_revision':'draft','coordinate_reference':'OGC:CRS84','geometry_hash_method':'binary64-sorted-compact-geojson-v1','provenance':{'source_refs':[{'source_id':source['source_id'],'version':source['version']}]},'geometry':g,'geometry_sha256':m.geom_sha(g)}]}
 def repin(self):
  src=self.snapshot['sources'][0];src['sha256']=m.sha(self.osm);src['size_bytes']=self.osm.stat().st_size
 def test_reverse_way_and_preserve_north(self):
  g,r=m.reconstruct(self.snapshot,self.osm,1);self.assertEqual(g,self.snapshot['mainland_boundaries'][0]['geometry']);self.assertTrue(r['matches_selected_geometry']);self.assertEqual(r['osm_main_stream_edges'],2);self.assertEqual(r['retained_northern_vertices'],1)
 def test_source_change_detected(self):
  self.osm.write_text(self.raw.replace('lon="1"','lon="1.1"'));self.repin();_,r=m.reconstruct(self.snapshot,self.osm,1);self.assertFalse(r['matches_selected_geometry'])
 def test_missing_node_fails(self):
  self.osm.write_text(self.raw.replace('ref="2"','ref="4"'));self.repin()
  with self.assertRaisesRegex(ValueError,'missing main-stream node'):m.reconstruct(self.snapshot,self.osm,1)
 def test_unpinned_source_fails(self):
  self.osm.write_text(self.raw+' ')
  with self.assertRaisesRegex(ValueError,'selected source link'):m.reconstruct(self.snapshot,self.osm,1)
 def test_missing_source_link_fails(self):
  self.snapshot['mainland_boundaries'][0]['provenance']['source_refs']=[]
  with self.assertRaisesRegex(ValueError,'selected source link'):m.reconstruct(self.snapshot,self.osm,1)
 def test_wrong_orientation_fails(self):
  g=self.snapshot['mainland_boundaries'][0]['geometry'];g['coordinates'][1]=[1.,0.];self.snapshot['mainland_boundaries'][0]['geometry_sha256']=m.geom_sha(g)
  with self.assertRaisesRegex(ValueError,'unique OSM endpoint'):m.reconstruct(self.snapshot,self.osm,1)
 def test_duplicate_edge_fails(self):
  self.osm.write_text(self.raw.replace('<nd ref="1"/>','<nd ref="1"/><nd ref="2"/>'));self.repin()
  with self.assertRaisesRegex(ValueError,'duplicate or degenerate'):m.reconstruct(self.snapshot,self.osm,1)
if __name__=='__main__':unittest.main()
