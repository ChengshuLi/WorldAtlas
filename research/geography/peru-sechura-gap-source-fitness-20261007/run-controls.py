#!/usr/bin/env python3
"""Deterministic positive/negative controls for the bounded geometry predicates."""
import json
from pathlib import Path
from shapely.geometry import Polygon, box
import sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from evidence.geometry import land_area_m2

out=Path(__file__).resolve().parent/'validation'
out.mkdir(exist_ok=True)
method='bounded-sechura-component-comparison'
cases=[
 ('positive-control', Polygon([(0,0),(1,0),(1,1),(0,1),(0,0)]), box(.2,.2,.3,.3), True),
 ('negative-control', Polygon([(0,0),(1,0),(1,1),(0,1),(0,0)]), box(2,2,3,3), False),
]
for kind,source,candidate,expected in cases:
 actual=source.intersects(candidate) and source.covers(candidate) and candidate.intersection(source).area>0
 assert actual is expected
 evidence={'version':1,'method_id':method,'kind':kind,'outcome':'passed','predicate':'intersects and covers and positive planar area','expected':expected,'observed':actual,'software':'Shapely 2.1.2 / GEOS 3.13.1','geometry':'Synthetic unit-square positive inclusion and disjoint unit-square negative case; not geographic evidence'}
 (out/f'{kind}.json').write_text(json.dumps(evidence,indent=2)+'\n')

# The repository's WGS84 straight-source-edge area helper has a separate
# geography-method control pair: positive polygon area and rejection of a
# zero-area line, which is outside its land-footprint domain.
method='wgs84-selected-feature-area'
positive=land_area_m2(Polygon([(0,0),(1,0),(1,1),(0,1),(0,0)]))
assert positive > 0
(out/'wgs84-positive-control.json').write_text(json.dumps({'version':1,'method_id':method,'kind':'positive-control','outcome':'passed','expected':'positive finite area','observed':positive,'unit':'m2','software':'scripts/evidence/geometry.py worldatlas-evidence-geometry-v1','geometry':'Synthetic one-degree square; control only, not geographic evidence'},indent=2)+'\n')
try:
 land_area_m2(box(0,0,1,0))
except ValueError:
 rejected=True
else:
 rejected=False
assert rejected
(out/'wgs84-negative-control.json').write_text(json.dumps({'version':1,'method_id':method,'kind':'negative-control','outcome':'passed','expected':'reject zero-area geometry','observed':'rejected','software':'scripts/evidence/geometry.py worldatlas-evidence-geometry-v1','geometry':'Synthetic degenerate polygon boundary; control only, not geographic evidence'},indent=2)+'\n')
