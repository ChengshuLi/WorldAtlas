"""Shared WGS84 nearest-shore calculations for physical water and final land.

Distances are measured in metres between cell centers and physical coastal
land-cell centers. Each participant is indexed independently. Missing shores
or an insufficient crop are reported instead of assuming a distance.
"""

from __future__ import annotations
import math
import numpy as np
from scipy.spatial import cKDTree
from worldatlas.geodesy.wgs84 import GEOD, MIN_RADIUS


def unit(lat, lon):
    lat = np.deg2rad(lat)
    lon = np.deg2rad(lon)
    c = np.cos(lat)
    return np.column_stack((c * np.cos(lon), c * np.sin(lon), np.sin(lat)))


def geodesic_distances(lon, lat, target_lon, target_lat):
    lon, lat, target_lon, target_lat = np.broadcast_arrays(
        *[np.asarray(v, dtype=np.float64) for v in (lon, lat, target_lon, target_lat)]
    )
    if lon.ndim != 1:
        raise ValueError("distance inputs must be one-dimensional")
    if not len(lon):
        return np.empty(0, dtype=np.float64)
    if len(lon) == 1:
        return np.asarray(
            [
                GEOD.inv(
                    float(lon[0]),
                    float(lat[0]),
                    float(target_lon[0]),
                    float(target_lat[0]),
                )[2]
            ]
        )
    return np.asarray(GEOD.inv(lon, lat, target_lon, target_lat)[2], dtype=np.float64)


def crop(rows, runs, y, x0, x1, width):
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


def boundary_lower(lat, lon, bounds, width, height, step):
    """Conservative distance to any shoreline omitted outside the crop."""
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


def make_indexes(centers, pairs):
    indexes = {}
    for _, land_code, _ in pairs:
        mask = centers["category"] == land_code
        if not np.any(mask):
            raise ValueError(
                f"crop has no shoreline for participant land code {land_code}"
            )
        part = {k: centers[k][mask] for k in ("mids", "lat", "lon", "category")}
        # Actual points from occupied degree tiles provide inexpensive upper
        # witnesses. They narrow searches, never replace the complete tree.
        tiles = np.floor(part["lat"] + 90).astype(np.int64) * 360 + np.floor(
            (part["lon"] + 180) % 360
        ).astype(np.int64)
        _, selected = np.unique(tiles, return_index=True)
        part["witness_ids"] = selected
        part["witness_tree"] = cKDTree(part["mids"][selected])
        indexes[land_code] = (part, cKDTree(part["mids"]))
    return indexes


def nearest_class_bounds(lat, lon, points, pairs, indexes, *, upper_limit=None):
    """Lower bounds for all classes, one exact candidate upper bound per query.

    The spherical-nearest class need not win on WGS84. It is only a candidate:
    callers must prove its exact upper bound beats every competing lower bound
    or fall back to complete exact minima. No inverse call is needed for a
    competing class that has already been excluded by its lower bound.
    """
    count = len(points)
    lower = np.empty((count, len(pairs)), dtype=np.float64)
    targets_lon = np.empty_like(lower)
    targets_lat = np.empty_like(lower)
    query_options = {}
    search_limit = None
    if upper_limit is None and count:
        # Without a cutoff, an unbounded query against a distant class can
        # traverse much of its tree. First obtain any real WGS84 upper witness;
        # no class farther than that witness can win. A generous shared bound
        # lets scipy perform the batch query without per-point Python calls.
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


def scan_exact_minimum(point, lon, lat, data, best):
    """Finish a wide search in blocks using its already measured upper bound."""
    for first in range(0, len(data["mids"]), 4096):
        last = first + 4096
        # MIN_RADIUS times the central angle is a distance lower bound. Express
        # the upper witness as a unit-sphere chord so each block needs only
        # squared distances. The margins expand the search, never decide a tie.
        angle = min(math.pi, (best + 0.01) / MIN_RADIUS)
        chord = 2 * math.sin(angle / 2) + 1e-12
        delta = data["mids"][first:last] - point
        keep = np.flatnonzero(np.einsum("ij,ij->i", delta, delta) <= chord * chord)
        if len(keep):
            indices = keep + first
            distances = geodesic_distances(
                np.full(len(keep), lon),
                np.full(len(keep), lat),
                data["lon"][indices],
                data["lat"][indices],
            )
            if np.any(~np.isfinite(distances)):
                raise ValueError("invalid inverse geodesic")
            best = min(best, float(distances.min()))
    return best


def exact_minima_by_ordered_chord(points, lon, lat, data, tree):
    """Batch exact WGS84 minima, proving that every omitted center is farther.

    Neighbor prefixes grow only for queries whose conservative lower bound
    cannot prove the minimum. Wide unresolved searches still visit the entire
    shore in ordinary blocks, using the best distance already measured.
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
                    points[q], lon[q], lat[q], data, result[q]
                )
            break
        take = min(n, take * 2)
    return result


def classify_wgs84(lat, lon, bounds, width, height, step, pairs, indexes, *, band=None):
    """Certify WGS84 nearest coastal-cell-center assignments or fail closed.

    Spherical unit vectors only narrow the search using a conservative WGS84
    lower bound. All returned classifications use ellipsoidal distances.
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
    if abs(step * width - 360) > 1e-8:
        raise ValueError("step does not match world width")
    if not len(lat):
        return np.empty(0, dtype=np.uint32), {"bounded": 0, "exact": 0}
    # An omitted-shore proof is valid only for points inside the indexed crop.
    y = (90 - lat) / step
    x = (lon + 180) / step
    x = x + np.ceil((x0 - x) / width) * width
    if (
        np.any(y < y0 - 1e-8)
        or np.any(y > y1 + 1e-8)
        or np.any(x < x0 - 1e-8)
        or np.any(x > x1 + 1e-8)
    ):
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
        fast = unique
    else:
        threshold = band
        outside = (lows.min(axis=1) > threshold) & (boundary > threshold)
        inside = unique & (upper <= threshold)
        fast = outside | inside
    for i, (_, _, code) in enumerate(available):
        out[fast & (best == i) & (True if band is None else inside)] = code
    pending = np.flatnonzero(~fast)
    if len(pending):
        # Conservative lower bounds exclude classes that cannot beat the
        # candidate. Retain its class so exact distances decide the threshold.
        limit = upper[pending] + 0.000001
        if band is not None:
            limit = np.minimum(limit, threshold + 0.000001)
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
            inside = minimum <= threshold
            if np.any(~inside & (boundary[pending] <= threshold)):
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


def classify(lat, lon, bounds, width, height, step, pairs, indexes):
    out, stats = classify_wgs84(lat, lon, bounds, width, height, step, pairs, indexes)
    return out, stats["bounded"], stats["exact"]
