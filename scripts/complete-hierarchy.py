"""Build total, sourced atlas membership; never manufacture polygon cuts.

A whole-territory tier is a cartographic grouping, not a claimed extra government.
The report distinguishes those tiers from distinct source subdivisions.
"""
import collections, csv, gzip, hashlib, json, pathlib, re, unicodedata, urllib.request
from shapely import STRtree, make_valid
from shapely.geometry import shape

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA, CACHE = ROOT / 'data', ROOT / '.cache'
def read(p): return json.loads(p.read_text())
def write(p, value): p.write_text(json.dumps(value, ensure_ascii=False, separators=(',', ':')))
def norm(s): return re.sub('[^a-z0-9]', '', unicodedata.normalize('NFKD', s or '').encode('ascii','ignore').decode().lower())
old = {u['id']: u for u in read(DATA/'hierarchy.json')}
parts = read(DATA/'world-index.json')['parts']
collections_by_part = {p:read(DATA/p) for p in parts}
features = [f for c in collections_by_part.values() for f in c['features']]
ne = read(CACHE/'ne_10m_admin_1_states_provinces.json')['features']
ne_by_iso = collections.defaultdict(list)
for f in ne: ne_by_iso[f['properties']['adm0_a3']].append(f)
codes = {r['ISO3166-1-Alpha-3']:r for r in csv.DictReader((CACHE/'country-codes.csv').open())}
brazil_path=CACHE/'brazil-states-regions.json'
if not brazil_path.exists():
    raw=urllib.request.urlopen('https://servicodados.ibge.gov.br/api/v1/localidades/estados', timeout=60).read()
    brazil_path.write_bytes(gzip.decompress(raw) if raw[:2]==b'\x1f\x8b' else raw)
brazil = {norm(r['nome']):r['regiao']['nome'] for r in read(brazil_path)}
units, indexes, parent_matches = {}, {}, {}
report = {'version':2,'locations':len(features),'matching':collections.Counter(),'whole_territory_units':[], 'low_overlap_matches':[]}

def unit(level, name, parent, basis, source, identity=None, kind='source_group'):
    key = f'{parent or "world"}/{level}:{identity or name}'
    units[key] = {'id':key,'name':name,'level':level,'parent_id':parent,'metadata':{'basis':basis,'source':source,'kind':kind}}
    return key

def ancestors(f):
    chain={}
    p=f['properties']['parent_id']
    while p:
        u=old[p];chain[u['level']]=u;p=u['parent_id']
    return chain

def candidates(key, rows):
    if key not in indexes:
        geometries=[make_valid(shape(f['geometry'])) for f in rows]
        indexes[key]=(rows,geometries,STRtree(geometries) if geometries else None)
    return indexes[key]

def match(geometry, indexed):
    rows, geoms, tree = indexed
    if tree is None: return None,0,None
    values=[]
    for i in tree.query(geometry):
        overlap=geometry.intersection(geoms[int(i)]).area
        if overlap>0: values.append((overlap/geometry.area,int(i)))
    if not values: return None,0,None
    ratio,i=max(values)
    return rows[i],ratio,geoms[i]

for n,f in enumerate(features):
    p=f['properties']; meta=p['metadata']; chain=ancestors(f)
    country=chain['region']['name']; continent=chain['continent']['name']
    subcontinent=chain.get('subcontinent',{}).get('name')
    source_id=meta['source_id']; iso=source_id.split(':')[1] if source_id.startswith('gb:') else f['id'].split('-')[0]
    if iso=='IOT+00?': iso='IOT'
    if not subcontinent:
        row=codes.get(iso,{})
        subcontinent=row.get('Intermediate Region Name') or row.get('Sub-region Name')
        if row.get('Region Name') in ('Africa','Oceania'): continent=row['Region Name']
        assert subcontinent, f'No sourced subcontinent: {f["id"]}'
    root=unit('continent',continent,None,'Geographic continent','Natural Earth / UN M49')
    sub=unit('subcontinent',subcontinent,root,'Published geographic subregion','Natural Earth / UN M49 country-codes')
    region=unit('region',country,sub,'Country or territory in the modern reference','Natural Earth / geoBoundaries')
    geometry=make_valid(shape(f['geometry']))
    parent_level='ADM1' if iso=='CAN' else meta.get('parent_source_level','ADM1')
    gb_path=CACHE/f'geoboundaries/{iso}-{parent_level}.json'
    gb_rows=read(gb_path)['features'] if ('gb',iso) not in indexes and gb_path.exists() else []
    gb_index=indexes.get(('gb',iso)) or candidates(('gb',iso),gb_rows)
    gb,gb_ratio,gb_geometry=match(geometry,gb_index)
    ne_index=indexes.get(('ne',iso)) or candidates(('ne',iso),ne_by_iso.get(iso,[]))
    ne_local,ne_ratio,ne_geometry=match(geometry,ne_index)
    # China's gbOpen ADM1 contains a mislabeled Guangdong and mixed vintages.
    # Prefer the independent, named Natural Earth province crosswalk there.
    if iso=='CHN' and ne_local and ne_ratio>.5:
        province_name=ne_local['properties']['name']; province_geometry=ne_geometry
        province_source='Natural Earth admin-1'; province_key=ne_local['properties']['adm1_code']; ratio=ne_ratio; method='Natural Earth dominant overlap'
    elif gb and gb_ratio>.5:
        province_name=gb['properties'].get('shapeName') or p['name']; province_geometry=gb_geometry
        province_source=f'gb:{iso}:{parent_level}'; province_key=gb['properties']['shapeID']; ratio=gb_ratio; method='geoBoundaries dominant overlap'
    elif ne_local and ne_ratio>.5:
        province_name=ne_local['properties']['name'] or p['name']; province_geometry=ne_geometry
        province_source='Natural Earth admin-1'; province_key=ne_local['properties']['adm1_code']; ratio=ne_ratio; method='Natural Earth dominant overlap'
    else:
        # Retain the actual named territory as a one-location atlas province.
        # This does not guess an administrative parent from a nearest centroid.
        province_name=p['name']; province_geometry=geometry; province_key=f['id']
        province_source=meta['source_name']; ratio=1; method='Source territory envelope'
    parent_key=(iso,province_source,province_key)
    if parent_key not in parent_matches: parent_matches[parent_key]=match(province_geometry,ne_index)
    matched_ne,parent_ratio,_=parent_matches[parent_key]
    np=matched_ne['properties'] if matched_ne and parent_ratio>.5 else {}
    # region, then region_sub: subdivisions must not be placed above their parent.
    area_name=np.get('region') or np.get('region_sub')
    area_source='Natural Earth region / region_sub'; area_kind='source_group'
    if iso=='BRA':
        native=brazil.get(norm(province_name)) or brazil.get(norm(np.get('name')))
        if native:
            area_name={'Norte':'North Brazil','Nordeste':'Northeast Brazil','Centro-Oeste':'Central-West Brazil','Sudeste':'Southeast Brazil','Sul':'South Brazil'}[native]
            area_source='IBGE, Grandes Regiões / state membership'
    if iso=='CHN' and province_name=='Fujian':
        area_name='East China';area_source='Natural Earth East China grouping; Fujian membership curated from geographic region'
    # UK source ADM1 is a constituent nation; source region is a finer level.
    if iso=='GBR' and gb and ne_local and ne_ratio>.5:
        group=ne_local['properties'].get('region')
        if group:
            area_name=gb['properties']['shapeName']; area_source='geoBoundaries GBR ADM1 constituent country'
            province_name=group;province_key=group;province_source='Natural Earth GBR region';method='Named UK regional group';ratio=ne_ratio
    if not area_name or norm(area_name)==norm(province_name):
        area_name=country;area_source='Source country/territory envelope';area_kind='whole_territory'
    area=unit('area',area_name,region,'Whole-territory atlas area; coextensive with its region, not an extra administrative division' if area_kind=='whole_territory' else 'Named administrative or geographic grouping',area_source,kind=area_kind)
    province_kind='whole_territory' if method=='Source territory envelope' or meta['administrative_level'].startswith('ADM1') else 'source_group'
    province=unit('province',province_name,area,'Source territory represented as a single-location province' if province_kind=='whole_territory' else 'Named administrative parent / regional group',province_source,identity=province_key,kind=province_kind)
    p['parent_id']=province
    meta['parent_match']=f'{method}: {ratio:.2%}'
    meta['hierarchy_version']=2
    meta['hierarchy_source']=province_source
    meta['hierarchy_overlap']=round(ratio,6)
    report['matching'][method]+=1
    if ratio<.95: report['low_overlap_matches'].append({'location_id':f['id'],'province':province_name,'overlap':round(ratio,4),'method':method})
    if n%5000==0: print(f'Completed {n}/{len(features)} hierarchy chains',flush=True)

levels=['location','province','area','region','subcontinent','continent']
for f in features:
    expected=levels[1:];current=f['properties']['parent_id']
    for level in expected:
        assert current in units, f['id']
        u=units[current];assert u['level']==level,(f['id'],level,u['level'])
        current=u['parent_id']
    assert current is None
    assert u['name']!='Antarctica'
report['counts']={level:sum(u['level']==level for u in units.values()) for level in levels[1:]}
report['whole_territory_units']=[{'id':u['id'],'name':u['name'],'level':u['level']} for u in units.values() if u['metadata']['kind']=='whole_territory']
report['missing_chains']=0
report['sources']={'brazil':{'url':'https://servicodados.ibge.gov.br/api/v1/localidades/estados','sha256':hashlib.sha256((CACHE/'brazil-states-regions.json').read_bytes()).hexdigest()}}
for part,c in collections_by_part.items(): write(DATA/part,c)
write(DATA/'hierarchy.json',list(units.values()))
write(DATA/'hierarchy-report.json',report)
print(json.dumps({'locations':len(features),'counts':report['counts'],'matching':report['matching'],'whole_territory_units':len(report['whole_territory_units']),'low_overlap_matches':len(report['low_overlap_matches']),'missing_chains':0}),flush=True)
