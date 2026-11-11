import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from pyproj import CRS
import shapefile

from watersheds.sources import Sources


class SourceGeometryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def shape_archive(self):
        path = self.root / 'lines.shp'
        with shapefile.Writer(path, shapeType=shapefile.POLYLINE) as layer:
            layer.field('SOURCE_ID', 'N', decimal=0)
            layer.line([[(0, 0), (1, 1), (2, 0)]])
            layer.record(42)
        path.with_suffix('.prj').write_text(CRS.from_epsg(4326).to_wkt())
        archive = self.root / 'provider.zip'
        with zipfile.ZipFile(archive, 'w') as z:
            for extension in ('.shp', '.shx', '.dbf', '.prj'):
                z.write(path.with_suffix(extension), 'nested/lines' + extension)
        return archive

    def test_selected_source_vertices_and_edge_fraction_are_preserved(self):
        with Sources({'provider': self.shape_archive()}) as sources:
            line = sources.line([dict(source='provider', member='nested/lines.shp',
                                      feature_field='SOURCE_ID', feature=42,
                                      vertices=[{'edge': [0, .5]}, 1, 2])])
        self.assertEqual(list(line.coords), [(.5, .5), (1., 1.), (2., 0.)])

    def test_geojson_selection_has_no_dependency_on_an_earlier_boundary(self):
        path = self.root / 'source.geojson'
        path.write_text(json.dumps({'features': [{'geometry': {
            'type': 'LineString', 'coordinates': [[0, 0], [1, 1], [2, 0]]}}]}))
        with Sources({'provider': path}) as sources:
            line = sources.line([dict(source='provider', geojson_feature=0, vertices=[0, 1, 2])])
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
        with Sources({'river': path}) as sources:
            line = sources.line([dict(source='river', relation='30', role='main_stream', start_node='1')])
        self.assertEqual(list(line.coords), [(0., 0.), (1., 1.), (2., 0.)])

    def test_archive_member_cannot_escape_its_source_directory(self):
        with Sources({'provider': self.shape_archive()}) as sources:
            with self.assertRaisesRegex(ValueError, 'invalid source archive member'):
                sources.member('provider', '../lines.shp')

    def test_invalid_source_coordinates_are_rejected(self):
        with Sources({}) as sources:
            with self.assertRaisesRegex(ValueError, 'finite WGS84'):
                sources.line([{'point': [0, 0]}, {'point': [0, 100]}])


if __name__ == '__main__':
    unittest.main()
