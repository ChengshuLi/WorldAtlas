"""Screen ordered line edges against coordinate-linear HydroBASINS rings.

The angular buffer is a numerical tolerance, not a geodesic distance or a
source-provenance claim. Uncovered lengths are WGS84 inverse chord sums.
"""
import argparse
import hashlib
import json
import shapefile
from pyproj import Geod
from shapely.geometry import LineString
from shapely.ops import unary_union
from shapely.strtree import STRtree

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--selected', required=True)
p.add_argument('--shp', required=True)
p.add_argument('--output', required=True)
p.add_argument('--angular-tolerance', type=float, default=1e-8)
a = p.parse_args()
with open(a.selected, encoding='utf-8') as f:
    line = json.load(f)
normal = dict(line)
normal['coordinates'] = [[float(v) for v in pt] for pt in line['coordinates']]
canonical = json.dumps(normal, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()
if hashlib.sha256(canonical).hexdigest() != '9f4ae3bc778ebbcd0258a19868acf0fa655763f5e849361196160fb4289c0d52':
    raise ValueError('selected line hash mismatch')
h = hashlib.sha256()
with open(a.shp, 'rb') as f:
    for chunk in iter(lambda:f.read(1024*1024), b''):
        h.update(chunk)
if h.hexdigest() != 'aad745e7f15498fc99c34ad9ffc16271ec927cd1e3c223794747220a4dbe2203':
    raise ValueError('source shp hash mismatch')
if not 0 < a.angular_tolerance <= 1e-6:
    raise ValueError('invalid angular tolerance')
rings = []
for geom in shapefile.Reader(shp=a.shp).iterShapes():
    x0,y0,x1,y1 = geom.bbox
    if x1 < 37 or x0 > 51 or y1 < 39 or y0 > 46:
        continue
    parts = list(geom.parts) + [len(geom.points)]
    for begin, end in zip(parts, parts[1:]):
        if end-begin >= 2:
            rings.append(LineString(geom.points[begin:end]))
tree = STRtree(rings)
geod = Geod(ellps='WGS84')
records = []
for i, (left,right) in enumerate(zip(line['coordinates'],line['coordinates'][1:])):
    edge = LineString([left,right])
    indices = tree.query(edge.buffer(a.angular_tolerance))
    if len(indices):
        cover = unary_union([rings[int(j)].buffer(a.angular_tolerance) for j in indices])
        missing = edge.difference(cover)
    else:
        missing = edge
    records.append({'edge_start_index': i, 'fully_covered_at_tolerance': missing.is_empty,
                    'uncovered_wgs84_chord_m': geod.geometry_length(missing)})
with open(a.output,'x',encoding='utf-8') as f:
    json.dump({'angular_tolerance_degrees':a.angular_tolerance,'edges':records},f,indent=2)
for begin,end in [(0,1893),(1893,1894),(1894,2290),(2290,2291)]:
    subset=records[begin:end]
    print(begin,end,'edges',len(subset),'covered',sum(x['fully_covered_at_tolerance'] for x in subset),
          'uncovered_m',round(sum(x['uncovered_wgs84_chord_m'] for x in subset),3))
