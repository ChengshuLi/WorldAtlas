"""Coastal-band rectangle certificates with complete WGS84 fallback."""

import math
import numpy as np
from map_build.water import shared_nearest as s
from map_build.water import coastal_core as core


def classify(water, x0, y0, bounds, w, h, step, pairs, tol, band, bandtol, idx, block=32):
    water = np.asarray(water)
    if water.ndim != 2 or water.dtype != np.bool_:
        raise ValueError('boolean water grid required')
    nr, nc = water.shape
    if any(type(z) is not int for z in (x0, y0, w, h)) or not (
        0 < w
        and 0 < h
        and 0 <= x0 <= x0 + nc <= w
        and 0 <= y0 <= y0 + nr <= h
        and math.isfinite(step)
        and step > 0
        and abs(step * w - 360) <= 1e-8
    ):
        raise ValueError('invalid grid')
    if (
        type(block) != int
        or block <= 0
        or not all(math.isfinite(z) and z >= 0 for z in (tol, band, bandtol))
    ):
        raise ValueError('invalid classification parameters')
    if nr and 90 - (y0 + nr - 0.5) * step < -90:
        raise ValueError('query latitude outside globe')
    xa, xb, ya, yb = bounds
    if any(type(z) is not int for z in bounds) or not (
        0 < xb - xa <= w and 0 <= ya < yb <= h and y0 >= ya and y0 + nr <= yb
    ):
        raise ValueError('invalid crop')
    # Crop may wrap the antimeridian; place core in the same unwrapped copy.
    mapped = x0 + math.ceil((xa - x0) / w) * w
    if mapped < xa or mapped + nc > xb:
        raise ValueError('query outside crop')
    if not nr or not nc:
        return np.zeros((nr, nc), dtype=np.uint32), {'bounded': 0, 'exact': 0}
    # Summed area lets each rectangle skip land-only regions in constant time.
    sat = np.pad(
        np.cumsum(np.cumsum(water, axis=0, dtype=np.int64), axis=1, dtype=np.int64),
        ((1, 0), (1, 0)),
    )

    def wet(y0, y1, x0, x1):
        return sat[y1, x1] - sat[y0, x1] - sat[y1, x0] + sat[y0, x0]

    ys, xs = np.meshgrid(np.arange(0, nr, block), np.arange(0, nc, block), indexing='ij')
    a = ys.ravel()
    c = xs.ravel()
    b = np.minimum(a + block, nr)
    d = np.minimum(c + block, nc)
    mask = wet(a, b, c, d) > 0
    a, b, c, d = a[mask], b[mask], c[mask], d[mask]
    output = np.zeros(water.shape, dtype=np.uint32)
    available = [p for p in pairs if p[1] in idx]
    unresolved = []
    while len(a):
        # Centers are midpoints between extreme grid-cell centers.
        ml = 90 - (y0 + (a + b) / 2) * step
        mid = -180 + (x0 + (c + d) / 2) * step
        pts = s.unit(ml, mid)
        half_lat = (b - a - 1) * step / 2
        half_lon = (d - c - 1) * step / 2
        # The linear lat/lon path is bounded by the maximum principal radius
        # and the maximum parallel radius attained within the rectangle.
        rmax = s.A / (1 - s.F)
        closest_abs = np.maximum(0, np.abs(ml) - half_lat)
        radius = (
            np.hypot(
                rmax * np.deg2rad(half_lat),
                rmax * np.cos(np.deg2rad(closest_abs)) * np.deg2rad(half_lon),
            )
            + 0.01
        )
        if available:
            lows, winner, candidate = s.nearest_class_bounds(
                ml, mid, pts, available, idx, upper_limit=band + bandtol + radius
            )
            low = lows.min(axis=1)
        else:
            lows = np.empty((len(mid), 0))
            low = np.full(len(mid), np.inf)
        boundary = s.boundary_lower(ml, mid, bounds, w, h, step)
        outside = (low - radius > band + bandtol) & (boundary - radius > band + bandtol)
        inside = np.zeros(len(mid), dtype=bool)
        if available:
            upper = candidate + radius
            others = lows.copy()
            others[np.arange(len(mid)), winner] = np.inf
            inside = (
                (~outside)
                & (upper <= band + bandtol)
                & (upper + tol < others.min(axis=1) - radius)
                & (upper + tol < boundary - radius)
            )
            for k, (_, _, code) in enumerate(available):
                for i in np.flatnonzero(inside & (winner == k)):
                    output[a[i] : b[i], c[i] : d[i]] = code
        pending = ~(outside | inside)
        leaf = pending & (b - a == 1) & (d - c == 1)
        if np.any(leaf):
            unresolved.append((a[leaf], c[leaf]))
        pending &= ~leaf
        a, b, c, d = a[pending], b[pending], c[pending], d[pending]
        if not len(a):
            break
        # Four children if both dimensions exceed one, two otherwise.
        ym = np.where(b - a > 1, (a + b) // 2, b)
        xm = np.where(d - c > 1, (c + d) // 2, d)
        aa = np.concatenate([a, a, ym, ym])
        bb = np.concatenate([ym, ym, b, b])
        cc = np.concatenate([c, xm, c, xm])
        dd = np.concatenate([xm, d, xm, d])
        valid = (aa < bb) & (cc < dd)
        aa, bb, cc, dd = aa[valid], bb[valid], cc[valid], dd[valid]
        valid = wet(aa, bb, cc, dd) > 0
        a, b, c, d = aa[valid], bb[valid], cc[valid], dd[valid]
    ny = np.concatenate([q[0] for q in unresolved]) if unresolved else np.empty(0, dtype=np.int64)
    nx = np.concatenate([q[1] for q in unresolved]) if unresolved else np.empty(0, dtype=np.int64)
    stats = {'bounded': int(water.sum()) - len(ny), 'exact': 0}
    if len(ny):
        lat = 90 - (y0 + ny + 0.5) * step
        lon = -180 + (x0 + nx + 0.5) * step
        codes, s0 = core.classify(lat, lon, bounds, w, h, step, pairs, tol, band, bandtol, idx)
        output[ny, nx] = codes
        stats['bounded'] += s0['bounded']
        stats['exact'] += s0['exact']
    if stats['bounded'] + stats['exact'] != int(water.sum()):
        raise RuntimeError('accounting mismatch')
    output[~water] = 0
    return output, stats


def centers_for_crop(physical, land, bounds, width, height, step, land_codes):
    """Use the common exact RLE shoreline extractor for coast and shared seas."""
    return s.centers_for_crop(physical, land, bounds, width, height, step, land_codes)
