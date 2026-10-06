"""Preserve complete old/new diagnostic components and exact correspondence."""
import argparse
import gzip
import io
import json
import pathlib
import subprocess
import sys

import shapely

from evidence.immutable import Baseline, MAX_FILE_BYTES, canonical_json, descriptor, deterministic_gzip, safe_path, sha256
from geographic_components import components
from physical_gap_crosswalk import VERSION, crosswalk, membership

ROOT = pathlib.Path(__file__).resolve().parents[1]
OWNED = 'coordination/engineering/physical-gap-components-1005-20261005-local19/'
OLD = 'coordination/engineering/coverage-gaps-907-20261005-local01/global-v3/report.json'
OLD_COMPONENTS = 'coordination/engineering/geographic-components-946-20261005-local06/components-v2/report.json'
NEW = 'coordination/engineering/physical-gap-audit-1005-20261005-local18/detection-v4/report.json'
CODE = ['scripts/build-physical-gap-components.py', 'scripts/physical_gap_crosswalk.py',
        'scripts/geographic_components.py', 'scripts/physical_gap_audit.py', 'scripts/evidence/immutable.py']


class Inputs:
    def __init__(self, commit):
        raw = subprocess.check_output(['git', 'show', commit + ':' + OLD], cwd=ROOT)
        self.source = Baseline(ROOT, commit, [descriptor(OLD, raw)])
        self.pins = {}

    def read(self, path):
        raw = self.source.read(safe_path(path))
        self.pins[path] = descriptor(path, raw)
        return raw

    def report(self, path, version):
        row = json.loads(self.read(path))
        if row['version'] != version:
            raise ValueError('Unexpected original diagnostic report')
        return row

    def bundle(self, entry):
        raw = self.read(entry['path'])
        if len(raw) != entry['bytes'] or sha256(raw) != entry['sha256']:
            raise ValueError('Original complete input bundle changed')
        with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
            decoded = stream.read(MAX_FILE_BYTES + 1)
        if (len(decoded) > MAX_FILE_BYTES or len(decoded) != entry['uncompressed_bytes']
                or sha256(decoded) != entry['uncompressed_sha256']):
            raise ValueError('Original complete decoded bundle changed')
        return json.loads(decoded)

    def features(self, report, kinds=('outputs',)):
        result = []
        for kind in kinds:
            for entry in report[kind]:
                body = self.bundle(entry)
                if body['type'] != 'FeatureCollection':
                    raise ValueError('Original FeatureCollection required')
                result.extend(body['features'])
        return result


def write_bundles(out, name, rows, collection=False):
    outputs, batch, size = [], [], 0

    def flush():
        if not batch:
            return
        body = {'type': 'FeatureCollection', 'features': batch} if collection else batch
        raw = canonical_json(body)
        if len(raw) > MAX_FILE_BYTES:
            raise ValueError('Complete output exceeds unchanged file budget')
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
    flush()
    return outputs


def unknowns(features):
    return sorted(f['id'] for f in features if f['properties'].get('area_m2') is None)


def run(commit, output):
    output = safe_path(output)
    if not output.startswith(OWNED) or output == OWNED.rstrip('/'):
        raise ValueError('Use an explicit new vintage inside the claimed owned packet')
    out = ROOT / output
    if out.exists() or any(p.is_symlink() for p in [out, *out.parents]):
        raise ValueError('Original/prior outputs must never be overwritten')
    executed = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip()
    code = []
    for path in CODE:
        raw = subprocess.check_output(['git', 'show', executed + ':' + path], cwd=ROOT)
        if (ROOT / path).is_symlink() or (ROOT / path).read_bytes() != raw:
            raise ValueError('Commit exact ordinary executable bytes before scientific generation')
        code.append(descriptor(path, raw))
    inputs = Inputs(commit)
    old_report = inputs.report(OLD, 'worldatlas-geographic-gap-audit-v1')
    old_component_report = inputs.report(OLD_COMPONENTS, 'worldatlas-geographic-gap-components-v1')
    new_report = inputs.report(NEW, 'worldatlas-physical-land-before-water-v1')
    new_pins = {row['path']: row for row in new_report['inputs']}
    if any(new_pins.get(row['path']) != row for row in old_report['inputs']):
        raise ValueError('Original comparison audit consumed different physical/native/grid inputs')
    if old_report['bounds'] != new_report['bounds'] or old_component_report['bounds'] != new_report['bounds']:
        raise ValueError('Original/new declared domains differ')
    old_features, new_features = inputs.features(old_report), inputs.features(new_report)
    new_residues = inputs.features(new_report, ('residue_outputs',))
    old_records = []
    for entry in old_component_report['outputs']:
        body = inputs.bundle(entry)
        if isinstance(body, dict) and body.get('type') == 'FeatureCollection':
            old_records.extend(body['features'])
    if (len(old_features) != old_report['candidate_fragments'] or len(new_features) != new_report['candidate_fragments']
            or len(new_residues) != new_report['residues'] or len(old_records) != old_component_report['component_count']):
        raise ValueError('Original complete candidate/residue/component counts differ')
    old_unknown = sorted(f"{e['tile']}:{e['fragment']}" for e in old_report['measurement_errors'])
    new_unknown = sorted(e['fragment'] for e in new_report['measurement_errors'])
    if unknowns(old_features) != old_unknown or unknowns(new_features) != new_unknown:
        raise ValueError('Original measurement uncertainty changed')
    if old_component_report['unmeasured_fragment_ids'] != old_unknown:
        raise ValueError('Original component uncertainty changed')
    membership(old_features, old_records)
    blocked = [row for row in new_report['tiles'] if row['status'] != 'checked']
    records, contacts = components(new_features, blocked, new_report['bounds'])
    for record in records:
        record['id'] = 'physical-component:' + record['id'].split(':', 1)[1]
    members = membership(new_features, records)
    for contact in contacts:
        contact['components'] = [members[i] for i in contact['fragments']]
    print(json.dumps({'stage': 'new-components-complete', 'components': len(records), 'contacts': len(contacts)}), flush=True)
    result = crosswalk(old_features, new_features, old_records, records)
    out.mkdir(parents=True, exist_ok=False)
    outputs = {'new_components': write_bundles(out, 'components', records, True),
               'new_contacts': write_bundles(out, 'contacts', contacts)}
    for name, rows in result.items():
        outputs[name] = write_bundles(out, name.replace('_', '-'), rows)
    errors = [p for p in result['fragment_pairs'] if p['status'] != 'checked']
    difference_errors = [f for key in ('old_fragments', 'new_fragments') for f in result[key]
                         if f['difference']['status'] != 'checked']
    old_blocked = []
    for tile in old_report['tiles_blocked']:
        same = [r for r in new_report['tiles'] if r['bounds'] == tile['bounds']]
        if len(same) != 1:
            raise ValueError('Original blocked domain is missing from complete new ledger')
        old_blocked.append({'original': tile, 'new': same[0]})
    report = {'version': VERSION, 'input_commit': commit, 'executed_code_commit': executed,
              'code_inputs': code, 'inputs': list(inputs.pins.values()), 'outputs': outputs,
              'bounds': new_report['bounds'], 'software': {'python': sys.version.split()[0],
                   'shapely': shapely.__version__, 'geos': shapely.geos_version_string},
              'old_fragments': len(old_features), 'new_fragments': len(new_features),
              'old_components': len(old_records), 'new_components': len(records),
              'new_remnants_preserved_in_original_bundles': len(new_residues),
              'fragment_pairs': len(result['fragment_pairs']), 'component_links': len(result['component_links']),
              'unmeasured_original_ids': old_unknown, 'unmeasured_new_ids': new_unknown,
              'original_blocked_domains': old_blocked, 'overlay_unknowns': errors,
              'difference_unknowns': [{'fragment': r['fragment'], 'side': r['side'], 'difference': r['difference']}
                                      for r in difference_errors],
              'status': 'complete-accounting-with-explicit-unknowns' if errors or difference_errors else 'complete-exact-correspondence-accounting',
              'limits': ['Numerical source-set correspondence, not factual repair, water truth or administrative approval.',
                         'Edge/point-only contacts are separate from positive-area relations and do not establish identity.',
                         'Original component and fragment IDs are preserved; every new component has a distinct namespace.',
                         'Original invalid-water blocked domains/measurement unknowns remain historical evidence.',
                         'Dateline comparisons translate copies only; original input coordinates and identities remain intact.',
                         'Residual planar areas are square degrees, not physical square metres.',
                         'The independent physical reference cannot certify every island, fine coast or river.',
                         'Worldwide source-backed priorities, factual repairs, release/content revalidation and delivery follow separately.']}
    with (out / 'report.json').open('xb') as stream:
        stream.write(canonical_json(report))
    print(json.dumps({k: report[k] for k in ('status', 'old_fragments', 'new_fragments', 'old_components', 'new_components', 'fragment_pairs', 'component_links')}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    run(args.commit, args.output)
