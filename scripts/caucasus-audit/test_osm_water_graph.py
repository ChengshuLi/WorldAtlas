import tempfile,unittest
from pathlib import Path
from osm_water_graph import WaterGraph

OSM='''<osm>
<node id="1" lon="0.00000" lat="0"/><node id="2" lon="0.00010" lat="0"/><node id="3" lon="0.00020" lat="0"/>
<way id="10"><nd ref="1"/><nd ref="2"/><tag k="waterway" v="stream"/></way>
<way id="20"><nd ref="2"/><nd ref="3"/><tag k="waterway" v="river"/><tag k="name" v="Sample"/></way>
<way id="30"><nd ref="3"/><nd ref="missing"/><tag k="waterway" v="stream"/></way>
</osm>'''
class WaterGraphTests(unittest.TestCase):
    def test_network_and_first_contact(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'source.osm';p.write_text(OSM);g=WaterGraph(p)
            self.assertEqual(g.incomplete,1)
            r=g.first_contact([(0.00001,0)],5,5)
            self.assertEqual(r['status'],'matched');self.assertEqual(r['names'],('Sample',))
            self.assertEqual(g.first_contact([(1,1)],5,5)['status'],'no_nearby_way')
    def test_ties_not_guessed(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'source.osm';p.write_text(OSM);g=WaterGraph(p)
            self.assertEqual(g.first_contact([(.0001,0)],5,5)['status'],'way_tie_ambiguous')
            self.assertEqual(g.first_contact([(.00005,0)],5,10)['status'],'node_tie_ambiguous')

if __name__=='__main__':unittest.main()
