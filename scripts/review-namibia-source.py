"""Exhaustive Namibia reference-source audit; never mutate atlas geometry or records.

The downloadable COD source is a licensed, coherent former-107 framework, not
proof of today's 121 constituencies. Source errors and temporal successions are
kept separate and no correspondence authorizes historical attribute transfer.
"""
import argparse
import collections
import gzip
import hashlib
import json
import pathlib
import re
import struct
import unicodedata

from shapely import make_valid, union_all
from shapely.geometry import shape
from shapely.validation import explain_validity
from ellipsoidal_area import area

ROOT = pathlib.Path(__file__).resolve().parents[1]
CACHE = ROOT / '.cache/namibia-source-review'


def load(path):
    return json.load(gzip.open(path, 'rt') if str(path).endswith('.gz') else open(path))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def key(name):
    return re.sub('[^a-z0-9]', '', unicodedata.normalize('NFKD', name).lower())


def original_shapefile_rows():
    """Independently check upstream SHP/DBF row joins without a conversion library."""
    dbf = (CACHE / 'NAM.dbf').read_bytes()
    count, header, length = struct.unpack_from('<IHH', dbf, 4)
    fields, offset = [], 32
    while dbf[offset] != 13:
        fields.append((dbf[offset:offset + 11].split(b'\0')[0].decode(), dbf[offset + 16]))
        offset += 32
    data, offset, rows = (CACHE / 'NAM.shp').read_bytes(), 100, []
    while offset < len(data):
        number, words = struct.unpack_from('>ii', data, offset)
        body = data[offset + 8:offset + 8 + words * 2]
        record = dbf[header + len(rows) * length:header + (len(rows) + 1) * length]
        values, position = {}, 1
        for name, width in fields:
            values[name] = record[position:position + width].decode('latin1').strip()
            position += width
        rows.append({'row': number, 'name': values['ADM2'],
                     'region': values['ADM1'], 'bbox': list(struct.unpack_from('<dddd', body, 4))})
        offset += 8 + words * 2
    assert len(rows) == count == 109, 'Original source count changed; reassess source audit'
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='data/namibia-source-review.json.gz')
    args = parser.parse_args()
    metadata = load(CACHE / 'hdx.txt')['result']
    assert metadata['license_id'] == 'cc-by-igo'
    assert 'former 107 constituency' in metadata['caveats']
    index = load(ROOT / 'data/world-index.json')
    current = [f for part in index['parts'] for f in load(ROOT / 'data' / part)['features']
               if f['properties']['reference_owner'] == 'Namibia']
    source = load(CACHE / 'hdx/nam_admin2.geojson')['features']
    regions = load(CACHE / 'hdx/nam_admin1.geojson')['features']
    country = shape(load(CACHE / 'hdx/nam_admin0.geojson')['features'][0]['geometry'])
    assert len(current) == 111 and len(source) == 107 and len(regions) == 14
    assert len({f['properties']['id'] for f in current}) == 111
    assert len({f['properties']['adm2_pcode'] for f in source}) == 107
    geoms = [make_valid(shape(f['geometry'])) for f in source]
    atlas_geoms = [make_valid(shape(f['geometry'])) for f in current]
    source_union, atlas_union = union_all(geoms), union_all(atlas_geoms)
    source_total, atlas_total = area(source_union), area(atlas_union)
    region_geoms = {f['properties']['adm1_pcode']: make_valid(shape(f['geometry'])) for f in regions}
    original_rows = original_shapefile_rows()
    raw = load(ROOT / '.cache/geoboundaries/NAM-ADM2.json')['features']
    # The original binary records and the gbOpen derivative retain the same
    # erroneous joins. This independently rules out our GeoJSON loader.
    upstream = []
    for row, feature in zip(original_rows, raw):
        bounds = shape(feature['geometry']).bounds
        assert row['name'] == feature['properties']['shapeName']
        row['gb_derivative_bbox_max_difference_degrees'] = max(abs(x - y) for x, y in zip(row['bbox'], bounds))
        # gbOpen simplifies the source; this tolerance verifies the same
        # footprint context, not byte-identical coordinates.
        assert row['gb_derivative_bbox_max_difference_degrees'] < .001
        upstream.append(row)
    old_rows, new_rows, positive_pairs = [], [], []
    for i, f in enumerate(current):
        g, p, overlaps = atlas_geoms[i], f['properties'], []
        own_area = area(g)
        for j, h in enumerate(geoms):
            if not g.intersects(h):
                continue
            value = area(g.intersection(h))
            if value > 0:
                q = source[j]['properties']
                pair = {'old_id': p['id'], 'source_code': q['adm2_pcode'],
                        'source_name': q['adm2_name'], 'intersection_km2': value / 1e6,
                        'old_land_share': value / own_area, 'source_land_share': value / area(h)}
                positive_pairs.append(pair)
                overlaps.append(pair)
        overlaps.sort(key=lambda r: -r['intersection_km2'])
        exact_named = [q['properties']['adm2_pcode'] for q in source
                       if key(p['name'].split(' · ')[0]) == key(q['properties']['adm2_name'])]
        old_rows.append({'id': p['id'], 'name': p['name'], 'parent_id': p['parent_id'],
                         'area_km2': own_area / 1e6, 'point': list(g.representative_point().coords)[0],
                         'source_metadata': p['metadata'], 'top_spatial_matches': overlaps[:5],
                         'same_normalized_name_codes': exact_named,
                         'name_matches_spatial_winner': bool(overlaps) and
                         key(p['name'].split(' · ')[0]) == key(overlaps[0]['source_name']),
                         'decision': 'Archive original identity and geometry; replacement correspondence is evidence, not an automatic record transfer.'})
    for j, f in enumerate(source):
        g, p = geoms[j], f['properties']
        parent = region_geoms[p['adm1_pcode']]
        matches = sorted([r for r in positive_pairs if r['source_code'] == p['adm2_pcode']],
                         key=lambda r: -r['intersection_km2'])
        new_rows.append({'proposed_id': 'hdx:NAM:ADM2:' + p['adm2_pcode'],
                         'code': p['adm2_pcode'], 'name': p['adm2_name'],
                         'parent_code': p['adm1_pcode'], 'parent_name': p['adm1_name'],
                         'area_km2': area(g) / 1e6, 'valid_geometry': shape(f['geometry']).is_valid,
                         'validity_reason': explain_validity(shape(f['geometry'])),
                         'repair': 'None' if shape(f['geometry']).is_valid else
                         'Shapely make_valid: ring self-intersection repaired; preserves polygon type and WGS84 area to numerical precision.',
                         'parent_containment_share': area(g.intersection(parent)) / area(g),
                         'current_coverage_share': area(g.intersection(atlas_union)) / area(g),
                         'old_correspondences': matches,
                         'evidence': {'valid_on': p['valid_on'], 'version': p['version'],
                                      'framework_vintage': 'Former 107 constituency framework, boundary creation/edit 2011; regional names/partition updated separately.'}})
    pairs_overlap = []
    for i, a in enumerate(geoms):
        for j in range(i + 1, len(geoms)):
            if a.intersects(geoms[j]):
                value = area(a.intersection(geoms[j]))
                if value > 0:
                    pairs_overlap.append({'a': source[i]['properties']['adm2_pcode'],
                                          'b': source[j]['properties']['adm2_pcode'], 'overlap_m2': value})
    paths = ['hdx.txt', 'hdx-boundaries.zip', 'hdx/nam_admin2.geojson', 'hdx/nam_admin1.geojson',
             'hdx/nam_admin0.geojson', 'NAM.shp', 'NAM.dbf', 'stanfordxml.txt', 'geolatest.txt', 'arcgis121.txt',
             'fao-item.json', 'fao-layer.json', 'fao-namibia-attributes.json']
    report = {
        'schema_version': 1, 'review_date': '2026-10-01',
        'scope': {'all_current_locations': 111, 'all_candidate_constituencies': 107,
                  'all_candidate_regions': 14, 'all_original_source_rows': 109},
        'source': {'url': 'https://data.humdata.org/dataset/cod-ab-nam',
                   'publisher': 'OCHA Field Information Services / HDX',
                   'original_author': metadata['dataset_source'],
                   'license': metadata['license_title'], 'license_id': metadata['license_id'],
                   'source_boundary_date': '2011-01-01', 'humanitarian_valid_on': '2020-01-09',
                   'accuracy_review_date': '2025-01-28', 'caveats': metadata['caveats'],
                   'notes': metadata['notes'], 'pinned_inputs': {p: sha(CACHE / p) for p in paths}},
        'method': 'All-pairs WGS84 ellipsoidal polygon intersection using the shared pinned area integral; nonzero overlaps recorded in both directions. No centroid assignment, shape growth, or attribute transfer.',
        'summary': {'current_land_km2': atlas_total / 1e6, 'source_union_km2': source_total / 1e6,
                    'candidate_country_coverage_share': area(source_union.intersection(country)) / area(country),
                    'candidate_outside_country_km2': area(source_union.difference(country)) / 1e6,
                    'candidate_gap_km2': area(country.difference(source_union)) / 1e6,
                    'old_footprint_outside_candidate_km2': area(atlas_union.difference(source_union)) / 1e6,
                    'candidate_footprint_outside_old_km2': area(source_union.difference(atlas_union)) / 1e6,
                    'candidate_pair_overlaps': len(pairs_overlap),
                    'candidate_overlap_sum_m2': sum(r['overlap_m2'] for r in pairs_overlap),
                    'invalid_candidate_geometries': sum(not r['valid_geometry'] for r in new_rows),
                    'minimum_parent_containment_share': min(r['parent_containment_share'] for r in new_rows),
                    'old_names_not_matching_spatial_winner': sum(not r['name_matches_spatial_winner'] for r in old_rows),
                    'old_without_candidate_overlap': sum(not r['top_spatial_matches'] for r in old_rows),
                    'upstream_binary_join_verified': True},
        'recommendation': {'action': 'Replace the defective country reference layer as one versioned release using all 107 COD territories, subject to topology and adjacent-country reconciliation gates.',
                           'reference_label': 'Namibia former constituency framework (2011 source, later regional labeling); modern 121-constituency completeness open.',
                           'archive_old_ids': True, 'new_source_ids': True,
                           'historical_record_transfer': 'None without separately reviewed identity and date evidence. Spatial correspondence alone cannot distinguish erroneous names from actual succession.',
                           'current_121_framework_status': 'Open: inspected Esri 2025 layer is restricted; no independently licensed complete newer constituency polygon layer verified.'},
        'additional_source_assessments': [
            {'url': 'https://www.arcgis.com/home/item.html?id=3f933df86b604db2b655680a221a9a04',
             'role': '2025 constituency boundaries', 'decision': 'Excluded from offline dataset',
             'reason': 'Esri Master License Agreement explicitly prohibits offline export; requires subscription.'},
            {'url': load(CACHE / 'fao-item.json')['url'], 'license': 'CC BY 4.0',
             'role': 'FAO DIEM administrative reference layer', 'decision': 'No newer full framework established',
             'observed_rows': len(load(CACHE / 'fao-namibia-attributes.json')['features']),
             'observed_unique_constituency_codes': len({f['attributes']['adm2_pcode'] for f in load(CACHE / 'fao-namibia-attributes.json')['features']}),
             'reason': '214 returned rows contain only the same 107 constituency codes; live layer availability does not establish a modern 121-constituency dataset.'}],
        'current_locations': old_rows, 'candidate_locations': new_rows,
        'candidate_overlaps': pairs_overlap, 'all_positive_correspondences': positive_pairs,
        'original_binary_source_rows': upstream,
    }
    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    with gzip.GzipFile(filename=str(output), mode='wb', mtime=0) as out:
        out.write(json.dumps(report, ensure_ascii=False, separators=(',', ':')).encode())
    print(json.dumps({'output': str(output), 'sha256': sha(output), 'scope': report['scope'], 'summary': report['summary']}, indent=2))


if __name__ == '__main__':
    main()
