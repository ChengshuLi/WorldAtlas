"""Test general exact face handling against all eleven retained neighbors."""
import time
import hashlib
from fractions import Fraction as F
started = time.monotonic()
prefix = open('.cache/shared-edge-991/exact-world-case.py').read().split('counts={};')[0]
prefix = prefix.replace('from exact_arrangement import arrange,point,inside_ring,signed_area',
                        'from exact_arrangement import point,inside_ring,signed_area\nfrom exact_faces_v2 import arrange')
exec(compile(prefix, 'retained-case-initialization-v2', 'exec'))
from exact_faces_v2 import boundaries, validate_noding
from exact_arrangement import export_rings
from shapely.validation import explain_validity

noding = validate_noding(segments, arrangement, bbox_reference=True)
counts = {}
records = []
labels = []
before_labels = []
unknown = []
old_areas = {k: F(0) for k in all_before}
component_area = F(0)
for n, (ring, area, p) in enumerate(arrangement['faces']):
    old = [k for k in all_before if classify(p, polys['old:' + k])]
    in_component = classify(p, polys['component'])
    named = [k for k in source if classify(p, polys['source:' + k])] if in_component and not old else []
    after = old if old else [ns['SUBJECTS'][named[0]]] if in_component and len(named) == 1 else []
    if in_component and not old and len(named) != 1:
        unknown.append(n)
    for owner in old:
        old_areas[owner] += area
    if in_component:
        component_area += area
    category = 'preserved' if old else 'source-added' if after else 'unknown' if in_component else 'unassigned-outside'
    counts[category] = counts.get(category, 0) + 1
    labels.append(after)
    before_labels.append(old)
    records.append({'face': n, 'category': category, 'before': old, 'after': after,
                    'source_labels': named, 'component': in_component,
                    'exact_area': str(area), 'rings': [[[str(x), str(y)] for x, y in r]
                                                     for r in arrangement['face_rings'][n]]})

def exact_geometry_area(g):
    raw = mapping(g)
    polygons = [raw['coordinates']] if raw['type'] == 'Polygon' else raw['coordinates']
    return sum(abs(signed_area([point(p) for p in rings[0][:-1]])) -
               sum(abs(signed_area([point(p) for p in r[:-1]])) for r in rings[1:])
               for rings in polygons)

area_checks = {k: {'original': str(exact_geometry_area(g)), 'reconstructed': str(old_areas[k]),
                   'equal': exact_geometry_area(g) == old_areas[k]} for k, g in all_before.items()}
assert all(record['equal'] for record in area_checks.values()), area_checks
assert component_area == exact_geometry_area(component)
export = {}
summaries = {}
for owner in d['subject_ids']:
    r = boundaries(arrangement, labels, owner)
    exact_area = sum(signed_area(ring) for ring in r)
    assigned_area = sum(area for (_, area, _), membership in zip(arrangement['faces'], labels) if owner in membership)
    assert exact_area == assigned_area
    g = export_rings(r)
    polygon = shape(g)
    export[owner] = g
    summaries[owner] = {'rings': len(r), 'exact_area_matches_assigned_faces': True,
                        'valid_rounded': polygon.is_valid, 'validity_reason': explain_validity(polygon),
                        'rounded_type': polygon.geom_type}

result = {'experimental': True, 'segments': len(segments), 'noded_edges': len(arrangement['edges']),
          'vertices': arrangement['vertices'], 'connected_components': arrangement['connected_components'],
          'bounded_faces': len(arrangement['faces']), 'hole_attachments': arrangement['attachments'],
          'counts': counts, 'noding': noding, 'original_area_checks': area_checks,
          'component_exact_area_equal': True, 'unknown_component_faces': unknown,
          'lost_face_memberships': sum(len(set(old) - set(new)) for old, new in zip(before_labels, labels)),
          'new_multiple_faces': sum(len(new) > 1 and len(old) <= 1 for old, new in zip(before_labels, labels)),
          'summaries': summaries, 'records': records, 'candidates': export,
          'limits': ['Exact binary-rational planar coordinate model only; not physical/source/country/county approval.',
                     'Rounded derivatives remain rejected when invalid; no snap, repair, area cutoff or omission.',
                     'This eleven-neighbor case is not a worldwide repair or audit.']}
payload = (json.dumps(result, sort_keys=True, indent=2) + '\n').encode()
pathlib.Path('.cache/shared-edge-991/exact-world-case-v2.json').write_bytes(payload)
print(json.dumps({'sha256': hashlib.sha256(payload).hexdigest(), 'counts': counts, 'noding': noding,
                  'old_subjects_exact_area_equal': len(area_checks), 'component_exact_area_equal': True,
                  'holes': sum(len(r)-1 for r in arrangement['face_rings']),
                  'rounded_summaries': summaries, 'seconds': time.monotonic() - started}))
