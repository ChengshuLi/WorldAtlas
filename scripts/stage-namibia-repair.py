"""Stage a complete source-backed Namibia replacement without live mutation.

Every location uses a licensed COD territory. Archive all old identities, audit
every neighboring atlas footprint, and expose unexplained land as a blocking
condition instead of inventing cells or silently changing a neighboring source.
"""
import argparse
import gzip
import hashlib
import json
import pathlib

from shapely import make_valid, union_all, normalize
from shapely.geometry import box, mapping, shape, LineString
from ellipsoidal_area import area

ROOT = pathlib.Path(__file__).resolve().parents[1]
CACHE = ROOT / '.cache/namibia-source-review'
RETAINED = ROOT / 'data/retained-geographic-sources/namibia'
SOURCE = 'https://data.humdata.org/dataset/cod-ab-nam'
REVISION = 'ca96624a56bd078437bca8184e78163e5039ad19'
NE = f'https://raw.githubusercontent.com/nvkelso/natural-earth-vector/{REVISION}/geojson/ne_10m_land.geojson'


def load(path):
    with gzip.open(path, 'rt') if str(path).endswith('.gz') else open(path) as stream:
        return json.load(stream)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def dump(path, value):
    data = json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    if str(path).endswith('.gz'):
        with open(path, 'wb') as stream, gzip.GzipFile(filename='', mode='wb', fileobj=stream, mtime=0) as out:
            out.write(data)
    else:
        path.write_bytes(data)
    return digest(data)


def poly(geometry):
    valid = make_valid(geometry)
    if valid.geom_type in ('Polygon', 'MultiPolygon'):
        return valid
    return union_all([poly(g) for g in getattr(valid, 'geoms', ())
                      if g.geom_type in ('Polygon', 'MultiPolygon', 'GeometryCollection')])


def geometry_hash(geometry):
    return digest(normalize(geometry).wkb)


def bounds_intersect(a, b):
    return a[0] <= b[2] and b[0] <= a[2] and a[1] <= b[3] and b[1] <= a[3]


def archive_sources(current, hierarchy, neighboring_conflicts):
    entries = []
    sources = [
        ('hdx-boundaries.zip', 'cod-original.zip', SOURCE, 'CC BY-IGO', False),
        ('hdx.txt', 'cod-metadata.json.gz', SOURCE, 'CC BY-IGO', True),
        ('hdx/nam_admin2.geojson', 'cod-constituencies.geojson.gz', SOURCE, 'CC BY-IGO', True),
        ('hdx/nam_admin1.geojson', 'cod-regions.geojson.gz', SOURCE, 'CC BY-IGO', True),
        ('hdx/nam_admin0.geojson', 'cod-country.geojson.gz', SOURCE, 'CC BY-IGO', True),
        ('NAM.shp', 'original-2007.shp.gz', 'https://purl.stanford.edu/cs051py0596', 'Public Domain', True),
        ('NAM.dbf', 'original-2007.dbf.gz', 'https://purl.stanford.edu/cs051py0596', 'Public Domain', True),
        ('NAM.shx', 'original-2007.shx.gz', 'https://purl.stanford.edu/cs051py0596', 'Public Domain', True),
        ('NAM.prj', 'original-2007.prj.gz', 'https://purl.stanford.edu/cs051py0596', 'Public Domain', True),
        ('stanford-original.geojson', 'original-2007-constituencies.geojson.gz', 'https://purl.stanford.edu/cs051py0596', 'Public Domain', True),
        ('stanfordxml.txt', 'original-2007-metadata.xml.gz', 'https://purl.stanford.edu/cs051py0596', 'Public Domain', True),
        ('ne_10m_land.geojson', 'natural-earth-land.geojson.gz', NE, 'Public Domain', True),
        ('../ne_10m_admin_0_countries.json', 'natural-earth-reference-countries.geojson.gz',
         f'https://raw.githubusercontent.com/nvkelso/natural-earth-vector/{REVISION}/geojson/ne_10m_admin_0_countries.geojson', 'Public Domain', True),
        ('geolatest.txt', 'geoboundaries-metadata.json.gz', 'https://www.geoboundaries.org/api/current/gbOpen/NAM/ADM2/', 'Public Domain', True),
        ('arcgis121.txt', 'rejected-esri-license.json.gz', 'https://www.arcgis.com/home/item.html?id=3f933df86b604db2b655680a221a9a04', 'Metadata retained for license assessment only; no Esri polygon export', True),
        ('fao-item.json', 'fao-license.json.gz', 'https://www.arcgis.com/home/item.html?id=3596c3ad318849068eda21517ade30be', 'CC BY 4.0', True),
        ('fao-namibia-attributes.json', 'fao-name-inventory.json.gz', 'https://www.arcgis.com/home/item.html?id=3596c3ad318849068eda21517ade30be', 'CC BY 4.0', True),
    ]
    RETAINED.mkdir(parents=True, exist_ok=True)
    for original, retained, url, license_text, compressed in sources:
        data = (CACHE / original).read_bytes()
        path = RETAINED / retained
        if compressed:
            with open(path, 'wb') as stream, gzip.GzipFile(filename='', mode='wb', fileobj=stream, mtime=0) as out:
                out.write(data)
        else:
            path.write_bytes(data)
        assert path.stat().st_size < 16 * 1024 * 1024, 'Retained source exceeds Git per-file limit'
        entries.append({'path': retained, 'encoding': 'gzip' if compressed else 'original',
                        'input_cache_path': original,
                        'original_sha256': digest(data), 'retained_sha256': digest(path.read_bytes()),
                        'bytes': path.stat().st_size, 'url': url, 'license': license_text})
    for name, value in [('archived-atlas-locations.geojson.gz', {'type': 'FeatureCollection', 'features': current}),
                        ('archived-atlas-hierarchy.json.gz', hierarchy),
                        ('neighbor-source-conflicts.geojson.gz', {'type': 'FeatureCollection', 'features': neighboring_conflicts})]:
        raw_sha = dump(RETAINED / name, value)
        entries.append({'path': name, 'encoding': 'gzip', 'original_sha256': raw_sha,
                        'retained_sha256': digest((RETAINED / name).read_bytes()),
                        'bytes': (RETAINED / name).stat().st_size,
                        'url': 'Atlas pre-migration snapshot; original source URLs retained per feature',
                        'license': 'Derived source geometry retains its original per-feature license'})
    dump(RETAINED / 'manifest.json', {'schema_version': 1, 'reference_date': '2026-10-01',
                                    'sources': entries, 'total_bytes': sum(r['bytes'] for r in entries)})
    return entries


def restore_pinned_inputs():
    """A fresh checkout can reconstruct source caches from retained Git proofs."""
    manifest = RETAINED / 'manifest.json'
    if not manifest.exists():
        return
    for record in load(manifest)['sources']:
        if 'input_cache_path' not in record:
            continue
        destination = (CACHE / record['input_cache_path']).resolve()
        assert destination.is_relative_to(ROOT / '.cache'), 'Invalid retained cache path'
        if destination.exists():
            assert digest(destination.read_bytes()) == record['original_sha256'], 'Pinned source changed'
            continue
        stored = (RETAINED / record['path']).read_bytes()
        assert digest(stored) == record['retained_sha256']
        raw = gzip.decompress(stored) if record['encoding'] == 'gzip' else stored
        assert digest(raw) == record['original_sha256']
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(raw)


def pieces(g):
    if g.geom_type == 'Polygon':
        return [g]
    return [p for q in getattr(g, 'geoms', ()) for p in pieces(q)]


def coastal_concordance(source, raw_geoms, land, shoreline, unresolved_land, ne_namibia):
    """Geometry-only two-way source matches; never extend an inland border.

    A candidate coast component must already be in the old atlas, be physical
    reference land, touch the physical exterior shoreline, and belong to a
    published original footprint with >=95% correspondence in both directions.
    Names from the corrupt source are kept as evidence but never used to match.
    """
    original = load(CACHE / 'stanford-original.geojson')['features']
    rows, groups = [], {}
    for i, f in enumerate(original):
        g = poly(shape(f['geometry'])).intersection(land)
        measured = area(g)
        matches = [(j, area(g.intersection(h))) for j, h in enumerate(raw_geoms) if g.intersects(h)]
        matches.sort(key=lambda row: -row[1])
        winner = matches[0] if measured > 0 and matches else None
        share = winner[1] / measured if winner else 0
        rows.append({'original_record': i + 1, 'original_name_untrusted': f['properties']['ADM2'],
                     'original_physical_land_m2': measured,
                     'winner_code': source[winner[0]]['properties']['adm2_pcode'] if winner else None,
                     'winning_old_land_share': share,
                     'eligible_one_way': share >= .95,
                     'matching_method': 'Spatial footprint correspondence only; corrupt source names ignored.'})
        if share >= .95:
            groups.setdefault(winner[0], []).append((i, g))
    extensions, group_rows, coast_rows = {}, [], []
    for j in range(len(source)):
        members = groups.get(j, [])
        if not members:
            group_rows.append({'source_code': source[j]['properties']['adm2_pcode'],
                               'source_name': source[j]['properties']['adm2_name'],
                               'original_records': [], 'combined_old_land_share': None,
                               'candidate_land_share': 0, 'eligible_bidirectional': False,
                               'reason': 'No original source footprint passed the one-way >=95% geometry correspondence.'})
            continue
        combined = union_all([g for i, g in members])
        target = raw_geoms[j].intersection(land)
        old_share = area(combined.intersection(target)) / area(combined)
        target_share = area(combined.intersection(target)) / area(target)
        eligible = old_share >= .95 and target_share >= .95
        group_rows.append({'source_code': source[j]['properties']['adm2_pcode'],
                           'source_name': source[j]['properties']['adm2_name'],
                           'original_records': [i + 1 for i, g in members],
                           'combined_old_land_share': old_share, 'candidate_land_share': target_share,
                           'eligible_bidirectional': eligible})
        if not eligible:
            continue
        remainder = combined.intersection(unresolved_land).intersection(ne_namibia)
        accepted = []
        for g in pieces(remainder):
            coastline = g.boundary.intersection(shoreline)
            coastal = not coastline.is_empty and coastline.length > 1e-10
            coast_rows.append({'source_code': source[j]['properties']['adm2_pcode'],
                               'area_m2': area(g), 'bounds': list(g.bounds),
                               'touches_physical_exterior_shoreline': coastal,
                               'decision': 'Source-supported coast restoration' if coastal else
                               'Blocked: inland source-border offset, not a coastal correction'})
            if coastal:
                accepted.append(g)
        extensions[j] = union_all(accepted)
    conflicts = []
    keys = list(extensions)
    for position, i in enumerate(keys):
        for j in keys[position + 1:]:
            overlap = extensions[i].intersection(extensions[j])
            if area(overlap) > .001:
                conflicts.append({'a': source[i]['properties']['adm2_pcode'],
                                  'b': source[j]['properties']['adm2_pcode'],
                                  'area_m2': area(overlap), '_geometry': overlap})
    disputed = union_all([row['_geometry'] for row in conflicts])
    for row in conflicts:
        del row['_geometry']
    safe = {j: g.difference(disputed) for j, g in extensions.items()}
    return safe, {'schema_version': 1, 'method': coastal_concordance.__doc__,
                  'original_records_reviewed': len(rows), 'candidate_groups_reviewed': len(group_rows),
                  'source_records': rows, 'source_groups': group_rows, 'residual_components': coast_rows,
                  'conflicts': conflicts, 'ambiguous_coast_overlap_m2': area(disputed),
                  'safe_coast_restored_m2': area(union_all(list(safe.values()))),
                  'historical_attribute_transfer': 'None',
                  'uncertainty': 'Reference coastline restoration by strong two-source shape correspondence. Does not certify the historical identity or modern administrative vintage.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', default='.cache/namibia-repair-stage')
    args = parser.parse_args()
    restore_pinned_inputs()
    stage = ROOT / args.stage
    stage.mkdir(parents=True, exist_ok=True)
    report = load(ROOT / 'data/namibia-source-review.json.gz')
    assert report['source']['license_id'] == 'cc-by-igo'
    source = load(CACHE / 'hdx/nam_admin2.geojson')['features']
    region_source = load(CACHE / 'hdx/nam_admin1.geojson')['features']
    country = poly(shape(load(CACHE / 'hdx/nam_admin0.geojson')['features'][0]['geometry']))
    raw_geoms = [poly(shape(f['geometry'])) for f in source]
    source_union = union_all(raw_geoms)
    assert area(source_union.symmetric_difference(country)) < .01
    # Only physical land features intersecting the country's extent are needed;
    # no country ownership polygons are substituted for the land mask.
    land_features = load(CACHE / 'ne_10m_land.geojson')['features']
    relevant_land = [poly(shape(f['geometry'])) for f in land_features
                     if bounds_intersect(shape(f['geometry']).bounds, country.bounds)]
    physical_land = union_all(relevant_land)
    land = physical_land.intersection(box(*country.bounds))
    geoms = [g.intersection(land) for g in raw_geoms]
    footprint = union_all(geoms)
    current, neighbors, world_count, world_hashes = [], [], 0, {}
    index = load(ROOT / 'data/world-index.json')
    for part in index['parts']:
        path = ROOT / 'data' / part
        world_hashes[part] = digest(path.read_bytes())
        for f in load(path)['features']:
            world_count += 1
            g = shape(f['geometry'])
            if f['properties']['reference_owner'] == 'Namibia':
                current.append(f)
            elif bounds_intersect(g.bounds, country.bounds):
                neighbors.append((f, poly(g)))
    assert len(current) == 111 and len(source) == 107
    old_union = union_all([poly(shape(f['geometry'])) for f in current])
    conflict_rows, neighbors_union = [], union_all([g for f, g in neighbors])
    for f, g in neighbors:
        overlap = g.intersection(footprint)
        if not overlap.is_empty and area(overlap) > .001:
            p = f['properties']
            conflict_rows.append({'id': p['id'], 'name': p['name'], 'reference_owner': p['reference_owner'],
                                  'overlap_m2': area(overlap), 'old_area_m2': area(g),
                                  'overlap_share': area(overlap) / area(g),
                                  'source_url': p['metadata'].get('source_url'),
                                  'geometry_sha256': geometry_hash(g),
                                  'proposed_action': 'Unresolved source-boundary disagreement; no neighbor geometry changed'})
    hierarchy = load(ROOT / 'data/hierarchy.json')
    by_id = {u['id']: u for u in hierarchy}
    old_chain_ids = set()
    for f in current:
        parent = f['properties']['parent_id']
        while parent:
            old_chain_ids.add(parent)
            parent = by_id[parent]['parent_id']
    conflicting_ids = {r['id'] for r in conflict_rows}
    retained = archive_sources(current, [u for u in hierarchy if u['id'] in old_chain_ids],
                               [f for f, g in neighbors if f['properties']['id'] in conflicting_ids])
    units = []
    # Source regional administrative divisions are local clusters at this
    # atlas's province tier. Do not fabricate a missing middle administrative
    # tier or make every location an identically shaped province.
    macro_area = {u['name']: u for u in hierarchy if u['level'] == 'area' and u['name'] in ('Namibia', 'Caprivi Strip')}
    assert set(macro_area) == {'Namibia', 'Caprivi Strip'}
    for f in region_source:
        p = f['properties']
        parent = macro_area['Caprivi Strip' if p['adm1_name'] == 'Zambezi' else 'Namibia']
        units.append({'id': 'hdx:NAM:province:' + p['adm1_pcode'], 'name': p['adm1_name'],
                      'level': 'province', 'parent_id': parent['id'],
                      'metadata': {'source_id': 'hdx:NAM:COD-AB:v01', 'source_url': SOURCE,
                                   'license': 'CC BY-IGO', 'source_role': 'Published regional cluster of constituency territories',
                                   'reference_year': '2011 source / later regional labels',
                                   'basis': 'Complete constituency membership of published source region; province tier describes regional local-territory clusters, not ADM-level number.',
                                   'parent_assignment': 'Zambezi is the renamed Caprivi source region; other regions use existing Namibia geographic-area context.',
                                   'semantic_review': {'status': 'open', 'boundary_status': 'source-backed',
                                                       'remaining_reasons': ['Modern 121-constituency reference coverage is unavailable in this source; independent macro-area convention remains under review.']}}})
    locations = []
    for f, raw, g in zip(source, raw_geoms, geoms):
        p = f['properties']
        assert not g.is_empty, 'Physical reference land mask erased a candidate territory'
        locations.append({'type': 'Feature', 'geometry': mapping(g),
                          'properties': {'id': 'hdx:NAM:ADM2:' + p['adm2_pcode'], 'name': p['adm2_name'],
                                         'parent_id': 'hdx:NAM:province:' + p['adm1_pcode'],
                                         'reference_owner': 'Namibia',
                                         'metadata': {'source_id': 'hdx:NAM:COD-AB:v01', 'source_name': 'NSA / OCHA COD-AB',
                                                      'source_url': SOURCE, 'license': 'CC BY-IGO', 'reference_year': '2011',
                                                      'source_role': 'Published constituency territory in former 107-unit framework',
                                                      'original_id': p['adm2_pcode'], 'source_boundary_created': '2011-01-01',
                                                      'humanitarian_valid_on': p['valid_on'], 'source_accuracy_reviewed': '2025-01-28',
                                                      'original_geometry_sha256': geometry_hash(raw),
                                                      'land_mask': {'source_url': NE, 'license': 'Public Domain',
                                                                    'removed_source_nonland_m2': area(raw.difference(g))},
                                                      'reference_owner_id': 'owner:Q1030',
                                                      'framework_reference': 'Former constituency reference geography, not a verified 2026 administrative map',
                                                      'historical_assignment': 'No imported historical attributes transferred automatically',
                                                      'semantic_review': {'status': 'open', 'boundary_status': 'source-backed',
                                                                          'remaining_reasons': ['Source vintage predates current 121-constituency system.']}}}})
    assert len(units) == 14 and len(locations) == 107
    common_chain = [u for u in hierarchy if u['id'] in old_chain_ids and u['level'] != 'province']
    staged_units = common_chain + units
    complete = {u['id']: u for u in staged_units}
    for f in locations:
        expected = ['province', 'area', 'region', 'subcontinent', 'continent']
        parent = f['properties']['parent_id']
        for level in expected:
            assert complete[parent]['level'] == level
            parent = complete[parent]['parent_id']
        assert parent is None
    candidate_crosswalk = report['all_positive_correspondences']
    new_only = footprint.difference(old_union)
    uncovered_new_land = new_only.difference(neighbors_union)
    removed_old_land = old_union.intersection(land).difference(footprint)
    uncovered_removed_land = removed_old_land.difference(neighbors_union)
    reference_country_features = load(ROOT / '.cache/ne_10m_admin_0_countries.json')['features']
    reference_countries = [(f['properties'], poly(shape(f['geometry'])))
                           for f in reference_country_features
                           if bounds_intersect(shape(f['geometry']).bounds, country.bounds)]
    residual_country_context = []
    for p, g in reference_countries:
        overlap = uncovered_removed_land.intersection(g)
        value = area(overlap)
        if value > .001:
            residual_country_context.append({'name': p.get('NAME') or p.get('name') or p.get('ADMIN'),
                                             'iso': p.get('ADM0_A3') or p.get('adm0_a3'),
                                             'area_m2': value,
                                             'context': 'Independent reference ownership/context only; does not assign a location or override historical ownership.'})
    residual_parts = list(uncovered_removed_land.geoms) if uncovered_removed_land.geom_type == 'MultiPolygon' else [uncovered_removed_land]
    residual_parts = sorted([g for g in residual_parts if area(g) > .001], key=area, reverse=True)
    residual_components = [{'area_m2': area(g), 'bounds': list(g.bounds),
                            'reference_point': list(g.representative_point().coords)[0]}
                           for g in residual_parts]
    namibia_context = union_all([g for p, g in reference_countries
                                if (p.get('ADM0_A3') or p.get('adm0_a3')) == 'NAM'])
    shoreline = union_all([LineString(g.exterior.coords) for g in pieces(physical_land)]).intersection(box(*country.bounds))
    safe_extensions, coast_review = coastal_concordance(source, raw_geoms, land, shoreline,
                                                       uncovered_removed_land, namibia_context)
    coast_locations = []
    for j, f in enumerate(locations):
        value = json.loads(json.dumps(f))
        extension = safe_extensions.get(j)
        if extension is not None and not extension.is_empty:
            merged = poly(union_all([geoms[j], extension]))
            value['geometry'] = mapping(merged)
            value['properties']['metadata']['coastal_concordance'] = {
                'method': 'Geometry-only bidirectional >=95% original-2007 / COD correspondence; restore only previously mapped physical land components touching the independent exterior coastline.',
                'restored_area_m2': area(extension), 'original_source_url': 'https://purl.stanford.edu/cs051py0596',
                'original_source_license': 'Public Domain', 'physical_land_url': NE,
                'historical_records_transferred': False,
                'evidence_file': 'coastal-extension-review.json.gz',
                'uncertainty': coast_review['uncertainty']}
        coast_locations.append(value)
    coast_union = union_all([shape(f['geometry']) for f in coast_locations])
    assert abs(area(coast_union.intersection(neighbors_union)) - area(footprint.intersection(neighbors_union))) < .1
    coast_review['remaining_unresolved_old_land_m2'] = area(uncovered_removed_land.difference(coast_union))
    blocks = []
    if conflict_rows:
        blocks.append({'code': 'neighbor-source-boundary-conflicts', 'locations': len(conflict_rows),
                       'action_required': 'Inspect conflicting neighboring source geometries and approve sourced territorial corrections; this isolated stage does not clip them.'})
    if area(uncovered_removed_land) > .001:
        blocks.append({'code': 'old-land-left-without-source-territory', 'area_m2': area(uncovered_removed_land),
                       'action_required': 'Identify an actual licensed neighboring territory or explain a source-land defect. No nearest-location fill.'})
    result = {'schema_version': 1, 'status': 'blocked' if blocks else 'ready-for-root-integration',
              'reference_date': '2026-10-01', 'source_framework': 'Former 107 constituency framework; 2011 boundaries / later regional labeling',
              'world_locations_inspected': world_count, 'world_source_hashes': world_hashes,
              'counts': {'old_locations_archived': 111, 'new_locations': 107, 'new_provinces': 14,
                         'existing_geographic_areas': 2},
              'geometry': {'source_country_km2': area(country)/1e6, 'land_footprint_km2': area(footprint)/1e6,
                           'source_country_nonland_removed_km2': area(country.difference(land))/1e6,
                           'neighbor_overlap_km2': area(footprint.intersection(neighbors_union))/1e6,
                           'new_land_not_previously_mapped_km2': area(uncovered_new_land)/1e6,
                           'old_land_lost_not_mapped_elsewhere_km2': area(uncovered_removed_land)/1e6,
                           'old_country_geometry_nonland_km2': area(old_union.difference(land))/1e6},
              'neighbor_conflicts': conflict_rows, 'blocks': blocks,
              'uncovered_old_land_reference_country_context': residual_country_context,
              'uncovered_old_land_components': residual_components,
              'coastal_concordance': {'safe_restoration_m2': coast_review['safe_coast_restored_m2'],
                                      'remaining_unresolved_old_land_m2': coast_review['remaining_unresolved_old_land_m2'],
                                      'review_file': 'coastal-extension-review.json.gz',
                                      'candidate_file': 'locations-coastal-concordance.geojson.gz'},
              'old_to_candidate_crosswalk': candidate_crosswalk,
              'archival_policy': 'Every old ID, footprint, source reference and record retained; no source of direct historical evidence moved automatically.',
              'hierarchy_policy': '107 locations in 14 published regional constituency clusters at province tier, within two existing sourced geographical areas; all five adjacent-tier parents resolved. No count quota or invented intermediate administrative division.',
              'retained_sources': retained}
    dump(stage / 'locations.geojson.gz', {'type': 'FeatureCollection', 'features': locations})
    dump(stage / 'hierarchy.json', staged_units)
    dump(stage / 'migration.json.gz', result)
    dump(stage / 'archive.geojson.gz', {'type': 'FeatureCollection', 'features': current})
    dump(stage / 'locations-coastal-concordance.geojson.gz', {'type': 'FeatureCollection', 'features': coast_locations})
    dump(stage / 'coastal-extension-review.json.gz', coast_review)
    dump(RETAINED / 'coastal-concordance-receipt.json.gz', coast_review)
    dump(stage / 'unresolved-land.geojson.gz', {'type': 'FeatureCollection',
                                              'features': [{'type': 'Feature', 'geometry': mapping(g),
                                                            'properties': {'status': 'unresolved-source-boundary-gap',
                                                                           'area_m2': area(g), 'assigned_location': None}}
                                                           for g in residual_parts]})
    manifest = load(RETAINED / 'manifest.json')
    for source_path, retained_name in [('locations.geojson.gz', 'staged-cod-locations.geojson.gz'),
                                       ('locations-coastal-concordance.geojson.gz', 'staged-coast-concordance-locations.geojson.gz'),
                                       ('migration.json.gz', 'migration-receipt.json.gz'),
                                       ('coastal-extension-review.json.gz', 'coastal-concordance-receipt.json.gz'),
                                       ('unresolved-land.geojson.gz', 'unresolved-land.geojson.gz')]:
        data = (stage / source_path).read_bytes()
        (RETAINED / retained_name).write_bytes(data)
        manifest['sources'].append({'path': retained_name, 'encoding': 'gzip',
                                    'original_sha256': digest(gzip.decompress(data)),
                                    'retained_sha256': digest(data), 'bytes': len(data),
                                    'role': 'Blocked migration candidate or preparation receipt; not an applied release',
                                    'url': SOURCE, 'license': 'Underlying COD CC BY-IGO; original 2007 and Natural Earth inputs Public Domain'})
    raw_sha = dump(RETAINED / 'staged-hierarchy.json.gz', staged_units)
    manifest['sources'].append({'path': 'staged-hierarchy.json.gz', 'encoding': 'gzip',
                                'original_sha256': raw_sha, 'retained_sha256': digest((RETAINED / 'staged-hierarchy.json.gz').read_bytes()),
                                'bytes': (RETAINED / 'staged-hierarchy.json.gz').stat().st_size,
                                'role': 'Blocked migration reference hierarchy, not an applied release',
                                'url': SOURCE, 'license': 'COD CC BY-IGO; existing geographic source licenses retained per unit'})
    manifest['total_bytes'] = sum(r['bytes'] for r in manifest['sources'])
    dump(RETAINED / 'manifest.json', manifest)
    print(json.dumps({'stage': str(stage), 'status': result['status'], 'counts': result['counts'],
                      'geometry': result['geometry'], 'blocks': blocks}, indent=2))


if __name__ == '__main__':
    main()
