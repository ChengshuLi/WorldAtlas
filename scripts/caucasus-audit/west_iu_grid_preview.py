"""Compare two provisional registrations of the 1941 L-37-125 sheet.

The grid interpretation assumes Bessel 1841 and zone 7, but the actual sheet
datum and a transformation to WGS84 have not been established. This is an
uncertainty screen, not an analytical georeference.
"""
import json
import numpy as np
from pyproj import Transformer


def main():
    # Approximate grid-line centre positions detected over a 3,000-pixel-wide
    # crop: their spread includes line width, scan distortion and local detail.
    x = np.array([5247, 5728, 6196, 6683, 7143, 7629], dtype=float)
    e = np.array([7440, 7442, 7444, 7446, 7448, 7450], dtype=float) * 1000
    y = np.array([1780, 2244, 2705, 3180, 3664], dtype=float)
    n = np.array([4944, 4942, 4940, 4938, 4936], dtype=float) * 1000
    xf, yf = np.polyfit(e, x, 1), np.polyfit(n, y, 1)
    lon, lat = 38.31791666666666, 44.59583333333336
    old = np.array([670.5 + (lon - 38.0) * (10062 - 670.5) / .5,
                    902.9 + (44 + 40/60 - lat) * (9806 - 902.9) / (20/60)])
    positions = {}
    for ellipsoid in ('bessel', 'krass'):
        crs = ('+proj=tmerc +lat_0=0 +lon_0=39 +k=1 +x_0=7500000 '
               '+y_0=0 +ellps=' + ellipsoid + ' +units=m +no_defs')
        east, north = Transformer.from_crs('EPSG:4326', crs, always_xy=True).transform(lon, lat)
        point = np.array([np.polyval(xf, east), np.polyval(yf, north)])
        positions[ellipsoid] = {'pixel': point.tolist(),
                                'distance_from_corner_fit_pixels': float(np.linalg.norm(point - old))}
    print(json.dumps({'corner_fit_pixel': old.tolist(), 'hypotheses': positions,
                      'grid_x_residual_pixels': (x - np.polyval(xf, e)).tolist(),
                      'grid_y_residual_pixels': (y - np.polyval(yf, n)).tolist(),
                      'caveat': 'Assumed ellipsoid and grid; no datum transform or independent controls.'},
                     sort_keys=True, indent=2))


if __name__ == '__main__':
    main()
