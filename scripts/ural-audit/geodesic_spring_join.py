#!/usr/bin/env python3
"""Replace the modeled spring-pixel snap with WGS84 geodesic chords.

Inputs: canonical SHA-256-pinned GeoJSON LineString and archived OSM relation
XML. The final modeled cell center must be immediately before the unique OSM
spring node. A one-metre maximum interval represents the WGS84 geodesic in
GeoJSON's coordinate-linear segments; endpoints and all other vertices remain
unchanged. Outputs are exclusively created local files.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET
from pyproj import Geod
from shapely.geometry import LineString


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(value).hexdigest()


def build(geom, raw_osm, max_step=1.0):
    if geom.get('type') != 'LineString' or not math.isfinite(max_step) or max_step <= 0:
        raise ValueError('invalid geometry or step')
    root = ET.fromstring(raw_osm)
    relations = [v for v in root.findall('relation') if v.get('id') == '214415' and v.get('version') == '122']
    if len(relations) != 1:
        raise ValueError('expected Ural relation version 122')
    refs = [m.get('ref') for m in relations[0].findall('member') if m.get('type') == 'node' and m.get('role') == 'spring']
    if len(refs) != 1:
        raise ValueError('expected one spring role')
    nodes = [n for n in root.findall('node') if n.get('id') == refs[0]]
    if len(nodes) != 1:
        raise ValueError('missing or duplicate spring node')
    spring = [float(nodes[0].get('lon')), float(nodes[0].get('lat'))]
    coords = geom['coordinates']
    positions = [i for i, p in enumerate(coords) if p == spring]
    if len(positions) != 1 or positions[0] < 1:
        raise ValueError('expected one spring in line')
    i = positions[0]
    start = coords[i-1]
    geod = Geod(ellps='WGS84')
    az, _, length = geod.inv(*start, *spring)
    if not 10 < length < 20:
        raise ValueError('unexpected spring connector length')
    count = math.ceil(length / max_step)
    intermediate = [list(geod.fwd(*start, az, length * j/count)[:2]) for j in range(1, count)]
    new = {'type':'LineString', 'coordinates':coords[:i] + intermediate + coords[i:]}
    if not LineString(new['coordinates']).is_simple:
        raise ValueError('replacement intersects boundary')
    return new, {'schema':'ural-spring-geodesic-join-v1', 'osm_spring_node_id':refs[0], 'start':start, 'end':spring, 'length_wgs84_m':length, 'max_geodesic_step_m':max_step, 'segments':count, 'added_vertices':len(intermediate), 'input_geometry_sha256':digest(canonical(geom)), 'output_geometry_sha256':digest(canonical(new)), 'osm_sha256':digest(raw_osm), 'method':'WGS84 inverse/direct geodesic, represented by coordinate-linear chords with maximum 1m geodesic station spacing'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--geometry',type=Path,required=True);p.add_argument('--geometry-sha256',required=True)
    p.add_argument('--osm',type=Path,required=True);p.add_argument('--osm-sha256',required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--report',type=Path,required=True)
    a=p.parse_args();gb=a.geometry.read_bytes();ob=a.osm.read_bytes();geom=json.loads(gb)
    if digest(canonical(geom)) != a.geometry_sha256 or digest(ob) != a.osm_sha256:
        raise ValueError('input digest mismatch')
    result, report=build(geom,ob)
    if a.geometry.read_bytes()!=gb or a.osm.read_bytes()!=ob:
        raise ValueError('input changed during construction')
    for path, data in ((a.output,canonical(result)+b'\n'),(a.report,canonical(report)+b'\n')):
        with path.open('xb') as f:f.write(data)
    print(json.dumps(report,sort_keys=True))


if __name__=='__main__':main()
