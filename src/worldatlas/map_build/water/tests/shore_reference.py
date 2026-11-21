"""Independent row-wise shore extraction used to check the batched implementation."""

import math
import numpy as np
from worldatlas.map_build.water.shore_spans import ShoreSpans
from worldatlas.map_build.water import shared_nearest as shore


def row(grid, y, width):
    offsets, runs = grid
    first, last = int(offsets[y]), int(offsets[y + 1])
    ends, codes = runs[2 * first : 2 * last : 2], runs[2 * first + 1 : 2 * last : 2]
    if (
        not len(ends)
        or int(ends[0]) <= 0
        or int(ends[-1]) != width
        or np.any(ends[1:] <= ends[:-1])
    ):
        raise ValueError("invalid RLE row")
    return ends, codes


class ReferenceShoreIndex(ShoreSpans):
    def __init__(self, physical, land, width, height, *, land_codes=None):
        if any(type(v) is not int or v <= 0 for v in (width, height)):
            raise ValueError("invalid grid")
        self.width, self.height = width, height
        offsets = [0]
        all_starts, all_ends, all_codes = [], [], []

        def physical_row(y):
            ends, codes = row(physical, y, width)
            if np.any((codes != 1) & (codes != 17)):
                raise ValueError("invalid physical or land row")
            return ends, codes

        previous, current = None, physical_row(0)
        following = physical_row(1) if height > 1 else None
        for y in range(height):
            le, lv = row(land, y, width)
            pieces = [np.array([0, width]), le, current[0]]
            pieces.extend(
                adjacent[0]
                for adjacent in (previous, following)
                if adjacent is not None
            )
            cuts = np.unique(np.concatenate(pieces))
            starts, ends = cuts[:-1], cuts[1:]
            values = current[1][np.searchsorted(current[0], starts, side="right")]
            categories = lv[np.searchsorted(le, starts, side="right")]
            valid = (
                categories > 0
                if land_codes is None
                else np.isin(categories, land_codes)
            )
            if np.any((values == 17) & ~valid):
                raise ValueError("invalid physical or land row")
            wet = np.zeros(len(starts), dtype=bool)
            for adjacent in (previous, following):
                if adjacent is not None:
                    wet |= (
                        adjacent[1][np.searchsorted(adjacent[0], starts, side="right")]
                        == 1
                    )
            chosen = (values == 17) & wet
            aa, bb, cc = starts[chosen], ends[chosen], categories[chosen]
            ce, cv = current
            changes = np.flatnonzero(cv[:-1] != cv[1:])
            side = np.where(cv[changes] == 17, ce[changes] - 1, ce[changes]).astype(
                np.int64
            )
            if cv[0] != cv[-1]:
                side = np.r_[side, 0 if cv[0] == 17 else width - 1]
            if len(side):
                aa, bb = np.r_[aa, side], np.r_[bb, side + 1]
                cc = np.r_[cc, lv[np.searchsorted(le, side, side="right")]]
            order = np.argsort(aa, kind="stable")
            aa, bb, cc = aa[order], bb[order], cc[order]
            if len(aa):
                # Side-neighbor cells can duplicate or lie inside a vertical
                # coastal interval. Merge their union at category transitions
                # without converting every global span to Python tuples.
                split = np.r_[
                    True,
                    (aa[1:] > np.maximum.accumulate(bb)[:-1]) | (cc[1:] != cc[:-1]),
                ]
                indices = np.flatnonzero(split)
                all_starts.append(aa[indices].astype(np.uint32))
                all_ends.append(np.maximum.reduceat(bb, indices).astype(np.uint32))
                all_codes.append(cc[indices].astype(np.uint32))
                offsets.append(offsets[-1] + len(indices))
            else:
                offsets.append(offsets[-1])
            previous, current = current, following
            following = physical_row(y + 2) if y + 2 < height else None
        self.offsets = np.asarray(offsets, dtype=np.uint64)
        self.starts = (
            np.concatenate(all_starts) if all_starts else np.empty(0, dtype=np.uint32)
        )
        self.ends = (
            np.concatenate(all_ends) if all_ends else np.empty(0, dtype=np.uint32)
        )
        self.codes = (
            np.concatenate(all_codes) if all_codes else np.empty(0, dtype=np.uint32)
        )


def _shore_spans(grid, y, x0, x1, width):
    rows, runs = grid
    first, last = int(rows[y]), int(rows[y + 1])
    ends = runs[2 * first : 2 * last : 2]
    vals = runs[2 * first + 1 : 2 * last : 2]
    if (
        not len(ends)
        or int(ends[0]) <= 0
        or int(ends[-1]) != width
        or np.any(ends[1:] <= ends[:-1])
    ):
        raise ValueError("invalid RLE row")
    out_e = []
    out_v = []
    x = x0
    while x < x1:
        xm = x % width
        take = min(x1 - x, width - xm)
        stop = xm + take
        i = int(np.searchsorted(ends, xm, side="right"))
        j = int(np.searchsorted(ends, stop, side="left")) + 1
        ee = np.minimum(ends[i:j].astype(np.int64), stop) - xm + x
        out_e.extend(ee.tolist())
        out_v.extend(vals[i:j].tolist())
        x += take
    return np.asarray(out_e, dtype=np.int64), np.asarray(out_v, dtype=np.int64)


def centers_for_crop(
    physical, land, bounds, width, height, step, land_codes, *, all_land_codes=None
):
    """Extract exact four-neighbor coastal centers from RLE change positions.

    Dense arrays are allocated only for coastal centers. Wrapped crops retain
    original row/column order and use real physical neighbors beyond crop edges.
    """
    x0, x1, y0, y1 = bounds
    if not (
        0 <= y0 < y1 <= height
        and 0 < x1 - x0 <= width
        and math.isfinite(step)
        and step > 0
    ):
        raise ValueError("invalid crop")
    selected = np.asarray(land_codes, dtype=np.uint32)
    latitudes = []
    longitudes = []
    categories = []
    count = 0

    # full-width crops cannot be extended in the original crop helper, but this
    # span reader intentionally supports repeated wrapping for the side halo.
    def pget(y):
        e, v = _shore_spans(physical, y, x0 - 1, x1 + 1, width)
        if np.any((v != 1) & (v != 17)):
            raise ValueError("invalid physical or land row")
        return e, v

    prev = pget(y0 - 1) if y0 > 0 else None
    cur = pget(y0)
    nxt = pget(y0 + 1) if y0 + 1 < height else None
    for y in range(y0, y1):
        le, lv = _shore_spans(land, y, x0, x1, width)
        # Break at all changes in either adjacent physical row, current physical
        # row, or land category. Side halo endpoints are clipped out.
        breaks = [np.array([x0, x1]), le, cur[0]]
        if prev is not None:
            breaks.append(prev[0])
        if nxt is not None:
            breaks.append(nxt[0])
        b = np.unique(np.concatenate(breaks))
        b = b[(b >= x0) & (b <= x1)]
        starts = b[:-1]
        ends = b[1:]
        mv = cur[1][np.searchsorted(cur[0], starts, side="right")]
        cats = lv[np.searchsorted(le, starts, side="right")]
        valid = (cats > 0) if all_land_codes is None else np.isin(cats, all_land_codes)
        bad = (mv == 17) & ~valid
        if np.any(bad):
            raise ValueError("invalid physical or land row")
        wet = np.zeros(len(starts), dtype=bool)
        for row in (prev, nxt):
            if row is not None:
                wet |= row[1][np.searchsorted(row[0], starts, side="right")] == 1
        chosen = (mv == 17) & np.isin(cats, selected) & wet
        starts1 = starts[chosen]
        ends1 = ends[chosen]
        xx = (
            np.concatenate(
                [np.arange(a, b, dtype=np.int64) for a, b in zip(starts1, ends1)]
            )
            if len(starts1)
            else np.empty(0, dtype=np.int64)
        )
        # Horizontal coast consists of the land cell on each wet/dry run boundary.
        ce, cv = cur
        t = np.flatnonzero(cv[:-1] != cv[1:])
        boundary = ce[t]
        side = np.where(cv[t] == 17, boundary - 1, boundary)
        side = side[(side >= x0) & (side < x1)]
        if len(side):
            sc = lv[np.searchsorted(le, side, side="right")]
            side = side[np.isin(sc, selected)]
            xx = np.union1d(xx, side)
        count += len(xx)
        if len(xx):
            latitudes.append(np.full(len(xx), 90 - (y + 0.5) * step))
            longitudes.append(((-180 + (xx + 0.5) * step + 180) % 360) - 180)
            categories.append(
                lv[np.searchsorted(le, xx, side="right")].astype(np.uint32)
            )
        prev, cur = cur, nxt
        nxt = pget(y + 2) if y + 2 < height and y + 1 < y1 else None
    if not count:
        raise ValueError("no participant shorelines in crop")
    lat = np.concatenate(latitudes)
    lon = np.concatenate(longitudes)
    cat = np.concatenate(categories)
    return {"mids": shore.unit(lat, lon), "lat": lat, "lon": lon, "category": cat}
