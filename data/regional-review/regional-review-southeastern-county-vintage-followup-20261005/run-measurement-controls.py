#!/usr/bin/env python3
"""Positive/negative controls for #978 native validity and projected IoU methods."""
import json
from pathlib import Path
from pyproj import Transformer
from shapely.affinity import translate
from shapely.geometry import Polygon, box
from shapely.ops import transform
from shapely.validation import explain_validity
OUT=Path(__file__).resolve().parent

def write(filename, method, kind, observed):
 data={'method_id':method,'kind':kind,'outcome':'passed','observed':observed}
 (OUT/filename).write_text(json.dumps(data,sort_keys=True,indent=2)+'\n')

# Native validity method: known valid triangle and a self-crossing invalid bow-tie.
valid=Polygon([(0,0),(1,0),(0,1),(0,0)])
invalid=Polygon([(0,0),(1,1),(0,1),(1,0),(0,0)])
assert valid.is_valid and valid.area>0
assert not invalid.is_valid
write('measurement-positive-control.json','native-geometry-validity','positive-control',explain_validity(valid))
write('measurement-negative-control.json','native-geometry-validity','negative-control',explain_validity(invalid))

# IoU method: define rectangles in EPSG:5070 then round-trip through GeoJSON lon/lat.
# Equal 1,000 x 1,000 m squares shifted 500 m have exact IoU 1/3 by construction.
forward=Transformer.from_crs('EPSG:4326','EPSG:5070',always_xy=True)
inverse=Transformer.from_crs('EPSG:5070','EPSG:4326',always_xy=True)
center=forward.transform(-90,30)
a5070=translate(box(center[0],center[1],center[0]+1000,center[1]+1000),xoff=-500)
b5070=translate(box(center[0],center[1],center[0]+1000,center[1]+1000),xoff=0)
a4326=transform(inverse.transform,a5070); b4326=transform(inverse.transform,b5070)
a=transform(forward.transform,a4326); b=transform(forward.transform,b4326)
iou=a.intersection(b).area/a.union(b).area
assert abs(iou-(1/3))<1e-7, iou
write('iou-positive-control.json','iou-5070-reproduction','positive-control',{'analytic_iou':1/3,'observed_iou':iou,'axis_order':'longitude-latitude','control':'equal squares shifted by half their width'})

# Negative controls detect wrong axis order and substituting intersection/source area for IoU.
known=forward.transform(-90,30)
assert max(abs(known[0]-577912.4519685141),abs(known[1]-787624.2805250759))<1e-5
wrong_axis=Transformer.from_crs('EPSG:4326','EPSG:5070').transform(-90,30)
assert abs(wrong_axis[0]-known[0])>1e6
intersection=a.intersection(b).area
wrong_denominator=intersection/a.area
assert abs(wrong_denominator-0.5)<1e-7 and abs(wrong_denominator-iou)>0.1
write('iou-negative-control.json','iou-5070-reproduction','negative-control',{'known_always_xy_coordinate_m':known,'authority_axis_coordinate_m':wrong_axis,'swapped_axis_rejected':True,'wrong_intersection_over_source_area':wrong_denominator,'correct_iou':iou,'wrong_formula_rejected':True})
