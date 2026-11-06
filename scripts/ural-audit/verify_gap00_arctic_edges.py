#!/usr/bin/env python3
"""Verify every gap-00 route segment against the 15 m construction grid."""
import argparse, hashlib, json, math, sys
from pathlib import Path
import numpy as np
from pyproj import Transformer

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--inputs', type=Path, required=True)
p.add_argument('--helpers', type=Path, required=True)
p.add_argument('--boundary', type=Path, required=True)
p.add_argument('--boundary-sha256', required=True)
p.add_argument('--route', type=Path, required=True)
p.add_argument('--route-file-sha256', required=True)
args = p.parse_args()
sys.path.insert(0, str(args.helpers.resolve()))
from spring_connector_graph import basin_labels

root = args.inputs
basins = [
    (str(root/'ural-hydro-eu.zip'), '21797d53e0792cae047d25f0c3cfb570c7ef43700ec962b35b2ac92467e29f03', str(root/'ural-hydro-eu/hybas_eu_lev12_v1c.shp')),
    (str(root/'ural-hydro-si.zip'), '67ea00df7d14a397f8f78e5b1dc31dcca036018ccbcb36e007ce6854b91d71bd', str(root/'ural-hydro-si/hybas_si_lev12_v1c.shp')),
]
labels, transform, _, unknown = basin_labels(
    str(root/'ural-gap00-12km-nearest.tif'), '3dbc4da15948791a70b78346eaba7174ccb464226bf9adf292184757f7c6af6b',
    None, None, basins, [59.70,64.10,59.83,64.18], [2120043720,3120001840,9999999999], 15)
to_grid = Transformer.from_crs(4326, 32640, always_xy=True)
route_bytes = args.route.read_bytes()
if hashlib.sha256(route_bytes).hexdigest() != args.route_file_sha256:
    raise ValueError('unexpected terrain route file')
source_route = json.loads(route_bytes)['coordinates']
boundary = json.loads(args.boundary.read_bytes())
canonical = json.dumps(boundary, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
if hashlib.sha256(canonical).hexdigest() != args.boundary_sha256:
    raise ValueError('unexpected Ural boundary geometry')
positions = [i for i, v in enumerate(boundary['coordinates']) if v == source_route[1]]
if len(positions) != 1:
    raise ValueError('ambiguous gap route')
begin = positions[0] - 1
route = boundary['coordinates'][begin:begin+len(source_route)]
if route[1:-1] != source_route[1:-1]:
    raise ValueError('gap route interior changed')
to_cell = ~transform
coords = [to_cell * to_grid.transform(*p) for p in route]
failed = []
for i, (a,b) in enumerate(zip(coords, coords[1:])):
    mx, my = (a[0]+b[0])/2, (a[1]+b[1])/2
    if max(abs(a[0]-b[0]), abs(a[1]-b[1])) > 1.00001:
        failed.append({'segment':i,'reason':'spans more than one grid edge','endpoints_grid':[a,b]})
        continue
    if abs(a[0]-b[0]) < 1e-5 and abs(mx-round(mx)) < 1e-5:
        c, r = round(mx), math.floor(my)
        vals = [int(labels[r,c-1]), int(labels[r,c])]
    elif abs(a[1]-b[1]) < 1e-5 and abs(my-round(my)) < 1e-5:
        r, c = round(my), math.floor(mx)
        vals = [int(labels[r-1,c]), int(labels[r,c])]
    else:
        failed.append({'segment':i,'reason':'not a construction grid edge','endpoints_grid':[a,b]})
        continue
    if sorted(vals) != [1,2]:
        failed.append({'segment':i,'reason':'adjacent basin classes differ from 1 and 2','classes':vals})
print(json.dumps({'segments':len(route)-1,'boundary_start_index':begin,'unknown_valid_cells':unknown,'failed_count':len(failed),
                  'failed':failed[:20], 'grid':'EPSG:32640, 15m',
                  'limitation':'Model-cell adjacency only, not ground-truth watershed.'},sort_keys=True))
