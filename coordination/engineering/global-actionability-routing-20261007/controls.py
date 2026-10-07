"""Directed actual-reader and complete-cohort controls; never spatial tests."""
import copy
import gzip
import pathlib
import subprocess
import tempfile
import inputs
import producer


def run(join, source_repo):
    passed = []

    def reject(name, call):
        try:
            call()
        except (ValueError, KeyError, AssertionError, subprocess.CalledProcessError):
            passed.append(dict(name=name, expected='reject', status='PASS'))
        else:
            raise AssertionError('Control unexpectedly admitted: ' + name)

    P = join['physical']
    F = join['families']
    B = join['batches']
    producer.family_partitions(F, B, P)
    passed.append(dict(name='actual-complete-95173-15610-594-partitions', expected='accept', status='PASS'))
    reject('complete-family-omission', lambda: producer.family_partitions(F[1:], B, P))
    reject('complete-family-extra-duplicate', lambda: producer.family_partitions(F + [F[0]], B, P))
    reject('complete-batch-omission', lambda: producer.family_partitions(F, B[1:], P))
    reject('complete-batch-extra-duplicate', lambda: producer.family_partitions(F, B + [B[0]], P))
    altered = dict(F[0], component_ids=F[0]['component_ids'][1:])
    reject('actual-family-member-omission', lambda: producer.family_partitions([altered] + F[1:], B, P))
    altered = dict(B[0], fine_family_ids=B[0]['fine_family_ids'][1:])
    reject('actual-batch-family-omission', lambda: producer.family_partitions(F, [altered] + B[1:], P))
    actual = next(i for i, row in P.items() if producer.reason_flags(row)[0] and i in join['admin'])
    if producer.next_prerequisite(P[actual], join['admin'][actual]) != 'engineering-numeric-closure-first':
        raise AssertionError('Actual numeric prerequisite suppressed by original-source availability')
    passed.append(dict(name='actual-numeric-first-with-original-admin-availability', component=actual,
        expected='engineering-numeric-closure-first', status='PASS'))
    allocations, sets = producer.complete_plan_sets(join['plan'], join['family_by_id'], join['admin'])
    if not sets['missing_recorded_source_bindings'] <= sets['complement_outside_B']:
        raise AssertionError('Source-empty subset accounting')
    passed.append(dict(name='actual-5139-source-empty-subset-not-addition', expected='accept', status='PASS'))
    modified = copy.deepcopy(join['plan'])
    key = next(iter(allocations))
    entry = next(x for x in modified['complete_family_allocations'] if x['family'] == key)
    entry['component_ids'] = list(reversed(entry['component_ids'])) if len(entry['component_ids']) > 1 else []
    reject('actual-remaining-members-reordered-or-omitted', lambda: producer.complete_plan_sets(modified, join['family_by_id'], join['admin']))
    modified = copy.deepcopy(join['plan'])
    modified['complete_family_allocations'].append(modified['complete_family_allocations'][0])
    reject('actual-remaining-allocation-duplicate', lambda: producer.complete_plan_sets(modified, join['family_by_id'], join['admin']))
    products = producer.routing_products(join)
    families = products['families'][0]
    land = products['land-source-fitness'][0]
    if len(land) != 1005 or len({r['family'] for r in land}) != 711 or any(
        r['original_responsible_role'] != 'GEO-source-research' or
        r['source_fitness_prerequisite'] != 'GEO-source-fitness-before-processing-reproduction' for r in land):
        raise AssertionError('GEO source-fit prerequisite lost')
    passed.append(dict(name='actual-all-1005-land-711-wholefamily-GEO-prerequisites', expected='accept', status='PASS'))
    flagged = {i for i, m in join['metadata'].items() if m[0].get('unmeasured_fragment_ids')}
    retained = {i for f in families for i in f['unmeasured_components']}
    if retained != flagged or len(flagged) != 5:
        raise AssertionError('Actual unmeasured fragment flags lost')
    passed.append(dict(name='actual-all-five-unmeasured-fragment-components-retained', expected='accept', status='PASS'))
    if any(f['boundary_length_m'] is not None for f in families) or any(b['boundary_length_m'] is not None for b in products['batches'][0]):
        raise AssertionError('Boundary metres invented')
    passed.append(dict(name='actual-all-family-batch-boundary-metres-unknown', expected='accept', status='PASS'))

    def rational(x):
        return producer.Fraction(int(x['numerator']), int(x['denominator']))
    global_summary = products['global-summary'][0]
    for label, rows in [('fine-families', families), ('operational-batches', products['batches'][0])]:
        if sum((rational(r['exact_existing_fragment_area_sum_m2']) for r in rows), producer.Fraction()) != rational(global_summary['exact_existing_fragment_area_sum_m2']):
            raise AssertionError('Exact original fragment measurement partition sum differs')
        for relation, expected in global_summary['exact_existing_support_area_sums_m2'].items():
            if sum((rational(r['exact_existing_support_area_sums_m2'][relation]) for r in rows), producer.Fraction()) != rational(expected):
                raise AssertionError('Exact original support measurement partition sum differs')
        passed.append(dict(name='actual-' + label + '-exact-original-measurement-reconciliation', expected='accept', status='PASS'))
    raw = b'actual-reader-fixture\n'
    descriptor = dict(bytes=len(raw), sha256=producer.digest(raw))
    compressed = gzip.compress(raw, mtime=0)
    compressed_desc = dict(bytes=len(compressed), sha256=producer.digest(compressed),
        uncompressed_bytes=len(raw), uncompressed_sha256=producer.digest(raw))
    reject('reader-whole-byte-corruption', lambda: inputs.checked_encoded(raw[:-1] + b'X', descriptor))
    reject('reader-whole-size-corruption', lambda: inputs.checked_encoded(raw, dict(descriptor, bytes=len(raw)+1)))
    reject('reader-declared-encoded-overbound', lambda: inputs.checked_encoded(raw, dict(descriptor, bytes=inputs.LIMIT+1)))
    reject('reader-decoded-hash-corruption', lambda: inputs.checked_decoded(compressed, dict(compressed_desc, uncompressed_sha256='0'*64)))
    reject('reader-decoded-overbound', lambda: inputs.checked_decoded(compressed, dict(compressed_desc, uncompressed_bytes=inputs.LIMIT+1)))
    for path in ('/absolute', '../escape', 'a/../escape', 'a\\escape', 'a//b'):
        reject('reader-unsafe-path-' + path, lambda path=path: inputs.safe_path(path))
    with tempfile.TemporaryDirectory() as temporary:
        repo = pathlib.Path(temporary)
        def git(*args, **kwargs):
            return subprocess.check_output(['git', '-C', str(repo), *args], stderr=subprocess.PIPE, **kwargs)
        git('init', '--quiet')
        oid = git('hash-object', '-w', '--stdin', input=raw).decode().strip()
        linkoid = git('hash-object', '-w', '--stdin', input=b'ordinary').decode().strip()
        tree = git('mktree', input=f'100644 blob {oid}\tordinary\n120000 blob {linkoid}\tlink\n'.encode()).decode().strip()
        commit = git('-c', 'user.name=Directed control', '-c', 'user.email=controls@invalid', 'commit-tree', tree,
            input=b'Bounded ordinary reader fixture\n').decode().strip()
        if inputs.ordinary_git(repo, commit, 'ordinary', descriptor) != raw:
            raise AssertionError('Actual Git whole-body reader positive')
        passed.append(dict(name='actual-Git-ordinary-reader', expected='accept', status='PASS'))
        reject('actual-Git-symlink-not-ordinary', lambda: inputs.ordinary_git(repo, commit, 'link', dict(bytes=8, sha256=producer.digest(b'ordinary'))))
        reject('actual-Git-missing-source', lambda: inputs.ordinary_git(repo, commit, 'missing', descriptor))
        reject('actual-Git-short-commit', lambda: inputs.ordinary_git(repo, commit[:8], 'ordinary', descriptor))
        reject('actual-Git-branch-vintage', lambda: inputs.ordinary_git(repo, 'main', 'ordinary', descriptor))
        reject('actual-Git-body-hash-corruption', lambda: inputs.ordinary_git(repo, commit, 'ordinary', dict(descriptor, sha256='0'*64)))

    desc = next(d for d in join['input_receipts'] if d.get('kind') == 'components')
    source_raw = inputs.ordinary_git(source_repo, desc['commit'], desc['path'], desc)
    original = producer.json.loads(inputs.checked_decoded(source_raw, desc))
    source_feature = original['features'][0] if isinstance(original, dict) else original[0]
    for field in ('geometry', 'properties'):
        changed = copy.deepcopy(original)
        feature = changed['features'][0] if isinstance(changed, dict) else changed[0]
        feature[field] = {} if field == 'properties' else {'type': 'Polygon', 'coordinates': []}
        modified_raw = producer.canonical(changed)
        modified_encoded = producer.immutable.deterministic_gzip(modified_raw) if 'uncompressed_bytes' in desc else modified_raw
        reject('actual-whole-candidate-' + field + '-mismatch', lambda raw=modified_encoded: inputs.checked_encoded(raw, desc))

    features = original['features'] if isinstance(original, dict) else original
    if len(features) < 2:
        raise AssertionError('Actual whole source fixture lacks reorder coverage')
    reordered = dict(original, features=list(reversed(features))) if isinstance(original, dict) else list(reversed(features))
    reordered_raw = producer.canonical(reordered)
    reordered_encoded = producer.immutable.deterministic_gzip(reordered_raw) if 'uncompressed_bytes' in desc else reordered_raw
    reject('actual-original-candidate-reordered-identities', lambda: inputs.checked_encoded(reordered_encoded, desc))
    from run import checked_execution
    reject('execution-branch-name-not-fixed-vintage', lambda: checked_execution(source_repo, 'HEAD'))
    reject('execution-shortsha-not-fixed-vintage', lambda: checked_execution(source_repo, desc['commit'][:8]))

    class RehashedWholeFixture:
        def __init__(self, raw):
            self.raw = raw
            self.descriptor = dict(path='actual-whole-rehashed.json', bytes=len(raw), sha256=producer.digest(raw))
        def read(self, desc):
            if desc != self.descriptor:
                raise ValueError('Fixture descriptor differs')
            return inputs.checked_decoded(self.raw, desc)

    physical_desc = next(d for d in join['input_receipts'] if '/results/components-' in d['path'])
    physical_raw = inputs.checked_decoded(inputs.ordinary_git(source_repo, physical_desc['commit'], physical_desc['path'], physical_desc), physical_desc)
    actual_physical = producer.json.loads(physical_raw.splitlines()[0])
    actual_id = actual_physical['component_id']
    one_metadata = {actual_id: join['metadata'][actual_id]}
    for name, rows in [('foreign', [dict(actual_physical, component_id='foreign-component')]),
        ('duplicate', [actual_physical, actual_physical])]:
        fixture = RehashedWholeFixture(b''.join(producer.canonical(r) for r in rows))
        reject('authentic-rehashed-physical-' + name + '-identity',
            lambda fixture=fixture: producer.physical_records(fixture, [fixture.descriptor], one_metadata))
    admin_desc = next(d for d in join['input_receipts'] if '/scientific/components-' in d['path'])
    admin_raw = inputs.checked_decoded(inputs.ordinary_git(source_repo, admin_desc['commit'], admin_desc['path'], admin_desc), admin_desc)
    actual_admin = producer.json.loads(admin_raw)[0]
    for name, rows in [('foreign', [dict(actual_admin, component='foreign-component')]),
        ('duplicate', [actual_admin, actual_admin]),
        ('geometry-binding', [dict(actual_admin, component_geometry_sha256='0'*64)]),
        ('full-context-binding', [dict(actual_admin, full_component_feature_sha256='0'*64)])]:
        fixture = RehashedWholeFixture(producer.canonical(rows))
        group = dict(namespace='actual-rehashed-reader-control', files=[fixture.descriptor])
        reject('authentic-rehashed-admin-' + name,
            lambda fixture=fixture, group=group: producer.administrative_records(fixture, [group], P, join['metadata']))
    config = producer.json.loads((producer.HERE/'input-config.json').read_bytes())
    reject('actual-wrong-fixed-delivery-vintage', lambda: producer.metadata_join(source_repo, dict(config, source_delivery='0'*40)))
    selected = next(d for d in join['input_receipts'] if d.get('kind') == 'reconstruction_code')
    helper = inputs.ordinary_git(source_repo, selected['commit'], selected['path'], selected)
    reject('actual-frozen-helper-whole-body-mutation', lambda: inputs.existing_reconstructor(helper + b'\n', selected['sha256'], producer.canonical))
    return dict(status='PASS', actual_directed_controls=len(passed), controls=passed,
        limits=['Metadata and actual ordinary reader controls only; no geometry predicates or source approval.'])
