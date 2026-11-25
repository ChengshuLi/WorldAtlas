"""Rasterize polygons on the native map grid."""

import math
from functools import cached_property

import numpy as np
from osgeo import gdal, ogr, osr
from shapely import bounds, get_parts
from shapely.geometry import MultiPolygon, Polygon
from shapely.geometry.base import BaseGeometry

from worldatlas.map_build.core.grid import Grid, column_windows


def polygon_grid_bounds(
    geometry: BaseGeometry, grid: Grid
) -> tuple[int, int, int, int]:
    """Find a grid window that encloses every piece of a polygon.

    Args:
        geometry: Validated WGS84 polygon or multipolygon.
        grid: Grid to which the window is aligned.

    Returns:
        (first column, end column, first row, end row), with exclusive ends.
        The end column may exceed the grid width when the window crosses
        180°. A polygon south of the grid has an empty row interval.

    Raises:
        ValueError: The geometry is empty, is not polygonal, or has no
            longitude span on the grid.
    """
    if not isinstance(geometry, (Polygon, MultiPolygon)) or geometry.is_empty:
        raise ValueError("expected a nonempty Polygon or MultiPolygon")

    # Keep each piece's longitude span separate so space between pieces can
    # be skipped. Use 0 to 360 for columns measured eastward from 180°W.
    piece_bounds = bounds(get_parts(geometry))
    spans = sorted(
        (west - grid.west, east - grid.west) for west, _, east, _ in piece_bounds
    )
    merged = []
    for start, end in spans:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))

    # The shortest window includes everything except the largest empty gap.
    # Include the gap from the last piece around to the first.
    next_starts = [start for start, _ in merged[1:]] + [merged[0][0] + 360]
    gaps = [start - end for start, (_, end) in zip(next_starts, merged, strict=True)]
    largest = max(range(len(gaps)), key=gaps.__getitem__)
    if gaps[largest] <= 0:
        first_column, end_column = 0, grid.width
    else:
        start = merged[(largest + 1) % len(merged)][0]
        end = merged[largest][1]
        if end < start:
            end += 360
        first_column = min(grid.width - 1, math.floor(start / grid.step))
        end_column = math.ceil(end / grid.step)
        if end_column - first_column >= grid.width:
            first_column, end_column = 0, grid.width
    if first_column == end_column:
        raise ValueError("invalid polygon grid bounds")

    south = float(piece_bounds[:, 1].min())
    north = float(piece_bounds[:, 3].max())
    first_row = min(grid.height, math.floor((grid.north - north) / grid.step))
    end_row = min(grid.height, math.ceil((grid.north - south) / grid.step))
    return first_column, end_column, first_row, end_row


class PolygonRasterizer:
    """Prepare one validated source geometry for repeated native-grid windows."""

    def __init__(self, geometry: BaseGeometry, grid: Grid) -> None:
        """Prepare a polygon once for use in multiple grid windows.

        Args:
            geometry: Validated WGS84 polygon or multipolygon.
            grid: Grid on which to rasterize it.
        """
        self.grid = grid
        self.geometry = geometry
        with ogr.ExceptionMgr():
            self.source = ogr.GetDriverByName("Memory").CreateDataSource("")
            spatial_reference = osr.SpatialReference()
            spatial_reference.SetFromUserInput("OGC:CRS84")
            self.layer = self.source.CreateLayer(
                "area", spatial_reference, geom_type=ogr.wkbUnknown
            )
            feature = ogr.Feature(self.layer.GetLayerDefn())
            feature.SetGeometry(ogr.CreateGeometryFromWkb(geometry.wkb))
            self.layer.CreateFeature(feature)
            self.projection = spatial_reference.ExportToWkt()

    @cached_property
    def bounds(self) -> tuple[int, int, int, int]:
        """Return the polygon's grid window with exclusive end columns and rows."""
        return polygon_grid_bounds(self.geometry, self.grid)

    def rasterize(
        self, bounds: tuple[int, int, int, int] | None = None
    ) -> tuple[tuple[int, int, int, int], np.ndarray]:
        """Mark covered cell centres using GDAL's polygon fill.

        Args:
            bounds: (first_column, end_column, first_row, end_row), or None to
                derive the bounds from the polygon. A window may wrap at ±180°.

        Returns:
            (bounds, mask). The 2-D bool mask has one entry for each cell in the
            window, with True for the cells GDAL marks as covered.

        Raises:
            ValueError: The window is invalid or GDAL cannot rasterize the polygon.
        """
        grid = self.grid
        if bounds is None:
            bounds = self.bounds
        x0, x1, y0, y1 = bounds
        if not (
            0 <= x0 < grid.width
            and 0 < x1 - x0 <= grid.width
            and 0 <= y0 <= y1 <= grid.height
        ):
            raise ValueError("invalid rasterization window")
        mask = np.zeros((y1 - y0, x1 - x0), dtype=bool)
        if y0 == y1:
            return bounds, mask
        windows = column_windows(x0, x1, grid.width)
        with ogr.ExceptionMgr(), gdal.ExceptionMgr():
            for first, last in windows:
                raster = gdal.GetDriverByName("MEM").Create(
                    "", last - first, y1 - y0, 1, gdal.GDT_Byte
                )
                raster.SetGeoTransform(
                    (
                        grid.west + first * grid.step,
                        grid.step,
                        0,
                        grid.north - y0 * grid.step,
                        0,
                        -grid.step,
                    )
                )
                raster.SetProjection(self.projection)
                if gdal.RasterizeLayer(raster, [1], self.layer, burn_values=[1]) != 0:
                    raise ValueError("polygon rasterization failed")
                offset = (first - x0) % grid.width
                mask[:, offset : offset + last - first] = raster.ReadAsArray() != 0
        return bounds, mask
