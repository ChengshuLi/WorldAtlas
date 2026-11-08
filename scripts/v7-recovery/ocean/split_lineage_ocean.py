#!/usr/bin/env python3
"""Research-only ocean fill with separately pinned prefill and ocean decisions.

The snapshots are evidence, not authenticated Neon exports. No existing
single-snapshot validation is weakened and no output is published.
"""
import argparse, hashlib, json, time
from pathlib import Path
import ocean_fill_runner as ocean
import partition_core, rle_inputs, exclusive_outputs


def _bindings(snapshot):
    rows = snapshot.get('category_bindings')
    if not isinstance(rows, list):
        raise ValueError('missing category bindings')
    result = set()
    for row in rows:
        item = (row.get('entity_id'), row.get('code'), row.get('physical_class'))
        if (type(item[0]) is not int or type(item[1]) is not int
                or item[2] not in ('land', 'water') or item in result):
            raise ValueError('invalid category bindings')
        result.add(item)
    if (not result or len(result) != len({x[1] for x in result})
            or len(result) != len({(x[0],x[2]) for x in result})
            or {x[2] for x in result} != {'land', 'water'}):
        raise ValueError('invalid or duplicate category codes')
    return result


def validate(ocean_snapshot, prefill_snapshot, prefill_sha, plan, audit, candidate, hashes):
    """Validate both branches of lineage before launching or finalizing a fill."""
    o = ocean_snapshot.get('decision_revision', {})
    b = prefill_snapshot.get('decision_revision', {})
    e = o.get('entity_revision')
    if (ocean_snapshot.get('source') != 'neon-export'
            or ocean_snapshot.get('schema') != 'worldatlas-geography-decision-draft-evidence-v1'
            or o.get('status') != 'draft' or not o.get('id') or not e
            or ocean_snapshot.get('entity_revision', {}).get('id') != e
            or ocean_snapshot.get('entity_revision', {}).get('status') != 'draft'):
        raise ValueError('a draft Neon ocean snapshot is required')
    if (o.get('evidence', {}).get('base_local_snapshot_sha256') != prefill_sha
            or b.get('entity_revision') != e
            or prefill_snapshot.get('entity_revision', {}).get('id') != e
            or _bindings(prefill_snapshot) != _bindings(ocean_snapshot)):
        raise ValueError('prefill and ocean snapshot lineage or registry mismatch')
    if (audit.get('schema') != 'worldatlas-v7-prefill-class-rle-audit-v1'
            or audit.get('status') != 'staged-not-published'
            or audit.get('prior_ocean_water_labels_read') != 'none'
            or audit.get('source_plan_sha256') != hashes['plan']
            or audit.get('decision_snapshot_sha256') != prefill_sha
            or plan.get('decision_snapshot_sha256') != prefill_sha
            or audit.get('decision_revision') != b.get('id')
            or plan.get('decision_revision') != b.get('id')
            or audit.get('entity_revision') != e or plan.get('entity_revision') != e):
        raise ValueError('prefill audit, plan, or snapshot mismatch')
    physical = plan.get('rle_inputs', {}).get('physical', {})
    output = audit.get('output', {})
    if (any(not ocean.HEX.fullmatch(str(x or '')) for x in hashes.values())
            or not ocean.HEX.fullmatch(str(audit.get('physical_mask_sha256') or ''))
            or not ocean.HEX.fullmatch(str(physical.get('report_sha256') or ''))
            or physical.get('rows_sha256') != hashes['physical_rows']
            or physical.get('runs_sha256') != hashes['physical_runs']
            or physical.get('physical_mask_sha256') != audit.get('physical_mask_sha256')
            or output.get('rows_sha256') != hashes['prefill_rows']
            or output.get('runs_sha256') != hashes['prefill_runs']):
        raise ValueError('physical or prefill grid binding mismatch')
    grid = plan.get('grid', {})
    if (candidate.get('schema') != 'worldatlas-direct-candidate-build-v1'
            or candidate.get('status') != 'unverified-research-not-published'
            or candidate.get('decision_snapshot_sha256') != hashes['ocean_snapshot']
            or candidate.get('decision_revision') != o['id'] or candidate.get('entity_revision') != e
            or candidate.get('physical_rows_sha256') != hashes['physical_rows']
            or candidate.get('physical_runs_sha256') != hashes['physical_runs']
            or candidate.get('physical_mask_sha256') != audit.get('physical_mask_sha256')
            or candidate.get('physical_report_sha256') != physical.get('report_sha256')
            or candidate.get('grid', {}).get('width') != grid.get('width')
            or candidate.get('grid', {}).get('height') != grid.get('height')):
        raise ValueError('ocean candidate build binding mismatch')
    if type(grid.get('width')) is not int or type(grid.get('height')) is not int or grid['width'] <= 0 or grid['height'] <= 0:
        raise ValueError('invalid grid dimensions')
    return grid['width'], grid['height']


def main(argv=None, *, emit=print):
    processing_started=time.perf_counter()
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('ocean-snapshot', 'ocean-snapshot-sha256', 'prefill-snapshot', 'prefill-snapshot-sha256',
                 'prefill-plan', 'prefill-dir', 'physical-rows', 'physical-runs',
                 'candidate-build', 'candidate-build-sha256', 'out'):
        p.add_argument('--' + name, required=True)
    p.add_argument('--allow-unverified-snapshots', action='store_true')
    p.add_argument('--allow-draft-snapshot', action='store_true')
    a = p.parse_args(argv)
    if not a.allow_unverified_snapshots or not a.allow_draft_snapshot:
        raise ValueError('explicit unverified and draft research opt-ins required')
    files = {'ocean_snapshot': Path(a.ocean_snapshot), 'prefill_snapshot': Path(a.prefill_snapshot),
             'plan': Path(a.prefill_plan), 'physical_rows': Path(a.physical_rows),
             'physical_runs': Path(a.physical_runs), 'candidate': Path(a.candidate_build),
             'audit': Path(a.prefill_dir) / 'prefill-audit.json'}
    audit_raw=files['audit'].read_bytes(); audit=json.loads(audit_raw); prefill = Path(a.prefill_dir).resolve()
    for key in ('rows', 'runs'):
        f = (prefill / audit['output'][key + '_path']).resolve()
        if not f.is_relative_to(prefill): raise ValueError('prefill path escapes input directory')
        files['prefill_' + key] = f
    out = Path(a.out).resolve()
    if out.is_relative_to(prefill) or any(out == x.resolve() or x.resolve().is_relative_to(out) or
           (x.is_dir() and out.is_relative_to(x.resolve())) for x in files.values()):
        raise ValueError('output must be separate from all inputs')
    hashes = {k: ocean.sha(v) for k, v in files.items()}
    if hashlib.sha256(audit_raw).hexdigest()!=hashes['audit']:
        raise ValueError('prefill audit changed while being read')
    if (hashes['ocean_snapshot'] != a.ocean_snapshot_sha256
            or hashes['prefill_snapshot'] != a.prefill_snapshot_sha256
            or hashes['candidate'] != a.candidate_build_sha256):
        raise ValueError('supplied input hash mismatch')
    def pinned_json(key):
        raw=files[key].read_bytes()
        if hashlib.sha256(raw).hexdigest()!=hashes[key]:raise ValueError('JSON input changed while being read: '+key)
        return json.loads(raw)
    ocean_snapshot=pinned_json('ocean_snapshot');baseline=pinned_json('prefill_snapshot')
    plan=pinned_json('plan');candidate=pinned_json('candidate')
    width, height = validate(ocean_snapshot, baseline, a.prefill_snapshot_sha256, plan, audit, candidate, hashes)
    execution_paths={'adapter':Path(__file__).resolve(),'ocean_runner':Path(ocean.__file__).resolve(),
                     'partition_core':Path(partition_core.__file__).resolve(),'rle_inputs':Path(rle_inputs.__file__).resolve(),
                     'exclusive_outputs':Path(exclusive_outputs.__file__).resolve()}
    execution_hashes={k:ocean.sha(v) for k,v in execution_paths.items()}
    pins = {'split_execution_code_sha256':execution_hashes,'physical_rows_sha256': hashes['physical_rows'], 'physical_runs_sha256': hashes['physical_runs'],
            'physical_mask_sha256': audit['physical_mask_sha256'], 'prefill_rows_sha256': hashes['prefill_rows'],
            'prefill_runs_sha256': hashes['prefill_runs'], 'prefill_audit_sha256': hashes['audit'],
            'prefill_plan_sha256': hashes['plan'], 'prefill_decision_snapshot_sha256': hashes['prefill_snapshot'],
            'prefill_decision_revision': baseline['decision_revision']['id'], 'candidate_build_sha256': hashes['candidate'],
            'lineage_mode': 'separately-pinned-prefill-and-ocean-research-decisions'}
    def recheck():
        if (any(ocean.sha(v)!=execution_hashes[k] for k,v in execution_paths.items())
                or any(ocean.sha(v) != hashes[k] for k, v in files.items())):
            raise ValueError('an input changed during ocean fill')
    recheck()
    ocean.run(ocean_snapshot, hashes['ocean_snapshot'], files['physical_rows'], files['physical_runs'],
              files['prefill_rows'], files['prefill_runs'], out, width, height, pins,
              allow_draft=True, software_versions=candidate.get('software_versions', {}), pre_finalize=recheck, pre_summary=recheck, processing_started=processing_started)
    try:
        recheck()
    except Exception:
        summary=out/'run-summary.json'
        if summary.exists():summary.rename(out/'run-summary-invalid.json')
        raise
    emit(json.dumps({'status': 'unverified-research-not-published', 'output': str(out),
                      'summary_sha256': ocean.sha(out / 'run-summary.json')}))

if __name__ == '__main__':
    main()
