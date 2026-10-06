#!/usr/bin/env python3
"""Positive and negative validity controls for the read-only #978 geometry measurement."""
import json, hashlib
from pathlib import Path
from shapely.geometry import Polygon
from shapely.validation import explain_validity
OUT=Path(__file__).resolve().parent
method='native-validity-and-iou'
pos=Polygon([(0,0),(1,0),(0,1),(0,0)])
neg=Polygon([(0,0),(1,1),(0,1),(1,0),(0,0)])
assert pos.is_valid and pos.area > 0
assert not neg.is_valid
for fn,kind,passed,reason in [
 ('measurement-positive-control.json','positive-control',pos.is_valid,explain_validity(pos)),
 ('measurement-negative-control.json','negative-control',not neg.is_valid,explain_validity(neg))]:
 data={'method_id':method,'kind':kind,'outcome':'passed' if passed else 'failed','fixture':'synthetic polygon rings; no repair','observed':reason}
 (OUT/fn).write_text(json.dumps(data,sort_keys=True,indent=2)+'\n')
