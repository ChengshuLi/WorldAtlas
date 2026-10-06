"""Validate exhaustive diagnostic orders against complete original source ledgers.

This byte/semantic gate cannot establish boundary placement or physical water.
"""
import argparse
import gzip
import io
import json
import pathlib
import importlib.util
from collections import defaultdict

from evidence.immutable import Baseline, MAX_FILE_BYTES, canonical_json, sha256, safe_path
from physical_component_contacts import component_contacts
from physical_gap_priority import (PARTITIONS, ORDER_NAMES, partition_accounting,
                                  hierarchy_context, investigation_record, related_issue_scopes,
                                  issue_subject_index, legacy_grid_links, legacy_water_links,
                                  validate_rank_positions, investigation_ranks,
                                  difference_unknown_accounting)

ROOT = pathlib.Path(__file__).resolve().parents[1]
OWNED = 'coordination/engineering/physical-gap-priorities-1005-20261006-local20/'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def ordinary(path):
    path = safe_path(path)
    target = ROOT / path
    require(not any(p.is_symlink() for p in [target, *target.parents]), 'Symlink in retained artifact')
    require(target.is_file() and target.stat().st_size <= MAX_FILE_BYTES, 'Missing or oversized whole artifact')
    return target.read_bytes()


def product(pin):
    raw = ordinary(pin['path'])
    require(len(raw) == pin['bytes'] and sha256(raw) == pin['sha256'], 'Whole output byte pin changed')
    if pin['path'].endswith('.gz'):
        with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
            raw = stream.read(MAX_FILE_BYTES + 1)
        require(len(raw) <= MAX_FILE_BYTES and len(raw) == pin['uncompressed_bytes']
                and sha256(raw) == pin['uncompressed_sha256'], 'Complete decoded output differs')
    return json.loads(raw)


def validate_rows(report, rows, contexts, component_rows):
    """Check original binding/measurement preservation and complete rank semantics."""
    counts = partition_accounting(rows, [r['id'] for r in component_rows])
    require(counts == report['partition_counts'], 'Complete partition counts differ')
    require(sum(counts.values()) == report['component_count'] == len(rows), 'Component count differs')
    require(set(counts) == set(PARTITIONS), 'Partition family omitted')
    originals = {r['id']: r for r in component_rows}
    context_by_id = {r['id']: r for r in contexts}
    require(len(context_by_id) == len(contexts) == report['native_context_count'], 'Native context roster differs')
    unmeasured = []
    for row in rows:
        original = originals[row['component']]['properties']
        require(row['original_fragment_bindings'] == original['fragment_bindings'], 'Whole original fragment bindings differ')
        require(row['measured_fragment_area_sum_m2'] == original['measured_fragment_area_sum_m2'], 'Recorded known area changed')
        require(row['unmeasured_fragment_ids'] == original['unmeasured_fragment_ids'], 'Original uncertainty changed')
        unmeasured.extend(row['unmeasured_fragment_ids'])
        require(row['surface_status'] == 'unverified' and row['administrative_assignment'] is None
                and row['source_authority_status'] == 'not-independently-approved', 'Diagnostic promoted to geography fact')
        require(row['investigation_orders'] == investigation_ranks(row, context_by_id), 'Investigation ordering keys changed')
        require(all(c['new_component_grid_status'] == 'not-exhaustively-assessed' for c in row['legacy_grid_context']), 'Legacy grid sample promoted')
        require(all(c['new_component_water_status'] == 'unverified' and c['measurement_status'] == 'archived-context-not-recomputed'
                    for c in row['archived_water_context']), 'Archived water context promoted')
    require(sorted(unmeasured) == sorted(report['unmeasured_fragment_ids']), 'Original unmeasured roster differs')
    validate_rank_positions(rows)
    for name in ORDER_NAMES:
        require(report['complete_order_counts'][name] == len(rows), 'Rank count omitted')
        require(all(row['rank_positions'][name] == rank for rank, row in
                    enumerate(sorted(rows, key=lambda r:r['investigation_orders'][name]))), 'Rank positions disagree with recorded order')
    return counts


def require_semantic_row(row, expected):
    require(set(row)==set(expected)|{'rank_positions'}, 'Unexpected or omitted derived record field')
    require(canonical_json({k:v for k,v in row.items() if k!='rank_positions'})==canonical_json(expected),
            'Complete original semantic references or uncertainty changed')


def validate(prefix):
    prefix = safe_path(prefix)
    require(prefix.startswith(OWNED), 'Use owned retained diagnostic vintage')
    report = json.loads(ordinary(prefix + '/report.json'))
    require(report['version'] == 'worldatlas-physical-gap-investigation-priorities-v1', 'Unknown producer version')
    sources = Baseline(ROOT, report['input_commit'], report['inputs'])
    # All original native audit input pins are checked at their original commit;
    # this includes index/hierarchy, not just location-containing geometry parts.
    native = Baseline(ROOT, report['original_native_commit'], report['original_native_inputs'])
    Baseline(ROOT, report['executed_code_commit'], report['code_inputs'])
    custody_path = 'coordination/engineering/physical-gap-components-1005-20261005-local19/custody-v1/index.json'
    custody = json.loads(sources.read(custody_path))
    aliases = {r['original']['path']: r for r in custody['aliases']}
    def logical(path):
        row = aliases[path]
        raw = sources.read(row['payload'])
        pin = row['original']
        require(len(raw) == pin['bytes'] and sha256(raw) == pin['sha256'], 'Original complete custody alias changed')
        if path.endswith('.gz'):
            with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
                raw = stream.read(MAX_FILE_BYTES + 1)
            require(len(raw) <= MAX_FILE_BYTES and len(raw) == pin['uncompressed_bytes'] and sha256(raw) == pin['uncompressed_sha256'], 'Original decoded custody changed')
        return json.loads(raw)
    component_report = logical(report['original_component_report'])
    component_rows = []
    for pin in component_report['outputs']['new_components']:
        body = logical(pin['path'])
        component_rows.extend(body['features'])
    require(len(component_rows) == component_report['new_components'], 'Complete original component family differs')
    require(set(report['outputs']) == {'investigations','native_contexts','unmatched_original_unknowns'}, 'Output family omitted')
    families = {name:[row for pin in pins for row in product(pin)] for name,pins in report['outputs'].items()}
    require(report['fragment_count'] == component_report['new_fragments'], 'Fragment count differs')
    # Reconstruct original full native metadata/context; a rehashed derived name,
    # source locator, ancestry or feature binding is not trusted on its own.
    nodes = {n['id']:n for n in json.loads(native.read('data/hierarchy.json'))}
    world = json.loads(native.read('data/world-index.json'))
    expected_contexts=[]
    for part in world['parts']:
        path='data/'+safe_path(part)
        raw=native.read(path)
        if path.endswith('.gz'):
            with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
                raw=stream.read(MAX_FILE_BYTES+1)
            require(len(raw)<=MAX_FILE_BYTES, 'Oversized original native decoded part')
        for leaf in json.loads(raw)['features']:
            context=hierarchy_context(leaf,nodes)
            context.update(original_feature_sha256=sha256(canonical_json(leaf)), original_input_path=path,
                original_metadata=leaf['properties'].get('metadata',{}), original_name=leaf['properties'].get('name'),
                source_authority_status='not-independently-approved')
            expected_contexts.append(context)
    require(canonical_json(sorted(expected_contexts,key=lambda r:r['id']))==canonical_json(families['native_contexts']),
            'Complete original native context changed')
    # Every original source-contact and water/grid-context reference is compared
    # with its retained full feature/report, not just a derived byte hash.
    detection_path='coordination/engineering/physical-gap-audit-1005-20261005-local18/detection-v4/report.json'
    detection=json.loads(sources.read(detection_path))
    fragments=[]
    for pin in detection['outputs']:
        encoded=sources.read(pin['path'])
        require(len(encoded)==pin['bytes'] and sha256(encoded)==pin['sha256'], 'Original detector encoded pin differs')
        with gzip.GzipFile(fileobj=io.BytesIO(encoded)) as stream:
            raw=stream.read(MAX_FILE_BYTES+1)
        require(len(raw)<=MAX_FILE_BYTES and len(raw)==pin['uncompressed_bytes'] and sha256(raw)==pin['uncompressed_sha256'], 'Original detector decoded pin differs')
        fragments.extend(json.loads(raw)['features'])
    fragment_by_id={f['id']:f for f in fragments}
    resolved=component_contacts(fragments,component_rows)
    triage_path='coordination/engineering/geographic-grid-triage-946-20261005-local08/triage-v1/report.json'
    triage=json.loads(sources.read(triage_path))
    samples={}
    for pin in triage['sample_parts']:
        path=str(pathlib.PurePosixPath(triage_path).parent)+'/'+pin['path']
        encoded=sources.read(path)
        require(len(encoded)==pin['bytes'] and sha256(encoded)==pin['sha256'], 'Original grid encoded pin differs')
        with gzip.GzipFile(fileobj=io.BytesIO(encoded)) as stream:
            raw=stream.read(MAX_FILE_BYTES+1)
        require(len(raw)<=MAX_FILE_BYTES and len(raw)==pin['uncompressed_bytes'] and sha256(raw)==pin['uncompressed_sha256'], 'Original grid decoded pin differs')
        for row in json.loads(raw):
            require(row['component_id'] not in samples, 'Duplicate original grid sample')
            samples[row['component_id']]=row
    require(len(samples)==triage['component_count'], 'Original grid sample family incomplete')
    links_by_new=defaultdict(list)
    links_by_old=defaultdict(list)
    all_links=[]
    for pin in component_report['outputs']['component_links']:
        all_links.extend(logical(pin['path']))
    for ordinal,link in enumerate(all_links):
        links_by_new[link['new_component']].append((ordinal,link))
        links_by_old[link['old_component']].append(link['new_component'])
    new_member={binding['id']:component['id'] for component in component_rows for binding in component['properties']['fragment_bindings']}
    old_member={binding['id']:identity for identity,sample in samples.items() for binding in sample['fragment_bindings']}
    unknowns,unmatched,accounting=difference_unknown_accounting(component_report['difference_unknowns'],new_member,old_member,links_by_old)
    for row in component_report['overlay_unknowns']:
        unknowns.setdefault(row['new_component'],[]).append(row)
    require(unmatched==families['unmatched_original_unknowns'] and accounting==report['difference_unknown_accounting'], 'Complete original operation unknown accounting differs')
    water_pin=triage['water_pilot_reference']
    water=json.loads(sources.read(water_pin['path']))
    module_spec=importlib.util.spec_from_file_location('priority_producer',ROOT/'scripts/build-physical-gap-priorities.py')
    producer=importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(producer)
    issue_paths=[pin['path'] for pin in report['inputs'] if pin['path'].startswith(OWNED) and '/open-issues-api-pages-' in pin['path']]
    require(len(issue_paths)==1, 'Exact original issue roster missing')
    declared=producer.issue_subjects(json.loads(sources.read(issue_paths[0])))
    require({str(k):v for k,v in declared.items()}==report['issue_subject_rosters'], 'Original issue subject rosters changed')
    compiled=issue_subject_index(declared)
    context_by_id={r['id']:r for r in expected_contexts}
    native_ids=set(context_by_id)
    actual={r['component']:r for r in families['investigations']}
    for component,contact in zip(sorted(component_rows,key=lambda r:r['id']),resolved):
        identity=component['id']
        row=actual.get(identity)
        require(row is not None, 'Original component omitted')
        expected=investigation_record(component,contact,fragment_by_id,operation_unknowns=unknowns.get(identity,[]))
        scopes=related_issue_scopes(expected['distinct_contact_ids'],expected['positive_length_neighbor_ids'],declared,compiled=compiled)
        if scopes:
            expected=investigation_record(component,contact,fragment_by_id,links=scopes,operation_unknowns=unknowns.get(identity,[]))
        expected['legacy_grid_context']=legacy_grid_links(identity,links_by_new[identity],samples)
        expected['archived_water_context']=legacy_water_links(identity,links_by_new[identity],samples,water['pilots'],water_pin)
        expected['investigation_orders']=investigation_ranks(expected,context_by_id)
        expected['missing_native_contact_ids']=sorted(set(expected['distinct_contact_ids'])-native_ids)
        require_semantic_row(row,expected)
    counts = validate_rows(report, families['investigations'], families['native_contexts'], component_rows)
    require(report['original_unknown_overlay_count'] == len(component_report['overlay_unknowns'])
            and report['original_unknown_difference_count'] == len(component_report['difference_unknowns']), 'Original operation uncertainty count changed')
    require(report['difference_unknown_accounting']['unmatched_original_error_count'] == len(families['unmatched_original_unknowns']), 'Unmatched original uncertainty lost')
    require(report['surface_status'] == 'unverified' and report['administrative_assignment'] is None, 'Report promoted to geography fact')
    return {'status':'diagnostic-only','components':len(families['investigations']),
            'native_contexts':len(families['native_contexts']),'partition_counts':counts,
            'unmeasured_fragments':len(report['unmeasured_fragment_ids'])}


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prefix',required=True)
    print(json.dumps(validate(parser.parse_args().prefix)))
