import unittest
from xml.etree import ElementTree

from shapely.geometry import shape

from worldatlas.source_imports.iho.areas import SeaAreas, surface
from worldatlas.source_imports.iho.s130 import NS, EPSG_4326


def patch(coordinates, hole=None):
    def ring(points, kind):
        return (f'<g:{kind}><g:LinearRing><g:posList srsName="{EPSG_4326}">'
                + ' '.join(str(value) for x, y in points for value in (y, x))
                + f'</g:posList></g:LinearRing></g:{kind}>')
    return '<g:PolygonPatch>' + ring(coordinates, 'exterior') + (
        ring(hole, 'interior') if hole else '') + '</g:PolygonPatch>'


def area(ident, mrn, geometry='', parent=None, children=()):
    return (f'<s:GlobalSeaArea g:id="{ident}"><s:featureIdentifier>{mrn}</s:featureIdentifier>'
            + (f'<s:theComponent x:href="#{parent}"/>' if parent else '')
            + ''.join(f'<s:theCollection x:href="#{child}"/>' for child in children)
            + geometry + '</s:GlobalSeaArea>')


def document(*areas):
    return ElementTree.fromstring(
        '<root xmlns:s="' + NS['s130'] + '" xmlns:g="' + NS['gml']
        + '" xmlns:x="http://www.w3.org/1999/xlink">' + ''.join(areas) + '</root>')


SQUARE = [(0, 0), (2, 0), (2, 2), (0, 2), (0, 0)]


class AreaTests(unittest.TestCase):
    def test_hole_is_preserved(self):
        hole = [(.5, .5), (1.5, .5), (1.5, 1.5), (.5, 1.5), (.5, .5)]
        reader = SeaAreas(document(area('a', 'mrn', patch(SQUARE, hole))))
        geometry, ident = reader.geometry('mrn')
        self.assertEqual(ident, 'a')
        self.assertEqual(shape(geometry).area, 3)

    def test_complete_shared_mrn_collection_keeps_every_piece(self):
        second = [(x + 5, y) for x, y in SQUARE]
        reader = SeaAreas(document(area('parent', 'mrn', children=['a', 'b']),
                                  area('a', 'mrn', patch(SQUARE), parent='parent'),
                                  area('b', 'mrn', patch(second), parent='parent')))
        geometry, ident = reader.geometry('mrn')
        self.assertEqual(reader.roots(), {'parent': 'mrn'})
        self.assertEqual(ident, 'parent')
        self.assertEqual(shape(geometry).area, 8)
        self.assertEqual(len(shape(geometry).geoms), 2)

    def test_parent_with_its_own_surface_is_not_replaced_by_subseas(self):
        reader = SeaAreas(document(area('parent', 'large', patch(SQUARE), children=['child']),
                                  area('child', 'small', patch([(x / 2, y / 2) for x, y in SQUARE]), parent='parent')))
        self.assertEqual(shape(reader.geometry('large')[0]).area, 4)
        self.assertEqual(shape(reader.geometry('small')[0]).area, 1)
        self.assertEqual(reader.parents('small'), ['large'])
        self.assertEqual(reader.parents('large'), [])

    def test_parent_identity_traverses_collection_parts(self):
        reader = SeaAreas(document(
            area('ocean', 'ocean-mrn', patch(SQUARE), children=['part']),
            area('part', 'ocean-mrn', parent='ocean', children=['sea']),
            area('sea', 'sea-mrn', patch(SQUARE), parent='part')))
        self.assertEqual(reader.parents('sea-mrn'), ['ocean-mrn'])

    def test_parent_cycle_is_rejected(self):
        reader = SeaAreas(document(area('a', 'a-mrn', patch(SQUARE), parent='b'),
                                  area('b', 'b-mrn', patch(SQUARE), parent='a')))
        with self.assertRaisesRegex(ValueError, 'cyclic'):
            reader.parents('a-mrn')

    def test_dateline_splits_without_world_spanning_interior(self):
        points = [(179, 0), (-179, 0), (-179, 2), (179, 2), (179, 0)]
        result = surface(ElementTree.fromstring(patch(points).replace('<g:', '<g:').replace(
            '<g:PolygonPatch>', '<g:PolygonPatch xmlns:g="' + NS['gml'] + '">', 1)))
        self.assertEqual(result.area, 4)
        self.assertEqual(len(result.geoms), 2)
        self.assertTrue(result.is_valid)

    def test_missing_cyclic_or_ambiguous_collection_is_rejected(self):
        examples = [document(area('p', 'mrn', children=['missing'])),
                    document(area('p', 'mrn', children=['p'])),
                    document(area('a', 'mrn', patch(SQUARE)), area('b', 'mrn', patch(SQUARE)))]
        for value in examples:
            with self.subTest(value=value), self.assertRaises(ValueError):
                SeaAreas(value).geometry('mrn')

    def test_bad_ring_is_rejected(self):
        for points in (SQUARE[:-1], [(0, 0), (1, 1), (0, 1), (1, 0), (0, 0)]):
            with self.subTest(points=points), self.assertRaises(ValueError):
                SeaAreas(document(area('a', 'mrn', patch(points)))).geometry('mrn')

    def test_explicit_polar_cap_preserves_both_world_edges(self):
        points = [(180, 70), (0, 75), (-180, 70), (-180, 90), (180, 90), (180, 70)]
        result = shape(SeaAreas(document(area('a', 'mrn', patch(points)))).geometry('mrn')[0])
        self.assertTrue(result.is_valid)
        self.assertEqual(result.bounds, (-180, 70, 180, 90))
