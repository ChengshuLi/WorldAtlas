#!/usr/bin/env python3
"""Fetch a bounded JUPEM/MYGOS query in memory and emit non-authoritative diagnostics only."""
import argparse
import gzip
import hashlib
import json
import pathlib
import sys
import urllib.parse
import urllib.request

from shapely.geometry import shape
from shapely.ops import unary_union
from shapely.validation import explain_validity

ROOT = pathlib.Path(__file__).resolve().parents[3]
OWNED = 'research/geography/malaysia-terengganu-gap-source-fitness-20261007'
CONFIG = OWNED + '/input-config.json'
CUSTODY = 'coordination/engineering/physical-gap-components-1005-20261005-local19/custody-v1/index.json'
COMPONENT_PREFIX = 'coordination/engineering/physical-gap-components-1005-20261005-local19/components-v3/components-'
URL = 'https://mygos.mygeoportal.gov.my/gisserver/rest/services/MyGeomap/Msia_Coverage/MapServer/2/query'
PARAMS = {
    'where': "KOD_NEGERI='11'",
    'outFields': 'OBJECTID,NAM,KOD_DAERAH,ARM,BA5,PPM,Sumber,Tahun_Kemaskini,Tahun_Terima',
    'returnGeometry': 'true', 'outSR': '4326', 'f': 'geojson',
}
EXPECTED_COMPONENTS = [
    'physical-component:46a2537871d6055d90416c1508d40805648567d8dfc37696192a8a23d778922b',
    'physical-component:4dbe3afea3880fac1e82de705149e196aa6ad6930a0e0d4b740059fa75d401b2',
    'physical-component:6233f6efda804999c5d871acf8fca60daf4742a13f5001a69fba6f15b375f9b6',
    'physical-component:8bb9857dc07c70b27c9b4ed6a55fe70af5b322a293423aa1879d1d4e994c8c3f',
    'physical-component:96632d82d1eb09e9410028d0259535bf712f6005d821777f3b3d65e3941eb9ff',
    'physical-component:a5dbeb12c0625bb589edcafb5bc44d9953f36980565865e2032c4888221733e9',
    'physical-component:e9dd7858cb946a4779d6c2079ddd9876cb953d0406101094a428b10d602c70d5',
    'physical-component:f181e43671a67d0313075212a5b10c5c9d086541a044284eb3d7ff70f097fb62',
]


def canonical(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


def run(output_path):
    config = json.loads((ROOT / CONFIG).read_text())
    sys.path.insert(0, str(ROOT / 'scripts'))
    from evidence.immutable import Baseline
    baseline = Baseline(ROOT, config['baseline']['commit'], config['baseline']['files'])
    custody = json.loads(baseline.pinned_bytes(CUSTODY))
    alias_rows = {row['original']['path']: row for row in custody['aliases']}
    components = {}
    for path, alias in alias_rows.items():
        if not path.startswith(COMPONENT_PREFIX):
            continue
        raw = baseline.pinned_bytes(alias['payload'])
        features = json.loads(gzip.decompress(raw)).get('features', [])
        for feature in features:
            if feature.get('id') in EXPECTED_COMPONENTS:
                components[feature['id']] = shape(feature['geometry'])
    if set(components) != set(EXPECTED_COMPONENTS):
        raise ValueError('Incomplete pinned component geometry roster')

    request_url = URL + '?' + urllib.parse.urlencode(PARAMS)
    request = urllib.request.Request(request_url, headers={'User-Agent': 'WorldAtlas source-fitness review'})
    raw = urllib.request.urlopen(request, timeout=60).read()
    response = json.loads(raw)
    if len(response.get('features', [])) != 8:
        raise ValueError('The pinned query did not return all eight Terengganu districts')
    district_rows = []
    district_shapes = []
    district_validity = []
    valid_rows = []
    valid_shapes = []
    for feature in response['features']:
        properties = feature['properties']
        geometry = shape(feature['geometry'])
        district_rows.append((properties, geometry))
        district_shapes.append(geometry)
        valid = geometry.is_valid
        district_validity.append({
            'name': properties.get('NAM'),
            'district_code': properties.get('KOD_DAERAH'),
            'valid': bool(valid),
            'reason': None if valid else explain_validity(geometry),
        })
        if valid:
            valid_rows.append((properties, geometry))
            valid_shapes.append(geometry)
    union = unary_union(valid_shapes) if valid_shapes else None
    component_rows = []
    for component_id in EXPECTED_COMPONENTS:
        geom = components[component_id]
        intersections = []
        for properties, district in district_rows:
            valid = district.is_valid
            try:
                touches = bool(geom.intersects(district))
            except Exception as error:
                touches = None
                predicate_error = type(error).__name__
            else:
                predicate_error = None
            if touches:
                intersections.append({
                    'name': properties.get('NAM'),
                    'district_code': properties.get('KOD_DAERAH'),
                    'source': properties.get('Sumber'),
                    'update_field': properties.get('Tahun_Kemaskini'),
                    'receipt_field': properties.get('Tahun_Terima'),
                    'ppm': properties.get('PPM'),
                    'input_geometry_valid': bool(valid),
                    'positive_coordinate_plane_intersection': geom.intersection(district).area > 0 if valid else None,
                    'invalid_geometry_diagnostic': not valid,
                })
            elif predicate_error:
                intersections.append({
                    'name': properties.get('NAM'),
                    'district_code': properties.get('KOD_DAERAH'),
                    'input_geometry_valid': bool(valid),
                    'predicate_error': predicate_error,
                })
        component_rows.append({
            'component_id': component_id,
            'intersecting_districts': intersections,
            'covered_by_valid_district_subset_union_in_requested_output_coordinates': bool(union.covers(geom)) if union is not None else None,
            'complete_eight_district_coverage_assessed': len(valid_rows) == len(district_rows),
        })
    result = {
        'version': 1,
        'source': {
            'url': URL,
            'parameters': PARAMS,
            'returned_geojson_bytes': len(raw),
            'returned_geojson_sha256': hashlib.sha256(raw).hexdigest(),
            'retrieval_date': '2026-10-07',
            'feature_count': len(response['features']),
            'district_geometry_validity': district_validity,
            'output_crs_request': 'EPSG:4326',
            'native_layer_wkid_reported_elsewhere': 4742,
            'service_description_conflict': 'Service description calls its coordinate system projected GDMRSO; layer reports WKID 4742 (GDM2000 geographic). The output service applied an unspecified transformation to requested EPSG:4326.',
            'reuse_status': 'unknown; layer PPM is null and MyGDI provider agreement applies; response bytes are not retained here',
        },
        'components': component_rows,
        'limits': [
            'Live endpoint response bytes were used in memory but are not redistributed; the digest can detect a later response change but cannot restore the original source bytes.',
            'No datum transformation was pinned; predicates are source-relative coordinate diagnostics only.',
            'A public service response is not legal authority, evidence of dry land/water, ownership, or a boundary accuracy statement.',
        ],
    }
    out = ROOT / output_path
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(canonical(result))
    return result

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    if not args.output.startswith(OWNED + '/mygos-runs/'):
        raise SystemExit('Output must remain under this packet mygos-runs directory')
    run(args.output)
