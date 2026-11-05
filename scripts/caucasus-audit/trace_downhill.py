#!/usr/bin/env python3
"""Conservative local D8 trace; not a catchment delineator or a stream map.

See README for assumptions, limitations and input format. Requires GDAL and NumPy.
"""
import argparse
from collections import deque
from functools import lru_cache
import json
import math
from pathlib import Path

import numpy as np
from osgeo import gdal, ogr, osr
from geodesic_tools import GEOD, METHOD, line_sha256


def trace(z, valid, start, transform, flat_limit=0, max_steps=10000):
    """Return pixel path and stopping reason; never route uphill.

    A cell touching invalid or cropped data cannot be resolved conservatively.
    If enabled, a bounded, equal-height component is explored and the nearest
    downhill exit is selected by fewest grid steps, with WGS84 slope as secondary criterion.
    """
    height, width = z.shape
    if len(transform)!=6 or any(not math.isfinite(x) for x in transform) or transform[2]!=0 or transform[4]!=0 or transform[1]<=0 or transform[5]>=0:
        raise ValueError('north-up geographic transform required')
    @lru_cache(maxsize=8192)
    def step_distance(row, dr, dc):
        lat=transform[3]+(row+.5)*transform[5]
        other=transform[3]+(row+dr+.5)*transform[5]
        if not (-90<=lat<=90 and -90<=other<=90):raise ValueError('pixel latitude outside WGS84')
        _,_,metres=GEOD.inv(0,lat,dc*transform[1],other)
        if not math.isfinite(metres) or metres<=0:raise ValueError('invalid geodesic neighbor distance')
        return metres
    r, c = start
    if not (0 <= r < height and 0 <= c < width and valid[r, c]):
        return [], 'invalid_start'
    visited = set()
    path = []
    while len(path) < max_steps:
        if (r, c) in visited:
            return path, 'cycle'
        visited.add((r, c))
        path.append((r, c))
        elevation = int(z[r, c])
        queue = deque([(r, c)])
        previous = {(r, c): None}
        depth = {(r, c): 0}
        exits = []
        uncertain = False
        while queue:
            rr, cc = queue.popleft()
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if not (dr or dc):
                        continue
                    nr, nc = rr + dr, cc + dc
                    if not (0 <= nr < height and 0 <= nc < width and valid[nr, nc]):
                        uncertain = True
                        continue
                    value = int(z[nr, nc])
                    distance = step_distance(rr,dr,dc)
                    if value < elevation:
                        exits.append((depth[(rr, cc)], -(elevation - value) / distance, rr, cc, nr, nc))
                    elif flat_limit and value == elevation and (nr, nc) not in previous:
                        previous[(nr, nc)] = (rr, cc)
                        depth[(nr, nc)] = depth[(rr, cc)] + 1
                        if len(previous) > flat_limit:
                            return path, 'large_flat'
                        queue.append((nr, nc))
        if uncertain:
            return path, 'invalid_neighbor'
        if not exits:
            return path, 'pit_or_flat'
        _, _, rr, cc, nr, nc = min(exits)
        steps = []
        while (rr, cc) != (r, c):
            steps.append((rr, cc))
            rr, cc = previous[(rr, cc)]
        for point in reversed(steps):
            if point in visited:
                return path, 'cycle'
            if len(path) >= max_steps:
                return path, 'step_limit'
            visited.add(point)
            path.append(point)
        r, c = nr, nc
    return path, 'step_limit'


def filter_surface(z, valid, window):
    """Median filter only where every input pixel in the window is valid."""
    if window < 1 or window > 9 or window % 2 == 0:
        raise ValueError('median window must be an odd integer from 1 to 9')
    if window == 1:
        return z, valid
    from scipy.ndimage import median_filter, minimum_filter
    filtered = median_filter(z, size=window, mode='nearest')
    qualified = minimum_filter(valid.astype('u1'), size=window, mode='constant', cval=0).astype(bool)
    return filtered, qualified


def open_tile(spec, median_window=1, center=None, crop_radius=None):
    parts = spec.split(':')
    if len(parts) != 4:
        raise ValueError('tile must be ID:DSM:MSK:STK')
    name, *files = parts
    datasets = [gdal.Open(f, gdal.GA_ReadOnly) for f in files]
    if any(d is None for d in datasets):
        raise ValueError(f'cannot open all rasters for {name}')
    gt = datasets[0].GetGeoTransform()
    projection = datasets[0].GetProjection()
    if any(d.GetGeoTransform() != gt or d.GetProjection() != projection or
           d.RasterXSize != datasets[0].RasterXSize or d.RasterYSize != datasets[0].RasterYSize
           for d in datasets):
        raise ValueError(f'rasters for {name} do not share a grid')
    if gt[2] != 0 or gt[4] != 0 or gt[1] <= 0 or gt[5] >= 0:
        raise ValueError('only north-up geographic rasters are supported')
    if not (abs(gt[1] - 1/3600) < 1e-10 and abs(gt[5] + 1/3600) < 1e-10):
        raise ValueError('expected the original 1-arcsecond JAXA grid')
    srs = osr.SpatialReference(wkt=projection)
    if not srs.IsGeographic() or srs.GetAuthorityCode(None) != '4326':
        raise ValueError('expected WGS 84 (EPSG:4326)')
    if name != f'N{int(gt[3]-1):02d}E{int(gt[0]):03d}':
        raise ValueError('tile ID does not match raster origin')
    if crop_radius is None:
        z, mask, stack = [d.ReadAsArray() for d in datasets]
    else:
        if crop_radius < 1 or center is None:
            raise ValueError('crop radius must be positive and have a center')
        x = math.floor((center[0] - gt[0]) / gt[1])
        y = math.floor((center[1] - gt[3]) / gt[5])
        if not (0 <= x < datasets[0].RasterXSize and 0 <= y < datasets[0].RasterYSize):
            raise ValueError('crop center is outside its tile')
        x0 = max(0, x - crop_radius)
        y0 = max(0, y - crop_radius)
        x1 = min(datasets[0].RasterXSize, x + crop_radius + 1)
        y1 = min(datasets[0].RasterYSize, y + crop_radius + 1)
        z, mask, stack = [d.ReadAsArray(x0, y0, x1-x0, y1-y0) for d in datasets]
        gt = (gt[0] + x0 * gt[1], gt[1], 0, gt[3] + y0 * gt[5], 0, gt[5])
    nodata = datasets[0].GetRasterBand(1).GetNoDataValue()
    valid = (mask == 0) & (stack > 0)
    if nodata is not None:
        valid &= z != nodata
    z, valid = filter_surface(z, valid, median_window)
    return z, valid, gt


def trace_record(profile, section, routes, pairs):
    """Use the already validated document section for every emitted record."""
    return {'distance_method':METHOD,'section':section,'distance_m':profile.get('distance_m'),
            'center':profile.get('center'),'routes':routes,'pairs':pairs}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--profiles', required=True, help='profile JSON produced by ridge_candidates.py')
    p.add_argument('--line', required=True, help='GeoJSON LineString geometry')
    p.add_argument('--tile', action='append', required=True, help='ID:DSM:MSK:STK; repeat per tile')
    p.add_argument('--offsets', nargs='+', type=int, default=[-250, -100, 100, 250])
    p.add_argument('--flat-limit', type=int, default=0, help='0: stop at flats; positive: maximum connected flat cells')
    p.add_argument('--median-window', type=int, default=1, help='odd pixel window for sensitivity check; 1 means no filter')
    p.add_argument('--crop-radius-pixels', type=int, help='read a bounded square around each profile center')
    p.add_argument('--section',type=int,required=True)
    p.add_argument('--start-vertex',type=int,required=True)
    p.add_argument('--end-vertex',type=int,required=True)
    p.add_argument('--output', required=True)
    args = p.parse_args()
    if args.flat_limit < 0:
        p.error('--flat-limit must not be negative')
    if args.crop_radius_pixels is not None and args.crop_radius_pixels < 1:
        p.error('--crop-radius-pixels must be positive')
    tile_specs = {v.split(':', 1)[0]: v for v in args.tile}
    tiles = {} if args.crop_radius_pixels is not None else {k: open_tile(v, args.median_window) for k,v in tile_specs.items()}
    line_data = json.loads(Path(args.line).read_text())
    if line_data.get('type') == 'Feature':
        line_data = line_data['geometry']
    line = ogr.CreateGeometryFromJson(json.dumps(line_data))
    if line is None or line.GetGeometryName() != 'LINESTRING':
        raise ValueError('line must be a GeoJSON LineString')
    results = []
    profile_data = json.loads(Path(args.profiles).read_text())
    if not isinstance(profile_data,dict) or profile_data.get('distance_method')!=METHOD or profile_data.get('source_line_sha256')!=line_sha256(line_data['coordinates']) or profile_data.get('section')!=args.section or profile_data.get('start_vertex')!=args.start_vertex or profile_data.get('end_vertex')!=args.end_vertex or not 0<=args.start_vertex<args.end_vertex<len(line_data['coordinates']):raise ValueError('matching WGS84 source-line profile required')
    profiles=profile_data['samples']
    for profile in profiles:
        results_for_profile = {}
        by_offset = {s['offset_m']: s for s in profile['samples']}
        for offset in args.offsets:
            point = by_offset[offset]
            lon = point.get('longitude', point.get('lon'))
            lat = point.get('latitude', point.get('lat'))
            if lon is None or lat is None:
                results_for_profile[str(offset)] = {'status': 'missing_coordinates', 'path': []}
                continue
            tile = f'N{math.floor(lat):02d}E{math.floor(lon):03d}'
            if tile not in tile_specs:
                results_for_profile[str(offset)] = {'status': 'missing_tile', 'path': []}
                continue
            if args.crop_radius_pixels is not None:
                z, valid, gt = open_tile(tile_specs[tile], args.median_window, profile['center'], args.crop_radius_pixels)
            else:
                z, valid, gt = tiles[tile]
            c, r = int((lon - gt[0]) / gt[1]), int((lat - gt[3]) / gt[5])
            path, status = trace(z, valid, (r, c), gt, flat_limit=args.flat_limit)
            coordinates = [[gt[0] + (cc + .5)*gt[1], gt[3] + (rr + .5)*gt[5]] for rr, cc in path]
            obj = {'status': status, 'path': coordinates, 'start_height_m': int(z[r,c]) if path else None}
            if len(path) > 1:
                geom = ogr.Geometry(ogr.wkbLineString)
                for x,y in coordinates:
                    geom.AddPoint_2D(x,y)
                intersection = geom.Intersection(line)
                obj['crosses_selected'] = not intersection.IsEmpty()
                obj['intersection_wkt'] = intersection.ExportToWkt() if not intersection.IsEmpty() else None
            results_for_profile[str(offset)] = obj
        pairs = {}
        for offset in sorted(x for x in args.offsets if x > 0 and -x in args.offsets):
            a = results_for_profile[str(-offset)]['path']
            b = results_for_profile[str(offset)]['path']
            lookup = {tuple(point): i for i,point in enumerate(a)}
            merge = next(((lookup[tuple(point)], j, point) for j,point in enumerate(b)
                          if tuple(point) in lookup), None)
            pairs[str(offset)] = {'merged': merge is not None, 'merge': merge}
        results.append(trace_record(profile,args.section,results_for_profile,pairs))
    Path(args.output).write_text(json.dumps(results, indent=2))


if __name__ == '__main__':
    gdal.UseExceptions()
    main()
