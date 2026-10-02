"""Prepare actual dated name attestations with exact, conservative identity checks.

US Census 2020 county gazetteer: exact source name and unique internal point.
Eurostat NUTS 2021: exact name/country and strong mutual footprint correspondence.
Snapshot intervals are single supported years, never ancient carry-forwards.
"""
import collections
import csv
import gzip
import hashlib
import io
import json
import pathlib
import re
import subprocess
import unicodedata
import zipfile

from shapely import make_valid, union_all
from shapely.geometry import Point, shape

ROOT = pathlib.Path(__file__).resolve().parents[1]
CACHE = ROOT / '.cache/dated-reference-names'
OUT = ROOT / 'data/dated-reference-names'
US_URL = 'https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2020_Gazetteer/2020_Gaz_counties_national.zip'
EU_URL = 'https://gisco-services.ec.europa.eu/distribution/v2/nuts/geojson/NUTS_RG_10M_2021_4326.geojson'
EU_LICENSE = 'https://ec.europa.eu/eurostat/help/copyright-notice'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalized(value):
    return re.sub('[^a-z0-9]', '', unicodedata.normalize('NFKD', value).lower())


def county_key(value):
    # Keep "City" in James City, Charles City, Carson City; historical county names
    # require attested suffix stripping only for source file's formal type endings.
    return normalized(re.sub(r'\s+(County|Parish|Borough|Census Area|Municipio|Municipality)$', '', value, flags=re.I))


def prepare():
    OUT.mkdir(exist_ok=True)
    gaz = CACHE / 'county-2020.zip'
    nuts = CACHE / 'nuts-2021-10m.geojson'
    if not gaz.exists() or not nuts.exists():
        raise FileNotFoundError('Pin actual source downloads in .cache/dated-reference-names first')
    source_hashes = {'census-county-gazetteer:2020': sha(gaz), 'eurostat:nuts:2021': sha(nuts)}
    hierarchy = json.loads((ROOT / 'data/hierarchy.json').read_bytes())
    by = {g['id']: g for g in hierarchy}
    nut_features = json.loads(nuts.read_bytes())['features']
    source_candidates = collections.defaultdict(list)
    excluded = collections.Counter()
    for f in nut_features:
        p = f['properties']
        if not any(p.get(flag) == 'T' for flag in ['EU_STAT', 'EFTA_STAT', 'CC_STAT']):
            excluded[p['CNTR_CODE']] += 1
            continue
        name = p.get('NAME_LATN') or p.get('NUTS_NAME')
        if not name:
            continue
        source_candidates[(p['ISO3_CODE'], normalized(name))].append(f)
    candidate_names = {key[1] for key in source_candidates}
    candidate_groups = {g['id']: g for g in hierarchy if g['level'] in ['area', 'province'] and normalized(g['name']) in candidate_names}
    member_geometries = collections.defaultdict(list)
    member_iso = collections.defaultdict(set)
    matching_locations = []
    us_locations = []
    all_ids = {g['id'] for g in hierarchy}
    for part in json.loads((ROOT / 'data/world-index.json').read_bytes())['parts']:
        for f in json.loads((ROOT / 'data' / part).read_bytes())['features']:
            p = f['properties']
            all_ids.add(p['id'])
            sid = p['metadata'].get('source_id', '')
            iso = sid.split(':')[1] if sid.startswith('gb:') else None
            key = (iso, normalized(p['name']))
            if iso in ['USA', 'PRI']:
                us_locations.append(f)
            if key in source_candidates:
                matching_locations.append((f, key))
            gid = p['parent_id']
            while gid:
                if gid in candidate_groups:
                    member_geometries[gid].append(f['geometry'])
                    member_iso[gid].add(iso)
                gid = by[gid]['parent_id']
    rows = []
    crosswalk = []
    failures = []
    with zipfile.ZipFile(gaz) as z:
        csv_rows = [{k.strip(): v.strip() for k, v in row.items()} for row in csv.DictReader(io.StringIO(z.read(z.namelist()[0]).decode('utf8')), delimiter='\t')]
    gaz_by_name = collections.defaultdict(list)
    for r in csv_rows:
        gaz_by_name[county_key(r['NAME'])].append(r)
    for f in us_locations:
        p = f['properties']
        geo = make_valid(shape(f['geometry']))
        candidates = [r for r in gaz_by_name[county_key(p['name'])] if geo.covers(Point(float(r['INTPTLONG']), float(r['INTPTLAT'])))]
        if len(candidates) != 1:
            failures.append({'id': p['id'], 'source': 'census-county-gazetteer:2020', 'reason': 'Exact source name and unique internal-point match required', 'candidate_geoids': [r['GEOID'] for r in candidates]})
            continue
        r = candidates[0]
        evidence = {'geoid': r['GEOID'], 'ansi_code': r['ANSICODE'], 'state_postal': r['USPS'], 'source_name': r['NAME'], 'source_internal_point': [float(r['INTPTLONG']), float(r['INTPTLAT'])], 'identity_match': 'Exact normalized source name plus unique official internal-point containment in current location land; no fuzzy matching'}
        rows.append({'id': f"name:census:2020:{p['id']}", 'entity_id': p['id'], 'name': r['NAME'], 'language': 'en', 'role': 'preferred', 'valid_from': 2020, 'valid_to': 2021, 'source_id': 'census-county-gazetteer:2020', 'is_example': 0, 'metadata': evidence | {'source_year': 2020, 'snapshot_only': True, 'geometry_vintage_context': p['metadata'].get('reference_year'), 'not_a_historical_boundary_assertion': True, 'source_sha256': source_hashes['census-county-gazetteer:2020']}})
        crosswalk.append({'entity_id': p['id'], 'source': 'census-county-gazetteer:2020', 'source_id': r['GEOID'], 'evidence': evidence})

    def nuts_name(identity, name, geometry, key, level):
        candidates = source_candidates[key]
        geographic = []
        for f in candidates:
            source = make_valid(shape(f['geometry']))
            inter = geometry.intersection(source).area
            inside = inter / geometry.area if geometry.area else 0
            represented = inter / source.area if source.area else 0
            if min(inside, represented) >= .95:
                geographic.append((f, inside, represented))
        if len(geographic) != 1:
            failures.append({'id': identity, 'source': 'eurostat:nuts:2021', 'reason': 'Unique exact name/country and >=95% mutual geometry correspondence required', 'matched_codes': [f['properties']['NUTS_ID'] for f, _, _ in geographic]})
            return
        f, inside, represented = geographic[0]
        p = f['properties']
        source_name = p.get('NAME_LATN') or p['NUTS_NAME']
        evidence = {'nuts_id': p['NUTS_ID'], 'nuts_level': p['LEVL_CODE'], 'country_iso': p['ISO3_CODE'], 'inside_share': inside, 'source_represented_share': represented, 'geometry_method': 'Planar WGS84 diagnostic, exact current member union versus official 10M reference polygon; required strong mutual agreement', 'identity_match': 'Exact normalized source name and source-country, unique matching official polygon; no fuzzy label or centroid assignment', 'atlas_level': level}
        rows.append({'id': f'name:nuts:2021:{identity}', 'entity_id': identity, 'name': source_name, 'language': 'und', 'role': 'preferred', 'valid_from': 2021, 'valid_to': 2022, 'source_id': 'eurostat:nuts:2021', 'is_example': 0, 'metadata': evidence | {'source_year': 2021, 'snapshot_only': True, 'not_a_historical_boundary_assertion': True, 'source_sha256': source_hashes['eurostat:nuts:2021'], 'attribution': 'Eurostat, GISCO NUTS2021. Adapted by WorldAtlas; Eurostat is not responsible for these crosswalks.'}})
        crosswalk.append({'entity_id': identity, 'source': 'eurostat:nuts:2021', 'source_id': p['NUTS_ID'], 'evidence': evidence})

    for identity, g in candidate_groups.items():
        isos = member_iso[identity]
        if len(isos) != 1:
            failures.append({'id': identity, 'source': 'eurostat:nuts:2021', 'reason': 'Mixed or missing exact source-country namespace'})
            continue
        key = (next(iter(isos)), normalized(g['name']))
        if key not in source_candidates:
            continue
        geometry = union_all([make_valid(shape(x)) for x in member_geometries[identity]])
        nuts_name(identity, g['name'], geometry, key, g['level'])
    for f, key in matching_locations:
        nuts_name(f['properties']['id'], f['properties']['name'], make_valid(shape(f['geometry'])), key, 'location')

    assert len(rows) == len({r['id'] for r in rows})
    assert all(r['entity_id'] in all_ids for r in rows)
    assert all(r['valid_to'] == r['valid_from'] + 1 for r in rows)
    assert len(rows) == len({(r['entity_id'], r['language'], r['valid_from']) for r in rows})
    (OUT / 'names.json.gz').write_bytes(gzip.compress(json.dumps(rows, separators=(',', ':'), ensure_ascii=False).encode(), mtime=0))
    (OUT / 'crosswalk.json.gz').write_bytes(gzip.compress(json.dumps(crosswalk, separators=(',', ':')).encode(), mtime=0))
    (OUT / 'unmatched.json.gz').write_bytes(gzip.compress(json.dumps(failures, separators=(',', ':')).encode(), mtime=0))
    sources = [{'id': 'census-county-gazetteer:2020', 'name': 'US Census 2020 national county Gazetteer', 'url': US_URL, 'license': 'United States government work; public domain', 'vintage': '2020', 'supported_from': 2020, 'supported_to': 2021, 'status': 'reference', 'metadata': {'sha256': source_hashes['census-county-gazetteer:2020'], 'snapshot_only': True}},
       {'id': 'eurostat:nuts:2021', 'name': 'Eurostat GISCO NUTS2021 names and classification metadata', 'url': EU_URL, 'license': 'Eurostat metadata reuse authorised with source acknowledgement; official reuse notice retained', 'vintage': 'NUTS2021', 'supported_from': 2021, 'supported_to': 2022, 'status': 'reference', 'metadata': {'sha256': source_hashes['eurostat:nuts:2021'], 'reuse_notice': EU_LICENSE, 'snapshot_only': True, 'geometry_not_republished': True, 'country_reuse_exceptions_excluded': dict(excluded), 'attribution': 'Eurostat GISCO NUTS2021. Adapted by WorldAtlas; Eurostat is not responsible for these crosswalks.'}}]
    manifest = {'version': 1, 'sources': sources, 'parts': ['names.json.gz'], 'records': len(rows), 'source_counts': dict(collections.Counter(r['source_id'] for r in rows)), 'role': 'Dated annual reference name attestations, not uninterrupted historical names', 'unmatched_count': len(failures), 'crosswalk': 'crosswalk.json.gz', 'unmatched': 'unmatched.json.gz', 'algorithm_sha256': sha(pathlib.Path(__file__)), 'hierarchy_sha256': sha(ROOT / 'data/hierarchy.json'), 'source_country_reuse_exceptions_excluded': dict(excluded), 'scope_limits': ['No date propagation outside source snapshots.', 'No inference from boundaryYearRepresented or modification dates.', 'No settlement point renames a larger territory.', 'All ambiguous crosswalks remain unmatched.']}
    # Use the shared JavaScript canonical ordering rather than a Python approximation.
    manifest['footprints_sha256'] = subprocess.check_output(['node', '--input-type=module', '-e', "import fs from 'node:fs'; import {footprintHash} from './scripts/check-prepared.mjs'; const index=JSON.parse(fs.readFileSync('data/world-index.json')); console.log(footprintHash(index.parts.flatMap(p=>JSON.parse(fs.readFileSync('data/'+p)).features)));"], cwd=ROOT, text=True).strip()
    manifest['location_index_sha256'] = sha(ROOT / 'data/world-index.json')
    manifest['parts'] = [{'path': 'names.json.gz', 'sha256': sha(OUT / 'names.json.gz'), 'records': len(rows)}]
    (OUT / 'index.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    prepare()
