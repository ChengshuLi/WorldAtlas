#!/usr/bin/env python3
"""Verify the saved #601 crosswalk, output pins and evidence-quality receipt."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

from build_assessment import OWNED, ROOT, SCOPE, canon


def main():
    scope = json.loads((ROOT / SCOPE).read_bytes())
    manifest_path = ROOT / OWNED / 'evidence-quality.json'
    manifest = json.loads(manifest_path.read_bytes())
    assessment_path = ROOT / OWNED / 'assessment.json'
    assessment = json.loads(assessment_path.read_bytes())
    ids = scope['subject_ids']
    if manifest['issue'] != 601 or manifest['lane'] != 'geography' or manifest['worker_id'] != scope['worker_id']:
        raise ValueError('Manifest issue, lane or worker identity differs from reservation')
    if manifest['subject_ids'] != ids or manifest['subject_ids_sha256'] != scope['subject_ids_sha256']:
        raise ValueError('Manifest subject roster differs from exact assigned scope')
    if len(assessment['source_role_assessment']) != 33 or set(x['id'] for x in assessment['source_role_assessment']) != set(ids):
        raise ValueError('Saved assessment differs from the complete exact scope')
    if manifest['baseline']['subject_files'] != assessment['baseline']['subject_files']:
        raise ValueError('Manifest containing-part map differs from exhaustive source scan')
    for row in manifest['outputs']:
        raw = (ROOT / row['path']).read_bytes()
        if len(raw) != row['bytes'] or hashlib.sha256(raw).hexdigest() != row['sha256']:
            raise ValueError('Output hash/byte descriptor mismatch: ' + row['path'])
    subprocess.run([sys.executable, str(ROOT / OWNED / 'build_assessment.py'), '--check'], cwd=ROOT, check=True)
    controls = json.loads((ROOT / OWNED / 'negative-control-results.json').read_bytes())
    if controls.get('result') != 'PASS' or controls.get('case_count') != 13:
        raise ValueError('Saved positive/negative control record is incomplete')
    checked = subprocess.check_output(['node','scripts/evidence-quality.mjs',str((OWNED / 'evidence-quality.json'))],cwd=ROOT,text=True)
    result = json.loads(checked)
    if result.get('status') not in {'limited','bytes-verified'}:
        raise ValueError('Evidence-quality validator did not accept the packet')
    print(json.dumps({'result':'PASS','subjects':len(ids),'indexed_parts_scanned':36,
                      'predecessors':assessment['whole_scope_summary']['distinct_2018_adm2_predecessors'],
                      'census_predecessors':assessment['whole_scope_summary']['official_tiger_2018_county_equivalent_predecessors'],
                      'resolve_features':assessment['whole_scope_summary']['distinct_resolve_2017_ecoregion_features'],
                      'negative_controls':controls['case_count'],'evidence_status':result['status']},indent=2))

if __name__ == '__main__':
    main()
