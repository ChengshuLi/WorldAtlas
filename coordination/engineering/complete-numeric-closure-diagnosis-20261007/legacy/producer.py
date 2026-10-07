"""All-component source-relative GSHHG comparison; never a repair decision."""
import argparse
import datetime
import hashlib
import io
import json
import pathlib
import re
import struct
import subprocess
import sys
import time
import zipfile
from collections import Counter, defaultdict

import numpy
import shapely
from shapely import prepare, union_all
from shapely.affinity import translate
from shapely.geometry import box, mapping, shape
from shapely.strtree import STRtree

import comparison
import ellipsoidal_area
import immutable
import inputs

HERE = pathlib.Path(__file__).resolve().parent
OWNED = 'coordination/engineering/global-physical-comparison-20261006/'
SCIENCE_FILES = ('producer.py', 'comparison.py', 'inputs.py', 'immutable.py',
                 'ellipsoidal_area.py', 'input-config.json', 'run.py')
LIMIT = 33554432
SHARD = 8388608


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], stderr=subprocess.PIPE)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def freeze_guard(repo, commit):
    if re.fullmatch('[a-f0-9]{40}', commit) is None:
        raise ValueError('Exact immutable execution commit required')
    if git(repo, 'rev-parse', 'HEAD').decode().strip() != commit:
        raise ValueError('Execution checkout is not the declared immutable commit')
    rows = []
    for name in SCIENCE_FILES:
        path = HERE / name
        if not path.is_file() or path.is_symlink():
            raise ValueError('Executed scientific module is not ordinary')
        raw = path.read_bytes()
        expected = git(repo, 'show', commit + ':' + OWNED + name)
        if raw != expected:
            raise ValueError('Executed scientific module/config differs: ' + name)
        rows.append(dict(path=OWNED + name, bytes=len(raw), sha256=digest(raw)))
    for module in (comparison, ellipsoidal_area, immutable, inputs):
        if pathlib.Path(module.__file__).resolve() != HERE / (module.__name__ + '.py'):
            raise ValueError('Imported scientific helper escaped the frozen closure')
    return rows


class Products:
    """Existing deterministic gzip, bounded complete JSONL records per shard."""
    def __init__(self, directory):
        self.directory = directory
        directory.mkdir(parents=True, exist_ok=False)
        self.buffers = defaultdict(bytearray)
        self.ordinals = Counter()
        self.descriptors = []

    def emit(self, kind, row):
        raw = immutable.canonical_json(row)
        if len(raw) > LIMIT:
            raise ValueError('One complete scientific row exceeds ordinary decoded bound')
        if self.buffers[kind] and len(self.buffers[kind]) + len(raw) > SHARD:
            self.flush(kind)
        self.buffers[kind].extend(raw)

    def flush(self, kind):
        if not self.buffers[kind]:
            return
        raw = bytes(self.buffers.pop(kind))
        encoded = immutable.deterministic_gzip(raw)
        if len(raw) > LIMIT or len(encoded) > LIMIT:
            raise ValueError('Actual scientific ordinary product bound exceeded')
        name = f'{kind}-{self.ordinals[kind]:03}.jsonl.gz'
        self.ordinals[kind] += 1
        (self.directory / name).write_bytes(encoded)
        self.descriptors.append(dict(path=name, bytes=len(encoded), sha256=digest(encoded),
                                     uncompressed_bytes=len(raw), uncompressed_sha256=digest(raw),
                                     hash_kind='file-bytes'))

    def finish(self):
        for kind in sorted(self.buffers):
            self.flush(kind)
        return sorted(self.descriptors, key=lambda row: row['path'])


def load_candidates(repo, config):
    """Read every original body and reconstruct complete four ledger families."""
    groups = defaultdict(list)
    deltas = {}
    receipts = []
    source_code = None
    report = None
    for row in config['inputs']:
        raw = inputs.ordinary_git(repo, row['commit'], row['path'], row)
        decoded = inputs.checked_decoded(raw, row)
        receipts.append(dict(row, actual_encoded_sha256=digest(raw),
                             actual_decoded_bytes=len(decoded), actual_decoded_sha256=digest(decoded)))
        kind = row['kind']
        if kind in ('components', 'fragments', 'contacts', 'residues'):
            value = json.loads(decoded)
            groups[kind].extend(value['features'] if isinstance(value, dict) else value)
        elif kind.endswith('_delta'):
            deltas[kind[:-6]] = json.loads(decoded)
        elif kind == 'reconstruction_code':
            source_code = decoded
        elif kind == 'audit_report':
            report = json.loads(decoded)
    reconstruct, contact_key, code_receipt = inputs.existing_reconstructor(
        source_code, config['existing_reconstructor']['sha256'], immutable.canonical_json)
    current = {}
    lineage = {}
    for kind in ('components', 'fragments', 'contacts', 'residues'):
        key = contact_key if kind == 'contacts' else lambda row: row['id']
        current[kind] = reconstruct(groups[kind], deltas[kind], key)
        lineage[kind] = deltas[kind]
    if len(current['components']) != config['current_components']:
        raise ValueError('Incomplete current global component roster')
    fragments = {row['id']: row for row in current['fragments']}
    members = {}
    for component in current['components']:
        for binding in component['properties']['fragment_bindings']:
            identity = binding['id']
            if identity not in fragments or identity in members:
                raise ValueError('Missing or multiply bound complete fragment')
            if digest(immutable.canonical_json(fragments[identity])) != binding['feature_sha256']:
                raise ValueError('Complete fragment feature differs from component binding')
            members[identity] = component['id']
    if set(members) != set(fragments):
        raise ValueError('Complete fragment/component bijection differs')
    component_ids = {row['id'] for row in current['components']}
    for contact in current['contacts']:
        if not set(contact['components']) <= component_ids or not set(contact['fragments']) <= set(fragments):
            raise ValueError('Complete contact ledger escapes current roster')
    return current, lineage, receipts, code_receipt, report


def original_native(repo, config):
    """Read the complete supported original archive/member, not a hash reference."""
    parts = sorted((row for row in config['inputs'] if row['kind'] == 'archive_part'),
                   key=lambda row: row['ordinal'])
    body = bytearray()
    for ordinal, row in enumerate(parts):
        if row['ordinal'] != ordinal or row['offset'] != len(body):
            raise ValueError('Missing/reordered original source fragment')
        body.extend(inputs.ordinary_git(repo, row['commit'], row['path'], row))
    archive = config['source_archive']
    if archive['member'] != 'gshhs_f.b':
        raise ValueError('Wrong complete original native member identity')
    if len(body) != archive['original_bytes'] or digest(body) != archive['original_sha256']:
        raise ValueError('Complete original ZIP differs')
    with zipfile.ZipFile(io.BytesIO(body)) as zipped:
        names = zipped.namelist()
        if len(names) != 18 or len(set(names)) != len(names):
            raise ValueError('Complete original member inventory differs')
        native = zipped.read(archive['member'])
    if len(native) != archive['member_bytes'] or digest(native) != archive['member_sha256']:
        raise ValueError('Wrong/incomplete complete original native member')
    del body
    return native


def native_records(native, validity=None):
    """Yield actual original records; reject trailing or incomplete native bytes."""
    offset = ordinal = 0
    while offset < len(native):
        if len(native) - offset < 44:
            raise ValueError('Trailing/truncated original native header')
        header = native[offset:offset + 44]
        values = comparison.HEADER.unpack(header)
        length = values[1] * 8
        if offset + 44 + length > len(native):
            raise ValueError('Truncated original coordinate member')
        meta, geometry = comparison.decode_record(header, native[offset + 44:offset + 44 + length], ordinal, offset, validity)
        yield meta, geometry
        offset += 44 + length
        ordinal += 1
    if ordinal != 188612 or offset != len(native):
        raise ValueError('Incomplete original native source roster')


def load_source(repo, config, products):
    """Authenticate original ZIP then read every native row, without repair."""
    native = original_native(repo, config)
    validity = comparison.ValidityCache()
    metas, geometries = {}, {}
    for meta, geometry in native_records(native, validity):
        if meta['id'] in metas:
            raise ValueError('Duplicate complete original source identity')
        metas[meta['id']] = meta
        geometries[meta['id']] = geometry
    del native
    containers = {}
    for identity in sorted(metas):
        meta = metas[identity]
        level = meta['level']
        if level in (2, 3, 4):
            outcome = container_outcome(identity, metas, geometries, validity)
            containers[identity] = dict(child=identity, parent=meta['container'], **outcome)
            products.emit('containers', containers[identity])
        products.emit('sources', meta)
    # Invalid and unsupported native records remain in conservative bbox queries.
    source_ids = sorted(metas)
    envelopes = [geometries[identity] if geometries[identity] is not None
                 else box(*metas[identity]['decoded_pointset_bounds']) for identity in source_ids]
    return metas, geometries, containers, source_ids, STRtree(envelopes), validity


def container_outcome(identity, metas, geometries, validity=None):
    meta = metas[identity]
    parent = metas.get(meta['container'])
    if parent is None or parent['level'] != meta['level'] - 1:
        return dict(status='unknown', issue='missing-or-wrong-level-whole-container')
    return comparison.full_container_relation(geometries[identity], geometries[parent['id']], validity)


def chain_issues(identity, metas, containers):
    result = []
    seen = set()
    while metas[identity]['level'] in (2, 3, 4):
        if identity in seen:
            return result + [dict(source_id=identity, issue='source-container-cycle')]
        seen.add(identity)
        row = containers[identity]
        if row['status'] != 'supported':
            result.append(dict(source_id=identity, issue=row['issue']))
        parent = row['parent']
        if parent not in metas:
            break
        identity = parent
    return result


def dimensional_parts(geometry):
    """Traverse every exact operation member without simplifying coordinates."""
    polygons, contacts = [], []
    def visit(member):
        if member.is_empty:
            return
        if member.geom_type == 'Polygon':
            polygons.append(member)
        elif member.geom_type in ('MultiPolygon','GeometryCollection','MultiLineString','MultiPoint'):
            for child in member.geoms:
                visit(child)
        elif member.geom_type in ('LineString','Point','LinearRing'):
            contacts.append(member)
        else:
            raise ValueError('Unsupported complete operation member: '+member.geom_type)
    visit(geometry)
    return polygons, contacts


def geometry_evidence(geometry, candidate, candidate_geometry_sha):
    """Whole pointsets are ordinary output or complete candidate reconstruction."""
    if geometry.is_empty:
        return dict(kind='empty', geometry=mapping(geometry), area_m2=0.0, planar_area=0.0)
    polygons, contacts = dimensional_parts(geometry)
    area = ellipsoidal_area.area(union_all(polygons)) if polygons else 0.0
    if geometry.equals_exact(candidate, 0):
        return dict(kind='complete-candidate-alias', candidate_geometry_sha256=candidate_geometry_sha,
                    area_m2=area, planar_area=geometry.area)
    value = mapping(geometry)
    return dict(kind='whole-operation-pointset', geometry=value,
                geometry_sha256=digest(immutable.canonical_json(value)), area_m2=area,
                planar_area=geometry.area)


def compare_component(record, metas, geometries, containers, source_ids, tree, shifted, validity=None):
    candidate = shape(record['geometry'])
    row = dict(component_id=record['id'], candidate_feature_sha256=digest(immutable.canonical_json(record)),
               candidate_geometry_sha256=digest(immutable.canonical_json(record['geometry'])),
               original_context=record['properties'], physical_authority='unapproved',
               physical_status='unknown-source-fitness-and-observation-date',
               physical_limits=['Source-relative support does not settle narrow registration-sensitive shoreline/channel truth.',
                                'Unrecorded river widths, seasonal wetness, observation-date mismatch and source precision remain unmeasured.'],
               source_vintage='GSHHG2.3.7/2017-06-15 release; observation dates heterogeneous',
               query_relations=[], unresolved=[])
    context = record['properties']
    for flag, issue in (('touches_domain_boundary', 'measured-domain-edge-context'),
                        ('touches_blocked_tile', 'existing-blocked-tile-context'),
                        ('positive_area_input_overlap', 'existing-positive-input-overlap')):
        if context.get(flag):
            row['unresolved'].append(dict(issue=issue))
    if context.get('unmeasured_fragment_ids'):
        row['unresolved'].append(dict(issue='existing-unmeasured-complete-fragment',
                                      fragment_ids=context['unmeasured_fragment_ids']))
    if candidate.is_empty or not comparison.checked_validity(candidate, validity):
        row.update(status='unknown', unresolved=[dict(issue='invalid-or-empty-complete-candidate')])
        return row
    pieces = defaultdict(list)
    for identity, periodic_offset in comparison.conservative_source_pairs(candidate, tree, source_ids):
        meta = metas[identity]
        source = geometries[identity]
        source_chain_issues = chain_issues(identity, metas, containers)
        if source is None or meta['geometry_issues']:
            relation = dict(source_id=identity, periodic_offset=periodic_offset,
                            status='unknown', issues=meta['geometry_issues'],
                            container_chain_issues=source_chain_issues)
            row['query_relations'].append(relation)
            row['unresolved'].append(dict(source_id=identity, issue='unusable-complete-original-source'))
            continue
        key = (identity, periodic_offset)
        if key not in shifted:
            shifted[key] = translate(source, xoff=periodic_offset) if periodic_offset else source
            prepare(shifted[key])
        relation, piece = comparison.relation(candidate, shifted[key], identity, periodic_offset, validity)
        relation.update(source_record_sha256=meta['record_sha256'],
                        source_pointset_sha256=meta['decoded_pointset_binary64_sha256'],
                        source_level=meta['level'], source_container=meta['container'],
                        container_chain_issues=source_chain_issues)
        row['query_relations'].append(relation)
        if relation['status'] == 'unknown':
            row['unresolved'].append(dict(source_id=identity, issue=relation['issue']))
            row['unresolved'].extend(source_chain_issues)
        elif piece is not None and not piece.is_empty:
            try:
                polygon_members, contact_members = dimensional_parts(piece)
                if piece.geom_type == 'GeometryCollection':
                    relation['whole_mixed_operation'] = geometry_evidence(piece, candidate, row['candidate_geometry_sha256'])
                    relation['exact_polygon_members'] = [geometry_evidence(g, candidate, row['candidate_geometry_sha256']) for g in polygon_members]
                    relation['exact_contact_members'] = [geometry_evidence(g, candidate, row['candidate_geometry_sha256']) for g in contact_members]
                elif contact_members:
                    relation['whole_contact_operation'] = geometry_evidence(piece, candidate, row['candidate_geometry_sha256'])
                for polygon in polygon_members:
                    if polygon.area <= 0:
                        row['unresolved'].append(dict(source_id=identity, issue='nonempty-polygon-zero-planar-area'))
                if polygon_members:
                    row['unresolved'].extend(source_chain_issues)
                    pieces[meta['level']].extend(polygon_members)
            except Exception as error:
                row['unresolved'].append(dict(source_id=identity, issue='operation-member-partition-failed', exception_type=type(error).__name__,exception_message=str(error)))
                relation['whole_unpartitioned_operation'] = mapping(piece)
    try:
        support = comparison.alternating_support(candidate, pieces)
        evidence = {}
        for key, geometry in support.items():
            if key == 'hierarchy_disagreements':
                evidence[key] = {name: geometry_evidence(g, candidate, row['candidate_geometry_sha256'])
                                 for name, g in geometry.items()}
                for name, g in geometry.items():
                    if not g.is_empty:
                        row['unresolved'].append(dict(issue='positive-or-contact-hierarchy-disagreement', relation=name))
            else:
                evidence[key] = geometry_evidence(geometry, candidate, row['candidate_geometry_sha256'])
                if not geometry.is_empty and geometry.geom_type in ('Polygon', 'MultiPolygon') and evidence[key]['area_m2'] <= 0:
                    row['unresolved'].append(dict(issue='nonempty-polygon-zero-ellipsoidal-area', relation=key))
                # Closed land/water polygons naturally share zero-area edges;
                # retain that whole contact but do not call it positive overlap.
                contradictory = key == 'contradictory_land_water_support' and geometry.area > 0
                closure_difference = key in ('missing_reconstruction', 'extra_reconstruction') and not geometry.is_empty
                if contradictory or closure_difference:
                    row['unresolved'].append(dict(issue='nonempty-support-closure-disagreement', relation=key))
        row['complete_support'] = evidence
        land = support['mapped_land_support'].area > 0
        water = support['mapped_inland_water_support'].area > 0
        exterior = support['outside_mapped_L1_context'].area > 0
        row['status'] = ('unknown' if row['unresolved'] else 'mixed-source-support' if sum((land, water, exterior)) > 1
                         else 'mapped-land-support' if land else 'mapped-inland-water-support' if water
                         else 'outside-mapped-L1-context')
    except Exception as error:
        row.update(status='unknown')
        row['unresolved'].append(dict(issue='support-operation-failed', exception_type=type(error).__name__,
                                      exception_message=str(error)))
    return row


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=pathlib.Path, required=True)
    parser.add_argument('--execution', required=True)
    parser.add_argument('--out', type=pathlib.Path, required=True)
    args = parser.parse_args()
    if args.repo.resolve() != HERE.parents[2] or not args.out.is_absolute():
        raise ValueError('Use the owned repository and absolute owned-cache output')
    if '..' in args.out.parts or not args.out.resolve().is_relative_to(args.repo.resolve() / '.cache'):
        raise ValueError('Output escapes the owned cache')
    for parent in args.out.parents:
        if parent.is_symlink():
            raise ValueError('Symlink output ancestor')
        if parent == args.repo.resolve():
            break
    code = freeze_guard(args.repo, args.execution)
    config = json.loads((HERE / 'input-config.json').read_bytes())
    source_docs=[]
    for descriptor in config['primary_documentation']:
        path=HERE / descriptor['path']
        if path.is_symlink() or not path.is_file():
            raise ValueError('Nonordinary original source documentation')
        raw=path.read_bytes()
        if len(raw)!=descriptor['bytes'] or digest(raw)!=descriptor['sha256']:
            raise ValueError('Original source documentation bytes differ')
        if raw!=git(args.repo,'show',args.execution+':'+OWNED+descriptor['path']):
            raise ValueError('Source documentation changed after scientific freeze')
        source_docs.append(descriptor)
    runtime = dict(python=sys.version.split()[0], numpy=numpy.__version__, shapely=shapely.__version__, GEOS=shapely.geos_version_string)
    if runtime != config['runtime']:
        raise ValueError('Measured scientific runtime differs')
    products = Products(args.out)
    current, lineage, receipts, reconstruction, audit = load_candidates(args.repo, config)
    contact_members = defaultdict(list)
    for kind in ('fragments', 'contacts', 'residues'):
        for record in current[kind]:
            identity = (digest(immutable.canonical_json([record['fragments'], record['dateline'], record['kind']]))
                        if kind == 'contacts' else record['id'])
            if kind == 'contacts':
                for component in record['components']:
                    contact_members[component].append(identity)
            products.emit('retained-' + kind, dict(record_id=identity, feature_sha256=digest(immutable.canonical_json(record))))
    for kind, delta in lineage.items():
        products.emit('lineage', dict(kind=kind, delta=delta))
    candidates = current.pop('components')
    del current
    metas, geometries, containers, source_ids, tree, validity = load_source(args.repo, config, products)
    shifted = {}
    statuses = Counter()
    roster = []
    for position, record in enumerate(candidates):
        result = compare_component(record, metas, geometries, containers, source_ids, tree, shifted, validity)
        result['complete_contact_ids'] = sorted(contact_members[record['id']])
        products.emit('components', result)
        roster.append(dict(id=record['id'], feature_sha256=result['candidate_feature_sha256']))
        statuses[result['status']] += 1
        if (position + 1) % 500 == 0:
            print(json.dumps(dict(complete_components=position + 1, total=len(candidates))), flush=True)
    descriptors = products.finish()
    report = dict(version=1, execution_commit=args.execution, executed_code=code, runtime=runtime,
                  input_receipts=receipts, primary_documentation=source_docs, existing_reconstruction=reconstruction,
                  candidate_delivery=config['candidate_delivery'], source_delivery=config['source_delivery'],
                  component_count=len(candidates), complete_roster_sha256=digest(immutable.canonical_json(roster)),
                  source_record_count=len(metas), validity_cache=dict(actual_whole_object_checks=validity.checks, exact_object_reuses=validity.hits), statuses=dict(sorted(statuses.items())), products=descriptors,
                  limits=['Source-relative polygon support only, not current/historical physical truth, political assignment or repair permission.',
                          'Outside mappedL1 is unclassified exterior context, never inferred dryland.',
                          'Original WVS/WDBII source dates, resolution, known registration uncertainty and absent river widths remain unresolved.',
                          'Invalid, container, source-frame, domain-edge, unmeasured and numerical uncertainty remain explicit; no geometry repair.'])
    (args.out / 'report.json').write_bytes(immutable.canonical_json(report))
    print(json.dumps(dict(outcome='complete', components=len(candidates), statuses=report['statuses'])), flush=True)


if __name__ == '__main__':
    main()
