#!/usr/bin/env python3
"""Reject restoration additions overlapping any immutable archived predecessor."""
import gzip, hashlib, json, pathlib, sys
sys.dont_write_bytecode = True
from shapely.geometry import shape
from shapely import STRtree
from majority import canonical
from ellipsoidal_area import area

def validate(payload):
    root = pathlib.Path(payload['root']).resolve()
    candidates = payload['candidates']
    geometries = [canonical(shape(f['geometry'])) for f in candidates]
    tree = STRtree(geometries)
    count = 0
    for entry in payload['archives']:
        source = (root / entry['path']).resolve()
        if not source.is_relative_to(root) or hashlib.sha256(source.read_bytes()).hexdigest() != entry['sha256']:
            raise ValueError('Archived geography bytes changed')
        document = json.loads(gzip.decompress(source.read_bytes()))
        for row in document.get('locations', []):
            old = row.get('feature', row)
            geometry = canonical(shape(old['geometry']))
            count += 1
            for index in tree.query(geometry, predicate='intersects'):
                if area(geometry.intersection(geometries[int(index)])) > .001:
                    raise ValueError('Existing archived land cannot be created again: ' + candidates[int(index)]['id'])
    return {'verified': True, 'archived_predecessors_checked': count, 'new_candidates': len(candidates), 'history_transfer': False}

if __name__ == '__main__':
    print(json.dumps(validate(json.load(sys.stdin)), separators=(',', ':')))
