"""Bounded metadata/contact/output controls; never replay the full centre query."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from shapely.geometry import shape

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('sle_interpret', ROOT / 'interpret.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
data = m.read_inputs()
checks = []


def reject(name, operation):
    try:
        operation()
    except ValueError:
        checks.append(name)
        return
    raise AssertionError('Expected rejection: ' + name)


roster, primary, bysid, byowner, states = m.validate_scope(data)
source, secondary, byid, selected, stages, physical = m.source_inventory(data, primary)
checks.append('actual complete original scope/source metadata')
for name, change in [
    ('missing original interval', lambda d: d['intervals'].pop()),
    ('duplicate original interval', lambda d: d['intervals'].__setitem__(1, d['intervals'][0])),
    ('wrong original owner', lambda d: d['intervals'][0].__setitem__(3, [39709])),
    ('wrong original source', lambda d: d['intervals'][0].__setitem__(4, [55540])),
    ('missing zero-candidate roster competitor', lambda d: d['global_roster'].__setitem__(slice(None), [r for r in d['global_roster'] if r['source_index'] != 55538])),
    ('missing selected owner key', lambda d: d['selected_state']['keys'].pop()),
]:
    altered = copy.deepcopy(data)
    change(altered)
    reject(name, lambda: m.validate_scope(altered))

for name, change in [
    ('omitted whole primary competitor', lambda d: d['source']['features'].pop(3)),
    ('missing retained physical target', lambda d: d['whole_physical']['results'].pop()),
    ('duplicate retained physical target', lambda d: d['whole_physical']['results'].__setitem__(1, d['whole_physical']['results'][0])),
]:
    altered = copy.deepcopy(data)
    change(altered)
    reject(name, lambda: m.source_inventory(altered, primary))

land = next(shape(r['support']['mapped_land_support']) for r in physical.values()
            if not shape(r['support']['mapped_land_support']).is_empty)
point = land.representative_point()
hits, contacts = m.witness_hits({'mapped_land_support': land}, [], point)
assert hits == ['mapped_land_support']
checks.append('actual retained mapped-land positive contact')
issue = next((identity, i, row, shape(row['geometry'])) for identity, result in physical.items()
             for i, row in enumerate(result['issues']))
point = issue[3].representative_point()
hits, contacts = m.witness_hits({}, [issue], point)
assert len(contacts) == 1 and contacts[0]['target'] == issue[0]
checks.append('actual retained Pujehun issue positive contact')

results = ROOT / 'results-001'
answers = json.loads((results / 'interval-assessments.json').read_text())
observations = json.loads((results / 'cell-observations.json').read_text())
questions = json.loads((results / 'questions.json').read_text())
assert len(answers) == 613 and len(observations) == 1213
assert [r['original_interval'] for r in answers] == data['intervals']
literal = {(y, x, owner[0]) for y, a, b, owner, sids, kind in data['intervals'] for x in range(a, b)}
parts = [(r['original_interval'][0], x, r['original_owner']) for r in answers for p in r['parts'] for x in range(p['start'], p['end'])]
assert len(parts) == len(set(parts)) == 1213 and set(parts) == literal
assert {(r['y'], r['x'], r['original_owner']) for r in observations} == literal
assert sum(q['native_cells'] for q in questions) == 1213
assert {p['question_id'] for r in answers for p in r['parts']} == {q['question_id'] for q in questions}
checks.append('literal interval/cell/question conservation without predicate replay')

with tempfile.TemporaryDirectory(prefix='sle-review-controls-') as d:
    d = Path(d)
    sentinel = d / 'occupied'
    sentinel.mkdir()
    (sentinel / 'sentinel').write_text('unchanged')
    result = subprocess.run([sys.executable, '-B', str(ROOT / 'interpret.py'), str(sentinel)], capture_output=True)
    assert result.returncode != 0 and b'Fresh output required' in result.stderr
    assert (sentinel / 'sentinel').read_text() == 'unchanged' and not result.stdout
    checks.append('actual CLI existing-output refusal before input/query')
    link = d / 'dangling'
    link.symlink_to(d / 'missing')
    result = subprocess.run([sys.executable, '-B', str(ROOT / 'interpret.py'), str(link)], capture_output=True)
    assert result.returncode != 0 and link.is_symlink() and not result.stdout
    checks.append('actual CLI dangling-symlink refusal before input/query')

print(json.dumps({'passed': len(checks), 'checks': checks,
                  'limit': 'No full centre computation, extractor, physical or native authority replay.'}, indent=2))
