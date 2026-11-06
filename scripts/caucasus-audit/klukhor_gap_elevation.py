"""Compare bridge and current-line terrain samples using WGS84 minima."""
import json

from geodesic_line import GeodesicLine


def paired_sample_points(current_coords, bridge_coords, interval_m=30):
    """Return current/bridge points paired by WGS84 nearest-line location.

    Both inputs retain their coordinate-linear source geometry. The bridge is
    sampled by WGS84 stationing; each sample is matched to the closest point on
    the current line using the WGS84 ellipsoid. Numerically ambiguous nearest
    locations fail closed instead of selecting by coordinate-space distance.
    """
    if type(interval_m) is not int or interval_m <= 0:
        raise ValueError('sample interval must be a positive integer metre')
    current = GeodesicLine(current_coords)
    bridge = GeodesicLine(bridge_coords)
    current_points, bridge_points = [], []
    for station_m in range(0, int(bridge.length) + 1, interval_m):
        bridge_point = bridge.point(float(station_m))
        nearest = current.closest(bridge_point)
        if nearest['ambiguous']:
            raise ValueError('bridge sample has ambiguous WGS84 nearest location')
        current_points.append(nearest['point'])
        bridge_points.append(bridge_point)
    return current_points, bridge_points


def main():
    import numpy as np
    import rasterio

    source = json.load(open('klukhor-gap-old-0-research.json'))['coordinates']
    bridge = json.load(open('klukhor-north-gap-0-research.json'))['coordinates']
    srcpts, altpts = paired_sample_points(source, bridge)
    for name in ('original/N043E041/ALPSMLC30_N043E041_DSM.tif', 'klukhor-cop30-DEM.tif'):
        with rasterio.open(name) as ds:
            a = np.array([x[0] for x in ds.sample(srcpts)], float)
            b = np.array([x[0] for x in ds.sample(altpts)], float)
            valid = np.isfinite(a) & np.isfinite(b) & (a != ds.nodata) & (b != ds.nodata)
            v = (b - a)[valid]
            print(name, 'paired', len(v), 'mean bridge minus current', round(float(v.mean()), 1),
                  'median', round(float(np.median(v)), 1), 'bridge higher', int((v > 0).sum()),
                  'lower', int((v < 0).sum()), 'tie', int((v == 0).sum()))
    base = 'original/N043E041/ALPSMLC30_N043E041_'
    with rasterio.open(base + 'MSK.tif') as ds, rasterio.open(base + 'STK.tif') as st:
        for name, positions in [('current', srcpts), ('bridge', altpts)]:
            m = np.array([int(x[0]) for x in ds.sample(positions)])
            k = np.array([int(x[0]) for x in st.sample(positions)])
            print(name, 'JAXA valid', int(((((m == 0) & (k > 0)) | (m == 48))).sum()), '/',
                  len(positions), 'mask values', dict(zip(*np.unique(m, return_counts=True))))


if __name__ == '__main__':
    main()
