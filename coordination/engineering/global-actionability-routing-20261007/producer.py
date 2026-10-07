"""Fixed complete metadata join for #1298. No geometry operations or source approvals."""
import collections
import gzip
import hashlib
import io
import json
import math
import pathlib
import re
import sys
from collections import defaultdict
from fractions import Fraction
import inputs
import immutable

HERE = pathlib.Path(__file__).resolve().parent
EXPECTED_DELIVERY = 'fbc3c4c3a7cb06e8d33d11992b0c26054a9d50d7'
PART_LIMIT = 8 * 1024 * 1024
NUMERIC = {'nonempty-support-closure-disagreement', 'nonempty-polygon-zero-ellipsoidal-area'}


def canonical(value):
    return immutable.canonical_json(value)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def unique(rows, key, label):
    result = {}
    for row in rows:
        identity = row[key]
        if not isinstance(identity, str) or not identity or identity in result:
            raise ValueError('Missing/duplicate ' + label + ' identity')
        result[identity] = row
    return result


def reason_flags(row):
    reasons = row['unresolved']
    return (any(r.get('issue') in NUMERIC for r in reasons),
            any(r.get('issue') == 'positive-or-contact-hierarchy-disagreement' for r in reasons),
            any(r.get('issue') == 'unusable-complete-original-source' for r in reasons))


def next_prerequisite(row, observations):
    numeric, hierarchy, invalid_source = reason_flags(row)
    compatible = any(x['current_binding'] == 'exact-current-geometry' and
        x['status'] == 'one-compatible-recorded-subject-uniquely-covers-component' for x in observations)
    if numeric:
        return 'engineering-numeric-closure-first'
    if hierarchy:
        return 'source-hierarchy-registration-review'
    if invalid_source:
        return 'native-invalid-source-review'
    status = row['status']
    if status == 'unknown':
        return 'remaining-explicit-unknown-review'
    if status == 'mapped-land-support':
        if compatible:
            return 'land-plus-compatible-original-processing-reproduction-candidate'
        return ('land-without-admin-comparison-source-or-processing-custody' if not observations else
                'land-with-admin-partial-or-unbound-source-fitness-review')
    return {'mapped-inland-water-support': 'source-relative-inland-water-retain-for-source-fitness',
            'mixed-source-support': 'mixed-support-retain-whole-source-fitness-review',
            'outside-mapped-L1-context': 'outside-source-domain-unclassified'}[status]


class Reader:
    """Consume each fixed declared ordinary input once; retain whole read relations."""
    def __init__(self, repo):
        self.repo = repo
        self.receipts = {}

    def read(self, descriptor):
        identity = (descriptor['commit'], descriptor['path'])
        if identity in self.receipts:
            raise ValueError('Duplicate declared input relation')
        raw = inputs.ordinary_git(self.repo, *identity, descriptor)
        decoded = inputs.checked_decoded(raw, descriptor)
        self.receipts[identity] = dict(descriptor, actual_encoded_bytes=len(raw),
            actual_encoded_sha256=digest(raw), actual_decoded_bytes=len(decoded),
            actual_decoded_sha256=digest(decoded))
        return decoded


def current_records(reader, config):
    groups = defaultdict(list)
    deltas = {}
    source = None
    for desc in config['candidate_inputs']:
        body = reader.read(desc)
        kind = desc['kind']
        if kind in ('components', 'fragments', 'contacts', 'residues'):
            value = json.loads(body)
            groups[kind].extend(value['features'] if isinstance(value, dict) else value)
        elif kind.endswith('_delta'):
            deltas[kind[:-6]] = json.loads(body)
        elif kind == 'reconstruction_code':
            source = body
        else:
            json.loads(body)
    reconstruct, contact_key, execution = inputs.existing_reconstructor(
        source, config['existing_reconstructor']['sha256'], canonical)
    current = {kind: reconstruct(groups[kind], deltas[kind],
        contact_key if kind == 'contacts' else lambda r: r['id'])
        for kind in ('components', 'fragments', 'contacts', 'residues')}
    assert len(current['components']) == config['current_components'] == 95173
    assert digest(canonical(current['components'])) == config['current_records_sha256']
    fragments = unique(current['fragments'], 'id', 'current fragment')
    seen = set()
    metadata = {}
    for row in current['components']:
        identity = row['id']
        if identity in metadata:
            raise ValueError('Duplicate current component')
        for binding in row['properties']['fragment_bindings']:
            key = binding['id']
            if key not in fragments or key in seen or digest(canonical(fragments[key])) != binding['feature_sha256']:
                raise ValueError('Whole current fragment/component binding differs')
            seen.add(key)
        metadata[identity] = (row['properties'], digest(canonical(row)), digest(canonical(row['geometry'])))
    if seen != set(fragments):
        raise ValueError('Complete current fragment bijection differs')
    complete_component_ids = set(metadata)
    for row in current['contacts']:
        if not set(row['components']) <= complete_component_ids or not set(row['fragments']) <= seen:
            raise ValueError('Whole current contact escapes component/fragment roster')
    lineage = {kind: {'original_count': d['original_count'], 'current_count': d['current_count'],
        'original_records_sha256': d['original_records_sha256'],
        'current_records_sha256': d['current_records_sha256'],
        'removed_ids': d['removed_ids'], 'upsert_record_ids': [r['id'] for r in d['upsert_records']]}
        for kind, d in deltas.items() if kind != 'contacts'}
    lineage['contacts'] = {k: deltas['contacts'][k] for k in ('original_count', 'current_count',
        'original_records_sha256', 'current_records_sha256', 'removed_ids')}
    return metadata, dict(reconstruction=execution, current_counts={k: len(v) for k, v in current.items()}, lineage=lineage)


def physical_records(reader, descriptors, metadata):
    result = {}
    for desc in descriptors:
        for line in reader.read(desc).splitlines():
            row = json.loads(line)
            identity = row['component_id']
            if identity in result or identity not in metadata:
                raise ValueError('Missing/extra/duplicate physical component')
            fields = ('original_context', 'candidate_feature_sha256', 'candidate_geometry_sha256')
            if row.get('complete_current_record_metadata_alias') != 'v1' or any(k in row for k in fields):
                raise ValueError('Wrong physical candidate alias product')
            context, feature, geometry = metadata[identity]
            if row['physical_authority'] != 'unapproved':
                raise ValueError('Physical authority unexpectedly promoted')
            support = row['complete_support']
            result[identity] = dict(component_id=identity, candidate_geometry_sha256=geometry,
                candidate_feature_sha256=feature, physical_authority=row['physical_authority'],
                source_vintage=row['source_vintage'], status=row['status'], unresolved=row['unresolved'],
                support_areas={k: {'area_m2': v['area_m2'], 'planar_area': v['planar_area']} for k, v in support.items() if k != 'hierarchy_disagreements'},
                hierarchy_support_areas={k: {'area_m2': v['area_m2'], 'planar_area': v['planar_area']}
                    for k, v in support['hierarchy_disagreements'].items()},
                complete_physical_contact_ids=row['complete_contact_ids'],
                original_scientific_containing_file=desc['path'],
                whole_packed_scientific_row_sha256=digest(canonical(row)))
    if set(result) != set(metadata):
        raise ValueError('Incomplete global physical/current identity bijection')
    return result


def family_partitions(families, batches, components):
    by_id = unique(families, 'id', 'fine family')
    by_component = {}
    for family in families:
        ids = family['component_ids']
        if len(ids) != family['component_count'] or len(set(ids)) != len(ids):
            raise ValueError('Family membership count/duplicate differs')
        for identity in ids:
            if identity in by_component:
                raise ValueError('Component assigned to multiple families')
            by_component[identity] = family['id']
    if set(by_component) != set(components):
        raise ValueError('Fine families omit/add current components')
    family_batch = {}
    for batch in unique(batches, 'id', 'operational batch').values():
        ids = batch['fine_family_ids']
        if len(ids) != batch['source_family_count'] or len(set(ids)) != len(ids):
            raise ValueError('Batch family membership differs')
        actual_components = 0
        for identity in ids:
            if identity not in by_id or identity in family_batch:
                raise ValueError('Missing/extra/duplicated batch family')
            family_batch[identity] = batch['id']
            actual_components += by_id[identity]['component_count']
        if actual_components != batch['component_count']:
            raise ValueError('Batch whole component count differs')
    if set(family_batch) != set(by_id):
        raise ValueError('Batches omit/add fine families')
    return by_id, by_component, family_batch


def administrative_records(reader, groups, physical, metadata):
    result = {}
    counts = []
    for group in groups:
        count = 0
        for desc in group['files']:
            for row in json.loads(reader.read(desc)):
                identity = row['component']
                if identity not in physical or identity in result:
                    raise ValueError('Missing/extra/duplicate current administrative binding')
                if row['component_geometry_sha256'] != physical[identity]['candidate_geometry_sha256']:
                    raise ValueError('Whole current administrative geometry binding differs')
                if row['full_component_feature_sha256'] != metadata[identity][1]:
                    raise ValueError('Whole current administrative context binding differs')
                value = {k: row.get(k) for k in ('component', 'component_geometry_sha256',
                    'full_component_feature_sha256', 'family', 'status', 'source_products', 'unknowns',
                    'uniquely_covering_compatible_recorded_subject', 'current_component_relation',
                    'current_component_source_successor', 'surface_status', 'cause_status')}
                value.update(packet=group['namespace'], containing_file=desc['path'],
                    whole_original_row_sha256=digest(canonical(row)), current_binding='exact-current-geometry')
                result[identity] = [value]
                count += 1
        counts.append(dict(packet=group['namespace'], actual_complete_rows=count,
            matched_current_geometry=count, changed_current_geometry=0))
    return result, counts


def metadata_join(repo, config):
    if config['source_delivery'] != EXPECTED_DELIVERY:
        raise ValueError('Wrong fixed source delivery')
    reader = Reader(repo)
    metadata, lineage = current_records(reader, config)
    families = []
    batches = []
    admin_groups = []
    physical = None
    for group in config['source_groups']:
        namespace = group['namespace']
        if namespace == 'worldwide-native-batches-1184-20261006':
            for desc in group['files']:
                value = json.loads(reader.read(desc))
                (batches if '/current-operational-batches-' in desc['path'] else families).extend(value)
        elif namespace == 'global-physical-comparison-20261006':
            physical = physical_records(reader, group['files'], metadata)
        else:
            admin_groups.append(group)
    family_by_id, component_family, family_batch = family_partitions(families, batches, metadata)
    admin, admin_counts = administrative_records(reader, admin_groups, physical, metadata)
    plan = json.loads(reader.read(config['remaining_plan']))
    for desc in config['provenance_inputs']:
        body = reader.read(desc)
        if desc['path'].endswith('.json') or desc['path'].endswith('.json.gz'):
            json.loads(body)
        if desc['path'] == 'scripts/evidence/immutable.py' and body != (HERE/'immutable.py').read_bytes():
            raise ValueError('Existing codec whole executed bytes differ')
    expected = config['expected']
    if (len(metadata), len(families), len(batches), len(admin)) != (expected['components'],
            expected['families'], expected['operational_batches'], expected['admin_bindings']):
        raise ValueError('Complete fixed cohort counts differ')
    return dict(metadata=metadata, physical=physical, families=families, batches=batches,
        family_by_id=family_by_id, component_family=component_family, family_batch=family_batch,
        admin=admin, admin_counts=admin_counts, plan=plan, current_lineage=lineage,
        input_receipts=list(reader.receipts.values()))

LIMITS = [
    'All physical/political/dated/source fitness and processing cause approvals remain unapproved.',
    'Frozen audited current cohort c6 is preserved; no claim of a later evolving main geography release.',
    'Existing measured areas are summed only; no geometry predicates, new areas or distances.',
    'Boundary metres are unknown; complete positive-length neighbor IDs/counts are retained.',
    'Historical related issues are collision clues, not current dispatch or claim eligibility.',
    'Whole scientific bodies are authenticated; opaque object references are not newly reconstructed.',
    'Numeric closure precedes GEO research; no epsilon, suppression or blanket rounding explanation.',
]


def complete_plan_sets(plan, families, administrative):
    allocations = unique(plan['complete_family_allocations'], 'family', 'remaining allocation')
    remaining = {i for i, f in families.items() if any(c not in administrative for c in f['component_ids'])}
    if any(any(c in administrative for c in families[i]['component_ids']) for i in remaining):
        raise ValueError('Partial missing-family administrative cohort')
    if set(allocations) != remaining:
        raise ValueError('Complete remaining plan roster differs')
    for identity, row in allocations.items():
        if row['component_ids'] != families[identity]['component_ids']:
            raise ValueError('Remaining original ordered family membership differs')
    groups = plan['disjoint_groups']
    selected = set(groups['physical-only::whole-retired-member-pointsets-present']['family_ids'])
    empty = set(groups['no-recorded-source-family::explicit-unknown']['family_ids'])
    complement = remaining - selected
    if not selected <= remaining or not empty <= complement:
        raise ValueError('B selection/source-empty subset differs')
    if empty != {i for i in remaining if not families[i]['source_families']}:
        raise ValueError('Complete original source-empty bindings differ')
    sets = dict(all_unscreened_admin=remaining, selected_retired_member_B=selected,
        complement_outside_B=complement, missing_recorded_source_bindings=empty)
    expected = [(6023, 37388), (2476, 20032), (3547, 17356), (3, 5139)]
    for ids, (nf, nc) in zip(sets.values(), expected):
        if len(ids) != nf or sum(families[i]['component_count'] for i in ids) != nc:
            raise ValueError('Complete B/complement/source-empty counts differ')
    return allocations, sets


def routing_products(join):
    P = join['physical']
    M = join['metadata']
    F = join['family_by_id']
    A = join['admin']
    CF = join['component_family']
    FB = join['family_batch']
    categories = {i: next_prerequisite(p, A.get(i, [])) for i, p in P.items()}
    numeric = {i for i, p in P.items() if reason_flags(p)[0]}
    hierarchy = {i for i, p in P.items() if reason_flags(p)[1]}
    invalid = {i for i, p in P.items() if reason_flags(p)[2]}
    compatible_land = {i for i, category in categories.items()
        if category == 'land-plus-compatible-original-processing-reproduction-candidate'}
    if len(numeric) != 26276 or len(compatible_land) != 1005 or len({CF[i] for i in compatible_land}) != 711:
        raise ValueError('Original numerical/source-fit prerequisites differ')
    if any(F[CF[i]]['responsible_role'] != 'GEO-source-research' for i in compatible_land):
        raise ValueError('Compatible source-fit GEO family prerequisite differs')
    area = {i: M[i][0].get('measured_fragment_area_sum_m2') for i in P}
    if any(v is not None and (not isinstance(v, (float, int)) or not math.isfinite(v)) for v in area.values()):
        raise ValueError('Existing measured area invalid')
    support_keys = sorted(next(iter(P.values()))['support_areas'])
    if any(sorted(p['support_areas']) != support_keys for p in P.values()):
        raise ValueError('Whole support relation roster differs')

    def exact_sum(values):
        value = sum((Fraction(v) for v in values if v is not None), Fraction())
        return dict(numerator=str(value.numerator), denominator=str(value.denominator),
            interpretation="Exact sum of original emitted binary64 measurements; not a new geometric measurement.")

    def summarize(ids):
        ids = sorted(ids)
        counts = collections.Counter(categories[i] for i in ids)
        return dict(component_count=len(ids), fine_family_count=len({CF[i] for i in ids}),
            measured_fragment_area_sum_m2=math.fsum(area[i] for i in ids if area[i] is not None),
            exact_existing_fragment_area_sum_m2=exact_sum(area[i] for i in ids),
            components_without_existing_area=sum(area[i] is None for i in ids),
            components_with_unmeasured_fragments=sum(bool(M[i][0].get('unmeasured_fragment_ids')) for i in ids),
            physical_status_counts=dict(collections.Counter(P[i]['status'] for i in ids)),
            exclusive_next_prerequisite_counts=dict(counts),
            exclusive_next_prerequisite_area_sums_m2={k: math.fsum(area[i] or 0 for i in ids if categories[i] == k) for k in counts},
            support_area_sums_m2={k: math.fsum(P[i]['support_areas'][k]['area_m2'] or 0 for i in ids) for k in support_keys},
            exact_existing_support_area_sums_m2={k: exact_sum(P[i]['support_areas'][k]['area_m2'] for i in ids) for k in support_keys},
            numeric_closure_component_count=sum(i in numeric for i in ids),
            hierarchy_unknown_component_count=sum(i in hierarchy for i in ids),
            invalid_original_source_component_count=sum(i in invalid for i in ids),
            missing_admin_component_count=sum(i not in A for i in ids), boundary_length_m=None)

    routes = []
    for i in sorted(P):
        f = F[CF[i]]
        routes.append(dict(component=i, family=CF[i], operational_batch=FB[CF[i]],
            next_prerequisite=categories[i], unresolved=P[i]['unresolved'],
            current_feature_sha256=M[i][1], current_geometry_sha256=M[i][2],
            physical_status=P[i]['status'], physical_source_vintage=P[i]['source_vintage'],
            existing_support_areas=P[i]['support_areas'],
            existing_hierarchy_support_areas=P[i]['hierarchy_support_areas'],
            measured_fragment_area_sum_m2=area[i],
            unmeasured_fragment_ids=M[i][0].get('unmeasured_fragment_ids', []),
            whole_current_context_alias=dict(component=i, full_current_feature_sha256=M[i][1],
                immutable_current_cohort='c6a26e1caba54e1b81a89fbda3a64fff56da323d',
                restoration='Complete declared original/current reconstruction; no hash-only source substitution.'),
            physical_authority='unapproved', dispatch_ready=False,
            source_fitness_prerequisite='GEO-source-fitness-before-processing-reproduction',
            original_responsible_role=f['responsible_role'],
            whole_physical_row_sha256=P[i]['whole_packed_scientific_row_sha256'],
            whole_physical_containing_file=P[i]['original_scientific_containing_file']))
    families = []
    for i in sorted(F):
        f = F[i]
        ids = f['component_ids']
        value = summarize(ids)
        value.update(id=i, operational_batch=FB[i], complete_component_ids=ids,
            original_fine_family=f,
            admin_status_counts=dict(collections.Counter(x['status'] for c in ids for x in A.get(c, []))),
            physical_reason_incidence_counts=dict(collections.Counter(r.get('issue', r.get('status', 'unspecified'))
                for c in ids for r in P[c]['unresolved'])),
            complete_positive_length_neighbor_ids=f['edge_neighbor_ids'],
            positive_length_neighbor_count=len(f['edge_neighbor_ids']),
            unmeasured_components=[c for c in ids if M[c][0].get('unmeasured_fragment_ids')],
            numeric_closure_component_ids=sorted(set(ids) & numeric),
            native_invalid_component_ids=sorted(set(ids) & invalid),
            hierarchy_unknown_component_ids=sorted(set(ids) & hierarchy),
            compatible_original_admin_component_ids=[c for c in ids if any(x['status'] ==
                'one-compatible-recorded-subject-uniquely-covers-component' for x in A.get(c, []))],
            source_fitness_required_compatible_land_component_ids=sorted(set(ids) & compatible_land),
            missing_admin_component_ids=[c for c in ids if c not in A],
            mismatched_admin_component_ids=[], collision_prerequisites=f['existing_related_issues'],
            physical_authority='unapproved', source_fitness='unapproved-for-all-components',
            dispatch_ready=False, boundary_length_limit=LIMITS[3])
        families.append(value)
    batches = []
    for b in sorted(join['batches'], key=lambda b: b['id']):
        fs = b['fine_family_ids']
        ids = [i for f in fs for i in F[f]['component_ids']]
        value = summarize(ids)
        value.update(id=b['id'], complete_fine_family_ids=fs, complete_component_ids=ids,
            original_operational_batch=b, complete_positive_length_neighbor_ids=sorted({n for f in fs for n in F[f]['edge_neighbor_ids']}),
            historic_collision_prerequisites=[dict(family=f, issues=F[f]['existing_related_issues'])
                for f in fs if F[f]['existing_related_issues']], dispatch_ready=False)
        batches.append(value)
    allocations, sets = complete_plan_sets(join['plan'], F, A)
    complements = dict(status='PASS', sets={}, limits=LIMITS)
    for name, fs in sets.items():
        ids = {i for f in fs for i in F[f]['component_ids']}
        value = summarize(ids)
        value.update(complete_family_ids=sorted(fs), complete_component_ids=sorted(ids),
            complete_operational_batch_ids=sorted({FB[f] for f in fs}),
            complete_positive_length_neighbor_ids=sorted({n for f in fs for n in F[f]['edge_neighbor_ids']}),
            affected_boundary_length_m=None)
        complements['sets'][name] = value
    groups = defaultdict(list)
    for i in sets['complement_outside_B']:
        groups[allocations[i]['disjoint_allocation']].append(i)
    if len(groups) != 27:
        raise ValueError('Complete complement group count differs')
    group_rows = []
    for name, fs in sorted(groups.items()):
        ids = {i for f in fs for i in F[f]['component_ids']}
        value = summarize(ids)
        value.update(disjoint_allocation=name, complete_family_ids=sorted(fs), complete_component_ids=sorted(ids),
            direct_role_requirements=sorted({r for f in fs for r in allocations[f]['direct_role_requirements']}),
            unresolved_original_member_leaf_ids=sorted({r for f in fs for r in allocations[f]['unresolved_member_leaf_ids']}),
            recursive_members_without_direct_original_pointset=sorted({r for f in fs for r in allocations[f]['recursive_member_ids_without_direct_original_pointset']}),
            dispatch_ready=False)
        group_rows.append(value)
    remaining = dict(status='PASS', complement_groups=group_rows,
        complete_family_allocation_sha256={i: digest(canonical(row)) for i, row in sorted(allocations.items())},
        complete_original_plan_required=True, limits=LIMITS)
    summary = summarize(P)
    summary.update(status='PASS', complete_operational_batches=len(batches),
        complete_source_input_count=len(join['input_receipts']),
        current_lineage=join['current_lineage'], admin_packets=join['admin_counts'], limits=LIMITS,
        reason_relation_incidence=[dict(issue=k[0], relation=k[1], count=v) for k, v in sorted(collections.Counter(
            (r.get('issue'), r.get('relation')) for p in P.values() for r in p['unresolved']).items(), key=lambda x: str(x[0]))])
    land_cases = [dict(component=i, family=CF[i], operational_batch=FB[CF[i]],
        original_responsible_role=F[CF[i]]['responsible_role'],
        source_fitness_prerequisite='GEO-source-fitness-before-processing-reproduction',
        original_admin_observations=A[i], physical_authority='unapproved', dispatch_ready=False) for i in sorted(compatible_land)]
    return {'components': (routes, True), 'families': (families, True), 'batches': (batches, True),
        'admin-bindings': ([dict(component=i, observations=A[i]) for i in sorted(A)], True),
        'global-summary': (summary, False), 'B-complement': (complements, False),
        'remaining-prerequisites': (remaining, False), 'land-source-fitness': (land_cases, False),
        'input-receipts': (join['input_receipts'], False)}


def write_products(products, destination):
    destination = pathlib.Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    outputs = []
    whole_bodies = []
    for name, (value, jsonl) in products.items():
        raw = b''.join(canonical(row) for row in value) if jsonl else canonical(value)
        chunks = [raw[i:i + PART_LIMIT] for i in range(0, len(raw), PART_LIMIT)]
        joined = bytearray()
        parts = []
        for index, chunk in enumerate(chunks):
            filename = f'{name}-{index:03d}.bin.gz'
            stream = io.BytesIO()
            with gzip.GzipFile(filename='', mode='wb', fileobj=stream, mtime=0, compresslevel=9) as zipped:
                zipped.write(chunk)
            encoded = stream.getvalue()
            if len(encoded) > inputs.LIMIT or len(chunk) > inputs.LIMIT:
                raise ValueError('Ordinary encoded/decoded output bound')
            (destination/filename).write_bytes(encoded)
            descriptor = dict(path=filename, bytes=len(encoded), sha256=digest(encoded),
                uncompressed_bytes=len(chunk), uncompressed_sha256=digest(chunk))
            outputs.append(descriptor)
            parts.append(descriptor)
            joined.extend(gzip.decompress(encoded))
        if bytes(joined) != raw:
            raise ValueError('Complete ordered raw output restoration differs')
        whole_bodies.append(dict(name=name, format='jsonl' if jsonl else 'json',
            bytes=len(raw), sha256=digest(raw), parts=parts))
    return dict(outputs=outputs, complete_whole_raw_bodies=whole_bodies)
