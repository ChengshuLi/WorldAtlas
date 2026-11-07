#!/usr/bin/env python3
"""Bounded selected Panama source/region/closure audit; does not build a map.

The caller authenticates the snapshot, source custody and physical inputs. The
closure contract is pinned but is not represented as independently reviewed.
"""
import argparse, hashlib, json, tempfile
from pathlib import Path
from export_adapter import boundary_records, load_pinned_snapshot, selected_regions
from panama_seed_source import BOUNDARY, SOURCE, bind
from region_client import execute
from regions import geometry_hash

HERE = Path(__file__).resolve().parent
FREEZE_SHA256 = '179019662572f62991ddb02aef0440a6854b71f93a3e4024e68d34506046e575'

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for data in iter(lambda: f.read(1 << 20), b''): h.update(data)
    return h.hexdigest()

def checked_freeze():
    raw = (HERE / 'source-freeze.sha256').read_bytes()
    if hashlib.sha256(raw).hexdigest() != FREEZE_SHA256: raise ValueError('unreviewed source-freeze manifest')
    pins = {}
    for line in raw.decode('ascii').splitlines():
        digest, name = line.split('  ', 1)
        if name in pins or Path(name).is_absolute() or '..' in Path(name).parts: raise ValueError('invalid source-freeze entry')
        pins[name] = digest
        if sha(HERE / name) != digest: raise ValueError('source-freeze mismatch: ' + name)
    if len(pins) != 14: raise ValueError('incomplete source-freeze manifest')
    return pins

def require_panama_region_usage(decision, source_trace, region_report):
    """Bind the reconstructed line to this region's selected and executed segment."""
    expected = {'kind': 'boundary', 'id': BOUNDARY, 'start': 0,
                'end': source_trace['vertices'], 'reverse': False}
    segments = [x for x in decision['segments'] if x.get('kind') == 'boundary' and x.get('id') == BOUNDARY]
    traces = [x for x in region_report['input_trace'] if x.get('kind') == 'boundary' and x.get('id') == BOUNDARY]
    if len(segments) != 1 or segments[0] != expected or len(traces) != 1:
        raise ValueError('selected region does not consume the full Panama boundary')
    if any(traces[0].get(k) != v for k, v in expected.items()) or traces[0].get('geometry_sha256') != source_trace['geometry_sha256']:
        raise ValueError('executed Panama segment differs from source-derived boundary')

def audit(snapshot_path, snapshot_sha256, archive, physical_dir, contract, contract_sha256):
    pins = checked_freeze()
    snapshot_path, archive, physical_dir, contract = (Path(p).resolve(strict=True) for p in (snapshot_path, archive, physical_dir, contract))
    if sha(contract) != contract_sha256: raise ValueError('closure contract hash mismatch')
    snapshot = load_pinned_snapshot(snapshot_path, snapshot_sha256, lambda: None)
    revision, _, boundaries, catalog = boundary_records(snapshot)
    source = catalog.get(SOURCE)
    if not source: raise ValueError('selected Panama source missing')
    archive_pin = {'path': str(archive), 'sha256': source['sha256']}
    boundaries, source_trace = bind(boundaries, catalog, archive_pin)
    regions, records = selected_regions(snapshot, revision, boundaries)
    matches = [r for r in regions if r['region_id'] == 'north_america_mainland_region_v1']
    if len(matches) != 1 or source_trace is None: raise ValueError('selected Panama region missing')
    decision = matches[0]; policy = snapshot['land_baseline_policy']
    physical = {k: policy[k + '_sha256'] for k in ('physical_rows', 'physical_runs', 'physical_report')}
    for name, key in (('rows.u32le', 'physical_rows'), ('runs.u32le', 'physical_runs'), ('report.json', 'physical_report')):
        if sha(physical_dir / name) != physical[key]: raise ValueError('selected physical input mismatch: ' + name)
    closure = {'checker_path': str(HERE / 'closure-checkers/validate_water_closure_v2.py'),
        'checker_sha256': pins['closure-checkers/validate_water_closure_v2.py'],
        'terminal_checker_path': str(HERE / 'closure-checkers/validate_terminal_closure.py'),
        'terminal_checker_sha256': pins['closure-checkers/validate_terminal_closure.py'],
        'physical_dir': str(physical_dir), 'physical_rows_sha256': physical['physical_rows'],
        'physical_runs_sha256': physical['physical_runs'], 'physical_report_sha256': physical['physical_report'],
        'contract_path': str(contract), 'contract_sha256': contract_sha256}
    request = {'schema': 'stage2-region-worker-direct-request-v2', 'revision_id': revision,
        'records': list(records.values()), 'sources': [{'source_id': k[0], 'version': k[1], **v} for k, v in catalog.items()],
        'decision': decision, 'closure': closure}
    with tempfile.TemporaryDirectory(prefix='panama-selected-region-') as work: result = execute(request, work)
    worker_pins = {k: pins[k] for k in ('region_worker.py', 'regions.py', 'closure_client.py')}
    if result['code_sha256'] != worker_pins or geometry_hash(result['geometry']) != decision['geometry_sha256']:
        raise ValueError('region execution or geometry mismatch')
    require_panama_region_usage(decision, source_trace, result['report'])
    route = [t for t in result['report']['input_trace'] if t['id'] == 'americas_exterior_closure_v1']
    if len(route) != 1 or route[0]['closure_proof']['status'] != 'valid': raise ValueError('selected Americas closure not validated')
    if sha(snapshot_path) != snapshot_sha256 or sha(archive) != archive_pin['sha256'] or sha(contract) != contract_sha256 or checked_freeze() != pins:
        raise ValueError('audit inputs changed during execution')
    proof = route[0]['closure_proof']
    return {'schema': 'panama-selected-region-audit-v1', 'status': 'research-only',
        'snapshot_sha256': snapshot_sha256, 'revision': revision, 'source_trace': source_trace,
        'physical_sha256': physical, 'closure_contract_sha256': contract_sha256,
        'region_id': decision['region_id'], 'region_geometry_sha256': decision['geometry_sha256'],
        'witnesses_checked': len(decision['witnesses']), 'closure_geometry_sha256': proof['geometry_sha256'],
        'closure_verification': proof['verification'], 'worker_code_sha256': worker_pins,
        'limitations': ['Caller authenticates the snapshot, source custody, physical inputs and closure contract.',
            'This audits one region, not complete producer, outer integration or map generation.',
            'The physical report does not independently prove original producer execution.']}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('snapshot', 'snapshot-sha256', 'archive', 'physical-dir', 'contract', 'contract-sha256'):
        p.add_argument('--' + name, required=True)
    a = p.parse_args()
    print(json.dumps(audit(a.snapshot, a.snapshot_sha256, a.archive, a.physical_dir, a.contract, a.contract_sha256), sort_keys=True, indent=2))

if __name__ == '__main__': main()
