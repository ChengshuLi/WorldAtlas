"""Build the existing evidence-quality v1 contract from actual #1423 receipts."""
import gzip, hashlib, json, pathlib, subprocess

R = pathlib.Path(__file__).resolve().parents[3]
N = 'coordination/engineering/angola-original-envelope-20261007/'
P = R / N
EXEC = '70f28d005157f2d32a56cd48b97a046613c37494'
METHOD = 'bounded-archive-conditional-mechanism'


def canonical(v):
    return (json.dumps(v, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode()


def digest(b):
    return hashlib.sha256(b).hexdigest()


def descriptor(name, raw):
    row = {'path': name, 'bytes': len(raw), 'sha256': digest(raw), 'hash_kind': 'file-bytes'}
    if name.endswith('.gz'):
        decoded = gzip.decompress(raw)
        row.update(uncompressed_bytes=len(decoded), uncompressed_sha256=digest(decoded))
    return row


def exclusive(name, value):
    path = P / name
    if path.exists() or path.is_symlink():
        raise ValueError('Fresh manifest support artifact required')
    path.write_bytes(canonical(value))


def main():
    issue = json.loads(subprocess.check_output(['gh', 'api', 'repos/ChengshuLi/WorldAtlas/issues/1423']))
    spec = json.loads(issue['body'].split('<!-- worldatlas-work:v1\n')[1].split('\n-->')[0])
    plan = json.loads((P / 'input-plan.json').read_bytes())
    equality = json.loads((P / 'vintages/final-focused-invocations/equality.json').read_bytes())
    invocations = json.loads((P / 'vintages/final-focused-invocations/invocations.json').read_bytes())
    controls = json.loads((P / 'vintages/final-controls/controls.json').read_bytes())
    admission = json.loads((P / 'vintages/final-admission-invocations/one.stdout.txt').read_bytes())
    if admission['execution_commit'] != EXEC or admission['status'] != 'complete-input-only-admission-no-GIS-import-or-calculation':
        raise ValueError('Actual standalone same-freeze input-only admission absent')
    if not equality['all_paired_scientific_products_equal'] or len(equality['complete_product_sets']) != 2:
        raise ValueError('Actual complete pair absent')
    if invocations['execution_commit'] != EXEC or any(not r['executed'] or r['returncode'] for r in invocations['invocations']):
        raise ValueError('Actual two successful invocations absent')
    for run, expected in zip(['one', 'two'], equality['complete_product_sets']):
        if len(expected) != len(plan['output_names']):
            raise ValueError('Incomplete declared scientific product set')
        for d in expected:
            raw = (P / ('vintages/final-focused-' + run) / d['name']).read_bytes()
            if len(raw) != d['bytes'] or digest(raw) != d['sha256']:
                raise ValueError('Actual paired product body drift')
    if controls['execution_commit'] != EXEC or len(controls['controls']) != 8 or any(not r['returncode'] or not r['no_scientific_output_created'] or r['expected_failure'] not in r['stderr'] for r in controls['controls']):
        raise ValueError('Nonvacuous actual controls absent')
    paired_hashes = [digest(canonical(rows)) for rows in equality['complete_product_sets']]
    if paired_hashes[0] != paired_hashes[1]:
        raise ValueError('Full paired scientific digest mismatch')
    for kind in ['positive-control', 'negative-control', 'reproducibility']:
        value = {'method_id': METHOD, 'kind': kind, 'outcome': 'passed', 'execution_commit': EXEC,
                 'actual_receipt': N + ('vintages/final-controls/controls.json' if kind == 'negative-control' else 'vintages/final-focused-invocations/equality.json'),
                 'interpretation': 'Typed link to retained actual complete executions/controls; no new test or invented pass.'}
        if kind == 'reproducibility':
            value.update(run_one_sha256=paired_hashes[0], run_two_sha256=paired_hashes[1], complete_scientific_product_count=len(plan['output_names']))
        exclusive(kind + '.json', value)
    baseline = []
    for pin in plan['ordinary_inputs']:
        d = {k: pin[k] for k in ['path', 'bytes', 'sha256', 'hash_kind']}
        if 'uncompressed_bytes' in pin:
            d.update(uncompressed_bytes=pin['uncompressed_bytes'], uncompressed_sha256=pin['uncompressed_sha256'])
        baseline.append(d)
    for name in ['run.py', 'producer.py', 'controls.py', 'execute.py', 'input-plan.json', 'runtime-plan.json', 'triage.json', 'source.geojson']:
        raw = subprocess.check_output(['git', '-C', str(R), 'show', EXEC + ':' + N + name])
        baseline.append(descriptor(N + name, raw))
    pin_paths = {}
    for key, expected in spec['evidence_quality']['pins'].items():
        found = [p for p in baseline if p['path'] == key and p['sha256'] == expected]
        if len(found) != 1:
            raise ValueError('Current authoritative issue machine pin lacks ordinary actual binding: ' + key)
        pin_paths[key] = key
    source_name = N + 'source.geojson'
    sources = [
        {'id': 'retained-ago-humanitarian-161', 'url': 'https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbHumanitarian/AGO/ADM2/geoBoundaries-AGO-ADM2.geojson',
         'role': 'Complete actual cached 161-feature source comparison; source coverage is not current assignment, physical land/water or repair approval.',
         'vintage': '2018 source metadata claim; whole raw7cf2a401 immutable semantic member/corpus binding', 'retrieved_at': '2026-10-06; immutable corpus verification, original network retrieval time unknown',
         'license': {'status': 'redistributable', 'terms': 'Retained source metadata declares CC BY3.0IGO; attribution and complete original declarations preserved in pinned corpus/registry. No new legal/admin authority approval.'},
         'retention': 'retained', 'verification': 'unverified', 'temporal_status': 'reference', 'files': [descriptor(source_name, (R / source_name).read_bytes())]},
        {'id': 'undated-ago-archive-158', 'url': 'https://github.com/ChengshuLi/WorldAtlas/blob/4bdba3d40acc2d725e4aeb54c3b9aab559a91469/data/geographic-migration-archive.json.gz',
         'role': 'Complete private immutable19050-record archive custody and selected158 processed inactive reference records; conditional old envelope only.',
         'vintage': 'First retained Git import4bdba3d4; historical_effective_year null; archived158 metadata source year2006 is a claim, not a dated archive.',
         'retrieved_at': '2026-10-07 complete private-stream verification; archive creation/execution date unknown',
         'license': {'status': 'unknown', 'terms': 'Selected158 source metadata declares Public Domain; mixed whole archive source reuse/authority not independently approved.'},
         'retention': 'restoration-only', 'verification': 'unverified', 'temporal_status': 'unknown',
         'restoration': 'Exact immutable original commit/path, whole encoded10765139B SHA9e4ca20b... and decoded56672580B SHAc072bbe6... in input-plan; complete first-pass verification precedes second-pass semantic selection. Selected raw bytes/offsets/hashes retained in both final runs.',
         'limit': 'Explicit private whole decoded archive exceeds ordinary32MiB file cap and is never encoded-only ordinaryPASS; immediate pre-refresh input binding, original unprocessed provider validity, dated physical/source/method/repair approval remain unproven. OS system-library ABI remains un-hashed; installed actually loaded closure is authenticated.'}
    ]
    files = sorted(p for p in P.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name != 'evidence-quality.json')
    if any(p.is_symlink() for p in files):
        raise ValueError('Nonordinary public artifact')
    outputs = [dict(descriptor(str(p.relative_to(R)), p.read_bytes()), role='retained-execution-or-scoped-evidence') for p in files if str(p.relative_to(R)) != source_name]
    comparison_path = N + 'vintages/final-focused-one/comparisons.json'
    comparison = json.loads((R / comparison_path).read_bytes())
    comparison_hash = digest((R / comparison_path).read_bytes())
    metrics = []; bindings = []
    fields = ['native_area_degrees2', 'missing_archived_envelope_degrees2', 'missing_source_degrees2', 'missing_conditional_refresh_degrees2']
    for index, row in enumerate(comparison['components']):
        for field in fields:
            key = row['component'] + ':' + field
            metrics.append({'id': key, 'value': row[field], 'unit': 'square degrees', 'vintage': 'archived', 'evaluation_commit': EXEC, 'input_sha256': comparison_hash})
            bindings.append({'metric_id': key, 'path': comparison_path, 'json_pointer': '/components/' + str(index) + '/' + field})
    changed = subprocess.check_output(['git', '-C', str(R), 'diff', '--name-only', 'origin/main', '--', N]).decode().splitlines()
    untracked = subprocess.check_output(['git', '-C', str(R), 'ls-files', '--others', '--exclude-standard', '--', N]).decode().splitlines()
    changed = sorted(set(changed + untracked + [N + 'evidence-quality.json']))
    manifest = {'version': 1, 'issue': 1423, 'lane': 'engineering', 'worker_id': '01a11735-f553-7231-8651-e8edade22f75',
                'subject_ids': spec['evidence_quality']['subject_ids'], 'subject_ids_sha256': digest(json.dumps(sorted(spec['evidence_quality']['subject_ids']), separators=(',', ':')).encode()),
                'baseline': {'commit': EXEC, 'files': baseline, 'pins': spec['evidence_quality']['pins'], 'pin_files': pin_paths},
                'sources': sources, 'outputs': outputs,
                'methods': [{'id': METHOD, 'kind': 'generator', 'helper_version': 'worldatlas-evidence-preparation-v1',
                             'description': 'Authenticated Baseline/load_modules/materialized reader and NewVintage admission; explicitly reviewed whole private streaming equivalent with complete encoded+decoded identity/all19050 records before158 selection. Literal retained refresh cuts/buffers/voting applied only to conditional archived envelope; original validity preserved. No geography correction/global graph.',
                             'software': 'Exact Python3.12/shapely2.1.2/GEOS captured394-file runtime closure in runtime-plan; OS system ABI trust limit retained.',
                             'units': 'whole bytes/records; literal CRS84 longitude-latitude degrees and planar square-degree diagnostics; no metres or fresh physical area'}],
                'metrics': metrics, 'metric_bindings': bindings, 'summaries': [],
                'validation': [{'method_id': METHOD, 'kind': kind, 'outcome': 'passed', 'evidence_path': N + kind + '.json'} for kind in ['positive-control', 'negative-control', 'reproducibility']],
                'conclusions': [{'source_ids': [s['id'] for s in sources], 'status': 'supported', 'text': 'Complete8-family/10-component/9-contact conditional archived-envelope tests: archive envelope fails full coverage for all10; complete raw161 source fully covers9 and partially covers tenth; literal conditional historical operators preserve omissions. Two same-freeze executions produce all8 scientific/products byte-equal after standalone full admission and8 actual-entry controls.'},
                                {'source_ids': [s['id'] for s in sources], 'status': 'unresolved', 'text': 'Conditional168-adjustment vector differs bytewise from actual report and3/9 current contacts differ. Exact immediate historical input binding/cause, source-date/physical/method/repair approval remain open; no geography mutation, current assignment, original2006 raw-provider recovery, global campaign closure or production acceptance.'}],
                'stages': {'research': 'partial', 'implementation': 'implemented', 'geographic_approval': 'not-requested'},
                'commands': ['Fixed authenticated Python -I -B execute.py --commit' + EXEC + ' --vintage FRESH --admission-only', 'Fixed authenticated Python -I -B controls.py --commit' + EXEC + ' --run FRESH', 'Fixed authenticated Python -I -B execute.py --commit' + EXEC + ' --vintage FRESH'],
                'change_receipts': [{'path': name, 'status': 'added'} for name in changed]}
    if len(baseline) + len(outputs) + sum(len(s.get('files', [])) for s in sources) > 512:
        raise ValueError('Flat ordinary evidence descriptor cap')
    if (P / 'evidence-quality.json').exists():
        raise ValueError('Fresh evidence manifest required')
    (P / 'evidence-quality.json').write_bytes(canonical(manifest))
    print(json.dumps({'manifest': N + 'evidence-quality.json', 'ordinary_baseline_files': len(baseline), 'candidate_outputs': len(outputs), 'metrics': len(metrics), 'changed_files': len(changed), 'private_archive_ordinary_descriptor': False}))


if __name__ == '__main__':
    main()
