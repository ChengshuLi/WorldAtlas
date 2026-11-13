"""Conservative WGS84 certificates from complete tiles and real seed witnesses."""

import math
import numpy as np
from scipy.spatial import cKDTree
from map_build.core.geodesy import GEOD, MIN_RADIUS as M_MIN


def _unit(lat, lon):
    p = np.deg2rad(lat)
    l = np.deg2rad(lon)
    return np.column_stack((np.cos(p) * np.cos(l), np.cos(p) * np.sin(l), np.sin(p)))


class CertificateIndex:
    def __init__(
        self,
        width,
        height,
        step,
        north,
        tiles,
        reps,
        tile_cells=1024,
        numerical_guard_m=1000.0,
        refinement=None,
    ):
        if (
            type(width) is not int
            or type(height) is not int
            or width < 2
            or height < 1
            or not math.isfinite(step)
            or step <= 0
            or abs(width * step - 360) > 1e-8
            or north > 90
            or north - height * step < -90 - 1e-8
        ):
            raise ValueError('invalid global grid')
        if (
            type(tile_cells) is not int
            or tile_cells < 1
            or not math.isfinite(numerical_guard_m)
            or numerical_guard_m < 1000
        ):
            raise ValueError('insufficient numerical guard')
        self.w = width
        self.h = height
        self.step = step
        self.north = north
        self.C = tile_cells
        self.guard = numerical_guard_m
        self.refinement = refinement
        if refinement is not None and (
            not isinstance(refinement, CertificateIndex)
            or (refinement.w, refinement.h, refinement.step, refinement.north)
            != (width, height, step, north)
        ):
            raise ValueError('invalid certificate refinement')
        self.trees = {}
        self.radii = {}
        self.reptrees = {}
        self.repcoords = {}
        rep = np.asarray(reps, dtype=np.int64)
        if (
            rep.ndim != 2
            or rep.shape[1] != 3
            or not len(rep)
            or np.any(
                (rep[:, 0] < 0)
                | (rep[:, 0] >= height)
                | (rep[:, 1] < 0)
                | (rep[:, 1] >= width)
                | (rep[:, 2] <= 0)
                | (rep[:, 2] >= 2**32)
            )
        ):
            raise ValueError('invalid representatives')
        self.codes = tuple(map(int, np.unique(rep[:, 2])))
        if refinement is not None and refinement.codes != self.codes:
            raise ValueError("certificate categories differ")
        for code in self.codes:
            positions = []
            rad = []
            for ty, tx, codes in tiles:
                if code not in codes:
                    continue
                if type(ty) is not int or type(tx) is not int or ty < 0 or tx < 0:
                    raise ValueError('invalid tile')
                y0 = ty * tile_cells
                y1 = min(height, y0 + tile_cells)
                x0 = tx * tile_cells
                x1 = min(width, x0 + tile_cells)
                if y0 >= y1 or x0 >= x1:
                    raise ValueError('tile outside grid')
                positions.append((north - (y0 + y1) * step / 2, -180 + (x0 + x1) * step / 2))
                rad.append(((y1 - y0) + (x1 - x0)) * step * math.pi / 360)
            if not positions:
                raise ValueError('missing category tile')
            pos = np.asarray(positions)
            self.trees[code] = cKDTree(_unit(pos[:, 0], pos[:, 1]))
            self.radii[code] = max(rad)
            v = rep[rep[:, 2] == code]
            if not len(v):
                raise ValueError('missing category representative')
            coords = np.column_stack(
                (north - (v[:, 0] + 0.5) * step, -180 + (v[:, 1] + 0.5) * step)
            )
            self.repcoords[code] = coords
            self.reptrees[code] = cKDTree(_unit(coords[:, 0], coords[:, 1]))

    def witnesses(self, rows, cols, hints):
        rows = np.asarray(rows, dtype=np.int64)
        cols = np.asarray(cols, dtype=np.int64)
        hints = np.asarray(hints, dtype=np.int64)
        if (
            rows.ndim != 1
            or len(rows) != len(cols)
            or len(rows) != len(hints)
            or np.any(
                (rows < 0)
                | (rows >= self.h)
                | (cols < 0)
                | (cols >= self.w)
                | ~np.isin(hints, self.codes)
            )
        ):
            raise ValueError('invalid query witnesses')
        lat = self.north - (rows + 0.5) * self.step
        lon = -180 + (cols + 0.5) * self.step
        xyz = _unit(lat, lon)
        upper = np.full(len(rows), np.nan)
        chosen = np.empty((len(rows), 2), dtype=float)
        for code in self.codes:
            k = np.flatnonzero(hints == code)
            if not len(k):
                continue
            _, ix = self.reptrees[code].query(xyz[k], k=1, workers=1)
            p = self.repcoords[code][ix]
            chosen[k] = p
            if len(k) == 1:
                upper[k] = GEOD.inv(
                    float(lon[k[0]]), float(lat[k[0]]), float(p[0, 1]), float(p[0, 0])
                )[2]
            else:
                upper[k] = GEOD.inv(lon[k], lat[k], p[:, 1], p[:, 0])[2]
        if not np.all(np.isfinite(upper)) or np.any(upper < 0):
            raise ValueError('invalid WGS84 upper')
        return upper, chosen

    def certify_runs(self, rows, starts, ends, uppers, hints, tolerance_m):
        rows = np.asarray(rows, dtype=np.int64)
        starts = np.asarray(starts, dtype=np.int64)
        ends = np.asarray(ends, dtype=np.int64)
        uppers = np.asarray(uppers, dtype=float)
        hints = np.asarray(hints, dtype=np.int64)
        n = len(rows)
        if (
            any(z.ndim != 1 or len(z) != n for z in (rows, starts, ends, uppers, hints))
            or not math.isfinite(tolerance_m)
            or tolerance_m < 0
            or np.any(
                (rows < 0)
                | (rows >= self.h)
                | (starts < 0)
                | (starts >= ends)
                | (ends > self.w)
                | ~np.isin(hints, self.codes)
            )
            or not np.all(np.isfinite(uppers))
            or np.any(uppers < 0)
        ):
            raise ValueError('invalid runs or bound')
        lat = self.north - (rows + 0.5) * self.step
        lon = -180 + ((starts + ends - 1) / 2 + 0.5) * self.step
        xyz = _unit(lat, lon)
        qr = (ends - starts - 1) * self.step * math.pi / 360
        return self._certify_points(xyz, qr, uppers, hints, tolerance_m)

    def _certify_points(self, xyz, qr, uppers, hints, tolerance_m, candidates=None):
        # Only this method forwards candidate masks, after its own conservative
        # bounds have ruled out every omitted category. Fine trees therefore never
        # search the faraway continents already excluded by a cheap coarse tree.
        n = len(hints)
        danger = np.zeros((n, len(self.codes)), dtype=bool)
        for column, code in enumerate(self.codes):
            selected = np.flatnonzero(
                (hints != code) if candidates is None else candidates[:, column]
            )
            if not len(selected):
                continue
            chord, _ = self.trees[code].query(xyz[selected], k=1, workers=1)
            limit = (
                (uppers[selected] + self.guard + tolerance_m) / M_MIN
                + self.radii[code]
                + qr[selected]
            )
            danger[selected, column] = (limit >= math.pi) | (
                chord <= 2 * np.sin(np.minimum(math.pi, limit) / 2)
            )
        good = ~danger.any(axis=1)
        if self.refinement is not None:
            selected = np.flatnonzero(~good)
            if len(selected):
                good[selected] = self.refinement._certify_points(
                    xyz[selected],
                    qr[selected],
                    uppers[selected],
                    hints[selected],
                    tolerance_m,
                    danger[selected],
                )
        return good
