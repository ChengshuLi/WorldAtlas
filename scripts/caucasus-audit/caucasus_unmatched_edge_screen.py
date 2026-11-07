"""Screen unmatched vertices against a bounded HydroBASINS edge subset.

The reported minimum is WGS84 distance to coordinate-linear edges within the
local candidate subset; the bounding-box prefilter is a screen, not proof of a
global nearest edge.
"""
import json
import hashlib
import argparse
import shapefile
from collections import defaultdict
from shapely.geometry import LineString, Point
from geodesic_line import GeodesicLine, closest_line

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--selected', required=True)
p.add_argument('--shp', required=True)
p.add_argument('--output', required=True, help='new private result file')
args = p.parse_args()
line = json.load(open(args.selected, encoding='utf-8'))
normal = dict(line)
normal['coordinates'] = [[float(v) for v in pt] for pt in line['coordinates']]
blob = json.dumps(normal, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()
if hashlib.sha256(blob).hexdigest() != '9f4ae3bc778ebbcd0258a19868acf0fa655763f5e849361196160fb4289c0d52':
    raise ValueError('line digest mismatch')
source = args.shp
with open(source, 'rb') as f:
    if hashlib.sha256(f.read()).hexdigest() != 'aad745e7f15498fc99c34ad9ffc16271ec927cd1e3c223794747220a4dbe2203':
        raise ValueError('source digest mismatch')
points = line['coordinates']
positions = defaultdict(list)
for i, p in enumerate(points):
    positions[tuple(p)].append(i)
reader = shapefile.Reader(shp=source)
matched = set()
for geom in reader.iterShapes():
    x0,y0,x1,y1 = geom.bbox
    if x1 < 37 or x0 > 51 or y1 < 39 or y0 > 46:
        continue
    for p in geom.points:
        matched.update(positions.get(p, ()))
unmatched = [i for i in range(len(points)) if i not in matched and not 1894 <= i <= 2290]
source_shapes = []
for geom in reader.iterShapes():
    x0,y0,x1,y1 = geom.bbox
    if not any(x0-.03 <= points[i][0] <= x1+.03 and y0-.03 <= points[i][1] <= y1+.03 for i in unmatched):
        continue
    bounds = list(geom.parts) + [len(geom.points)]
    for begin, end in zip(bounds, bounds[1:]):
        if end-begin >= 2:
            source_shapes.append(LineString(geom.points[begin:end]))
source_lines = [GeodesicLine(list(shape.coords)) for shape in source_shapes]
records = []
for i in unmatched:
    pt = Point(points[i])
    closest = closest_line(source_lines, (pt.x, pt.y))
    coordinate = closest['point']
    records.append({'index':i,'lon':pt.x,'lat':pt.y,'nearest_coordinate':list(coordinate),
                    'nearest_edge_wgs84_m':closest['distance_m'],
                    'nearest_edge_numerically_ambiguous':closest['ambiguous'],
                    'source_edge_index':closest['source_index']})
with open(args.output,'x',encoding='utf-8') as f:
    json.dump({'unmatched':len(records),'records':records},f,indent=2)
for threshold in [0.001,0.01,0.1,1,10,100,1000]:
    print('local WGS84 candidate distance <=',threshold,'m:',sum(r['nearest_edge_wgs84_m'] <= threshold for r in records))
print('records',len(records),'first',records[:3],'last',records[-3:])
