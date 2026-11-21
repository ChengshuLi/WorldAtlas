"""Native-grid polygon rasterization and exact boundary incidence."""

import json
import math
from fractions import Fraction

import numpy as np
from osgeo import gdal, ogr, osr

from worldatlas.map_build.core.wrapping import wrapped_grid_bounds


class PolygonRasterizer:
    """Prepare one validated source geometry for repeated native-grid windows."""

    def __init__(self, geometry, grid):
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

    def rasterize(self, bounds=None):
        """Rasterize all source pieces, preserving holes and longitude wrapping."""
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


def rasterize(geometry, grid, bounds=None):
    """Rasterize a single source window; repeated callers can prepare it once."""
    return PolygonRasterizer(geometry, grid).rasterize(bounds)


def _ceil(n, d):
    return -((-n) // d)


def need(ok, message):
    if not ok:
        raise ValueError(message)


def reject_boundary_centers(geometry, grid, *, selected=None):
    """Solve exact segment/center incidence with integer congruences.

    Fraction in the reviewed algorithm denotes each supplied binary64 coordinate
    exactly. ``selected(x,y)`` can restrict rejection to relevant cells, such as
    physical land; contacts on other cells do not affect that calculation.
    as_integer_ratio gives that same value. One conversion per vertex
    and a common integer denominator per edge avoid repeated Fraction arithmetic.
    """
    grid = vars(grid)
    step = Fraction(grid["step"])
    w, h = grid["width"], grid["height"]
    need(
        type(w) is int
        and type(h) is int
        and w > 0
        and h > 0
        and Fraction(str(grid["west"])) == -180
        and Fraction(str(grid["north"])) == 90
        and step > 0
        and h * step <= 180,
        "invalid global grid",
    )
    sn, sd = step.numerator, step.denominator

    def pixel(point):
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
                    need(
                        selected is not None,
                        "polygon boundary crosses grid cell center",
                    )
                    for y in range(hit, hi + 1, period):
                        x = (a * y + b) // denominator
                        need(
                            not selected(x, y),
                            "polygon boundary crosses grid cell center",
                        )
    return visits
