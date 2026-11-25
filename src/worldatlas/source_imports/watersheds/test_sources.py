"""Test reading the points and lines named in a recipe from small source files."""

import json
from pathlib import Path
import tempfile
import unittest
import zipfile

import osmium

from worldatlas.source_imports.watersheds.sources import Sources


class SourceGeometryTests(unittest.TestCase):
    """Exercise GeoJSON, ZIP member, and OSM node and line selections."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_geojson_selection_has_no_dependency_on_an_earlier_boundary(self):
        path = self.root / 'source.geojson'
        path.write_text(json.dumps({'features': [{'geometry': {
            'type': 'LineString', 'coordinates': [[0, 0], [1, 1], [2, 0]]}}]}))
        sources = Sources({'provider': path})
        line = sources.read_source_line(dict(source='provider', geojson_feature=0))
        self.assertEqual(list(line.coords), [(0., 0.), (1., 1.), (2., 0.)])

    def test_geojson_feature_positions_cannot_wrap_or_exceed_the_file(self):
        path = self.root / 'source.geojson'
        path.write_text(json.dumps({'features': [{'geometry': {
            'type': 'LineString', 'coordinates': [[0, 0], [1, 1]]}}]}))
        sources = Sources({'provider': path})
        for position in (-1, 1):
            with self.subTest(position=position), self.assertRaisesRegex(ValueError, 'position is outside'):
                sources.read_source_line(dict(source='provider', geojson_feature=position))

    def test_relation_order_is_reconstructed_from_its_selected_source_members(self):
        path = self.root / 'river.osm'
        # The relation lists the ways out of order, and both start at node 2.
        # The source line still follows 1 → 2 → 3.
        path.write_text('<osm version="0.6"><node id="1" lon="0" lat="0"/>'
                        '<node id="2" lon="1" lat="1"/><node id="3" lon="2" lat="0"/>'
                        '<way id="20"><nd ref="2"/><nd ref="3"/></way>'
                        '<way id="10"><nd ref="2"/><nd ref="1"/></way>'
                        '<relation id="30"><member type="way" ref="20" role="main_stream"/>'
                        '<member type="way" ref="10" role="main_stream"/></relation></osm>')
        sources = Sources({'river': path})
        line = sources.read_source_line(dict(source='river', relation='30', role='main_stream'))
        self.assertEqual(list(line.coords), [(0., 0.), (1., 1.), (2., 0.)])

    def test_selected_geojson_archive_member_is_read_without_extraction(self):
        archive = self.root / 'provider.zip'
        geometry = {'type': 'LineString', 'coordinates': [[0, 0], [1, 1]]}
        document = json.dumps({'features': [{'geometry': geometry}]})
        with zipfile.ZipFile(archive, 'w') as output:
            output.writestr('nested/source.geojson', document)
            output.writestr('../source.geojson', document)
        sources = Sources({'provider': archive})
        selection = {'source': 'provider', 'geojson_feature': 0, 'member': 'nested/source.geojson'}
        self.assertEqual(list(sources.read_source_line(selection).coords), [(0., 0.), (1., 1.)])
        with self.assertRaisesRegex(ValueError, 'invalid source archive member'):
            sources.read_source_line(dict(selection, member='../source.geojson'))
        self.assertEqual(list(self.root.iterdir()), [archive])

    def test_network_reads_the_selected_pbf_or_xml_member_of_an_archive(self):
        archive = self.root / 'provider.zip'
        pbf = self.root / 'way.osm.pbf'
        with osmium.SimpleWriter(str(pbf)) as writer:
            writer.add_node(osmium.osm.mutable.Node(id=1, location=(0., 0.)))
            writer.add_node(osmium.osm.mutable.Node(id=2, location=(1., 1.)))
            writer.add_way(osmium.osm.mutable.Way(id=10, nodes=[1, 2], tags={'waterway': 'stream'}))
        with zipfile.ZipFile(archive, 'w') as output:
            output.write(pbf, 'nested/way.osm.pbf')
            output.writestr('nested/way.osm', '<osm version="0.6"><node id="1" lon="0" lat="0"/>'
                            '<node id="2" lon="1" lat="1"/><way id="10"><nd ref="1"/><nd ref="2"/>'
                            '<tag k="waterway" v="stream"/></way></osm>')
            output.writestr('unused.osm', 'not an OSM document')
        sources = Sources({'provider': archive})
        for member in ('nested/way.osm.pbf', 'nested/way.osm'):
            with self.subTest(member=member):
                network = sources.read_osm_network([{'source': 'provider', 'member': member}], rivers_and_streams_only=True)
                self.assertEqual(list(network.way_line(10).coords), [(0., 0.), (1., 1.)])
        self.assertFalse((self.root / 'extracted').exists())

    def test_unused_shapefile_line_selection_is_not_silently_accepted(self):
        sources = Sources({})
        with self.assertRaisesRegex(ValueError, 'unsupported source line selection'):
            sources.read_source_line({'source': 'unused', 'feature_field': 'ID', 'feature': 42})

    def test_invalid_source_coordinates_are_rejected(self):
        path = self.root / 'invalid.geojson'
        path.write_text(json.dumps({'features': [{'geometry': {
            'type': 'LineString', 'coordinates': [[0, 0], [0, 100]]}}]}))
        sources = Sources({'provider': path})
        with self.assertRaisesRegex(ValueError, 'finite WGS84'):
            sources.read_source_line({'source': 'provider', 'geojson_feature': 0})

    def test_geojson_selection_requires_a_line_with_two_points(self):
        path = self.root / 'provider.geojson'
        for geometry, error in (
            ({'type': 'Point', 'coordinates': [0, 0]}, 'must be a line'),
            ({'type': 'LineString', 'coordinates': [[0, 0]]}, 'at least two selected points'),
        ):
            path.write_text(json.dumps({'features': [{'geometry': geometry}]}))
            with self.subTest(geometry=geometry), self.assertRaisesRegex(ValueError, error):
                Sources({'provider': path}).read_source_line({'source': 'provider', 'geojson_feature': 0})

    def test_standalone_vector_source_alias_resolves_to_the_local_path(self):
        path = self.root / 'basins.shp'
        path.touch()
        self.assertEqual(Path(Sources({'basins': path}).resolve_vector_path('basins')), path.resolve())

    def test_relation_selection_ignores_other_roles_and_rejects_a_separate_loop(self):
        path = self.root / 'river.osm'
        nodes = ''.join(f'<node id="{node}" lon="{node}" lat="0"/>' for node in range(1, 6))
        ways = ('<way id="10"><nd ref="1"/><nd ref="2"/></way>'
                '<way id="20"><nd ref="3"/><nd ref="4"/><nd ref="5"/><nd ref="3"/></way>')
        path.write_text(f'<osm version="0.6">{nodes}{ways}'
                        '<relation id="30"><member type="way" ref="10" role="main_stream"/>'
                        '<member type="way" ref="20" role="side_stream"/></relation>'
                        '<relation id="40"><member type="way" ref="10" role="main_stream"/>'
                        '<member type="way" ref="20" role="main_stream"/></relation></osm>')
        sources = Sources({'river': path})
        self.assertEqual(sources.resolve_recipe_point({'source': 'river', 'node': 1}, {}), (1., 0.))
        with self.assertRaisesRegex(ValueError, 'unknown source point selection'):
            sources.resolve_recipe_point({}, {})
        self.assertEqual(list(sources.read_source_line({'source': 'river', 'way': 10}).coords),
                         [(1., 0.), (2., 0.)])
        selection = {'source': 'river', 'relation': 30, 'role': 'main_stream'}
        self.assertEqual(sources.join_river_relation_ways(selection), [(1., 0.), (2., 0.)])
        with self.assertRaisesRegex(ValueError, 'unbranched chain'):
            sources.join_river_relation_ways(dict(selection, role='side_stream'))
        with self.assertRaisesRegex(ValueError, 'disconnected or closed'):
            sources.join_river_relation_ways(dict(selection, relation=40))

    def test_pbf_point_selection_includes_isolated_nodes_without_loading_ways(self):
        path = self.root / 'provider.osm.pbf'
        with osmium.SimpleWriter(str(path)) as writer:
            writer.add_node(osmium.osm.mutable.Node(id=42, location=(44., 43.), version=2))
            writer.add_node(osmium.osm.mutable.Node(id=99, location=(45., 44.), version=1))
            writer.add_node(osmium.osm.mutable.Node(id=101, location=(45., 91.), version=1))
        sources = Sources({'provider': path})
        specification = {'source': 'provider', 'node': 42}
        self.assertEqual(sources.resolve_recipe_point(specification, {}), (44., 43.))
        self.assertEqual(sources.resolve_recipe_point(specification, {}), (44., 43.))
        self.assertEqual(sources.networks, {})
        with self.assertRaisesRegex(ValueError, 'missing'):
            sources.resolve_recipe_point({'source': 'provider', 'node': 100}, {})
        with self.assertRaisesRegex(ValueError, 'invalid OSM node coordinates'):
            sources.resolve_recipe_point({'source': 'provider', 'node': 101}, {})

    def test_network_cache_keeps_reviewed_directions_separate(self):
        path = self.root / 'rivers.osm'
        path.write_text('<osm version="0.6"><node id="1" lon="0" lat="0"/>'
                        '<node id="2" lon="1" lat="1"/>'
                        '<way id="10"><nd ref="1"/><nd ref="2"/>'
                        '<tag k="waterway" v="river"/></way></osm>')
        sources = Sources({'rivers': path})
        normal = sources.read_osm_network(['rivers'], rivers_and_streams_only=True)
        reverse = sources.read_osm_network(['rivers'], rivers_and_streams_only=True, reverse=['10'])
        self.assertEqual(normal.ways['10'].nodes, ('1', '2'))
        self.assertEqual(reverse.ways['10'].nodes, ('2', '1'))
        self.assertIs(normal, sources.read_osm_network(['rivers'], rivers_and_streams_only=True))


if __name__ == '__main__':
    unittest.main()
