from pathlib import Path
import tempfile
import unittest
import zipfile

import numpy as np
import osmium
from shapely.geometry import LineString

from watersheds.terrain import Grid
from watersheds.drainage import single_destinations
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

    def test_real_junction_contact_is_allowed_independently_of_way_splits(self):
        nodes = (self.node(1, 0, 2) + self.node(2, 0, 0) +
                 self.node(3, -2, -2) + self.node(4, 2, -2))
        boundary = LineString([(-1, -.2), (0, 0), (1, -.2)])
        for name, ways in [('whole', self.way(10, [1, 2, 3])),
                           ('split', self.way(10, [1, 2]) + self.way(11, [2, 3]))]:
            network = Waterways([self.write(name + '.osm', nodes + ways + self.way(20, [2, 4]))])
            result = network.check_crossings(boundary)
            self.assertEqual(result['crossings'], [])
            self.assertEqual(result['junction_contacts'], ['2'])

    def test_crossing_at_an_arbitrary_way_split_is_still_rejected(self):
        nodes = self.node(1, 0, 2) + self.node(2, 0, 0) + self.node(3, 0, -2)
        for name, ways in [('whole', self.way(10, [1, 2, 3])),
                           ('split', self.way(10, [1, 2]) + self.way(11, [2, 3]))]:
            network = Waterways([self.write(name + '.osm', nodes + ways)])
            with self.assertRaisesRegex(ValueError, 'boundary crosses natural waterway'):
                network.check_crossings(LineString([(-1, 0), (1, 0)]))

    def test_real_river_head_contact_is_not_an_interior_crossing(self):
        network = Waterways([self.write('river.osm', self.node(1, 0, 0) + self.node(2, 0, 2) +
                                       self.way(10, [1, 2]))])
        result = network.check_crossings(LineString([(-1, 0), (1, 0)]))
        self.assertEqual(result['crossings'], [])
        self.assertEqual(result['river_endpoint_contacts'], ['1'])

    def test_unconnected_endpoint_at_the_same_coordinates_does_not_hide_a_crossing(self):
        network = Waterways([self.write('river.osm', self.node(1, 0, 2) + self.node(2, 0, 0) +
                                       self.node(3, 0, -2) + self.node(9, 0, 0) + self.node(10, 2, 1) +
                                       self.way(20, [1, 2, 3]) + self.way(30, [9, 10]))])
        with self.assertRaisesRegex(ValueError, 'boundary crosses natural waterway'):
            network.check_crossings(LineString([(-1, 0), (1, 0)]))

    def test_following_a_river_does_not_hide_a_separate_crossing(self):
        nodes = ''.join(self.node(i + 1, i, 0) for i in range(4))
        network = Waterways([self.write('river.osm', nodes + self.way(10, [1, 2, 3, 4]))])
        boundary = LineString([(0, 0), (1, 0), (1.5, 1), (2.5, -1), (3, -1)])
        with self.assertRaisesRegex(ValueError, 'boundary crosses natural waterway'):
            network.check_crossings(boundary)

    def test_followed_river_and_a_real_tributary_contact_are_allowed(self):
        nodes = self.node(1, -2, 0) + self.node(2, 0, 0) + self.node(3, 2, 0) + self.node(4, 0, 2)
        network = Waterways([self.write('river.osm', nodes + self.way(10, [1, 2, 3]) + self.way(20, [4, 2]))])
        result = network.check_crossings(LineString([(-1, 0), (1, 0)]))
        self.assertEqual(result['crossings'], [])
        self.assertEqual(result['junction_contacts'], ['2'])

    def test_a_closed_way_start_is_not_a_real_river_endpoint(self):
        nodes = ''.join(self.node(i, *p) for i, p in enumerate([(0, 0), (1, 0), (1, 1), (0, 1)], 1))
        network = Waterways([self.write('river.osm', nodes + self.way(10, [1, 2, 3, 4, 1]))])
        with self.assertRaisesRegex(ValueError, 'boundary crosses natural waterway'):
            network.check_crossings(LineString([(-.5, -.5), (.5, .5)]))

    def test_partly_unknown_fork_fails_early_and_two_known_destinations_pass(self):
        nodes = ''.join(self.node(i, *p) for i, p in enumerate([(.5, .9), (.5, .5), (.1, .1), (.9, .1)], 1))
        network = Waterways([self.write('fork.osm', nodes + self.way(10, [1, 2]) +
                                       self.way(20, [2, 3]) + self.way(30, [2, 4]))])
        _, report = network.groups({3: ['20']})
        with self.assertRaisesRegex(ValueError, '10.*unresolved downstream route'):
            network.require_destinations([[0, 0, 1, 1]], report)
        groups, report = network.groups({3: ['20'], 7: ['30']})
        network.require_destinations([[0, 0, 1, 1]], report)
        self.assertEqual(groups[('1', '2')], (3, 7))

    def test_unrelated_unknown_rivers_do_not_block_the_selected_area(self):
        nodes = self.node(1, .2, .8) + self.node(2, .2, .2) + self.node(3, 10, 11) + self.node(4, 10, 10)
        network = Waterways([self.write('rivers.osm', nodes + self.way(10, [1, 2]) + self.way(20, [3, 4]))])
        _, report = network.groups({3: ['10']})
        self.assertTrue(report['unresolved_sections'])
        network.require_destinations([[0, 0, 1, 1]], report)

    def test_known_destination_before_uncovered_estuary_does_not_fail_upstream(self):
        nodes = ''.join(self.node(i, *p) for i, p in enumerate([(.5, .9), (.5, .5), (.1, .1), (.9, .1)], 1))
        network = Waterways([self.write('estuary.osm', nodes + self.way(10, [1, 2]) +
                                       self.way(20, [2, 3]) + self.way(30, [2, 4]))])
        # The downstream reference already establishes this area's destination.
        # Uncovered estuary branches outside the calculation area do not undo it.
        assigned, report = network.groups({3: ['10']})
        network.require_destinations([[0, .6, 1, 1]], report)
        self.assertEqual(assigned[('1', '2')], (3,))

    def test_relevant_missing_coordinates_are_rejected(self):
        nodes = self.node(1, .2, .8) + self.node(2, .2, .5) + self.node(3, .2, .2)
        network = Waterways([self.write('rivers.osm', nodes + self.way(10, [1, 2, 3]) + self.way(20, [2, 99]))])
        _, report = network.groups({3: ['10']})
        with self.assertRaisesRegex(ValueError, '20.*missing source coordinates'):
            network.require_destinations([[0, 0, 1, 1]], report)

    def test_all_natural_tributaries_are_included_and_artificial_ones_excluded(self):
        nodes = ''.join(self.node(i, lon=i / 10) for i in range(1, 7))
        path = self.write('network.osm', nodes + self.way(10, [1, 2]) +
                          self.way(11, [3, 1], 'stream') + self.way(12, [4, 3], 'stream') +
                          self.way(13, [5, 4], 'canal') + self.way(14, [6, 5], 'ditch'))
        groups, report = Waterways([path]).groups({37: ['10']})
        self.assertEqual(groups, {('1', '2'): (37,), ('3', '1'): (37,), ('4', '3'): (37,)})
        self.assertEqual(report, {'ambiguous': [], 'unassigned': [], 'incomplete': [], 'shared_sections': [], 'unresolved_sections': []})

    def test_conflicting_downstream_groups_remain_ambiguous(self):
        path = self.write('network.osm', ''.join(self.node(i, lon=i / 10) for i in [1, 2, 3]) +
                          self.way(10, [1, 2]) + self.way(20, [2, 3]))
        assigned, report = Waterways([path]).groups({1: ['10'], 2: ['20']})
        self.assertEqual(assigned[('1', '2')], (1, 2))
        self.assertIn('10', report['ambiguous'])

    def test_tributary_at_an_internal_vertex_keeps_its_downstream_connection(self):
        path = self.write('network.osm', ''.join(self.node(i, lon=i / 10) for i in range(1, 6)) +
                          self.way(10, [1, 2, 3, 4]) + self.way(20, [5, 3], 'stream'))
        graph = Waterways([path])
        assigned, report = graph.groups({37: ['10']})
        self.assertEqual(assigned, {('1', '3'): (37,), ('3', '4'): (37,), ('5', '3'): (37,)})
        self.assertEqual(report['unassigned'], [])
        self.assertEqual(list(graph.line(10).coords), [(i / 10, 1.) for i in range(1, 5)])

    def test_latest_pinned_object_version_is_used_regardless_of_file_order(self):
        old = self.write('old.osm', self.node(1, 1, 1, 1))
        new = self.write('new.osm', self.node(1, 2, 1, 2))
        self.assertEqual(Waterways([new, old]).nodes['1'], (2., 1.))

    def test_later_memberships_can_reference_nodes_in_an_earlier_pbf(self):
        first = self.root / 'first.osm.pbf'
        with osmium.SimpleWriter(str(first)) as writer:
            for ident in (1, 2, 3):
                writer.add_node(osmium.osm.mutable.Node(id=ident, version=1,
                                                        location=(float(ident), 0.)))
            writer.add_way(osmium.osm.mutable.Way(id=10, version=1, nodes=[1, 2],
                                                 tags={'waterway': 'stream'}))
        second = self.root / 'second.osm.pbf'
        with osmium.SimpleWriter(str(second)) as writer:
            writer.add_way(osmium.osm.mutable.Way(id=10, version=2, nodes=[1, 3],
                                                 tags={'waterway': 'stream'}))
        xml = self.write('second.osm', self.way(10, [1, 3]).replace('version="1"', 'version="2"'))
        for later in (second, xml):
            for paths in ([first, later], [later, first]):
                with self.subTest(later=later.suffix, order=paths):
                    network = Waterways(paths, natural_only=True)
                    self.assertEqual(network.incomplete, set())
                    self.assertEqual(network.ways['10'].version, 2)
                    self.assertEqual(list(network.line(10).coords), [(1., 0.), (3., 0.)])
                    self.assertEqual(network.groups({7: ['10']})[0], {('1', '3'): (7,)})

    def test_conflicting_same_version_nodes_across_pbfs_are_rejected(self):
        paths = []
        for name, longitude in [('first', 1.), ('second', 2.)]:
            path = self.root / (name + '.osm.pbf')
            with osmium.SimpleWriter(str(path)) as writer:
                writer.add_node(osmium.osm.mutable.Node(id=1, version=1, location=(longitude, 0.)))
                writer.add_node(osmium.osm.mutable.Node(id=2, version=1, location=(3., 0.)))
                writer.add_way(osmium.osm.mutable.Way(id=10, version=1, nodes=[1, 2],
                                                     tags={'waterway': 'stream'}))
            paths.append(path)
        with self.assertRaisesRegex(ValueError, 'same-version OSM node'):
            Waterways(paths, natural_only=True)

    def test_latest_pbf_classification_can_remove_all_natural_memberships(self):
        paths = []
        for version, kind in [(1, 'stream'), (2, 'canal')]:
            path = self.root / f'version-{version}.osm.pbf'
            with osmium.SimpleWriter(str(path)) as writer:
                for ident in (1, 2):
                    writer.add_node(osmium.osm.mutable.Node(id=ident, version=1,
                                                            location=(float(ident), 0.)))
                writer.add_way(osmium.osm.mutable.Way(id=10, version=version, nodes=[1, 2],
                                                     tags={'waterway': kind}))
            paths.append(path)
        for ordered in (paths, paths[::-1]):
            network = Waterways(ordered, natural_only=True)
            self.assertEqual(network.ways, {})
            self.assertEqual(network.nodes, {})
            self.assertEqual(network.incomplete, set())

    def test_reviewed_reverse_uses_the_connected_downstream_network(self):
        path = self.write('network.osm', ''.join(self.node(i, lon=i / 10) for i in range(1, 5)) +
                          self.way(10, [1, 2, 3]) + self.way(20, [2, 4], 'stream'))
        network = Waterways([path], reverse=['20', '20'])
        assigned, report = network.groups({37: ['10']})
        self.assertEqual(assigned, {('1', '2'): (37,), ('2', '3'): (37,), ('4', '2'): (37,)})
        self.assertEqual(report['ambiguous'], [])
        self.assertEqual(list(network.line(20).coords), [(.4, 1.), (.2, 1.)])
        self.assertEqual(network.ways['20'].version, 1)

    def test_reviewed_reverse_requires_a_present_natural_way(self):
        path = self.write('network.osm', self.node(1) + self.node(2, 2) +
                          self.way(10, [1, 2], 'canal'))
        for ident in ['10', '999']:
            with self.subTest(ident=ident), self.assertRaisesRegex(ValueError, 'missing'):
                Waterways([path], reverse=[ident])

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
        np.testing.assert_array_equal(single_destinations(seeds, grid.elevation.shape),
                                      [[3, 3], [9876543210, 9876543210]])
        self.assertEqual(report['shared_seed_cells'], 0)

    def test_non_waterway_source_geometry_is_preserved_but_not_used_for_drainage(self):
        path = self.write('coast.osm', self.node(1, .1, 1.5) + self.node(2, 1.9, 1.5) +
                          self.way(10, [1, 2], 'coastline'))
        graph = Waterways([path])
        self.assertEqual(list(graph.line(10).coords), [(.1, 1.5), (1.9, 1.5)])
        self.assertEqual(graph.natural, set())


if __name__ == '__main__':
    unittest.main()
