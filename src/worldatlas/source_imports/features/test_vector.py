import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

from osgeo import ogr, osr

from worldatlas.source_imports.features.geometry import (
    geometry_bytes,
    geometry_hash,
    validate_geometry,
)
from worldatlas.source_imports.features.vector import dataset_path, read_features


class VectorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "worldatlas.source_imports.features.geojson"
        self.recipe = {
            "id_field": "provider_id",
            "selections": [{"feature_id": "selected", "source_feature_id": "a"}],
        }
        self.write()

    def write(self, ids=("a", "b")):
        self.path.write_text(
            json.dumps(
                {
                    "type": "FeatureCollection",
                    "features": [
                        {
                            "type": "Feature",
                            "properties": {"provider_id": ident, "name": "First"},
                            "geometry": {"type": "Point", "coordinates": [20 + i, 10]},
                        }
                        for i, ident in enumerate(ids)
                    ],
                }
            )
        )

    def test_selected_point_and_identity(self):
        rows = read_features(self.path, self.recipe)
        self.assertEqual(len(rows), 1)
        self.assertEqual(
            rows[0]["geometry"], {"type": "Point", "coordinates": [20, 10]}
        )
        self.assertEqual(rows[0]["source_feature_id"], "a")

    def test_missing_and_duplicate_provider_ids(self):
        self.write(("b",))
        with self.assertRaisesRegex(ValueError, "missing"):
            read_features(self.path, self.recipe)
        self.write(("a", "a"))
        with self.assertRaisesRegex(ValueError, "duplicated"):
            read_features(self.path, self.recipe)

    def test_provider_geometry_can_backfill_distinct_existing_feature_ids(self):
        self.recipe["selections"].append(
            {"feature_id": "existing-alias", "source_feature_id": "a"}
        )
        result = read_features(self.path, self.recipe)
        self.assertEqual(
            [r["feature_id"] for r in result], ["selected", "existing-alias"]
        )
        self.assertEqual(result[0]["geometry"], result[1]["geometry"])
        self.recipe["selections"][1]["feature_id"] = "selected"
        with self.assertRaisesRegex(ValueError, "unique"):
            read_features(self.path, self.recipe)

    def test_geojson_preserves_provider_numbers_and_integer_feature_ids(self):
        geometry = {"type": "Point", "coordinates": [-180, 1e-24]}
        self.path.write_text(
            json.dumps(
                {
                    "type": "FeatureCollection",
                    "features": [
                        {
                            "type": "Feature",
                            "id": 42,
                            "properties": {},
                            "geometry": geometry,
                        }
                    ],
                }
            )
        )
        recipe = dict(
            id_field="@fid",
            selections=[dict(feature_id="point", source_feature_id="42")],
        )
        self.assertEqual(read_features(self.path, recipe)[0]["geometry"], geometry)

    def test_geojson_preserves_small_coordinates_and_signed_zero(self):
        geometry = {"type": "Point", "coordinates": [-0.0, 1e-24]}
        self.path.write_text(
            json.dumps(
                {
                    "type": "FeatureCollection",
                    "features": [
                        {
                            "type": "Feature",
                            "properties": {"provider_id": "a", "name": "First"},
                            "geometry": geometry,
                        }
                    ],
                }
            )
        )
        result = read_features(self.path, self.recipe)[0]["geometry"]
        self.assertEqual(json.dumps(result), json.dumps(geometry))

    def test_projected_geojson_is_converted_instead_of_retaining_source_coordinates(
        self,
    ):
        self.path.write_text(
            json.dumps(
                {
                    "type": "FeatureCollection",
                    "crs": {"type": "name", "properties": {"name": "EPSG:3857"}},
                    "features": [
                        {
                            "type": "Feature",
                            "properties": {"provider_id": "a", "name": "First"},
                            "geometry": {
                                "type": "Point",
                                "coordinates": [1113194.9079327357, 0],
                            },
                        }
                    ],
                }
            )
        )
        geometry = read_features(self.path, self.recipe)[0]["geometry"]
        self.assertAlmostEqual(geometry["coordinates"][0], 10.0)
        self.assertAlmostEqual(geometry["coordinates"][1], 0.0)

    def test_complete_projected_collection_is_converted_to_longitude_latitude(self):
        polygons = []
        for left, right in ((1000, 2000), (2000, 3000)):
            polygons.append(
                {
                    "type": "Feature",
                    "properties": {"provider_id": "a", "name": "First"},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [
                                [left, 1000],
                                [right, 1000],
                                [right, 2000],
                                [left, 2000],
                                [left, 1000],
                            ]
                        ],
                    },
                }
            )
        self.path.write_text(
            json.dumps(
                {
                    "type": "FeatureCollection",
                    "crs": {"type": "name", "properties": {"name": "EPSG:3857"}},
                    "features": polygons,
                }
            )
        )
        self.recipe["selections"][0].update(collection=True, expected_feature_count=2)
        result = read_features(self.path, self.recipe)[0]
        self.assertNotIn("coordinate_reference", result)
        self.assertTrue(validate_geometry(result["geometry"]).is_valid)
        self.assertAlmostEqual(
            validate_geometry(result["geometry"]).bounds[0], 0.00898315284
        )
        self.recipe["selections"][0]["expected_feature_count"] = 3
        with self.assertRaisesRegex(ValueError, "number of features"):
            read_features(self.path, self.recipe)

    def test_projected_source_is_converted_with_xy_axis_order(self):
        path = self.path.with_suffix(".gpkg")
        source = ogr.GetDriverByName("GPKG").CreateDataSource(str(path))
        crs = osr.SpatialReference()
        crs.ImportFromEPSG(3857)
        layer = source.CreateLayer("points", crs, ogr.wkbPoint)
        layer.CreateField(ogr.FieldDefn("provider_id", ogr.OFTString))
        feature = ogr.Feature(layer.GetLayerDefn())
        feature.SetField("provider_id", "a")
        geometry = ogr.Geometry(ogr.wkbPoint)
        geometry.AddPoint_2D(1113194.9079327357, 0)
        feature.SetGeometry(geometry)
        layer.CreateFeature(feature)
        source = None
        result = read_features(path, self.recipe)[0]
        self.assertAlmostEqual(result["geometry"]["coordinates"][0], 10)
        self.assertAlmostEqual(result["geometry"]["coordinates"][1], 0)

    def test_archive_member_selection(self):
        path = self.path.with_suffix(".zip")
        with ZipFile(path, "w") as archive:
            archive.write(self.path, "nested/source.geojson")
        self.recipe["member"] = "nested/source.geojson"
        self.assertEqual(
            read_features(path, self.recipe)[0]["geometry"]["coordinates"], [20, 10]
        )
        with self.assertRaisesRegex(ValueError, "missing"):
            dataset_path(path, "missing")
        with self.assertRaisesRegex(ValueError, "non-archive"):
            dataset_path(self.path, "member")

    def test_invalid_geometry_is_rejected(self):
        for geometry in (
            {"type": "Point", "coordinates": [float("nan"), 1]},
            {"type": "Point", "coordinates": [1, 2, 3]},
            {"type": "Point", "coordinates": [True, 2]},
            {"type": "Point", "coordinates": ["1", 2]},
            {"type": "Point", "coordinates": [181, 2]},
            {"type": "Point", "coordinates": [1, -91]},
            {
                "type": "Polygon",
                "coordinates": [[[0, 0], [1, 1], [0, 1], [1, 0], [0, 0]]],
            },
        ):
            with self.subTest(geometry=geometry), self.assertRaises(ValueError):
                validate_geometry(geometry)


class GeometryChecksumTests(unittest.TestCase):
    def test_nested_signed_zero_uses_storage_form_without_mutating_or_rounding(self):
        point = [-0.0, 1e-24]
        for kind, coordinates in (
            ("Point", point),
            ("MultiPoint", [point]),
            ("LineString", [point, [1, 2]]),
            ("MultiLineString", [[point, [1, 2]]]),
            ("Polygon", [[point, [1, 0], [1, 2], point]]),
            ("MultiPolygon", [[[point, [1, 0], [1, 2], point]]]),
        ):
            with self.subTest(kind=kind):
                geometry = dict(type=kind, coordinates=coordinates)
                original = json.dumps(geometry)
                expected = json.loads(original.replace("-0.0", "0.0"))
                expected_bytes = json.dumps(
                    expected, sort_keys=True, separators=(",", ":")
                ).encode()
                self.assertEqual(geometry_bytes(geometry), expected_bytes)
                self.assertEqual(
                    geometry_hash(geometry), hashlib.sha256(expected_bytes).hexdigest()
                )
                self.assertEqual(json.dumps(geometry), original)
        self.assertNotEqual(
            geometry_hash(dict(type="Point", coordinates=[0, 1])),
            geometry_hash(dict(type="Point", coordinates=[0.0, 1])),
        )


class FootprintTests(unittest.TestCase):
    def test_explicit_group_extent_preserves_inputs_and_encloses_members(self):
        from copy import deepcopy
        from shapely.geometry import shape
        from worldatlas.source_imports.features.geometry import feature_footprint

        value = {
            "type": "MultiPolygon",
            "coordinates": [
                [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]],
                [[[3, 2], [4, 2], [4, 3], [3, 3], [3, 2]]],
            ],
        }
        before = deepcopy(value)
        self.assertIs(feature_footprint(value), value)
        self.assertEqual(
            shape(feature_footprint(value, "bounding_box")).bounds, (0, 0, 4, 3)
        )
        self.assertTrue(
            shape(feature_footprint(value, "bounding_box")).covers(shape(value))
        )
        self.assertEqual(value, before)

    def test_group_extent_wraps_the_dateline_without_covering_unrelated_longitudes(
        self,
    ):
        from shapely.geometry import shape, Point
        from worldatlas.source_imports.features.geometry import feature_footprint

        value = {
            "type": "MultiPolygon",
            "coordinates": [
                [[[178, 0], [179, 0], [179, 1], [178, 1], [178, 0]]],
                [[[-179, 0], [-178, 0], [-178, 1], [-179, 1], [-179, 0]]],
            ],
        }
        area = shape(feature_footprint(value, "bounding_box"))
        self.assertTrue(area.contains(Point(178.5, 0.5)))
        self.assertTrue(area.contains(Point(-178.5, 0.5)))
        self.assertFalse(area.contains(Point(0, 0.5)))

    def test_group_extents_reject_points_and_ambiguous_global_polygons(self):
        from worldatlas.source_imports.features.geometry import feature_footprint

        with self.assertRaisesRegex(ValueError, "polygon"):
            feature_footprint({"type": "Point", "coordinates": [0, 0]}, "bounding_box")
        wide = {
            "type": "Polygon",
            "coordinates": [
                [[-170, -10], [170, -10], [170, 10], [-170, 10], [-170, -10]]
            ],
        }
        with self.assertRaisesRegex(ValueError, "longitude"):
            feature_footprint(wide, "bounding_box")
