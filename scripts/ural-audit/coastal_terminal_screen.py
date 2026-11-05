#!/usr/bin/env python3
"""Research-only coastal connector contact and local loop screen.

Inputs are pinned local excerpts, not a replacement for full topology or grid
validation. Source geometry and grid are never changed.
"""
import argparse
from fractions import Fraction
import hashlib
import importlib.util
import json
import math
import numpy as np
from pyproj import Geod
from shapely.geometry import LineString, Point, Polygon

WIDTH, HEIGHT = 131072, 54614
STEP = Fraction(360, WIDTH)


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def screen(boundary, closure, rows, runs, checker, connector_count):
    if connector_count < 2 or connector_count >= len(boundary) or len(closure) < 2:
        raise ValueError('invalid excerpt or connector length')
    if boundary[0] != closure[0]:
        raise ValueError('boundary and closure do not share their initial terminal')
    def grid(p):
        return ((Fraction(str(p[0])) + 180) / STEP, (90 - Fraction(str(p[1]))) / STEP)
    def contacts(a, b):
        found = []
        for x, y in checker.touched_segment(*grid(a), *grid(b)):
            if not 0 <= x < WIDTH or not 0 <= y < HEIGHT:
                raise ValueError('contact outside grid')
            row = runs[int(rows[y]):int(rows[y+1])]
            if not len(row) or row[-1, 0] != WIDTH:
                raise ValueError('invalid physical row')
            code = int(row[np.searchsorted(row[:, 0], x, side='right'), 1])
            if code not in (1, 17):
                raise ValueError('unexpected physical code')
            found.append([x, y, code])
        return found
    start, a, b = boundary[0], boundary[connector_count - 1], boundary[connector_count]
    if b[1] == a[1]:
        raise ValueError('source edge does not cross terminal latitude uniquely')
    fraction = (start[1] - a[1]) / (b[1] - a[1])
    if not 0 <= fraction <= 1:
        raise ValueError('source edge does not cross terminal latitude')
    rejoin = [a[0] + fraction * (b[0] - a[0]), start[1]]
    ring = Polygon(boundary[:connector_count] + [rejoin])
    if not ring.is_valid or ring.is_empty or ring.area == 0:
        raise ValueError('invalid sensitivity polygon')
    minx, miny, maxx, maxy = ring.bounds
    step = float(STEP)
    xmin, xmax = math.floor((minx + 180) / step), math.floor((maxx + 180) / step)
    ymin, ymax = math.floor((90 - maxy) / step), math.floor((90 - miny) / step)
    if (xmax - xmin + 1) * (ymax - ymin + 1) > 1000000:
        raise ValueError('sensitivity polygon is too large')
    centers = [[x, y] for y in range(ymin, ymax + 1) for x in range(xmin, xmax + 1)
               if ring.covers(Point(-180 + (x + 0.5) * step, 90 - (y + 0.5) * step))]
    intersection = LineString(boundary).intersection(LineString(closure))
    geod = Geod(ellps='WGS84')
    area, _ = geod.geometry_area_perimeter(ring)
    return {'connector_start_to_end_wgs84_m': geod.inv(*start, *a)[2],
            'first_source_edge_wgs84_chord_m': geod.inv(*a, *b)[2],
            'rejoin_lonlat': rejoin, 'terminal_to_rejoin_wgs84_m': geod.inv(*start, *rejoin)[2],
            'sensitivity_polygon_wgs84_chord_area_m2': abs(area), 'native_grid_centers': centers,
            'last_connector_edge_contacts': contacts(boundary[connector_count-2], a),
            'first_source_edge_contacts': contacts(a, b), 'first_closure_edge_contacts': contacts(closure[0], closure[1]),
            'local_intersection_wkt': intersection.wkt,
            'note': 'Only supplied excerpts checked. Reference polygon is a sensitivity construction, not a proposed route. WGS84 chord lengths and area approximate coordinate-linear geometry; no formal error bound.'}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for arg in ('boundary', 'closure', 'rows', 'runs', 'checker', 'boundary-sha', 'closure-sha', 'rows-sha', 'runs-sha', 'checker-sha', 'output'):
        p.add_argument('--' + arg, required=True)
    p.add_argument('--connector-count', type=int, required=True)
    a = p.parse_args()
    inputs = {'boundary': a.boundary, 'closure': a.closure, 'rows': a.rows, 'runs': a.runs, 'checker': a.checker}
    expected = {'boundary': a.boundary_sha, 'closure': a.closure_sha, 'rows': a.rows_sha, 'runs': a.runs_sha, 'checker': a.checker_sha}
    if any(sha(inputs[k]) != expected[k] for k in inputs):
        raise ValueError('input checksum mismatch')
    with open(a.boundary) as f:
        boundary = json.load(f)
    with open(a.closure) as f:
        closure = json.load(f)
    spec = importlib.util.spec_from_file_location('closure_checker', a.checker)
    checker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)
    rows = np.memmap(a.rows, mode='r', dtype='<u4')
    runs = np.memmap(a.runs, mode='r', dtype='<u4').reshape(-1, 2)
    if len(rows) != HEIGHT + 1 or rows[0] != 0 or rows[-1] != len(runs):
        raise ValueError('invalid row index')
    result = screen(boundary, closure, rows, runs, checker, a.connector_count)
    if any(sha(inputs[k]) != expected[k] for k in inputs):
        raise ValueError('input changed during screen')
    result['input_sha256'] = expected
    with open(a.output, 'x') as f:
        json.dump(result, f, indent=2)
    print(json.dumps(result))
