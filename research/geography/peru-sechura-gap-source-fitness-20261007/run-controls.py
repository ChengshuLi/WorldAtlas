#!/usr/bin/env python3
"""Deterministic positive/negative controls for the bounded geometry predicates."""
import json
from pathlib import Path
from shapely.geometry import Polygon, box

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
