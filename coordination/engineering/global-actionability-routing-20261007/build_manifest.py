"""Mechanical receipt of actual complete runs; no routing or geometry generation."""
import gzip
import hashlib
import json
import pathlib
import subprocess

ROOT = pathlib.Path.cwd()
OWNED = 'coordination/engineering/global-actionability-routing-20261007'
HERE = ROOT/OWNED
BASE = 'fbc3c4c3a7cb06e8d33d11992b0c26054a9d50d7'
FROZEN = 'cc3c4d72012b33f9f5261302a2eb2d4bcb3b8194'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)+'\n').encode()


def desc(path, body, compressed=False):
    value = dict(path=path, bytes=len(body), sha256=sha(body), hash_kind='file-bytes')
    if compressed or path.endswith('.gz'):
        raw = gzip.decompress(body)
        value.update(uncompressed_bytes=len(raw), uncompressed_sha256=sha(raw))
    if value['bytes'] > 33554432 or value.get('uncompressed_bytes', 0) > 33554432:
        raise ValueError('Ordinary whole-file byte bound')
    return value


def main():
    config = json.loads((HERE/'input-config.json').read_bytes())
    declared = config['candidate_inputs'] + [d for g in config['source_groups'] for d in g['files']] + [config['remaining_plan']] + config['provenance_inputs']
    if len({d['path'] for d in declared}) != len(declared):
        raise ValueError('Duplicate ordinary declared source path')
    baseline = []
    for entry in declared:
        body = subprocess.check_output(['git', 'show', BASE + ':' + entry['path']])
        value = desc(entry['path'], body, 'uncompressed_bytes' in entry)
        if any(value.get(k) != entry[k] for k in ('bytes','sha256','uncompressed_bytes','uncompressed_sha256') if k in entry):
            raise ValueError('Actual containing baseline bytes differ from consumed immutable source')
        baseline.append(value)
    sources = []
    categories = [('audited-original-current-lineage', 'Frozen full original/current fragment/component/contact/residue identity and context, no live-release assertion.',
        next(d['path'] for d in config['candidate_inputs'] if d['kind'] == 'audit_report'))]
    categories += [(g['namespace'], 'Complete original emitted observation/identity collection; original citations/reuse terms/date/source-fitness limits remain in authenticated predecessor manifests.',
        'coordination/engineering/' + g['namespace'] + '/') for g in config['source_groups']]
    categories += [('complete-original-remaining-member-allocation', 'Complete original recipe/member/source prerequisites and disjoint remaining allocations; not source fitness or ready ownership.', config['remaining_plan']['path'])]
    for identity, role, path in categories:
        sources.append(dict(id=identity, url='https://github.com/ChengshuLi/WorldAtlas/tree/' + BASE + '/' + path,
            role=role, vintage='Immutable repository artifact delivery ' + BASE + '; audited c6 cohort and original predecessor execution/source vintages retained, not new observations.',
            retrieved_at='2026-10-07; exact full immutable Git read windows and runtime in both actual-execution receipts.',
            license=dict(status='unknown', terms='Existing repository-derived evidence reused through original immutable Git containing bodies; all underlying original terms/credits remain in consumed predecessor manifests, not newly approved or overridden.'),
            retention='restoration-only', restoration='Read complete baseline containing bodies with their exact encoded/decoded hashes; see input-config.json and actual complete run input receipts. No new upstream source bytes are copied.',
            verification='unverified', temporal_status='unknown', limit='Original physical/political/date/source-fitness and processing-cause authority remains unapproved; byte authentication is not factual verification.'))
    files = sorted(p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name != 'evidence-quality.json')
    outputs = [dict(desc(p.relative_to(ROOT).as_posix(), p.read_bytes()), role='evidence') for p in files]
    report_path = OWNED + '/results/report.json'
    report = json.loads((ROOT/report_path).read_bytes())
    report_desc = next(d for d in outputs if d['path'] == report_path)
    summary_part = next(b for b in report['complete_whole_raw_bodies'] if b['name'] == 'global-summary')['parts']
    if len(summary_part) != 1:
        raise ValueError('Small whole summary must remain one ordinary JSON-containing part')
    summary_path = OWNED + '/results/' + summary_part[0]['path']
    summary = json.loads(gzip.decompress((ROOT/summary_path).read_bytes()))
    summary_desc = next(d for d in outputs if d['path'] == summary_path)
    values = [('components',95173,'components','/counts/components',report_path,report_desc),
        ('families',15610,'families','/counts/families',report_path,report_desc),
        ('operational-batches',594,'batches','/counts/operational_batches',report_path,report_desc),
        ('administrative-bindings',57785,'components','/counts/admin_bindings',report_path,report_desc),
        ('numeric-first',summary['numeric_closure_component_count'],'components','/numeric_closure_component_count',summary_path,summary_desc),
        ('compatible-land-source-fitness',summary['exclusive_next_prerequisite_counts']['land-plus-compatible-original-processing-reproduction-candidate'],'components',
        '/exclusive_next_prerequisite_counts/land-plus-compatible-original-processing-reproduction-candidate',summary_path,summary_desc)]
    metrics = [dict(id=i, value=v, unit=u, vintage='archived', input_sha256=d['sha256'], evaluation_commit=FROZEN) for i,v,u,p,f,d in values]
    bindings = [dict(metric_id=i, path=f, json_pointer=p) for i,v,u,p,f,d in values]
    method_id = 'complete-fixed-metadata-routing'
    method = dict(id=method_id, kind='generator', helper_version='worldatlas-evidence-preparation-v1',
        description='Complete immutable ordinary-body metadata joins with exact full-record/current-lineage proof, full family/batch partitions, exclusive numerical/source prerequisites, inherited whole unknowns, exact sums of existing binary64 measurements and ordered whole-byte gzip restoration. No geometry operations, source/grid/world generation or approvals.',
        software='Python3.12.14 standard library; full committed cc3 producer/config/transitive import closure; copied unmodified existing b7ff immutable.py codec.',
        units='component/family/batch identities, whole bytes/SHA256; sums of previously emitted square-metres only; boundary metres explicitly unknown.')
    validation = [dict(method_id=method_id, kind=k, outcome='passed', evidence_path=OWNED+'/verification/'+method_id+'-'+k+'.json')
        for k in ('positive-control','negative-control','reproducibility')]
    pins = {}
    pin_files = {}
    expected = dict(audited_successor_report='3d95a15d3797943290997c9a16fede48e6eb6e0941b0071a5fcd410375c49d46',
        current_component_delta='21ad3c832ef294cae76d5e6603e61313fc2890a1a5653667caef8665374de460',
        physical_scientific_report='2a5b59198681d50f577bc4c2c321174f166aec14f57c7564100fc411ae940df0',
        existing_lossless_codec='b7ff607b7774595788396e94f08fc29d750e4032624eb93732a5735c1ddcf7fd')
    for name, digest in expected.items():
        value = next(d for d in baseline if d['sha256'] == digest)
        pins[name] = digest
        pin_files[name] = value['path']
    manifest = dict(version=1, issue=1298, lane='engineering', worker_id='01a112b0-1bc7-7343-8411-07b91825d3f9',
        subject_ids=[], subject_ids_sha256=sha(b'[]'), baseline=dict(commit=BASE, files=baseline, pins=pins, pin_files=pin_files),
        sources=sources, outputs=outputs, methods=[method], validation=validation, metrics=metrics, metric_bindings=bindings,
        summaries=[], conclusions=[dict(text='Complete prerequisite routing delivered for the frozen audited cohort; all source/date/physical/political/processing-cause approvals and fresh claim eligibility remain unresolved. Parent1202 repairs/prevention unfinished.', status='unresolved', source_ids=[s['id'] for s in sources])],
        stages=dict(research='partial', implementation='implemented', geographic_approval='not-requested'),
        commands=['PYTHONDONTWRITEBYTECODE=1 python -B ' + OWNED + '/run.py --repo . --execution ' + FROZEN + ' --out ABSOLUTE_ABSENT_OWNED_DIRECTORY'],
        change_receipts=[dict(path=p.relative_to(ROOT).as_posix(), status='added') for p in files] + [dict(path=OWNED+'/evidence-quality.json',status='added')])
    all_descriptors = baseline + outputs
    total = sum(d['bytes'] for d in all_descriptors)
    if len(all_descriptors) > 512 or total > 268435456:
        raise ValueError('Complete actual ordinary aggregate/descriptor budget exceeded')
    (HERE/'evidence-quality.json').write_bytes(canonical(manifest))
    print(json.dumps(dict(status='mechanically-prepared', descriptors=len(all_descriptors), encoded_bytes=total,
        max_decoded=max(d.get('uncompressed_bytes',d['bytes']) for d in all_descriptors), changed_paths=len(files)+1)))


if __name__ == '__main__':
    main()
