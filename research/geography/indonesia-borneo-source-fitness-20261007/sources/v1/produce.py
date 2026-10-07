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
REPORT_PATH = 'coordination/engineering/global-actionability-routing-20261007/results/report.json'
FAMILY_PART_PATH = 'coordination/engineering/global-actionability-routing-20261007/results/families-007.bin.gz'
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
CURRENT_SCOPE_RECEIPT = 'scope-extraction-current-745cc86a.json'
RESTORE_VINTAGE = 'restore-745cc86a'
RESTORE_ROOT = PACKET / 'vintages' / RESTORE_VINTAGE
RESTORE_RECEIPT = RESTORE_ROOT / 'custody-restoration.json'

sys.path.insert(0, str(REPO / 'scripts'))
from evidence.immutable import Baseline as BootstrapBaseline  # noqa: E402


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def git_bytes(commit: str, path: str) -> bytes:
    return subprocess.check_output(['git', '-C', str(REPO), 'show', f'{commit}:{path}'])


def descriptor(path: str, raw: bytes) -> dict:
    return {'path': path, 'bytes': len(raw), 'sha256': sha(raw), 'hash_kind': 'file-bytes'}


def topological_dimension(geom) -> int:
    if geom.is_empty:
        return -1
    if geom.geom_type in ('Polygon', 'MultiPolygon'):
        return 2
    if geom.geom_type in ('LineString', 'MultiLineString', 'LinearRing'):
        return 1
    if geom.geom_type in ('Point', 'MultiPoint'):
        return 0
    if geom.geom_type == 'GeometryCollection':
        return max((topological_dimension(part) for part in geom.geoms), default=-1)
    raise ValueError('Unexpected topological intersection type: ' + geom.geom_type)


def build(run_name: str) -> dict:
    commit = subprocess.check_output(['git', '-C', str(REPO), 'rev-parse', 'HEAD'], text=True).strip()
    evaluation_commit = subprocess.check_output(
        ['git', '-C', str(REPO), 'merge-base', 'HEAD', 'origin/main'], text=True).strip()
    current_main = subprocess.check_output(
        ['git', '-C', str(REPO), 'rev-parse', 'origin/main'], text=True).strip()
    if evaluation_commit != current_main:
        raise ValueError('Rebase onto current origin/main before producing current-vintage metrics')
    # Pins for every consumed file are derived from immutable custody aliases and
    # the committed source packet. Dynamic raster reads use authenticated bytes.
    index_raw = git_bytes(commit, INDEX_PATH)
    if sha(index_raw) != INDEX_SHA:
        raise ValueError('Custody index whole-file pin changed')
    index = json.loads(index_raw)
    component_aliases = [a for a in index['aliases'] if '/components-v3/components-' in a['original']['path']]
    if len(component_aliases) != 11:
        raise ValueError('Expected the complete 11-shard component-v3 inventory')
    source_vintage_paths = {
        INDEX_PATH, REPORT_PATH, FAMILY_PART_PATH, GEO_PATH,
        'data/geography/part-10.json', 'data/location-policy.json', 'data/world-index.json',
        *[a['payload'] for a in component_aliases],
    }
    for path in source_vintage_paths:
        if git_bytes(commit, path) != git_bytes(evaluation_commit, path):
            raise ValueError('Pinned source input differs from current origin/main: ' + path)
    restore_paths = [RESTORE_RECEIPT.as_posix()] + [
        (RESTORE_ROOT / Path(a['original']['path']).name.removesuffix('.gz')).as_posix()
        for a in component_aliases]
    pin_paths = {
        INDEX_PATH,
        REPORT_PATH,
        FAMILY_PART_PATH,
        GEO_PATH,
        'data/geography/part-10.json',
        'data/location-policy.json',
        'data/world-index.json',
        'scripts/evidence/immutable.py',
        'scripts/evidence/contracts.py',
        (SOURCE / 'produce.py').as_posix(),
        *[a['payload'] for a in component_aliases],
        *restore_paths,
        *[p.as_posix() for p in (SOURCE / CURRENT_SCOPE_RECEIPT, SOURCE / 'scope-extraction.json', SOURCE / 'family-row.json', SOURCE / 'component-roster.txt', SOURCE / 'jrc-source-receipts.json', SOURCE / 'worldcover-whole-tile-receipts.json', SOURCE / 'worldcover-extract-receipts.json', SOURCE / 'README.md', SOURCE / 'metadata-sources.md', SOURCE / 'metadata/occurrence_2024.xml', SOURCE / 'metadata/seasonality_2024.xml', SOURCE / 'metadata/big-2022-ksp-layer.json', SOURCE / 'metadata/big-2023-rbi-layer.json', SOURCE / 'metadata/big-source-receipts.json', SOURCE / 'requirements.txt')],
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
    scope = json.loads(baseline.materialized_bytes((SOURCE / CURRENT_SCOPE_RECEIPT).as_posix()))
    if (scope.get('family_id') != FAMILY or scope.get('component_count') != 45 or
        scope.get('route_report', {}).get('sha256') != '2bf401f76aabc30cb9f0120aba958545146ebf37e304d8817d15eed800fa5265' or
        len(scope.get('family_source_parts', [])) != 14 or
        scope.get('baseline_commit') != evaluation_commit or not all(scope.get('controls', {}).values())):
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
    restoration = json.loads(baseline.materialized_bytes(RESTORE_RECEIPT.as_posix()))
    restoration_rows = {row['custody_payload_path']: row for row in restoration.get('source_shards', [])}
    if (restoration.get('status') != 'complete' or restoration.get('source_commit') != evaluation_commit or
        restoration.get('custody_index', {}).get('sha256') != INDEX_SHA or
        restoration.get('family_row_sha256') != FAMILY_SHA or restoration.get('selected_subject_count') != 45 or
        restoration.get('restored_shard_count') != 11 or len(restoration_rows) != 11):
        raise ValueError('Complete authenticated JSON custody restoration receipt is missing or inconsistent')
    by_id = {}
    source_shards = []
    for alias in component_aliases:
        raw = baseline.pinned_bytes(alias['payload'])
        d = alias['original']
        if len(raw) != d['bytes'] or sha(raw) != d['sha256']:
            raise ValueError('Custody component payload differs from its index alias')
        row = restoration_rows.get(alias['payload'])
        output_path = (RESTORE_ROOT / Path(d['path']).name.removesuffix('.gz')).as_posix()
        decoded = baseline.materialized_bytes(output_path)
        if (row is None or row.get('original_source_path') != d['path'] or
            len(decoded) != d['uncompressed_bytes'] or sha(decoded) != d['uncompressed_sha256'] or
            row.get('decoded_bytes') != len(decoded) or row.get('decoded_sha256') != sha(decoded) or
            row.get('restored_output', {}).get('path') != output_path or
            row.get('restored_output', {}).get('sha256') != sha(decoded)):
            raise ValueError('Restored ordinary JSON bytes do not equal the complete authenticated custody payload')
        source_shards.append({'compressed_path': alias['payload'], 'compressed_bytes': len(raw),
                              'compressed_sha256': sha(raw), 'source_path': d['path'],
                              'decoded_path': output_path, 'uncompressed_bytes': len(decoded),
                              'uncompressed_sha256': sha(decoded)})
        document = json.loads(decoded)
        if document.get('type') != 'FeatureCollection' or not isinstance(document.get('features'), list):
            raise ValueError('Restored custody shard is not a complete JSON FeatureCollection')
        for feature in document['features']:
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

    big22_path = (SOURCE / 'metadata/big-2022-ksp-layer.json').as_posix()
    big23_path = (SOURCE / 'metadata/big-2023-rbi-layer.json').as_posix()
    big22 = json.loads(baseline.materialized_bytes(big22_path))
    big23 = json.loads(baseline.materialized_bytes(big23_path))
    big22_description = big22.get('description', '')
    if (big22.get('geometryType') != 'esriGeometryPolygon' or big22.get('sourceSpatialReference', {}).get('wkid') != 4326 or
        'edisi tahun 2022' not in big22_description or 'kesalahan topologi' not in big22_description or big22.get('copyrightText')):
        raise ValueError('Retained BIG 2022 layer metadata does not support its stated source/terms limits')
    if big23.get('geometryType') != 'esriGeometryPolygon' or big23.get('sourceSpatialReference', {}).get('wkid') != 4326:
        raise ValueError('Retained BIG 2023 layer metadata lacks expected polygon/WKID information')

    intersections = []
    tree = STRtree(admin_geoms)
    source_pair_count = 0
    coordinate_identity_count = 0
    for component_id in sorted(ids):
        component = components[component_id]
        for index_num in tree.query(component, predicate='intersects'):
            admin_index = int(index_num)
            overlay = component.intersection(admin_geoms[admin_index])
            if overlay.is_empty:
                continue
            source_pair_count += 1
            coordinate_identity_count += int(component.equals(admin_geoms[admin_index]))
            intersections.append({
                'type': 'Feature',
                'geometry': mapping(overlay),
            'properties': {
                    'overlay': 'component_x_geoboundaries_2020',
                    'component_id': component_id,
                    'source_feature_id': admin_rows[admin_index]['id'],
                    'source_name': admin_rows[admin_index]['name'],
                    'intersection_dimension': topological_dimension(overlay),
                    'intersection_geometry_type': overlay.geom_type,
                },
            })

    contact_intersections = []
    for component_id in sorted(ids):
        component = components[component_id]
        for feature in atlas_contacts:
            overlay = component.boundary.intersection(shape(feature['geometry']).boundary)
            if overlay.is_empty:
                continue
            contact_intersections.append({
                'type': 'Feature', 'geometry': mapping(overlay),
                'properties': {'overlay': 'component_boundary_x_current_admin_boundary', 'component_id': component_id,
                               'atlas_feature_id': feature['id'], 'atlas_name': feature['properties'].get('name'),
                               'intersection_dimension': topological_dimension(overlay),
                               'intersection_geometry_type': overlay.geom_type},
            })
    contact_summary = []
    for feature in sorted(atlas_contacts, key=lambda f: f['id']):
        rows = [f for f in contact_intersections if f['properties']['atlas_feature_id'] == feature['id']]
        dimensions = [f['properties']['intersection_dimension'] for f in rows]
        contact_summary.append({'atlas_feature_id': feature['id'], 'atlas_name': feature['properties'].get('name'),
                                'component_boundary_contact_rows': len(rows),
                                'max_contact_dimension': max(dimensions, default=-1),
                                'classification': 'positive-length' if max(dimensions, default=-1) == 1 else ('point-only' if max(dimensions, default=-1) == 0 else 'none')})

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
    coverage_rows = contract.exact_rows(raster_histograms, sorted(ids), key='component_id')
    if any(not row['source_rasters'] or any(not item['observed_pixels'] for item in row['source_rasters'])
           for row in coverage_rows.values()):
        raise ValueError('At least one component lacks positive source-raster coverage')
    missing_coverage_rejected = False
    adverse_coverage = [dict(row) for row in raster_histograms]
    adverse_coverage[0] = {**adverse_coverage[0], 'source_rasters': []}
    try:
        if any(not row['source_rasters'] for row in contract.exact_rows(adverse_coverage, sorted(ids), key='component_id').values()):
            raise ValueError('Empty-coverage adverse control rejected')
        raise ValueError('Empty-coverage adverse control unexpectedly passed')
    except ValueError as exc:
        if 'unexpectedly passed' in str(exc): raise
        missing_coverage_rejected = True

    positive = sum(f['properties']['intersection_dimension'] == 2 for f in intersections)
    possible_source_pairs = len(ids) * len(admin_features)
    if (len(intersections) != 51 or positive != 51 or len({f['properties']['component_id'] for f in intersections}) != 45 or
        source_pair_count != 51 or possible_source_pairs != 23355):
        raise ValueError('Expected 51 positive-area source intersections across all 45 components')
    if (len(contact_intersections) != 51 or len({f['properties']['atlas_feature_id'] for f in contact_intersections}) != 8 or
        sum(r['classification'] == 'positive-length' for r in contact_summary) != 7 or
        sum(r['classification'] == 'point-only' for r in contact_summary) != 1 or
        next(r for r in contact_summary if r['atlas_feature_id'] == 'gb:IDN:ADM2:22746128B2679722836886')['classification'] != 'point-only'):
        raise ValueError('Contact overlay omitted an issue-pinned current admin feature')

    component_uncertainty = []
    for component_id in sorted(ids):
        source_ids = sorted({f['properties']['source_feature_id'] for f in intersections
                             if f['properties']['component_id'] == component_id})
        contact_ids = sorted({f['properties']['atlas_feature_id'] for f in contact_intersections
                              if f['properties']['component_id'] == component_id})
        raster_rows = next(row['source_rasters'] for row in raster_histograms if row['component_id'] == component_id)
        component_uncertainty.append({
            'component_id': component_id,
            'geoBoundaries_source_feature_ids_with_positive_area_overlap': source_ids,
            'current_admin_boundary_contact_ids': contact_ids,
            'raster_products_with_observations': [row['raster'] for row in raster_rows],
            'physical_cause': 'unresolved',
            'dry_land_status': 'not established by these sources',
            'territorial_authority': 'unresolved',
            'positional_accuracy': 'not established locally',
            'next_evidence_needed': 'lawfully reusable authoritative BIG/Kemendagri geometry and source-specific local validation; obtain seasonal/field water evidence if physical cause is assessed',
        })

    area_exact = family.get('exact_existing_fragment_area_sum_m2')
    if not isinstance(area_exact, dict) or not {'numerator', 'denominator'}.issubset(area_exact):
        raise ValueError('Pinned family source lacks the exact inherited area-sum rational')
    area_value = int(area_exact['numerator']) / int(area_exact['denominator'])
    if area_value != 1078088489.3853252:
        raise ValueError('Inherited route area sum differs from the issue-pinned displayed value')

    assessment = {
        'version': 1,
        'baseline_commit': commit,
        'upstream_source_commit': evaluation_commit,
        'family_id': FAMILY,
        'family_raw_line_sha256': FAMILY_SHA,
        'scope': {'component_count': len(ids), 'roster_sha256': '88831aad22806bf4f461197a12cb8309bf9a0139e5bd82b967a55e8255ad26ec',
                  'contact_count': len(atlas_contacts), 'contact_ids': sorted(ATLAS_CONTACTS)},
        'routing_source_flags': {'numeric_closure_component_count': family.get('numeric_closure_component_count'),
                                 'numeric_closure_component_ids': sorted(family.get('numeric_closure_component_ids', [])),
                                 'existing_fragment_area_sum_m2': area_value,
                                 'existing_fragment_area_sum_exact': area_exact,
                                 'positive_length_neighbor_ids': sorted(family.get('complete_positive_length_neighbor_ids', [])),
                                 'compatible_original_admin_component_ids': sorted(family.get('compatible_original_admin_component_ids', [])),
                                 'source_fitness_required_compatible_land_component_ids': sorted(family.get('source_fitness_required_compatible_land_component_ids', [])),
                                 'admin_status_counts': family.get('admin_status_counts'),
                                 'positive_length_contact_feature_count': sum(r['classification'] == 'positive-length' for r in contact_summary),
                                 'point_only_contact_feature_count': sum(r['classification'] == 'point-only' for r in contact_summary),
                                 'point_only_contact_feature_ids': sorted(r['atlas_feature_id'] for r in contact_summary if r['classification'] == 'point-only'),
                                 'contact_classification': contact_summary,
                                 'interpretation': 'Inherited source-relative route flags and measurements only; not a new land-area measurement, cause, or authority finding.'},
        'source_join': {'product': 'geoBoundaries IDN ADM2', 'represented_year': 2020,
                        'source_feature_count': len(admin_features), 'unique_source_ids': len(admin_by_id),
                        'component_source_pair_count': possible_source_pairs,
                        'empty_component_source_pairs': possible_source_pairs - source_pair_count,
                        'component_source_intersection_count': len(intersections), 'positive_area_intersection_count': positive,
                        'coordinate_identity_count': coordinate_identity_count,
                        'components_with_positive_area_source_intersection': len({f['properties']['component_id'] for f in intersections}),
                        'exact_geometry_preserved': True, 'repair_or_buffer_used': False,
                        'original_source_sha256': GEO_RAW_SHA, 'compressed_payload_sha256': GEO_GZIP_SHA},
        'big_metadata': {'2022_ksp_layer': {'path': big22_path, **baseline.pins[big22_path],
                                            'geometry_type': big22['geometryType'], 'wkid': big22['sourceSpatialReference']['wkid'],
                                            'edition': '2022; revised December 2022', 'copyright_text': big22.get('copyrightText') or '',
                                            'topology_warning_retained': True},
                         '2023_rbi_layer': {'path': big23_path, **baseline.pins[big23_path],
                                            'geometry_type': big23['geometryType'], 'wkid': big23['sourceSpatialReference']['wkid'],
                                            'copyright_text': big23.get('copyrightText') or ''},
                         'redistribution_license': 'not stated in inspected metadata',
                         'big_geometry_downloaded_or_used': False},
        'raster_observation_method': 'Per-component all_touched pixel value histograms from pinned source rasters/crops; nodata excluded; counts are observations, not land-condition conclusions.',
        'raster_component_observation_count': len(raster_histograms),
        'raster_observations': raster_histograms,
        'per_component_uncertainty': component_uncertainty,
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
    all_features = component_features + contact_features + intersections + contact_intersections
    generated_ids = [f['properties']['component_id'] for f in component_features]
    contract.exact_rows([{'id': identity} for identity in generated_ids], sorted(ids))
    missing_output_rejected = False
    try:
        contract.exact_rows([{'id': identity} for identity in generated_ids[1:]], sorted(ids))
        raise ValueError('Generated-output completeness adverse control unexpectedly passed')
    except ValueError as exc:
        if 'unexpectedly passed' in str(exc): raise
        missing_output_rejected = True
    outputs = {
        'assessment.json.gz': deterministic_gzip(canonical_json(assessment)),
        'intersections.geojson.gz': deterministic_gzip(canonical_json({'type': 'FeatureCollection', 'features': all_features})),
        'positive-control.json': canonical_json({'method_id': 'source-fitness-generation', 'kind': 'positive-control', 'outcome': 'passed',
                                  'selected_components': len(ids), 'custody_joined_components': len(by_id),
                                  'source_features': len(admin_features), 'positive_area_intersections': positive,
                                  'current_contact_features': len(atlas_contacts), 'source_covered_components': len(coverage_rows),
                                  'generated_component_features': len(generated_ids)}),
        'negative-control.json': canonical_json({'method_id': 'source-fitness-generation', 'kind': 'negative-control', 'outcome': 'passed',
                                  'missing_identity_rejected': True, 'duplicate_identity_rejected': True,
                                  'fabricated_identity_rejected': True, 'missing_raster_coverage_rejected': missing_coverage_rejected,
                                  'missing_generated_component_rejected': missing_output_rejected,
                                  'method': 'Exact identity/coverage checks applied to actual source and generated records'}),
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
