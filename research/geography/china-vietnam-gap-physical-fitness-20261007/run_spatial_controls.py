#!/usr/bin/env python3
"""Run bounded synthetic controls against the classifier's exact geometry helper functions."""
import ast,json,math,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
source=(ROOT/'classify_worldcover_window.py').read_text()
tree=ast.parse(source)
selected={'on_segment','ring_covers','polygon_covers','covers','read_required'}
module=ast.Module(body=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name in selected],type_ignores=[])
ns={'math':math,'Path':Path}
exec(compile(module,'classify_worldcover_window.py','exec'),ns)
square=[[0.0,0.0],[1.0,0.0],[1.0,1.0],[0.0,1.0],[0.0,0.0]]
poly={'type':'Polygon','coordinates':[square]}
positive=ns['covers'](poly,(0.5,0.5))
negative=ns['covers'](poly,(2.0,2.0))
shifted={'type':'Polygon','coordinates':[[[x+10,y+10] for x,y in square]]}
altered=not ns['covers'](shifted,(0.5,0.5))
missing_path=ROOT/'sources'/'__control_missing_source__.bin'
try:
 ns['read_required'](missing_path)
 missing=True
except FileNotFoundError:
 missing=False
controls=[
 {'id':'directed-positive','outcome':'passed' if positive else 'failed','detail':'A synthetic pixel-center point strictly inside a synthetic polygon is covered.'},
 {'id':'directed-negative','outcome':'passed' if not negative else 'failed','detail':'A synthetic point outside the same polygon is not covered.'},
 {'id':'altered-input','outcome':'passed' if altered else 'failed','detail':'Shifting every polygon vertex by ten coordinate units changes the control point from covered to not covered.'},
 {'id':'missing-source','outcome':'passed' if not missing else 'failed','detail':'The producer required-read helper propagates FileNotFoundError; no pixel fill or substitute value is returned.'},
]
assert all(x['outcome']=='passed' for x in controls)
(ROOT/'spatial-control-results.json').write_text(json.dumps({'control_scope':'synthetic helper controls only; no WorldCover raster blocks or candidate GIS input were read by this control runner.','geometry_helpers_extracted_from':'classify_worldcover_window.py','controls':controls},indent=2)+'\n')
print(json.dumps(controls,indent=2))
