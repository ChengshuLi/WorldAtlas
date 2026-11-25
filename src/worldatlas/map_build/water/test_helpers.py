"""Build small grids and shore lookup tables for water assignment tests."""

import numpy as np
from scipy.spatial import cKDTree

from worldatlas.geodesy.wgs84 import unit_sphere
from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.division.shores import ShoreGeometry
from worldatlas.map_build.water.shared_nearest import classify_wgs84


def rle(array):
    rows = [0]
    runs = []
    for row in array:
        for i, x in enumerate(row):
            if i == len(row) - 1 or row[i + 1] != x:
                runs.extend((i + 1, int(x)))
        rows.append(len(runs) // 2)
    return np.array(rows, dtype='<u4'), np.array(runs, dtype='<u4')


def index_present(centers, owners):
    indices = {}
    if not len(centers['mids']):
        return indices
    for lc in owners:
        m = centers['category'] == lc
        if np.any(m):
            part = {k: centers[k][m] for k in ('mids', 'lat', 'lon', 'category')}
            indices[lc] = (part, cKDTree(part['mids']))
    return indices

def classify_points(*args, **kwargs):
    """Expose the two point-count metrics through the rectangle test callback."""
    values, stats = classify_wgs84(*args, **kwargs)
    return values, stats["bounded"], stats["exact"]


def production_shore_centers(physical, land, bounds, step, owners):
    height, width = physical.shape
    geometry = ShoreGeometry(rle(physical), Grid(width, height, step))
    shores = geometry.attach(rle(land), owners)
    return shores.centers_for_crop(bounds, step, owners)


def dense_shore_centers(physical, land, bounds, step, owners):
    """Independently enumerate the shore cells in a small dense test grid."""
    x0, x1, y0, y1 = bounds
    height, width = physical.shape
    cells = []
    for y in range(y0, y1):
        for x in range(x0, x1):
            column = x % width
            owner = land[y, column]
            if physical[y, column] != 17 or owner not in owners:
                continue
            neighbors = ((y, x - 1), (y, x + 1), (y - 1, x), (y + 1, x))
            if any(0 <= row < height and physical[row, col % width] == 1
                   for row, col in neighbors):
                cells.append((y, x, owner))
    if not cells:
        raise ValueError("no participant shorelines in crop")
    y, x, categories = np.asarray(cells).T
    lat = 90 - (y + 0.5) * step
    lon = ((-180 + (x + 0.5) * step + 180) % 360) - 180
    return {"mids": unit_sphere(lat, lon), "lat": lat, "lon": lon, "category": categories}
