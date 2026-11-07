"""Small helpers for WGS84 nearest-cell diagnostics."""
import math

import numpy as np
from pyproj import Geod


GEOD = Geod(ellps='WGS84')


def nearest_cell(point_lonlat, candidates):
    """Return the cell ID nearest a geographic point by WGS84 distance.

    `candidates` contains `(cell_id, lon, lat)` tuples. Exact distance ties
    are resolved by the cell ID ordering so results are deterministic.
    """
    lon, lat = point_lonlat
    if (not math.isfinite(lon) or not math.isfinite(lat)
            or not -180 <= lon <= 180 or not -90 <= lat <= 90):
        raise ValueError('invalid query coordinate')
    values = list(candidates)
    if not values:
        raise ValueError('no candidate cells')
    ids = [value[0] for value in values]
    lons = np.asarray([value[1] for value in values], dtype=float)
    lats = np.asarray([value[2] for value in values], dtype=float)
    if (len(set(ids)) != len(ids) or not np.isfinite(lons).all()
            or not np.isfinite(lats).all() or np.any(np.abs(lons) > 180)
            or np.any(np.abs(lats) > 90)):
        raise ValueError('invalid candidate cells')
    distances = np.asarray(GEOD.inv(np.full(len(values), lon),
                                    np.full(len(values), lat), lons, lats)[2])
    if not np.isfinite(distances).all() or np.any(distances < 0):
        raise ValueError('invalid WGS84 geodesic distance')
    return min(zip(distances.tolist(), ids), key=lambda item: (item[0], item[1]))[1]
