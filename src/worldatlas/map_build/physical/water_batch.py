"""Batch exact tile-local water burns using GDAL's supported Python bindings.

Arrow batches populate tile layers without a Python Feature per polygon, while
gdal_array.OpenArray shares the existing NumPy tile with the rasterizer.
"""

import hashlib
import math
import struct
import time
from collections.abc import Iterable
from enum import IntEnum
from pathlib import Path
from typing import cast

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
from osgeo import gdal, gdal_array, ogr

import worldatlas.geodesy.ogr as geometry_io
from worldatlas.map_build.core.grid import Grid


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


class GeometryStatus(IntEnum):
    """Outcome of checking one selected source geometry."""

    SKIPPED = 0
    POLYGON = 1
    MALFORMED = 2
    NON_POLYGON = 3
    INVALID_POLYGON = 4
    MISSING = 5
    NONFINITE = 6


type ParsedPolygon = tuple[int, ogr.Geometry, int, tuple[float, float, float, float]]
type TileGeometryRows = dict[tuple[int, int], list[int]]


def _read_polygons(
    geometry: pa.Array, selected: np.ndarray
) -> tuple[list[ParsedPolygon], np.ndarray, int | None]:
    """Read the polygons in one batch and record each row's status.

    Args:
        geometry: Arrow binary array of WKB shapes.
        selected: Boolean array indicating which rows passed the subtype check.

    Returns:
        A list of (row index, shape, GDAL geometry type, extent), an array of
        uint8 status codes, and the index of the first fatal error or None.
        Extents are in (west, south, east, north) order, in degrees. A fatal
        error returns an empty polygon list and marks later rows as skipped.
    """
    valid_bits, byte_offsets, geometry_bytes = geometry.buffers()
    count = len(geometry)
    status = np.zeros(count, dtype=np.uint8)
    offsets = np.frombuffer(
        byte_offsets,
        dtype=np.int64 if pa.types.is_large_binary(geometry.type) else np.int32,
    )
    # An Arrow slice shares its buffers with the original array.
    start, end = geometry.offset, geometry.offset + count
    starts = offsets[start:end]
    lengths = offsets[start + 1 : end + 1] - starts
    data = (
        np.frombuffer(geometry_bytes, dtype=np.uint8)
        if geometry_bytes is not None
        else np.empty(0, dtype=np.uint8)
    )
    selected = np.asarray(selected, dtype=np.bool_)
    has_geometry = np.ones(count, dtype=np.bool_)
    if valid_bits is not None:
        bits = np.frombuffer(valid_bits, dtype=np.uint8)
        positions = np.arange(start, end)
        has_geometry = (bits[positions // 8] & (1 << (positions % 8))) != 0

    # A finite point needs no GDAL object because it cannot fill an area.
    points = finite_points(data, starts, lengths, selected & has_geometry)
    status[points] = GeometryStatus.NON_POLYGON
    polygons: list[ParsedPolygon] = []
    max_wkb_size = np.iinfo(np.int32).max
    for index in np.flatnonzero(selected & ~points):
        if not has_geometry[index]:
            failure = GeometryStatus.MISSING
            break
        if not 0 < lengths[index] <= max_wkb_size:
            failure = GeometryStatus.MALFORMED
            break
        try:
            shape = ogr.CreateGeometryFromWkb(geometry[index].as_py())
        except RuntimeError:
            failure = GeometryStatus.MALFORMED
            break
        if shape is None or shape.IsEmpty():
            failure = GeometryStatus.MALFORMED
            break
        kind = ogr.GT_Flatten(shape.GetGeometryType())
        if kind not in (ogr.wkbPolygon, ogr.wkbMultiPolygon):
            status[index] = GeometryStatus.NON_POLYGON
            continue
        if not shape.IsValid():
            status[index] = GeometryStatus.INVALID_POLYGON
            continue
        west, east, south, north = shape.GetEnvelope()
        extent = (west, south, east, north)
        if not all(map(math.isfinite, extent)):
            failure = GeometryStatus.NONFINITE
            break
        status[index] = GeometryStatus.POLYGON
        polygons.append((int(index), shape, kind, extent))
    else:
        return polygons, status, None

    # The point scan ran in advance. Clear any results beyond the first failure.
    status[index] = failure
    status[index + 1 :] = GeometryStatus.SKIPPED
    return [], status, int(index)


def _index_water_tiles(
    geometry: pa.Array, polygons: list[ParsedPolygon], grid: Grid, tile: int
) -> tuple[pa.Array, TileGeometryRows]:
    """List the geometry rows to draw for each tile.

    Args:
        geometry: Arrow binary array of the original WKB shapes.
        polygons: Valid polygon rows, in source order.
        grid: Shared physical build grid.
        tile: Tile width and height in cells before clipping to the grid.

    Returns:
        An Arrow array with reduced shapes appended, and a mapping from
        (tile column, tile row) to indices into that array.
        For example, if there are three original rows, the first reduced
        shape is at row index 3.
    """
    tiles: TileGeometryRows = {}
    strip_shapes = []
    for index, shape, kind, extent in polygons:
        window = grid.window_for_extent(extent)
        if window is None:
            continue
        first_column, end_column, first_row, end_row = window
        first_tile_row = first_row // tile
        last_tile_row = (end_row - 1) // tile
        candidate_tiles: Iterable[tuple[int, int]]
        if kind == ogr.wkbMultiPolygon:
            # Index each piece separately so gaps between pieces add no tiles.
            part_tiles = set()
            for part in range(shape.GetGeometryCount()):
                component = cast(ogr.Geometry, shape.GetGeometryRef(part))
                if component.IsEmpty():
                    continue
                west, east, south, north = component.GetEnvelope()
                part_window = grid.window_for_extent((west, south, east, north))
                if part_window is not None:
                    left, right, top, bottom = part_window
                    part_tiles.update(
                        (tile_row, tile_column)
                        for tile_row in range(top // tile, (bottom - 1) // tile + 1)
                        for tile_column in range(left // tile, (right - 1) // tile + 1)
                    )
            candidate_tiles = sorted(part_tiles)
        else:
            candidate_tiles = (
                (tile_row, tile_column)
                for tile_row in range(first_tile_row, last_tile_row + 1)
                for tile_column in range(
                    first_column // tile, (end_column - 1) // tile + 1
                )
            )

        # Tiles in the same row share one reduced shape for this polygon.
        strip_indices: dict[int, int | None] = {}
        ring_coordinates = {}
        for tile_row, tile_column in candidate_tiles:
            geometry_row: int | None = index
            if first_tile_row != last_tile_row:
                if tile_row not in strip_indices:
                    wkb = strip_wkb(
                        shape,
                        grid.north - tile_row * tile * grid.step,
                        grid.north
                        - min(grid.height, (tile_row + 1) * tile) * grid.step,
                        grid.step,
                        ring_coordinates,
                        (),
                    )
                    strip_indices[tile_row] = (
                        len(geometry) + len(strip_shapes) if wkb is not None else None
                    )
                    if wkb is not None:
                        strip_shapes.append(wkb)
                geometry_row = strip_indices[tile_row]
            if geometry_row is not None:
                tiles.setdefault((tile_column, tile_row), []).append(geometry_row)
    if strip_shapes:
        geometry = pa.concat_arrays(
            [geometry, pa.array(strip_shapes, type=geometry.type)]
        )
    return geometry, tiles


def _draw_water_tiles(
    raster: gdal.Dataset,
    geometry: pa.Array,
    tiles: TileGeometryRows,
    grid: Grid,
    tile: int,
) -> None:
    """Draw each tile's polygons over the water already present in that tile.

    Args:
        raster: Target water mask updated in place.
        geometry: Arrow binary array of shapes referenced by the tiles.
        tiles: Tile coordinates mapped to rows in the geometry array.
        grid: Shared physical build grid.
        tile: Tile width and height in cells before clipping to the grid.

    Raises:
        ValueError: GDAL cannot position or draw a tile.
    """
    srs = raster.GetSpatialRef()
    band = raster.GetRasterBand(1)
    for (tile_column, tile_row), indices in tiles.items():
        x, y = tile_column * tile, tile_row * tile
        width = min(tile, grid.width - x)
        height = min(tile, grid.height - y)
        values = band.ReadAsArray(x, y, width, height, buf_type=gdal.GDT_Byte)
        target = gdal_array.OpenArray(values)
        if target is None or target.SetGeoTransform(
            (
                grid.west + x * grid.step,
                grid.step,
                0,
                grid.north - y * grid.step,
                0,
                -grid.step,
            )
        ):
            raise ValueError('GDAL tile transform failed')
        if srs is not None:
            target.SetSpatialRef(srs)
        dataset, layer = geometry_io.geometry_layer(
            pc.take(geometry, pa.array(indices, type=pa.int64())), srs
        )
        # The dataset owns the temporary layer while GDAL draws it.
        with dataset:
            if gdal.RasterizeLayer(target, [1], layer, burn_values=[1]):
                raise ValueError('GDAL water geometry rasterization failed')
        target.FlushCache()
        band.WriteArray(values, x, y)


class WaterBatch:
    """Mark water from Arrow geometry batches using GDAL and NumPy tiles."""

    def __init__(self) -> None:
        """Prepare the batch rasterizer and its timing counters."""
        self.provenance = {
            'implementation': 'python-gdal-api-v2',
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
        grid: Grid,
        tile: int,
    ) -> tuple[np.ndarray, int | None]:
        """Mark selected polygon cells in the output raster.

        Args:
            raster: Target raster updated in place.
            geometry: Arrow column of WKB geometry byte strings.
            selected: Boolean array indicating which rows to inspect.
            grid: Shared physical build grid.
            tile: Tile width and height in cells before clipping to the grid.

        Returns:
            (status, failed_row), with a uint8 status per source row. If a
            geometry cannot be read, failed_row is its index and no tiles are
            drawn. None means the whole batch was processed.

        Raises:
            ValueError: The Arrow column has the wrong type or GDAL fails to draw.
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
        polygons, status, failed_row = _read_polygons(geometry, selected)
        if failed_row is not None:
            return status, failed_row
        geometry, tiles = _index_water_tiles(geometry, polygons, grid, tile)
        del polygons
        ready_to_draw = time.perf_counter()
        self.timings['parse_validate_index_seconds'] += ready_to_draw - started
        _draw_water_tiles(raster, geometry, tiles, grid, tile)
        self.timings['tile_burn_seconds'] += time.perf_counter() - ready_to_draw
        return status, None
