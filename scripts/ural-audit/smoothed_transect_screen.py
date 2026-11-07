#!/usr/bin/env python3
"""Compare local-edge and windowed transects using modeled drainage roots.

All coordinates and offsets are WGS84. Source route geometry is preserved;
windowed directions are sensitivity checks, not surveyed crest directions.
"""
import argparse
import json
import math
import numpy as np
import rasterio
from rasterio.warp import transform_bounds
from pyproj import Transformer
from shapely.geometry import LineString, Point
from shapely.strtree import STRtree
from priority_d8 import drainage
from projected_route import GEOD, ProjectedRoute
from terrain_basin_screen import checked_shapes, digest_file


def screen(dem, dem_sha, basins, line, line_sha, spacing, windows, offsets):
    if spacing <= 0 or not windows or any(x <= 0 for x in windows) or any(x <= 0 for x in offsets):
        raise ValueError('spacing, windows and offsets must be positive')
    with open(line, 'rb') as f:
        if digest_file(f) != line_sha:
            raise ValueError('line hash mismatch')
    with open(line) as f:
        coordinates = json.load(f)
    with open(dem, 'rb') as f:
        if digest_file(f) != dem_sha:
            raise ValueError('DEM hash mismatch')
    with rasterio.open(dem) as ds:
        z = ds.read(1).astype('float64')
        valid = np.isfinite(z) & (ds.read_masks(1) != 0)
        if ds.nodata is not None and np.isfinite(ds.nodata):
            valid &= z != ds.nodata
        transform, crs = ds.transform, ds.crs
        bounds = transform_bounds(crs, 'EPSG:4326', *ds.bounds, densify_pts=21)
    features = []
    for archive, sha, shp in basins:
        features.extend(checked_shapes(archive, sha, shp, bounds))
    if not features:
        raise ValueError('no basin features in crop')
    geoms = [x[0] for x in features]
    tree = STRtree(geoms)
    roots, _, _ = drainage(z, valid, transform, crs)
    to_grid = Transformer.from_crs(4326, crs, always_xy=True)
    to_geo = Transformer.from_crs(crs, 4326, always_xy=True)
    route = ProjectedRoute(coordinates, crs)
    source = LineString([to_grid.transform(*p) for p in coordinates])
    if not source.is_simple:
        raise ValueError('source route must be simple')
    cache = {}
    def sample(lon, lat):
        row, col = rasterio.transform.rowcol(transform, *to_grid.transform(lon, lat))
        if not (0 <= row < z.shape[0] and 0 <= col < z.shape[1]) or not valid[row, col]:
            return None
        index = int(roots[row, col])
        if index < 0:
            return None
        if index not in cache:
            rr, cc = divmod(index, z.shape[1])
            outlet = to_geo.transform(*rasterio.transform.xy(transform, rr, cc))
            point = Point(*outlet)
            root_ids = sorted({features[i][1] for i in tree.query(point) if geoms[i].covers(point)})
            cache[index] = {'outlet_lonlat': list(outlet), 'main_basins': root_ids}
        return {'root_index': index, 'main_basins': cache[index]['main_basins'],
                'outlet_lonlat': cache[index]['outlet_lonlat'], 'elevation': float(z[row, col])}
    results = []
    for station in np.arange(spacing, route.length - max(windows) + 1e-7, spacing):
        station = float(station)
        if station < max(windows):
            continue
        lon, lat, edge_azimuth = route.point(station)
        directions = [('edge', edge_azimuth)]
        for window in windows:
            before = route.point(station - window)[:2]
            after = route.point(station + window)[:2]
            azimuth, _, distance = GEOD.inv(*before, *after)
            if not math.isfinite(distance) or distance <= 0:
                raise ValueError('undefined window direction')
            directions.append((str(window), azimuth))
        entries = []
        for mode, azimuth in directions:
            for offset in offsets:
                points = [GEOD.fwd(lon, lat, azimuth - 90, sign * offset)[:2] for sign in (-1, 1)]
                samples = [sample(*p) for p in points]
                count = math.ceil(2 * offset / 5)
                transect = LineString([to_grid.transform(*GEOD.fwd(lon, lat, azimuth - 90, -offset + 2 * offset * i / count)[:2]) for i in range(count + 1)])
                crossing = source.intersection(transect)
                pieces = [crossing] if crossing.geom_type == 'Point' else list(getattr(crossing, 'geoms', []))
                if any(p.geom_type != 'Point' for p in pieces) or (not pieces and not crossing.is_empty):
                    raise ValueError('unsupported route/transect overlap')
                entries.append({'mode': mode, 'azimuth_degrees': azimuth, 'offset_wgs84_m': offset,
                                'samples': samples, 'crossing_count': len(pieces)})
        results.append({'station_wgs84_m': station, 'lonlat': [lon, lat], 'directions': entries})
    return {'dem_sha256': dem_sha, 'line_sha256': line_sha, 'station_spacing_wgs84_m': spacing,
            'window_half_lengths_wgs84_m': windows, 'offsets_wgs84_m': offsets,
            'route_length_wgs84_m_approx': route.length, 'stations': results,
            'caveat': 'Local D8 and HydroBASINS crosswalk are modeled, not ground truth; WGS84 transects and projected-linear route use chord approximations with no formal error bound. Windowed directions do not replace source geometry.'}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dem', required=True)
    p.add_argument('--dem-sha', required=True)
    p.add_argument('--line', required=True)
    p.add_argument('--line-sha', required=True)
    p.add_argument('--basin', nargs=3, action='append', required=True)
    p.add_argument('--spacing', type=float, default=250)
    p.add_argument('--window', type=float, action='append', required=True)
    p.add_argument('--offset', type=float, action='append', required=True)
    p.add_argument('--output', required=True)
    a = p.parse_args()
    result = screen(a.dem, a.dem_sha, a.basin, a.line, a.line_sha, a.spacing, a.window, a.offset)
    with open(a.output, 'x') as f:
        json.dump(result, f, indent=2)
    print(json.dumps({'station_count': len(result['stations']), 'status': 'research only'}))
