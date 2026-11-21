"""Batch exact tile-local water burns using GDAL's supported Python bindings.

Arrow batches populate tile layers without a Python Feature per polygon, while
gdal_array.OpenArray shares the existing NumPy tile with the rasterizer.
"""

import hashlib
import math
import struct
import time
from pathlib import Path
from typing import cast

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
from osgeo import gdal, gdal_array, ogr

import worldatlas.geodesy.ogr as geometry_io


def finite_points(
    data: np.ndarray, starts: np.ndarray, lengths: np.ndarray, selected: np.ndarray
) -> np.ndarray:
    """Identify finite two-dimensional points without decoding every geometry.

    Args:
        data: Flat uint8 array of WKB bytes.
        starts: Byte offset of each record.
        lengths: Byte length of each record.
        selected: Bool mask of records to inspect.

    Returns:
        Bool array marking standard finite Point records in either byte order.
    """
    result = np.zeros(len(starts), dtype=np.bool_)
    indices = np.flatnonzero(selected & (lengths == 21))
    if not len(indices):
        return result
    offsets = starts[indices]
    headers = data[offsets[:, None] + np.arange(5)]
    little = np.all(headers == [1, 1, 0, 0, 0], axis=1)
    big = np.all(headers == [0, 0, 0, 0, 1], axis=1)
    for mask, dtype in ((little, '<f8'), (big, '>f8')):
        slots = np.flatnonzero(mask)
        if len(slots):
            coordinates = (
                data[offsets[slots, None] + np.arange(5, 21)].view(dtype).reshape(-1, 2)
            )
            result[indices[slots]] = np.all(np.isfinite(coordinates), axis=1)
    return result


def strip_wkb(
    source: ogr.Geometry,
    top: float,
    bottom: float,
    step: float,
    coordinates: dict[tuple[int, ...], tuple[np.ndarray, np.ndarray, np.ndarray]],
    key: tuple[int, ...],
) -> bytes | None:
    """Keep the polygon edges that can affect a tile-row strip.

    Edges removed from a ring can be replaced by a bridge outside the visible
    rows. This preserves the original coordinates used at each visible row.

    Args:
        source: Polygon or multipolygon read from the source.
        top: Top latitude of the strip in degrees.
        bottom: Bottom latitude of the strip in degrees.
        step: One cell's height in degrees, used as padding.
        coordinates: Cache of ring coordinates and minimum and maximum edge
            latitudes.
        key: Cache key identifying this geometry or child polygon.

    Returns:
        WKB bytes for the polygon pieces that reach the strip, or None if empty.

    Raises:
        ValueError: The geometry is neither a polygon nor a multipolygon.
    """
    kind = ogr.GT_Flatten(source.GetGeometryType())
    if kind == ogr.wkbMultiPolygon:
        parts = [
            strip_wkb(
                cast(ogr.Geometry, source.GetGeometryRef(i)),
                top,
                bottom,
                step,
                coordinates,
                (*key, i),
            )
            for i in range(source.GetGeometryCount())
        ]
        parts = [part for part in parts if part is not None]
        return (
            struct.pack('<BII', 1, 6, len(parts)) + b''.join(parts) if parts else None
        )
    if kind != ogr.wkbPolygon:
        raise ValueError('unexpected strip geometry type')
    rings = []
    for i in range(source.GetGeometryCount()):
        ring_key = (*key, i)
        if ring_key not in coordinates:
            values = np.asarray(
                cast(ogr.Geometry, source.GetGeometryRef(i)).GetPoints(2),
                dtype=np.float64,
            ).reshape(-1, 2)
            ys = values[:, 1]
            following = np.roll(ys, -1)
            coordinates[ring_key] = (
                values,
                np.minimum(ys, following),
                np.maximum(ys, following),
            )
        values, low, high = coordinates[ring_key]
        edges = (low <= top + step) & (high >= bottom - step)
        keep = edges | np.roll(edges, 1)
        if not np.any(keep):
            if i == 0:
                return None
            continue
        retained = values[keep]
        if not np.array_equal(retained[0], retained[-1]):
            retained = np.vstack((retained, retained[0]))
        rings.append(
            struct.pack('<I', len(retained))
            + retained.astype('<f8', copy=False).tobytes()
        )
    return struct.pack('<BII', 1, 3, len(rings)) + b''.join(rings)


class WaterBatch:
    """Mark water from Arrow geometry batches using GDAL and NumPy tiles."""

    def __init__(
        self, output: Path | str | None = None, method: str = 'hybrid'
    ) -> None:
        """Prepare the batch rasterizer and its timing counters.

        Args:
            output: Legacy caller argument. The kernel writes to the raster supplied
                to burn.
            method: "hybrid" to batch polygon burns or "tiled" to limit them to
                individual tiles.

        Raises:
            ValueError: The rasterization method is unsupported.
        """
        if method not in ('hybrid', 'tiled'):
            raise ValueError(
                'method must be hybrid or tiled; global vector mode does not preserve tile-local pixel-center ties'
            )
        self.method = method
        self.provenance = {
            'implementation': 'python-gdal-api-v2',
            'method': method,
            'binding_sha256': hashlib.sha256(
                Path(__file__).read_bytes() + Path(geometry_io.__file__).read_bytes()
            ).hexdigest(),
            'gdal': gdal.VersionInfo(),
        }
        self.timings = {'parse_validate_index_seconds': 0.0, 'tile_burn_seconds': 0.0}

    def burn(
        self,
        raster: gdal.Dataset,
        geometry: pa.Array,
        selected: np.ndarray,
        grid: tuple[int, int, float, float, float],
        tile: int,
    ) -> tuple[np.ndarray, int | None]:
        """Mark selected polygon cells in the output raster.

        Args:
            raster: Target raster updated in place.
            geometry: Arrow column of WKB geometry byte strings.
            selected: Array marking which rows to inspect.
            grid: (width, height, west, north, step).
            tile: Tile size in cells.

        Returns:
            (status, failed_index), with a uint8 status per source row. A
            missing or unreadable geometry sets failed_index to its row.
            None means processing reached the end of the batch.
        """
        if isinstance(geometry, pa.ExtensionArray) and geometry.type.extension_name in (
            'geoarrow.wkb',
            'geoarrow.large_wkb',
        ):
            geometry = geometry.storage
        if not (
            pa.types.is_binary(geometry.type) or pa.types.is_large_binary(geometry.type)
        ):
            raise ValueError('GeoParquet geometry must be a binary WKB array')
        started = time.perf_counter()
        width, height, west, north, step = grid
        width = int(width)
        height = int(height)
        buffers = geometry.buffers()
        count = len(geometry)
        status = np.zeros(count, dtype=np.uint8)
        offsets = np.frombuffer(
            buffers[1],
            dtype=np.int64 if pa.types.is_large_binary(geometry.type) else np.int32,
        )
        starts = offsets[geometry.offset : geometry.offset + count]
        lengths = offsets[geometry.offset + 1 : geometry.offset + count + 1] - starts
        data = (
            np.frombuffer(buffers[2], dtype=np.uint8)
            if buffers[2] is not None
            else np.empty(0, dtype=np.uint8)
        )
        selected = np.asarray(selected, dtype=np.bool_)
        valid = np.ones(count, dtype=np.bool_)
        if buffers[0] is not None:
            bits = np.frombuffer(buffers[0], dtype=np.uint8)
            positions = np.arange(count) + geometry.offset
            valid = (bits[positions // 8] & (1 << (positions % 8))) != 0
        points = finite_points(data, starts, lengths, selected & valid)
        status[points] = 3
        tiles = {}
        coordinates = {}
        views = []
        parsed = []

        def fail(index: int | np.integer, code: int) -> tuple[np.ndarray, int]:
            """Stop the batch and record the first fatal geometry error.

            Args:
                index: Index of the failed geometry.
                code: Status to record for this error.

            Returns:
                Status array with later rows cleared, and the failed index.
            """
            status[index] = code
            status[index + 1 :] = 0
            return status, int(index)

        def extent(
            bounds: tuple[float, float, float, float],
        ) -> tuple[int, int, int, int]:
            """Convert a polygon's bounding box to a clipped grid window.

            Args:
                bounds: GDAL envelope as (west, east, south, north).

            Returns:
                Inclusive (first_column, last_column, first_row, last_row).
            """
            xmin, xmax, ymin, ymax = bounds
            return (
                max(0, math.floor((xmin - west) / step)),
                min(width - 1, math.floor((xmax - west) / step)),
                max(0, math.floor((north - ymax) / step)),
                min(height - 1, math.floor((north - ymin) / step)),
            )

        for i in np.flatnonzero(selected & ~points):
            if not valid[i]:
                return fail(i, 5)
            length = int(lengths[i])
            if length <= 0 or length > np.iinfo(np.int32).max:
                return fail(i, 2)
            try:
                raw = ogr.CreateGeometryFromWkb(geometry[i].as_py())
            except RuntimeError:
                return fail(i, 2)
            if raw is None or raw.IsEmpty():
                return fail(i, 2)
            kind = ogr.GT_Flatten(raw.GetGeometryType())
            if kind not in (ogr.wkbPolygon, ogr.wkbMultiPolygon):
                status[i] = 3
                continue
            if not raw.IsValid():
                status[i] = 4
                continue
            bounds = raw.GetEnvelope()
            if not all(map(math.isfinite, bounds)):
                return fail(i, 6)
            status[i] = 1
            parsed.append((int(i), raw, kind, bounds))
        for i, raw, kind, bounds in parsed:
            x0, x1, y0, y1 = extent(bounds)
            if x0 > x1 or y0 > y1:
                continue
            spans_rows = y0 // tile != y1 // tile
            strips = {}
            if self.method == 'hybrid' and kind == ogr.wkbMultiPolygon:
                candidates = set()
                for part in range(raw.GetGeometryCount()):
                    component = raw.GetGeometryRef(part)
                    if component.IsEmpty():
                        continue
                    p, q, r, s = extent(component.GetEnvelope())
                    if p <= q and r <= s:
                        candidates.update(
                            (ty, tx)
                            for ty in range(r // tile, s // tile + 1)
                            for tx in range(p // tile, q // tile + 1)
                        )
                candidates = sorted(candidates)
            else:
                candidates = (
                    (ty, tx)
                    for ty in range(y0 // tile, y1 // tile + 1)
                    for tx in range(x0 // tile, x1 // tile + 1)
                )
            for ty, tx in candidates:
                view = i
                if self.method == 'hybrid' and spans_rows:
                    if ty not in strips:
                        wkb = strip_wkb(
                            raw,
                            north - ty * tile * step,
                            north - min(height, (ty + 1) * tile) * step,
                            step,
                            coordinates,
                            (i,),
                        )
                        strips[ty] = count + len(views) if wkb is not None else None
                        if wkb is not None:
                            views.append(wkb)
                    view = strips[ty]
                if view is not None:
                    tiles.setdefault((tx, ty), []).append(view)
        validated = time.perf_counter()
        self.timings['parse_validate_index_seconds'] += validated - started
        if views:
            geometry = pa.concat_arrays([geometry, pa.array(views, type=geometry.type)])
        srs = raster.GetSpatialRef()
        for (tx, ty), indices in tiles.items():
            x, y = tx * tile, ty * tile
            w, h = min(tile, width - x), min(tile, height - y)
            values = raster.GetRasterBand(1).ReadAsArray(
                x, y, w, h, buf_type=gdal.GDT_Byte
            )
            target = gdal_array.OpenArray(values)
            if target is None or target.SetGeoTransform(
                (west + x * step, step, 0, north - y * step, 0, -step)
            ):
                raise ValueError('GDAL tile transform failed')
            if srs is not None:
                target.SetSpatialRef(srs)
            dataset, layer = geometry_io.geometry_layer(
                pc.take(geometry, pa.array(indices, type=pa.int64())), srs
            )
            if gdal.RasterizeLayer(target, [1], layer, burn_values=[1]):
                raise ValueError('GDAL water geometry rasterization failed')
            layer = None
            dataset = None
            target.FlushCache()
            target = None
            raster.GetRasterBand(1).WriteArray(values, x, y)
        self.timings['tile_burn_seconds'] += time.perf_counter() - validated
        return status, None
