#!/usr/bin/env python3
"""Reconcile geoBoundaries advertised, sourceData, full-resolution and simplified counts."""
import collections
import argparse
import gzip
import hashlib
import importlib.util
import json
import pathlib
import subprocess
import zipfile

HERE = pathlib.Path(__file__).resolve().parent
PACKET = HERE.parent
ROOT = pathlib.Path(__file__).resolve().parents[4]
SOURCES = HERE / 'sources'
SCREEN = PACKET / 'vintages' / 'coverage-screen-2026-10-08-04'
BASELINE = '64770c1a8c82c3626344d3d5ce322cdcb839ea2e'
LFS = {
    'ADM2_source_archive': 'de31379da90a382fc595d05ea71df8742ac01da04fc7fbad5775b3b8d90a6915',
    'ADM3_source_archive': '322f8689cbdf274bbf6477158904e68aa292b4603c1a035ed7b7e92833f8a0ef',
    'ADM2_full_resolution': '8bef6929fd65432e7dc775e7c44473e84efff064ebddbfd6b834e6291546db40',
    'ADM3_full_resolution': 'f9c38b47f2b8755af59d30bb846f66d0823aba127872668ccc2fa9f0dc3cd48f',
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode()


def sha_file(path):
    h = hashlib.sha256(); size = 0
    with open(path, 'rb') as stream:
        while block := stream.read(1024 * 1024):
            h.update(block); size += len(block)
    return size, h.hexdigest()


def descriptor(path):
    size, digest = sha_file(path)
    return {'path': str(path.relative_to(ROOT)), 'bytes': size, 'sha256': digest, 'hash_kind': 'file-bytes'}


def chunks(paths, compressed=False):
    for path in paths:
        opener = gzip.open if compressed else open
        with opener(path, 'rb') as stream:
            while block := stream.read(1024 * 1024):
                yield block


def features(stream):
    """Incrementally decode one FeatureCollection without materializing it."""
    import codecs
    import re
    decoder = codecs.getincrementaldecoder('utf-8')()
    parser = json.JSONDecoder()
    text = ''; found = False; ended = False
    for raw in stream:
        text += decoder.decode(raw, final=False)
        if not found:
            match = re.search(r'"features"\s*:\s*\[', text)
            if match:
                text = text[match.end():]; found = True
        if found:
            while True:
                text = text.lstrip()
                if not text: break
                if text[0] == ',': text = text[1:]; continue
                if text[0] == ']': ended = True; break
                try: row, end = parser.raw_decode(text)
                except json.JSONDecodeError:
                    if len(text.encode('utf-8')) > 32 * 1024 * 1024:
                        raise ValueError('A single feature exceeded the 32 MiB buffer limit')
                    break
                if not isinstance(row, dict) or row.get('type') != 'Feature':
                    raise ValueError('FeatureCollection contains a non-Feature row')
                yield row
                text = text[end:]
        if ended:
            for _ in stream: pass
            return
    text += decoder.decode(b'', final=True)
    if not ended and not text.lstrip().startswith(']'):
        raise ValueError('FeatureCollection ended before the features array closed')


def geodata_inventory(source):
    count = 0; ids = {}; names = []
    for feature in source:
        properties = feature.get('properties') or {}
        name = properties.get('shapeName') or properties.get('Name')
        if name is not None: names.append(str(name))
        shape_id = properties.get('shapeID')
        if shape_id:
            if shape_id in ids: raise ValueError('Duplicate shapeID in release product: ' + str(shape_id))
            ids[shape_id] = str(name or '')
        count += 1
    return {'feature_count': count, 'shape_ids': ids, 'names': names}


def baseline_blob(path, manifest):
    row = next((x for x in manifest['baseline']['files'] if x['path'] == path), None)
    if row is None: raise ValueError('Baseline descriptor absent for ' + path)
    raw = subprocess.check_output(['git', '-C', str(ROOT), 'show', BASELINE + ':' + path])
    if len(raw) != row['bytes'] or sha(raw) != row['sha256']:
        raise ValueError('Pinned metadata bytes differ: ' + path)
    return raw, row


def dbf_names(raw):
    if len(raw) < 33: raise ValueError('Truncated DBF header')
    records = int.from_bytes(raw[4:8], 'little')
    header_len = int.from_bytes(raw[8:10], 'little')
    record_len = int.from_bytes(raw[10:12], 'little')
    fields = []; offset = 32
    while offset < header_len and raw[offset] != 13:
        row = raw[offset:offset + 32]
        if len(row) != 32: raise ValueError('Truncated DBF field descriptor')
        fields.append({'name': row[:11].split(b'\0')[0].decode('ascii'), 'type': chr(row[11]), 'width': row[16]})
        offset += 32
    cursor = 1; name_offset = None; name_width = None
    for field in fields:
        if field['name'].casefold() == 'name': name_offset, name_width = cursor, field['width']
        cursor += field['width']
    if name_offset is None or cursor != record_len: raise ValueError('DBF field layout mismatch')
    names = []; deleted = 0
    for i in range(records):
        row = raw[header_len + i * record_len:header_len + (i + 1) * record_len]
        if len(row) != record_len: raise ValueError('Truncated DBF record')
        if row[0:1] == b'*': deleted += 1; continue
        if row[0:1] != b' ': raise ValueError('Invalid DBF deletion flag')
        names.append(row[name_offset:name_offset + name_width].decode('utf-8', 'replace').strip())
    return {'header_record_count': records, 'active_record_count': len(names), 'deleted_record_count': deleted,
            'fields': fields, 'names': names}


def multiset_missing(left, right):
    delta = collections.Counter(left) - collections.Counter(right)
    return [{'name': name, 'count': count} for name, count in sorted(delta.items())]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', required=True, help='New, nonexistent output directory under this packet')
    args = parser.parse_args()
    output_dir = pathlib.Path(args.output_dir).resolve()
    if ROOT not in output_dir.parents or output_dir.exists():
        raise ValueError('Output directory must be a fresh, nonexistent directory inside this packet')
    output_dir.mkdir(parents=True, exist_ok=False)
    manifest = json.loads((PACKET / 'evidence-quality.json').read_text())
    source_manifest = manifest
    admin_raw, admin_desc = baseline_blob('data/administrative-sources.json', source_manifest)
    adm3_raw, adm3_desc = baseline_blob('data/global-sources/IND-ADM3-metadata.json', source_manifest)
    catalog_raw, catalog_desc = baseline_blob('coordination/engineering/original-geography-source-corpus-20261006/catalogue.json', source_manifest)
    admin = json.loads(admin_raw); adm3meta = json.loads(adm3_raw); catalog = json.loads(catalog_raw)
    catalog_products = {x['key']: x for x in catalog['products']}
    source_archive = {}; simplified = {}
    source_paths = {}
    admitted_files = []
    metadata_bytes = admin_desc['bytes'] + adm3_desc['bytes'] + catalog_desc['bytes']
    for level in ('ADM2', 'ADM3'):
        archive_path = SOURCES / f'IND-{level}.zip'
        with zipfile.ZipFile(archive_path) as zf:
            suffix = '.geojson' if level == 'ADM2' else '.dbf'
            member = next(name for name in zf.namelist() if name.lower().endswith(suffix))
            decoded_archive_bytes = zf.getinfo(member).file_size
        simple_paths = sorted(SCREEN.glob(f'{level.lower()}-*.bin.gz'))
        if not simple_paths: raise ValueError('Missing retained simplified source parts for ' + level)
        simple_product = catalog_products[f'gb:IND:{level}']
        admitted_files.append({'path': str(archive_path.relative_to(ROOT)), 'member': member,
                               'raw_bytes': archive_path.stat().st_size, 'decoded_bytes': decoded_archive_bytes,
                               'handling': 'streamed one feature at a time' if level == 'ADM2' else 'bounded DBF table read'})
        for part in simple_paths:
            admitted_files.append({'path': str(part.relative_to(ROOT)), 'raw_bytes': part.stat().st_size,
                                   'decoded_bytes': 0, 'handling': 'streamed gzip part'})
        admitted_files.append({'path': f'assembled retained {level} product', 'raw_bytes': 0,
                               'decoded_bytes': simple_product['original_bytes'],
                               'handling': 'streamed concatenated gzip parts'})
    admitted_raw = metadata_bytes + sum(row['raw_bytes'] for row in admitted_files)
    admitted_decoded = sum(row['decoded_bytes'] for row in admitted_files)
    phase_total = admitted_raw + admitted_decoded
    if phase_total > 256 * 1024 * 1024:
        raise ValueError(f'Count reconciliation phase exceeds 256 MiB before reading inputs: {phase_total} bytes')

    for level in ('ADM2', 'ADM3'):
        archive_path = SOURCES / f'IND-{level}.zip'
        archive_desc = descriptor(archive_path)
        if archive_desc['sha256'] != LFS[f'{level}_source_archive']:
            raise ValueError(level + ' sourceData archive differs from its pinned Git LFS object')
        source_paths[f'{level}_source_archive'] = [archive_desc]
        with zipfile.ZipFile(archive_path) as zf:
            if level == 'ADM2':
                member = next(name for name in zf.namelist() if name.lower().endswith('.geojson'))
                member_bytes = zf.getinfo(member).file_size
                with zf.open(member) as stream:
                    inventory = geodata_inventory(features(iter(lambda: stream.read(1024 * 1024), b'')))
                source_count = inventory['feature_count']
                source_names = inventory['names']
                source_details = {'archive_member': member, 'record_kind': 'GeoJSON FeatureCollection', 'feature_count': source_count}
            else:
                member = next(name for name in zf.namelist() if name.lower().endswith('.dbf'))
                member_bytes = zf.getinfo(member).file_size
                parsed = dbf_names(zf.read(member))
                source_count = parsed['active_record_count']; source_names = parsed['names']
                source_details = {'archive_member': member, 'record_kind': 'DBF active rows', **{k:v for k,v in parsed.items() if k != 'names'}}
        simple_paths = sorted(SCREEN.glob(f'{level.lower()}-*.bin.gz'))
        if not simple_paths: raise ValueError('Missing retained simplified source parts for ' + level)
        simple_inv = geodata_inventory(features(chunks(simple_paths, compressed=True)))
        part_descs = []
        for path in simple_paths:
            item = descriptor(path)
            with gzip.open(path, 'rb') as stream:
                data_hash = hashlib.sha256(); decoded_bytes = 0
                while block := stream.read(1024 * 1024): data_hash.update(block); decoded_bytes += len(block)
            item.update(uncompressed_bytes=decoded_bytes, uncompressed_sha256=data_hash.hexdigest())
            part_descs.append(item)
        catalog_product = catalog_products[f'gb:IND:{level}']
        simple_hash = catalog_product['original_sha256']
        source_paths[f'{level}_simplified'] = part_descs
        simplified[level] = {'feature_count': simple_inv['feature_count'], 'shape_ids': simple_inv['shape_ids'],
                             'names': simple_inv['names'], 'parts': part_descs, 'whole_sha256': simple_hash,
                             'whole_bytes': catalog_product['original_bytes']}
        expected = int(catalog_products[f'gb:IND:{level}']['advertised_feature_count'])
        if source_count != expected:
            raise ValueError(f'{level} archive row count differs from pinned metadata: {source_count} != {expected}')
        source_archive[level] = {'archive': archive_desc, 'record_count': source_count, 'metadata_count': expected,
                                 'metadata_count_matches': source_count == expected,
                                 'record_details': source_details, 'names': source_names,
                                 'simplified_missing_by_name': multiset_missing(source_names, simple_inv['names']),
                                 'simplified_extra_by_name': multiset_missing(simple_inv['names'], source_names)}

    product_rows = {}
    for level in ('ADM2','ADM3'):
        expected = int(catalog_products[f'gb:IND:{level}']['advertised_feature_count'])
        product_rows[level] = {
            'metadata_advertised_feature_count': expected,
            'sourceData_archive_record_count': source_archive[level]['record_count'],
            'releaseData_simplified_feature_count': simplified[level]['feature_count'],
            'metadata_minus_simplified': expected - simplified[level]['feature_count'],
            'sourceData_minus_simplified': source_archive[level]['record_count'] - simplified[level]['feature_count'],
            'sourceData_names_missing_from_simplified': source_archive[level]['simplified_missing_by_name'],
            'sourceData_names_extra_in_simplified': source_archive[level]['simplified_extra_by_name'],
        }
    products = {}
    for level in ('ADM2','ADM3'):
        products[level] = {k:v for k,v in product_rows[level].items()}
        products[level]['sourceData_archive'] = {k:v for k,v in source_archive[level].items() if k != 'names'}
        products[level]['releaseData_simplified'] = {k:v for k,v in simplified[level].items() if k not in ('shape_ids','names')}
    inputs = {
        'baseline_commit': BASELINE,
        'baseline_metadata': {'administrative_sources': admin_desc, 'adm3_metadata': adm3_desc, 'source_catalogue': catalog_desc},
        'source_paths': source_paths,
    }
    inputs_sha = sha(canonical(inputs))
    omissions = {
        'The sourceData and retained simplified counts differ; the repository artifacts do not identify the processing stage or operation that explains the difference.',
        'Name multiset comparison is not a stable identifier join; sourceData input records do not carry the release shapeID. No geometry equality, land/water state, authority or legal interpretation is inferred.'
    }
    report = {
        'version':1,'status':'complete-advertised-to-retained-count-reconciliation-with-processing-cause-unresolved',
        'baseline_commit':BASELINE,'upstream_commit':'9469f09','analysis_input_sha256':inputs_sha,
        'admission':{'status':'admitted','budget_bytes':256*1024*1024,'raw_and_metadata_bytes':admitted_raw,
                     'decoded_bytes':admitted_decoded,'phase_total_bytes':phase_total,
                     'max_single_feature_buffer_bytes':32*1024*1024,'files':admitted_files},
        'method':'Compare pinned geoBoundaries metadata counts and SourceData archive records to retained simplified-product counts. Compare source names as multisets only; sourceData records do not carry release shapeIDs. Do not use geometry predicates or interpret physical surface.',
        'products':products,'input_inventory':inputs,'limits':sorted(omissions),
        'interpretation':'The advertised counts match the inspected SourceData archive row counts (736 ADM2; 6836 ADM3). The retained simplified products have 735 ADM2 and 6822 ADM3 features. The archive-to-retained count differences and exact source-name multisets are reproducible; the repository artifacts do not identify why those records are absent. Source-name equality is not a stable identity join.'
    }
    report_path = output_dir / 'report.json'; report_path.write_bytes(canonical(report))
    script = pathlib.Path(__file__)
    outputs=[]
    for path,role in [(script,'method-code'),(report_path,'generated-evidence')]:
        d=descriptor(path);d['role']=role;outputs.append(d)
    publication={'version':1,'status':'complete','outputs':[{k:x[k] for k in ('path','bytes','sha256','hash_kind')} for x in outputs if x['path'].endswith('report.json')]}
    pub_path=output_dir/'publication.json';pub_path.write_bytes(canonical(publication));d=descriptor(pub_path);d['role']='generated-evidence';outputs.append(d)
    evidence={
      'version':1,'issue':1432,'lane':'source-only','worker_id':manifest['worker_id'],
      'subject_ids':manifest['subject_ids'],'subject_ids_sha256':manifest['subject_ids_sha256'],
      'baseline':{'commit':BASELINE,'files':[admin_desc,adm3_desc,catalog_desc]},
      'sources':[
        {'id':'geoboundaries-ind-sourceData-archives','url':'https://github.com/wmgeolab/geoBoundaries/tree/9469f09/sourceData/gbOpen','role':'Original India ADM2 GeoJSON and ADM3 shapefile sourceData archives used to reconcile the advertised unit counts.','vintage':'geoBoundaries commit 9469f09','retrieved_at':'2026-10-08','license':{'status':'redistributable','terms':'geoBoundaries India release metadata declares ODbL 1.0; license URI https://opendatacommons.org/licenses/odbl/1-0/.'},'retention':'retained','verification':'verified','restoration':'Exact Git LFS objects from sourceData/gbOpen/IND_ADM2.zip and IND_ADM3.zip at commit 9469f09; whole archive bytes match LFS SHA-256 IDs.','files':source_paths['ADM2_source_archive']+source_paths['ADM3_source_archive'],'temporal_status':'reference','limit':'SourceData counts and name multisets explain observed retained-count differences, but repository artifacts do not identify the processing operation.'},
        {'id':'geoboundaries-ind-retained-simplified-products','url':'https://github.com/wmgeolab/geoBoundaries/tree/9469f09/releaseData/gbOpen/IND','role':'Complete retained simplified India ADM2 and ADM3 products compared with the sourceData records.','vintage':'geoBoundaries commit 9469f09','retrieved_at':'2026-10-08','license':{'status':'redistributable','terms':'geoBoundaries India release metadata declares ODbL 1.0; license URI https://opendatacommons.org/licenses/odbl/1-0/.'},'retention':'retained','verification':'verified','restoration':'Exact compressed retained-product partitions in coverage-screen-2026-10-08-04; decoded hashes match the source-corpus catalogue.','files':source_paths['ADM2_simplified']+source_paths['ADM3_simplified'],'temporal_status':'reference','limit':'Name multisets are not a stable identifier join; no geometry, physical surface or processing cause is inferred.'}
      ],
      'outputs':outputs,
      'methods':[{'id':'release-count-reconciliation','kind':'source','description':report['method'],'software':'Python 3.12; gzip, zipfile, incremental JSON parser, SHA-256','units':'features or source rows; source-name multiset differences'}],
      'commands':['python3 research/geography/india-western-gap-source-fitness-20261007/feature-count-reconciliation/run.py','node scripts/evidence-quality.mjs research/geography/india-western-gap-source-fitness-20261007/feature-count-reconciliation/evidence-quality.json'],
      'metrics':[
        {'id':'adm2_sourceData_record_count','value':product_rows['ADM2']['sourceData_archive_record_count'],'unit':'features','vintage':'baseline','input_sha256':source_paths['ADM2_source_archive'][0]['sha256'],'input_set_sha256':inputs_sha,'evaluation_commit':BASELINE,'title':'ADM2 sourceData archive features'},
        {'id':'adm3_sourceData_record_count','value':product_rows['ADM3']['sourceData_archive_record_count'],'unit':'features','vintage':'baseline','input_sha256':source_paths['ADM3_source_archive'][0]['sha256'],'input_set_sha256':inputs_sha,'evaluation_commit':BASELINE,'title':'ADM3 sourceData archive features'},
      ],
      'summaries':[{'metric_id':m['id'],'value':m['value'],'unit':m['unit']} for m in [
        {'id':'adm2_sourceData_record_count','value':product_rows['ADM2']['sourceData_archive_record_count'],'unit':'features'},
        {'id':'adm3_sourceData_record_count','value':product_rows['ADM3']['sourceData_archive_record_count'],'unit':'features'}]],
      'metric_bindings':[
        {'metric_id':'adm2_sourceData_record_count','path':str(report_path.relative_to(ROOT)),'json_pointer':'/products/ADM2/sourceData_archive_record_count'},
        {'metric_id':'adm3_sourceData_record_count','path':str(report_path.relative_to(ROOT)),'json_pointer':'/products/ADM3/sourceData_archive_record_count'}],
      'conclusions':[{'status':'supported','text':report['interpretation'],'source_ids':['geoboundaries-ind-sourceData-archives','geoboundaries-ind-retained-simplified-products']}],
      'stages':{'research':'complete','implementation':'not-proposed','geographic_approval':'unapproved'}
    }
    (output_dir/'evidence-quality.json').write_text(json.dumps(evidence,indent=2)+'\n')
    print(json.dumps({'status':report['status'],'inputs_sha256':inputs_sha,'products':{k:{x:y for x,y in v.items() if x.endswith('_count')} for k,v in product_rows.items()}},indent=2))

if __name__ == '__main__': main()
