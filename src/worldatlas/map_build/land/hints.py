"""Find WGS84 representative hints; complete certificates/search make the decisions."""

import math
import numpy as np
from worldatlas.map_build.core.geodesy import GEOD, MIN_RADIUS as MIN_CURVATURE_RADIUS

BOUND_CUSHION_M = 0.001
DISTANCE_BATCH = 65536


def _xyz(lat, lon):
    a = np.deg2rad(lat)
    b = np.deg2rad(lon)
    return np.column_stack((np.cos(a) * np.cos(b), np.cos(a) * np.sin(b), np.sin(a)))


def _inverse_distances(lon1, lat1, lon2, lat2):
    if len(lon1) == 1:
        return np.asarray(
            [GEOD.inv(float(lon1[0]), float(lat1[0]), float(lon2[0]), float(lat2[0]))[2]],
            dtype=np.float64,
        )
    return np.asarray(GEOD.inv(lon1, lat1, lon2, lat2)[2], dtype=np.float64)


def wgs84_nearest_categories(tree, latitudes, longitudes, codes, query_lat, query_lon):
    """Find the global WGS84 representative winner in one conservative search.

    The winning category is the category of the globally nearest sample, so
    computing independent category minima is unnecessary. The nearest
    spherical sample supplies only an ellipsoidal upper witness. Every sample
    that can beat it is still checked with the same WGS84 inverse, including
    exact ties, and the lowest category code wins those ties.
    """
    lat = np.asarray(latitudes, dtype=float)
    lon = np.asarray(longitudes, dtype=float)
    qlat = np.asarray(query_lat, dtype=float)
    qlon = np.asarray(query_lon, dtype=float)
    codes = np.asarray(codes)
    if (
        lat.ndim != 1
        or lon.shape != lat.shape
        or codes.shape != lat.shape
        or not len(lat)
        or not np.issubdtype(codes.dtype, np.integer)
        or np.any((codes < 1) | (codes >= 2**32))
        or qlat.ndim != 1
        or qlon.shape != qlat.shape
        or any(np.any(~np.isfinite(a)) for a in (lat, lon, qlat, qlon))
        or np.any(np.abs(lat) > 90)
        or np.any(np.abs(qlat) > 90)
        or np.any(np.abs(lon) > 180)
        or np.any(np.abs(qlon) > 180)
    ):
        raise ValueError('invalid geodesic nearest inputs')
    if not len(qlat):
        return np.empty(0, dtype=np.uint32)
    xyz = _xyz(qlat, qlon)
    _, first = tree.query(xyz, k=1, workers=1)
    first = np.asarray(first, dtype=np.int64)
    upper = _inverse_distances(qlon, qlat, lon[first], lat[first])
    if np.any(~np.isfinite(upper)) or np.any(upper < 0):
        raise ValueError('invalid WGS84 upper bound')
    angle = np.minimum(math.pi, (upper + BOUND_CUSHION_M) / MIN_CURVATURE_RADIUS)
    radii = np.nextafter(2 * np.sin(angle / 2), math.inf)
    # Ordinary candidate batches keep large valid neighborhoods streaming;
    # neither the number of samples nor the number of candidates is limited.
    best = np.full(len(qlat), math.inf)
    chosen = np.full(len(qlat), 2**32, dtype=np.uint64)
    queries = []
    samples = []
    pending = 0

    def flush():
        nonlocal pending
        if not pending:
            return
        qi = np.concatenate(queries)
        ix = np.concatenate(samples)
        distances = _inverse_distances(qlon[qi], qlat[qi], lon[ix], lat[ix])
        if np.any(~np.isfinite(distances)) or np.any(distances < 0):
            raise ValueError('invalid WGS84 distance')
        previous = best.copy()
        np.minimum.at(best, qi, distances)
        chosen[best < previous] = 2**32
        tied = distances == best[qi]
        np.minimum.at(chosen, qi[tied], codes[ix[tied]])
        queries.clear()
        samples.clear()
        pending = 0

    for q in range(len(qlat)):
        ids = tree.query_ball_point(xyz[q], float(radii[q]), workers=1)
        if int(first[q]) not in ids:
            ids.append(int(first[q]))
        for start in range(0, len(ids), DISTANCE_BATCH):
            ix = np.asarray(ids[start : start + DISTANCE_BATCH], dtype=np.int64)
            queries.append(np.full(len(ix), q, dtype=np.int64))
            samples.append(ix)
            pending += len(ix)
            if pending >= DISTANCE_BATCH:
                flush()
    flush()
    if np.any(chosen >= 2**32) or np.any(~np.isfinite(best)):
        raise RuntimeError('no WGS84 hint candidate')
    return chosen.astype(np.uint32)
