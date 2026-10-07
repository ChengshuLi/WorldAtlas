#!/usr/bin/env python3
"""Generate bounded source-relative Borneo component/admin/raster evidence."""
from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
from rasterio.io import MemoryFile
from rasterio.mask import mask
from shapely.geometry import mapping, shape
from shapely.strtree import STRtree

REPO = Path(__file__).resolve().parents[5]
PACKET = Path('research/geography/indonesia-borneo-source-fitness-20261007')
SOURCE = PACKET / 'sources/v1'
FAMILY = 'gap-source-batch:8875fd920e43656b5f36e704'
FAMILY_SHA = 'a08249214711d84d7d220a61fe10f2d4582e7bc64f1a5ae811436ddaf22d94b3'
INDEX_PATH = 'coordination/engineering/physical-gap-components-1005-20261005-local19/custody-v1/index.json'
INDEX_SHA = 'dfcca9fe2bb64805b94e784be89b3523f5683b95cbd4a617283965ca6187a77c'
GEO_PATH = 'coordination/engineering/original-geography-source-corpus-20261006/payloads/gb-IDN-ADM2-000.bin.gz'
GEO_GZIP_SHA = 'ef394916ba97454b5592e66eba1df67199731ce7d9636cc3968843801ae904a8'
GEO_RAW_SHA = '146653d488331086ddc43d159a261b01ea6dd08c7ed422e34a9886c3c690430c'
ATLAS_CONTACTS = {
    'gb:IDN:ADM2:22746128B34069275840087',
    'gb:IDN:ADM2:22746128B66626446070966',
    'gb:IDN:ADM2:22746128B2679722836886',
    'gb:IDN:ADM2:22746128B87893249930832',
    'gb:IDN:ADM2:22746128B55621143702768',
    'gb:IDN:ADM2:22746128B75924443266043',
    'gb:IDN:ADM2:22746128B17746000623405',
    'gb:IDN:ADM2:22746128B96540112180119',
}
RUN_ONE = 'run-five'

sys.path.insert(0, str(REPO / 'scripts'))
from evidence.immutable import Baseline as BootstrapBaseline  # noqa: E402


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def git_bytes(commit: str, path: str) -> bytes:
    return subprocess.check_output(['git', '-C', str(REPO), 'show', f'{commit}:{path}'])


def descriptor(path: str, raw: bytes) -> dict:
    return {'path': path, 'bytes': len(raw), 'sha256': sha(raw), 'hash_kind': 'file-bytes'}


def build(run_name: str) -> dict:
    commit = subprocess.check_output(['git', '-C', str(REPO), 'rev-parse', 'HEAD'], text=True).strip()
    # Pins for every consumed file are derived from immutable custody aliases and
    # the committed source packet. Dynamic raster reads use authenticated bytes.
    index_raw = git_bytes(commit, INDEX_PATH)
    if sha(index_raw) != INDEX_SHA:
        raise ValueError('Custody index whole-file pin changed')
    index = json.loads(index_raw)
    component_aliases = [a for a in index['aliases'] if '/components-v3/components-' in a['original']['path']]
    if len(component_aliases) != 11:
        raise ValueError('Expected the complete 11-shard component-v3 inventory')
    pin_paths = {
        INDEX_PATH,
        GEO_PATH,
        'data/geography/part-10.json',
        'scripts/evidence/immutable.py',
        'scripts/evidence/contracts.py',
        (SOURCE / 'produce.py').as_posix(),
        *[a['payload'] for a in component_aliases],
        *[p.as_posix() for p in (SOURCE / 'scope-extraction.json', SOURCE / 'family-row.json', SOURCE / 'component-roster.txt', SOURCE / 'jrc-source-receipts.json', SOURCE / 'worldcover-whole-tile-receipts.json', SOURCE / 'worldcover-extract-receipts.json', SOURCE / 'README.md', SOURCE / 'metadata-sources.md', SOURCE / 'metadata/occurrence_2024.xml', SOURCE / 'metadata/seasonality_2024.xml', SOURCE / 'requirements.txt')],
        *[p.as_posix() for p in sorted((SOURCE / 'worldcover').glob('*.tif'))],
        *[p.as_posix() for p in sorted((SOURCE / 'worldcover-crops').glob('*.tif'))],
        *[p.as_posix() for p in sorted((SOURCE / 'jrc-crops').glob('*.tif'))],
    }
    pins = [descriptor(path, git_bytes(commit, path)) for path in sorted(pin_paths)]
    bootstrap = BootstrapBaseline(REPO, commit, pins)
    modules = bootstrap.load_modules({
        'evidence.immutable': 'scripts/evidence/immutable.py',
        'evidence.contracts': 'scripts/evidence/contracts.py',
    })
    Baseline = modules['evidence.immutable'].Baseline
    NewVintage = modules['evidence.immutable'].NewVintage
    canonical_json = modules['evidence.immutable'].canonical_json
    deterministic_gzip = modules['evidence.immutable'].deterministic_gzip
    contract = modules['evidence.contracts']
    baseline = Baseline(REPO, commit, pins)
    if baseline.materialized_bytes((SOURCE / 'produce.py').as_posix()) != Path(__file__).read_bytes():
        raise ValueError('Executed producer differs from the authenticated baseline code')
    dest = NewVintage(baseline, PACKET.as_posix() + '/', run_name,
                      ['assessment.json.gz', 'intersections.geojson.gz', 'positive-control.json', 'negative-control.json'])

    # The family row and roster were independently extracted and retained by the
    # source-stage extractor against all 14 pinned routing chunks.
    scope = json.loads(baseline.materialized_bytes((SOURCE / 'scope-extraction.json').as_posix()))
    if (scope.get('family_id') != FAMILY or scope.get('component_count') != 45 or
        scope.get('route_report', {}).get('sha256') != '2bf401f76aabc30cb9f0120aba958545146ebf37e304d8817d15eed800fa5265' or
        len(scope.get('family_source_parts', [])) != 14 or
        not all(scope.get('controls', {}).values())):
        raise ValueError('Retained route-family extraction receipt is incomplete or failed')
    family_raw = baseline.materialized_bytes((SOURCE / 'family-row.json').as_posix())
    if sha(family_raw.rstrip(b'\n')) != FAMILY_SHA:
        raise ValueError('Pinned original family line hash changed')
    if scope.get('family_row', {}).get('sha256') != FAMILY_SHA:
        raise ValueError('Route-family extraction receipt does not bind the retained row')
    family = json.loads(family_raw)
    ids = family['complete_component_ids']
    if family.get('id') != FAMILY or family.get('component_count') != 45 or len(ids) != 45 or len(set(ids)) != 45:
        raise ValueError('Selected family must contain exactly 45 unique component IDs')
    roster = baseline.materialized_bytes((SOURCE / 'component-roster.txt').as_posix()).decode().splitlines()
    if sorted(ids) != roster or len(roster) != 45 or len(set(roster)) != 45:
        raise ValueError('Exact roster/source-row join failed')

    index = json.loads(baseline.pinned_bytes(INDEX_PATH))
    component_aliases = [a for a in index['aliases'] if '/components-v3/components-' in a['original']['path']]
    by_id = {}
    source_shards = []
    for alias in component_aliases:
        raw = baseline.pinned_bytes(alias['payload'])
        d = alias['original']
        if len(raw) != d['bytes'] or sha(raw) != d['sha256']:
            raise ValueError('Custody component payload differs from its index alias')
        decoded = gzip.decompress(raw)
        baseline.admit(alias['payload'] + ':decoded', len(decoded))
        if len(decoded) != d['uncompressed_bytes'] or sha(decoded) != d['uncompressed_sha256']:
            raise ValueError('Decoded custody component shard differs from its index alias')
        source_shards.append({'path': d['path'], 'bytes': d['bytes'], 'sha256': d['sha256'], 'uncompressed_bytes': len(decoded), 'uncompressed_sha256': sha(decoded)})
        for feature in json.loads(decoded)['features']:
            identity = feature.get('id')
            if identity in ids:
                if identity in by_id:
                    raise ValueError('Duplicate selected component in custody shards')
                by_id[identity] = feature
    actual = contract.exact_rows([{'id': i} for i in sorted(by_id)], sorted(ids))
    if set(actual) != set(ids):
        raise ValueError('Custody join did not bind all selected identities')
    # Adverse identity controls use actual selected source rows.
    try:
        contract.exact_rows([{'id': i} for i in sorted(by_id)][:-1], sorted(ids))
        raise ValueError('Missing-identity adverse control unexpectedly passed')
    except ValueError as exc:
        if 'unexpectedly passed' in str(exc): raise
    try:
        contract.exact_rows([{'id': i} for i in sorted(by_id)] + [{'id': sorted(ids)[0]}], sorted(ids))
        raise ValueError('Duplicate-identity adverse control unexpectedly passed')
    except ValueError as exc:
        if 'unexpectedly passed' in str(exc): raise
    try:
        contract.exact_rows([{'id': i} for i in sorted(by_id)] + [{'id': 'fabricated-component'}], sorted(ids))
        raise ValueError('Fabricated-identity adverse control unexpectedly passed')
    except ValueError as exc:
        if 'unexpectedly passed' in str(exc): raise

    components = {identity: shape(by_id[identity]['geometry']) for identity in ids}
    if any(g.is_empty or not g.is_valid or g.geom_type not in ('Polygon', 'MultiPolygon') for g in components.values()):
        raise ValueError('Original source geometry invalid; no repair or buffering is allowed')
    part10 = json.loads(baseline.materialized_bytes('data/geography/part-10.json'))['features']
    if len(part10) != 1500:
        raise ValueError('Unexpected pinned current-admin reference inventory')
    atlas_contacts = [f for f in part10 if any(components[i].intersects(shape(f['geometry'])) for i in ids)]
    if {f['id'] for f in atlas_contacts} != ATLAS_CONTACTS or len(atlas_contacts) != 8:
        raise ValueError('Current Atlas contact set differs from exact issue-pinned contact inventory')

    geo_gzip = baseline.pinned_bytes(GEO_PATH)
    if sha(geo_gzip) != GEO_GZIP_SHA:
        raise ValueError('geoBoundaries compressed source pin changed')
    geo_raw = gzip.decompress(geo_gzip)
    baseline.admit(GEO_PATH + ':decoded', len(geo_raw))
    if sha(geo_raw) != GEO_RAW_SHA:
        raise ValueError('geoBoundaries raw source content pin changed')
    admin_features = json.loads(geo_raw)['features']
    admin_rows = []
    admin_geoms = []
    for feature in admin_features:
        props = feature['properties']
        identity = props.get('shapeID')
        if not identity:
            raise ValueError('Missing geoBoundaries source identity')
        admin_rows.append({'id': identity, 'name': props.get('shapeName')})
        admin_geoms.append(shape(feature['geometry']))
    admin_by_id = contract.exact_rows(admin_rows, [r['id'] for r in admin_rows])
    if len(admin_features) != 519:
        raise ValueError('Expected complete 519-feature source product')

    intersections = []
    tree = STRtree(admin_geoms)
    for component_id in sorted(ids):
        component = components[component_id]
        for index_num in tree.query(component, predicate='intersects'):
            admin_index = int(index_num)
            overlay = component.intersection(admin_geoms[admin_index])
            if overlay.is_empty:
                continue
            intersections.append({
                'type': 'Feature',
                'geometry': mapping(overlay),
                'properties': {
                    'overlay': 'component_x_geoboundaries_2020',
                    'component_id': component_id,
                    'source_feature_id': admin_rows[admin_index]['id'],
                    'source_name': admin_rows[admin_index]['name'],
                    'intersection_dimension': 2 if overlay.area > 0 else (1 if overlay.geom_type in ('LineString', 'MultiLineString') else 0),
                    'intersection_geometry_type': overlay.geom_type,
                },
            })

    contact_intersections = []
    for component_id in sorted(ids):
        component = components[component_id]
        for feature in atlas_contacts:
            overlay = component.intersection(shape(feature['geometry']))
            if overlay.is_empty:
                continue
            contact_intersections.append({
                'type': 'Feature', 'geometry': mapping(overlay),
                'properties': {'overlay': 'component_x_current_atlas_admin', 'component_id': component_id,
                               'atlas_feature_id': feature['id'], 'atlas_name': feature['properties'].get('name'),
                               'intersection_dimension': 2 if overlay.area > 0 else (1 if overlay.geom_type in ('LineString', 'MultiLineString') else 0),
                               'intersection_geometry_type': overlay.geom_type},
            })

    # Raster source files are opened from the exact bytes authenticated above.
    raster_paths = sorted(p for p in pin_paths if p.endswith('.tif'))
    rasters = []
    for path in raster_paths:
        raw = baseline.materialized_bytes(path)
        with MemoryFile(raw) as mem, mem.open() as ds:
            rasters.append((path.rsplit('/', 1)[-1], ds.crs.to_string(), ds.nodata, tuple(ds.bounds), raw))
    raster_histograms = []
    for component_id in sorted(ids):
        geom = components[component_id]
        observations = []
        for name, crs, nodata, bounds, raw in rasters:
            from shapely.geometry import box
            if not geom.intersects(box(*bounds)):
                continue
            with MemoryFile(raw) as mem, mem.open() as ds:
                masked, _ = mask(ds, [mapping(geom)], crop=True, all_touched=True, filled=False)
                vals, counts = np.unique(masked.compressed(), return_counts=True)
                hist = {str(int(v)): int(n) for v, n in zip(vals, counts) if nodata is None or int(v) != int(nodata)}
                if hist:
                    observations.append({'raster': name, 'native_crs': crs, 'all_touched_pixel_counts_by_value': hist,
                                         'observed_pixels': sum(hist.values()), 'nodata_excluded': nodata})
        raster_histograms.append({'component_id': component_id, 'source_rasters': observations})
    if len(raster_histograms) != 45 or any(not row['source_rasters'] for row in raster_histograms):
        raise ValueError('At least one component lacks a retained source-raster observation')

    positive = sum(f['properties']['intersection_dimension'] == 2 for f in intersections)
    if len(intersections) != 51 or positive != 51 or len({f['properties']['component_id'] for f in intersections}) != 45:
        raise ValueError('Expected 51 positive-area source intersections across all 45 components')
    if not contact_intersections or len({f['properties']['atlas_feature_id'] for f in contact_intersections}) != 8:
        raise ValueError('Contact overlay omitted an issue-pinned current admin feature')

    assessment = {
        'version': 1,
        'baseline_commit': commit,
        'family_id': FAMILY,
        'family_raw_line_sha256': FAMILY_SHA,
        'scope': {'component_count': len(ids), 'roster_sha256': '88831aad22806bf4f461197a12cb8309bf9a0139e5bd82b967a55e8255ad26ec',
                  'contact_count': len(atlas_contacts), 'contact_ids': sorted(ATLAS_CONTACTS)},
        'routing_source_flags': {'numeric_closure_component_count': family.get('numeric_closure_component_count'),
                                 'numeric_closure_component_ids': sorted(family.get('numeric_closure_component_ids', [])),
                                 'interpretation': 'Inherited source-relative route flags only; not a new land-area measurement, cause, or authority finding.'},
        'source_join': {'product': 'geoBoundaries IDN ADM2', 'represented_year': 2020,
                        'source_feature_count': len(admin_features), 'unique_source_ids': len(admin_by_id),
                        'component_source_intersection_count': len(intersections), 'positive_area_intersection_count': positive,
                        'components_with_positive_area_source_intersection': len({f['properties']['component_id'] for f in intersections}),
                        'exact_geometry_preserved': True, 'repair_or_buffer_used': False,
                        'original_source_sha256': GEO_RAW_SHA, 'compressed_payload_sha256': GEO_GZIP_SHA},
        'raster_observation_method': 'Per-component all_touched pixel value histograms from pinned source rasters/crops; nodata excluded; counts are observations, not land-condition conclusions.',
        'raster_observations': raster_histograms,
        'source_shards': source_shards,
        'controls': {'exact_45_roster_join': 'passed', 'missing_identity_rejected': 'passed',
                     'duplicate_identity_rejected': 'passed', 'fabricated_identity_rejected': 'passed',
                     'all_45_have_source_overlay': 'passed', 'all_45_have_raster_observations': 'passed'},
        'limitations': [
            'This is source fitness and geometric correspondence evidence; it is not legal authority, positional accuracy, or boundary approval.',
            'ESA WorldCover class values are not locally validated; global accuracy is not a local estimate.',
            'JRC mapped open-water presence and non-detection do not establish dry land; observation and classification limits remain.',
            'JRC Seasonality XML and provider page disagree on temporal coverage; reported conservatively as the 2024 product.',
            'BIG geometry reuse remains unresolved because no open redistribution license or retained source response was established.',
            'All 21 numeric closure-component flags remain source-relative and unresolved; no cause is assigned.',
        ],
        'authority_disposition': 'not-requested',
        'source_approval': False,
    }
    component_features = [{'type': 'Feature', 'geometry': mapping(components[i]),
                           'properties': {'role': 'original_pinned_component', 'component_id': i}}
                          for i in sorted(ids)]
    contact_features = [{'type': 'Feature', 'geometry': f['geometry'],
                         'properties': {'role': 'current_atlas_admin_contact', 'atlas_feature_id': f['id'],
                                        'atlas_name': f['properties'].get('name')}} for f in atlas_contacts]
    outputs = {
        'assessment.json.gz': deterministic_gzip(canonical_json(assessment)),
        'intersections.geojson.gz': deterministic_gzip(canonical_json({'type': 'FeatureCollection', 'features': component_features + contact_features + intersections + contact_intersections})),
        'positive-control.json': canonical_json({'method_id': 'source-fitness-generation', 'kind': 'positive-control', 'outcome': 'passed',
                                  'selected_components': len(ids), 'custody_joined_components': len(by_id),
                                  'source_features': len(admin_features), 'positive_area_intersections': positive,
                                  'current_contact_features': len(atlas_contacts)}),
        'negative-control.json': canonical_json({'method_id': 'source-fitness-generation', 'kind': 'negative-control', 'outcome': 'passed',
                                  'missing_identity_rejected': True, 'duplicate_identity_rejected': True,
                                  'fabricated_identity_rejected': True, 'method': 'exact_rows applied to actual source records'}),
    }
    records = dest.publish_bytes(outputs)
    return {'run': run_name, 'records': records, 'intersections': len(intersections), 'contacts': len(contact_intersections),
            'raster_components': len(raster_histograms), 'input_bytes': sum(baseline.consumed.values())}


def compare_runs(run_one: str, run_two: str, run_name: str) -> dict:
    commit = subprocess.check_output(['git', '-C', str(REPO), 'rev-parse', 'HEAD'], text=True).strip()
    code_path = (SOURCE / 'produce.py').as_posix()
    helper_path = 'scripts/evidence/immutable.py'
    pins = [descriptor(code_path, git_bytes(commit, code_path)), descriptor(helper_path, git_bytes(commit, helper_path))]
    bootstrap = BootstrapBaseline(REPO, commit, pins)
    module = bootstrap.load_modules({'evidence.immutable': helper_path})['evidence.immutable']
    baseline = module.Baseline(REPO, commit, pins)
    if baseline.materialized_bytes(code_path) != Path(__file__).read_bytes():
        raise ValueError('Executed comparison producer differs from the authenticated baseline code')
    names = ['assessment.json.gz', 'intersections.geojson.gz', 'positive-control.json', 'negative-control.json']
    root = REPO / PACKET
    hashes = []
    for run in (run_one, run_two):
        aggregate = hashlib.sha256()
        for name in names:
            raw = (root / 'vintages' / run / name).read_bytes()
            aggregate.update(name.encode() + b'\0' + raw)
        hashes.append(aggregate.hexdigest())
    if hashes[0] != hashes[1]:
        raise ValueError('Two complete source-fitness runs differ byte-for-byte')
    dest = module.NewVintage(baseline, PACKET.as_posix() + '/', run_name, ['reproducibility.json'])
    value = {'method_id': 'source-fitness-generation', 'kind': 'reproducibility', 'outcome': 'passed',
             'run_one': run_one, 'run_two': run_two, 'run_one_sha256': hashes[0], 'run_two_sha256': hashes[1],
             'output_files_compared': names}
    return {'run': run_name, 'records': dest.publish({'reproducibility.json': value}), 'sha256': hashes[0]}


if __name__ == '__main__':
    run = sys.argv[1] if len(sys.argv) > 1 else RUN_ONE
    if run == 'compare':
        args = sys.argv[2:]
        print(json.dumps(compare_runs(args[0], args[1], args[2]), sort_keys=True))
    else:
        print(json.dumps(build(run), sort_keys=True))
