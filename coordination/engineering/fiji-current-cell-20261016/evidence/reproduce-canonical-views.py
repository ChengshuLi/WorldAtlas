"""Derive explicit views using the unchanged retained periodic canonicalizer.

Original source and physical evidence stay byte-identical. Only geometries with
an actual out-of-frame longitude are requested; the native verifier rejects any
material overrun or changed cell/boundary outcome separately. The parent passes
its authenticated captured original bodies, never paths to reopen.
"""
import base64
import hashlib
import json
import sys
from pathlib import Path


def read_captured_inputs(stream):
    envelope = json.load(stream)
    roles = ('physical_input', 'physical_evidence')
    if (set(envelope) != {'version', 'inputs'} or envelope['version'] != 1
            or set(envelope['inputs']) != set(roles)):
        raise ValueError('Invalid captured-input envelope')
    result = {}
    for role in roles:
        item = envelope['inputs'][role]
        if set(item) != {'bytes', 'sha256', 'body_base64'}:
            raise ValueError('Invalid captured input: ' + role)
        body = base64.b64decode(item['body_base64'], validate=True)
        if len(body) != item['bytes'] or hashlib.sha256(body).hexdigest() != item['sha256']:
            raise ValueError('Captured input differs: ' + role)
        result[role] = json.loads(body)
    return result


def overrun(value):
    if isinstance(value, list):
        if len(value) == 2 and all(isinstance(n, (int, float)) for n in value):
            return abs(value[0]) > 180
        return any(overrun(child) for child in value)
    return False


def main():
    # Read only the captured, authenticated bytes supplied by the JS parent.
    inputs = read_captured_inputs(sys.stdin)
    from shapely.geometry import shape, mapping
    root = Path(__file__).resolve().parents[4]
    sys.path.insert(0, str(root / 'scripts'))
    from majority import canonical
    records = []

    def add(role, source_id, pointer, geometry):
        if overrun(geometry.get('coordinates', [])):
            records.append(dict(role=role, source_id=source_id, pointer=pointer,
                                original_geometry=geometry,
                                geometry=mapping(canonical(shape(geometry)))))

    for source in inputs['physical_input']:
        add('source', source['target'], '/geometry', source['consumed']['geometry'])
    for result in inputs['physical_evidence']['results']:
        for field in ('mapped_land_support', 'mapped_inland_water_support', 'outside_mapped_L1_context'):
            add('physical', result['target'], '/support/' + field, result['support'][field])
        for ordinal, query in enumerate(result['query_relations']):
            geometry = query.get('witness_geometry')
            if geometry and geometry['type'] in ('Polygon', 'MultiPolygon'):
                add('physical', result['target'], f'/query_relations/{ordinal}/witness_geometry', geometry)
    print(json.dumps(records, separators=(',', ':')))


if __name__ == '__main__':
    main()
