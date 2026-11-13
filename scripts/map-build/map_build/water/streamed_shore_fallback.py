"""Exact WGS84 nearest participant using all full-shore points in blocks.

No full-shore spatial index is built. Each full-source point is visited; a
conservative chord lower bound prunes only inverse calls that cannot improve
the current exact WGS84 upper bound. Research only, dedicated stable inputs.
"""

import math
import numpy as np
from map_build.water import shared_nearest as s


def classify_one(
    lat,
    lon,
    full_bounds,
    width,
    height,
    step,
    pairs,
    tolerance,
    full_blocks,
    narrow_indexes,
    block=65536,
):
    if not (
        math.isfinite(lat)
        and math.isfinite(lon)
        and abs(lat) <= 90
        and abs(lon) <= 180
        and math.isfinite(tolerance)
        and tolerance >= 0
        and type(block) is int
        and block > 0
        and type(width) is int
        and type(height) is int
        and width > 0
        and height > 0
        and math.isfinite(step)
        and step > 0
        and abs(step * width - 360) <= 1e-8
        and pairs
    ):
        raise ValueError('invalid query or parameters')
    x0, x1, y0, y1 = full_bounds
    if not (0 < x1 - x0 <= width and 0 <= y0 < y1 <= height):
        raise ValueError('invalid crop')
    y = (90 - lat) / step
    x = (lon + 180) / step
    x += math.ceil((x0 - x) / width) * width
    if y < y0 - 1e-8 or y > y1 + 1e-8 or x < x0 - 1e-8 or x > x1 + 1e-8:
        raise ValueError('query lies outside crop')
    point = s.unit(np.asarray([lat]), np.asarray([lon]))[0]
    boundary = float(
        s.boundary_lower(np.asarray([lat]), np.asarray([lon]), full_bounds, width, height, step)[0]
    )
    distances = []
    for _, lc, _ in pairs:
        best = math.inf
        found = False
        if lc in narrow_indexes:
            nd, tree = narrow_indexes[lc]
            _, idx = tree.query(point, k=1, workers=1)
            best = float(s.geodesic_distances([lon], [lat], [nd['lon'][idx]], [nd['lat'][idx]])[0])
            if not math.isfinite(best):
                raise ValueError('invalid inverse geodesic')
        for data in full_blocks(lc):
            n = len(data['lat'])
            found |= n > 0
            if data['lon'].shape != (n,) or data['mids'].shape != (n, 3):
                raise ValueError('invalid full shore block')
            for first in range(0, n, block):
                last = min(first + block, n)
                diff = data['mids'][first:last] - point
                chord = np.sqrt(np.sum(diff * diff, axis=1))
                lower = np.maximum(0, s.MIN_RADIUS * chord - 0.01)
                ids = np.flatnonzero(lower <= best + 0.000001) + first
                if len(ids):
                    ds = s.geodesic_distances(
                        np.full(len(ids), lon),
                        np.full(len(ids), lat),
                        data['lon'][ids],
                        data['lat'][ids],
                    )
                    if np.any(~np.isfinite(ds)):
                        raise ValueError('invalid inverse geodesic')
                    best = min(best, float(np.min(ds)))
        if not found:
            raise ValueError('missing participant shore')
        distances.append(best)
    minimum = min(distances)
    if not math.isfinite(minimum):
        raise RuntimeError('no provable candidate shore')
    if minimum + tolerance + 0.000001 >= boundary:
        raise ValueError('crop cannot certify nearest shore; increase halo')
    for i, d in enumerate(distances):
        if math.isfinite(d) and abs((d - minimum) - tolerance) <= 0.0000001:
            raise RuntimeError('tie threshold numerically ambiguous')
        if d <= minimum + tolerance:
            return pairs[i][2]
    raise RuntimeError('no provable candidate shore')
