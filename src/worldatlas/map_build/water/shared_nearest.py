"""Shared WGS84 nearest-shore calculations for physical water and final land.

Distances are measured in metres between cell centers and physical coastal
land-cell centers. Each participant is indexed independently. Missing shores
or an insufficient crop are reported instead of assuming a distance.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any, cast

import numpy as np
from numpy.typing import ArrayLike

# SciPy publishes the compiled tree without type information.
from scipy.spatial import cKDTree  # pyright: ignore[reportAttributeAccessIssue]

from worldatlas.geodesy.wgs84 import MIN_RADIUS, geodesic_distances

# Shore code maps to prepared coordinates and the corresponding search tree.
type ShoreIndexes = dict[int, tuple[dict[str, Any], cKDTree]]


def unit(lat: ArrayLike, lon: ArrayLike) -> np.ndarray:
    """Convert paired geographic coordinates to points on a unit sphere.

    Args:
        lat: Latitudes in degrees.
        lon: Longitudes in degrees.

    Returns:
        N-by-3 float array of Cartesian coordinates.
    """
    lat = np.deg2rad(lat)
    lon = np.deg2rad(lon)
    c = np.cos(lat)
    return np.column_stack((c * np.cos(lon), c * np.sin(lon), np.sin(lat)))


def crop(
    rows: np.ndarray, runs: np.ndarray, y: int, x0: int, x1: int, width: int
) -> np.ndarray:
    """Expand part of one row-run row to a code per cell.

    Args:
        rows: Row offsets into the run array.
        runs: Flattened (end_column, code) pairs.
        y: Row to read.
        x0: First unwrapped column.
        x1: Exclusive end column. It may cross the longitude seam.
        width: Number of columns in the full grid.

    Returns:
        A uint32 array with x1 - x0 codes in column order.

    Raises:
        ValueError: The window or row-run records are invalid.
    """
    if not (0 <= y < len(rows) - 1 and 0 < x1 - x0 <= width):
        raise ValueError("invalid crop")
    first, last = int(rows[y]), int(rows[y + 1])
    ends = runs[2 * first : 2 * last : 2]
    vals = runs[2 * first + 1 : 2 * last : 2]
    if (
        not len(ends)
        or int(ends[0]) <= 0
        or int(ends[-1]) != width
        or np.any(ends[1:] <= ends[:-1])
    ):
        raise ValueError(f"invalid RLE row {y}")
    if x0 == 0 and x1 == width:
        lengths = np.diff(np.concatenate((np.array([0], dtype=ends.dtype), ends)))
        return np.repeat(vals, lengths).astype(np.uint32, copy=False)
    result = np.empty(x1 - x0, dtype=np.uint32)
    cur = 0
    x = x0
    while x < x1:
        xm = x % width
        take = min(x1 - x, width - xm)
        stop = xm + take
        i = int(np.searchsorted(ends, xm, side="right"))
        j = int(np.searchsorted(ends, stop, side="left")) + 1
        clipped = np.minimum(ends[i:j], stop).astype(np.int64)
        lengths = np.diff(np.r_[xm, clipped])
        result[cur : cur + take] = np.repeat(vals[i:j], lengths)
        cur += take
        x += take
    return result


def boundary_lower(
    lat: np.ndarray,
    lon: np.ndarray,
    bounds: tuple[int, int, int, int],
    width: int,
    height: int,
    step: float,
) -> np.ndarray:
    """Bound the distance to any shore outside the current crop.

    Args:
        lat: Query latitudes in degrees.
        lon: Matching query longitudes in degrees.
        bounds: Crop as (first_column, end_column, first_row, end_row).
        width: Number of grid columns.
        height: Number of grid rows.
        step: Cell size in degrees.

    Returns:
        One conservative lower bound per query, in metres. A full-grid
        crop has no omitted shores and gives infinity.
    """
    x0, x1, y0, y1 = bounds
    latr = np.deg2rad(lat)
    lonr = np.deg2rad(lon)
    d = np.full(len(lat), np.inf, dtype=np.float64)
    if y0 > 0:
        d = np.minimum(d, np.abs(lat - (90 - y0 * step)) * math.pi / 180 * MIN_RADIUS)
    if y1 < height:
        d = np.minimum(d, np.abs(lat - (90 - y1 * step)) * math.pi / 180 * MIN_RADIUS)
    if x1 - x0 < width:
        for edge in (x0, x1):
            lam = math.radians(-180 + edge * step)
            d = np.minimum(
                d,
                MIN_RADIUS
                * np.arcsin(np.clip(np.abs(np.cos(latr) * np.sin(lonr - lam)), 0, 1)),
            )
    return np.maximum(0.0, d - 0.001)


def make_indexes(
    centers: dict[str, np.ndarray], pairs: Sequence[tuple[int, int, int]]
) -> ShoreIndexes:
    """Index the full list of shore cells for each participating owner.

    Args:
        centers: Matching latitude, longitude, category, and unit-sphere arrays.
        pairs: Category tuples whose second field selects the shore code.

    Returns:
        Shore code mapped to (shore_data, tree). The data includes a small
        sample index for finding a nearby starting point quickly.

    Raises:
        ValueError: A participating category has no shore in the crop.
    """
    indexes = {}
    for _, land_code, _ in pairs:
        mask = centers["category"] == land_code
        if not np.any(mask):
            raise ValueError(
                f"crop has no shoreline for participant land code {land_code}"
            )
        part = {k: centers[k][mask] for k in ("mids", "lat", "lon", "category")}
        # Keep one real shore cell per occupied degree tile. A measured
        # distance to any real cell gives a safe starting limit for the search.
        tiles = np.floor(part["lat"] + 90).astype(np.int64) * 360 + np.floor(
            (part["lon"] + 180) % 360
        ).astype(np.int64)
        _, selected = np.unique(tiles, return_index=True)
        part["witness_ids"] = selected
        part["witness_tree"] = cKDTree(part["mids"][selected])
        indexes[land_code] = (part, cKDTree(part["mids"]))
    return indexes


def nearest_class_bounds(
    lat: np.ndarray,
    lon: np.ndarray,
    points: np.ndarray,
    pairs: Sequence[tuple[int, int, int]],
    indexes: ShoreIndexes,
    *,
    upper_limit: float | np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Bound the shortest distances from queries to each category.

    The nearest on the sphere supplies a candidate. The WGS84 distance
    decides which category wins when the bounds cannot separate them.

    Args:
        lat: Query latitudes in degrees.
        lon: Matching longitudes in degrees.
        points: N-by-3 unit-sphere query points.
        pairs: Category tuples in search order.
        indexes: Complete indexes by shore code.
        upper_limit: Optional distance cutoff in metres.

    Returns:
        (lower, best, upper). Lower is an N-by-category array of bounds
        in metres. Best and upper give the candidate category column and
        its measured upper bound for each query.
    """
    count = len(points)
    lower = np.empty((count, len(pairs)), dtype=np.float64)
    targets_lon = np.empty_like(lower)
    targets_lat = np.empty_like(lower)
    query_options = {}
    search_limit = None
    if upper_limit is None and count:
        # A search with no distance limit can scan a distant shore needlessly.
        # Find a real candidate for each point first, then use the largest
        # measured distance as a shared limit for the whole batch.
        witness_upper = np.full(count, np.inf)
        for _, code, _ in pairs:
            data, _ = indexes[code]
            if "witness_tree" in data:
                _, ids = data["witness_tree"].query(points, k=1, workers=1)
                ids = data["witness_ids"][ids]
            else:
                ids = np.zeros(count, dtype=np.int64)
            distance = geodesic_distances(lon, lat, data["lon"][ids], data["lat"][ids])
            witness_upper = np.minimum(witness_upper, distance + 0.000001)
        upper_limit = witness_upper
    if upper_limit is not None and count:
        # A coastal-band query need not find a shore on a distant continent.
        # Expand the query's exact-distance threshold using the same global
        # ellipsoid lower bound as the certificates. Missing neighbors then
        # have a finite proven lower bound, rather than being treated as absent.
        search_limit = float(np.max(upper_limit)) + 0.01
        if search_limit + 0.001 < math.pi * MIN_RADIUS:
            chord_limit = 2 * math.sin((search_limit + 0.001) / (2 * MIN_RADIUS))
            query_options["distance_upper_bound"] = np.nextafter(chord_limit, np.inf)
    for col, (_, code, _) in enumerate(pairs):
        data, tree = indexes[code]
        chord, ix = tree.query(points, k=1, workers=1, **query_options)
        found = np.isfinite(chord)
        angle = 2 * np.arcsin(np.clip(chord / 2, 0, 1))
        # Chord itself stays a conservative angular bound near antipodes,
        # where asin amplifies floating-point error.
        lower[:, col] = np.maximum(
            0, MIN_RADIUS * np.where(chord < 1.99, angle, chord) - 0.001
        )
        if search_limit is not None:
            lower[~found, col] = search_limit
        targets_lon[:, col] = 0
        targets_lat[:, col] = 0
        targets_lon[found, col] = data["lon"][ix[found]]
        targets_lat[found, col] = data["lat"][ix[found]]
    best = np.argmin(lower, axis=1)
    rows = np.arange(count)
    active = (
        np.ones(count, dtype=bool)
        if upper_limit is None
        else lower[rows, best] <= upper_limit
    )
    upper = np.full(count, np.inf)
    if np.any(active):
        d = geodesic_distances(
            lon[active],
            lat[active],
            targets_lon[rows[active], best[active]],
            targets_lat[rows[active], best[active]],
        )
        if np.any(~np.isfinite(d)):
            raise ValueError("invalid inverse geodesic")
        upper[active] = d + 0.000001
    return lower, best, upper


def scan_exact_minimum(
    point: np.ndarray,
    lon: float | np.floating,
    lat: float | np.floating,
    data: dict[str, Any],
    best: float | np.floating,
) -> float:
    """Search one shore in blocks for a closer cell.

    Args:
        point: Query point on the unit sphere.
        lon: Query longitude in degrees.
        lat: Query latitude in degrees.
        data: Indexed shore coordinates.
        best: Already measured distance in metres.

    Returns:
        Smallest exact distance found, in metres.
    """
    for first in range(0, len(data["mids"]), 4096):
        last = first + 4096
        # Compare straight-line distances on the unit sphere to skip cells
        # that cannot beat the best WGS84 distance. The margins keep extra
        # candidates in the search. Exact distances decide the winner.
        angle = min(math.pi, (best + 0.01) / MIN_RADIUS)
        chord = 2 * math.sin(angle / 2) + 1e-12
        delta = data["mids"][first:last] - point
        keep = np.flatnonzero(np.einsum("ij,ij->i", delta, delta) <= chord * chord)
        if len(keep):
            indices = keep + first
            distances = geodesic_distances(
                lon,
                lat,
                data["lon"][indices],
                data["lat"][indices],
            )
            if np.any(~np.isfinite(distances)):
                raise ValueError("invalid inverse geodesic")
            best = min(best, float(distances.min()))
    return float(best)


def exact_minima_by_ordered_chord(
    points: np.ndarray,
    lon: np.ndarray,
    lat: np.ndarray,
    data: dict[str, Any],
    tree: cKDTree,
) -> np.ndarray:
    """Find the exact WGS84 distance to the same shore for many points.

    Try a few nearby cells first. Expand the search only when a farther
    cell could still be closer on WGS84.

    Args:
        points: N-by-3 unit-sphere points.
        lon: Query longitudes in degrees.
        lat: Query latitudes in degrees.
        data: Shore coordinates indexed by the tree.
        tree: Full shore cell index.

    Returns:
        Float array of minimum WGS84 distances in metres.
    """
    count = len(points)
    result = np.full(count, np.inf)
    n = int(tree.n)
    if not count or not n:
        return result
    active = np.arange(count)
    take = min(1, n)
    while len(active):
        request = min(n, take + 1)
        chords, ids = tree.query(points[active], k=request, workers=1)
        chords = np.asarray(chords).reshape(len(active), request)
        ids = np.asarray(ids).reshape(len(active), request)
        candidates = ids[:, :take].ravel()
        ds = geodesic_distances(
            np.repeat(lon[active], take),
            np.repeat(lat[active], take),
            data["lon"][candidates],
            data["lat"][candidates],
        )
        if np.any(~np.isfinite(ds)):
            raise ValueError("invalid inverse geodesic")
        result[active] = np.minimum(result[active], ds.reshape(-1, take).min(axis=1))
        if take == n:
            break
        angle = 2 * np.arcsin(np.clip(chords[:, take] / 2, 0, 1))
        next_chord = chords[:, take]
        lower = np.maximum(
            0, MIN_RADIUS * np.where(next_chord < 1.99, angle, next_chord) - 0.001
        )
        active = active[lower <= result[active] + 0.000001]
        if take >= 4096:
            for q in active:
                result[q] = scan_exact_minimum(
                    points[q],
                    cast(float, lon[q]),
                    cast(float, lat[q]),
                    data,
                    cast(float, result[q]),
                )
            break
        take = min(n, take * 2)
    return result


def classify_wgs84(
    lat: np.ndarray,
    lon: np.ndarray,
    bounds: tuple[int, int, int, int],
    width: int,
    height: int,
    step: float,
    pairs: Sequence[tuple[int, int, int]],
    indexes: ShoreIndexes,
    *,
    band: float | None = None,
) -> tuple[np.ndarray, dict[str, int]]:
    """Find the nearest participating shore for each query cell centre.

    Args:
        lat: Query latitudes in degrees.
        lon: Query longitudes in degrees.
        bounds: Window covered by these shore indexes.
        width: Number of grid columns.
        height: Number of grid rows.
        step: Cell size in degrees.
        pairs: (category, shore_code, output_code) records in tie order.
        indexes: Shore indexes by code.
        band: Optional distance limit in metres.

    Returns:
        (output_codes, counts). Codes are uint32, with zero beyond the
        distance limit. Counts distinguish bounded and exact queries.

    Raises:
        ValueError: The inputs are invalid or a shore outside the crop
            might change an assignment.
    """
    lat = np.asarray(lat, dtype=np.float64)
    lon = np.asarray(lon, dtype=np.float64)
    if (
        lat.ndim != 1
        or lon.shape != lat.shape
        or np.any(~np.isfinite(lat))
        or np.any(~np.isfinite(lon))
        or np.any(np.abs(lat) > 90)
        or np.any(np.abs(lon) > 180)
    ):
        raise ValueError("invalid query coordinates")
    if band is not None and (
        isinstance(band, bool) or not math.isfinite(band) or band < 0
    ):
        raise ValueError("invalid coastal distance limit")
    x0, x1, y0, y1 = bounds
    if any(type(z) is not int for z in (x0, x1, y0, y1, width, height)) or not (
        0 < width
        and 0 < height
        and 0 < x1 - x0 <= width
        and 0 <= y0 < y1 <= height
        and math.isfinite(step)
        and step > 0
    ):
        raise ValueError("invalid crop or grid")
    if step != 360 / width:
        raise ValueError("step does not match world width")
    if not len(lat):
        return np.empty(0, dtype=np.uint32), {"bounded": 0, "exact": 0}
    # An omitted-shore proof is valid only for points inside the indexed crop.
    y = (90 - lat) / step
    x = (lon + 180) / step
    x = x + np.ceil((x0 - x) / width) * width
    if np.any(y < y0) or np.any(y > y1) or np.any(x < x0) or np.any(x > x1):
        raise ValueError("query lies outside crop")
    points = unit(lat, lon)
    boundary = boundary_lower(lat, lon, bounds, width, height, step)
    available = [p for p in pairs if p[1] in indexes]
    if band is None and len(available) != len(pairs):
        raise ValueError("missing participant shore")
    if not available:
        if band is None or np.any(boundary <= band):
            raise ValueError("crop cannot certify; increase halo")
        return np.zeros(len(lat), dtype=np.uint32), {"bounded": len(lat), "exact": 0}
    lows, best, upper = nearest_class_bounds(
        lat, lon, points, available, indexes, upper_limit=None if band is None else band
    )
    others = lows.copy()
    others[np.arange(len(lat)), best] = np.inf
    unique = (upper < others.min(axis=1)) & (upper < boundary)
    out = np.zeros(len(lat), dtype=np.uint32)
    if band is None:
        inside = unique
        fast = unique
    else:
        outside = (lows.min(axis=1) > band) & (boundary > band)
        inside = unique & (upper <= band)
        fast = outside | inside
    for i, (_, _, code) in enumerate(available):
        out[inside & (best == i)] = code
    pending = np.flatnonzero(~fast)
    if len(pending):
        # Conservative lower bounds exclude classes that cannot beat the
        # candidate. Retain its class so exact distances decide the threshold.
        limit = upper[pending] + 0.000001
        if band is not None:
            limit = np.minimum(limit, band + 0.000001)
        distances = np.full((len(pending), len(available)), np.inf)
        for col, (_, lc, _) in enumerate(available):
            relevant = (lows[pending, col] <= limit) | (best[pending] == col)
            queries = pending[relevant]
            if len(queries):
                distances[relevant, col] = exact_minima_by_ordered_chord(
                    points[queries], lon[queries], lat[queries], *indexes[lc]
                )
        minimum = distances.min(axis=1)
        if np.any(~np.isfinite(minimum)):
            raise RuntimeError("no provable candidate shore")
        inside = np.ones(len(pending), dtype=bool)
        if band is not None:
            inside = minimum <= band
            if np.any(~inside & (boundary[pending] <= band)):
                raise ValueError("crop cannot certify coastal band; increase halo")
        if np.any(inside & (minimum + 0.000001 >= boundary[pending])):
            raise ValueError("crop cannot certify nearest shore; increase halo")
        candidates = distances[inside]
        # Strict minimum wins; argmin chooses the first supplied class only
        # when computed distances are exactly equal.
        winners = np.argmin(candidates, axis=1)
        codes = np.asarray([p[2] for p in available], dtype=np.uint32)
        out[pending[inside]] = codes[winners]
    return out, {"bounded": int(fast.sum()), "exact": int(len(pending))}


def classify(
    lat: np.ndarray,
    lon: np.ndarray,
    bounds: tuple[int, int, int, int],
    width: int,
    height: int,
    step: float,
    pairs: Sequence[tuple[int, int, int]],
    indexes: ShoreIndexes,
) -> tuple[np.ndarray, int, int]:
    """Classify query cells with unrestricted distance to participating shores.

    Args:
        lat: Latitudes in degrees.
        lon: Matching longitudes in degrees.
        bounds: Grid window covered by the indexes.
        width: Number of grid columns.
        height: Number of grid rows.
        step: Cell size in degrees.
        pairs: Category tuples in tie order.
        indexes: Complete indexes by shore code.

    Returns:
        (output_codes, bounded_count, exact_count).
    """
    out, stats = classify_wgs84(lat, lon, bounds, width, height, step, pairs, indexes)
    return out, stats["bounded"], stats["exact"]
