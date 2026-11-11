from pathlib import Path
import tempfile
import unittest
import zipfile

import numpy as np
import osmium

from watersheds.terrain import Grid
from watersheds.waterways import Waterways, seed_grid


class WaterwayTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def write(self, name, body):
        path = self.root / name
        path.write_text('<osm version="0.6">' + body + '</osm>')
        return path

    def node(self, ident, lon=1, lat=1, version=1):
        return f'<node id="{ident}" version="{version}" lon="{lon}" lat="{lat}"/>'

    def way(self, ident, nodes, kind='river'):
        return (f'<way id="{ident}" version="1">' +
                ''.join(f'<nd ref="{n}"/>' for n in nodes) +
                f'<tag k="waterway" v="{kind}"/></way>')

    def test_all_natural_tributaries_are_included_and_artificial_ones_excluded(self):
        nodes = ''.join(self.node(i, lon=i / 10) for i in range(1, 7))
        path = self.write('network.osm', nodes + self.way(10, [1, 2]) +
                          self.way(11, [3, 1], 'stream') + self.way(12, [4, 3], 'stream') +
                          self.way(13, [5, 4], 'canal') + self.way(14, [6, 5], 'ditch'))
        groups, report = Waterways([path]).groups({37: ['10']})
        self.assertEqual(groups, {'10': 37, '11': 37, '12': 37})
        self.assertEqual(report, {'ambiguous': [], 'unassigned': [], 'incomplete': []})

    def test_conflicting_downstream_groups_remain_ambiguous(self):
        path = self.write('network.osm', ''.join(self.node(i, lon=i / 10) for i in [1, 2, 3]) +
                          self.way(10, [1, 2]) + self.way(20, [2, 3]))
        assigned, report = Waterways([path]).groups({1: ['10'], 2: ['20']})
        self.assertNotIn('10', assigned)
        self.assertIn('10', report['ambiguous'])

    def test_tributary_at_an_internal_vertex_keeps_its_downstream_connection(self):
        path = self.write('network.osm', ''.join(self.node(i, lon=i / 10) for i in range(1, 6)) +
                          self.way(10, [1, 2, 3, 4]) + self.way(20, [5, 3], 'stream'))
        graph = Waterways([path])
        assigned, report = graph.groups({37: ['10']})
        self.assertEqual(assigned, {'10': 37, '20': 37})
        self.assertEqual(report['unassigned'], [])
        self.assertEqual(list(graph.line(10).coords), [(i / 10, 1.) for i in range(1, 5)])

    def test_latest_pinned_object_version_is_used_regardless_of_file_order(self):
        old = self.write('old.osm', self.node(1, 1, 1, 1))
        new = self.write('new.osm', self.node(1, 2, 1, 2))
        self.assertEqual(Waterways([new, old]).nodes['1'], (2., 1.))

    def test_same_version_coordinate_conflict_is_rejected(self):
        first = self.write('first.osm', self.node(1, 1, 1))
        other = self.write('other.osm', self.node(1, 2, 1))
        with self.assertRaisesRegex(ValueError, 'same-version OSM node'):
            Waterways([first, other])

    def test_missing_referenced_nodes_are_exposed_and_cannot_seed_a_group(self):
        path = self.write('incomplete.osm', self.node(1) + self.way(10, [1, 2]))
        graph = Waterways([path])
        self.assertEqual(graph.incomplete, {'10'})
        with self.assertRaisesRegex(ValueError, 'missing or incomplete'):
            graph.groups({1: ['10']})

    def test_archive_responses_and_plain_xml_use_the_same_reader(self):
        path = self.write('network.osm', self.node(1) + self.node(2, 2) + self.way(10, [1, 2]))
        archive = self.root / 'responses.zip'
        with zipfile.ZipFile(archive, 'w') as z:
            z.write(path, 'response.osm')
        self.assertEqual(Waterways([path]).ways, Waterways([archive]).ways)

    def test_pbf_and_xml_preserve_the_same_objects_and_natural_network(self):
        path = self.write('network.osm', self.node(1) + self.node(2, 2) + self.node(3, 3) +
                          self.node(99, 4) + self.way(10, [1, 2]) + self.way(20, [2, 3], 'canal') +
                          '<relation id="30" version="1"><member type="way" ref="10" role="main_stream"/>'
                          '<member type="node" ref="1" role="spring"/></relation>')
        pbf = self.root / 'network.osm.pbf'
        writer = osmium.SimpleWriter(str(pbf))

        class Copy(osmium.SimpleHandler):
            def node(self, node):
                writer.add_node(node)

            def way(self, way):
                writer.add_way(way)

            def relation(self, relation):
                writer.add_relation(relation)

        Copy().apply_file(str(path))
        writer.close()
        for natural_only in (False, True):
            xml = Waterways([path], natural_only=natural_only)
            packed = Waterways([pbf], natural_only=natural_only)
            self.assertEqual(packed.nodes, xml.nodes)
            self.assertEqual(packed.ways, xml.ways)
            self.assertEqual(packed.relations, xml.relations)
            self.assertEqual(packed.groups({3: ['10']}), xml.groups({3: ['10']}))
        self.assertEqual(set(Waterways([pbf], natural_only=True).nodes), {'1', '2'})

    def test_later_artificial_classification_retires_an_older_natural_way(self):
        first = self.write('old.osm', self.node(1) + self.node(2, 2) + self.way(10, [1, 2]))
        other = self.write('new.osm', self.way(10, [1, 2], 'canal').replace('version="1"', 'version="2"'))
        for files in ([first, other], [other, first]):
            self.assertEqual(Waterways(files, natural_only=True).ways, {})

    def test_seed_raster_uses_actual_ids_and_native_cell_positions(self):
        path = self.write('network.osm', self.node(1, .1, 1.5) + self.node(2, 1.9, 1.5) +
                          self.node(3, .1, .5) + self.node(4, 1.9, .5) +
                          self.way(10, [1, 2]) + self.way(20, [3, 4]))
        grid = Grid(np.zeros((2, 2)), (0., 1., 0., 2., 0., -1.), 'EPSG:4326')
        network = Waterways([path])
        assigned, _ = network.groups({3: ['10'], 9876543210: ['20']})
        seeds, report = seed_grid(network, assigned, grid)
        np.testing.assert_array_equal(seeds, [[3, 3], [9876543210, 9876543210]])
        self.assertEqual(report['conflicting_seed_cells'], 0)

    def test_non_waterway_source_geometry_is_preserved_but_not_used_for_drainage(self):
        path = self.write('coast.osm', self.node(1, .1, 1.5) + self.node(2, 1.9, 1.5) +
                          self.way(10, [1, 2], 'coastline'))
        graph = Waterways([path])
        self.assertEqual(list(graph.line(10).coords), [(.1, 1.5), (1.9, 1.5)])
        self.assertEqual(graph.natural, set())


if __name__ == '__main__':
    unittest.main()
