"""Complete actual-world successor from authenticated ancestor plus lossless deltas."""
import argparse
import hashlib
import json
import math
import pathlib
import struct
import subprocess
import sys
from collections import defaultdict

import shapely
from shapely.geometry import mapping, shape, box
from shapely.strtree import STRtree
from shapely.affinity import translate
from evidence.immutable import canonical_json, deterministic_gzip
from evidence.geometry import land_area_m2
from geographic_components import components
from physical_gap_audit import Detector, load_inputs, decode
from physical_gap_crosswalk import membership, crosswalk
from physical_gap_successor import verify_decoded_relation
from worldwide_gap_inventory import (ORIGINAL, ARTIFACT, WATER, WATER_ROOT,
                                    DETECTOR, COMPONENT_ROOT, COMPONENT_REPORT,
                                    query, validate_selected, digest, verify)

SELECTED = '79ffb2ed04702e16f009e4675a8d74ef9bd09d4f'
FROZEN = 'cea80a8aa1f8a55ccb448a8f2ff71e10c49a26f1'
FROZEN_REPORT = 'coordination/engineering/worldwide-inventory-1164-20261006/run-one/report.json'


def coordinate_bytes(value):
    """Exact binary64 tree: no rounding, normalization, order or signed-zero loss."""
    if isinstance(value, bool):
        raise ValueError('Boolean coordinate')
    if isinstance(value, (int, float)):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError('Nonfinite coordinate')
        if isinstance(value,int) and int(number)!=value:
            raise ValueError('Coordinate integer cannot convert exactly to binary64')
        return b'd' + struct.pack('>d', number)
    if isinstance(value, (list, tuple)):
        return b'[' + struct.pack('>Q', len(value)) + b''.join(coordinate_bytes(x) for x in value) + b']'
    if isinstance(value, dict):
        return b'{' + b''.join(canonical_json(k) + coordinate_bytes(value[k]) for k in sorted(value)) + b'}'
    if isinstance(value, str):
        return b's' + canonical_json(value)
    raise ValueError('Unsupported geometry member')


def numeric_metadata_bytes(value):
    """Typed JSON relation allowing only exactly represented numeric spelling."""
    if value is None:
        return b'n'
    if isinstance(value,bool):
        return b't' if value else b'f'
    if isinstance(value,(int,float)):
        number=float(value)
        if not math.isfinite(number):
            raise ValueError('Nonfinite numeric metadata')
        if isinstance(value,int) and int(number)!=value:
            return b'i'+canonical_json(value)
        return b'd'+struct.pack('>d',number)
    if isinstance(value,str):
        return b's'+canonical_json(value)
    if isinstance(value,list):
        return b'['+struct.pack('>Q',len(value))+b''.join(numeric_metadata_bytes(x) for x in value)+b']'
    if isinstance(value,dict):
        return b'{'+b''.join(canonical_json(k)+numeric_metadata_bytes(value[k]) for k in sorted(value))+b'}'
    raise ValueError('Unsupported source metadata member')


def overlay_neighbors(rows, changed_shapes):
    """Complete ordinary and exact wrapped-seam intersection candidates."""
    geometries=[shape(f['geometry']) for f in rows]
    tree=STRtree(geometries)
    west=[(i,translate(g,xoff=360)) for i,g in enumerate(geometries) if g.bounds[0]==-180]
    east=[(i,translate(g,xoff=-360)) for i,g in enumerate(geometries) if g.bounds[2]==180]
    west_tree,east_tree=STRtree([g for _,g in west]),STRtree([g for _,g in east])
    chosen=set()
    for g in changed_shapes:
        chosen.update(int(i) for i in tree.query(g,predicate='intersects'))
        if g.bounds[2]==180:
            chosen.update(west[int(i)][0] for i in west_tree.query(g,predicate='intersects'))
        if g.bounds[0]==-180:
            chosen.update(east[int(i)][0] for i in east_tree.query(g,predicate='intersects'))
    return [rows[i] for i in sorted(chosen)]


def overlay_links(pairs):
    links,unknown=[] ,[]
    for p in pairs:
        ids=(p['old_fragment'],p['new_fragment'])
        if p['status']!='checked' or p.get('equality_overlay_disagreement'):
            unknown.append(ids)
        elif p.get('intersection_planar_area',0)>0:
            links.append(ids)
        elif p.get('kind') in ('identical-coordinates','equal-point-set'):
            unknown.append(ids)
    return links,unknown


def keyed(rows):
    result = {r['id']: r for r in rows}
    if len(result) != len(rows):
        raise ValueError('Duplicate full record identity')
    return result


def contact_key(row):
    return digest(canonical_json([row['fragments'], row['dateline'], row['kind']]))


def record_delta(old, new, key=lambda r: r['id']):
    before, after = {key(r): r for r in old}, {key(r): r for r in new}
    if len(before) != len(old) or len(after) != len(new):
        raise ValueError('Duplicate delta identity')
    retained = sorted(k for k in before.keys() & after.keys()
                      if canonical_json(before[k]) == canonical_json(after[k]))
    remove = sorted(set(before) - set(retained))
    upsert = [after[k] for k in sorted(set(after) - set(retained))]
    delta = {'retained_count': len(retained), 'retained_ids_sha256': digest(canonical_json(retained)),
             'removed_ids': remove, 'upsert_records': upsert,
             'original_count': len(old), 'current_count': len(new),
             'original_records_sha256': digest(canonical_json([before[k] for k in sorted(before)])),
             'current_records_sha256': digest(canonical_json([after[k] for k in sorted(after)]))}
    reconstruct(old, delta, key)
    return delta


def reconstruct(original, delta, key=lambda r: r['id']):
    before = {key(r): r for r in original}
    if len(before) != len(original) or len(before) != delta['original_count']:
        raise ValueError('Original delta roster incomplete')
    if digest(canonical_json([before[k] for k in sorted(before)])) != delta['original_records_sha256']:
        raise ValueError('Original full record bytes differ')
    removed = delta['removed_ids']
    if len(removed) != len(set(removed)) or not set(removed) <= set(before):
        raise ValueError('Missing/duplicated removed record')
    retained = sorted(set(before) - set(removed))
    if len(retained) != delta['retained_count'] or digest(canonical_json(retained)) != delta['retained_ids_sha256']:
        raise ValueError('Retained roster omitted or expanded')
    after = {k: before[k] for k in retained}
    for row in delta['upsert_records']:
        if key(row) in after:
            raise ValueError('Duplicate reconstructed record')
        after[key(row)] = row
    result = [after[k] for k in sorted(after)]
    if len(result) != delta['current_count'] or digest(canonical_json(result)) != delta['current_records_sha256']:
        raise ValueError('Current full record bytes differ')
    return result


def tile_equal(before, after, old_members, new_members, old_unknowns, new_unknowns):
    for query_rows, bindings in ((before,old_members),(after,new_members)):
        for kind, identities in query_rows.items():
            if kind not in bindings or len(identities)!=len(set(identities)) or any(i not in bindings[kind] for i in identities):
                raise ValueError('Declared tile member missing or duplicated')
    return (canonical_json(before) == canonical_json(after)
            and canonical_json(old_unknowns) == canonical_json(new_unknowns)
            and all(old_members[k][i] == new_members[k][i]
                    for k in before for i in before[k]))


def component_lineage(old_components, new_components, fragment_links, unknown_links=()):
    old_by_fragment, new_by_fragment = membership_from_records(old_components), membership_from_records(new_components)
    links = defaultdict(set)
    for old_id, new_id in fragment_links:
        if old_id not in old_by_fragment or new_id not in new_by_fragment:
            raise ValueError('Lineage member absent from complete component roster')
        links[old_by_fragment[old_id]].add(new_by_fragment[new_id])
    reverse = defaultdict(set)
    for a, values in links.items():
        for b in values:
            reverse[b].add(a)
    unknown_old, unknown_new = set(), set()
    for a,b in unknown_links:
        if a not in old_by_fragment or b not in new_by_fragment:
            raise ValueError('Unknown lineage member absent')
        unknown_old.add(old_by_fragment[a]);unknown_new.add(new_by_fragment[b])
    def side(records, matches, original):
        rows = []
        for r in records:
            targets = sorted(matches.get(r['id'], []))
            rows.append({'id': r['id'], 'full_feature_sha256': digest(canonical_json(r)),
                         'fragment_ids': [b['id'] for b in r['properties']['fragment_bindings']],
                         'unmeasured_fragment_ids': r['properties']['unmeasured_fragment_ids'],
                         'counterparts': targets,
                         'relation': 'unknown-overlay' if r['id'] in (unknown_old if original else unknown_new) else
                                     ('removed' if original else 'new') if not targets else
                                     'split' if original and len(targets) > 1 else
                                     'merged' if not original and len(targets) > 1 else 'linked'})
        return rows
    return {'original': side(old_components, links, True), 'current': side(new_components, reverse, False)}


def membership_from_records(records):
    result = {}
    for component in records:
        for binding in component['properties']['fragment_bindings']:
            if binding['id'] in result:
                raise ValueError('Fragment belongs to multiple components')
            result[binding['id']] = component['id']
    return result


def overlay_membership_view(records, features):
    """Expose exact subset bindings to overlay; full world records stay intact."""
    ids = {f['id'] for f in features}
    result = []
    for record in records:
        bindings = [b for b in record['properties']['fragment_bindings'] if b['id'] in ids]
        if bindings:
            result.append({**record, 'properties': {**record['properties'],
                          'fragment_bindings': bindings,
                          'unmeasured_fragment_ids': [i for i in record['properties']['unmeasured_fragment_ids'] if i in ids]}})
    membership(features, result)
    return result


def run(repo, selected, output):
    validate_selected(selected)
    if selected != SELECTED or output.exists():
        raise ValueError('Use declared immutable actual input and new output vintage')
    execution = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip()
    subprocess.run(['git', 'merge-base', '--is-ancestor', selected, 'origin/main'], cwd=repo, check=True)
    cache = {}
    def blob(commit, path):
        key = (commit, path)
        if key not in cache:
            tree = subprocess.check_output(['git', 'ls-tree', commit, '--', path], cwd=repo).split()
            if not tree or tree[0] not in (b'100644', b'100755'):
                raise ValueError('Ordinary immutable file required: ' + path)
            cache[key] = subprocess.check_output(['git', 'show', commit + ':' + path], cwd=repo)
        return cache[key]
    def descriptor(path, raw):
        return {'path': path, 'bytes': len(raw), 'sha256': digest(raw), 'hash_kind': 'file-bytes'}
    if (sys.version.split()[0], shapely.__version__, shapely.geos_version_string) != ('3.12.14', '2.1.2', '3.13.1'):
        raise ValueError('Original pinned mathematical runtime required')
    executed_files = []
    for module in list(sys.modules.values()):
        filename = getattr(module, '__file__', None)
        if not filename:
            continue
        p = pathlib.Path(filename).resolve()
        try:
            path = 'scripts/' + str(p.relative_to(repo / 'scripts'))
        except ValueError:
            continue
        if p.is_symlink() or p.suffix != '.py' or p.read_bytes() != blob(execution, path):
            raise ValueError('Imported owned code differs from committed execution')
        executed_files.append(descriptor(path, p.read_bytes()))
    executed_files = list({r['path']: r for r in executed_files}.values())
    frozen = json.loads(blob(SELECTED, FROZEN_REPORT))
    for row in frozen['source_descriptors']:
        verify(blob(FROZEN, row['path']), row)
        if row['path'] not in ('data/geography/part-11.json', 'data/geography/part-17.json',
                               'data/geographic-releases/current-manifest.json'):
            verify(blob(selected, row['path']), row)
    detection = json.loads(blob(ARTIFACT, DETECTOR))
    old_data = load_inputs(repo, ORIGINAL, WATER_ROOT, WATER)
    current_data = load_inputs(repo, selected, WATER_ROOT, WATER)
    old_detector, new_detector = Detector(old_data), Detector(current_data)
    for field in ('water_inputs', 'invalid_land', 'invalid_water'):
        if canonical_json(old_data[field]) != canonical_json(current_data[field]):
            raise ValueError('Physical reference or unknown state changed')
    # Complete raw/decoded input custody; aliases do not replace reading sources.
    custody, encoded_sources = [], {}
    old_inputs = {r['path']: r for r in old_data['inputs']}
    new_inputs = {r['path']: r for r in current_data['inputs']}
    for label, commit, inputs in [('original', ORIGINAL, old_inputs), ('current', selected, new_inputs)]:
        for path, row in inputs.items():
            raw = verify(blob(commit, path), row)
            if path in ('data/geography/part-11.json', 'data/geography/part-17.json', 'data/geography/part-29.json',
                        'data/geographic-releases/current-manifest.json'):
                alias_label = 'unchanged' if path == 'data/geography/part-29.json' else label
                alias = 'custody/' + alias_label + '-' + path.replace('/', '_') + '.gz'
                encoded = deterministic_gzip(raw)
                relation = verify_decoded_relation(descriptor(alias, encoded), encoded, descriptor(path, raw), raw, 1)
                encoded_sources[alias] = encoded
                custody.append({'source_commit': commit, 'original': row, 'alias': descriptor(alias, encoded),
                                'decoded_relation': relation})
            else:
                custody.append({'source_commit': commit, 'original': row, 'retained_path': path})
    feature_proof = []
    source_members = {'original': {}, 'current': {}}
    for label, data in [('original', old_data), ('current', current_data)]:
        for kind, geometries, metadata in [('land', data['land'], data['land_metadata']),
                                            ('locations', data['locations'], data['location_metadata'])]:
            source_members[label][kind] = {m['id']: (digest(g.wkb), digest(canonical_json(m)))
                                            for g, m in zip(geometries, metadata)}
        source_members[label]['invalid_land'] = {r['id']: digest(canonical_json(r)) for r in data['invalid_land']}
        source_members[label]['invalid_locations'] = {r['id']: digest(canonical_json(r)) for r in data['invalid_locations']}
        source_members[label]['invalid_water'] = {r['id']: digest(canonical_json(r)) for r in data['invalid_water']}
        source_members[label]['shorelines'] = {f'physical-shoreline:{i}': digest(g.wkb)
                                              for i, g in enumerate((old_detector if label == 'original' else new_detector).shorelines)}
    old_features, current_features = {}, {}
    for label, commit, target in [('original', ORIGINAL, old_features), ('current', selected, current_features)]:
        world = json.loads(blob(commit, 'data/world-index.json'))
        for part in world['parts']:
            rows = json.loads(blob(commit, 'data/' + part))['features']
            for f in rows:
                identity = f.get('id') or f['properties']['id']
                if identity in target:
                    raise ValueError('Duplicate world source feature')
                target[identity] = f
    if set(old_features) != set(current_features):
        raise ValueError('Current source identity roster changed outside this integration')
    for identity in sorted(old_features):
        a, b = old_features[identity], current_features[identity]
        ma,mb={k:v for k,v in a.items() if k!='geometry'},{k:v for k,v in b.items() if k!='geometry'}
        metadata_equal=canonical_json(ma)==canonical_json(mb)
        metadata_numeric_equal=numeric_metadata_bytes(ma)==numeric_metadata_bytes(mb)
        if not metadata_numeric_equal:
            raise ValueError('Source metadata semantic change outside declared integration')
        feature_proof.append({'id': identity, 'original_feature_sha256': digest(canonical_json(a)),
                              'current_feature_sha256': digest(canonical_json(b)),
                              'original_geometry_sha256': digest(canonical_json(a['geometry'])),
                              'current_geometry_sha256': digest(canonical_json(b['geometry'])),
                              'original_binary64_sha256': digest(coordinate_bytes(a['geometry'])),
                              'current_binary64_sha256': digest(coordinate_bytes(b['geometry'])),
                              'original_metadata_sha256':digest(canonical_json(ma)),
                              'current_metadata_sha256':digest(canonical_json(mb)),
                              'original_numeric_metadata_sha256':digest(numeric_metadata_bytes(ma)),
                              'current_numeric_metadata_sha256':digest(numeric_metadata_bytes(mb)),
                              'metadata_canonical_equal':metadata_equal,
                              'metadata_numeric_equal':metadata_numeric_equal})
    def read_features(row, path=None):
        raw = verify(blob(ARTIFACT, path or row['path']), {**row, 'path': path or row['path']})
        decoded = decode(raw)
        if len(decoded) != row['uncompressed_bytes'] or digest(decoded) != row['uncompressed_sha256']:
            raise ValueError('Archived decoded feature custody mismatch')
        value = json.loads(decoded)
        return value['features'] if isinstance(value, dict) else value
    fragments = [f for row in detection['outputs'] for f in read_features(row)]
    residues = [f for row in detection['residue_outputs'] for f in read_features(row)]
    index = json.loads(blob(ARTIFACT, COMPONENT_ROOT + 'custody-v1/index.json'))
    comp_report = json.loads(blob(ARTIFACT, COMPONENT_REPORT))
    aliases = {r['original']['path']: r['payload'] for r in index['aliases']}
    old_components = [f for row in comp_report['outputs']['new_components'] for f in read_features(row, aliases[row['path']])]
    old_contacts = [f for row in comp_report['outputs']['new_contacts'] for f in read_features(row, aliases[row['path']])]
    membership(fragments, old_components)
    by_tile, residue_by_tile = defaultdict(list), defaultdict(list)
    for f in fragments:
        by_tile[int(f['id'].split(':')[1])].append(f)
    for f in residues:
        residue_by_tile[int(f['id'].split(':')[1])].append(f)
    new_fragments, new_residues, tile_rows, changed = [], [], [], []
    for row in detection['tiles']:
        tid, bounds = row['id'], row['bounds']
        before, after = query(old_detector, old_data, bounds), query(new_detector, current_data, bounds)
        old_unknowns = [r for kind in ('invalid_land', 'invalid_locations', 'invalid_water')
                        for r in old_data[kind] if box(*r['unchecked_bounds']).intersects(box(*bounds))]
        new_unknowns = [r for kind in ('invalid_land', 'invalid_locations', 'invalid_water')
                        for r in current_data[kind] if box(*r['unchecked_bounds']).intersects(box(*bounds))]
        reusable = tile_equal(before, after, source_members['original'], source_members['current'], old_unknowns, new_unknowns)
        evidence = {'tile_id': tid, 'bounds': bounds, 'original_query': before, 'current_query': after,
                    'original_unknowns': old_unknowns, 'current_unknowns': new_unknowns, 'reused': reusable}
        if reusable:
            new_fragments.extend(by_tile[tid]); new_residues.extend(residue_by_tile[tid])
            evidence['result'] = row
        else:
            changed.append(tid)
            result = new_detector.tile(bounds)
            evidence['result'] = {k:v for k,v in result.items() if k not in ('candidates', 'physical_shore')}
            if result['status'] == 'checked':
                for j, piece in enumerate(result['candidates']):
                    geometry = mapping(piece)
                    identity = f'physical-gap:{tid}:{j}:{digest(canonical_json(geometry))}'
                    try:
                        area = land_area_m2(piece)
                        if not math.isfinite(area) or area <= 0:
                            raise ValueError('Nonpositive/nonfinite source area')
                        error = None
                    except (ValueError, OverflowError) as exception:
                        area, error = None, str(exception)
                    properties = {'status':'uncovered-physical-reference-candidate', 'tile':list(bounds),
                                  'area_m2':area, 'original_planar_area':piece.area,
                                  'touches_reference_shore':piece.intersects(result['physical_shore']),
                                  'exact_location_contacts':new_detector.contacts(piece),
                                  'water_diagnostics':new_detector.water_diagnostics(piece),
                                  'water_status':'unverified', 'administrative_assignment':None}
                    if error is not None:
                        evidence.setdefault('measurement_errors', []).append({'fragment':identity,'error':error})
                    new_fragments.append({'type':'Feature','id':identity,'geometry':geometry,'properties':properties})
                for j, residue in enumerate(result['residues']):
                    new_residues.append({'type':'Feature','id':f'physical-residue:{tid}:{j}',
                                         'geometry':residue['geometry'],
                                         'properties':{**{k:v for k,v in residue.items() if k!='geometry'},
                                                       'tile':list(bounds),'status':'retained-nonpolygon-residue'}})
        tile_rows.append(evidence)
    print('Authenticated all source features and tile operands; changed tiles', changed, flush=True)
    blocked = [r['result'] for r in tile_rows if r['result']['status'] != 'checked']
    new_components, new_contacts = components(new_fragments, blocked, detection['bounds'])
    for c in new_components:
        c['id'] = 'physical-component:' + c['id'].split(':',1)[1]
    members = membership(new_fragments, new_components)
    for c in new_contacts:
        c['components'] = [members[f] for f in c['fragments']]
    deltas = {'fragments':record_delta(fragments,new_fragments), 'residues':record_delta(residues,new_residues),
              'components':record_delta(old_components,new_components), 'contacts':record_delta(old_contacts,new_contacts,contact_key)}
    # Full unchanged-record bijections plus exact changed-fragment overlay and
    # its complete neighboring contact closure; no duplicate global geometries.
    original_by_id, current_by_id = keyed(fragments), keyed(new_fragments)
    retained = {i for i in original_by_id.keys() & current_by_id.keys()
                if canonical_json(original_by_id[i]) == canonical_json(current_by_id[i])}
    old_changed = [f for f in fragments if f['id'] not in retained]
    new_changed = [f for f in new_fragments if f['id'] not in retained]
    changed_shapes = [shape(f['geometry']) for f in old_changed + new_changed]
    old_overlay,new_overlay=overlay_neighbors(fragments,changed_shapes),overlay_neighbors(new_fragments,changed_shapes)
    overlay = crosswalk(old_overlay,new_overlay,
                        overlay_membership_view(old_components,old_overlay),
                        overlay_membership_view(new_components,new_overlay))
    overlay['component_ledger_scope'] = 'Only exact overlay fragment bindings; full original/current component ledger follows separately.'
    changed_links,unknown_links=overlay_links(overlay['fragment_pairs'])
    links=[(i,i) for i in sorted(retained)]+changed_links
    lineage = {'retained_full_record_count':len(retained),
               'retained_full_record_ids_sha256':digest(canonical_json(sorted(retained))),
               'retained_rule':'All original IDs absent from fragment removed_ids retain their identical full canonical feature bytes.',
               'changed_fragment_overlay':overlay, 'components':component_lineage(old_components,new_components,links,unknown_links),
               'original_unmeasured_fragment_ids':sorted(f['id'] for f in fragments if f['properties'].get('area_m2') is None),
               'current_unmeasured_fragment_ids':sorted(f['id'] for f in new_fragments if f['properties'].get('area_m2') is None)}
    output.mkdir(parents=True)
    products = []
    def emit(name, value):
        raw = canonical_json(value)
        if len(raw)>32*1024*1024:
            raise ValueError('Product decoded budget exceeded: '+name)
        encoded = deterministic_gzip(raw) if name.endswith('.gz') else raw
        (output/name).parent.mkdir(parents=True,exist_ok=True)
        (output/name).write_bytes(encoded)
        products.append({**descriptor(name,encoded),'uncompressed_bytes':len(raw),'uncompressed_sha256':digest(raw)} if name.endswith('.gz') else descriptor(name,encoded))
    for name,raw in encoded_sources.items():
        (output/name).parent.mkdir(parents=True,exist_ok=True);(output/name).write_bytes(raw)
        products.append({**descriptor(name,raw),'uncompressed_bytes':len(decode(raw)),'uncompressed_sha256':digest(decode(raw))})
    emit('source-custody.json',custody)
    for start in range(0,len(feature_proof),10000):
        emit(f'source-feature-bindings-{start//10000:02d}.json.gz',feature_proof[start:start+10000])
    emit('tile-queries.json.gz',tile_rows)
    for name,delta in deltas.items():
        emit(name+'-delta.json.gz',delta)
    # Complete component ledger is split losslessly under unchanged decoded cap.
    for side in ('original','current'):
        rows = lineage['components'][side]
        for start in range(0,len(rows),20000):
            emit(f'component-lineage-{side}-{start//20000:02d}.json.gz',rows[start:start+20000])
    del lineage['components']
    emit('fragment-lineage.json.gz',lineage)
    summary = {'version':'worldatlas-actual-world-successor-v1','selected_input_commit':selected,
               'executed_code_commit':execution,'executed_code_files':executed_files,
               'original_input_commit':ORIGINAL,'frozen_selected_commit':FROZEN,'measurement_artifact_commit':ARTIFACT,
               'release_ids':current_data['release_ids'],'release_index_sha256':current_data['release_index_sha256'],
               'tiles':len(tile_rows),'changed_tiles':changed,'reused_tiles':len(tile_rows)-len(changed),
               'original_counts':{'fragments':len(fragments),'components':len(old_components),'residues':len(residues),'contacts':len(old_contacts)},
               'current_counts':{'fragments':len(new_fragments),'components':len(new_components),'residues':len(new_residues),'contacts':len(new_contacts)},
               'deltas':{k:{x:v for x,v in d.items() if x not in ('upsert_records','removed_ids')} for k,d in deltas.items()},
               'source_canonical_feature_changes':sum(r['original_feature_sha256']!=r['current_feature_sha256'] for r in feature_proof),
               'source_binary64_geometry_changes':sum(r['original_binary64_sha256']!=r['current_binary64_sha256'] for r in feature_proof),
               'source_canonical_metadata_changes':sum(not r['metadata_canonical_equal'] for r in feature_proof),
               'complete_ancestor_products':frozen['complete_products'],'products':products,
               'limits':frozen['limits']+['Current input is explicitly selected79ff; no later release claims.',
                                        'Exact binary64 equality does not imply raw JSON identity.',
                                        'Current tile measurements are dated to this execution; unchanged full records retain their original measurement vintage.',
                                        'Native/context/ranking remain independent1184 work; no core repair or deployment.']}
    emit('report.json',summary)
    print(json.dumps(summary['current_counts']),flush=True)
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--selected',required=True)
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    run(pathlib.Path(__file__).resolve().parents[1],args.selected,pathlib.Path(args.output).resolve())
