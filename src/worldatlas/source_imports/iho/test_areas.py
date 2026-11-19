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
from shapely.geometry import shape

from worldatlas.source_imports.iho.areas import SeaAreas, surface
from worldatlas.source_imports.iho.areas import NS, EPSG_4326
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

    def test_command_selects_and_verifies_the_saved_gml_member(self):
        gml = ElementTree.tostring(document(area("area", "urn:mrn:example", patch(SQUARE))))
        archive = BytesIO()
        with ZipFile(archive, "w") as output:
            output.writestr("unused.gml", b"unused member")
            output.writestr("selected.gml", gml)
        raw = archive.getvalue()
        recipe = dict(
            source_id="iho-test", gml_member="selected.gml",
            gml_sha256=hashlib.sha256(gml).hexdigest(),
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
                        (Jsonb(dict(recipe, gml_sha256="0" * 64)),),
                    )
                    with self.assertRaisesRegex(ValueError, "IHO GML SHA-256 mismatch"):
                        main()
                    self.assertEqual(database.execute(stored).fetchone(), (geometry,))
                client.get_object.assert_called_once_with(Bucket="test", Key="s130.zip")


class AreaTests(unittest.TestCase):
    def test_hole_is_preserved(self):
        hole = [(0.5, 0.5), (1.5, 0.5), (1.5, 1.5), (0.5, 1.5), (0.5, 0.5)]
        reader = SeaAreas(document(area("a", "mrn", patch(SQUARE, hole))))
        geometry, ident = reader.geometry("mrn")
        self.assertEqual(ident, "a")
        self.assertEqual(shape(geometry).area, 3)

    def test_complete_shared_mrn_collection_keeps_every_piece(self):
        second = [(x + 5, y) for x, y in SQUARE]
        reader = SeaAreas(
            document(
                area("parent", "mrn", children=["a", "b"]),
                area("a", "mrn", patch(SQUARE), parent="parent"),
                area("b", "mrn", patch(second), parent="parent"),
            )
        )
        geometry, ident = reader.geometry("mrn")
        self.assertEqual(reader.roots(), {"parent": "mrn"})
        self.assertEqual(ident, "parent")
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
        self.assertEqual(shape(reader.geometry("large")[0]).area, 4)
        self.assertEqual(shape(reader.geometry("small")[0]).area, 1)

    def test_dateline_splits_without_world_spanning_interior(self):
        points = [(179, 0), (-179, 0), (-179, 2), (179, 2), (179, 0)]
        result = surface(
            ElementTree.fromstring(
                patch(points)
                .replace("<g:", "<g:")
                .replace(
                    "<g:PolygonPatch>",
                    '<g:PolygonPatch xmlns:g="' + NS["gml"] + '">',
                    1,
                )
            )
        )
        self.assertEqual(result.area, 4)
        self.assertEqual(len(result.geoms), 2)
        self.assertTrue(result.is_valid)

    def test_missing_cyclic_or_ambiguous_collection_is_rejected(self):
        examples = [
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

    def test_explicit_polar_cap_preserves_both_world_edges(self):
        points = [(180, 70), (0, 75), (-180, 70), (-180, 90), (180, 90), (180, 70)]
        result = shape(
            SeaAreas(document(area("a", "mrn", patch(points)))).geometry("mrn")[0]
        )
        self.assertTrue(result.is_valid)
        self.assertEqual(result.bounds, (-180, 70, 180, 90))
