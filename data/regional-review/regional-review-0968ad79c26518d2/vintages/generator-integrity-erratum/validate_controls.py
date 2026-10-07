#!/usr/bin/env python3
"""Reproduce positive, negative, and two-run controls for issue #1308."""
from pathlib import Path
import hashlib, json, subprocess, sys, gzip
from integrity_guards import verify_bound_input, require_new_output

ROOT = Path(__file__).resolve().parents[2]
VINTAGE = Path(__file__).resolve().parent
RUNS = VINTAGE / 'runs' / '2026-10-07'
OUT = VINTAGE / 'controls' / 'verified-run-2'
SUMMARY = VINTAGE / 'erratum-summary-v2.json'
LEDGER = VINTAGE / 'correction-ledger-v2.json'
# Check every destination before reading or writing any control result.
for destination in (OUT, SUMMARY, LEDGER):
    require_new_output(destination)
OLD = ROOT / 'assessments.json'
ONE = RUNS / 'run-1' / 'assessments.json.gz'
TWO = RUNS / 'run-2' / 'assessments.json.gz'
BASE = 'cbb829672d18801e4310c30896a7ddb13a79b451'
sha = lambda b: hashlib.sha256(b).hexdigest()

# Check both changed national source and exact subject list are rejected by the
# same guard used before every production computation.
spec = json.loads((VINTAGE / 'evaluation-inputs.json').read_text())
by_path = {x['path']: x for x in spec['inputs']}
for path in ('data/global-sources/IND-ADM3.geojson.gz', 'data/regional-review/regional-review-0968ad79c26518d2/issue-scope.json'):
    descriptor = by_path[path]
    committed = subprocess.check_output(['git', 'show', f'{BASE}:{path}'], cwd=ROOT.parents[2])
    verify_bound_input(descriptor, committed, committed)
    changed = committed + b'changed'
    try:
        verify_bound_input(descriptor, committed, changed)
    except ValueError:
        pass
    else:
        raise AssertionError(f'Changed input was accepted: {path}')

# Existing destinations are refused without changing the original bytes.
before = OLD.read_bytes()
try:
    require_new_output(ONE)
except FileExistsError:
    pass
else:
    raise AssertionError('Existing output collision was accepted')
assert OLD.read_bytes() == before

original = json.loads(before)
a = json.loads(gzip.decompress(ONE.read_bytes()))
b = TWO.read_bytes()
assert ONE.read_bytes() == b, 'Fresh deterministic runs differ'
assert len(a['exact_subjects']) == 224 and len(a['province_assessments']) == 27
assert [r['id'] for r in original['exact_subjects']] == [r['id'] for r in a['exact_subjects']]
assert [r['classification'] for r in original['exact_subjects']] == [r['classification'] for r in a['exact_subjects']]
agar = [r for r in a['exact_subjects'] if r['province_name'] == 'Agar']
assert len(agar) == 4 and all(r['current_roster_source_system'] == 'IGOD / Local Government Directory' and
    r['current_roster_source_sha256'] == '190564a28ca08e96785ad20d9a6d2d235c7b0972d731c102ba361c16ac01374e' and
    r['current_roster_name_exact_match'] is True for r in agar)
sheopur = next(r for r in a['province_assessments'] if r['province'] == 'Sheopur')
assert sheopur['lgd_source_sha256'] is None and sheopur['classification'] == 'insufficient-evidence'
assert OLD.read_bytes() == before and sha(before) == spec['baseline_output']['sha256']
changes = []
for old_row, new_row in zip(original['exact_subjects'], a['exact_subjects']):
    for key in old_row:
        if old_row[key] != new_row[key]:
            changes.append({'id': old_row['id'], 'name': old_row['name'], 'field': key,
                            'before': old_row[key], 'after': new_row[key]})
assert len(changes) == 16 and all(x['before'] is None for x in changes)

out = OUT
out.mkdir()
results = {
 'positive-control.json': {'method_id':'integrity-erratum','kind':'positive-control','outcome':'passed',
   'checked':'All four Agar subject records use the one retained Agar-Malwa roster key; 16 null-to-source metadata fields; classifications unchanged; Sheopur remains unbound.'},
 'negative-control.json': {'method_id':'integrity-erratum','kind':'negative-control','outcome':'passed',
   'checked':'The production guard rejects altered geoBoundaries source bytes and altered exact issue-scope subject input bytes; existing output destinations are refused before write; original assessment bytes remain unchanged.'},
 'reproducibility.json': {'method_id':'integrity-erratum','kind':'reproducibility','outcome':'passed',
   'run_one_sha256':sha(ONE.read_bytes()),'run_two_sha256':sha(TWO.read_bytes()),'subjects':224,'provinces':27,
   'classification_counts':{c:sum(x['classification']==c for x in a['exact_subjects']) for c in ('justified','correction-needed','insufficient-evidence')},
   'original_assessments_sha256':sha(before),'original_preserved':True}
}
for name, row in results.items():
    (out/name).write_text(json.dumps(row,indent=2)+'\n')
summary = {'version':1,'issue':1308,'baseline_commit':BASE,'subjects':224,'province_groups':27,
 'corrected_field_values':len(changes),'newly_roster_bound_subjects':4,'justified':0,'correction_needed':11,
 'insufficient_evidence':213,'sheopur_roster_source_available':False}
(SUMMARY).write_text(json.dumps(summary,indent=2)+'\n')
(LEDGER).write_text(json.dumps({'version':1,'issue':1308,'baseline_commit':BASE,
 'baseline_assessments_sha256':sha(before),'corrected_assessments_sha256':sha(ONE.read_bytes()),
 'changes':changes,'unchanged_metrics':summary,
 'uncertainty_preserved':['IGOD is administrative roster evidence only; it does not establish jurisdiction or polygons.',
  'Sheopur current roster source remains unavailable.', 'geoBoundaries source-vintage/completeness and 14-unit metadata discrepancy remain unresolved.',
  'Current/legal boundary correspondence and territorial role remain unverified.']},indent=2)+'\n')
print(json.dumps({'positive':'passed','negative':'passed','reproducibility':'passed','field_updates':len(changes),'original_sha256':sha(before)},indent=2))
