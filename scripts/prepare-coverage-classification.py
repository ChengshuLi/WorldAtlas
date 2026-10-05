"""Prepare sparse physical-reference classification on the unchanged canonical grid.

No dense world bitmap, location geometry, political affiliation or DB writes.
Class1=reference land,2=major reference water,0=unknown. Blocked reference tiles
are carved out before packing. Reference classes express source support, not certified hydrology or ownership.
"""
import argparse
import array
import io
import gzip
import hashlib
import json
import math
import pathlib
import resource
import subprocess
import sys
import time

import numpy as np
from shapely.geometry import box, shape

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from evidence.immutable import Baseline, descriptor, deterministic_gzip, canonical_json

LAND_ROOT = 'data/macro-foundation/retained-inspections/retained-geographic-sources/namibia/'
WATER_ROOT = 'coordination/engineering/coverage-gaps-907-20261005-local01/sources/'
MAX_DECODED = 32 * 1024 * 1024

def decode_gzip(raw):
    with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
        decoded = stream.read(MAX_DECODED + 1)
    if len(decoded) > MAX_DECODED:
        raise ValueError('Reference decompression exceeds budget')
    return decoded

def verify(raw, expected):
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError('Reference source checksum mismatch')


def reader(commit, first):
    raw = subprocess.check_output(['git', '-C', str(ROOT), 'show', commit + ':' + first])
    return Baseline(ROOT, commit, [descriptor(first, raw)])


def project(ring, size):
    xy = np.asarray(ring.coords)
    if xy.shape[1] != 2:
        raise ValueError('Expected 2D longitude/latitude')
    lat = np.clip(xy[:, 1], -85.05112878, 85.05112878)
    s = np.sin(lat * math.pi / 180)
    return np.column_stack(((xy[:, 0] + 180) / 360 * size,
                            (.5 - np.log((1+s)/(1-s)) / (4*math.pi)) * size))


def add_polygon(spans, polygon, kind, size):
    edges = []
    for ring in [polygon.exterior, *polygon.interiors]:
        xy = project(ring, size)
        for (x1, y1), (x2, y2) in zip(xy[:-1], xy[1:]):
            if y1 == y2:
                continue
            first = max(0, math.ceil(min(y1, y2) - .5))
            end = min(size, math.ceil(max(y1, y2) - .5))
            if first < end:
                edges.append((first, end, x1, y1, (x2-x1)/(y2-y1)))
    edges.sort(key=lambda e: e[0])
    next_edge, active = 0, []
    row = edges[0][0] if edges else size
    while row < size and (active or next_edge < len(edges)):
        active = [e for e in active if e[1] > row]
        while next_edge < len(edges) and edges[next_edge][0] == row:
            active.append(edges[next_edge])
            next_edge += 1
        xs = sorted(e[2] + (row+.5-e[3]) * e[4] for e in active)
        if len(xs) % 2:
            raise ValueError('Odd reference intersections; never infer a fill')
        for a, b in zip(xs[::2], xs[1::2]):
            start, end = max(0, math.ceil(a-.5)), min(size, math.ceil(b-.5))
            if start < end:
                spans[row].extend((start, end, kind))
        row += 1
        if not active and next_edge < len(edges):
            row = max(row, edges[next_edge][0])


def pieces(g):
    if g.geom_type == 'Polygon':
        if not g.is_empty and g.area > 0:
            yield g
    elif hasattr(g, 'geoms'):
        for child in g.geoms:
            yield from pieces(child)


def compile_runs(spans, size):
    rows, runs = array.array('I'), array.array('I')
    bits = math.ceil(math.log2(size))
    cells = [0, 0, 0]
    for y, row in enumerate(spans):
        offset = len(runs) // 2
        events = []
        for k in range(0, len(row), 3):
            start, end, kind = row[k:k+3]
            events.extend(((start, 1, kind), (end, -1, kind)))
        events.sort()
        active, previous, k, merged = [0, 0, 0, 0], 0, 0, []
        while k < len(events):
            x = events[k][0]
            kind = 3 if active[3] else 2 if active[2] else 1 if active[1] else 0
            if previous < x and kind in (1, 2):
                if merged and merged[-1][1] == previous and merged[-1][2] == kind:
                    merged[-1][1] = x
                else:
                    merged.append([previous, x, kind])
            while k < len(events) and events[k][0] == x:
                _, change, kind = events[k]
                active[kind] += change
                k += 1
            if any(n < 0 for n in active):
                raise ValueError('Unbalanced reference intervals')
            previous = x
        if any(active):
            raise ValueError('Unclosed reference intervals')
        for start, end, kind in merged:
            runs.extend(((kind << bits) | start, end-1))
            cells[kind] += end-start
        rows.extend((offset, len(merged)))
        spans[y] = None
    return rows, runs, cells, bits


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--geography-commit', required=True)
    parser.add_argument('--water-commit')
    parser.add_argument('--out', type=pathlib.Path, required=True)
    args = parser.parse_args()
    args.water_commit = args.water_commit or args.geography_commit
    out = args.out.resolve()
    if out.exists():
        raise FileExistsError('Preserve existing classification; choose a new output')
    if not out.is_relative_to(ROOT) or any(p.is_symlink() for p in [args.out, *args.out.parents]):
        raise ValueError('Output must be an ordinary directory inside this checkout')
    started = time.monotonic()
    geo = reader(args.geography_commit, 'data/canonical-grid/manifest.json')
    grid = json.loads(geo.read('data/canonical-grid/manifest.json'))
    size = grid['size']
    if grid.get('version') != 2 or not isinstance(size, int) or size < 2 or size > 300000:
        raise ValueError('Unsupported canonical grid; require compact bounded grid')
    grid_raw = geo.read('data/canonical-grid/manifest.json')
    release_index = json.loads(geo.read('data/geographic-releases/index.json'))
    pointer_path = 'data/geographic-releases/current-manifest.json'
    exists = subprocess.run(['git','-C',str(ROOT),'cat-file','-e',args.geography_commit+':'+pointer_path], capture_output=True).returncode == 0
    if exists:
        pointer = json.loads(geo.read(pointer_path))
        verify(geo.read('data/geographic-releases/index.json'), pointer['predecessor_index_sha256'])
        name = pointer['path']
        if '/' in name or not name.endswith('.json.gz'):
            raise ValueError('Unsafe release manifest pointer')
        encoded = geo.read('data/geographic-releases/'+name)
        verify(encoded, pointer['sha256'])
        release_index = json.loads(decode_gzip(encoded))
    release = release_index['releases'][-1]
    if any(release[key] != grid[key] for key in ('footprints_sha256','hierarchy_sha256')):
        raise ValueError('Release and canonical grid mismatch')
    spans = [array.array('I') for _ in range(size)]
    land_receipt = json.loads(decode_gzip(geo.read(LAND_ROOT+'manifest.json.gz')))
    source = next(s for s in land_receipt['sources'] if s['path']=='natural-earth-land.geojson.gz')
    inner = decode_gzip(geo.read(LAND_ROOT+'natural-earth-land.geojson.gz.gz'))
    verify(inner, source['retained_sha256'])
    raw = decode_gzip(inner)
    verify(raw, source['original_sha256'])
    land = json.loads(raw)
    water_reader = reader(args.water_commit, WATER_ROOT+'receipt.json')
    receipt = json.loads(water_reader.read(WATER_ROOT+'receipt.json'))
    encoded = water_reader.read(WATER_ROOT+'natural-earth-lakes.geojson.gz')
    verify(encoded, receipt['retained_sha256'])
    water_raw = decode_gzip(encoded)
    verify(water_raw, receipt['original_sha256'])
    water = json.loads(water_raw)
    domain = box(-180, -60, 180, 85.0511287798066)
    bad = []
    count = 0
    for kind, data in [(1, land), (2, water)]:
        for f in data['features']:
            g = shape(f['geometry'])
            if not g.is_valid:
                if kind == 1:
                    raise ValueError('Invalid land reference')
                bad.append(g.bounds)
                continue
            for polygon in pieces(g.intersection(domain)):
                add_polygon(spans, polygon, kind, size)
                count += 1
                if count % 1000 == 0:
                    print(json.dumps({'polygons': count}), flush=True)
    blocked = set()
    for west, south, east, north in bad:
        for x in range(math.floor((west+180)/5), math.floor((east+180)/5)+1):
            for y in range(math.floor((south+60)/5), math.floor((north+60)/5)+1):
                blocked.add((x*5-180, y*5-60, x*5-175, y*5-55))
    for bounds in sorted(blocked):
        add_polygon(spans, box(*bounds).intersection(domain), 3, size)
    rows, runs, cells, bits = compile_runs(spans, size)
    out.mkdir(parents=True, exist_ok=False)
    parts = []
    for kind, values in [('rows', rows), ('runs', runs)]:
        values = np.asarray(values, dtype='<u4')
        for offset in range(0, len(values), 1048576):
            part = values[offset:offset+1048576]
            raw = part.tobytes()
            shuffled = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 4).T.tobytes()
            encoded = deterministic_gzip(shuffled)
            name = f'{kind}-{offset}.bin.gz'
            (out/name).write_bytes(encoded)
            parts.append({'kind':kind,'offset':offset,'words':len(part),'path':'coverage-classification/'+name,'encoding':'byte-shuffle','sha256':hashlib.sha256(encoded).hexdigest(),'decoded_sha256':hashlib.sha256(raw).hexdigest(),'compressed_bytes':len(encoded)})
    manifest = {'kind':'physical-reference-classification','classification_version':1,
                'release_id':release['id'],'geography_commit':args.geography_commit,'water_commit':args.water_commit,
                'canonical_grid_sha256':hashlib.sha256(grid_raw).hexdigest(),
                'classes':{'1':'reference-land','2':'reference-major-water'},
                'sources':[{'name':'Natural Earth 1:10m land','url':source['url'] if 'url' in source else 'https://www.naturalearthdata.com/downloads/10m-physical-vectors/10m-land/','original_sha256':source['original_sha256']},
                           {'name':'Natural Earth 1:10m lakes','url':'https://www.naturalearthdata.com/downloads/10m-physical-vectors/10m-lakes/','original_sha256':receipt['original_sha256']}],
                'domain':[-180,-60,180,85.0511287798066],
                'version':2,'coordinateBits':bits,'size':size,'runWords':len(runs),'parts':parts,
                'footprints_sha256':grid['footprints_sha256'],'hierarchy_sha256':grid['hierarchy_sha256'],
                'land_cells':cells[1],'major_water_cells':cells[2],'blocked_tiles':sorted(blocked),
                'note':'Modern coarse physical references; smaller rivers, lakes and shoreline differences remain uncertain. Classification changes no location ID or boundary.'}
    (out/'manifest.json').write_bytes(canonical_json(manifest))
    print(json.dumps({'runWords':len(runs),'land_cells':cells[1],'major_water_cells':cells[2],'seconds':time.monotonic()-started,'peak_rss_native':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}), flush=True)


if __name__ == '__main__':
    main()
