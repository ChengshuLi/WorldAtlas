"""Check reconstruction of every complete retained neighbor, including holes."""
exec(open('.cache/shared-edge-991/exact_world_v2.py').read().split('export = {}')[0])
from exact_collinear_v3 import split_exact_walk, reduce_ring
from exact_faces_v2 import boundaries
from exact_arrangement import export_rings
from shapely.validation import explain_validity
records = []
candidates = {}
for owner, old in all_before.items():
    walks = boundaries(arrangement, before_labels, owner)
    cycles = [reduce_ring(c)[0] for walk in walks for c in split_exact_walk(walk)]
    raw = export_rings(cycles)
    g = shape(raw)
    equal_area = sum(signed_area(r) for r in cycles) == exact_geometry_area(old)
    assert equal_area
    records.append({'owner': owner, 'exact_area_equal': equal_area,
                    'rounded_valid': g.is_valid, 'rounded_equals_original': g.equals(old),
                    'validity_reason': explain_validity(g), 'rings': len(cycles)})
    candidates[owner] = raw
result = {'experimental': True, 'subjects': records, 'reconstructed': candidates,
          'all_valid_and_equal': all(r['rounded_valid'] and r['rounded_equals_original'] for r in records),
          'limits': ['Eleven-neighbor original reconstruction only; does not accept the proposed repair or a global method.']}
payload = (json.dumps(result, sort_keys=True, indent=2) + '\n').encode()
pathlib.Path('.cache/shared-edge-991/exact-baseline-reconstruction-v1.json').write_bytes(payload)
print(json.dumps({'sha256': hashlib.sha256(payload).hexdigest(),
                  'all_valid_and_equal': result['all_valid_and_equal'], 'subjects': records}))
