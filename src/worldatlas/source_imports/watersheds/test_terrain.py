"""Test cropping a height map and filling its gaps from a second map."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from osgeo import gdal
from pyproj import CRS

from worldatlas.source_imports.watersheds import terrain
from worldatlas.source_imports.watersheds.terrain import align_raster_to_grid, prepare_elevation_grid, read_native_elevation_crop


class TerrainTests(unittest.TestCase):
    """Check that replacement heights leave the primary grid and valid heights intact."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_failed_array_wrapper_reports_the_terrain_error(self):
        cells = np.zeros((2, 2), dtype=np.float32)
        grid = terrain.TerrainGrid(cells, (0, 1, 0, 2, 0, -1), "EPSG:4326")
        with patch.object(terrain.gdal_array, 'OpenArray', return_value=None):
            with self.assertRaisesRegex(ValueError, 'could not open the terrain array'):
                terrain.wrap_array_as_raster(cells, grid)

    def raster(self, name, values, transform=(0., 1., 0., 2., 0., -1.), crs=4326):
        """Write a georeferenced test raster.

        Args:
            name: Filename under the fixture directory.
            values: Rows of raster values.
            transform: GDAL coefficients for the fixture grid.
            crs: Coordinate reference of the raster.

        Returns:
            The path of the written raster.
        """
        values = np.array(values, dtype='float64')
        path = self.root / name
        dataset = gdal.GetDriverByName('GTiff').Create(str(path), values.shape[1],
                                                    values.shape[0], 1, gdal.GDT_Float64)
        dataset.SetGeoTransform(transform)
        dataset.SetProjection(CRS.from_user_input(crs).to_wkt())
        dataset.GetRasterBand(1).SetNoDataValue(float('nan'))
        dataset.GetRasterBand(1).WriteArray(values)
        dataset = None
        return path

    def test_crop_preserves_native_values_and_alignment(self):
        path = self.raster('primary.tif', [[1, 2], [3, 4]])
        grid = read_native_elevation_crop([path], [.4, .4, 1.6, 1.6])
        np.testing.assert_array_equal(grid.elevation, [[1, 2], [3, 4]])

    def test_invalid_crop_requests_are_rejected(self):
        path = self.raster('primary.tif', [[1, 2], [3, 4]])
        for paths, bounds, error in (
            ([], [0, 0, 2, 2], 'source tiles and finite analysis bounds'),
            ([path], [0, 0, float('nan'), 2], 'source tiles and finite analysis bounds'),
            ([path], [2, 0, 1, 2], 'invalid analysis bounds'),
            ([path], [0, 0, 2, 91], 'invalid WGS84 analysis bounds'),
        ):
            with self.subTest(bounds=bounds, paths=paths), self.assertRaisesRegex(ValueError, error):
                read_native_elevation_crop(paths, bounds)

    def test_rotated_primary_grid_is_rejected(self):
        path = self.raster('rotated.tif', [[1, 2], [3, 4]], transform=(0., 1., .1, 2., 0., -1.))
        with self.assertRaisesRegex(ValueError, 'north-up native grid'):
            read_native_elevation_crop([path], [0, 0, 2, 2])

    def test_different_primary_crs_is_rejected(self):
        primary = self.raster('primary.tif', [[1, 2], [3, 4]])
        other = self.raster('other.tif', [[5, 6], [7, 8]], crs=3857)
        with self.assertRaisesRegex(ValueError, 'share one native grid and CRS'):
            read_native_elevation_crop([primary, other], [0, 0, 2, 2])

    def test_primary_tile_outside_crop_leaves_inside_values_unchanged(self):
        primary = self.raster('primary.tif', [[1, 2], [3, 4]])
        outside = self.raster('outside.tif', [[5, 6]], transform=(5., 1., 0., 2., 0., -1.))
        grid = read_native_elevation_crop([primary, outside], [0, 0, 2, 2])
        np.testing.assert_array_equal(grid.elevation, [[1, 2], [3, 4]])
        self.assertEqual(grid.transform, (0., 1., 0., 2., 0., -1.))

    def test_projected_bounds_select_the_exact_native_cells(self):
        values = np.arange(20).reshape(4, 5)
        path = self.raster('polar.tif', values,
                           transform=(2249900., 2., 0., 900100., 0., -2.), crs=3413)
        grid = read_native_elevation_crop([path], [2249902.5, 900094.5, 2249907.5, 900099.5], bounds_crs=3413)
        np.testing.assert_array_equal(grid.elevation, values[:3, 1:4])
        self.assertEqual(grid.transform, (2249902., 2., 0., 900100., 0., -2.))
        self.assertEqual(grid.window_offset, (0, 1))

    def test_projected_domain_gap_fill_preserves_valid_primary_heights(self):
        transform = (2249900., 2., 0., 900100., 0., -2.)
        primary = self.raster('polar.tif', [[3, np.nan], [np.nan, 8]], transform, 3413)
        secondary = self.raster('secondary.tif', [[11, 12], [13, 14]], transform, 3413)
        grid = prepare_elevation_grid([primary], [2249900, 900096, 2249904, 900100], [secondary], bounds_crs=3413)
        np.testing.assert_array_equal(grid.elevation, [[3, 12], [13, 8]])

    def test_gap_fill_and_height_offset_leave_valid_primary_values_unchanged(self):
        primary = self.raster('primary.tif', [[np.nan, 2], [3, np.nan]])
        secondary = self.raster('secondary.tif', [[11, 12], [13, 14]])
        offset = self.raster('offset.tif', [[1, 2], [3, 4]])
        grid = prepare_elevation_grid([primary], [0, 0, 2, 2], [secondary], offset)
        # Read 11 + 1 and 14 + 4 for the two gaps. Keep the primary 2 and 3.
        np.testing.assert_array_equal(grid.elevation, [[12, 2], [3, 18]])
        self.assertEqual(grid.secondary_cells, 2)

    def test_secondary_uses_bilinear_interpolation(self):
        primary = self.raster('primary.tif', [[np.nan] * 2] * 2,
                              transform=(1., 1., 0., 3., 0., -1.))
        secondary = self.raster('secondary.tif', [[10, 14], [18, 22]],
                                transform=(0., 2., 0., 4., 0., -2.))
        grid = prepare_elevation_grid([primary], [1, 1, 3, 3], [secondary])
        np.testing.assert_allclose(grid.elevation, [[13, 15], [17, 19]])

    def test_water_categories_are_aligned_without_mixing_codes(self):
        primary = self.raster('primary.tif', [[0] * 2] * 2,
                              transform=(1., 1., 0., 3., 0., -1.))
        mask = self.raster('water.tif', [[0, 1], [2, 3]],
                           transform=(0., 2., 0., 4., 0., -2.))
        grid = read_native_elevation_crop([primary], [1, 1, 3, 3])
        # Each result is a real category from the second map, with no averaging.
        np.testing.assert_array_equal(align_raster_to_grid([mask], grid, resampling='near'), [[0, 1], [2, 3]])

    def test_unfilled_gaps_are_rejected(self):
        primary = self.raster('primary.tif', [[np.nan, 2], [3, 4]])
        with self.assertRaisesRegex(ValueError, '1 missing cells'):
            prepare_elevation_grid([primary], [0, 0, 2, 2])

    def test_tiles_are_mosaicked_without_resampling(self):
        first = self.raster('first.tif', [[1, 2], [3, 4]])
        second = self.raster('second.tif', [[5, 6], [7, 8]],
                             transform=(2., 1., 0., 2., 0., -1.))
        grid = prepare_elevation_grid([first, second], [0, 0, 4, 2])
        np.testing.assert_array_equal(grid.elevation, [[1, 2, 5, 6], [3, 4, 7, 8]])

    def test_misaligned_primary_tiles_are_rejected(self):
        first = self.raster('first.tif', [[1, 2], [3, 4]])
        for shifted_origin in (.5, np.nextafter(2.0, np.inf)):
            with self.subTest(shifted_origin=shifted_origin):
                second = self.raster('second.tif', [[5, 6], [7, 8]],
                                     transform=(shifted_origin, 1., 0., 2., 0., -1.))
                with self.assertRaisesRegex(ValueError, 'not aligned'):
                    read_native_elevation_crop([first, second], [0, 0, 4, 2])

    def test_overlapping_crops_share_native_grid_node_identity(self):
        path = self.raster('primary.tif', np.arange(16).reshape(4, 4),
                           transform=(0., 1., 0., 4., 0., -1.))
        first = read_native_elevation_crop([path], [0, 0, 3, 3])
        second = read_native_elevation_crop([path], [1, 1, 4, 4])
        self.assertEqual(first.cell_coordinates(1, 1, center=False),
                         second.cell_coordinates(2, 0, center=False))
        self.assertEqual((first.window_offset[0] + 1, first.window_offset[1] + 1),
                         (second.window_offset[0] + 2, second.window_offset[1]))


if __name__ == '__main__':
    unittest.main()
