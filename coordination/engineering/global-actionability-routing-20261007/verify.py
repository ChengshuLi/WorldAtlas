"""Full delivered metadata readback; no producer invocation or geometry operations."""
import argparse
import collections
from fractions import Fraction
import gzip
import hashlib
import io
import json
import pathlib
import re

LIMIT = 33554432
NUMERIC = {'nonempty-support-closure-disagreement', 'nonempty-polygon-zero-ellipsoidal-area'}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)+'\n').encode()


def read_bodies(root):
    report = json.loads((root/'report.json').read_bytes())
    bodies = {}
    seen = set()
    for body in report['complete_whole_raw_bodies']:
        chunks = []
        for index, descriptor in enumerate(body['parts']):
            expected = f"{body['name']}-{index:03d}.bin.gz"
            if descriptor['path'] != expected or expected in seen:
                raise ValueError('Ordered unique whole-output part identity differs')
            seen.add(expected)
            path = root/expected
            if path.is_symlink() or not path.is_file():
                raise ValueError('Nonordinary output')
            if descriptor['bytes'] > LIMIT or descriptor['uncompressed_bytes'] > LIMIT or path.stat().st_size > LIMIT:
                raise ValueError('Encoded/decoded ordinary output bound')
            raw = path.read_bytes()
            if len(raw) != descriptor['bytes'] or sha(raw) != descriptor['sha256']:
                raise ValueError('Whole encoded output differs')
            with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
                decoded = stream.read(LIMIT + 1)
                if len(decoded) > LIMIT or stream.read(1):
                    raise ValueError('Actual decoded output bound')
            if len(decoded) != descriptor['uncompressed_bytes'] or sha(decoded) != descriptor['uncompressed_sha256']:
                raise ValueError('Whole decoded output differs')
            chunks.append(decoded)
        complete = b''.join(chunks)
        if len(complete) != body['bytes'] or sha(complete) != body['sha256'] or body['name'] in bodies:
            raise ValueError('Whole concatenated raw body identity differs')
        bodies[body['name']] = [json.loads(line) for line in complete.splitlines()] if body['format'] == 'jsonl' else json.loads(complete)
    if seen != {d['path'] for d in report['outputs']}:
        raise ValueError('Whole report descriptor roster differs')
    return report, bodies


def indexed(rows, key):
    out = {r[key]: r for r in rows}
    if len(out) != len(rows):
        raise ValueError('Duplicate complete metadata identity')
    return out


def rational(value):
    return Fraction(int(value['numerator']), int(value['denominator']))


def verify(root):
    report, bodies = read_bodies(root)
    R = indexed(bodies['components'], 'component')
    F = indexed(bodies['families'], 'id')
    B = indexed(bodies['batches'], 'id')
    if (len(R), len(F), len(B)) != (95173,15610,594):
        raise ValueError('Complete global output counts differ')
    numeric = {i for i, r in R.items() if any(x.get('issue') in NUMERIC for x in r['unresolved'])}
    zero = {i for i, r in R.items() if any(x.get('issue') == 'nonempty-polygon-zero-ellipsoidal-area' for x in r['unresolved'])}
    closure = {i for i, r in R.items() if any(x.get('issue') == 'nonempty-support-closure-disagreement' for x in r['unresolved'])}
    additional_zero = zero - closure
    if len(numeric) != 26276 or len(zero) != 10 or len(additional_zero) != 5 or any(R[i]['next_prerequisite'] != 'engineering-numeric-closure-first' for i in numeric):
        raise ValueError('All numerical-first membership, including five zero-area cases, differs')
    family_members = []
    batch_families = []
    batch_members = []
    for identity, family in F.items():
        ids = family['complete_component_ids']
        if ids != family['original_fine_family']['component_ids'] or len(ids) != family['component_count']:
            raise ValueError('Original complete family order/context differs')
        if any(R[i]['family'] != identity or R[i]['operational_batch'] != family['operational_batch'] for i in ids):
            raise ValueError('Complete component/family/batch binding differs')
        if family['numeric_closure_component_ids'] != sorted(set(ids) & numeric):
            raise ValueError('Complete family numerical-first memberships differ')
        if family['exclusive_next_prerequisite_counts'] != dict(collections.Counter(R[i]['next_prerequisite'] for i in ids)):
            raise ValueError('Complete family category partition differs')
        if family['unmeasured_components'] != [i for i in ids if R[i]['unmeasured_fragment_ids']]:
            raise ValueError('Complete family unmeasured fragments differ')
        if family['boundary_length_m'] is not None or family['dispatch_ready']:
            raise ValueError('Unsupported boundary metres/dispatch approval')
        family_members.extend(ids)
    for identity, batch in B.items():
        families = batch['complete_fine_family_ids']
        ids = [i for f in families for i in F[f]['complete_component_ids']]
        if ids != batch['complete_component_ids'] or len(ids) != batch['component_count']:
            raise ValueError('Complete batch ordered memberships differ')
        if any(F[f]['operational_batch'] != identity for f in families):
            raise ValueError('Complete family/batch binding differs')
        if batch['exclusive_next_prerequisite_counts'] != dict(collections.Counter(R[i]['next_prerequisite'] for i in ids)):
            raise ValueError('Complete batch categories differ')
        if batch['numeric_closure_component_count'] != len(set(ids) & numeric) or batch['boundary_length_m'] is not None:
            raise ValueError('Complete batch numerical/boundary facts differ')
        batch_members.extend(ids)
        batch_families.extend(families)
    if len(family_members) != len(set(family_members)) or set(family_members) != set(R) or len(batch_members) != len(set(batch_members)) or set(batch_members) != set(R):
        raise ValueError('Global family/batch component partition differs')
    if len(batch_families) != len(set(batch_families)) or set(batch_families) != set(F):
        raise ValueError('Global family/batch partition differs')
    summary = bodies['global-summary']
    for rows in (F.values(), B.values()):
        if sum((rational(r['exact_existing_fragment_area_sum_m2']) for r in rows), Fraction()) != rational(summary['exact_existing_fragment_area_sum_m2']):
            raise ValueError('Exact original emitted fragment measurement sum differs')
        for relation, total in summary['exact_existing_support_area_sums_m2'].items():
            if sum((rational(r['exact_existing_support_area_sums_m2'][relation]) for r in rows), Fraction()) != rational(total):
                raise ValueError('Exact original emitted support measurement sum differs')
    groups = bodies['B-complement']['sets']
    selected = set(groups['selected_retired_member_B']['complete_component_ids'])
    complement = set(groups['complement_outside_B']['complete_component_ids'])
    remaining = set(groups['all_unscreened_admin']['complete_component_ids'])
    empty = set(groups['missing_recorded_source_bindings']['complete_component_ids'])
    if selected & complement or selected | complement != remaining or not empty <= complement or (len(selected),len(complement),len(empty)) != (20032,17356,5139):
        raise ValueError('Complete original B/complement/source-empty subset differs')
    prerequisite_groups = bodies['remaining-prerequisites']['complement_groups']
    all_ids = [i for g in prerequisite_groups for i in g['complete_component_ids']]
    if len(prerequisite_groups) != 27 or len(all_ids) != len(set(all_ids)) or set(all_ids) != complement:
        raise ValueError('All27 complete complementary prerequisite groups differ')
    land = bodies['land-source-fitness']
    if len(land) != 1005 or len({r['family'] for r in land}) != 711 or any(r['original_responsible_role'] != 'GEO-source-research' or r['source_fitness_prerequisite'] != 'GEO-source-fitness-before-processing-reproduction' for r in land):
        raise ValueError('Complete compatible land/GEO prerequisite differs')
    return dict(status='PASS', report_sha256=sha((root/'report.json').read_bytes()),
        verifier_sha256=sha(pathlib.Path(__file__).read_bytes()), complete_components=len(R), complete_families=len(F),
        complete_batches=len(B), complete_numeric_first=len(numeric), complete_zero_area_numeric_ids=sorted(zero), additional_zero_area_numeric_ids=sorted(additional_zero),
        whole_family_numeric_union_sha256=sha(canonical(sorted(numeric))), exact_measurement_partition_sums='PASS',
        complete_land_source_fitness_components=len(land), complete_land_families=711,
        complete_complement_groups=27, missing_source_bindings_subset=True,
        limits=['Full delivered metadata reconciliation only; no producer/world kernel invocation, spatial predicate or factual/source approval.'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root',required=True)
    parser.add_argument('--receipt',required=True)
    args = parser.parse_args()
    result = verify(pathlib.Path(args.root))
    pathlib.Path(args.receipt).write_bytes(canonical(result))
    print(json.dumps(result,sort_keys=True))
