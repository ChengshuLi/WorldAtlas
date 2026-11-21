"""Conservative grid envelopes for all polygon pieces across longitude wrapping."""

import math
from collections.abc import Iterator
from typing import Any


def _pairs(x: object) -> Iterator[tuple[float, float]]:
    """Read all coordinate pairs in a nested GeoJSON array.

    Args:
        x: Coordinate pair, ring, or collection of rings.

    Yields:
        (longitude, latitude) in degrees.

    Raises:
        ValueError: A coordinate is malformed or out of range.
    """
    if (
        isinstance(x, (list, tuple))
        and len(x) >= 2
        and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in x[:2])
    ):
        lon, lat = map(float, x[:2])
        if not (
            math.isfinite(lon)
            and math.isfinite(lat)
            and -180 <= lon <= 180
            and -90 <= lat <= 90
        ):
            raise ValueError('invalid coordinates')
        yield lon, lat
    elif isinstance(x, (list, tuple)):
        for a in x:
            yield from _pairs(a)
    else:
        raise ValueError('invalid coordinates')


def wrapped_grid_bounds(
    feature: dict[str, Any], width: int, height: int, step: float
) -> tuple[tuple[int, int, int, int], tuple[tuple[int, int], ...]]:
    """Find the smallest grid window that encloses all polygon pieces.

    Args:
        feature: GeoJSON Polygon, MultiPolygon, or Feature holding either, in
            WGS84.
        width: Number of columns in the full grid.
        height: Number of rows retained from the north.
        step: Cell width and height in degrees.

    Returns:
        (bounds, windows). Bounds are (first_column, end_column, first_row,
        end_row) and can extend past the last column. Windows hold one or two
        (first_column, end_column) pairs within the grid. Ends are exclusive.
        A polygon south of the grid has an empty row interval.

    Raises:
        ValueError: The grid, geometry, or resulting window is invalid.
    """
    if (
        type(width) is not int
        or type(height) is not int
        or width <= 0
        or height <= 0
        or not math.isfinite(step)
        or step <= 0
        or step != 360 / width
    ):
        raise ValueError('invalid grid')
    g = feature.get('geometry', feature)
    typ = g.get('type')
    coords = g.get('coordinates')
    if typ == 'Polygon':
        polys = [coords]
    elif typ == 'MultiPolygon':
        polys = coords
    else:
        raise ValueError('expected Polygon or MultiPolygon')
    if not isinstance(polys, (tuple, list)) or not polys:
        raise ValueError('empty geometry')
    spans = []
    minlat = 90.0
    maxlat = -90.0
    for poly in polys:
        p = list(_pairs(poly))
        if not p:
            raise ValueError('empty polygon')
        spans.append((min(z[0] for z in p) + 180.0, max(z[0] for z in p) + 180.0))
        minlat = min(minlat, min(z[1] for z in p))
        maxlat = max(maxlat, max(z[1] for z in p))
    spans.sort()
    merged = []
    for a, b in spans:
        if not merged or a > merged[-1][1]:
            merged.append([a, b])
        else:
            merged[-1][1] = max(merged[-1][1], b)
    gaps = []
    for i, (_, b) in enumerate(merged):
        a2 = merged[(i + 1) % len(merged)][0] + (360.0 if i == len(merged) - 1 else 0.0)
        gaps.append((a2 - b, i))
    gap, i = max(gaps, key=lambda z: (z[0], -z[1]))
    if gap <= 0:
        x0, x1 = 0, width
    else:
        start = merged[(i + 1) % len(merged)][0]
        end = merged[i][1]
        if end < start:
            end += 360.0
        x0 = max(0, min(width - 1, math.floor(start / step)))
        x1 = math.ceil(end / step)
        if x1 - x0 >= width:
            x0, x1 = 0, width
    y0 = min(height, max(0, math.floor((90 - maxlat) / step)))
    y1 = min(height, math.ceil((90 - minlat) / step))
    if not 0 < x1 - x0 <= width or not 0 <= y0 <= y1 <= height:
        raise ValueError('invalid polygon grid bounds')
    windows = [(x0, x1)] if x1 <= width else [(0, x1 - width), (x0, width)]
    return (x0, x1, y0, y1), tuple(windows)
