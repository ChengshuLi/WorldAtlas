from pathlib import Path
import tempfile
import unittest

from worldatlas.source_imports.features.geometry import geometry_hash
from worldatlas.source_imports.osm.features import assemble_rings, read_features


class OsmFeatureTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.path = Path(temporary.name) / 'source.osm'
        coordinates = {1: (0, 0), 2: (10, 0), 3: (10, 10), 4: (0, 10),
                       5: (2, 2), 6: (3, 2), 7: (3, 3), 8: (2, 3),
                       20: (20, 0), 21: (30, 0), 22: (30, 10), 23: (20, 10)}
        nodes = [f'<node id="{i}" version="1" lon="{lon}" lat="{lat}">'
                 '<tag k="name" v="Selected"/></node>' for i, (lon, lat) in coordinates.items()]
        ways = []
        for ident, refs in {10: [1, 2, 3], 20: [4, 3], 30: [4, 1],
                            40: [20, 21, 22, 23, 20], 50: [5, 6, 7, 8, 5]}.items():
            ways.append(f'<way id="{ident}" version="2">' + ''.join(
                f'<nd ref="{n}"/>' for n in refs) + '</way>')
        members = ''.join(f'<member type="way" ref="{i}" role="{role}"/>'
                          for i, role in [(10, 'outer'), (20, 'outer'), (30, 'outer'),
                                          (40, 'outer'), (50, 'inner')])
        relation = ('<relation id="100" version="3">' + members +
                    '<member type="node" ref="1" role="label"/>'
                    '<tag k="type" v="multipolygon"/><tag k="name" v="Selected"/></relation>')
        self.path.write_text('<osm version="0.6">' + ''.join(nodes + ways) + relation + '</osm>')
        self.selection = dict(feature_id='islands', source_feature_id='100', object_type='relation',
                              object_version='3', expected_tags={'name': 'Selected'},
                              ignored_member_roles=[['n', 'label']])

    def read(self, selection=None):
        return read_features(self.path, {'selections': [selection or self.selection]})[0]

    def test_unordered_and_reversed_way_members_join_with_holes_preserved(self):
        result = self.read()
        polygons = result['geometry']['coordinates']
        self.assertEqual(result['geometry']['type'], 'MultiPolygon')
        self.assertEqual(polygons[0][0], [[0., 0.], [10., 0.], [10., 10.], [0., 10.], [0., 0.]])
        self.assertEqual(len(polygons[0]), 2)
        self.assertEqual(len(polygons[1]), 1)
        self.selection['expected_geometry_sha256'] = geometry_hash(result['geometry'])
        self.assertEqual(self.read(), result)
        self.selection['expected_geometry_sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'checksum'):
            self.read()

    def test_outer_envelope_is_an_explicit_construction_choice(self):
        self.selection['holes'] = 'outer_envelope'
        self.assertEqual([len(p) for p in self.read()['geometry']['coordinates']], [1, 1])

    def test_anchor_selects_one_ring_without_discarding_or_misassigning_other_holes(self):
        self.selection.update(geometry_type='Polygon', ring_anchors=[dict(
            node_id='21', node_version='1', way_id='40', expected_tags={'name': 'Selected'})])
        geometry = self.read()['geometry']
        self.assertEqual(geometry, {'type': 'Polygon', 'coordinates': [
            [[20., 0.], [30., 0.], [30., 10.], [20., 10.], [20., 0.]]]})
        self.selection['ring_anchors'][0]['way_id'] = '10'
        with self.assertRaisesRegex(ValueError, 'anchor'):
            self.read()

    def test_nodes_closed_ways_and_parent_membership(self):
        node = dict(feature_id='point', source_feature_id='1', object_type='node', object_version='1',
                    parent_relation={'id': '100', 'version': '3', 'role': 'label'})
        self.assertEqual(self.read(node)['geometry'], {'type': 'Point', 'coordinates': [0., 0.]})
        node['parent_relation']['role'] = 'other'
        with self.assertRaisesRegex(ValueError, 'parent'):
            self.read(node)
        way = dict(feature_id='closed', source_feature_id='40', object_type='way', object_version='2')
        self.assertEqual(len(self.read(way)['geometry']['coordinates']), 1)
        way['source_feature_id'] = '10'
        with self.assertRaisesRegex(ValueError, 'open or branched'):
            self.read(way)

    def test_missing_versions_identity_and_unselected_roles_fail(self):
        for update, message in [({'source_feature_id': '999'}, 'missing'),
                                ({'object_version': '4'}, 'version'),
                                ({'expected_tags': {'name': 'Other'}}, 'identity'),
                                ({'ignored_member_roles': []}, 'member role')]:
            with self.subTest(update=update), self.assertRaisesRegex(ValueError, message):
                self.read(dict(self.selection, **update))

    def test_open_branches_missing_nodes_and_self_intersections_fail(self):
        for ways in ({1: [1, 2]}, {1: [1, 2], 2: [2, 3], 3: [2, 1]}):
            with self.assertRaisesRegex(ValueError, 'open or branched'):
                assemble_rings(ways)
        original = self.path.read_text()
        self.path.write_text(original.replace('<nd ref="22"/>', '<nd ref="999"/>'))
        with self.assertRaisesRegex(ValueError, 'missing nodes'):
            self.read()
        self.path.write_text(original.replace('<nd ref="21"/><nd ref="22"/>',
                                             '<nd ref="22"/><nd ref="21"/>'))
        with self.assertRaisesRegex(ValueError, 'valid'):
            self.read()


if __name__ == '__main__':
    unittest.main()
