"""Native-grid polygon rasterization and exact boundary incidence."""

import json
import math
from collections.abc import Callable
from fractions import Fraction
from typing import Any

import numpy as np
from osgeo import gdal, ogr, osr

from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.core.wrapping import wrapped_grid_bounds


class PolygonRasterizer:
    """Prepare one validated source geometry for repeated native-grid windows."""

    def __init__(self, geometry: dict[str, Any], grid: Grid) -> None:
        """Prepare a polygon once for use in multiple grid windows.

        Args:
            geometry: GeoJSON Polygon or MultiPolygon in WGS84.
            grid: Grid on which to rasterize it.

        Raises:
            ValueError: The geometry is invalid or empty.
        """
        self.grid = grid
        self.geometry = geometry
        self.bounds = None
        with ogr.ExceptionMgr():
            self.source = ogr.GetDriverByName("Memory").CreateDataSource("")
            self.reference = osr.SpatialReference()
            self.reference.SetFromUserInput("OGC:CRS84")
            self.layer = self.source.CreateLayer(
                "area", self.reference, geom_type=ogr.wkbUnknown
            )
            imported = ogr.CreateGeometryFromJson(json.dumps(geometry, allow_nan=False))
            if imported is None or imported.IsEmpty() or not imported.IsValid():
                raise ValueError("invalid polygon geometry")
            feature = ogr.Feature(self.layer.GetLayerDefn())
            feature.SetGeometry(imported)
            self.layer.CreateFeature(feature)
            self.projection = self.reference.ExportToWkt()

    def rasterize(
        self, bounds: tuple[int, int, int, int] | None = None
    ) -> tuple[tuple[int, int, int, int], np.ndarray]:
        """Mark the cell centres covered by a polygon, including any holes.

        Args:
            bounds: (first_column, end_column, first_row, end_row), or None to
                derive the bounds from the polygon. A window may wrap at ±180°.

        Returns:
            (bounds, mask). The 2-D bool mask has one entry for each cell in the
            window, with True for the cells covered by the polygon.

        Raises:
            ValueError: The window is invalid or GDAL cannot rasterize the polygon.
        """
        grid = self.grid
        if bounds is None:
            if self.bounds is None:
                self.bounds, _ = wrapped_grid_bounds(
                    self.geometry, grid.width, grid.height, grid.step
                )
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
        windows = ((x0, min(x1, grid.width)),)
        if x1 > grid.width:
            windows += ((0, x1 - grid.width),)
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
                # OGR readers retain iteration state between rasterizations.
                self.layer.ResetReading()
                if gdal.RasterizeLayer(raster, [1], self.layer, burn_values=[1]) != 0:
                    raise ValueError("polygon rasterization failed")
                offset = (first - x0) % grid.width
                mask[:, offset : offset + last - first] = raster.ReadAsArray() != 0
        return bounds, mask


def rasterize(
    geometry: dict[str, Any],
    grid: Grid,
    bounds: tuple[int, int, int, int] | None = None,
) -> tuple[tuple[int, int, int, int], np.ndarray]:
    """Mark cells covered by a polygon in a single grid window.

    Args:
        geometry: GeoJSON Polygon or MultiPolygon in WGS84.
        grid: Grid on which to rasterize it.
        bounds: Optional window with exclusive end column and row.

    Returns:
        (bounds, mask), where mask is a 2-D bool array marking covered cells.
    """
    return PolygonRasterizer(geometry, grid).rasterize(bounds)


def _ceil(n: int, d: int) -> int:
    """Round the quotient up using exact integer division.

    Args:
        n: Numerator.
        d: Nonzero denominator.

    Returns:
        Smallest integer greater than or equal to n / d.
    """
    return -((-n) // d)


def reject_boundary_centers(
    geometry: dict[str, Any],
    grid: Grid,
    *,
    selected: Callable[[int, int], bool] | None = None,
) -> int:
    """Reject selected cell centres that fall exactly on a polygon edge.

    Express the stored coordinates exactly as fractions. A common denominator
    lets the edge check use integers, so a centre close to an edge still
    counts as distinct from the edge.

    Args:
        geometry: GeoJSON Polygon or MultiPolygon in WGS84.
        grid: Grid of cell centres to check.
        selected: Optional (column, row) test to ignore cells outside the
            calculation.

    Returns:
        Number of candidate grid rows inspected across all polygon edges.

    Raises:
        ValueError: An included cell centre lies on an edge.
    """
    step = Fraction(grid.step)
    w, h = grid.width, grid.height
    sn, sd = step.numerator, step.denominator

    def pixel(point: list[float] | tuple[float, float]) -> list[int]:
        """Express one coordinate in exact cell-centre units.

        Args:
            point: Longitude and latitude in degrees.

        Returns:
            [x_numerator, x_denominator, y_numerator, y_denominator]. The
            centre of the first cell is (0, 0) on this scale.
        """
        values = []
        for value, origin, sign in ((point[0], 180, 1), (point[1], 90, -1)):
            n, d = (
                value.as_integer_ratio()
                if hasattr(value, "as_integer_ratio")
                else Fraction(value).as_integer_ratio()
            )
            numerator, denominator = (
                2 * (sign * n + origin * d) * sd - sn * d,
                2 * d * sn,
            )
            g = math.gcd(numerator, denominator)
            values.extend((numerator // g, denominator // g))
        return values

    visits = 0
    polygons = (
        [geometry["coordinates"]]
        if geometry["type"] == "Polygon"
        else geometry["coordinates"]
    )
    for polygon in polygons:
        for ring in polygon:
            if len(ring) < 2:
                continue
            previous = pixel(ring[0])
            for point in ring[1:]:
                current = pixel(point)
                d = math.lcm(previous[1], previous[3], current[1], current[3])
                x0, y0 = (
                    previous[0] * (d // previous[1]),
                    previous[2] * (d // previous[3]),
                )
                x1, y1 = current[0] * (d // current[1]), current[2] * (d // current[3])
                previous = current
                if y0 == y1:
                    if y0 % d == 0 and 0 <= y0 // d < h:
                        first, last = (
                            max(0, _ceil(min(x0, x1), d)),
                            min(w - 1, max(x0, x1) // d),
                        )
                        if first <= last and (
                            selected is None
                            or any(selected(x, y0 // d) for x in range(first, last + 1))
                        ):
                            raise ValueError(
                                "polygon boundary crosses grid cell center"
                            )
                    continue
                lo, hi = max(0, _ceil(min(y0, y1), d)), min(h - 1, max(y0, y1) // d)
                visits += max(0, hi - lo + 1)
                if lo > hi:
                    continue
                dx, dy = x1 - x0, y1 - y0
                a, b, denominator = dx * d, x0 * dy - dx * y0, d * dy
                if denominator < 0:
                    a, b, denominator = -a, -b, -denominator
                if a > 0:
                    lo, hi = (
                        max(lo, _ceil(-b, a)),
                        min(hi, (denominator * w - 1 - b) // a),
                    )
                elif a < 0:
                    lo, hi = (
                        max(lo, _ceil(b - (denominator * w - 1), -a)),
                        min(hi, b // (-a)),
                    )
                elif not 0 <= b < denominator * w:
                    continue
                if lo > hi:
                    continue
                g = math.gcd(a, denominator)
                if b % g:
                    continue
                period = denominator // g
                residue = (-b // g * pow(a // g, -1, period)) % period
                hit = residue + _ceil(lo - residue, period) * period
                if hit <= hi:
                    if selected is None:
                        raise ValueError("polygon boundary crosses grid cell center")
                    for y in range(hit, hi + 1, period):
                        x = (a * y + b) // denominator
                        if selected(x, y):
                            raise ValueError(
                                "polygon boundary crosses grid cell center"
                            )
    return visits
