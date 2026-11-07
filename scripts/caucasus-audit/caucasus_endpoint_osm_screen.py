"""Measure to a specified complete OSM coast way, in a local extract only."""
import argparse
import json
import xml.etree.ElementTree as ET
from shapely.geometry import LineString, Point
from geodesic_line import GeodesicLine

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--line', required=True)
p.add_argument('--osm', required=True)
p.add_argument('--way', required=True)
p.add_argument('--index', required=True, type=int)
a = p.parse_args()
coords = json.load(open(a.line, encoding='utf-8'))['coordinates']
point = Point(coords[a.index])
root = ET.parse(a.osm).getroot()
nodes = {n.get('id'): (float(n.get('lon')), float(n.get('lat'))) for n in root.findall('node')}
ways = [w for w in root.findall('way') if w.get('id') == a.way]
if len(ways) != 1:
    raise ValueError('missing or duplicate OSM way')
way = ways[0]
tags = {t.get('k'): t.get('v') for t in way.findall('tag')}
if tags.get('natural') != 'coastline':
    raise ValueError('specified way is not tagged coastline')
refs = [nd.get('ref') for nd in way.findall('nd')]
shape = LineString([nodes[ref] for ref in refs])
closest = GeodesicLine(list(shape.coords)).closest((point.x, point.y))
near = closest['point']
print(json.dumps({'index': a.index, 'way': a.way, 'version': way.get('version'),
                  'timestamp': way.get('timestamp'), 'nearest': [near[0],near[1]],
                  'wgs84_geodesic_line_distance_m': closest['distance_m'],
                  'nearest_search_ambiguous': closest['ambiguous']}, indent=2))
