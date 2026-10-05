#!/usr/bin/env python3
"""Run the offline evidence generators twice and retain exact reproducibility receipts."""
import hashlib
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
OWN = ROOT / 'data/regional-review/argentina-adm2-source-revalidation-443'
FINDINGS = OWN / 'findings'
SCRIPTS = [
    'prepare-scoped-2020.py',
    'validate-controls.py',
    'reproduce-spatial.py',
    'reproduce-components.py',
    'reproduce-province-crosswalk.py',
    'reproduce-parent-review.py',
    'categorize-tabular-findings.py',
]
TABLES = [
    '2006-adm1-to-current-province-overlay.csv',
    'scoped-2020-to-current-georef-overlay.csv',
    'scoped-current-georef-positive-area-overlaps.csv',
    'scoped-multipart-components.csv',
    'scoped-parent-review.csv',
    'scoped-2020-internal-overlaps.csv',
]


def run_once():
    for name in SCRIPTS:
        subprocess.run([sys.executable, str(OWN / name)], cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
    partition = hashlib.sha256((OWN / 'source/geoBoundaries-2020-scoped-214.geojson').read_bytes()).hexdigest()
    table_hashes = {name: hashlib.sha256((FINDINGS / name).read_bytes()).hexdigest() for name in TABLES}
    combined = hashlib.sha256('\n'.join(f'{name}:{table_hashes[name]}' for name in TABLES).encode()).hexdigest()
    return partition, combined, table_hashes


one = run_once()
two = run_once()
assert one[0] == two[0] and one[1] == two[1] and one[2] == two[2]
reports = [
    ('source-partition', one[0], two[0], ['source/geoBoundaries-2020-scoped-214.geojson']),
    ('categorical-table-generation', one[1], two[1], TABLES),
]
for method_id, first, second, files in reports:
    report = {
        'method_id': method_id,
        'kind': 'reproducibility',
        'outcome': 'passed',
        'run_one_sha256': first,
        'run_two_sha256': second,
        'files': files,
    }
    (FINDINGS / f'{method_id}-reproducibility.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')
print('Two full offline runs produced identical source partition and categorical table hashes.')
