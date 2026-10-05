"""Reproduce dated water pilots from ordinary immutable Git inputs."""
import argparse
import gzip
import io
import json
import pathlib
import sys

import rasterio
import shapely
from shapely.geometry import box, mapping, shape

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from evidence.immutable import Baseline, MAX_FILE_BYTES, canonical_json, descriptor, safe_path, sha256
from geographic_water import VERSION, monthly_diagnostics, compare_months


def decoded_bundle(encoded, pin):
    with gzip.GzipFile(fileobj=io.BytesIO(encoded)) as stream:
        raw = stream.read(MAX_FILE_BYTES + 1)
    if (len(raw) > MAX_FILE_BYTES or len(raw) != pin['uncompressed_bytes']
            or sha256(raw) != pin['uncompressed_sha256']):
        raise ValueError('Decoded immutable bundle exceeds budget or differs from whole-file pin')
    return raw


def diagnose(commit, inputs_path, inputs_bytes, inputs_sha256, destination):
    pin = {'path': safe_path(inputs_path), 'bytes': inputs_bytes,
           'sha256': inputs_sha256, 'hash_kind': 'file-bytes'}
    source = Baseline(ROOT, commit, [pin])
    registry = json.loads(source.read(inputs_path))
    if registry.get('version') != 'worldatlas-water-pilot-inputs-v1':
        raise ValueError('Unknown water input registry')
    if not 1 <= len(registry['pilots']) <= 8 or not 1 <= len(registry['sources']) <= 24:
        raise ValueError('Pilot/source budget exceeded')
    source = Baseline(ROOT, commit, [pin, *registry['sources'], *registry['references']])
    component_pins = {p['component_file']['path']: p['component_file'] for p in registry['pilots']}
    components = Baseline(ROOT, registry['component_input_commit'],
                          [registry['component_report'], *component_pins.values()])
    component_report = json.loads(components.read(registry['component_report']['path']))
    if component_report['version'] != 'worldatlas-geographic-gap-components-v1':
        raise ValueError('Unexpected component report')
    if component_report['original_evaluation_commit'] != registry['original_geography_evaluation_commit']:
        raise ValueError('Original geography evaluation context differs')
    names = [p['name'] for p in registry['pilots']]
    if len(set(names)) != len(names):
        raise ValueError('Unique pilot names required')
    declared = {f['path']: f for f in component_report['outputs']}
    for name, f in component_pins.items():
        if declared.get(name) != f:
            raise ValueError('Component file is not declared by immutable component report')
    available = {}
    for name, f in component_pins.items():
        raw = decoded_bundle(components.read(name), f)
        for feature in json.loads(raw)['features']:
            if feature['id'] in available:
                raise ValueError('Duplicate component identity')
            available[feature['id']] = feature
    sources = {f['path']: f for f in registry['sources']}
    results = []
    for pilot in registry['pilots']:
        f = available[pilot['component_id']]
        if sha256(canonical_json(f)) != pilot['component_feature_sha256']:
            raise ValueError('Whole original component feature hash mismatch')
        original = shape(f['geometry'])
        sampling = original if pilot['aoi'] is None else original.intersection(box(*pilot['aoi']))
        sampled_feature = {**f, 'geometry': mapping(sampling)}
        records = []
        for name in pilot['source_paths']:
            receipt = sources[name]
            r = monthly_diagnostics(source.read(name), sampled_feature, receipt['source_month'],
                                    pilot['anchor'])
            records.append({**r, 'original_source': receipt})
        results.append({'name': pilot['name'], 'component_id': f['id'],
                        'original_component_feature_sha256': pilot['component_feature_sha256'],
                        'fragment_bindings': f['properties']['fragment_bindings'],
                        'diagnostic_nearby_locations': f['properties']['diagnostic_nearby_locations'],
                        'original_component_bounds': list(original.bounds),
                        'sampling_geometry': mapping(sampling),
                        'sampling_geometry_sha256': sha256(canonical_json(mapping(sampling))),
                        'explicit_pilot_aoi': pilot['aoi'],
                        'full_component_sampled': sampling.equals(original),
                        'records': records, 'comparison': compare_months(records),
                        'administrative_assignment': None,
                        'component_water_status': 'unknown'})
    result = {'version': VERSION, 'status': 'partial-diagnostic-only',
              'input_commit': commit, 'input_registry': pin,
              'component_input_commit': components.commit,
              'original_geography_evaluation_commit': registry['original_geography_evaluation_commit'],
              'source_encoding_inference': registry['scope'],
              'pilots': results, 'references': registry['references'],
              'software': {'rasterio': rasterio.__version__, 'gdal': rasterio.__gdal_version__,
                           'shapely': shapely.__version__, 'geos': shapely.geos_version_string},
              'limits': ['Two sampled months cannot certify annual permanence or historical extent.',
                         'No local geolocation bound or fine-scale water/land classification is certified.',
                         'Native FTP class semantics are inferred from the published monthly-history schema.',
                         'Portugal/Spain pilot covers an explicit small AOI, not its entire connected seam.',
                         'No boundary edit, owner assignment, water waiver, release or deployment.']}
    out = ROOT / safe_path(destination)
    if out.exists() or any(p.is_symlink() for p in [out, *out.parents]):
        raise ValueError('Output must be an unused nonsymlink vintage')
    out.mkdir(parents=True)
    raw = canonical_json(result)
    with (out / 'report.json').open('xb') as f:
        f.write(raw)
    return descriptor(str((out / 'report.json').relative_to(ROOT)), raw)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--commit', required=True)
    p.add_argument('--inputs', required=True)
    p.add_argument('--inputs-bytes', required=True, type=int)
    p.add_argument('--inputs-sha256', required=True)
    p.add_argument('--out', required=True)
    a = p.parse_args()
    print(json.dumps(diagnose(a.commit, a.inputs, a.inputs_bytes, a.inputs_sha256, a.out), sort_keys=True))
