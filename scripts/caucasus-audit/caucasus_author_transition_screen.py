"""Test transition endpoints against the author feature's terminal edges."""
import argparse
import hashlib
import json
from shapely.geometry import LineString, Point
from geodesic_line import GeodesicLine, GEOD

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--selected', required=True)
p.add_argument('--source', required=True)
a = p.parse_args()
with open(a.selected, encoding='utf-8') as f:
    line = json.load(f)
normal = dict(line)
normal['coordinates'] = [[float(v) for v in pt] for pt in line['coordinates']]
canonical = json.dumps(normal, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()
if hashlib.sha256(canonical).hexdigest() != '9f4ae3bc778ebbcd0258a19868acf0fa655763f5e849361196160fb4289c0d52':
    raise ValueError('selected geometry hash mismatch')
with open(a.source, 'rb') as f:
    raw = f.read()
if hashlib.sha256(raw).hexdigest() != 'c9d56b1291522573fbb8b0baa1a39cecfd192eda8f5e51650b24f562d13688e6':
    raise ValueError('author source hash mismatch')
author = json.loads(raw)['features'][463]['geometry']['coordinates']
selected = line['coordinates']
for index, author_index in [(1893, 0), (2291, 397)]:
    point = Point(selected[index])
    source_edge = LineString(author[author_index:author_index+2])
    closest = GeodesicLine(list(source_edge.coords)).closest((point.x, point.y))
    nearest = Point(closest['point'])
    result = {'selected_index': index, 'author_edge_start': author_index,
              'distance_to_wgs84_line_minimum_m': closest['distance_m'],
              'nearest_search_ambiguous': closest['ambiguous'],
              'author_edge_fraction_angular': source_edge.project(nearest, normalized=True)}
    selected_edge = LineString(selected[1893:1895] if index == 1893 else selected[2290:2292])
    for epsilon in [1e-9, 1e-8, 1e-7]:
        remaining = selected_edge.difference(source_edge.buffer(epsilon))
        result['uncovered_m_at_angular_tolerance_' + str(epsilon)] = GEOD.geometry_length(remaining)
    print(json.dumps(result, indent=2))
