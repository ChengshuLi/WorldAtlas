"""Use named source boundaries, never geometric subdivisions or target counts."""
import concurrent.futures, csv, hashlib, json, math, pathlib, re, unicodedata, urllib.request
from collections import defaultdict
from shapely import make_valid, STRtree
from shapely.geometry import shape, mapping

ROOT = pathlib.Path(__file__).resolve().parents[1]
CACHE = ROOT / '.cache' / 'geoboundaries'
CACHE.mkdir(parents=True, exist_ok=True)
policy = json.loads((ROOT / 'data/location-policy.json').read_text())
codes_path = ROOT / '.cache/country-codes.csv'
if not codes_path.exists():
    codes_path.write_bytes(urllib.request.urlopen('https://raw.githubusercontent.com/datasets/country-codes/2e9d6498a0456f4afc2f6cf367d1e12a9ed4afe1/data/country-codes.csv', timeout=60).read())
country_codes = {row['ISO3166-1-Alpha-3']: row for row in csv.DictReader(codes_path.open())}

def read(path):
    return json.loads(path.read_text())

def write(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')))

def download(url, path):
    if path.exists(): return read(path)
    last = None
    for attempt in range(3):
        try:
            request = urllib.request.Request(url, headers={'User-Agent': 'WorldAtlas source-boundary research'})
            raw = urllib.request.urlopen(request, timeout=90).read()
            data = json.loads(raw)
            path.write_bytes(raw)
            return data
        except Exception as error: last = error
    raise RuntimeError(f'{url}: {last}')

def normalize(name):
    return re.sub(r'[^a-z0-9]', '', unicodedata.normalize('NFKD', name or '').encode('ascii', 'ignore').decode().lower())

def polygon(feature):
    g = make_valid(shape(feature['geometry']))
    if g.geom_type == 'GeometryCollection':
        from shapely.geometry import MultiPolygon
        g = MultiPolygon([p for part in g.geoms for p in (list(part.geoms) if part.geom_type == 'MultiPolygon' else [part]) if p.geom_type == 'Polygon'])
    if g.is_empty or g.geom_type not in ('Polygon', 'MultiPolygon'): raise ValueError('Non-polygon source feature')
    return g

metadata = {level: download(f'https://www.geoboundaries.org/api/current/gbOpen/ALL/{level}/', CACHE / f'{level}-metadata.json') for level in ['ADM1', 'ADM2', 'ADM3']}
by_level = {level: {row['boundaryISO']: row for row in rows} for level, rows in metadata.items()}
selected = {}
for iso, rule in policy['countries'].items():
    level = rule['level']
    if level == 'NE': continue
    if rule.get('collection') == 'gbHumanitarian':
        row = download(f'https://www.geoboundaries.org/api/current/gbHumanitarian/{iso}/{level}/', CACHE / f'{iso}-{level}-humanitarian-metadata.json')
        row['collection'] = 'gbHumanitarian'
    else: row = dict(by_level[level][iso])
    if rule.get('source_url'): row['simplifiedGeometryGeoJSON'] = rule['source_url'].replace('.geojson','_simplified.geojson')
    selected[iso] = row
needed = {(iso, row['boundaryType']): row for iso, row in selected.items()}
for iso, row in selected.items():
    if row['boundaryType'] != 'ADM1' and iso in by_level['ADM1']: needed[(iso, 'ADM1')] = by_level['ADM1'][iso]
    if row['boundaryType'] == 'ADM3' and iso in by_level['ADM2']: needed[(iso, 'ADM2')] = by_level['ADM2'][iso]

def fetch(item):
    key, row = item
    path = CACHE / f'{key[0]}-{key[1]}.json'
    if row.get('collection') == 'gbHumanitarian' and path.exists(): path.unlink()
    data = download(row['simplifiedGeometryGeoJSON'], path)
    return key, data

datasets = {}
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
    for i, (key, data) in enumerate(pool.map(fetch, needed.items()), 1):
        datasets[key] = data
        if i % 20 == 0: print(f'Loaded {i}/{len(needed)} source layers', flush=True)

ne_countries = read(ROOT / '.cache/ne_10m_admin_0_countries.json')['features']
ne_locations = read(ROOT / '.cache/ne_10m_admin_1_states_provinces.json')['features']
country_by_iso = {f['properties']['ADM0_A3']:f['properties'] for f in ne_countries}
for feature in ne_countries:
    p = feature['properties']
    for code in [p['ADM0_A3'], p['ISO_A3'], p['ISO_A3_EH']]:
        if code and code != '-99': country_by_iso.setdefault(code, p)
ne_by_country = defaultdict(list)
for feature in ne_locations:
    p = feature['properties']; country = country_by_iso.get(p['adm0_a3'], {})
    iso = country.get('ISO_A3_EH', p['adm0_a3'])
    if iso == '-99': iso = p['adm0_a3']
    ne_by_country[iso].append(feature)

units, features, sources, statistics = {}, [], {}, defaultdict(int)
def unit(level, name, parent, basis, source):
    identifier = f'{parent or "world"}/{level}:{name}'
    units[identifier] = {'id': identifier, 'name': name, 'level': level, 'parent_id': parent, 'metadata': {'basis': basis, 'source': source}}
    return identifier

def country_parent(iso, name, continent, subcontinent):
    if continent == 'Seven seas (open ocean)':
        continent = {'AF':'Africa','AS':'Asia','EU':'Europe','NA':'North America','SA':'South America','OC':'Oceania','AN':'Antarctica'}.get(country_codes.get(iso, {}).get('Continent'))
    root = unit('continent', continent or 'Unclassified', None, 'Geographic continent', 'Natural Earth / geoBoundaries')
    sub = unit('subcontinent', subcontinent, root, 'Published geographic subregion', 'Natural Earth / geoBoundaries UNSDG-subregion') if subcontinent and subcontinent != 'Seven seas (open ocean)' else root
    return unit('region', name, sub, 'Modern country / territory grouping; not historical membership', f'country:{iso}')

aliases = {('GBR', 'cityoflondon'): 'GBR-4809', ('FRA', 'paris'): 'FRA-5333', ('TUR', 'istanbul'): 'TUR-2265'}
for iso, selected_row in selected.items():
    level = selected_row['boundaryType']
    c = country_by_iso.get(iso, {})
    country = selected_row['boundaryName']
    country_id = country_parent(iso, country, c.get('CONTINENT', selected_row.get('Continent')), c.get('SUBREGION', selected_row.get('UNSDG-subregion')))
    parent_level = 'ADM2' if level == 'ADM3' else 'ADM1'
    parent_data = datasets.get((iso, parent_level)) if level != 'ADM1' else None
    parent_shapes = [polygon(f) for f in parent_data['features']] if parent_data else []
    tree = STRtree(parent_shapes) if parent_shapes else None
    ne_index = {normalize(f['properties']['name']): f['properties'] for f in ne_by_country[iso]}
    for source_level in ['ADM1', 'ADM2', 'ADM3']:
        if (iso, source_level) in needed:
            row = needed[(iso, source_level)]
            path = CACHE / f'{iso}-{source_level}.json'
            sources[f'gb:{iso}:{source_level}'] = {**row, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    for f in datasets[(iso, level)]['features']:
        p = f['properties']; geometry = polygon(f); parent = country_id; parent_match = 'Not available in source'
        name = p.get('shapeName') or f'Unnamed {level} {p["shapeID"]}'
        if tree is not None:
            candidates = tree.query(geometry)
            overlaps = [(geometry.intersection(parent_shapes[int(i)]).area / geometry.area, int(i)) for i in candidates]
            ratio, index = max(overlaps, default=(0, -1))
            # No nearest-centre clustering: retain a parent only with near-complete spatial containment.
            if ratio >= .95:
                pp = parent_data['features'][index]['properties']
                ne = ne_index.get(normalize(pp['shapeName']), {})
                if ne.get('region_sub') or ne.get('region'):
                    area_name = ne.get('region_sub') or ne.get('region')
                    parent = unit('area', area_name, parent, 'Named grouping from Natural Earth admin-1 metadata', 'Natural Earth region_sub / region')
                parent = unit('province', pp['shapeName'], parent, 'Real ADM1; spatially matched to ADM2 (at least 95% containment)', f'gb:{iso}:{parent_level}')
                parent_match = f'ADM1 spatial containment: {ratio:.2%}'
            else: statistics['unresolved_adm1'] += 1
        identifier = aliases.get((iso, normalize(name)), f'gb:{iso}:{level}:{p["shapeID"]}')
        point = geometry.representative_point()
        provenance = {'source_id': f'gb:{iso}:{level}', 'source_name': 'geoBoundaries '+selected_row.get('collection','gbOpen'), 'source_url': selected_row['gjDownloadURL'], 'license': selected_row['boundaryLicense'], 'reference_year': selected_row['boundaryYearRepresented'], 'administrative_level': level, 'parent_source_level': parent_level, 'granularity_version': 3, 'source_role': policy['countries'][iso]['role'], 'selection_reason': policy['countries'][iso]['reason'], 'parent_match': parent_match, 'original_id': p['shapeID'], 'representative_point':[point.x,point.y]}
        features.append({'type': 'Feature', 'id': identifier, 'properties': {'id': identifier, 'name': name, 'parent_id': parent, 'reference_owner': country, 'metadata': provenance}, 'geometry': mapping(geometry)})
        statistics[level] += 1

# Preserve geographic coverage for countries/territories outside the source collection.
# These are complete named Natural Earth features, never leftover fragments or geometric cuts.
used_codes = set(selected)
for iso, rows in ne_by_country.items():
    if iso in used_codes: continue
    c = country_by_iso.get(iso, {})
    for f in rows:
        p = f['properties']; parent = country_parent(iso, p['admin'], c.get('CONTINENT'), c.get('SUBREGION'))
        for level, field in [('area', 'region'), ('province', 'region_sub')]:
            if p.get(field): parent = unit(level, p[field], parent, 'Named source administrative grouping', 'Natural Earth')
        name = p.get('name') or p.get('woe_name') or p['admin']
        features.append({'type':'Feature','id':p['adm1_code'],'properties':{'id':p['adm1_code'],'name':name,'parent_id':parent,'reference_owner':None if iso=='ATA' else p['admin'],'metadata':{'source_name':'Natural Earth','source_id':'natural-earth','administrative_level':'ADM1 fallback','source_url':'https://www.naturalearthdata.com/','license':'Public domain','reference_year':'Undated modern reference','parent_match':'Named source metadata'}},'geometry':f['geometry']})
        statistics['natural_earth_fallback'] += 1
covered_names = {f['properties']['reference_owner'] for f in features}
for f in ne_countries:
    p = f['properties']; iso = p['ISO_A3_EH']
    if iso in used_codes or ne_by_country.get(iso) or p['ADMIN'] in covered_names: continue
    parent = country_parent(iso, p['ADMIN'], p['CONTINENT'], p['SUBREGION'])
    identifier = f'country-{p["ADM0_A3"]}'
    features.append({'type':'Feature','id':identifier,'properties':{'id':identifier,'name':p['ADMIN'],'parent_id':parent,'reference_owner':None if iso=='ATA' else p['ADMIN'],'metadata':{'source_name':'Natural Earth','source_id':'natural-earth','administrative_level':'ADM0 fallback','source_url':'https://www.naturalearthdata.com/','license':'Public domain','reference_year':'Undated modern reference'}},'geometry':f['geometry']})
    statistics['country_fallback'] += 1

def included(feature):
    parent = units[feature['properties']['parent_id']]
    while parent['parent_id']: parent = units[parent['parent_id']]
    return parent['name'] != 'Antarctica'

features = [f for f in features if included(f)]
used = set()
for feature in features:
    parent = feature['properties']['parent_id']
    while parent:
        used.add(parent); parent = units[parent]['parent_id']
units = {key:value for key,value in units.items() if key in used}
write(ROOT / '.cache/administrative.geojson', {'type':'FeatureCollection','features':features})
write(ROOT / 'data/hierarchy.json', list(units.values()))
write(ROOT / 'data/administrative-sources.json', sources)
print(json.dumps({'locations':len(features),'countries':len(selected),'counts':dict(statistics),'hierarchy':{level:sum(u['level']==level for u in units.values()) for level in ['province','area','region','subcontinent','continent']}}),flush=True)

write(ROOT / 'data/granularity-report.json', {'version':3,'method':policy['principle'],'selections':[{**{k:r[k] for k in ['boundaryISO','boundaryType','admUnitCount','meanAreaSqKM','boundaryYearRepresented','boundaryLicense']},'role':policy['countries'][iso]['role'],'reason':policy['countries'][iso]['reason']} for iso,r in selected.items()]})
