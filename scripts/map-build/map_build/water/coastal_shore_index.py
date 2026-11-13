"""Reusable exact coastal-land span index for one immutable pair of RLE grids.

Build the four-neighbor geometry once, retaining spans rather than expanding
the globe into cell centers. Crops expand only their selected coastal cells,
in the same wrapped row/column order as the common reference extractor.
"""

from __future__ import annotations
import math
import numpy as np
from map_build.water import shared_nearest as shore


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
        raise ValueError('invalid RLE row')
    return ends, codes


class CoastalShoreIndex:
    def __init__(self, physical, land, width, height, *, land_codes=None):
        if any(type(v) is not int or v <= 0 for v in (width, height)):
            raise ValueError('invalid grid')
        self.width, self.height = width, height
        offsets = [0]
        all_starts, all_ends, all_codes = [], [], []

        def physical_row(y):
            ends, codes = row(physical, y, width)
            if np.any((codes != 1) & (codes != 17)):
                raise ValueError('invalid physical or land row')
            return ends, codes

        previous, current = None, physical_row(0)
        following = physical_row(1) if height > 1 else None
        for y in range(height):
            le, lv = row(land, y, width)
            pieces = [np.array([0, width]), le, current[0]]
            pieces.extend(adjacent[0] for adjacent in (previous, following) if adjacent is not None)
            cuts = np.unique(np.concatenate(pieces))
            starts, ends = cuts[:-1], cuts[1:]
            values = current[1][np.searchsorted(current[0], starts, side='right')]
            categories = lv[np.searchsorted(le, starts, side='right')]
            valid = categories > 0 if land_codes is None else np.isin(categories, land_codes)
            if np.any((values == 17) & ~valid):
                raise ValueError('invalid physical or land row')
            wet = np.zeros(len(starts), dtype=bool)
            for adjacent in (previous, following):
                if adjacent is not None:
                    wet |= adjacent[1][np.searchsorted(adjacent[0], starts, side='right')] == 1
            chosen = (values == 17) & wet
            aa, bb, cc = starts[chosen], ends[chosen], categories[chosen]
            ce, cv = current
            changes = np.flatnonzero(cv[:-1] != cv[1:])
            side = np.where(cv[changes] == 17, ce[changes] - 1, ce[changes]).astype(np.int64)
            if cv[0] != cv[-1]:
                side = np.r_[side, 0 if cv[0] == 17 else width - 1]
            if len(side):
                aa, bb = np.r_[aa, side], np.r_[bb, side + 1]
                cc = np.r_[cc, lv[np.searchsorted(le, side, side='right')]]
            order = np.argsort(aa, kind='stable')
            aa, bb, cc = aa[order], bb[order], cc[order]
            if len(aa):
                # Side-neighbor cells can duplicate or lie inside a vertical
                # coastal interval. Merge their union at category transitions
                # without converting every global span to Python tuples.
                split = np.r_[True, (aa[1:] > np.maximum.accumulate(bb)[:-1]) | (cc[1:] != cc[:-1])]
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
        self.starts = np.concatenate(all_starts) if all_starts else np.empty(0, dtype=np.uint32)
        self.ends = np.concatenate(all_ends) if all_ends else np.empty(0, dtype=np.uint32)
        self.codes = np.concatenate(all_codes) if all_codes else np.empty(0, dtype=np.uint32)

    def centers_for_crop(self, bounds, step, land_codes):
        x0, x1, y0, y1 = bounds
        width, height = self.width, self.height
        if not (
            0 <= y0 < y1 <= height and 0 < x1 - x0 <= width and math.isfinite(step) and step > 0
        ):
            raise ValueError('invalid crop')
        selected = np.asarray(land_codes, dtype=np.uint32)
        latitudes, longitudes, categories = [], [], []
        for y in range(y0, y1):
            first, last = map(int, self.offsets[y : y + 2])
            if first == last:
                continue
            starts, ends, codes = (
                self.starts[first:last],
                self.ends[first:last],
                self.codes[first:last],
            )
            x = x0
            while x < x1:
                xm = x % width
                stop = min(width, xm + x1 - x)
                a, b = np.searchsorted(ends, xm, side='right'), np.searchsorted(
                    starts, stop, side='left'
                )
                if a < b:
                    keep = np.isin(codes[a:b], selected)
                    aa = np.maximum(starts[a:b][keep].astype(np.int64), xm) - xm + x
                    bb = np.minimum(ends[a:b][keep].astype(np.int64), stop) - xm + x
                    if len(aa):
                        lengths = bb - aa
                        offsets = np.repeat(np.cumsum(lengths) - lengths, lengths)
                        xx = np.repeat(aa, lengths) + np.arange(int(lengths.sum())) - offsets
                        latitudes.append(np.full(len(xx), 90 - (y + 0.5) * step))
                        longitudes.append(((-180 + (xx + 0.5) * step + 180) % 360) - 180)
                        categories.append(np.repeat(codes[a:b][keep], bb - aa))
                x += stop - xm
        if not latitudes:
            raise ValueError('no participant shorelines in crop')
        lat, lon, category = (
            np.concatenate(latitudes),
            np.concatenate(longitudes),
            np.concatenate(categories),
        )
        return {'mids': shore.unit(lat, lon), 'lat': lat, 'lon': lon, 'category': category}
