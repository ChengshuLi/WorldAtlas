"""Exact WGS84 nearest-class certificates over selected cell-center rectangles.

The mask is only a selection, never a source of previous labels. Rectangles
share proofs across rows; uncertain cells use the complete point classifier.
"""

import math
import numpy as np
from map_build.water import shared_nearest as s
from map_build.water.interval_nearest import exact_certificate_possible

MAX_RADIUS = s.A / (1 - s.F)


def classify(
    water,
    x0,
    y0,
    bounds,
    width,
    height,
    step,
    pairs,
    tolerance,
    indexes,
    point_classifier,
    block=64,
    *,
    band=None,
    band_tolerance=0.0
):
    water = np.asarray(water)
    if water.ndim != 2 or water.dtype != np.bool_:
        raise ValueError('boolean selection grid required')
    if (
        not isinstance(pairs, (list, tuple))
        or len(pairs) < (2 if band is None else 0)
        or any(
            not isinstance(p, (list, tuple))
            or len(p) != 3
            or type(p[1]) is not int
            or type(p[2]) is not int
            for p in pairs
        )
        or len({p[1] for p in pairs}) != len(pairs)
        or len({p[2] for p in pairs}) != len(pairs)
    ):
        raise ValueError('invalid participant classes')
    nr, nc = water.shape
    if (
        any(type(v) is not int for v in (x0, y0, width, height, block))
        or not (
            width > 0
            and height > 0
            and block > 0
            and 0 <= x0 <= x0 + nc <= width
            and 0 <= y0 <= y0 + nr <= height
        )
        or isinstance(step, (bool, np.bool_))
        or isinstance(tolerance, (bool, np.bool_))
        or not math.isfinite(step)
        or step <= 0
        or abs(step * width - 360) > 1e-8
        or not math.isfinite(tolerance)
        or tolerance < 0
        or not callable(point_classifier)
    ):
        raise ValueError('invalid grid or classifier')
    if band is not None and (
        not math.isfinite(band)
        or band < 0
        or not math.isfinite(band_tolerance)
        or band_tolerance < 0
    ):
        raise ValueError('invalid coastal band')
    threshold = None if band is None else band + band_tolerance
    if (
        not isinstance(bounds, (list, tuple))
        or len(bounds) != 4
        or any(type(v) is not int for v in bounds)
    ):
        raise ValueError('invalid crop')
    xa, xb, ya, yb = bounds
    if not (0 < xb - xa <= width and 0 <= ya < yb <= height):
        raise ValueError('invalid crop')
    if nr and 90 - (y0 + nr - 0.5) * step < -90:
        raise ValueError('query latitude outside globe')
    output = np.zeros(water.shape, dtype=np.uint32)
    total = int(water.sum())
    stats = {
        'certified_cells': 0,
        'leaf_cells': 0,
        'bounded_cells': 0,
        'exact_cells': 0,
        'exact_rectangle_probes': 0,
    }
    if not total:
        return output, stats
    sat = np.pad(
        water.cumsum(axis=0, dtype=np.int64).cumsum(axis=1, dtype=np.int64), ((1, 0), (1, 0))
    )

    def wet(a, b, c, d):
        return sat[b, d] - sat[a, d] - sat[b, c] + sat[a, c]

    ys, xs = np.meshgrid(np.arange(0, nr, block), np.arange(0, nc, block), indexing='ij')
    a, c = ys.ravel(), xs.ravel()
    b, d = np.minimum(a + block, nr), np.minimum(c + block, nc)
    keep = wet(a, b, c, d) > 0
    a, b, c, d = a[keep], b[keep], c[keep], d[keep]
    leaves = []
    available = [p for p in pairs if p[1] in indexes]
    complete = len(available) == len(pairs) or band is not None
    while len(a):
        lat = 90 - (y0 + (a + b) / 2) * step
        lon = -180 + (x0 + (c + d) / 2) * step
        points = s.unit(lat, lon)
        half_lat, half_lon = (b - a - 1) * step / 2, (d - c - 1) * step / 2
        # Integrating the straight lat/lon segment bounds its ellipsoidal
        # length by this maximum metric norm. A geodesic is no longer.
        closest = np.maximum(0, np.abs(lat) - half_lat)
        radius = (
            np.hypot(
                MAX_RADIUS * np.deg2rad(half_lat),
                MAX_RADIUS * np.cos(np.deg2rad(closest)) * np.deg2rad(half_lon),
            )
            + 0.01
        )
        left = x0 + c
        mapped = left + np.ceil((xa - left - 0.5) / width).astype(np.int64) * width
        inside_crop = (
            (y0 + a >= ya) & (y0 + b <= yb) & (mapped + 0.5 >= xa) & (mapped + d - c - 0.5 <= xb)
        )
        inside = np.zeros(len(a), dtype=bool)
        outside = np.zeros(len(a), dtype=bool)
        best = np.zeros(len(a), dtype=np.int64)
        boundary = s.boundary_lower(lat, lon, bounds, width, height, step)
        if complete and available:
            lower, best, upper = s.nearest_class_bounds(
                lat,
                lon,
                points,
                available,
                indexes,
                upper_limit=None if band is None else threshold + radius,
            )
            other = lower.copy()
            other[np.arange(len(a)), best] = np.inf
            inside = (
                inside_crop
                & (upper + 2 * radius + tolerance < other.min(axis=1))
                & (upper + 2 * radius + tolerance < boundary)
            )
            possible = exact_certificate_possible(lower, best, upper, radius, tolerance, boundary)
            if band is not None:
                inside &= upper + radius <= threshold
                outside = (
                    inside_crop
                    & (lower.min(axis=1) - radius > threshold)
                    & (boundary - radius > threshold)
                )
                possible &= lower.min(axis=1) + radius <= threshold
                possible |= (upper > threshold + radius) & (boundary > threshold + radius)
            probe = np.flatnonzero(
                inside_crop & ~(inside | outside) & possible & ((b - a) * (d - c) > 1)
            )
            if len(probe):
                exact_lower = lower[probe].copy()
                exact_upper = np.full_like(exact_lower, np.inf)
                for col, (_, code, _) in enumerate(available):
                    # Excluded classes keep their already-valid lower bound.
                    needed = exact_lower[:, col] <= upper[probe] + 2 * radius[probe] + tolerance
                    if band is not None:
                        needed &= (
                            exact_lower[:, col] <= threshold + radius[probe] + tolerance + 0.001
                        )
                    q = probe[needed]
                    values = s.exact_minima_by_ordered_chord(
                        points[q], lon[q], lat[q], *indexes[code]
                    )
                    if np.any(~np.isfinite(values)):
                        raise RuntimeError('invalid exact rectangle distances')
                    exact_lower[needed, col] = np.maximum(0, values - 0.001)
                    exact_upper[needed, col] = values + 0.001
                winner = np.argmin(exact_upper, axis=1)
                rows = np.arange(len(probe))
                if band is not None:
                    outside[probe] = (exact_lower.min(axis=1) - radius[probe] > threshold) & (
                        boundary[probe] - radius[probe] > threshold
                    )
                exact_lower[rows, winner] = np.inf
                proved = (
                    exact_upper[rows, winner] + 2 * radius[probe] + tolerance
                    < exact_lower.min(axis=1)
                ) & (exact_upper[rows, winner] + 2 * radius[probe] + tolerance < boundary[probe])
                if band is not None:
                    proved &= exact_upper[rows, winner] + radius[probe] <= threshold
                chosen = probe[proved]
                inside[chosen] = True
                best[chosen] = winner[proved]
                stats['exact_rectangle_probes'] += len(probe)
        elif band is not None:
            outside = inside_crop & (boundary - radius > threshold)
        good = inside | outside
        for i in np.flatnonzero(good):
            if inside[i]:
                output[a[i] : b[i], c[i] : d[i]] = available[int(best[i])][2]
            stats['certified_cells'] += int(wet(a[i], b[i], c[i], d[i]))
        pending = ~good
        leaf = pending & (b - a == 1) & (d - c == 1)
        if np.any(leaf):
            leaves.append((a[leaf], c[leaf]))
        pending &= ~leaf
        a, b, c, d = a[pending], b[pending], c[pending], d[pending]
        ym, xm = np.where(b - a > 1, (a + b) // 2, b), np.where(d - c > 1, (c + d) // 2, d)
        aa, bb = np.r_[a, a, ym, ym], np.r_[ym, ym, b, b]
        cc, dd = np.r_[c, xm, c, xm], np.r_[xm, d, xm, d]
        keep = (aa < bb) & (cc < dd)
        a, b, c, d = aa[keep], bb[keep], cc[keep], dd[keep]
        keep = wet(a, b, c, d) > 0
        a, b, c, d = a[keep], b[keep], c[keep], d[keep]
    yy = np.concatenate([q[0] for q in leaves]) if leaves else np.empty(0, dtype=np.int64)
    xx = np.concatenate([q[1] for q in leaves]) if leaves else np.empty(0, dtype=np.int64)
    stats['bounded_cells'] = stats['certified_cells']
    # Ordinary point batches cover every unresolved selected cell, without an
    # input-size/candidate limit or any full-grid dense allocation.
    for first in range(0, len(yy), 5000):
        gy, gx = yy[first : first + 5000], xx[first : first + 5000]
        codes, bounded, exact = point_classifier(
            90 - (y0 + gy + 0.5) * step, -180 + (x0 + gx + 0.5) * step
        )
        codes = np.asarray(codes)
        if (
            codes.shape != gx.shape
            or not np.issubdtype(codes.dtype, np.integer)
            or np.any(~np.isin(codes, ([0] if band is not None else []) + [p[2] for p in pairs]))
            or any(
                not isinstance(v, (int, np.integer)) or isinstance(v, (bool, np.bool_))
                for v in (bounded, exact)
            )
            or min(bounded, exact) < 0
            or bounded + exact != len(gx)
        ):
            raise ValueError('invalid point classifier result')
        output[gy, gx] = codes
        stats['bounded_cells'] += int(bounded)
        stats['exact_cells'] += int(exact)
    output[~water] = 0
    stats['leaf_cells'] = len(yy)
    if (
        stats['certified_cells'] + len(yy) != total
        or stats['bounded_cells'] + stats['exact_cells'] != total
    ):
        raise RuntimeError('rectangle classification accounting mismatch')
    return output, stats
