#!/usr/bin/env python3
"""Extract the issue-pinned family row from immutable route outputs."""
from pathlib import Path
import gzip, hashlib, json, subprocess

BASELINE = '745cc86a5e1e4d9917730bad0b5a7a031de99ceb'
REPORT = 'coordination/engineering/global-actionability-routing-20261007/results/report.json'
REPORT_SHA256 = '2bf401f76aabc30cb9f0120aba958545146ebf37e304d8817d15eed800fa5265'
FAMILY_ID = 'gap-source-batch:8875fd920e43656b5f36e704'
FAMILY_SHA256 = 'a08249214711d84d7d220a61fe10f2d4582e7bc64f1a5ae811436ddaf22d94b3'
ROSTER_SHA256 = '88831aad22806bf4f461197a12cb8309bf9a0139e5bd82b967a55e8255ad26ec'
OUT = Path('research/geography/indonesia-borneo-source-fitness-20261007/sources/v1')

def git(path):
    return subprocess.check_output(['git', 'show', f'{BASELINE}:{path}'])
def sha(raw):
    return hashlib.sha256(raw).hexdigest()
def validate_roster(values, expected):
    if not isinstance(values, list) or len(values) != 45 or len(values) != len(set(values)) or set(values) != expected:
        raise ValueError('Candidate roster must exactly match the 45 unique source IDs')
    return True
def rejected(values, expected):
    try:
        validate_roster(values, expected)
    except (TypeError, ValueError):
        return True
    return False

report_raw = git(REPORT)
if sha(report_raw) != REPORT_SHA256:
    raise SystemExit('Pinned route report changed')
report = json.loads(report_raw)
parts = sorted((x for x in report['outputs'] if x['path'].startswith('families-')), key=lambda x: x['path'])
if len(parts) != 14:
    raise SystemExit('Expected the complete 14-part family inventory')
encoded_total = decoded_total = 0
raw_rows = []
for desc in parts:
    path = 'coordination/engineering/global-actionability-routing-20261007/results/' + desc['path']
    body = git(path)
    if len(body) != desc['bytes'] or sha(body) != desc['sha256']:
        raise SystemExit('Encoded source descriptor mismatch: ' + path)
    decoded = gzip.decompress(body)
    if len(decoded) != desc['uncompressed_bytes'] or sha(decoded) != desc['uncompressed_sha256']:
        raise SystemExit('Decoded source descriptor mismatch: ' + path)
    encoded_total += len(body)
    decoded_total += len(decoded)
    raw_rows.extend(line for line in decoded.splitlines() if FAMILY_ID.encode() in line)
if encoded_total + decoded_total > 256 * 1024 * 1024:
    raise SystemExit('Complete family-source phase exceeds 256 MiB')
if len(raw_rows) != 1 or sha(raw_rows[0]) != FAMILY_SHA256:
    raise SystemExit('Pinned family row missing, duplicated, or changed')
row = json.loads(raw_rows[0])
ids = row.get('complete_component_ids')
if not isinstance(ids, list) or len(ids) != 45 or len(ids) != len(set(ids)):
    raise SystemExit('Exact route row must contain 45 unique component IDs')
sorted_roster = ''.join(identity + '\n' for identity in sorted(ids)).encode()
if sha(sorted_roster.rstrip(b'\n')) != ROSTER_SHA256:
    raise SystemExit('Sorted 45-component roster hash mismatch')
# Nonvacuous adverse controls use the actual selected roster.
expected = set(ids)
controls = {
    'positive_exact_roster': validate_roster(ids, expected),
    'negative_missing_id_rejected': rejected(ids[:-1], expected),
    'negative_duplicate_id_rejected': rejected(ids + [ids[0]], expected),
    'negative_fabricated_id_rejected': rejected(ids[:-1] + ['physical-component:' + '0' * 64], expected),
}
if not all(controls.values()):
    raise SystemExit('A source-scope control failed')
row_path = OUT / 'family-row.json'
roster_path = OUT / 'component-roster.txt'
receipt_path = OUT / 'scope-extraction-current-745cc86a.json'
if not row_path.is_file() or row_path.read_bytes() != raw_rows[0]:
    raise ValueError('The preserved original family row differs from the current pinned source row')
if not roster_path.is_file() or roster_path.read_bytes() != sorted_roster:
    raise ValueError('The preserved original roster differs from the current pinned source roster')
if receipt_path.exists():
    raise FileExistsError('Preserve existing evidence; use a new receipt vintage: ' + str(receipt_path))
receipt = {
    'version': 1,
    'baseline_commit': BASELINE,
    'route_report': {'path': REPORT, 'bytes': len(report_raw), 'sha256': REPORT_SHA256},
    'family_id': FAMILY_ID,
    'family_row': {'path': row_path.as_posix(), 'bytes': len(raw_rows[0]), 'sha256': FAMILY_SHA256},
    'component_roster': {'path': roster_path.as_posix(), 'bytes': len(sorted_roster), 'sha256': sha(sorted_roster), 'sorted_without_trailing_lf_sha256': ROSTER_SHA256},
    'component_count': len(ids),
    'family_source_parts': parts,
    'input_encoded_bytes': encoded_total,
    'input_decoded_bytes': decoded_total,
    'controls': controls,
}
with receipt_path.open('x', encoding='utf-8') as stream:
    stream.write(json.dumps(receipt, sort_keys=True, indent=2) + '\n')
print(json.dumps(receipt, indent=2))
