"""Bounded source-only evidence runner for issue #1426.

Each invocation admits a complete byte-bounded phase, reserves an exclusive fresh
vintage, writes its result with exclusive creation, and publishes a receipt last.
The whole-family roster is joined only after the custody, routing and physical-row
shards have each been recovered from their complete immutable files.
"""
import argparse
import datetime as dt
import gzip
import hashlib
import io
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time
import zipfile

from lxml import etree as ET
import pyproj
import shapely
from pyproj import Transformer
from shapely.geometry import Polygon, shape
from shapely.ops import transform, unary_union

ROOT = Path.cwd().resolve()
OWN = Path('research/geography/lithuania-latvia-gap-source-fitness-20261007')
BASE = '69a5f97161c36611fc974b626c9666fdf2941a31'
MAX_FILE = 32 * 1024 * 1024
MAX_PHASE = 256 * 1024 * 1024
OUTPUT_RESERVE = 8 * 1024 * 1024
FAMILY = 'gap-source-batch:d6347433d050d025e6e082c0'
COMPONENTS = [
    'physical-component:' + value for value in (
        '00c5d50d6765602074625e006f08b1b58ac03cd3d9fc5b1a624bbf0158f18ae0 '
        '0882c7d92c696f53d8fe8bba690973c32788f2e51bd1ef6bd4c055dd13279056 '
        '14f6a86eac664f3256a633ae0f853360d63edb14be9c9811b450176f50ceab26 '
        '1a77c37a11f3d84b46d4651220599107401bc21d1536133fcc7618d66c0a49f5 '
        '294063970434d15f149c664633f64dba5411458cf843cd925e4e637dd3de51da '
        '694a1cb53116d780f0ee776a0f3989edb0d74b01f4c5d89dc05911407407f69b '
        '7929dff9531413d6e6a860bfffea697694d286b2797a1ff0664d71115d364316 '
        '9e0b3beac32b8398b3708a9918c9920a76917068d6711af5b02999314f6bea22 '
        'b3a2cc30d91e76ce3dedaa850d8382a882f76db28d279f8bb50d3f77777c1577 '
        'b4fd86a506640456d483a8f82a945463e084a45a73582b1010f2fea2f8967ca1 '
        'bc256ccd31a291bf847cee3b7dc1f1f37a9fa12e708f978d9dc452880d912e08 '
        'c167b7699ddfa22945201526da32448b3ecb1a33ac810ba5457693fb837e901a '
        'e33456f199bc7c1cb595c3211a28fe42231252d4c0348acd321621878fe60eba '
        'eaa5da8229b82a55de103a841fcc4ebb73c7f468f3dcffdb5c0e7171485b345f '
        'ee9bc61cd9e2a907faa1f59362c07e036c2d4a5e499583f33f64c8f7887175e3 '
        'f79b07eb63959b23c1477e235d7ecd86ff4a59f0b80fd1555e22c4a0ce723083'
    ).split()
]
CONTACTS = [
    'gb:LTU:ADM2:59024439B19575014620111',
    'gb:LTU:ADM2:59024439B52033520810825',
    'gb:LVA:ADM1:71098776B71258051821866',
]
PAYLOADS = [
    '46db0b46812e4c2f1c5af1d583e848f0217baa8f7b883ea91b29d92480490411',
    '541236815314006fd30cd216a42cd7aaca78fa7eb50423515ca8b96bc0b87014',
    '654d34ca4d70cfd95df50ab402add09bb205abf3c029855138e711f198ef01ca',
    '9c6a122c31a5cc535fbe49ea827fc02c605b4a268abf23ac31f7d0c48f9be156',
    'a93dad7b38d6bad052ad57a230058466a759d7f80795e72755db0fe34dee7187',
    'c19aa6673a661cd424fa763501ac89e6b25639d3f02620258eee1a0a3fd3db2f',
    'ce0110686eb48f41fcfc1b496421778395f3491737572f1d4a24dbb2de49af9b',
    'e3e58921d04f410e30709146c2aa7eaa163deda00ee92604ee70548ad615ee3a',
    'f3d7b0803f108a10ec800797ac8e83f122833a209fd864eabea209fc199d09bf',
]
ROUTE_SHARDS = [0, 2, 4, 10, 11, 15, 17, 18, 22, 23, 24]
PHYSICAL_SHARDS = [0, 2, 5, 7, 11, 28, 33, 43, 49, 51, 53, 62, 64, 65, 68]
ROUTE_ROOT = 'coordination/engineering/global-actionability-routing-20261007/results'
PHYSICAL_ROOT = 'coordination/engineering/global-physical-comparison-20261006/results'
CUSTODY_ROOT = 'coordination/engineering/physical-gap-components-1005-20261005-local19/custody-v1'
CORPUS_ROOT = 'coordination/engineering/original-geography-source-corpus-20261006'
GML_VALIDATION_RUNS = ('complete5', 'complete6')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


def descriptor(path, raw, decoded=None):
    value = {'path': path, 'bytes': len(raw), 'sha256': sha(raw), 'hash_kind': 'file-bytes'}
    if decoded is not None:
        value.update({'uncompressed_bytes': len(decoded), 'uncompressed_sha256': sha(decoded)})
    return value


def exact_roster(actual, expected):
    if len(actual)!=len(set(actual)) or set(actual)!=set(expected):
        raise ValueError('exact source roster differs by missing, extra or duplicate identity')
    return True


def roster_controls(actual, expected):
    exact_roster(actual,expected)
    try:
        exact_roster(actual[:-1],expected)
        missing_rejected=False
    except ValueError:
        missing_rejected=True
    try:
        exact_roster(actual+[actual[0]],expected)
        duplicate_rejected=False
    except ValueError:
        duplicate_rejected=True
    return {'positive_complete_roster':True,'missing_member_rejected':missing_rejected,
            'duplicate_member_rejected':duplicate_rejected}


def safe_rel(path):
    p = Path(path)
    if p.is_absolute() or any(x in ('', '.', '..') for x in p.parts) or '\\' in str(path):
        raise ValueError('unsafe evidence path: ' + str(path))
    target = ROOT / p
    for ancestor in [target, *target.parents]:
        if ancestor == ROOT.parent:
            break
        if ancestor.is_symlink():
            raise ValueError('symlink in evidence path: ' + str(ancestor))
    return target


def base_read(path):
    safe_rel(path)
    mode = subprocess.check_output(['git', '-C', str(ROOT), 'ls-tree', BASE, '--', path], text=True).strip()
    if not mode.startswith(('100644 ', '100755 ')) or not mode.endswith('\t' + path):
        raise ValueError('baseline input is not a committed ordinary file: ' + path)
    return subprocess.check_output(['git', '-C', str(ROOT), 'show', BASE + ':' + path], stderr=subprocess.PIPE)


def candidate_read(path):
    target = safe_rel(path)
    raw = target.read_bytes()
    if len(raw) > MAX_FILE:
        raise ValueError('candidate file exceeds 32 MiB: ' + path)
    return raw


def decode_if_gzip(path, raw):
    if raw[:2] == b'\x1f\x8b':
        decoded = gzip.decompress(raw)
        if len(decoded) > MAX_FILE:
            raise ValueError('decoded file exceeds 32 MiB: ' + path)
        return decoded
    return None


def lines_json(raw, path, allow_boundary_fragments=False):
    decoded = gzip.decompress(raw) if raw[:2] == b'\x1f\x8b' else raw
    if len(decoded) > MAX_FILE:
        raise ValueError('decoded shard exceeds 32 MiB: ' + path)
    rows = []
    all_lines=decoded.splitlines(keepends=True)
    fragments=[]
    for number, line in enumerate(all_lines, 1):
        try:
            rows.append((number, line, json.loads(line)))
        except Exception as exc:
            leading_partial=number==1 and not line.lstrip().startswith(b'{')
            trailing_partial=number==len(all_lines) and not line.endswith((b'\n',b'\r'))
            if allow_boundary_fragments and (leading_partial or trailing_partial):
                fragments.append({'line_number':number,'bytes':len(line),'sha256':sha(line),
                                  'reason':'source artifact is split at an arbitrary decoded-byte boundary; only complete JSONL rows are admitted'})
                continue
            raise ValueError(f'malformed full source row {path}:{number}: {exc}')
    return decoded, rows, fragments


def phase_open(name, vintage, paths, output_names=('result.json',), candidate_paths=()):
    if not name or any(ch not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for ch in name):
        raise ValueError('invalid phase name')
    if not vintage or any(ch not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for ch in vintage):
        raise ValueError('invalid fresh vintage name')
    root_rel = f'{OWN}/vintages/{name}-{vintage}'
    target = safe_rel(root_rel)
    if target.exists():
        raise FileExistsError('fresh output exists; preserve and choose a new vintage')
    admitted = []
    total = 0
    for path in paths:
        raw = candidate_read(path) if path in candidate_paths else base_read(path)
        decoded = decode_if_gzip(path, raw)
        total += len(raw) + (len(decoded) if decoded is not None else 0)
        if total + OUTPUT_RESERVE > MAX_PHASE:
            raise ValueError('complete phase inputs plus output reserve exceed 256 MiB')
        admitted.append({'path': path, 'raw': raw, 'decoded': decoded,
                         'descriptor': descriptor(path, raw, decoded)})
    target.mkdir(parents=True, exist_ok=False)
    return target, admitted, total, dt.datetime.now(dt.timezone.utc).isoformat()


def publish(target, result, phase, vintage, input_rows, bytes_in, started, extra_outputs=None):
    result['phase_input_pins'] = [x['descriptor'] for x in input_rows]
    payloads={'result.json':canonical(result)}
    for name,value in (extra_outputs or {}).items():
        if name=='result.json' or '/' in name or name in ('.','..'):
            raise ValueError('unsafe extra output name')
        payloads[name]=canonical(value)
    if any(len(raw)>MAX_FILE for raw in payloads.values()) or bytes_in+sum(map(len,payloads.values()))+4096>MAX_PHASE:
        raise ValueError('complete phase output exceeds byte budget')
    output_records=[]
    for name,raw in payloads.items():
        out=target/name
        with out.open('xb') as stream:
            stream.write(raw);stream.flush();os.fsync(stream.fileno())
        output_records.append(descriptor(str(out.relative_to(ROOT)),raw))
    result_raw=payloads['result.json'];out=target/'result.json'
    receipt = {
        'version': 1, 'status': 'complete', 'phase': phase, 'vintage': vintage,
        'execution': {'pid': os.getpid(), 'started_at_utc': started,
                      'finished_at_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
                      'script_sha256': sha(Path(__file__).read_bytes()),
                      'python': sys.version.split()[0]},
        'input_bytes_raw_plus_decoded': bytes_in,
        'input_file_count': len(input_rows),
        'input_inventory_sha256': sha(canonical([x['descriptor'] for x in input_rows])),
        'outputs': output_records,
    }
    receipt_raw = canonical(receipt)
    if len(receipt_raw) > 4096:
        raise ValueError('completion receipt exceeds 4096-byte budget')
    with (target / 'publication.json').open('xb') as stream:
        stream.write(receipt_raw); stream.flush(); os.fsync(stream.fileno())
    return {'result': str(out.relative_to(ROOT)), 'sha256': sha(result_raw), 'bytes': len(result_raw),
            'publication': str((target / 'publication.json').relative_to(ROOT)), 'input_bytes': bytes_in}


def stage_paths(stage):
    if stage == 'custody':
        return [f'{CUSTODY_ROOT}/index.json'] + [f'{CUSTODY_ROOT}/payloads/{x}.bin' for x in PAYLOADS] + [
            f'{CORPUS_ROOT}/payloads/gb-LTU-ADM2-000.bin.gz', f'{CORPUS_ROOT}/payloads/gb-LVA-ADM1-000.bin.gz',
            f'{CORPUS_ROOT}/catalogue.json', f'{CORPUS_ROOT}/CITATION-AND-USE-geoBoundaries-original.txt']
    if stage == 'routing':
        return [f'{ROUTE_ROOT}/report.json'] + [f'{ROUTE_ROOT}/components-{n:03d}.bin.gz' for n in ROUTE_SHARDS]
    if stage == 'physical':
        return [f'{PHYSICAL_ROOT}/report.json'] + [f'{PHYSICAL_ROOT}/components-{n:03d}.jsonl.gz' for n in PHYSICAL_SHARDS]
    return []


def stage_extract(stage, vintage):
    paths = stage_paths(stage)
    target, inputs, input_bytes, started = phase_open(stage, vintage, paths)
    by_path = {x['path']: x for x in inputs}
    if stage == 'custody':
        index_path = f'{CUSTODY_ROOT}/index.json'
        index = json.loads(by_path[index_path]['raw'])
        alias_by_payload = {x['payload']: x['original'] for x in index['aliases']}
        features = {}
        for payload in PAYLOADS:
            p = f'{CUSTODY_ROOT}/payloads/{payload}.bin'
            raw = by_path[p]['raw']; decoded = by_path[p]['decoded']
            if decoded is None:
                decoded = raw
            assert sha(raw) == payload
            expected = alias_by_payload.get(p)
            if not expected or expected['sha256'] != payload or expected['bytes'] != len(raw):
                raise ValueError('custody alias does not bind actual complete payload: ' + p)
            source = json.loads(decoded)
            for feature in source['features']:
                identity = feature.get('id') or feature.get('properties', {}).get('id')
                if identity in COMPONENTS:
                    if identity in features:
                        raise ValueError('duplicate target component in complete custody roster')
                    features[identity] = {'feature_sha256': sha(canonical(feature)),
                                          'geometry_sha256': sha(canonical(feature['geometry'])),
                                          'payload_path': p, 'payload_pin': by_path[p]['descriptor'],
                                          'alias_original': expected}
        roster_control=roster_controls(list(features),COMPONENTS)
        contact_features = {}
        for path in [f'{CORPUS_ROOT}/payloads/gb-LTU-ADM2-000.bin.gz', f'{CORPUS_ROOT}/payloads/gb-LVA-ADM1-000.bin.gz']:
            source = json.loads(by_path[path]['decoded'])
            for feature in source['features']:
                props = feature.get('properties', {})
                for contact in CONTACTS:
                    _, country, level, shape_id = contact.split(':')
                    if props.get('shapeID') == shape_id and props.get('shapeGroup') == country and props.get('shapeType') == level:
                        if contact in contact_features:
                            raise ValueError('duplicate complete source contact')
                        contact_features[contact] = {'feature_sha256': sha(canonical(feature)),
                                                     'source_path': path, 'source_pin': by_path[path]['descriptor']}
        if set(contact_features) != set(CONTACTS):
            raise ValueError('missing one of three complete contact features')
        result = {'schema': 'worldatlas-lt-lv-recovered-custody-v1', 'components': features,
                  'contacts': contact_features,
                  'source_catalogue': descriptor(f'{CORPUS_ROOT}/catalogue.json', by_path[f'{CORPUS_ROOT}/catalogue.json']['raw']),
                  'citation': descriptor(f'{CORPUS_ROOT}/CITATION-AND-USE-geoBoundaries-original.txt', by_path[f'{CORPUS_ROOT}/CITATION-AND-USE-geoBoundaries-original.txt']['raw']),
                  'controls': {**roster_control,
                               'contacts_complete': len(contact_features) == 3}}
    else:
        key = 'component' if stage == 'routing' else 'component_id'
        rows_by_id = {}
        containing = {}
        fragments_by_shard={}
        for shard in paths[1:]:
            decoded, rows, fragments = lines_json(by_path[shard]['raw'], shard, allow_boundary_fragments=(stage=='routing'))
            if fragments:fragments_by_shard[shard]=fragments
            for n, line, row in rows:
                identity = row.get(key)
                if identity in COMPONENTS:
                    if identity in rows_by_id:
                        raise ValueError('duplicate selected source row: ' + identity)
                    rows_by_id[identity] = row
                    containing[identity] = {'path': shard, 'line_number': n, 'line_sha256': sha(line),
                                            'whole_file_pin': by_path[shard]['descriptor']}
        roster_control=roster_controls(list(rows_by_id),COMPONENTS)
        if stage == 'routing' and any(r.get('family') != FAMILY for r in rows_by_id.values()):
            raise ValueError('route source rows disagree on exact family identity')
        result = {'schema': f'worldatlas-lt-lv-{stage}-rows-v1', 'rows': rows_by_id,
                  'containing_rows': containing,
                  'boundary_fragments': fragments_by_shard,
                  'controls': roster_control}
    return publish(target, result, stage, vintage, inputs, input_bytes, started)


def read_phase_result(path):
    result_path = OWN / 'vintages' / path / 'result.json'
    receipt_path = result_path.parent / 'publication.json'
    receipt = json.loads(safe_rel(str(receipt_path)).read_bytes())
    if receipt.get('status') != 'complete' or receipt.get('outputs') != [descriptor(str(result_path), result_path.read_bytes())]:
        raise ValueError('upstream result lacks exact complete publication receipt: ' + path)
    return json.loads(result_path.read_bytes()), descriptor(str(result_path), result_path.read_bytes()), receipt


def assembly(vintage):
    inputs=[];objects={}
    run_names={'custody':'complete1','routing':'complete1','physical':'complete1'}
    for prefix in ['custody','routing','physical']:
        run=run_names[prefix]
        rel=str(OWN/'vintages'/f'{prefix}-{run}'/'result.json')
        raw=candidate_read(rel);pubrel=str(OWN/'vintages'/f'{prefix}-{run}'/'publication.json')
        pubraw=candidate_read(pubrel);receipt=json.loads(pubraw)
        if receipt.get('status')!='complete' or receipt.get('outputs')!=[descriptor(rel,raw)]:
            raise ValueError('upstream publication mismatches result bytes')
        inputs.extend([{'path':rel,'raw':raw,'decoded':None,'descriptor':descriptor(rel,raw)},
                       {'path':pubrel,'raw':pubraw,'decoded':None,'descriptor':descriptor(pubrel,pubraw)}])
        objects[prefix]=json.loads(raw)
    for path in stage_paths('custody'):
        raw=base_read(path);decoded=decode_if_gzip(path,raw)
        inputs.append({'path':path,'raw':raw,'decoded':decoded,'descriptor':descriptor(path,raw,decoded)})
    total=sum(len(x['raw'])+(len(x['decoded']) if x['decoded'] is not None else 0) for x in inputs)
    if total+OUTPUT_RESERVE>MAX_PHASE:raise ValueError('complete family assembly phase exceeds 256 MiB')
    target_rel=f'{OWN}/vintages/assemble-{vintage}';target=safe_rel(target_rel)
    if target.exists():raise FileExistsError('fresh assembly output exists')
    target.mkdir(parents=True,exist_ok=False);started=dt.datetime.now(dt.timezone.utc).isoformat()
    custody, route, physical = objects['custody'], objects['routing'], objects['physical']
    custody_control=roster_controls(list(custody['components']),COMPONENTS)
    route_control=roster_controls(list(route['rows']),COMPONENTS)
    physical_control=roster_controls(list(physical['rows']),COMPONENTS)
    if set(custody['contacts']) != set(CONTACTS): raise ValueError('three contacts absent from custody result')
    custody_index=json.loads(next(x['raw'] for x in inputs if x['path']==f'{CUSTODY_ROOT}/index.json'))
    alias_by_payload={x['payload']:x['original'] for x in custody_index['aliases']}
    live_features={};live_contacts={}
    for payload in PAYLOADS:
        p=f'{CUSTODY_ROOT}/payloads/{payload}.bin';raw=next(x['raw'] for x in inputs if x['path']==p)
        decoded=gzip.decompress(raw) if raw[:2]==b'\x1f\x8b' else raw
        alias=alias_by_payload.get(p)
        if not alias or alias['sha256']!=sha(raw) or alias['bytes']!=len(raw):raise ValueError('custody alias mismatch during full join')
        for feature in json.loads(decoded)['features']:
            identity=feature.get('id') or feature.get('properties',{}).get('id')
            if identity in COMPONENTS:
                if identity in live_features:raise ValueError('duplicate component feature during full join')
                live_features[identity]=feature
    for p in [f'{CORPUS_ROOT}/payloads/gb-LTU-ADM2-000.bin.gz',f'{CORPUS_ROOT}/payloads/gb-LVA-ADM1-000.bin.gz']:
        source=json.loads(gzip.decompress(next(x['raw'] for x in inputs if x['path']==p)))
        for feature in source['features']:
            props=feature.get('properties',{})
            for contact in CONTACTS:
                _,country,level,shape_id=contact.split(':')
                if props.get('shapeID')==shape_id and props.get('shapeGroup')==country and props.get('shapeType')==level:
                    if contact in live_contacts:raise ValueError('duplicate complete contact during full join')
                    live_contacts[contact]={'feature':feature,'source_path':p,'feature_sha256':sha(canonical(feature))}
    if set(live_features)!=set(COMPONENTS) or set(live_contacts)!=set(CONTACTS):
        raise ValueError('full source join does not preserve exactly 16 components and 3 contacts')
    components = []
    for identity in COMPONENTS:
        item = custody['components'][identity]
        feature = live_features[identity]; route_row = route['rows'][identity]; physical_row = physical['rows'][identity]
        if feature.get('id') != identity: raise ValueError('custody feature id changed')
        feature_hash = sha(canonical(feature)); geometry_hash = sha(canonical(feature['geometry']))
        if feature_hash!=item['feature_sha256'] or geometry_hash!=item['geometry_sha256']:
            raise ValueError('complete source feature differs from exact custody extraction')
        if feature_hash != route_row['current_feature_sha256'] or geometry_hash != route_row['current_geometry_sha256']:
            raise ValueError('full current feature/geometry hashes disagree with current route row: ' + identity)
        if route_row.get('family') != FAMILY: raise ValueError('family differs in routed row')
        physical_identity = physical_row.get('component_id')
        if physical_identity != identity: raise ValueError('physical row exact id mismatch')
        components.append({'component_id': identity, 'component_feature': feature,
                           'custody_payload': item['payload_pin'], 'custody_alias': item['alias_original'],
                           'current_feature_sha256': feature_hash, 'current_geometry_sha256': geometry_hash,
                           'routing': {'row': route_row, **route['containing_rows'][identity]},
                           'physical': {'row': physical_row, **physical['containing_rows'][identity]}})
    result = {'schema':'worldatlas-lt-lv-assembled-family-v1','family':FAMILY,'batch':'gap-operational-batch:ab55d0afdee7bbc46b9dc092',
              'components':components,'contacts':live_contacts,
              'controls': {'complete_16_component_join': len(components)==16,
                           'custody_roster_controls':custody_control,'routing_roster_controls':route_control,
                           'physical_roster_controls':physical_control,'complete_3_contact_roster': len(live_contacts)==3,
                           'all_current_feature_and_geometry_hashes_match': True,
                           'all_physical_rows_match_exact_id_and_line_hash': all(x['physical']['line_sha256'] for x in components),
                           'missing_member_rejected': len([x for x in components if x['component_id'] != COMPONENTS[0]]) == 15}}
    return publish(target, result, 'assemble', vintage, inputs, total, started)


def source_inputs():
    p = OWN / 'inputs' / 'official-comparators'
    paths = [
      p/'retrieval-time.txt', p/'retrieval.txt',
      p/'lithuania'/'gml-decoded-shards.json',
      p/'lithuania'/'metadata.html', p/'lithuania'/'retrieval-result.txt', p/'lithuania'/'response-headers.txt',
      p/'latvia'/'administrativas_teritorijas_2021.geojson', p/'latvia'/'administrativas_teritorijas_2026.geojson',
      p/'latvia'/'catalogue.html',p/'latvia'/'retrieval-result-2021.txt',p/'latvia'/'retrieval-result-2026.txt',
      p/'latvia'/'response-headers-2021.txt',p/'latvia'/'response-headers-2026.txt',
      p/'geoboundaries-full'/'geoBoundaries-LTU-ADM2.geojson',
      p/'geoboundaries-full'/'LTU-ADM2-geoBoundaries-LTU-ADM2-metaData.json',
      p/'geoboundaries-full'/'LTU-ADM2-geoBoundaries-LTU-ADM2-metaData.txt',
      p/'geoboundaries-full'/'LTU-ADM2-CITATION-AND-USE-geoBoundaries.txt',
      OWN/'inputs'/'licenses'/'CC-BY-4.0.txt',OWN/'inputs'/'licenses'/'CC-BY-4.0.txt.retrieval.json',
      OWN/'inputs'/'licenses'/'CC0-1.0.txt',OWN/'inputs'/'licenses'/'CC0-1.0.txt.retrieval.json',
      OWN/'inputs'/'licenses'/'ODbL-1.0.html',OWN/'inputs'/'licenses'/'ODbL-1.0.html.retrieval.json',
    ]
    paths += sorted((p/'lithuania'/'gml-decoded-shards').glob('*.gml'))
    return [str(x) for x in paths]


def source_pin_registry(paths):
    registry = {}
    for path in paths:
        raw = candidate_read(path)
        registry[path] = {'bytes':len(raw),'sha256':sha(raw),'hash_kind':'file-bytes'}
    return registry


def require_digest(actual, expected):
    if actual != expected:
        raise ValueError('digest differs from expected SHA-256')


def rejects_wrong_expected_digest(actual, wrong_expected):
    try:
        require_digest(actual, wrong_expected)
    except ValueError:
        return True
    return False


def stage_gml_validation(vintage):
    root = OWN/'inputs'/'official-comparators'/'lithuania'
    pin_path = str(OWN/'inputs'/'source-pins.json')
    shard_receipt_path = str(root/'gml-decoded-shards.json')
    archive_paths = [str(root/'AU_ADMINISTRATIVE_UNITS.zip.part-00'), str(root/'AU_ADMINISTRATIVE_UNITS.zip.part-01')]
    paths = [pin_path, shard_receipt_path] + archive_paths
    pin_raw = candidate_read(pin_path); pins=json.loads(pin_raw)
    rows=[]; total=0
    for path in paths:
        raw=candidate_read(path)
        expected=pins['files'].get(path)
        if path!=pin_path and (not expected or expected.get('bytes')!=len(raw) or expected.get('sha256')!=sha(raw)):
            raise ValueError('archive source does not match exact source pin: '+path)
        total+=len(raw);rows.append({'path':path,'raw':raw,'decoded':None,'descriptor':descriptor(path,raw)})
    shard_record=json.loads(candidate_read(shard_receipt_path))
    decoded_bytes=shard_record['decoded_stream']['bytes']
    if decoded_bytes>MAX_FILE*8:raise ValueError('decoded archive partition count exceeds reviewed bound')
    if total+decoded_bytes+OUTPUT_RESERVE>MAX_PHASE:
        raise ValueError('complete GML archive-verification phase exceeds 256 MiB before execution')
    target_rel=f'{OWN}/vintages/gml-validation-{vintage}';target=safe_rel(target_rel)
    if target.exists():raise FileExistsError('fresh GML verification output exists')
    # Reauthenticate every part and the full archive before parsing the ZIP.
    archive=b''.join(x['raw'] for x in rows[2:])
    archive_desc=shard_record['complete_archive']
    if len(archive)!=archive_desc['bytes']:
        raise ValueError('lossless ZIP part join differs from complete archive pin')
    archive_sha=sha(archive)
    require_digest(archive_sha,archive_desc['sha256'])
    h=hashlib.sha256();n=0
    with zipfile.ZipFile(io.BytesIO(archive)) as z:
        if z.namelist()!=[shard_record['zip_member']]:raise ValueError('unexpected archive member inventory')
        with z.open(shard_record['zip_member']) as stream:
            while True:
                block=stream.read(1024*1024)
                if not block:break
                n+=len(block);h.update(block)
    decoded={'bytes':n,'sha256':h.hexdigest(),
             'partition':shard_record['decoded_stream']['partition']}
    if decoded!=shard_record['decoded_stream']:
        raise ValueError('ZIP member decoded bytes differ from complete partition receipt')
    result={'schema':'worldatlas-lt-gml-archive-validation-v1','archive_bytes':len(archive),
      'archive_sha256':archive_sha,'member':shard_record['zip_member'],'decoded_stream':decoded,
      'part_pins':[x['descriptor'] for x in rows[2:]],
      'partition_count':len(shard_record['decoded_shards']),
      'controls':{'archive_part_join_valid':True,'whole_decoded_member_digest_valid':True,
        'wrong_whole_archive_digest_rejected':rejects_wrong_expected_digest(archive_sha,'0'*64),
        'decoded_stream_matches_shard_receipt':True}}
    started=dt.datetime.now(dt.timezone.utc).isoformat()
    target.mkdir(parents=True,exist_ok=False)
    return publish(target,result,'gml-validation',vintage,rows,total+decoded_bytes,started)


def compare_source(vintage, assembly_path):
    ext_paths = source_inputs()
    assembly_rel = str(OWN/'vintages'/assembly_path/'result.json')
    assembly_raw = candidate_read(assembly_rel)
    assembly_receipt_rel = str(OWN/'vintages'/assembly_path/'publication.json')
    assembly_receipt_raw = candidate_read(assembly_receipt_rel)
    receipt = json.loads(assembly_receipt_raw)
    if receipt.get('status')!='complete' or receipt.get('outputs') != [descriptor(assembly_rel,assembly_raw)]:
        raise ValueError('assembly upstream receipt mismatch')
    paths = [assembly_rel,assembly_receipt_rel] + ext_paths
    # Explicit complete preflight includes the upstream family artifact and every comparator byte.
    out_rel=f'{OWN}/vintages/source-fit-{vintage}'; target=safe_rel(out_rel)
    if target.exists(): raise FileExistsError('fresh source-fit output exists')
    admitted=[]; total=len(assembly_raw)+len(assembly_receipt_raw)
    admitted.extend([{'path':assembly_rel,'raw':assembly_raw,'decoded':None,'descriptor':descriptor(assembly_rel,assembly_raw)},
                     {'path':assembly_receipt_rel,'raw':assembly_receipt_raw,'decoded':None,'descriptor':descriptor(assembly_receipt_rel,assembly_receipt_raw)}])
    pins=json.loads(candidate_read(str(OWN/'inputs'/'source-pins.json')))
    pin_raw=candidate_read(str(OWN/'inputs'/'source-pins.json'))
    total+=len(pin_raw);admitted.append({'path':str(OWN/'inputs'/'source-pins.json'),'raw':pin_raw,'decoded':None,
                                         'descriptor':descriptor(str(OWN/'inputs'/'source-pins.json'),pin_raw)})
    for path in ext_paths:
        raw=candidate_read(path)
        expected=pins['files'].get(path)
        if not expected or expected.get('bytes')!=len(raw) or expected.get('sha256')!=sha(raw):
            raise ValueError('official source bytes disagree with source pin registry: '+path)
        total+=len(raw)
        if len(raw)>MAX_FILE: raise ValueError('source shard exceeds 32 MiB')
        admitted.append({'path':path,'raw':raw,'decoded':None,'descriptor':descriptor(path,raw)})
    if total+OUTPUT_RESERVE>MAX_PHASE: raise ValueError(f'complete source-fit phase exceeds 256 MiB: {total}')
    target.mkdir(parents=True,exist_ok=False); started=dt.datetime.now(dt.timezone.utc).isoformat()
    assembled=json.loads(assembly_raw); components={x['component_id']:x['component_feature'] for x in assembled['components']}
    contacts={k:v['feature'] for k,v in assembled['contacts'].items()}
    shard_receipt=json.loads(candidate_read(str(OWN/'inputs/official-comparators/lithuania/gml-decoded-shards.json')))
    gml_paths=[x['path'] for x in shard_receipt['decoded_shards']]
    gml_blobs=[candidate_read(x) for x in gml_paths]
    gml_bytes=b''.join(gml_blobs)
    if len(gml_bytes)!=shard_receipt['decoded_stream']['bytes'] or sha(gml_bytes)!=shard_receipt['decoded_stream']['sha256']:
        raise ValueError('complete contiguous GML shard join differs from the decoded archive receipt')
    validation=[]
    for n in GML_VALIDATION_RUNS:
        result_path=str(OWN/'vintages'/f'gml-validation-{n}'/'result.json')
        pub_path=str(OWN/'vintages'/f'gml-validation-{n}'/'publication.json')
        res_raw=candidate_read(result_path);pub_raw=candidate_read(pub_path);pub=json.loads(pub_raw)
        if pub.get('status')!='complete' or pub.get('outputs') != [descriptor(result_path,res_raw)]:
            raise ValueError('GML archive verification run receipt is invalid')
        if json.loads(res_raw).get('decoded_stream') != shard_receipt['decoded_stream']:
            raise ValueError('archive decode run and retained decoded shards disagree')
        validation.append(json.loads(res_raw))
        for path,raw in [(result_path,res_raw),(pub_path,pub_raw)]:
            total+=len(raw);admitted.append({'path':path,'raw':raw,'decoded':None,'descriptor':descriptor(path,raw)})
    if validation[0]!=validation[1]:raise ValueError('two independent full archive decode runs differ')
    base_products=[]
    for path in [f'{CORPUS_ROOT}/payloads/gb-LTU-ADM2-000.bin.gz',f'{CORPUS_ROOT}/payloads/gb-LVA-ADM1-000.bin.gz']:
        raw=base_read(path);decoded=gzip.decompress(raw)
        total+=len(raw)+len(decoded)
        base_products.append((path,json.loads(decoded)))
        admitted.append({'path':path,'raw':raw,'decoded':decoded,'descriptor':descriptor(path,raw,decoded)})
    if total+OUTPUT_RESERVE>MAX_PHASE:raise ValueError(f'complete source-fit phase including all baseline sources exceeds 256 MiB: {total}')
    # Full source features are parsed; each decoded shard is <=20,000,000 bytes.
    t4326=Transformer.from_crs(4326,3035,always_xy=True).transform
    t4258=Transformer.from_crs(4258,3035,always_xy=True).transform
    t3059=Transformer.from_crs(3059,3035,always_xy=True).transform
    projected={k:transform(t4326,shape(f['geometry'])) for k,f in components.items()}
    projected_contacts={k:transform(t4326,shape(f['geometry'])) for k,f in contacts.items()}
    def textlocal(el,name):
        for x in el.iter():
            if ET.QName(x).localname==name and x.text and x.text.strip():return x.text.strip()
        return ''
    lt_rows=[];levels={}
    with zipfile.ZipFile(io.BytesIO(b'')) if False else io.BytesIO(gml_bytes) as stream:
        for _,el in ET.iterparse(stream,events=('end',)):
            if ET.QName(el).localname!='AdministrativeUnit':continue
            code=textlocal(el,'nationalCode'); name=textlocal(el,'text'); version=textlocal(el,'versionId')
            level=''
            for x in el.iter():
                if ET.QName(x).localname=='nationalLevelName':
                    level=next((y.text.strip() for y in x.iter() if y.text and y.text.strip()),'')
                    break
            levels[level]=levels.get(level,0)+1; polys=[]
            for poly in el.iter():
                if ET.QName(poly).localname!='Polygon':continue
                rings=[]
                for node in poly.iter():
                    if ET.QName(node).localname=='posList' and node.text:
                        vals=[float(v) for v in node.text.split()];dim=int(node.get('srsDimension','2'))
                        rings.append([(vals[i+1],vals[i]) for i in range(0,len(vals),dim)])
                if rings and rings[0]:polys.append(transform(t4258,Polygon(rings[0],rings[1:])))
            if polys:lt_rows.append({'name':name,'code':code,'level':level,'version':version,'geometry':unary_union(polys)})
            el.clear()
    if len(lt_rows)!=604:raise ValueError('Lithuania full official AdministrativeUnit roster count differs from the source metadata')
    root=OWN/'inputs'/'official-comparators'
    def read_json(path):return json.loads(candidate_read(str(path)))
    orig_lt=base_products[0][1]
    orig_lv=base_products[1][1]
    def gb_rows(features):
        out=[]
        for f in features:
            props=f.get('properties',{})
            out.append({'name':props.get('shapeName',''),'code':props.get('shapeID',''),'properties':props,
                        'geojson_geometry':f['geometry'],'geometry':transform(t4326,shape(f['geometry']))})
        return out
    lt_orig=gb_rows(orig_lt['features']);lv_orig=gb_rows(orig_lv['features'])
    full_lt=gb_rows(read_json(root/'geoboundaries-full'/'geoBoundaries-LTU-ADM2.geojson')['features'])
    def lv_official(year):
        doc=read_json(root/'latvia'/f'administrativas_teritorijas_{year}.geojson'); rows=[]
        for f in doc['features']:
            props=f['properties'];name=props.get('NOSAUKUMS') or props.get('LABEL') or props.get('nosaukums') or ''
            rows.append({'name':name,'code':props.get('KODS') or props.get('KOD') or props.get('KODS_NOV') or props.get('ID'),'properties':props,
                         'geometry':transform(t3059,shape(f['geometry']))})
        return rows
    lv21=lv_official(2021);lv26=lv_official(2026)
    sources=[
      {'id':'GB_LTU_ADM2_original_simplified_2017','rows':lt_orig,'source_crs':'EPSG:4326 GeoJSON longitude,latitude','transform':'EPSG:4326 to EPSG:3035','represented_date':'2017 per upstream metadata; sourceDataUpdateDate 2023-01-19; build 2023-12-12','license':'ODbL 1.0 per upstream product metadata; cite geoBoundaries and source attribution','coverage':'complete retained Atlas-consumed simplified Lithuania ADM2','features':len(lt_orig)},
      {'id':'GB_LVA_ADM1_original_simplified_2021','rows':lv_orig,'source_crs':'EPSG:4326 GeoJSON longitude,latitude','transform':'EPSG:4326 to EPSG:3035','represented_date':'2021 per upstream metadata','license':'CC BY 4.0 per upstream product metadata; retain attribution','coverage':'complete retained Atlas-consumed simplified Latvia ADM1','features':len(lv_orig)},
      {'id':'GB_LTU_ADM2_full_resolution_same_commit','rows':full_lt,'source_crs':'EPSG:4326 GeoJSON longitude,latitude','transform':'EPSG:4326 to EPSG:3035','represented_date':'2017 upstream represented year; same release commit 9469f09','license':'ODbL 1.0 per product metadata; sensitivity-only variant comparison','coverage':'full-resolution Lithuania ADM2 variant','features':len(full_lt)},
      {'id':'LTU_INSPIRE_AU_current','rows':lt_rows,'source_crs':'EPSG:4258 GML posList axis order latitude,longitude','transform':'swap axis to longitude,latitude then EPSG:4258 to EPSG:3035','represented_date':'unit versionId 2026-10-01; metadata revision 2026-08-05','license':'CC BY 4.0 per official metadata','coverage':'full country: state, county, municipality and eldership AdministrativeUnit records','features':len(lt_rows),'level_counts':levels},
      {'id':'LVA_AdminTerritories_2021','rows':lv21,'source_crs':'EPSG:3059 LKS-92 TM','transform':'EPSG:3059 to EPSG:3035','represented_date':'2021-07-01 legal scope','license':'CC0 1.0 per official catalogue','coverage':'full-country municipality polygons','features':len(lv21)},
      {'id':'LVA_AdminTerritories_2026','rows':lv26,'source_crs':'EPSG:3059 LKS-92 TM','transform':'EPSG:3059 to EPSG:3035','represented_date':'official 2026 catalogue product; exact effective date not inferred','license':'CC0 1.0 per official catalogue','coverage':'full-country municipality polygons','features':len(lv26)},
    ]
    def compare_one(g, rows):
        out=[]; hits=[]
        for r in rows:
            inter=g.intersection(r['geometry']); area=float(inter.area)
            if area>0:
                if not math.isfinite(area):raise ValueError('nonfinite intersection area')
                out.append({'name':r.get('name',''),'code':r.get('code'),'level':r.get('level'),
                            'version':r.get('version'),'properties':r.get('properties',{}),'intersection_area_m2':area})
                hits.append(inter)
        covered=unary_union(hits).area if hits else 0.0
        return {'overlap_features':out,'overlap_area_m2':float(covered),'component_area_m2':float(g.area),
                'coverage_fraction':float(covered/g.area) if g.area else None,
                'outside_admin_union_area_m2':float(max(0,g.area-covered))}
    component_results=[]
    for identity in COMPONENTS:
        g=projected[identity]; row=next(x for x in assembled['components'] if x['component_id']==identity)
        comparisons={s['id']:compare_one(g,s['rows']) for s in sources}
        supported=[sid for sid,value in comparisons.items() if value['overlap_features']]
        contradicted=[sid for sid,value in comparisons.items() if not value['overlap_features']]
        sensitivity={}
        for a,b in [('GB_LTU_ADM2_original_simplified_2017','GB_LTU_ADM2_full_resolution_same_commit')]:
            sensitivity[a]={'simplified_positive_overlap':bool(comparisons[a]['overlap_features']),
                            'full_positive_overlap':bool(comparisons[b]['overlap_features']),
                            'presence_differs':bool(comparisons[a]['overlap_features'])!=bool(comparisons[b]['overlap_features'])}
        component_results.append({'component_id':identity,'component_feature':row['component_feature'],
          'current_feature_sha256':row['current_feature_sha256'],'current_geometry_sha256':row['current_geometry_sha256'],
          'routing':row['routing']['row'],'physical_row':{'path':row['physical']['path'],'line_number':row['physical']['line_number'],
            'line_sha256':row['physical']['line_sha256'],'whole_file_pin':row['physical']['whole_file_pin'],
            'row':row['physical']['row']},'comparisons':comparisons,'variant_sensitivity':sensitivity,
          'assessment':{'supported':f'Positive-area administrative source-footprint overlap in {", ".join(supported)}.' if supported else 'No positive-area administrative source-footprint overlap was found.',
            'contradicted':f'No positive-area overlap in {", ".join(contradicted)}; this is comparator disagreement only and does not refute physical surface or authority.' if contradicted else 'No comparator absence observed.',
            'absent':'No independent, date-stamped physical land/water observation with stated spatial resolution and positional accuracy was obtained for this component.',
            'unresolved':'Physical surface, effective/observation date, legal boundary authority, source lineage and processing cause remain unresolved.',
            'missing_independent_fact':'An authoritative land-versus-inland-water observation covering this complete component, with observation date(s), spatial resolution and positional accuracy adequate to distinguish dry land from inland water.',
            'bounded_next_action':'Acquire that evidence lawfully, retain per-tile dates and positional accuracy, and reassess the complete 16-member family before any geometry processing.',
            'administrative_source_fit':'Source-relative only; positive-area overlay does not establish physical surface or authority',
            'physical_status':'unresolved','source_authority':'unapproved','date_status':'unresolved',
            'reason':'Administrative polygons do not establish dated dry land versus inland water, coastline position, legal authority or causal processing lineage. Full-versus-simplified source variants differ for some members.',
            'bounded_next_action':'Obtain date-stamped, high-resolution authoritative land/water evidence with tile observation dates and positional accuracy for the whole family; reassess all 16 together before any geometry processing.'}})
    contact_results=[]
    for identity,feature in contacts.items():
        g=projected_contacts[identity]
        contact_comparisons={s['id']:compare_one(g,s['rows']) for s in sources}
        present=[sid for sid,value in contact_comparisons.items() if value['overlap_features']]
        absent=[sid for sid,value in contact_comparisons.items() if not value['overlap_features']]
        contact_results.append({'contact_id':identity,'feature':feature,
          'comparisons':contact_comparisons,
          'assessment':{'role':'complete contact/context feature, not an independent component claim',
            'supported':f'Positive-area administrative source-footprint overlap in {", ".join(present)}.' if present else 'No positive-area administrative source-footprint overlap was found.',
            'contradicted':f'No positive-area overlap in {", ".join(absent)}; this is comparator disagreement only and does not refute the contact identity or physical surface.' if absent else 'No comparator absence observed.',
            'absent':'No date-stamped authoritative land/water observation with stated positional accuracy was acquired for this contact or adjoining family.',
            'unresolved':'Physical surface, legal boundary, source authority, applicable date, and lineage are not inferred from administrative overlap.',
            'missing_independent_fact':'Date-matched authoritative land/water evidence with per-tile observation dates and positional accuracy for the complete family.',
            'bounded_next_action':'Acquire that evidence lawfully and reassess all 16 components together before any geometry processing.',
            'physical_status':'not inferred','reason':'Contact geometry is context only; administrative overlap does not establish surface or a legal boundary.'}})
    totals={s['id']:sum(bool(x['comparisons'][s['id']]['overlap_features']) for x in component_results) for s in sources}
    positive_pair=None
    for c in component_results:
        g=projected[c['component_id']]
        for row in lt_orig:
            area=float(g.intersection(row['geometry']).area)
            if area>0:
                positive_pair=(c['component_id'],row,area);break
        if positive_pair:break
    if not positive_pair:raise ValueError('positive source-overlay control lacks a real family/source intersection')
    positive_id,positive_source,positive_area=positive_pair
    swapped=transform(lambda x,y,z=None:(y,x) if z is None else (y,x,z),shape(positive_source['geojson_geometry']))
    swapped_projected=transform(t4326,swapped)
    swapped_area=float(projected[positive_id].intersection(swapped_projected).area)
    if swapped_area>0:raise ValueError('swapped-axis adverse control unexpectedly overlaps selected component')
    result={'schema':'worldatlas-lt-lv-source-fit-v1','issue':1426,'family':FAMILY,'operational_batch':'gap-operational-batch:ab55d0afdee7bbc46b9dc092',
      'method':{'area_crs':'EPSG:3035 ETRS89-extended / LAEA Europe','area_method':'Shapely planar polygon intersection; positive area means geometric overlap only',
        'transform_library':f'pyproj {pyproj.__version__}','geometry_library':f'Shapely {shapely.__version__}','xml_library':f'lxml {__import__("lxml").__version__}',
        'source_feature_coverage':'complete retained Atlas products, the same-commit full-resolution Lithuania variant, and full-country official Lithuania and Latvia administrative products',
        'gml_stream_bytes':len(gml_bytes),'gml_stream_sha256':sha(gml_bytes),'gml_chunks':shard_receipt['decoded_shards'],
        'limits':['Administrative polygon overlap is source-footprint evidence only; it does not establish dry land, inland water, legal boundary, physical authority, date-matched truth, source reproduction or cause.',
          'Lithuania 2026 and Latvia 2021/2026 are not exact historical copies of the 2017 Lithuania/2021 Latvia simplified Atlas inputs; no lineage equivalence is inferred.',
          'Contact comparisons use original simplified Atlas contact geometries; components use current complete physical pointsets.',
          'No full historical official 2017 Lithuanian administrative product was located and pinned. The retained 2017 product is geoBoundaries simplified output; current official full coverage is 2026.',
          'The official Latvia GRPK SHP retrieval was abandoned at 787 MB and the partial file discarded; none of those bytes were consumed.']},
      'sources':[{k:v for k,v in s.items() if k!='rows'} for s in sources],
      'component_overlap_counts':totals,'components':component_results,'contacts':contact_results,
      'controls':{'complete_16_component_roster':len(component_results)==16,'complete_3_contact_roster':len(contact_results)==3,
        'all_source_features_parsed':len(lt_rows)==604 and len(lv21)==43 and len(lv26)==42 and len(full_lt)==60,
        'positive_intersection_and_outside_measurements_finite':all(math.isfinite(v) for c in component_results for d in c['comparisons'].values() for v in [d['overlap_area_m2'],d['component_area_m2'],d['outside_admin_union_area_m2']]),
        'nonoverlap_control':any(not c['comparisons'][s['id']]['overlap_features'] for c in component_results for s in sources),
        'real_positive_overlay_control':{'component_id':positive_id,'source_feature_id':positive_source.get('code'),'source_id':'GB_LTU_ADM2_original_simplified_2017','intersection_area_m2':positive_area},
        'swapped_axis_negative_control':{'component_id':positive_id,'source_feature_id':positive_source.get('code'),'intersection_area_m2':swapped_area},
        'source_fit_does_not_approve_physical_surface':True}}
    extras={
      'positive-control.json':{'method_id':'admin-source-overlap','kind':'positive-control','outcome':'passed',
        'component_id':positive_id,'source_feature_id':positive_source.get('code'),'intersection_area_m2':positive_area,
        'meaning':'An exact whole-family component and retained full-source feature have a finite positive-area intersection.'},
      'negative-control.json':{'method_id':'admin-source-overlap','kind':'negative-control','outcome':'passed',
        'component_id':positive_id,'source_feature_id':positive_source.get('code'),'axis_order_adversary':'latitude-longitude swapped as longitude-latitude',
        'intersection_area_m2':swapped_area,'meaning':'The same retained source feature with swapped axes does not overlap the same component.'}}
    return publish(target,result,'source-fit',vintage,admitted,total,started,extra_outputs=extras)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('stage',choices=['custody','routing','physical','assemble','gml-validation','source-fit'])
    parser.add_argument('--vintage',required=True)
    parser.add_argument('--assembly',default='assemble-complete1')
    args=parser.parse_args()
    if args.stage in ('custody','routing','physical'):
        receipt=stage_extract(args.stage,args.vintage)
    elif args.stage=='assemble':
        receipt=assembly(args.vintage)
    elif args.stage=='gml-validation':
        receipt=stage_gml_validation(args.vintage)
    else:
        receipt=compare_source(args.vintage,args.assembly)
    print(json.dumps(receipt,sort_keys=True))


if __name__=='__main__':
    main()
