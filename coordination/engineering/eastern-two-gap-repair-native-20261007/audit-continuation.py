"""Preserve the original audit; recompute only the two changes and affected statistics."""
import ast, hashlib, json, math, pathlib, sys
from shapely.geometry import shape
recipe = pathlib.Path(sys.argv[1]).read_bytes()
area_node = next(n for n in ast.parse(recipe).body if isinstance(n, ast.FunctionDef) and n.name == 'area')
namespace = {'math': math}
exec(compile(ast.Module(body=[area_node], type_ignores=[]), '<exact-original-area-recipe>', 'exec'), namespace)
area = namespace['area']
x = json.load(sys.stdin)
old = x['audit']
assert len(old['locations_audited']) == 49625
rows = {r['id']: r for r in old['locations_audited']}
targets = set(x['targets'])
assert len(targets) == 2
before = x['before']
after = x['after']
assert len(before) == len(after) == old['countries']['Canada']['locations']
assert [f['id'] for f in before] == [f['id'] for f in after]
old_areas = [area(shape(f['geometry'])) for f in before]
new_areas = [area(shape(f['geometry'])) for f in after]
def summary(values):
    return {'locations': len(values), 'min_km2': round(min(values), 2), 'median_km2': round(sorted(values)[len(values)//2], 2), 'max_km2': round(max(values), 2)}
assert summary(old_areas) == old['countries']['Canada']
changes = []
for a, b, old_area, new_area in zip(before, after, old_areas, new_areas):
    assert rows[a['id']]['area_km2'] == round(old_area, 3)
    if a['id'] not in targets:
        assert a == b and old_area == new_area
    else:
        assert a['properties'] == b['properties'] and a['id'] == b['id']
        changes.append({'id': a['id'], 'before_area_km2': round(old_area, 3), 'after_area_km2': round(new_area, 3)})
        rows[a['id']]['area_km2'] = round(new_area, 3)
assert {r['id'] for r in changes} == targets
old['countries']['Canada'] = summary(new_areas)
old['coarse_units'] = [r for r in old['locations_audited'] if r['area_km2'] > 50000]
old['small_units'] = [r for r in old['locations_audited'] if r['area_km2'] < 25]
old['input_sha256']['geography/part-29.json'] = x['proposed_part_sha256']
old['reference_correction'] = {**x['binding'], 'original_audit_sha256': x['original_audit_sha256'], 'actual_area_recipe_sha256': hashlib.sha256(recipe).hexdigest(), 'recomputed_features': changes, 'complete_affected_distribution_members': len(after), 'unchanged_full_audit_rows': 49623, 'fresh_complete_audit_claimed': False}
json.dump(old, sys.stdout, ensure_ascii=False, separators=(',', ':'))
sys.stdout.write('\n')
