"""Exact WGS84 nearest-class certificates over selected cell-center rectangles.

The mask is only a selection, never a source of previous labels. Rectangles
share proofs across rows; uncertain cells use the complete point classifier.
"""

import math
from collections.abc import Callable, Sequence

import numpy as np

from worldatlas.geodesy.wgs84 import MAX_RADIUS, MIN_RADIUS, unit_sphere
from worldatlas.map_build.execution.control import check_cancelled
from worldatlas.map_build.water import shared_nearest as s
from worldatlas.map_build.water.shared_nearest import ShoreIndexes


def rectangle_counts(
    mask: np.ndarray, block: int
) -> Callable[[int, int, int, int], np.integer]:
    """Prepare a fast count of selected cells in the rectangles of each tile.

    Args:
        mask: Two-dimensional bool grid of selected cells.
        block: Maximum width and height of a tile.

    Returns:
        Function taking (first_row, end_row, first_column, end_column)
        for a window inside one tile and returning its selected cell count.
    """
    nr, nc = mask.shape
    h, w = min(block, nr), min(block, nc)
    ny, nx = math.ceil(nr / h), math.ceil(nc / w)
    padded = np.pad(mask, ((0, ny * h - nr), (0, nx * w - nc)))
    tiles = np.ascontiguousarray(padded.reshape(ny, h, nx, w).transpose(0, 2, 1, 3))
    dtype = np.int32 if h * w <= np.iinfo(np.int32).max else np.int64
    table = np.pad(
        tiles.cumsum(axis=3, dtype=dtype).cumsum(axis=2, dtype=dtype),
        ((0, 0), (0, 0), (1, 0), (1, 0)),
    )

    def count(a: int, b: int, c: int, d: int) -> np.integer:
        """Count selected cells within one tile.

        Args:
            a: First row, in mask coordinates.
            b: Exclusive end row.
            c: First column, in mask coordinates.
            d: Exclusive end column.

        Returns:
            Integer count from the tile's precomputed sums.
        """
        ty, tx = a // h, c // w
        a, b, c, d = a - ty * h, b - ty * h, c - tx * w, d - tx * w
        return (
            table[ty, tx, b, d]
            - table[ty, tx, a, d]
            - table[ty, tx, b, c]
            + table[ty, tx, a, c]
        )

    return count


def exact_certificate_possible(
    lower: np.ndarray,
    best: np.ndarray,
    upper: np.ndarray,
    radius: np.ndarray,
    boundary: np.ndarray,
) -> np.ndarray:
    """Check whether exact distances could prove one owner for a rectangle.

    The distance from the rectangle's centre to any of its cells is at most
    its radius. If even the most favourable bounds fall short of the
    needed gap, split the rectangle without measuring exact distances.

    Args:
        lower: Rectangle-by-category array of shore lower bounds in metres.
        best: Candidate category column for each rectangle.
        upper: Measured upper distance bound for each candidate.
        radius: Distance in metres from the centre to cover each rectangle.
        boundary: Lower bound in metres to shores outside the crop.

    Returns:
        Bool array marking rectangles that might have one provable owner.
    """
    maximum = np.where(
        lower < MIN_RADIUS * 1.98,
        MAX_RADIUS / MIN_RADIUS * (lower + 0.001) + 0.01,
        math.pi * MAX_RADIUS + 0.01,
    )
    rows = np.arange(len(lower))
    maximum[rows, best] = np.minimum(maximum[rows, best], upper)
    possible = np.zeros(len(lower), dtype=bool)
    for col in range(lower.shape[1]):
        competing = maximum.copy()
        competing[:, col] = np.inf
        possible |= (competing.min(axis=1) - lower[:, col] > 2 * radius) & (
            boundary - lower[:, col] > 2 * radius
        )
    return possible


def classify(
    water: np.ndarray,
    x0: int,
    y0: int,
    bounds: tuple[int, int, int, int],
    width: int,
    height: int,
    step: float,
    owners: Sequence[int],
    indexes: ShoreIndexes,
    point_classifier: Callable[[np.ndarray, np.ndarray], tuple[np.ndarray, int, int]],
    block: int = 64,
    *,
    band: float | None = None,
) -> tuple[np.ndarray, dict[str, int]]:
    """Assign selected water cells to the nearest shore.

    Args:
        water: Two-dimensional bool mask of cells to assign.
        x0: First column of the mask.
        y0: First row of the mask.
        bounds: Grid window represented by the shore indexes.
        width: Full grid width in columns.
        height: Full grid height in rows.
        step: Cell size in degrees.
        owners: Owner IDs in exact tie order.
        indexes: Spatial indexes by shore code.
        point_classifier: Function for unresolved points. Takes latitude and
            longitude arrays and returns codes and bounded and exact counts.
        block: Tile side length in cells.
        band: Optional maximum distance to shore in metres.

    Returns:
        (codes, counts). Codes are a uint32 grid shaped like water, with
        zero where no cell was assigned. Counts describe bounded and exact work.
    """
    water = np.asarray(water)
    if water.ndim != 2 or water.dtype != np.bool_:
        raise ValueError("boolean selection grid required")
    if (
        len(owners) < (2 if band is None else 0)
        or any(type(owner) is not int or not 0 < owner < 2**32 for owner in owners)
        or len(set(owners)) != len(owners)
    ):
        raise ValueError("invalid participant classes")
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
        or not math.isfinite(step)
        or step <= 0
        or step != 360 / width
        or not callable(point_classifier)
    ):
        raise ValueError("invalid grid or classifier")
    if band is not None and (not math.isfinite(band) or band < 0):
        raise ValueError("invalid coastal band")
    threshold = None if band is None else band
    if (
        not isinstance(bounds, (list, tuple))
        or len(bounds) != 4
        or any(type(v) is not int for v in bounds)
    ):
        raise ValueError("invalid crop")
    xa, xb, ya, yb = bounds
    if not (0 < xb - xa <= width and 0 <= ya < yb <= height):
        raise ValueError("invalid crop")
    if nr and 90 - (y0 + nr - 0.5) * step < -90:
        raise ValueError("query latitude outside globe")
    output = np.zeros(water.shape, dtype=np.uint32)
    total = int(water.sum())
    stats = {
        "certified_cells": 0,
        "leaf_cells": 0,
        "bounded_cells": 0,
        "exact_cells": 0,
        "exact_rectangle_probes": 0,
    }
    if not total:
        return output, stats
    wet = rectangle_counts(water, block)

    ys, xs = np.meshgrid(
        np.arange(0, nr, block), np.arange(0, nc, block), indexing="ij"
    )
    a, c = ys.ravel(), xs.ravel()
    b, d = np.minimum(a + block, nr), np.minimum(c + block, nc)
    keep = wet(a, b, c, d) > 0
    a, b, c, d = a[keep], b[keep], c[keep], d[keep]
    leaves = []
    available = [owner for owner in owners if owner in indexes]
    complete = len(available) == len(owners) or band is not None
    while len(a):
        check_cancelled()
        lat = 90 - (y0 + (a + b) / 2) * step
        lon = -180 + (x0 + (c + d) / 2) * step
        points = unit_sphere(lat, lon)
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
            (y0 + a >= ya)
            & (y0 + b <= yb)
            & (mapped + 0.5 >= xa)
            & (mapped + d - c - 0.5 <= xb)
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
                & (upper + 2 * radius < other.min(axis=1))
                & (upper + 2 * radius < boundary)
            )
            possible = exact_certificate_possible(lower, best, upper, radius, boundary)
            if band is not None:
                inside &= upper + radius <= threshold
                outside = (
                    inside_crop
                    & (lower.min(axis=1) - radius > threshold)
                    & (boundary - radius > threshold)
                )
                possible &= lower.min(axis=1) + radius <= threshold
                possible |= (upper > threshold + radius) & (
                    boundary > threshold + radius
                )
            probe = np.flatnonzero(
                inside_crop & ~(inside | outside) & possible & ((b - a) * (d - c) > 1)
            )
            if len(probe):
                exact_lower = lower[probe].copy()
                exact_upper = np.full_like(exact_lower, np.inf)
                for col, code in enumerate(available):
                    # Excluded classes keep their already-valid lower bound.
                    needed = exact_lower[:, col] <= upper[probe] + 2 * radius[probe]
                    if band is not None:
                        needed &= (
                            exact_lower[:, col] <= threshold + radius[probe] + 0.001
                        )
                    q = probe[needed]
                    values = s.exact_minima_by_ordered_chord(
                        points[q], lon[q], lat[q], *indexes[code]
                    )
                    if np.any(~np.isfinite(values)):
                        raise RuntimeError("invalid exact rectangle distances")
                    exact_lower[needed, col] = np.maximum(0, values - 0.001)
                    exact_upper[needed, col] = values + 0.001
                winner = np.argmin(exact_upper, axis=1)
                rows = np.arange(len(probe))
                if band is not None:
                    outside[probe] = (
                        exact_lower.min(axis=1) - radius[probe] > threshold
                    ) & (boundary[probe] - radius[probe] > threshold)
                exact_lower[rows, winner] = np.inf
                proved = (
                    exact_upper[rows, winner] + 2 * radius[probe]
                    < exact_lower.min(axis=1)
                ) & (exact_upper[rows, winner] + 2 * radius[probe] < boundary[probe])
                if band is not None:
                    proved &= exact_upper[rows, winner] + radius[probe] <= threshold
                chosen = probe[proved]
                inside[chosen] = True
                best[chosen] = winner[proved]
                stats["exact_rectangle_probes"] += len(probe)
        elif band is not None:
            outside = inside_crop & (boundary - radius > threshold)
        good = inside | outside
        stats["certified_cells"] += int(wet(a[good], b[good], c[good], d[good]).sum())
        for i in np.flatnonzero(inside):
            output[a[i] : b[i], c[i] : d[i]] = available[int(best[i])]
        pending = ~good
        leaf = pending & (b - a == 1) & (d - c == 1)
        if np.any(leaf):
            leaves.append((a[leaf], c[leaf]))
        pending &= ~leaf
        a, b, c, d = a[pending], b[pending], c[pending], d[pending]
        ym, xm = (
            np.where(b - a > 1, (a + b) // 2, b),
            np.where(d - c > 1, (c + d) // 2, d),
        )
        aa, bb = np.r_[a, a, ym, ym], np.r_[ym, ym, b, b]
        cc, dd = np.r_[c, xm, c, xm], np.r_[xm, d, xm, d]
        keep = (aa < bb) & (cc < dd)
        a, b, c, d = aa[keep], bb[keep], cc[keep], dd[keep]
        keep = wet(a, b, c, d) > 0
        a, b, c, d = a[keep], b[keep], c[keep], d[keep]
    yy = (
        np.concatenate([q[0] for q in leaves])
        if leaves
        else np.empty(0, dtype=np.int64)
    )
    xx = (
        np.concatenate([q[1] for q in leaves])
        if leaves
        else np.empty(0, dtype=np.int64)
    )
    stats["bounded_cells"] = stats["certified_cells"]
    # Ordinary point batches cover every unresolved selected cell, without an
    # input-size/candidate limit or any full-grid dense allocation.
    for first in range(0, len(yy), 5000):
        check_cancelled()
        gy, gx = yy[first : first + 5000], xx[first : first + 5000]
        codes, bounded, exact = point_classifier(
            90 - (y0 + gy + 0.5) * step, -180 + (x0 + gx + 0.5) * step
        )
        codes = np.asarray(codes)
        if (
            codes.shape != gx.shape
            or not np.issubdtype(codes.dtype, np.integer)
            or np.any(~np.isin(codes, ([0] if band is not None else []) + list(owners)))
            or any(
                not isinstance(v, (int, np.integer)) or isinstance(v, (bool, np.bool_))
                for v in (bounded, exact)
            )
            or min(bounded, exact) < 0
            or bounded + exact != len(gx)
        ):
            raise ValueError("invalid point classifier result")
        output[gy, gx] = codes
        stats["bounded_cells"] += int(bounded)
        stats["exact_cells"] += int(exact)
    output[~water] = 0
    stats["leaf_cells"] = len(yy)
    if (
        stats["certified_cells"] + len(yy) != total
        or stats["bounded_cells"] + stats["exact_cells"] != total
    ):
        raise RuntimeError("rectangle classification accounting mismatch")
    return output, stats
