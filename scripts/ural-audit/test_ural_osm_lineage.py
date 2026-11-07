import importlib.util,json,hashlib,tempfile,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('lineage',Path(__file__).with_name('ural-osm-construction-lineage.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Lineage(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);d=Path(self.t.name);self.osm=d/'full.osm';self.history=d/'history.osm';self.osm.write_text('''<osm><node id="1" lat="0" lon="0" timestamp="2026-01-01T00:00:00Z"/><node id="2" lat="0" lon="1" timestamp="2026-01-01T00:00:00Z"/><node id="3" lat="0" lon="2" timestamp="2026-01-01T00:00:00Z"/><way id="7" timestamp="2026-01-01T00:00:00Z"><nd ref="1"/><nd ref="2"/></way><way id="8" timestamp="2026-01-01T00:00:00Z"><nd ref="2"/><nd ref="3"/></way><relation id="214415" version="9" timestamp="2026-01-01T00:00:00Z"><member type="way" ref="7" role="main_stream"/><member type="way" ref="8" role="main_stream"/></relation></osm>''');self.history.write_text('<osm><relation id="214415" version="9" timestamp="2026-01-01T00:00:00Z"/></osm>');g={'type':'LineString','coordinates':[[0.,0.],[1.,0.],[2.,0.]]};h=hashlib.sha256(json.dumps(g,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest();self.snapshot={'mainland_boundaries':[{'boundary_id':'ural','geometry':g,'geometry_sha256':h}]}
 def runv(self):return m.verify(self.snapshot,self.osm,self.history,'ural',0,'2026-11-02T00:00:00Z')
 def test_chain_and_order(self):
  r=self.runv();self.assertTrue(r['edge_multisets_equal'] and r['node_chain_connected'] and r['ordered_coordinates_match'] and r['history_relation_version_matches'])
 def test_after_cutoff_is_reported(self):
  self.osm.write_text(self.osm.read_text().replace('2026-01-01T00:00:00Z','2026-11-03T00:00:00Z',1));self.assertEqual(self.runv()['main_stream_nodes_after_cutoff_or_missing_timestamp'],1)
 def test_missing_node_fails(self):
  self.osm.write_text(self.osm.read_text().replace('<nd ref="3"/>','<nd ref="4"/>'))
  with self.assertRaisesRegex(ValueError,'missing main-stream nodes'):self.runv()
 def test_geometry_tampering_fails(self):
  self.snapshot['mainland_boundaries'][0]['geometry']['coordinates'][1][0]=1.5
  with self.assertRaisesRegex(ValueError,'geometry hash mismatch'):self.runv()
if __name__=='__main__':unittest.main()
