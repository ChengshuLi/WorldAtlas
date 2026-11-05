import tempfile
import unittest
from pathlib import Path
from pyproj import Transformer
from osm_water_graph import WaterGraph

OSM='''<osm>
<node id="1" lon="0.00000" lat="0"/>
<node id="2" lon="0.00010" lat="0"/>
<node id="3" lon="0.00020" lat="0"/>
<way id="10"><nd ref="1"/><nd ref="2"/><tag k="waterway" v="stream"/></way>
<way id="20"><nd ref="2"/><nd ref="3"/><tag k="waterway" v="river"/><tag k="name" v="Sample"/></way>
<way id="30"><nd ref="3"/><nd ref="missing"/><tag k="waterway" v="stream"/></way>
</osm>'''

class WaterGraphTests(unittest.TestCase):
    def test_directed_network_and_missing_nodes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'source.osm';path.write_text(OSM)
            graph=WaterGraph(path,3857)
            self.assertEqual(graph.incomplete,1)
            p=Transformer.from_crs(4326,3857,always_xy=True).transform(0,0)
            result=graph.first_contact([p],5,5)
            self.assertEqual(result['status'],'matched')
            self.assertEqual(result['way_id'],'10')
            self.assertEqual(result['names'],('Sample',))
            self.assertEqual(graph.first_contact([(10000,10000)],5,5)['status'],'no_nearby_way')
    def test_invalid_crs_rejected(self):
        with self.assertRaises(ValueError):WaterGraph('not-opened',4326)

if __name__=='__main__':unittest.main()
