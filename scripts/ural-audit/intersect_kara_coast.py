#!/usr/bin/env python3
"""Replace a coastal connector with its mapped-coast/watershed intersection.

Inputs are a pinned existing LineString and a pinned OSM XML map capture. The
caller supplies the coastline way ID and the two expected SHA-256 digests.
The old first segment is removed; the new start is the unique intersection of
the following source edge and the mapped coastline. Only local files are written.
"""
import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from pyproj import Geod
from shapely.geometry import LineString, Point


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1048576), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--geometry', type=Path, required=True)
    p.add_argument('--geometry-sha256', required=True, help='canonical compact geometry digest')
    p.add_argument('--osm', type=Path, required=True)
    p.add_argument('--osm-sha256', required=True)
    p.add_argument('--coast-way', required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--report', type=Path, required=True)
    a = p.parse_args()
    raw = a.geometry.read_bytes()
    geom = json.loads(raw)
    canonical = lambda v: json.dumps(v, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    if hashlib.sha256(canonical(geom)).hexdigest() != a.geometry_sha256:
        raise ValueError('geometry digest mismatch')
    if geom.get('type') != 'LineString' or len(geom.get('coordinates', [])) < 3:
        raise ValueError('expected a LineString with at least three positions')
    if sha(a.osm) != a.osm_sha256:
        raise ValueError('OSM input digest mismatch')
    root = ET.parse(a.osm).getroot()
    nodes = {n.get('id'): (float(n.get('lon')), float(n.get('lat'))) for n in root.findall('node')}
    ways = [w for w in root.findall('way') if w.get('id') == a.coast_way]
    if len(ways) != 1 or not any(t.get('k') == 'natural' and t.get('v') == 'coastline' for t in ways[0].findall('tag')):
        raise ValueError('expected exactly one coastline way')
    refs = [n.get('ref') for n in ways[0].findall('nd')]
    if len(refs) < 2 or any(r not in nodes for r in refs):
        raise ValueError('coastline has missing nodes')
    coast = LineString([nodes[r] for r in refs])
    old = geom['coordinates']
    edge = LineString(old[1:3])
    hit = coast.intersection(edge)
    if (not isinstance(hit, Point) or hit.is_empty or edge.length == 0
            or not (0 < edge.project(hit) < edge.length) or edge.distance(hit) > 1e-12):
        raise ValueError('expected one interior intersection with the retained watershed edge')
    start = [hit.x, hit.y]
    new = {'type': 'LineString', 'coordinates': [start] + old[2:]}
    if not LineString(new['coordinates']).is_simple:
        raise ValueError('new line is not simple')
    if sha(a.osm) != a.osm_sha256 or a.geometry.read_bytes() != raw:
        raise ValueError('source changed during derivation')
    g = Geod(ellps='WGS84')
    report = {'schema': 'ural-kara-coast-intersection-v1', 'input_geometry_sha256': a.geometry_sha256,
              'output_geometry_sha256': hashlib.sha256(canonical(new)).hexdigest(),
              'osm_sha256': a.osm_sha256, 'coast_way_id': a.coast_way,
              'old_start': old[0], 'new_start': start,
              'start_shift_wgs84_m': g.inv(*old[0], *start)[2],
              'old_connector_wgs84_m': g.inv(*old[0], *old[1])[2],
              'vertices': len(new['coordinates']),
              'limits': 'Intersection uses coordinate-linear source segments, not a surveyed shoreline; regenerate terminal closure for the new boundary.'}
    for path, data in ((a.output, canonical(new) + b'\n'),
                       (a.report, json.dumps(report, indent=2, sort_keys=True, allow_nan=False).encode() + b'\n')):
        with path.open('xb') as f:
            f.write(data)
    print(json.dumps(report, sort_keys=True))


if __name__ == '__main__':
    main()
