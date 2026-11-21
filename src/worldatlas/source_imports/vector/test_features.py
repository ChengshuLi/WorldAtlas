"""Test vector selection, geometry checks, and CRS conversion."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

from osgeo import ogr, osr

from worldatlas.geodesy.geojson import validate_geometry
from worldatlas.source_imports.shared.sources import gdal_dataset_path
from worldatlas.source_imports.vector.features import read_features


class VectorTests(unittest.TestCase):
    """Exercise GDAL selection and conversion with small local datasets."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "features.geojson"
        self.recipe = {
            "id_field": "provider_id",
            "selections": [{"feature_id": "selected", "source_feature_id": "a"}],
        }
        self.write()

    def write(self, ids=("a", "b")):
        """Write the default GeoJSON selection fixture.

        Args:
            ids: Provider IDs for the features in file order.
        """
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

    def write_point_shapefile(self, source_crs=None):
        """Create a one-point Shapefile with its companion files.

        Args:
            source_crs: Optional GDAL coordinate reference for the layer.

        Returns:
            Path to the .shp member.
        """
        path = self.path.with_name("points.shp")
        source = ogr.GetDriverByName("ESRI Shapefile").CreateDataSource(str(path))
        layer = source.CreateLayer("points", source_crs, ogr.wkbPoint)
        feature = ogr.Feature(layer.GetLayerDefn())
        point = ogr.Geometry(ogr.wkbPoint)
        point.AddPoint_2D(20, 10)
        feature.SetGeometry(point)
        self.assertEqual(layer.CreateFeature(feature), 0)
        source = None
        return path

    def test_selects_point_by_provider_id(self):
        rows = read_features(self.path, **self.recipe)
        self.assertEqual(len(rows), 1)
        self.assertEqual(
            rows[0]["geometry"], {"type": "Point", "coordinates": [20, 10]}
        )

    def test_missing_and_duplicate_provider_ids(self):
        self.write(("b",))
        with self.assertRaisesRegex(ValueError, "missing"):
            read_features(self.path, **self.recipe)
        self.write(("a", "a"))
        with self.assertRaisesRegex(ValueError, "duplicated"):
            read_features(self.path, **self.recipe)

    def test_missing_id_field_or_native_feature(self):
        cases = (
            (dict(id_field="absent"), "selected provider ID field is missing"),
            (
                dict(id_field="@fid", selections=[dict(feature_id="label", source_feature_id=999)]),
                "selected provider feature is missing",
            ),
        )
        for options, message in cases:
            with self.subTest(options=options), self.assertRaisesRegex(ValueError, message):
                read_features(self.path, **dict(self.recipe, **options))

    def test_unrecognized_vector_file_is_rejected(self):
        path = self.path.with_suffix(".txt")
        path.write_text("This is not a vector dataset.")
        with self.assertRaisesRegex(ValueError, "source vector dataset cannot be opened"):
            read_features(path, **self.recipe)

    def test_selected_record_requires_geometry(self):
        document = json.loads(self.path.read_text())
        document["features"][0]["geometry"] = None
        self.path.write_text(json.dumps(document))
        with self.assertRaisesRegex(ValueError, "source feature has no geometry"):
            read_features(self.path, **self.recipe)

    def test_provider_geometry_can_backfill_distinct_existing_feature_ids(self):
        self.recipe["selections"].append(
            {"feature_id": "existing-alias", "source_feature_id": "a"}
        )
        result = read_features(self.path, **self.recipe)
        self.assertEqual(
            [r["feature_id"] for r in result], ["selected", "existing-alias"]
        )
        self.assertEqual(result[0]["geometry"], result[1]["geometry"])
        self.recipe["selections"][1]["feature_id"] = "selected"
        with self.assertRaisesRegex(ValueError, "unique"):
            read_features(self.path, **self.recipe)

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
        self.assertEqual(read_features(self.path, **recipe)[0]["geometry"], geometry)

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
        result = read_features(self.path, **self.recipe)[0]["geometry"]
        self.assertEqual(json.dumps(result), json.dumps(geometry))

    def test_native_ids_select_correct_geometry_when_only_some_features_have_ids(self):
        first = {"type": "Point", "coordinates": [10, 20]}
        second = {"type": "Point", "coordinates": [30, 40]}
        self.path.write_text(json.dumps({
            "type": "FeatureCollection",
            "features": [
                {"type": "Feature", "id": 1, "properties": {}, "geometry": first},
                {"type": "Feature", "properties": {}, "geometry": second},
            ],
        }))
        result = read_features(
            self.path,
            id_field="@fid",
            selections=[
                dict(feature_id="first", source_feature_id=1),
                dict(feature_id="second", source_feature_id=2),
            ],
        )
        self.assertEqual([item["geometry"] for item in result], [first, second])

    def test_geojson_can_store_a_geometry_without_a_feature_wrapper(self):
        geometry = {"type": "Point", "coordinates": [-0.0, 1e-24]}
        self.path.write_text(json.dumps(geometry))
        zipped = self.path.with_suffix(".zip")
        member = "nested/point.geojson"
        with ZipFile(zipped, "w") as archive:
            archive.write(self.path, member)
        for path, selected_member in ((self.path, None), (zipped, member)):
            with self.subTest(path=path):
                result = read_features(
                    path,
                    member=selected_member,
                    id_field="@fid",
                    selections=[dict(feature_id="point", source_feature_id=0)],
                )
                self.assertEqual(json.dumps(result[0]["geometry"]), json.dumps(geometry))

    def test_polygon_part_selection_preserves_original_rings_not_the_largest_part(self):
        small = [
            [[0, 0], [3, 0], [3, 3], [0, 3], [0, 0]],
            [[1, 1], [1, 2], [2, 2], [2, 1], [1, 1]],
        ]
        large = [[[10, 0], [20, 0], [20, 10], [10, 10], [10, 0]]]
        document = dict(
            type="FeatureCollection",
            features=[
                dict(
                    type="Feature",
                    properties=dict(provider_id="a"),
                    geometry=dict(type="MultiPolygon", coordinates=[large, small]),
                )
            ],
        )
        original = json.dumps(document)
        self.path.write_text(original)
        selection = self.recipe["selections"][0]
        selection["polygon_containing"] = [0.5, 0.5]
        result = read_features(self.path, **self.recipe)[0]["geometry"]
        self.assertEqual(result, dict(type="Polygon", coordinates=small))
        selection["fill_holes"] = False
        result = read_features(self.path, **self.recipe)[0]["geometry"]
        self.assertEqual(result, dict(type="Polygon", coordinates=small))
        selection["fill_holes"] = True
        result = read_features(self.path, **self.recipe)[0]["geometry"]
        expected = dict(type="Polygon", coordinates=[small[0]])
        self.assertTrue(validate_geometry(result).equals(validate_geometry(expected)))
        self.assertEqual(self.path.read_text(), original)
        for point in ([1.5, 1.5], [0, 0.5], [30, 30]):
            selection["polygon_containing"] = point
            with (
                self.subTest(point=point),
                self.assertRaisesRegex(ValueError, "strictly inside"),
            ):
                read_features(self.path, **self.recipe)

    def test_fill_holes_requires_polygon_geometry(self):
        self.recipe["selections"][0]["fill_holes"] = True
        with self.assertRaisesRegex(ValueError, "fill_holes requires a polygon source"):
            read_features(self.path, **self.recipe)

    def test_polygon_selection_point_uses_wgs84_after_source_conversion(self):
        document = dict(
            type="FeatureCollection",
            crs={"type": "name", "properties": {"name": "EPSG:3857"}},
            features=[
                dict(
                    type="Feature",
                    properties=dict(provider_id="a"),
                    geometry=dict(
                        type="MultiPolygon",
                        coordinates=[
                            [
                                [
                                    [1000, 1000],
                                    [2000, 1000],
                                    [2000, 2000],
                                    [1000, 2000],
                                    [1000, 1000],
                                ]
                            ],
                            [
                                [
                                    [3000, 1000],
                                    [4000, 1000],
                                    [4000, 2000],
                                    [3000, 2000],
                                    [3000, 1000],
                                ]
                            ],
                        ],
                    ),
                )
            ],
        )
        self.path.write_text(json.dumps(document))
        self.recipe["selections"][0]["polygon_containing"] = [0.012, 0.012]
        result = validate_geometry(read_features(self.path, **self.recipe)[0]["geometry"])
        self.assertEqual(result.geom_type, "Polygon")
        self.assertAlmostEqual(result.bounds[0], 0.00898315284)
        self.assertAlmostEqual(result.bounds[2], 0.01796630568)
        self.write()
        with self.assertRaisesRegex(ValueError, "needs polygon geometry"):
            read_features(self.path, **self.recipe)

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
        geometry = read_features(self.path, **self.recipe)[0]["geometry"]
        self.assertAlmostEqual(geometry["coordinates"][0], 10.0)
        self.assertAlmostEqual(geometry["coordinates"][1], 0.0)

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
        source.CreateLayer("other_points", crs, ogr.wkbPoint)
        source = None
        with self.assertRaisesRegex(ValueError, "select one source vector layer"):
            read_features(path, **self.recipe)
        with self.assertRaisesRegex(ValueError, "selected vector layer is missing"):
            read_features(path, layer="absent", **self.recipe)
        result = read_features(path, layer="points", **self.recipe)[0]
        self.assertAlmostEqual(result["geometry"]["coordinates"][0], 10)
        self.assertAlmostEqual(result["geometry"]["coordinates"][1], 0)

    def test_shapefile_requires_a_coordinate_reference(self):
        path = self.write_point_shapefile()
        with self.assertRaisesRegex(ValueError, "vector source has no coordinate reference"):
            read_features(
                path,
                id_field="@fid",
                selections=[dict(feature_id="point", source_feature_id=0)],
            )

    def test_rejects_a_local_grid_without_a_wgs84_conversion(self):
        reference = osr.SpatialReference()
        reference.SetLocalCS("Site grid")
        reference.SetLinearUnits("metre", 1)
        path = self.write_point_shapefile(reference)
        for use_exceptions in (False, True):
            with (
                self.subTest(use_exceptions=use_exceptions),
                osr.ExceptionMgr(useExceptions=use_exceptions),
                self.assertRaisesRegex(ValueError, "coordinate reference cannot be converted to WGS84"),
            ):
                read_features(
                    path,
                    id_field="@fid",
                    selections=[dict(feature_id="point", source_feature_id=0)],
                )

    def test_fails_if_gdal_cannot_initialize_wgs84(self):
        with (
            patch.object(osr.SpatialReference, "SetFromUserInput", return_value=1),
            self.assertRaisesRegex(ValueError, "unsupported output coordinate reference"),
        ):
            read_features(self.path, **self.recipe)

    def test_rejects_a_point_outside_its_source_projection(self):
        document = json.loads(self.path.read_text())
        document["crs"] = dict(type="name", properties={"name": "EPSG:32631"})
        document["features"][0]["geometry"]["coordinates"] = [1e12, 0]
        self.path.write_text(json.dumps(document))
        with self.assertRaisesRegex(ValueError, "source geometry coordinate conversion failed"):
            read_features(self.path, **self.recipe)

    def test_archive_member_selection(self):
        path = self.path.with_suffix(".zip")
        with ZipFile(path, "w") as archive:
            archive.write(self.path, "nested/source.geojson")
        self.recipe["member"] = "nested/source.geojson"
        self.assertEqual(
            read_features(path, **self.recipe)[0]["geometry"]["coordinates"], [20, 10]
        )
        with self.assertRaisesRegex(ValueError, "missing"):
            gdal_dataset_path(path, "missing")
        for member in ("../source.geojson", "/source.geojson"):
            with self.subTest(member=member), self.assertRaisesRegex(ValueError, "invalid source archive member"):
                gdal_dataset_path(path, member)
        with self.assertRaisesRegex(ValueError, "non-archive"):
            gdal_dataset_path(self.path, "member")
        # Cached archives may carry the provider's arbitrary file extension.
        opaque = path.with_suffix(".download")
        path.rename(opaque)
        self.assertEqual(
            read_features(opaque, **self.recipe)[0]["geometry"]["coordinates"], [20, 10]
        )

    def test_zip_with_one_shapefile_can_select_it_automatically(self):
        reference = osr.SpatialReference()
        reference.ImportFromEPSG(4326)
        shapefile = self.write_point_shapefile(reference)
        path = self.path.with_suffix(".zip")
        members = list(shapefile.parent.glob(f"{shapefile.stem}.*"))
        with ZipFile(path, "w") as archive:
            for member in members:
                archive.write(member, f"nested/{member.name}")
        result = read_features(
            path,
            id_field="@fid",
            selections=[dict(feature_id="point", source_feature_id=0)],
        )
        self.assertEqual(result[0]["geometry"], dict(type="Point", coordinates=[20, 10]))

        with ZipFile(path, "a") as archive:
            for member in members:
                archive.write(member, f"other/{member.name}")
        with self.assertRaisesRegex(ValueError, "select one vector dataset archive member"):
            gdal_dataset_path(path)
