"""Exhaustive diagnostic investigation joins, never factual gap filling."""
import argparse
from collections import Counter, defaultdict
import gzip
import io
import json
import pathlib
import re
import subprocess
import sys
import platform
import zlib

from evidence.immutable import Baseline, MAX_FILE_BYTES, canonical_json, descriptor, deterministic_gzip, safe_path, sha256
from physical_component_contacts import component_contacts
from physical_gap_priority import investigation_record, partition_accounting, hierarchy_context, investigation_ranks, related_issue_scopes, legacy_grid_links, attach_rank_positions, legacy_water_links, difference_unknown_accounting, issue_subject_index

ROOT = pathlib.Path(__file__).resolve().parents[1]
OWNED = 'coordination/engineering/physical-gap-priorities-1005-20261006-local20/'
CUSTODY = 'coordination/engineering/physical-gap-components-1005-20261005-local19/custody-v1/index.json'
DETECTION = 'coordination/engineering/physical-gap-audit-1005-20261005-local18/detection-v4/report.json'
ENVELOPE = 'coordination/engineering/physical-gap-audit-1005-20261005-local18/input-envelope-v1/manifest.json'
TRIAGE = 'coordination/engineering/geographic-grid-triage-946-20261005-local08/triage-v1/report.json'
VERSION = 'worldatlas-physical-gap-investigation-priorities-v1'
CODE = ['scripts/build-physical-gap-priorities.py', 'scripts/physical_gap_priority.py',
        'scripts/physical_component_contacts.py', 'scripts/physical_gap_crosswalk.py',
        'scripts/physical_gap_audit.py', 'scripts/evidence/immutable.py']


class GitInputs:
    def __init__(self, commit):
        raw = subprocess.check_output(['git', 'show', commit + ':' + CUSTODY], cwd=ROOT)
        self.source = Baseline(ROOT, commit, [descriptor(CUSTODY, raw)])
        self.pins, self.cache = {}, {}

    def read(self, path, pin=None):
        path = safe_path(path)
        if path not in self.cache:
            self.cache[path] = self.source.read(path)
        raw = self.cache[path]
        observed = descriptor(path, raw)
        if pin and observed != {k:v for k,v in pin.items() if k in observed}:
            raise ValueError('Complete original input descriptor differs: ' + path)
        self.pins[path] = observed
        return raw

    def json(self, path, pin=None):
        return json.loads(self.read(path, pin))

    def decoded(self, path, pin):
        encoded = self.read(path, pin)
        with gzip.GzipFile(fileobj=io.BytesIO(encoded)) as stream:
            raw = stream.read(MAX_FILE_BYTES + 1)
        if (len(raw) > MAX_FILE_BYTES or len(raw) != pin['uncompressed_bytes']
                or sha256(raw) != pin['uncompressed_sha256']):
            raise ValueError('Complete original decoded product differs')
        return json.loads(raw)


def write_parts(out, name, rows):
    outputs, batch, size = [], [], 0
    def flush():
        raw = canonical_json(batch)
        if len(raw) > MAX_FILE_BYTES:
            raise ValueError('Complete derived file exceeds byte limit')
        encoded = deterministic_gzip(raw)
        target = out / f'{name}-{len(outputs):03d}.json.gz'
        with target.open('xb') as stream:
            stream.write(encoded)
        outputs.append({**descriptor(str(target.relative_to(ROOT)), encoded),
                        'uncompressed_bytes': len(raw), 'uncompressed_sha256': sha256(raw)})
    for row in rows:
        count = len(canonical_json(row))
        if batch and size + count > 8 * 1024 * 1024:
            flush()
            batch, size = [], 0
        batch.append(row)
        size += count
    if batch:
        flush()
    return outputs


def issue_subjects(snapshots):
    """Only explicit machine-contract subjects; text/names/affiliation are ignored."""
    if not isinstance(snapshots, list) or not snapshots:
        raise ValueError('Complete paginated original issue API snapshot required')
    if any(not isinstance(page, list) or len(page) > 100 for page in snapshots):
        raise ValueError('Original issue API pages must retain their complete row arrays')
    if any(len(page) != 100 for page in snapshots[:-1]):
        raise ValueError('Incomplete nonfinal issue API page')
    snapshots = [row for page in snapshots for row in page]
    if len({row['number'] for row in snapshots}) != len(snapshots):
        raise ValueError('Duplicate issue API identity across pages')
    result = {}
    for issue in snapshots:
        if 'pull_request' in issue or issue.get('state') != 'open':
            continue
        matches = re.findall(r'<!-- worldatlas-work:v1\s*([\s\S]*?)\s*-->', issue.get('body') or '')
        if len(matches) != 1:
            continue
        spec = json.loads(matches[0])
        subjects = spec.get('evidence_quality', {}).get('subject_ids', [])
        if not isinstance(subjects, list) or any(not isinstance(i,str) for i in subjects) or len(subjects) != len(set(subjects)):
            raise ValueError('Malformed original declared issue subjects')
        if subjects:
            result[issue['number']] = subjects
    return result


def run(commit, issues_path, output):
    output, issues_path = safe_path(output), safe_path(issues_path)
    if not output.startswith(OWNED) or output == OWNED.rstrip('/') or not issues_path.startswith(OWNED):
        raise ValueError('Explicit new owned vintage and complete issue snapshot required')
    out = ROOT / output
    if out.exists() or any(p.is_symlink() for p in [out, *out.parents]):
        raise ValueError('Never overwrite original/prior evidence')
    executed = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip()
    code = []
    for path in CODE:
        raw = subprocess.check_output(['git','show',executed+':'+path],cwd=ROOT)
        if (ROOT/path).is_symlink() or (ROOT/path).read_bytes()!=raw:
            raise ValueError('Commit exact ordinary executable bytes before generation')
        code.append(descriptor(path,raw))
    inputs = GitInputs(commit)
    custody = inputs.json(CUSTODY)
    aliases = {a['original']['path']:a for a in custody['aliases']}
    if len(aliases)!=len(custody['aliases']):
        raise ValueError('Duplicate original custody alias')
    payloads = {p['path']:p for p in custody['payloads']}
    complete = [g for g in custody['generations'] if g['status']=='complete']
    if len(complete)!=2:
        raise ValueError('Require two retained complete scientific executions')
    generation = complete[0]
    def logical_json(path):
        a = aliases[path]
        raw = inputs.read(a['payload'],payloads[a['payload']])
        original = a['original']
        if len(raw)!=original['bytes'] or sha256(raw)!=original['sha256']:
            raise ValueError('Original whole-file custody changed')
        if path.endswith('.gz'):
            with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
                decoded=stream.read(MAX_FILE_BYTES+1)
            if (len(decoded)>MAX_FILE_BYTES or len(decoded)!=original['uncompressed_bytes']
                    or sha256(decoded)!=original['uncompressed_sha256']):
                raise ValueError('Original decoded custody changed')
            raw=decoded
        return json.loads(raw)
    report=logical_json(generation['prefix']+'/report.json')
    def family(name):
        rows=[]
        for pin in report['outputs'][name]:
            body=logical_json(pin['path'])
            rows.extend(body['features'] if isinstance(body,dict) else body)
        return rows
    records=family('new_components')
    if len(records)!=report['new_components']:
        raise ValueError('Incomplete original new component roster')
    detection=inputs.json(DETECTION)
    # Original candidate bundles live at the same immutable comparison input.
    features=[]
    for pin in detection['outputs']:
        encoded=inputs.read(pin['path'],pin)
        if descriptor(pin['path'],encoded)!={k:v for k,v in pin.items() if not k.startswith('uncompressed_')}:
            raise ValueError('Original candidate bundle changed')
        with gzip.GzipFile(fileobj=io.BytesIO(encoded)) as stream:
            raw=stream.read(MAX_FILE_BYTES+1)
        if len(raw)>MAX_FILE_BYTES or len(raw)!=pin['uncompressed_bytes'] or sha256(raw)!=pin['uncompressed_sha256']:
            raise ValueError('Complete original candidate decoded bytes changed')
        features.extend(json.loads(raw)['features'])
    if len(features)!=report['new_fragments']:
        raise ValueError('Incomplete original fragment inventory')
    by_fragment={f['id']:f for f in features}
    resolved=component_contacts(features,records)
    contexts, native_pins=[], []
    native=Baseline(ROOT,detection['baseline_commit'],detection['inputs'])
    world=json.loads(native.read('data/world-index.json'))
    hierarchy=json.loads(native.read('data/hierarchy.json'))
    nodes={n['id']:n for n in hierarchy}
    if len(nodes)!=len(hierarchy):
        raise ValueError('Duplicate exact hierarchy identity')
    for part in world['parts']:
        path='data/'+safe_path(part)
        raw=native.read(path)
        native_pins.append(descriptor(path,raw))
        if path.endswith('.gz'):
            with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
                raw=stream.read(MAX_FILE_BYTES+1)
            if len(raw)>MAX_FILE_BYTES:
                raise ValueError('Complete original native part exceeds decoded budget')
        for leaf in json.loads(raw)['features']:
            context=hierarchy_context(leaf,nodes)
            context.update(original_feature_sha256=sha256(canonical_json(leaf)), original_input_path=path,
                           original_metadata=leaf['properties'].get('metadata',{}),
                           original_name=leaf['properties'].get('name'),
                           source_authority_status='not-independently-approved')
            contexts.append(context)
    context_by_id={r['id']:r for r in contexts}
    if len(context_by_id)!=len(contexts) or len(contexts)!=49625:
        raise ValueError('Incomplete or duplicate original worldwide location contexts')
    triage=inputs.json(TRIAGE)
    samples={}
    prefix=str(pathlib.PurePosixPath(TRIAGE).parent)+'/'
    for pin in triage['sample_parts']:
        # Legacy sample filenames were reported relative to their report directory.
        full={**pin,'path':prefix+pin['path']}
        for row in inputs.decoded(full['path'],full):
            if row['component_id'] in samples:
                raise ValueError('Duplicate original grid sample')
            samples[row['component_id']]=row
    if len(samples)!=triage['component_count']:
        raise ValueError('Incomplete original grid sample accounting')
    links_by_new=defaultdict(list)
    for ordinal,link in enumerate(family('component_links')):
        links_by_new[link['new_component']].append((ordinal,link))
    unknowns_by_new=defaultdict(list)
    new_member={binding['id']:component['id'] for component in records
                for binding in component['properties']['fragment_bindings']}
    old_bindings=[(binding['id'],identity) for identity,sample in samples.items()
                  for binding in sample['fragment_bindings']]
    old_member=dict(old_bindings)
    if len(old_member)!=len(old_bindings) or len(old_member)!=triage['fragment_count']:
        raise ValueError('Incomplete or duplicate original grid fragment memberships')
    links_by_old=defaultdict(list)
    for links in links_by_new.values():
        for ordinal,link in links:
            links_by_old[link['old_component']].append(link['new_component'])
    mapped_errors, unmatched_errors, difference_accounting = difference_unknown_accounting(
        report['difference_unknowns'], new_member, old_member, links_by_old)
    for identity,errors in mapped_errors.items():
        unknowns_by_new[identity].extend(errors)
    water_pin=triage['water_pilot_reference']
    water=inputs.json(water_pin['path'],water_pin)
    for row in report['overlay_unknowns']:
        unknowns_by_new[row['new_component']].append(row)
    issues=inputs.json(issues_path)
    declared=issue_subjects(issues)
    compiled_issues=issue_subject_index(declared)
    native_ids=set(context_by_id)
    investigation=[]
    for component,contact in zip(sorted(records,key=lambda r:r['id']),resolved):
        record=investigation_record(component,contact,by_fragment,operation_unknowns=unknowns_by_new[component['id']])
        scopes=related_issue_scopes(record['distinct_contact_ids'],record['positive_length_neighbor_ids'],declared,compiled=compiled_issues)
        if scopes:
            record=investigation_record(component,contact,by_fragment,links=scopes,operation_unknowns=unknowns_by_new[component['id']])
        record['legacy_grid_context']=legacy_grid_links(component['id'],links_by_new[component['id']],samples)
        record['archived_water_context']=legacy_water_links(component['id'],links_by_new[component['id']],samples,water['pilots'],water_pin)
        record['investigation_orders']=investigation_ranks(record,context_by_id)
        record['missing_native_contact_ids']=sorted(set(record['distinct_contact_ids'])-native_ids)
        investigation.append(record)
    counts=partition_accounting(investigation,[r['id'] for r in records])
    order_counts=attach_rank_positions(investigation)
    # Original native input envelope is retained as transport, not source authority.
    envelope=inputs.json(ENVELOPE)
    for row in envelope['entries']:
        inputs.read(row['encoded']['path'],row['encoded'])
    out.mkdir(parents=True,exist_ok=False)
    outputs={'investigations':write_parts(out,'investigations',investigation),
             'native_contexts':write_parts(out,'native-contexts',sorted(contexts,key=lambda r:r['id'])),
             'unmatched_original_unknowns':write_parts(out,'unmatched-original-unknowns',unmatched_errors)}
    result={'version':VERSION,'input_commit':commit,'executed_code_commit':executed,'code_inputs':code,
            'inputs':list(inputs.pins.values()),'original_native_inputs':list(native.pins.values()),
            'native_location_containing_parts':native_pins,
            'original_native_commit':detection['baseline_commit'],'original_component_report':generation['prefix']+'/report.json',
            'outputs':outputs,'component_count':len(investigation),'fragment_count':len(features),
            'native_context_count':len(contexts),'partition_counts':counts,'complete_order_counts':order_counts,
            'declared_issue_subject_roster_count':len(declared),
            'issue_subject_rosters':declared,
            'software':{'python':platform.python_version(),'zlib':zlib.ZLIB_RUNTIME_VERSION},
            'unmeasured_fragment_ids':report['unmeasured_new_ids'],
            'original_unknown_overlay_count':len(report['overlay_unknowns']),
            'original_unknown_difference_count':len(report['difference_unknowns']),
            'difference_unknown_accounting':difference_accounting,
            'surface_status':'unverified','administrative_assignment':None,
            'limits':['Every candidate retained; investigation ranks do not certify data or assign geography.',
                      'Complete original input bytes are preserved; Atlas metadata may describe reconciled upstream geometry.',
                      'Exact declared subject overlap locates related issues, not confirmed geometric repair scope.',
                      'Old grid evidence samples one old representative cell; new grid coverage remains unassessed.',
                      'Reference lake intersections and shoreline flags do not classify physical water.',
                      'Archived dated-water reports are joined as old-shape context only; original raster measurements are not recomputed.',
                      'Confirmed repairs, full grid/rendering verification and delivery remain separate required work.']}
    with (out/'report.json').open('xb') as stream:
        stream.write(canonical_json(result))
    print(json.dumps({'component_count':len(investigation),'partition_counts':counts,'status':'diagnostic-only'}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--commit',required=True)
    parser.add_argument('--issues',required=True)
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    run(args.commit,args.issues,args.output)
