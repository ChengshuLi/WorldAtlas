#!/usr/bin/env python3
"""Extract retained inherited physical/source claims for the complete roster."""
import csv
import gzip
import hashlib
import io
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PACKET = Path(__file__).resolve().parent
MANIFEST_PATH = PACKET / 'evidence-quality.json'
OWNED = 'research/geography/india-western-gap-source-fitness-20261007/'
VINTAGE = 'inherited-claims-2026-10-08-01'


def load_reader(manifest):
    helper = 'scripts/evidence/immutable.py'
    commit = manifest['baseline']['commit']
    pin = next(x for x in manifest['baseline']['files'] if x['path'] == helper)
    tree = subprocess.check_output(['git', '-C', str(ROOT), 'ls-tree', '-z', commit, '--', helper]).decode().rstrip('\0')
    if not tree.startswith(('100644 ', '100755 ')) or '\t' + helper != tree[tree.find('\t'):]:
        raise ValueError('Immutable helper is not an ordinary baseline file')
    blob = tree.split()[2]
    raw = subprocess.check_output(['git', '-C', str(ROOT), 'cat-file', 'blob', blob])
    if len(raw) != pin['bytes'] or hashlib.sha256(raw).hexdigest() != pin['sha256']:
        raise ValueError('Immutable helper differs from its reviewed pin')
    namespace = {'__name__': 'worldatlas_bootstrap_immutable', '__file__': str(ROOT / helper)}
    exec(compile(raw, str(ROOT / helper), 'exec'), namespace)
    bootstrap = namespace['Baseline'](ROOT, commit, [pin])
    return bootstrap.load_modules({'evidence.immutable': helper})['evidence.immutable']


def main():
    manifest = json.loads(MANIFEST_PATH.read_text())
    immutable = load_reader(manifest)
    baseline = immutable.Baseline(ROOT, manifest['baseline']['commit'], manifest['baseline']['files'])
    baseline.load_modules({'evidence.immutable': 'scripts/evidence/immutable.py'})
    pin_files = manifest['baseline']['pin_files']
    expected = set(manifest['subject_ids'])
    rows = {}
    for key in sorted(k for k in pin_files if k.startswith('physical_component_rows_')):
        path = pin_files[key]
        raw = baseline.pinned_bytes(path)
        decoded = gzip.decompress(raw)
        baseline.admit(path + '#decoded', len(decoded))
        descriptor = next(x for x in manifest['baseline']['files'] if x['path'] == path)
        if (len(decoded) != descriptor.get('uncompressed_bytes') or
                hashlib.sha256(decoded).hexdigest() != descriptor.get('uncompressed_sha256')):
            raise ValueError('Decoded inherited row shard differs from its manifest descriptor: ' + path)
        for line in decoded.splitlines():
            record = json.loads(line)
            sid = record.get('component_id')
            if sid in expected:
                if sid in rows:
                    raise ValueError('Duplicate inherited component row: ' + sid)
                rows[sid] = record
    if set(rows) != expected:
        raise ValueError('Inherited row roster is incomplete')

    output_rows = []
    for sid in manifest['subject_ids']:
        record = rows[sid]
        support = record.get('complete_support', {})
        support_summary = {}
        for category, detail in sorted(support.items()):
            if not isinstance(detail, dict):
                continue
            support_summary[category] = {
                'kind': detail.get('kind'),
                'area_m2_diagnostic_only': detail.get('area_m2'),
                'planar_area_diagnostic_only': detail.get('planar_area'),
                'geometry_sha256': detail.get('geometry_sha256'),
            }
        output_rows.append({
            'subject_id': sid,
            'inherited_status': record.get('status', ''),
            'inherited_physical_status': record.get('physical_status', ''),
            'inherited_physical_authority': record.get('physical_authority', ''),
            'inherited_source_vintage': record.get('source_vintage', ''),
            'inherited_complete_contact_ids': json.dumps(record.get('complete_contact_ids', []), separators=(',', ':')),
            'inherited_complete_support_summary': json.dumps(support_summary, sort_keys=True, separators=(',', ':'), ensure_ascii=False),
            'inherited_query_relations': json.dumps(record.get('query_relations', []), sort_keys=True, separators=(',', ':'), ensure_ascii=False),
            'inherited_physical_limits': json.dumps(record.get('physical_limits', []), separators=(',', ':'), ensure_ascii=False),
            'inherited_unresolved': json.dumps(record.get('unresolved', []), separators=(',', ':'), ensure_ascii=False),
        })

    report = {
        'version': 1,
        'status': 'complete-inherited-claims-extraction',
        'baseline_commit': manifest['baseline']['commit'],
        'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'subject_ids_sha256': manifest['subject_ids_sha256'],
        'row_count': len(output_rows),
        'physical_status_counts': {},
        'source_status_counts': {},
        'physical_authority_counts': {},
        'baseline_phase_consumed_bytes_including_decoded_parts': sum(baseline.consumed.values()),
        'input_shards': [{'path': pin_files[key], 'compressed_sha256': manifest['baseline']['pins'][key],
                          'uncompressed_sha256': next(x['uncompressed_sha256'] for x in manifest['baseline']['files'] if x['path'] == pin_files[key])}
                         for key in sorted(k for k in pin_files if k.startswith('physical_component_rows_'))],
        'scope': 'Field-preserving projection from the exact 18 pinned global physical-comparison rows. Inherited category values and diagnostics are not fresh observations or approvals.',
    }
    for row in output_rows:
        for field, target in [('inherited_physical_status', 'physical_status_counts'), ('inherited_status', 'source_status_counts'), ('inherited_physical_authority', 'physical_authority_counts')]:
            value = row[field] or 'not-recorded'
            report[target][value] = report[target].get(value, 0) + 1

    stream = io.StringIO(newline='')
    fields = list(output_rows[0])
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator='\n')
    writer.writeheader()
    writer.writerows(output_rows)
    csv_bytes = stream.getvalue().encode('utf-8')
    report_bytes = (json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + '\n').encode()
    filenames = ['inherited-claims.csv', 'report.json']
    published = immutable.NewVintage(baseline, OWNED, VINTAGE, filenames).publish_bytes({
        'inherited-claims.csv': csv_bytes,
        'report.json': report_bytes,
    })
    print(json.dumps({'status': 'complete', 'published': published, 'report': report}, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
