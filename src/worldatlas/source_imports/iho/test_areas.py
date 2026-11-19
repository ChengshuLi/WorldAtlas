"""Test S-130 surface parsing and import of a selected GML member."""

from contextlib import nullcontext, redirect_stdout
import hashlib
from io import BytesIO, StringIO
import json
import os
import tempfile
import unittest
from unittest.mock import Mock, patch as mock_patch
from xml.etree import ElementTree
from zipfile import ZipFile

import psycopg
from psycopg.types.json import Jsonb
from shapely.geometry import GeometryCollection, LineString, MultiPolygon, Polygon, box, shape

from worldatlas.source_imports.iho.areas import (
    EPSG_4326,
    NS,
    SeaAreas,
    polygon_parts,
    read_polygon_patch,
    read_ring_coordinates,
)
from worldatlas.source_imports.run_import import main


def patch(coordinates, hole=None):
    def ring(points, kind):
        return (
            f'<g:{kind}><g:LinearRing><g:posList srsName="{EPSG_4326}">'
            + " ".join(str(value) for x, y in points for value in (y, x))
            + f"</g:posList></g:LinearRing></g:{kind}>"
        )

    return (
        "<g:PolygonPatch>"
        + ring(coordinates, "exterior")
        + (ring(hole, "interior") if hole else "")
        + "</g:PolygonPatch>"
    )


def area(ident, mrn, geometry="", parent=None, children=()):
    return (
        f'<s:GlobalSeaArea g:id="{ident}"><s:featureIdentifier>{mrn}</s:featureIdentifier>'
        + (f'<s:theComponent x:href="#{parent}"/>' if parent else "")
        + "".join(f'<s:theCollection x:href="#{child}"/>' for child in children)
        + geometry
        + "</s:GlobalSeaArea>"
    )


def document(*areas):
    return ElementTree.fromstring(
        '<root xmlns:s="'
        + NS["s130"]
        + '" xmlns:g="'
        + NS["gml"]
        + '" xmlns:x="http://www.w3.org/1999/xlink">'
        + "".join(areas)
        + "</root>"
    )


SQUARE = [(0, 0), (2, 0), (2, 2), (0, 2), (0, 0)]


@unittest.skipUnless(
    os.environ.get("WORLDATLAS_TEST_DATABASE_URL"), "requires disposable PostgreSQL"
)
class ImportTests(unittest.TestCase):
    """Exercise the command with a real database and a minimal S-130 archive."""

    def test_command_imports_only_the_selected_gml_member(self):
        gml = ElementTree.tostring(document(area("area", "urn:mrn:example", patch(SQUARE))))
        archive = BytesIO()
        with ZipFile(archive, "w") as output:
            output.writestr("unused.gml", b"unused member")
            output.writestr("selected.gml", gml)
        raw = archive.getvalue()
        recipe = dict(
            source_id="iho-test", gml_member="selected.gml",
            selections=[dict(feature_id="test-sea", source_feature_id="urn:mrn:example")],
        )
        client = Mock()
        client.get_object.return_value = {"Body": BytesIO(raw)}

        url = os.environ["WORLDATLAS_TEST_DATABASE_URL"]
        with tempfile.TemporaryDirectory() as work, psycopg.connect(url) as database:
            with database.transaction(force_rollback=True):
                database.execute(
                    "INSERT INTO atlas.source_assets "
                    "(id,title,provider,source_uri,license_name,license_uri,attribution,"
                    "r2_bucket,r2_key,sha256,size_bytes) "
                    "VALUES ('iho-test','Test','IHO','test:source','Test','test:license','Test',"
                    "'test','s130.zip',%s,%s)",
                    (hashlib.sha256(raw).hexdigest(), len(raw)),
                )
                database.execute(
                    "INSERT INTO atlas.construction_records(id,method,arguments,basis) "
                    "VALUES ('iho-recipe','s130_areas',%s,'Select one archived area')",
                    (Jsonb(recipe),),
                )
                argv = ["worldatlas-import", "--recipe", "iho-recipe", "--r2-endpoint",
                        "https://example.test", "--work-dir", work]
                output = StringIO()
                with (
                    mock_patch.dict(os.environ, NEON_DATABASE_URL=url),
                    mock_patch("sys.argv", argv),
                    mock_patch("psycopg.connect", side_effect=lambda *_args, **_kw: nullcontext(database)),
                    mock_patch("boto3.client", return_value=client),
                    redirect_stdout(output),
                ):
                    main()
                    stored = "SELECT geometry FROM atlas.source_features WHERE id='test-sea'"
                    geometry, = database.execute(stored).fetchone()
                    self.assertEqual(shape(geometry).area, 4)
                    result = json.loads(output.getvalue())
                    self.assertEqual(result["feature_ids"], ["test-sea"])
                    self.assertEqual(database.execute(
                        "SELECT source_id FROM atlas.construction_sources WHERE construction_id='iho-recipe'"
                    ).fetchall(), [("iho-test",)])

                    database.execute(
                        "UPDATE atlas.construction_records SET arguments=%s WHERE id='iho-recipe'",
                        (Jsonb(dict(recipe, gml_member="missing.gml")),),
                    )
                    with self.assertRaisesRegex(ValueError, "expected exactly one IHO GML member"):
                        main()
                    self.assertEqual(database.execute(stored).fetchone(), (geometry,))
                client.get_object.assert_called_once_with(Bucket="test", Key="s130.zip")


class AreaTests(unittest.TestCase):
    """Check sea-area assembly and polygon math on small XML fixtures."""

    def test_hole_is_preserved(self):
        hole = [(0.5, 0.5), (1.5, 0.5), (1.5, 1.5), (0.5, 1.5), (0.5, 0.5)]
        reader = SeaAreas(document(area("a", "mrn", patch(SQUARE, hole))))
        geometry = reader.geometry("mrn")
        self.assertEqual(shape(geometry).area, 3)

    def test_complete_shared_mrn_collection_keeps_every_piece(self):
        second = [(x + 5, y) for x, y in SQUARE]
        reader = SeaAreas(
            document(
                '<s:DataCoverage g:id="coverage"/>',
                area("parent", "mrn", children=["a", "b"]),
                area("a", "mrn", patch(SQUARE), parent="parent"),
                area("b", "mrn", patch(second), parent="parent"),
            )
        )
        geometry = reader.geometry("mrn")
        self.assertEqual(shape(geometry).area, 8)
        self.assertEqual(len(shape(geometry).geoms), 2)

    def test_parent_with_its_own_surface_is_not_replaced_by_subseas(self):
        reader = SeaAreas(
            document(
                area("parent", "large", patch(SQUARE), children=["child"]),
                area(
                    "child",
                    "small",
                    patch([(x / 2, y / 2) for x, y in SQUARE]),
                    parent="parent",
                ),
            )
        )
        self.assertEqual(shape(reader.geometry("large")).area, 4)
        self.assertEqual(shape(reader.geometry("small")).area, 1)

    def test_dateline_splits_without_world_spanning_interior(self):
        points = [(179, 0), (-179, 0), (-179, 2), (179, 2), (179, 0)]
        expected = MultiPolygon([box(179, 0, 180, 2), box(-180, 0, -179, 2)])
        for ring in (points, [(-longitude, latitude) for longitude, latitude in points]):
            with self.subTest(start=ring[0]):
                result = read_polygon_patch(document(patch(ring))[0])
                self.assertTrue(result.is_valid)
                self.assertEqual(result.geom_type, "MultiPolygon")
                self.assertTrue(result.equals(expected))

    def test_clipping_keeps_polygon_area_and_discards_edge_contacts(self):
        polygon = box(179, 0, 180, 1)
        clipped = GeometryCollection(
            [polygon, LineString([(180, 2), (180, 3)]), Polygon()]
        )
        self.assertEqual(polygon_parts(clipped), [polygon])

    def test_duplicate_xml_ids_and_missing_provider_ids_are_rejected(self):
        cases = (
            (document(area("a", "first"), area("a", "second")), "duplicate GML feature ID"),
            (document(area("a", "")), "S-130 area has no provider area ID"),
        )
        for value, message in cases:
            with self.subTest(case=message), self.assertRaisesRegex(ValueError, message):
                SeaAreas(value)

    def test_missing_cyclic_or_ambiguous_collection_is_rejected(self):
        examples = [
            document(area("p", "mrn")),
            document(area("p", "mrn", children=["missing"])),
            document(area("p", "mrn", children=["p"])),
            document(area("a", "mrn", patch(SQUARE)), area("b", "mrn", patch(SQUARE))),
        ]
        for value in examples:
            with self.subTest(value=value), self.assertRaises(ValueError):
                SeaAreas(value).geometry("mrn")

    def test_bad_ring_is_rejected(self):
        for points in (SQUARE[:-1], [(0, 0), (1, 1), (0, 1), (1, 0), (0, 0)]):
            with self.subTest(points=points), self.assertRaises(ValueError):
                SeaAreas(document(area("a", "mrn", patch(points)))).geometry("mrn")

    def test_ring_rejects_wrong_coordinate_system(self):
        position = document('<g:posList srsName="EPSG:3857">0 0</g:posList>')[0]
        with self.assertRaisesRegex(ValueError, "expected S-130 latitude/longitude"):
            read_ring_coordinates(position)

    def test_ring_requires_at_least_four_complete_coordinate_pairs(self):
        for values in ("0 0 0 1 0 0", "0 0 0 2 2 2 2 0 0"):
            position = document(f'<g:posList srsName="{EPSG_4326}">{values}</g:posList>')[0]
            with (
                self.subTest(coordinates=values),
                self.assertRaisesRegex(ValueError, "invalid S-130 ring coordinates"),
            ):
                read_ring_coordinates(position)

    def test_explicit_polar_cap_preserves_both_world_edges(self):
        points = [(180, 70), (0, 75), (-180, 70), (-180, 90), (180, 90), (180, 70)]
        result = shape(
            SeaAreas(document(area("a", "mrn", patch(points)))).geometry("mrn")
        )
        self.assertTrue(result.is_valid)
        self.assertEqual(result.bounds, (-180, 70, 180, 90))

    def test_ring_that_winds_around_pole_requires_an_explicit_pole_edge(self):
        points = [(-135, 80), (-45, 82), (45, 83), (135, 81), (-135, 80)]
        with self.assertRaisesRegex(ValueError, "does not close after unwrapping"):
            read_polygon_patch(document(patch(points))[0])
