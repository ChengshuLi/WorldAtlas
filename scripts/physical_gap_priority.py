"""Preparation for #1005 part3; not a published scientific artifact.

Inputs must be complete immutable component/source-contact bindings. This
classifies investigation work only; every candidate's surface and administrative
assignment remain unverified. Missing measurement must never become zero.
"""
from collections import Counter
import math
from evidence.immutable import canonical_json, sha256

PARTITIONS = ('original-unknowns', 'related-declared-neighbor-subjects',
              'interior-multiple-edge-neighbors', 'interior-other-native-cases',
              'water-reference-diagnostic', 'shore-with-source-contacts',
              'shore-without-source-contacts', 'retained-other')


def investigation_record(component, resolved, features, links=(), operation_unknowns=()):
    identity = component['id']
    properties = component['properties']
    if resolved['component'] != identity:
        raise ValueError('Source-contact component mismatch')
    bindings = {b['id']: b['feature_sha256'] for b in properties['fragment_bindings']}
    if len(bindings) != len(properties['fragment_bindings']):
        raise ValueError('Duplicate original fragment')
    contact_bindings = resolved['fragment_contacts']
    if (len(contact_bindings) != len(bindings)
            or set(bindings) != {b['fragment'] for b in contact_bindings}):
        raise ValueError('Incomplete original contact binding roster')
    contacts, diagnostic_refs = [], []
    for binding in resolved['fragment_contacts']:
        fragment = binding['fragment']
        if binding['feature_sha256'] != bindings[fragment]:
            raise ValueError('Changed whole original feature binding')
        original = features[fragment]
        if original['id'] != fragment or sha256(canonical_json(original)) != bindings[fragment]:
            raise ValueError('Wrong original feature')
        recorded = 'exact_location_contacts' in original['properties']
        if recorded != (binding['status'] == 'recorded'):
            raise ValueError('Original contact recording presence changed')
        if binding['status'] not in ('recorded', 'unknown-not-recorded'):
            raise ValueError('Unknown original contact recording status')
        if binding['status'] == 'recorded':
            if binding['exact_location_contacts'] != original['properties'].get('exact_location_contacts'):
                raise ValueError('Original complete contact ledger changed')
            for number, contact in enumerate(binding['exact_location_contacts']):
                if contact['kind'] not in ('positive-area-intersection-flag', 'positive-length-boundary', 'point-only-ambiguous'):
                    raise ValueError('Unknown exact geometry contact kind')
                contacts.append({'fragment': fragment, 'contact_number': number,
                                 'id': contact['id'], 'kind': contact['kind'],
                                 'source': contact.get('source'),
                                 'reference_year': contact.get('reference_year')})
        diagnostics = original['properties'].get('water_diagnostics')
        if diagnostics is None:
            diagnostic_refs.append({'fragment': fragment, 'status': 'unknown-not-recorded'})
        else:
            if not isinstance(diagnostics, list):
                raise ValueError('Original water diagnostics must be a complete list')
            diagnostic_refs.extend({'fragment': fragment, 'diagnostic_number': n,
                                    'status': 'recorded-diagnostic'} for n in range(len(diagnostics)))
    expected_status = ('complete-recorded-contacts' if all(b['status'] == 'recorded' for b in contact_bindings)
                       else 'incomplete-source-contact-recording')
    if resolved['status'] != expected_status:
        raise ValueError('Component contact recording certainty changed')
    ids = sorted({c['id'] for c in contacts})
    edges = sorted({c['id'] for c in contacts if c['kind'] == 'positive-length-boundary'})
    unmeasured = list(properties['unmeasured_fragment_ids'])
    original_unmeasured = sorted(f for f in bindings if features[f]['properties']['area_m2'] is None)
    if sorted(unmeasured) != original_unmeasured:
        raise ValueError('Original measurement uncertainty changed')
    unknown = bool(unmeasured or operation_unknowns or resolved['status'] != 'complete-recorded-contacts')
    shore = properties['touches_reference_shore']
    if unknown:
        partition = PARTITIONS[0]
    elif any(link.get('qualification') == 'complete-recorded-edge-subject-roster' for link in links):
        partition = PARTITIONS[1]
    elif not shore and len(edges) >= 2:
        partition = PARTITIONS[2]
    elif not shore:
        partition = PARTITIONS[3]
    elif any(r['status'] == 'recorded-diagnostic' for r in diagnostic_refs):
        partition = PARTITIONS[4]
    elif shore and contacts:
        partition = PARTITIONS[5]
    elif shore:
        partition = PARTITIONS[6]
    else:
        partition = PARTITIONS[7]
    measured_sum = properties['measured_fragment_area_sum_m2']
    if not isinstance(measured_sum, (int, float)) or not math.isfinite(measured_sum) or measured_sum < 0:
        raise ValueError('Known measurement sum must be finite and nonnegative')
    original_sum = math.fsum(features[f]['properties']['area_m2'] for f in bindings
                             if features[f]['properties']['area_m2'] is not None)
    if measured_sum != original_sum:
        raise ValueError('Known original measurements changed')
    return {'component': identity, 'partition': partition,
            'original_fragment_bindings': properties['fragment_bindings'],
            'source_contact_references': contacts, 'distinct_contact_ids': ids,
            'positive_length_neighbor_ids': edges,
            'positive_area_location_contact_flag_ids': sorted({c['id'] for c in contacts
                if c['kind'] == 'positive-area-intersection-flag'}),
            'water_diagnostic_references': diagnostic_refs,
            'linked_followups': list(links), 'operation_unknowns': list(operation_unknowns),
            'unmeasured_fragment_ids': unmeasured,
            'original_domain_flags': {key: properties.get(key) for key in (
                'touches_reference_shore', 'touches_blocked_tile',
                'touches_domain_boundary', 'dateline_connected', 'positive_area_input_overlap')},
            'measured_fragment_area_sum_m2': measured_sum,
            'total_area_status': 'unmeasured-original-fragments-present' if unmeasured else 'all-fragments-measured',
            'surface_status': 'unverified', 'administrative_assignment': None,
            'source_authority_status': 'not-independently-approved'}


def partition_accounting(records, expected_ids):
    ids = [r['component'] for r in records]
    expected_ids = list(expected_ids)
    if (len(expected_ids) != len(set(expected_ids))
            or len(ids) != len(set(ids)) or set(ids) != set(expected_ids)):
        raise ValueError('Exhaustive component partition roster differs')
    counts = Counter(r['partition'] for r in records)
    if set(counts) - set(PARTITIONS):
        raise ValueError('Unknown investigation partition')
    return {p: counts[p] for p in PARTITIONS}


def hierarchy_context(leaf, nodes):
    """Resolve exact recorded parents only, never country/owner/ID guesses."""
    parent = leaf['properties'].get('parent_id')
    result = {'id': leaf['id'], 'original_parent_id': parent, 'ancestry': []}
    seen = {leaf['id']}
    if parent is None:
        return dict(result, status='missing-recorded-leaf-parent')
    while parent is not None:
        if parent in seen:
            return dict(result, status='cyclic-recorded-parent', unresolved_parent=parent)
        seen.add(parent)
        if parent not in nodes:
            return dict(result, status='missing-recorded-ancestor', unresolved_parent=parent)
        node = nodes[parent]
        if node.get('id') != parent:
            raise ValueError('Recorded hierarchy lookup identity changed')
        if 'parent_id' not in node:
            return dict(result, status='missing-recorded-ancestor-parent', unresolved_parent=parent)
        result['ancestry'].append({k: node.get(k) for k in ('id', 'level', 'name', 'parent_id')})
        parent = node.get('parent_id')
    return dict(result, status='complete-recorded-ancestry')


def investigation_ranks(record, contexts):
    """Three independent investigation orders; none approves a source or fact."""
    contacts = record['source_contact_references']
    missing_locator = not contacts or any(not c['source'] for c in contacts)
    missing_vintage = not contacts or any(c['reference_year'] is None for c in contacts)
    regions = set()
    unresolved_ancestry = not record['distinct_contact_ids']
    for subject in record['distinct_contact_ids']:
        context = contexts.get(subject)
        if context is None or context['status'] != 'complete-recorded-ancestry':
            unresolved_ancestry = True
        if context:
            regions.update(n['id'] for n in context['ancestry'] if n['level'] == 'region')
    unmeasured = bool(record['unmeasured_fragment_ids'])
    return {'source_locator_readiness': [int(missing_locator), int(missing_vintage), record['component']],
            'coordination_complexity': [int(unresolved_ancestry), len(regions),
                                        len(record['distinct_contact_ids']), record['component']],
            'measured_impact': [int(unmeasured),
                                None if unmeasured else -record['measured_fragment_area_sum_m2'],
                                record['component']],
            'limits': ['Locators/vintages do not establish lawful restoration or authority.',
                       'Unmeasured impact is explicitly separated; never compared as zero area.',
                       'Recorded region ancestry is geographic context, not political affiliation.']}


def issue_subject_index(issue_subjects):
    """Compile exact declared rosters once; no geography inference is performed."""
    rosters = {number: frozenset(subjects) for number, subjects in issue_subjects.items()}
    reverse = {}
    for number, subjects in rosters.items():
        for subject in subjects:
            reverse.setdefault(subject, set()).add(number)
    return rosters, reverse


def related_issue_scopes(contact_ids, edge_ids, issue_subjects, compiled=None):
    """Exact declared subjects locate related work; they do not prove repair scope."""
    contacts, edges = set(contact_ids), set(edge_ids)
    result = []
    rosters, reverse = compiled if compiled is not None else issue_subject_index(issue_subjects)
    candidates = set().union(*(reverse.get(subject, set()) for subject in contacts))
    for number in sorted(candidates):
        declared = rosters[number]
        matches = sorted(contacts & declared)
        if matches:
            result.append({'issue': number, 'matching_contact_subject_ids': matches,
                           'qualification': 'complete-recorded-edge-subject-roster'
                           if len(edges) >= 2 and edges <= declared else 'partial-contact-context',
                           'scope_status': 'related-subjects-only-geometry-coverage-unverified'})
    return result


def legacy_grid_links(component_id, crosswalk_links, samples):
    """An old sampled cell is historical context, never a new-component verdict."""
    result = []
    for ordinal, link in crosswalk_links:
        if link['new_component'] != component_id or link['old_component'] not in samples:
            raise ValueError('Missing or redirected original grid/crosswalk binding')
        sample = samples[link['old_component']]
        if sample['component_id'] != link['old_component']:
            raise ValueError('Wrong original component grid sample')
        result.append({'component_link_number': ordinal,
                       'old_component': link['old_component'],
                       'original_relation_kinds': link['kinds'],
                       'original_pair_numbers': link['pair_numbers'],
                       'original_sample_status': sample['status'],
                       'original_sample_row_sha256': sha256(canonical_json(sample)),
                       'applicability': 'one-old-representative-cell-only',
                       'new_component_grid_status': 'not-exhaustively-assessed'})
    return result


ORDER_NAMES = ('source_locator_readiness', 'coordination_complexity', 'measured_impact')


def attach_rank_positions(records):
    """Complete total orders recorded once per component, without repeated ID tables."""
    if len({r['component'] for r in records}) != len(records):
        raise ValueError('Duplicate component in investigation ranking')
    for record in records:
        if set(record['investigation_orders']) != set(ORDER_NAMES) | {'limits'}:
            raise ValueError('Incomplete investigation order keys')
        record['rank_positions'] = {}
    for name in ORDER_NAMES:
        for rank, record in enumerate(sorted(records, key=lambda r: r['investigation_orders'][name])):
            record['rank_positions'][name] = rank
    validate_rank_positions(records)
    return {name: len(records) for name in ORDER_NAMES}


def validate_rank_positions(records):
    expected = set(range(len(records)))
    for name in ORDER_NAMES:
        values = [r.get('rank_positions', {}).get(name) for r in records]
        if any(type(v) is not int for v in values) or set(values) != expected:
            raise ValueError('Incomplete or duplicate total-order rank positions')


def legacy_water_links(component_id, crosswalk_links, samples, pilots, report_pin):
    """Join recorded old-shape observations; no raster measurement or new water verdict."""
    result = []
    for ordinal, link in crosswalk_links:
        if link['new_component'] != component_id:
            raise ValueError('Redirected original water/crosswalk context')
        for number, pilot in enumerate(pilots):
            if pilot['component_id'] != link['old_component']:
                continue
            sample = samples.get(link['old_component'])
            if (sample is None or sample.get('original_component_feature_sha256')
                    != pilot['original_component_feature_sha256']):
                raise ValueError('Original recorded water/grid shape binding differs')
            result.append({'component_link_number': ordinal,
                           'old_component': link['old_component'],
                           'original_relation_kinds': link['kinds'],
                           'original_water_report': report_pin,
                           'original_pilot_number': number,
                           'original_pilot_row_sha256': sha256(canonical_json(pilot)),
                           'recorded_original_feature_sha256': pilot['original_component_feature_sha256'],
                           'sampled_months': pilot['comparison']['sampled_months'],
                           'original_explicit_pilot_aoi': pilot['explicit_pilot_aoi'],
                           'original_full_component_sampled': pilot['full_component_sampled'],
                           'applicability': 'recorded-old-shape-and-sampled-months-only',
                           'new_component_water_status': 'unverified',
                           'measurement_status': 'archived-context-not-recomputed',
                           'limits': ['Recorded shape hashes agree; this join does not recalculate original raster observations.',
                                      'An old sampled shape/month does not classify a changed component or unsampled dates.',
                                      'Original encoding, registration, no-observation and AOI limits remain in the full report.']})
    return result



def difference_unknown_accounting(errors, new_members, old_members, links_by_old):
    """Retain old failures even when there is no related new component."""
    mapped, unmatched = {}, []
    mapped_original_count = associations = 0
    for number, row in enumerate(errors):
        if row['side'] == 'new':
            affected = [new_members[row['fragment']]]
        elif row['side'] == 'old':
            affected = links_by_old.get(old_members[row['fragment']], [])
        else:
            raise ValueError('Unknown original difference side')
        if len(affected) != len(set(affected)):
            raise ValueError('Duplicate original difference association')
        reference = {'original_error_number': number, 'original': row}
        if not affected:
            unmatched.append({**reference, 'status': 'retained-old-error-without-new-crosswalk-link'})
        else:
            mapped_original_count += 1
            for identity in affected:
                mapped.setdefault(identity, []).append(reference)
                associations += 1
    accounting = {'original_error_count': len(errors),
                  'mapped_original_error_count': mapped_original_count,
                  'unmatched_original_error_count': len(unmatched),
                  'affected_component_associations': associations}
    if mapped_original_count + len(unmatched) != len(errors):
        raise ValueError('Original difference uncertainty accounting failed')
    return mapped, unmatched, accounting
