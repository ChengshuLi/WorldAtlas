"""One bounded original-AGO custody and conditional mechanism comparison.

The archived envelope is an undated processed reference, not authenticated as
refresh-angola's immediate input. No output here is an approved repair.
"""
import ast, collections, gc, gzip, hashlib, io, json, pathlib, platform, resource, subprocess, sys

NAMESPACE = 'coordination/engineering/angola-original-envelope-20261007/'
CAP = 32 * 1024 * 1024
PHASE = 256 * 1024 * 1024
BLOCK = 1024 * 1024


def canonical(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def unique(rows, key):
    ids = [r[key] for r in rows]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate actual raw identities: ' + key)
    return {r[key]: r for r in rows}


def whole_archive(encoded, pin, select=False):
    """Complete two-pass private stream, never materialize a 56 MiB body.

    First pass authenticates every decoded byte and parses all 19,050 records,
    including unique identities and outer JSON. Only the second pass may select
    semantic records. Individual records and the outer skeleton stay <32 MiB.
    """
    if len(encoded) != pin['bytes'] or sha(encoded) != pin['sha256']:
        raise ValueError('Private whole encoded archive mismatch')
    digest = hashlib.sha256(); total = 0; prefix = bytearray(); suffix = bytearray()
    depth = 0; quoted = False; escape = False; record = bytearray()
    inside = False; done = False; offset = 0; count = 0; largest = 0
    seen = set(); chosen = []; header = None
    with gzip.GzipFile(fileobj=io.BytesIO(encoded)) as source:
        while True:
            block = source.read(BLOCK)
            if not block:
                break
            digest.update(block); total += len(block)
            if total > pin['decoded_bytes']:
                raise ValueError('Private stream exceeds declared whole body')
            for byte in block:
                if not inside:
                    if done:
                        suffix.append(byte)
                    else:
                        prefix.append(byte)
                        if prefix.endswith(b'"locations":['):
                            header = bytes(prefix); inside = True
                        if len(prefix) > CAP:
                            raise ValueError('Private archive prefix cap')
                elif depth:
                    record.append(byte)
                    if len(record) > CAP:
                        raise ValueError('Individual archive record cap')
                    if quoted:
                        if escape:
                            escape = False
                        elif byte == 92:
                            escape = True
                        elif byte == 34:
                            quoted = False
                    elif byte == 34:
                        quoted = True
                    elif byte in (123, 91):
                        depth += 1
                    elif byte in (125, 93):
                        depth -= 1
                    if depth == 0:
                        raw = bytes(record); value = json.loads(raw)
                        identity = value['id']
                        if identity in seen:
                            raise ValueError('Duplicate original archive identity')
                        seen.add(identity); count += 1; largest = max(largest, len(raw))
                        if select and identity.startswith('gb:AGO:ADM2:91424787'):
                            chosen.append((value, raw, start))
                        record.clear()
                elif byte == 123:
                    start = offset; record.append(byte); depth = 1; quoted = False
                elif byte == 93:
                    inside = False; done = True; suffix.append(byte)
                elif byte not in (9, 10, 13, 32, 44):
                    raise ValueError('Malformed archive locations delimiter')
                offset += 1
            if len(suffix) > CAP:
                raise ValueError('Private outer skeleton cap')
    if total != pin['decoded_bytes'] or digest.hexdigest() != pin['decoded_sha256'] or count != pin['records'] or depth or not done:
        raise ValueError('Private complete decoded identity/record inventory mismatch')
    outer = json.loads(header + bytes(suffix))
    if outer['locations'] != []:
        raise ValueError('Invalid complete outer skeleton')
    return chosen, {'encoded_bytes': len(encoded), 'encoded_sha256': sha(encoded),
                    'decoded_bytes': total, 'decoded_sha256': digest.hexdigest(),
                    'all_records': count, 'largest_record_bytes': largest,
                    'outer_skeleton_sha256': sha(header + bytes(suffix)),
                    'outer_metadata': {k: v for k, v in outer.items() if k not in ('original_records', 'original_entities', 'units')},
                    'outer_units_count': len(outer['units']), 'outer_units_canonical_sha256': sha(canonical(outer['units'])),
                    'ordinary_decoded_cap_pass': False,
                    'custody': 'explicit complete-stream private reconstruction; two passes; semantic selection after first complete verification'}


def run(repo, args, immutable, code, own):
    plan = json.loads(own['input-plan.json'])
    if len(plan['ordinary_inputs']) > 512:
        raise ValueError('Descriptor cap')
    base = immutable.Baseline(repo, plan['baseline_commit'], plan['ordinary_inputs'])
    # Account exact private stream and code inputs in the same total ceiling;
    # no ordinary-file cap waiver or encoded-only archive admission occurs.
    private = plan['private_archive']
    runtime_plan = json.loads(own['runtime-plan.json'])
    runtime_roots = {'prefix': pathlib.Path(sys.prefix).resolve(), 'base_prefix': pathlib.Path(sys.base_prefix).resolve()}
    if len(runtime_plan['files']) + len(plan['ordinary_inputs']) + len(code.pins) > 512:
        raise ValueError('Complete runtime/input/code descriptor cap')
    for pin in runtime_plan['files']:
        path = runtime_roots[pin['root']] / pin['path']
        with path.open('rb') as stream:
            actual = stream.read(CAP + 1)
        if len(actual) > CAP or len(actual) != pin['bytes'] or sha(actual) != pin['sha256']:
            raise ValueError('Actually consumed installed runtime drift')
    total_forecast = plan['resource_forecast']['ordinary_phase_bytes'] + private['bytes'] + private['decoded_bytes'] + sum(code.consumed.values()) + runtime_plan['total_bytes'] + plan['resource_forecast']['max_output_bytes'] + 4096
    if total_forecast > PHASE or plan['resource_forecast']['max_rss_bytes'] != 512 * 1024 * 1024:
        raise ValueError('Whole ordinary/private/code/output phase forecast')
    out = immutable.NewVintage(code, NAMESPACE, args.run, plan['output_names'])
    by_path = {p['path']: p for p in plan['ordinary_inputs']}
    consumed = []

    def read(path, decode=False):
        raw = base.pinned_bytes(path); pin = by_path[path]
        if decode:
            with gzip.GzipFile(fileobj=io.BytesIO(raw)) as z:
                decoded = z.read(CAP + 1)
            if len(decoded) > CAP or len(decoded) != pin['uncompressed_bytes'] or sha(decoded) != pin['uncompressed_sha256']:
                raise ValueError('Complete decoded ordinary containing body drift')
            base.admit(path + ':decoded', len(decoded)); raw = decoded
        consumed.append(path)
        return raw

    # Complete authentication/admission of every declared ordinary input occurs
    # before installed GIS imports or geometry construction/calculation.
    for pin in plan['ordinary_inputs']:
        read(pin['path'], 'uncompressed_bytes' in pin)
    scope = json.loads(own['triage.json'])['cohorts'][0]['complete_families']
    if sha(own['triage.json']) != plan['scope_sha256']:
        raise ValueError('Authoritative triage identity')
    frozen_scope = scope
    required_frames = sorted({frame for f in frozen_scope for frame in f['containing_parts']})
    actual_frames = sorted(pathlib.Path(p['path']).name for p in plan['ordinary_inputs'] if p['kind'] == 'families')
    if required_frames != actual_frames or plan['required_family_frames'] != required_frames:
        raise ValueError('Whole family containing-frame UNION mismatch')
    if args.scope_fixture:
        target = pathlib.Path(args.scope_fixture)
        if target.is_symlink() or target.stat().st_size > CAP:
            raise ValueError('Scope fixture ordinary bound')
        scope = json.loads(target.read_bytes())
    unique(scope, 'family')
    wanted = [c for f in scope for c in f['complete_component_ids']]
    if len(wanted) != 10 or len(set(wanted)) != 10 or len(scope) != 8:
        raise ValueError('Complete eight-family/ten-component roster')
    contacts = sorted({c for f in scope for c in f['full_contacts']})
    if len(contacts) != 9:
        raise ValueError('Complete nine-contact roster')
    for f in scope:
        reference = next(r for r in frozen_scope if r['family'] == f['family'])
        if f != reference:
            raise ValueError('Scope identities/contacts/parents differ from independent frozen triage')
    family_rows = {}
    for pin in plan['ordinary_inputs']:
        if pin['kind'] != 'families':
            continue
        body = read(pin['path'], True)
        # Parts are byte frames, so only complete interior JSONL lines are
        # parsed; selected records are admitted only by their independent hash.
        for line in body.splitlines():
            try:
                row = json.loads(line)
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
            if row['id'] in {f['family'] for f in scope}:
                if row['id'] in family_rows:
                    raise ValueError('Duplicate selected family')
                f = next(f for f in scope if f['family'] == row['id'])
                if sha(canonical(row)) != f['row_sha256'] or sorted(row['complete_component_ids']) != sorted(f['complete_component_ids']) or sorted(row['original_fine_family']['contact_ids']) != sorted(f['full_contacts']):
                    raise ValueError('Complete family/contact/source identity binding')
                family_rows[row['id']] = row
    if len(family_rows) != 8:
        raise ValueError('Missing complete selected family; byte-frame boundary requires additional containing frame')
    batch_body = b''.join(read(p['path'], True) for p in plan['ordinary_inputs'] if p['kind'] == 'batches')
    batch_all = [json.loads(line) for line in batch_body.splitlines()]
    if len(unique(batch_all, 'id')) != 594:
        raise ValueError('Complete batch inventory')
    batch_ids = {f['operational_batch'] for f in scope}
    batches = [r for r in batch_all if r['id'] in batch_ids]
    if len(batches) != 3 or sum(r['fine_family_count'] for r in batches) != 173 or sum(r['component_count'] for r in batches) != 543:
        raise ValueError('Complete containing three-batch context')
    del batch_all, batch_body; gc.collect()
    features = {}
    for pin in plan['ordinary_inputs']:
        if pin['kind'] == 'components':
            records = json.loads(read(pin['path'], True))['features']
            unique(records, 'id')
            for f in records:
                if f['id'] in wanted:
                    if f['id'] in features:
                        raise ValueError('Duplicate original complete component')
                    features[f['id']] = f
            del records
    delta_pin = next(p for p in plan['ordinary_inputs'] if p['kind'] == 'component-delta')
    delta = json.loads(read(delta_pin['path'], True))
    if set(wanted) & set(delta['removed_ids']):
        raise ValueError('A selected original component was retired')
    for f in delta['upsert_records']:
        if f['id'] in wanted:
            features[f['id']] = f
    if set(features) != set(wanted):
        raise ValueError('Incomplete actual original pointsets')
    current = json.loads(read('data/geography/part-29.json'))['features']
    unique(current, 'id')
    current_ago = [f for f in current if f['properties']['reference_owner'] == 'Angola']
    current_contacts = [f for f in current if f['id'] in contacts]
    if len(current_ago) != 161 or sorted(f['id'] for f in current_contacts) != contacts:
        raise ValueError('Actual current containing part/whole Angola contacts')
    hierarchy = unique(json.loads(read('data/hierarchy.json')), 'id')
    parent_chains = {}
    for f in current_contacts:
        pid = f['properties']['parent_id']; chain = []; seen = set()
        while pid:
            if pid in seen or pid not in hierarchy:
                raise ValueError('Current parent identity/chain join')
            seen.add(pid); parent = hierarchy[pid]; chain.append(parent); pid = parent.get('parent_id')
        parent_chains[f['id']] = chain
    del current, hierarchy; gc.collect()
    source_pin = next(p for p in plan['ordinary_inputs'] if p['kind'] == 'source')
    source_raw = code.materialized_bytes(NAMESPACE + 'source.geojson')
    if args.source_fixture:
        fixture = pathlib.Path(args.source_fixture)
        if fixture.is_symlink() or fixture.stat().st_size > CAP:
            raise ValueError('Source fixture ordinary-file cap')
        source_raw = fixture.read_bytes()
    if sha(source_raw) != plan['source_raw_sha256'] or source_raw != read(source_pin['path'], True):
        raise ValueError('Actually consumed source drift')
    source = json.loads(source_raw)
    source_features = source['features']; unique([f['properties'] for f in source_features], 'shapeID')
    if len(source_features) != 161:
        raise ValueError('Complete original source roster')
    archive_tree = subprocess.check_output(['git', '-C', str(repo), 'ls-tree', private['commit'], '--', private['path']]).decode().strip().split()
    if len(archive_tree) != 4 or archive_tree[0] != '100644':
        raise ValueError('Private archive ordinary immutable Git object')
    archive_encoded = subprocess.check_output(['git', '-C', str(repo), 'cat-file', 'blob', archive_tree[2]])
    _, archive_receipt = whole_archive(archive_encoded, private, False)
    selected, second = whole_archive(archive_encoded, private, True)
    if archive_receipt != second or len(selected) != 158:
        raise ValueError('Private repeated stream/selection mismatch')
    retired = [r['id'] for r in json.loads(read('data/semantic-report.json'))['retired'] if r['id'].startswith('gb:AGO:ADM2:91424787')]
    if sorted(retired) != sorted(r['id'] for r, raw, offset in selected):
        raise ValueError('Recorded executed refresh obsolete identity join')
    anchor = json.loads(read(private['metadata_anchor']['path']))
    archive_rows = [r for r in anchor['files'] if r['sha256'] == private['sha256']]
    if len(archive_rows) != 1 or archive_rows[0]['bytes'] != private['bytes']:
        raise ValueError('Independent whole private archive metadata anchor')
    archive_encoded = None; gc.collect()
    if args.validate_inputs_only:
        print(json.dumps({'status': 'complete-input-only-admission-no-GIS-import-or-calculation', 'execution_commit': args.commit,
                          'complete_families': 8, 'complete_components': 10, 'complete_contacts': 9, 'complete_context_batches': 3,
                          'complete_context_families': 173, 'complete_context_components': 543, 'whole_archive_records': 19050,
                          'selected_archive_records': 158, 'source_features': 161, 'actual_family_frame_union': required_frames,
                          'family_row_hashes': {f['family']: f['row_sha256'] for f in scope},
                          'ordinary_input_bytes': sum(base.consumed.values()), 'private_input_bytes': private['bytes'] + private['decoded_bytes'],
                          'runtime_input_bytes': runtime_plan['total_bytes'], 'admitted_total_forecast_bytes': total_forecast,
                          'max_rss_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                          'source_raw_sha256': sha(source_raw), 'archive_whole': archive_receipt,
                          'destination_admitted_not_created': str(out.root.relative_to(repo))}))
        return
    # Full source/input/code/output admission is complete here. Every archive
    # raw record is preserved untouched; original invalidity is never repaired.
    if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss > plan['resource_forecast']['max_rss_bytes']:
        raise ValueError('Measured pre-GIS peak exceeds conservative RAM budget')
    import shapely
    from shapely import union_all, make_valid
    from shapely.geometry import shape, mapping, Polygon
    from shapely.validation import explain_validity
    admitted_runtime = {(p['root'], p['path']) for p in runtime_plan['files']}
    for module in sys.modules.values():
        for attribute in ('__file__', '__cached__'):
            name = getattr(module, attribute, None)
            if not name:
                continue
            path = pathlib.Path(name).resolve()
            for root_name, root_path in runtime_roots.items():
                if path.is_file() and path.is_relative_to(root_path) and (root_name, str(path.relative_to(root_path))) not in admitted_runtime:
                    raise ValueError('Undeclared actually imported runtime code: ' + str(path.relative_to(root_path)))
    old = [r for r, raw, offset in selected]
    og = [shape(f['geometry']) for f in old]
    sg = [shape(f['geometry']) for f in source_features]
    cg = {i: shape(f['geometry']) for i, f in features.items()}
    validity = [{'id': f['id'], 'is_valid': g.is_valid, 'is_empty': g.is_empty, 'reason': explain_validity(g)} for f, g in zip(old, og)]
    if any(not g.is_valid or g.is_empty for g in og + sg + list(cg.values())):
        raise ValueError('Original invalidity requires separate diagnostic interpretation; no silent repair')
    envelope = union_all(og); source_union = union_all(sg)
    # Execute the EXACT retained refresh poly/cutting/residual-buffer operators
    # over the CONDITIONAL archived old envelope, with no new repair application.
    method_raw = read('scripts/refresh-angola.py')
    method_ast = ast.parse(method_raw)
    nodes = [n for n in method_ast.body if (isinstance(n, ast.FunctionDef) and n.name == 'poly') or (16 <= n.lineno <= 26)]
    method = ast.Module(body=nodes, type_ignores=[])
    environment = {'union_all': union_all, 'make_valid': make_valid, 'Polygon': Polygon,
                   'shape': shape, 'envelope': envelope, 'remaining': envelope, 'source': source_features, 'parts_geo': []}
    exec(compile(method, 'pinned-refresh-angola-lines-9-12-and-16-26', 'exec'), environment)
    parts = environment['parts_geo']; residual = environment['remaining']
    vote_loop = next(n for n in method_ast.body if isinstance(n, ast.For) and n.lineno == 27)
    vote_nodes = [n for n in vote_loop.body if 29 <= n.lineno <= 31]
    vote_method = ast.Module(body=vote_nodes, type_ignores=[])
    vote_code = compile(vote_method, 'pinned-refresh-angola-lines29-31', 'exec')
    historical_old_features = [{'properties': {'parent_id': r['parent_id']}} for r in old]
    diagnostic = []; votes_all = []
    for f, geometry in zip(source_features, parts):
        vote_environment = {'collections': collections, 'g': geometry, 'old': historical_old_features, 'og': og}
        exec(vote_code, vote_environment)
        votes = vote_environment['votes']
        parent = max(votes, key=votes.get) if votes else None
        votes_all.append({'source_id': f['properties']['shapeID'], 'old_parent_overlap_votes_degrees2': dict(votes), 'conditional_old_parent': parent})
        diagnostic.append({'type': 'Feature', 'id': 'gb:AGO:ADM2:' + f['properties']['shapeID'], 'properties': {'conditional_archived_envelope_only': True, 'old_parent_vote': parent}, 'geometry': mapping(geometry)})
    part_union = union_all(parts)
    recorded_revision = json.loads(read('data/semantic-report.json'))['angola_source_revision']
    results = []
    for identity in sorted(wanted):
        g = cg[identity]; missing_old = g.difference(envelope); missing_source = g.difference(source_union); missing_conditional = g.difference(part_union)
        results.append({'component': identity, 'family': next(f['family'] for f in scope if identity in f['complete_component_ids']),
                        'original_feature_sha256': sha(canonical(features[identity])), 'original_geometry_sha256': sha(canonical(features[identity]['geometry'])),
                        'native_area_degrees2': g.area, 'archived_envelope_covers': envelope.covers(g), 'source_union_covers': source_union.covers(g),
                        'missing_archived_envelope_degrees2': missing_old.area, 'missing_source_degrees2': missing_source.area,
                        'missing_conditional_refresh_degrees2': missing_conditional.area,
                        'missing_archived_envelope_geometry': mapping(missing_old), 'missing_source_geometry': mapping(missing_source),
                        'missing_conditional_refresh_geometry': mapping(missing_conditional),
                        'historical_input_binding': 'unproven', 'repair_approval': 'open'})
    contact_comparisons = []
    diagnostic_by_id = unique(diagnostic, 'id')
    for f in current_contacts:
        actual = shape(f['geometry']); test = shape(diagnostic_by_id[f['id']]['geometry'])
        difference = actual.symmetric_difference(test)
        contact_comparisons.append({'id': f['id'], 'current_feature_sha256': sha(canonical(f)), 'current_parent_id': f['properties']['parent_id'], 'conditional_current_symmetric_difference_degrees2': difference.area, 'geometry': mapping(difference), 'equal_pointset': actual.equals(test)})
    descriptors = [{'id': r['id'], 'decoded_offset': offset, 'raw_bytes': len(raw), 'raw_sha256': sha(raw), 'canonical_row_sha256': sha(canonical(r)), 'geometry_sha256': sha(canonical(r['geometry']))} for r, raw, offset in selected]
    scientific = {'status': 'conditional-archived-envelope-mechanism-tests', 'components': results,
                  'current_contact_comparisons': contact_comparisons, 'original_validity': validity,
                  'source_crs': source.get('crs'), 'axis_order': 'longitude-latitude', 'coordinate_units': 'degrees', 'area_units': 'square degrees',
                  'conditional_old_parent_votes': votes_all, 'conditional_historical_adjustments': environment['adjustments'],
                  'recorded_adjustments_byte_equal': canonical(recorded_revision['adjustments']) == canonical(environment['adjustments']),
                  'recorded_adjustments_sha256': sha(canonical(recorded_revision['adjustments'])),
                  'conditional_adjustments_sha256': sha(canonical(environment['adjustments'])),
                  'conditional_remaining_degrees2': residual.area, 'executed_historical_method_sha256': sha(method_raw),
                  'executed_historical_ast_sha256': sha(ast.dump(method, include_attributes=True).encode()),
                  'executed_historical_vote_ast_sha256': sha(ast.dump(vote_method, include_attributes=True).encode()),
                  'method_attribution': 'Literal pinned refresh poly lines9-12 and serial cuts/buffers lines16-26; overlap voting retains old parent IDs; conditional diagnostic only',
                  'recorded_executed_branch': {'old_locations': 158, 'new_locations': 161, 'evidence': 'pinned semantic-report angola_source_revision plus all nine current source_revision_reason records'},
                  'immediate_pre_refresh_envelope_hash_binding': None,
                  'limits': ['Archived records are processed undated inactive references; exact immediate refresh input binding is unproven.', 'Conditional diagnostic does not prove actual historical loss or repair fitness.', 'Source year2018 claim/CRS84 longitude-latitude preserved; dated physical and administrative authority remain open in #411/#1046.', 'No geography mutation, political/ownership/water approval, global graph or whole-batch repair.', 'Historical MakeValid and buffers are literal conditional operator execution, not a newly applied repair; original validity is recorded separately.']}
    code_bytes = sum(code.consumed.values()); ordinary_bytes = sum(base.consumed.values())
    receipt = {'baseline_commit': plan['baseline_commit'], 'execution_commit': args.commit, 'ordinary_encoded_and_decoded_bytes': ordinary_bytes, 'code_bytes': code_bytes,
               'whole_private_stream': archive_receipt, 'combined_unique_input_bytes': ordinary_bytes + code_bytes + private['bytes'] + private['decoded_bytes'] + runtime_plan['total_bytes'],
               'ordinary_file_limit_bytes': CAP, 'complete_phase_limit_bytes': PHASE, 'descriptor_limit': 512,
               'ordinary_descriptor_count': len(by_path), 'actual_consumed_inputs': [dict(p, commit=plan['baseline_commit']) for p in plan['ordinary_inputs']],
               'actual_consumed_code': list(code.pins.values()), 'runtime': {'python': platform.python_version(), 'shapely': shapely.__version__, 'geos': shapely.geos_version_string, 'full_admitted_runtime': runtime_plan},
               'scope': {'families': 8, 'components': 10, 'contacts': 9, 'context_batches': 3, 'context_families': 173, 'context_components': 543}}
    payload = {'archive-records.jsonl.gz': immutable.deterministic_gzip(b'\n'.join(raw for r, raw, offset in selected) + b'\n'),
               'archive-index.json': canonical({'archive': archive_receipt, 'selected_records': descriptors, 'selected_roster_sha256': sha(canonical(sorted(r['id'] for r in old))), 'selected_descriptor_sha256': sha(canonical(descriptors))}),
               'contexts.json.gz': immutable.deterministic_gzip(canonical({'complete_families': list(family_rows.values()), 'complete_batches': batches, 'current_parent_chains': parent_chains})),
               'original-components.geojson': canonical({'type': 'FeatureCollection', 'features': [features[i] for i in sorted(features)]}),
               'current-contacts.geojson': canonical({'type': 'FeatureCollection', 'features': sorted(current_contacts, key=lambda f: f['id'])}),
               'conditional-refresh.geojson.gz': immutable.deterministic_gzip(canonical({'type': 'FeatureCollection', 'features': diagnostic})),
               'comparisons.json': canonical(scientific), 'input-receipt.json': canonical(receipt)}
    outputs_total = sum(len(v) + (len(gzip.decompress(v)) if k.endswith('.gz') else 0) for k, v in payload.items())
    if outputs_total > plan['resource_forecast']['max_output_bytes']:
        raise ValueError('Actual complete output exceeds conservative admission')
    if receipt['combined_unique_input_bytes'] + outputs_total + 4096 > PHASE:
        raise ValueError('Actual whole private/ordinary/output phase budget')
    if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss > plan['resource_forecast']['max_rss_bytes']:
        raise ValueError('Measured complete execution peak exceeds RAM budget')
    out.publish_bytes(payload)
    print(json.dumps({'status': scientific['status'], 'components': 10, 'ordinary_input_bytes': ordinary_bytes,
                      'private_input_bytes': private['bytes'] + private['decoded_bytes'], 'complete_phase_bytes': receipt['combined_unique_input_bytes'] + outputs_total + 4096,
                      'max_rss_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                      'products': sorted(payload)}))
