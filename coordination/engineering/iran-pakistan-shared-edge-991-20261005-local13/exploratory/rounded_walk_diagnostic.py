"""Diagnose exact vertex collisions in the floating point derivative.

Keeps every collapsed walk separately. No candidate from this experiment is
approved or installed. Source-rational topology remains the retained reference.
"""
exec(open('.cache/shared-edge-991/exact_world_v2.py').read().split('export = {}')[0])
from exact_collinear_v3 import split_exact_walk, reduce_ring
from exact_faces_v2 import boundaries
from exact_arrangement import export_rings
from shapely.validation import explain_validity
summaries = {}
candidates = {}
collapsed_records = {}
for owner in d['subject_ids']:
    originals = [reduce_ring(c)[0] for walk in boundaries(arrangement, labels, owner)
                 for c in split_exact_walk(walk)]
    retained = []
    collapsed = []
    for original in originals:
        rounded = [point((float(x), float(y))) for x, y in original]
        stack = []
        positions = {}
        all_cycles = []
        for p in rounded + rounded[:1]:
            if p in positions:
                n = positions[p]
                cycle = stack[n:]
                all_cycles.append(cycle)
                for deleted in stack[n + 1:]:
                    del positions[deleted]
                stack = stack[:n + 1]
            else:
                positions[p] = len(stack)
                stack.append(p)
        assert len(stack) == 1
        assert sum(signed_area(c) for c in all_cycles) == signed_area(rounded)
        original_edges = sorted(zip(rounded, rounded[1:] + rounded[:1]))
        cycle_edges = sorted(e for c in all_cycles for e in zip(c, c[1:] + c[:1]))
        assert original_edges == cycle_edges
        for cycle in all_cycles:
            if signed_area(cycle) == 0:
                collapsed.append({'rounded_ring': [[str(x), str(y)] for x, y in cycle],
                                  'complete_exact_source_ring': [[str(x), str(y)] for x, y in original]})
            else:
                retained.append(cycle)
    collapsed_records[owner] = collapsed
    if retained:
        candidate = export_rings(retained)
        candidates[owner] = candidate
        g = shape(candidate)
        summaries[owner] = {'rounded_valid': g.is_valid, 'validity_reason': explain_validity(g),
                            'exact_zero_area_rounded_walks': len(collapsed), 'retained_cycles': len(retained)}
    else:
        summaries[owner] = {'rejected': 'All rounded cycles collapsed'}
result = {'experimental': True, 'summaries': summaries, 'candidates': candidates,
          'retained_collapsed_walks': collapsed_records,
          'limits': ['Diagnostic derivative only; exact-zero rounded walks retained separately, no positive-area cutoff.',
                     'Rounding changes exact source coordinates and may collapse exact-source regions; source model is not replaced.',
                     'No source approval, boundary/pixel-tie equivalence, global regression or installation is established.']}
payload = (json.dumps(result, sort_keys=True, indent=2) + '\n').encode()
pathlib.Path('.cache/shared-edge-991/rounded-walk-diagnostic-v1.json').write_bytes(payload)
print(json.dumps({'sha256': hashlib.sha256(payload).hexdigest(), 'summaries': summaries}))
