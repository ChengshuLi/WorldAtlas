import json
from pathlib import Path
import tempfile
import unittest
import zipfile

import osmium

from worldatlas.source_imports.watersheds.sources import Sources


class SourceGeometryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_geojson_selection_has_no_dependency_on_an_earlier_boundary(self):
        path = self.root / 'source.geojson'
        path.write_text(json.dumps({'features': [{'geometry': {
            'type': 'LineString', 'coordinates': [[0, 0], [1, 1], [2, 0]]}}]}))
        sources = Sources({'provider': path})
        line = sources.line([dict(source='provider', geojson_feature=0)])
        self.assertEqual(sources.point({'line': 'selected', 'endpoint': 'end'},
                                       {'selected': line}), (2., 0.))
        self.assertEqual(list(line.coords), [(0., 0.), (1., 1.), (2., 0.)])

    def test_relation_order_is_reconstructed_from_its_selected_source_members(self):
        path = self.root / 'river.osm'
        path.write_text('<osm><node id="1" lon="0" lat="0"/>'
                        '<node id="2" lon="1" lat="1"/><node id="3" lon="2" lat="0"/>'
                        '<way id="20"><nd ref="2"/><nd ref="3"/></way>'
                        '<way id="10"><nd ref="2"/><nd ref="1"/></way>'
                        '<relation id="30"><member type="way" ref="20" role="main_stream"/>'
                        '<member type="way" ref="10" role="main_stream"/></relation></osm>')
        sources = Sources({'river': path})
        line = sources.line([dict(source='river', relation='30', role='main_stream', start_node='1')])
        self.assertEqual(list(line.coords), [(0., 0.), (1., 1.), (2., 0.)])

    def test_archive_member_cannot_escape_its_source_directory(self):
        archive = self.root / 'provider.zip'
        with zipfile.ZipFile(archive, 'w') as output:
            output.writestr('nested/source.txt', 'source data')
        sources = Sources({'provider': archive})
        self.assertEqual(sources.member('provider', 'nested/source.txt').read_text(), 'source data')
        with self.assertRaisesRegex(ValueError, 'invalid source archive member'):
            sources.member('provider', '../lines.shp')

    def test_unused_shapefile_line_selection_is_not_silently_accepted(self):
        sources = Sources({})
        with self.assertRaisesRegex(ValueError, 'unsupported source line selection'):
            sources.line([{'source': 'unused', 'feature_field': 'ID', 'feature': 42}])

    def test_invalid_source_coordinates_are_rejected(self):
        path = self.root / 'invalid.geojson'
        path.write_text(json.dumps({'features': [{'geometry': {
            'type': 'LineString', 'coordinates': [[0, 0], [0, 100]]}}]}))
        sources = Sources({'provider': path})
        with self.assertRaisesRegex(ValueError, 'finite WGS84'):
            sources.line([{'source': 'provider', 'geojson_feature': 0}])

    def test_source_reader_does_not_invent_connectors_between_features(self):
        sources = Sources({})
        with self.assertRaisesRegex(ValueError, 'one source feature per line'):
            sources.line([{'source': 'provider', 'geojson_feature': 0},
                          {'source': 'provider', 'geojson_feature': 1}])

    def test_pbf_point_selection_includes_isolated_nodes_without_loading_ways(self):
        path = self.root / 'provider.osm.pbf'
        with osmium.SimpleWriter(str(path)) as writer:
            writer.add_node(osmium.osm.mutable.Node(id=42, location=(44., 43.), version=2))
            writer.add_node(osmium.osm.mutable.Node(id=99, location=(45., 44.), version=1))
        sources = Sources({'provider': path})
        specification = {'source': 'provider', 'node': 42}
        self.assertEqual(sources.point(specification, {}), (44., 43.))
        self.assertEqual(sources.point(specification, {}), (44., 43.))
        self.assertEqual(sources.networks, {})
        with self.assertRaisesRegex(ValueError, 'missing'):
            sources.point({'source': 'provider', 'node': 100}, {})

    def test_network_cache_keeps_reviewed_directions_separate(self):
        path = self.root / 'rivers.osm'
        path.write_text('<osm><node id="1" lon="0" lat="0"/>'
                        '<node id="2" lon="1" lat="1"/>'
                        '<way id="10"><nd ref="1"/><nd ref="2"/>'
                        '<tag k="waterway" v="river"/></way></osm>')
        sources = Sources({'rivers': path})
        normal = sources.network(['rivers'], natural_only=True)
        reverse = sources.network(['rivers'], natural_only=True, reverse=['10'])
        self.assertEqual(normal.ways['10'].nodes, ('1', '2'))
        self.assertEqual(reverse.ways['10'].nodes, ('2', '1'))
        self.assertIs(normal, sources.network(['rivers'], natural_only=True))


if __name__ == '__main__':
    unittest.main()
