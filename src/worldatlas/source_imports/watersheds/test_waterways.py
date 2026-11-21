"""Test how streams connect, where they drain, and when they cross a boundary."""

from pathlib import Path
import tempfile
import unittest
import zipfile

import numpy as np
import osmium
from shapely.geometry import LineString

from worldatlas.source_imports.watersheds.terrain import Grid
from worldatlas.source_imports.watersheds.drainage import unique_destination_labels
from worldatlas.source_imports.watersheds.waterways import (
    Waterways, rasterize_waterway_destinations, rasterize_waterway_lines,
)


class WaterwayTests(unittest.TestCase):
    """Use small archived stream networks with known connections and directions."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def write(self, name, body):
        """Write fixture OSM objects to an XML extract.

        Args:
            name: Filename under the fixture directory.
            body: Serialized OSM objects to place within the root element.

        Returns:
            The path to the extract.
        """
        path = self.root / name
        path.write_text('<osm version="0.6">' + body + '</osm>')
        return path

    def node(self, ident, lon=1, lat=1, version=1):
        """Create one OSM node for an XML fixture.

        Args:
            ident: OSM node ID.
            lon: Longitude in degrees.
            lat: Latitude in degrees.
            version: OSM version of the node.

        Returns:
            The node as XML text.
        """
        return f'<node id="{ident}" version="{version}" lon="{lon}" lat="{lat}"/>'

    def way(self, ident, nodes, kind='river'):
        """Create one OSM way with an ordered list of nodes.

        Args:
            ident: OSM way ID.
            nodes: Node IDs in source order.
            kind: Value of the OSM waterway tag.

        Returns:
            The way as XML text.
        """
        return (f'<way id="{ident}" version="1">' +
                ''.join(f'<nd ref="{n}"/>' for n in nodes) +
                f'<tag k="waterway" v="{kind}"/></way>')

    def test_selected_shared_drainage_fork_passes_independently_of_way_splits(self):
        nodes = (self.node(1, -2, 2) + self.node(2, 0, 0) +
                 self.node(3, 2, 2) + self.node(4, 2, -2))
        boundary = LineString([(-1, 0), (1, 0)])
        for name, ways in [('whole', self.way(10, [1, 2, 3])),
                           ('split', self.way(10, [1, 2]) + self.way(11, [2, 3]))]:
            network = Waterways([self.write(name + '.osm', nodes + ways + self.way(20, [2, 4]))])
            continuing = '10' if name == 'whole' else '11'
            for selections in ({3: [continuing, '20']}, {3: [continuing], 7: ['20']}):
                assigned, _ = network.trace_destinations_from_ways(selections)
                reviewed = {'2': network.drainage_groups_by_outgoing_node('2', assigned)}
                if len(selections) == 1:
                    with self.assertRaisesRegex(ValueError, 'boundary crosses a river or stream'):
                        network.check_boundary_crossings(boundary, shared_forks=reviewed)
            with self.assertRaisesRegex(ValueError, 'boundary crosses a river or stream'):
                network.check_boundary_crossings(boundary)
            result = network.check_boundary_crossings(boundary, shared_forks=reviewed)
            self.assertEqual(result['crossings'], [])
            self.assertEqual(result['junction_contacts'], ['2'])
            self.assertEqual(result['shared_drainage_contacts'], [{'node': '2', 'groups': [3, 7]}])

    def test_tributary_at_the_crossing_does_not_exempt_the_main_channel(self):
        nodes = (self.node(1, 0, 2) + self.node(2, 0, 0) +
                 self.node(3, 0, -2) + self.node(4, 2, 2))
        ways = self.way(10, [1, 2, 3]) + self.way(20, [4, 2])
        network = Waterways([self.write('confluence.osm', nodes + ways)])
        with self.assertRaisesRegex(ValueError, 'boundary crosses a river or stream'):
            network.check_boundary_crossings(LineString([(-1, 0), (1, 0)]))

    def test_a_point_touch_stays_on_one_side(self):
        nodes = self.node(1, 0, -2) + self.node(2, 0, 2)
        network = Waterways([self.write('river.osm', nodes + self.way(10, [1, 2]))])
        boundary = LineString([(-1, -1), (0, 0), (-1, 1)])
        self.assertEqual(network.check_boundary_crossings(boundary)['crossings'], [])

    def test_crossing_at_an_arbitrary_way_split_is_still_rejected(self):
        nodes = self.node(1, 0, 2) + self.node(2, 0, 0) + self.node(3, 0, -2)
        for name, ways in [('whole', self.way(10, [1, 2, 3])),
                           ('split', self.way(10, [1, 2]) + self.way(11, [2, 3]))]:
            network = Waterways([self.write(name + '.osm', nodes + ways)])
            with self.assertRaisesRegex(ValueError, 'boundary crosses a river or stream'):
                network.check_boundary_crossings(LineString([(-1, 0), (1, 0)]))

    def test_real_river_head_contact_is_not_an_interior_crossing(self):
        network = Waterways([self.write('river.osm', self.node(1, 0, 0) + self.node(2, 0, 2) +
                                       self.way(10, [1, 2]))])
        result = network.check_boundary_crossings(LineString([(-1, 0), (1, 0)]))
        self.assertEqual(result['crossings'], [])
        self.assertEqual(result['river_endpoint_contacts'], ['1'])

    def test_unconnected_endpoint_at_the_same_coordinates_does_not_hide_a_crossing(self):
        network = Waterways([self.write('river.osm', self.node(1, 0, 2) + self.node(2, 0, 0) +
                                       self.node(3, 0, -2) + self.node(9, 0, 0) + self.node(10, 2, 1) +
                                       self.way(20, [1, 2, 3]) + self.way(30, [9, 10]))])
        with self.assertRaisesRegex(ValueError, 'boundary crosses a river or stream'):
            network.check_boundary_crossings(LineString([(-1, 0), (1, 0)]))

    def test_following_a_river_does_not_hide_a_separate_crossing(self):
        nodes = ''.join(self.node(i + 1, i, 0) for i in range(4))
        network = Waterways([self.write('river.osm', nodes + self.way(10, [1, 2, 3, 4]))])
        boundary = LineString([(0, 0), (1, 0), (1.5, 1), (2.5, -1), (3, -1)])
        with self.assertRaisesRegex(ValueError, 'boundary crosses a river or stream'):
            network.check_boundary_crossings(boundary, followed_source_line=LineString([(0, 0), (1, 0)]))

    def test_followed_river_and_a_real_tributary_contact_are_allowed(self):
        nodes = self.node(1, -2, 0) + self.node(2, 0, 0) + self.node(3, 2, 0) + self.node(4, 0, 2)
        network = Waterways([self.write('river.osm', nodes + self.way(10, [1, 2, 3]) + self.way(20, [4, 2]))])
        result = network.check_boundary_crossings(LineString([(-1, 0), (1, 0)]))
        self.assertEqual(result['crossings'], [])
        self.assertEqual(result['junction_contacts'], ['2'])

    def test_crossing_along_the_boundary_depends_on_entry_and_exit_sides(self):
        # Water starts above this line and follows it from x = -1 to x = 1.
        # It crosses only when it leaves below. Try one way and three pieces.
        boundary = LineString([(-2, 0), (2, 0)])
        for split in (False, True):
            ways = (self.way(10, [1, 2]) + self.way(20, [2, 3]) + self.way(30, [3, 4])
                    if split else self.way(10, [1, 2, 3, 4]))
            for exit_latitude in (-1, 1):
                with self.subTest(split=split, exit_latitude=exit_latitude):
                    points = [(-1, 1), (-1, 0), (1, 0), (1, exit_latitude)]
                    nodes = ''.join(self.node(i, *p) for i, p in enumerate(points, 1))
                    network = Waterways([self.write('river.osm', nodes + ways)])
                    if exit_latitude < 0:
                        with self.assertRaisesRegex(ValueError, 'boundary crosses a river or stream'):
                            network.check_boundary_crossings(boundary)
                        followed = LineString([(-1, 0), (1, 0)])
                        self.assertEqual(network.check_boundary_crossings(
                            boundary, followed_source_line=followed)['crossings'], [])
                    else:
                        self.assertEqual(network.check_boundary_crossings(boundary)['crossings'], [])

    def test_shared_stretch_can_begin_and_end_between_saved_river_points(self):
        nodes = self.node(1, -1.5, 0) + self.node(2, 1.5, 0)
        network = Waterways([self.write('river.osm', nodes + self.way(10, [1, 2]))])
        for exit_latitude in (-1, 1):
            with self.subTest(exit_latitude=exit_latitude):
                boundary = LineString([(-2, 1), (-1, 0), (0, 0), (1, 0), (2, exit_latitude)])
                if exit_latitude < 0:
                    with self.assertRaisesRegex(ValueError, 'boundary crosses a river or stream'):
                        network.check_boundary_crossings(boundary)
                else:
                    self.assertEqual(network.check_boundary_crossings(boundary)['crossings'], [])

    def test_overlap_crossing_requires_a_connected_downstream_route(self):
        points = [(-1, 1), (-1, 0), (1, 0), (1, -1), (1, 0)]
        nodes = ''.join(self.node(i, *p) for i, p in enumerate(points, 1))
        boundary = LineString([(-2, 0), (2, 0)])
        for exit_node, shared_nodes in [(5, [2, 3]), (3, [3, 2])]:
            with self.subTest(exit_node=exit_node):
                ways = self.way(10, [1, 2]) + self.way(20, shared_nodes) + self.way(30, [exit_node, 4])
                network = Waterways([self.write('river.osm', nodes + ways)])
                self.assertEqual(network.check_boundary_crossings(boundary)['crossings'], [])

    def test_crossing_follows_more_than_one_shared_stretch(self):
        points = [(-1, 1), (-1, 0), (0, 0), (1, 0), (1, -1), (-1.5, 1)]
        nodes = ''.join(self.node(i, *p) for i, p in enumerate(points, 1))
        # A repeated source node adds no length and cannot break the route.
        # A second tributary joins at the same point as the first.
        for route in ([1, 2, 3, 3, 4, 5], [5, 4, 3, 3, 2, 1]):
            ways = self.way(10, route) + self.way(20, [6, 2])
            network = Waterways([self.write('river.osm', nodes + ways)])
            with self.subTest(route=route), self.assertRaisesRegex(ValueError, 'boundary crosses a river or stream'):
                network.check_boundary_crossings(LineString([(-2, 0), (2, 0)]))

    def test_followed_part_of_a_shared_stretch_interrupts_the_crossing_check(self):
        points = [(-1, 1), (-1, 0), (1, 0), (1, -1)]
        nodes = ''.join(self.node(i, *p) for i, p in enumerate(points, 1))
        network = Waterways([self.write('river.osm', nodes + self.way(10, [1, 2, 3, 4]))])
        boundary = LineString([(-2, 0), (2, 0)])
        source = LineString([(-1, 0), (0, 0)])
        with self.assertRaisesRegex(ValueError, 'boundary crosses a river or stream'):
            network.check_boundary_crossings(boundary)
        self.assertEqual(network.check_boundary_crossings(boundary, followed_source_line=source)['crossings'], [])

    def test_river_can_follow_the_line_past_both_boundary_endpoints(self):
        nodes = ''.join(self.node(i, *p) for i, p in enumerate([(-2, 0), (2, 0), (2, -1)], 1))
        network = Waterways([self.write('river.osm', nodes + self.way(10, [1, 2, 3]))])
        result = network.check_boundary_crossings(LineString([(-1, 0), (1, 0)]))
        self.assertEqual(result['crossings'], [])

    def test_a_closed_way_start_is_not_a_real_river_endpoint(self):
        nodes = ''.join(self.node(i, *p) for i, p in enumerate([(0, 0), (1, 0), (1, 1), (0, 1)], 1))
        network = Waterways([self.write('river.osm', nodes + self.way(10, [1, 2, 3, 4, 1]))])
        with self.assertRaisesRegex(ValueError, 'boundary crosses a river or stream'):
            network.check_boundary_crossings(LineString([(-.5, -.5), (.5, .5)]))

    def test_partly_unknown_fork_fails_early_and_two_known_destinations_pass(self):
        nodes = ''.join(self.node(i, *p) for i, p in enumerate([(.5, .9), (.5, .5), (.1, .1), (.9, .1)], 1))
        network = Waterways([self.write('fork.osm', nodes + self.way(10, [1, 2]) +
                                       self.way(20, [2, 3]) + self.way(30, [2, 4]))])
        partly_known, report = network.trace_destinations_from_ways({3: ['20']})
        self.assertEqual(network.drainage_groups_by_outgoing_node('2', partly_known), {})
        with self.assertRaisesRegex(ValueError, '10.*unresolved downstream route'):
            network.require_known_drainage_in_bounds([[0, 0, 1, 1]], report)
        groups, report = network.trace_destinations_from_ways({3: ['20'], 7: ['30']})
        network.require_known_drainage_in_bounds([[0, 0, 1, 1]], report)
        self.assertEqual(groups[('1', '2')], (3, 7))

    def test_unrelated_unknown_rivers_do_not_block_the_selected_area(self):
        nodes = self.node(1, .2, .8) + self.node(2, .2, .2) + self.node(3, 10, 11) + self.node(4, 10, 10)
        network = Waterways([self.write('rivers.osm', nodes + self.way(10, [1, 2]) + self.way(20, [3, 4]))])
        _, report = network.trace_destinations_from_ways({3: ['10']})
        self.assertTrue(report['unresolved_sections'])
        network.require_known_drainage_in_bounds([[0, 0, 1, 1]], report)

    def test_known_destination_before_uncovered_estuary_does_not_fail_upstream(self):
        nodes = ''.join(self.node(i, *p) for i, p in enumerate([(.5, .9), (.5, .5), (.1, .1), (.9, .1)], 1))
        network = Waterways([self.write('estuary.osm', nodes + self.way(10, [1, 2]) +
                                       self.way(20, [2, 3]) + self.way(30, [2, 4]))])
        # The downstream reference already establishes this area's destination.
        # Uncovered estuary branches outside the calculation area do not undo it.
        assigned, report = network.trace_destinations_from_ways({3: ['10']})
        network.require_known_drainage_in_bounds([[0, .6, 1, 1]], report)
        self.assertEqual(assigned[('1', '2')], (3,))

    def test_relevant_missing_coordinates_are_rejected(self):
        nodes = self.node(1, .2, .8) + self.node(2, .2, .5) + self.node(3, .2, .2)
        network = Waterways([self.write('rivers.osm', nodes + self.way(10, [1, 2, 3]) + self.way(20, [2, 99]))])
        _, report = network.trace_destinations_from_ways({3: ['10']})
        with self.assertRaisesRegex(ValueError, '20.*missing source coordinates'):
            network.require_known_drainage_in_bounds([[0, 0, 1, 1]], report)

    def test_bounds_crossing_the_antimeridian_check_both_sides(self):
        points = [
            (179.5, 0), (179.5, .5), (-179.5, 0), (-179.5, .5),
            (0, 0), (0, .5), (-179.75, 0),
        ]
        nodes = ''.join(self.node(ident, *point) for ident, point in enumerate(points, 1))
        ways = (self.way(10, [1, 2]) + self.way(20, [3, 4], 'stream') +
                self.way(30, [5, 6]) + self.way(40, [7, 99]))
        network = Waterways([self.write('rivers.osm', nodes + ways)])
        bounds = (179, -1, -179, 1)
        self.assertEqual(network.way_ids_intersecting_bounds(bounds), ['10', '20'])
        _, report = network.trace_destinations_from_ways({3: ['10', '20']})
        with self.assertRaisesRegex(ValueError, '40.*missing source coordinates'):
            network.require_known_drainage_in_bounds([bounds], report)

    def test_tracing_includes_streams_and_skips_canals_and_ditches(self):
        nodes = ''.join(self.node(i, lon=i / 10) for i in range(1, 7))
        path = self.write('network.osm', nodes + self.way(10, [1, 2]) +
                          self.way(11, [3, 1], 'stream') + self.way(12, [4, 3], 'stream') +
                          self.way(13, [5, 4], 'canal') + self.way(14, [6, 5], 'ditch'))
        groups, report = Waterways([path]).trace_destinations_from_ways({37: ['10']})
        self.assertEqual(groups, {('1', '2'): (37,), ('3', '1'): (37,), ('4', '3'): (37,)})
        self.assertEqual(report, {'ambiguous': [], 'unassigned': [], 'incomplete': [], 'shared_sections': [], 'unresolved_sections': []})

    def test_conflicting_downstream_groups_remain_ambiguous(self):
        path = self.write('network.osm', ''.join(self.node(i, lon=i / 10) for i in [1, 2, 3]) +
                          self.way(10, [1, 2]) + self.way(20, [2, 3]))
        assigned, report = Waterways([path]).trace_destinations_from_ways({1: ['10'], 2: ['20']})
        self.assertEqual(assigned[('1', '2')], (1, 2))
        self.assertIn('10', report['ambiguous'])

    def test_tributary_at_an_internal_vertex_keeps_its_downstream_connection(self):
        path = self.write('network.osm', ''.join(self.node(i, lon=i / 10) for i in range(1, 6)) +
                          self.way(10, [1, 2, 3, 4]) + self.way(20, [5, 3], 'stream'))
        graph = Waterways([path])
        assigned, report = graph.trace_destinations_from_ways({37: ['10']})
        self.assertEqual(assigned, {('1', '3'): (37,), ('3', '4'): (37,), ('5', '3'): (37,)})
        self.assertEqual(report['unassigned'], [])
        self.assertEqual(list(graph.way_line(10).coords), [(i / 10, 1.) for i in range(1, 5)])

    def test_latest_pinned_object_version_is_used_regardless_of_file_order(self):
        old = self.write('old.osm', self.node(1, 1, 1, 1))
        new = self.write('new.osm', self.node(1, 2, 1, 2))
        self.assertEqual(Waterways([new, old]).nodes['1'], (2., 1.))

    def test_relation_uses_newest_members_and_rejects_conflicting_same_version(self):
        old_members = '<member type="way" ref="10" role="main_stream"/>'
        new_members = '<member type="way" ref="20" role="main_stream"/>'
        old = self.write('old.osm', f'<relation id="1" version="1">{old_members}</relation>')
        new = self.write('new.osm', f'<relation id="1" version="2">{new_members}</relation>')
        for paths in ([old, new], [new, new, old]):
            with self.subTest(paths=paths):
                self.assertEqual(Waterways(paths).relations['1'], (2, (('way', '20', 'main_stream'),)))

        conflict = self.write('conflict.osm', f'<relation id="1" version="2">{old_members}</relation>')
        with self.assertRaisesRegex(ValueError, 'same-version OSM relation'):
            Waterways([new, conflict])

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
                    network = Waterways(paths, rivers_and_streams_only=True)
                    self.assertEqual(network.incomplete, set())
                    self.assertEqual(network.ways['10'].version, 2)
                    self.assertEqual(list(network.way_line(10).coords), [(1., 0.), (3., 0.)])
                    self.assertEqual(network.trace_destinations_from_ways({7: ['10']})[0], {('1', '3'): (7,)})

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
            Waterways(paths, rivers_and_streams_only=True)

    def test_latest_pbf_tags_can_remove_a_way_from_the_river_network(self):
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
            network = Waterways(ordered, rivers_and_streams_only=True)
            self.assertEqual(network.ways, {})
            self.assertEqual(network.nodes, {})
            self.assertEqual(network.incomplete, set())

    def test_reviewed_reverse_uses_the_connected_downstream_network(self):
        path = self.write('network.osm', ''.join(self.node(i, lon=i / 10) for i in range(1, 5)) +
                          self.way(10, [1, 2, 3]) + self.way(20, [2, 4], 'stream'))
        network = Waterways([path], reverse=['20', '20'])
        assigned, report = network.trace_destinations_from_ways({37: ['10']})
        self.assertEqual(assigned, {('1', '2'): (37,), ('2', '3'): (37,), ('4', '2'): (37,)})
        self.assertEqual(report['ambiguous'], [])
        self.assertEqual(list(network.way_line(20).coords), [(.4, 1.), (.2, 1.)])
        self.assertEqual(network.ways['20'].version, 1)

    def test_reversal_requires_a_present_river_or_stream(self):
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
            graph.trace_destinations_from_ways({1: ['10']})

    def test_archive_responses_and_plain_xml_use_the_same_reader(self):
        path = self.write('network.osm', self.node(1) + self.node(2, 2) + self.way(10, [1, 2]))
        archive = self.root / 'responses.zip'
        with zipfile.ZipFile(archive, 'w') as z:
            z.write(path, 'response.osm')
        self.assertEqual(Waterways([path]).ways, Waterways([archive]).ways)

    def test_pbf_and_xml_preserve_the_same_objects_and_river_network(self):
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
        for rivers_and_streams_only in (False, True):
            xml = Waterways([path], rivers_and_streams_only=rivers_and_streams_only)
            packed = Waterways([pbf], rivers_and_streams_only=rivers_and_streams_only)
            self.assertEqual(packed.nodes, xml.nodes)
            self.assertEqual(packed.ways, xml.ways)
            self.assertEqual(packed.relations, xml.relations)
            self.assertEqual(packed.trace_destinations_from_ways({3: ['10']}), xml.trace_destinations_from_ways({3: ['10']}))
        self.assertEqual(set(Waterways([pbf], rivers_and_streams_only=True).nodes), {'1', '2'})

    def test_later_canal_tag_removes_a_way_from_the_river_network(self):
        first = self.write('old.osm', self.node(1) + self.node(2, 2) + self.way(10, [1, 2]))
        other = self.write('new.osm', self.way(10, [1, 2], 'canal').replace('version="1"', 'version="2"'))
        for files in ([first, other], [other, first]):
            self.assertEqual(Waterways(files, rivers_and_streams_only=True).ways, {})

    def test_archive_requires_osm_files(self):
        path = self.root / 'empty.zip'
        with zipfile.ZipFile(path, 'w') as archive:
            archive.writestr('README.txt', 'No OSM extract here.')
        with self.assertRaisesRegex(ValueError, 'no XML responses'):
            Waterways([path])

    def test_way_geometry_requires_valid_coordinates_and_complete_nodes(self):
        invalid = self.write('invalid.osm', self.node(1, 0, 91) + self.node(2, 0, 0) + self.way(10, [1, 2]))
        with self.assertRaisesRegex(ValueError, 'invalid OSM node coordinates'):
            Waterways([invalid])
        incomplete = self.write('incomplete.osm', self.node(1) + self.way(10, [1, 2]))
        network = Waterways([incomplete])
        with self.assertRaisesRegex(ValueError, 'selected OSM way has missing nodes'):
            network.way_line(10)
        _, report = network.trace_destinations_from_ways({})
        network.require_known_drainage_in_bounds([[10, 10, 12, 12]], report)

    def test_same_version_way_must_have_the_same_members_and_tags(self):
        first = self.write('first.osm', self.node(1) + self.node(2, 2) + self.way(10, [1, 2]))
        for nodes, kind in (([2, 1], 'river'), ([1, 2], 'canal')):
            with self.subTest(nodes=nodes, kind=kind), self.assertRaisesRegex(ValueError, 'conflicting same-version OSM way'):
                Waterways([first, self.write('other.osm', self.way(10, nodes, kind))], rivers_and_streams_only=True)

    def test_way_destination_requires_a_known_group_with_a_source(self):
        for groups in ({-1: ['10']}, {3: []}):
            with self.subTest(groups=groups), self.assertRaisesRegex(ValueError, 'nonnegative group IDs and downstream ways'):
                Waterways([]).trace_destinations_from_ways(groups)

    def test_empty_waterway_raster_has_no_seed_cells(self):
        grid = Grid(np.zeros((1, 2)), (0., 1., 0., 1., 0., -1.), 'EPSG:4326')
        np.testing.assert_array_equal(rasterize_waterway_lines([], grid), [[False, False]])

    def test_seed_raster_uses_actual_ids_and_native_cell_positions(self):
        path = self.write('network.osm', self.node(1, .1, 1.5) + self.node(2, 1.9, 1.5) +
                          self.node(3, .1, .5) + self.node(4, 1.9, .5) +
                          self.way(10, [1, 2]) + self.way(20, [3, 4]))
        grid = Grid(np.zeros((2, 2)), (0., 1., 0., 2., 0., -1.), 'EPSG:4326')
        network = Waterways([path])
        assigned, _ = network.trace_destinations_from_ways({3: ['10'], 9876543210: ['20']})
        seeds, report = rasterize_waterway_destinations(network, assigned, grid)
        np.testing.assert_array_equal(unique_destination_labels(seeds, grid.elevation.shape),
                                      [[3, 3], [9876543210, 9876543210]])
        self.assertEqual(report['shared_seed_cells'], 0)

    def test_non_waterway_source_geometry_is_preserved_but_not_used_for_drainage(self):
        path = self.write('coast.osm', self.node(1, .1, 1.5) + self.node(2, 1.9, 1.5) +
                          self.way(10, [1, 2], 'coastline'))
        graph = Waterways([path])
        self.assertEqual(list(graph.way_line(10).coords), [(.1, 1.5), (1.9, 1.5)])
        self.assertEqual(graph.river_and_stream_ids, set())


if __name__ == '__main__':
    unittest.main()
