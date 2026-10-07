"""Select atlas locations by geographic role, retaining an auditable source crosswalk.

Compact territories and published city territories are single units. Canadian
numbered/unorganized census remainders are replaced by named physical regions.
No historical attributes are redistributed across replacement footprints.
"""
import collections,hashlib,json,math,pathlib,re,urllib.request,urllib.parse,unicodedata
from shapely import STRtree,make_valid,union_all,clip_by_rect
from shapely.geometry import shape,mapping,Polygon
ROOT=pathlib.Path(__file__).resolve().parents[1];DATA=ROOT/'data';CACHE=ROOT/'.cache/semantic';CACHE.mkdir(exist_ok=True)
def read(p):return json.loads(p.read_text())
def write(p,d):p.write_text(json.dumps(d,ensure_ascii=False,separators=(',',':')))
def polygon(g):
    if g.is_empty:return Polygon()
    if g.geom_type in ('Polygon','MultiPolygon'):return g
    return union_all([polygon(p) for p in getattr(g,'geoms',[])])
def parts(g):return list(g.geoms) if g.geom_type=='MultiPolygon' else [g]
def km2(g):
    g=polygon(g)
    result=0
    for p in parts(g):
        if p.is_empty:continue
        rings=[p.exterior,*p.interiors]
        for i,r in enumerate(rings):
            a=0;coords=list(r.coords)
            for (x,y),(xx,yy) in zip(coords,coords[1:]):a+=math.radians((xx-x+180)%360-180)*(math.sin(math.radians(y))+math.sin(math.radians(yy)))
            result+=(1 if i==0 else -1)*abs(a)*6371.0088**2/2
    return result

def norm(s):return re.sub(r'[^a-z0-9]','',unicodedata.normalize('NFKD',s or '').encode('ascii','ignore').decode().lower())

def compact(g,limit):
    a,b,c,d=g.bounds;return km2(g)<=limit and max((c-a)*111.2*math.cos(math.radians((b+d)/2)),(d-b)*111.2)<=150
index=read(DATA/'world-index.json');features=[f for p in index['parts'] for f in read(DATA/p)['features']]
if all(f['properties']['metadata'].get('semantic_version')==1 for f in features):print('Semantic location policy already installed');raise SystemExit
write(CACHE/'input-index.json',index)
# The complete pre-adaptation polygons remain cached; active source records are archived by migration.
write(CACHE/'input.geojson',{'type':'FeatureCollection','features':features})
write(CACHE/'input-hierarchy.json',read(DATA/'hierarchy.json'))
units={u['id']:u for u in read(DATA/'hierarchy.json')};geoms=[shape(f['geometry']) for f in features];tree=STRtree(geoms)
retired=set();added=[];changes=[];warnings=[]
# WGSRPD areas in Canada are named provinces. Use the independently sourced
# province membership where an old coastline crosswalk strayed into a US state.
canadian_area_names={norm(u['name']):u['id'] for u in units.values() if u['level']=='area'}
for u in list(units.values()):
    if u['level']=='province' and u['metadata'].get('source')=='gb:CAN:ADM1':
        target=canadian_area_names.get(norm(u['name']))
        if target and u['parent_id']!=target:
            u['metadata']['area_crosswalk']='Named Canadian province membership overrides coastline-only source mismatch';u['parent_id']=target


def area_of(f):return units[f['properties']['parent_id']]['parent_id']
def dominant_area(indices):
    a=collections.defaultdict(float)
    for i in indices:a[area_of(features[i])]+=km2(geoms[i])
    return max(a,key=a.get)
def province(id,name,area,source,basis,kind='geographic_portion'):
    units[id]={'id':id,'name':name,'level':'province','parent_id':area,'metadata':{'source':source,'basis':basis,'kind':kind}}
    return id
def merge(indices,id,name,basis,source):
    indices=[i for i in indices if i not in retired]
    if len(indices)<2:return
    owners={features[i]['properties']['reference_owner'] for i in indices}
    assert len(owners)==1
    g=polygon(make_valid(union_all([geoms[i] for i in indices])))
    a=dominant_area(indices);parents={features[i]['properties']['parent_id'] for i in indices}
    if len(parents)==1:parent=next(iter(parents))
    else:parent=province('atlas:province:'+id.split(':',1)[1],name,a,source,'Named city/territory represented as one atlas province; coextensive with its location','whole_territory')
    old_names=sorted({features[i]['properties']['name'] for i in indices});aliases=set(old_names+[name.replace(' ','')]);aliases.update(a for i in indices for a in features[i]['properties']['metadata'].get('search_aliases',[]));old_ids=[features[i]['id'] for i in indices]
    if name=='Hong Kong':aliases.update(['Xianggang','Hongkong','香港'])
    m={'source_name':'Atlas source aggregation','source_id':id,'source_url':source,'license':'Underlying source licenses retained in semantic-report.json','reference_year':'Undated modern reference','administrative_level':basis,'location_basis':basis,'representative_point':list(g.representative_point().coords)[0],'search_aliases':sorted(aliases), 'reference_version':3,'hierarchy_version':3,'topology_version':1,'semantic_version':1,'source_member_ids':old_ids}
    added.append({'type':'Feature','id':id,'properties':{'id':id,'name':name,'parent_id':parent,'reference_owner':next(iter(owners)),'metadata':m},'geometry':mapping(g)})
    changes.append({'id':id,'name':name,'basis':basis,'source':source,'replaces':old_ids,'source_names':old_names,'area_km2':round(km2(g),2),'coverage_error_degrees2':0})
    retired.update(indices)

# Repair demonstrable UTF-8-as-Latin-1/Windows-1252 mojibake before name matching.
# Keep the exact original label as an alias for reproducible source lookup.
for f in features:
    name=f['properties']['name']
    if re.search(r'[ÃÂ][\x80-\xbf]|â[€™]',name):
        for codec in ['latin1','cp1252']:
            try:
                decoded=name.encode(codec).decode('utf-8')
                f['properties']['name']=decoded;f['properties']['metadata'].setdefault('search_aliases',[]).append(name);break
            except (UnicodeError,LookupError):pass

name_corrections={
'gb:AUS:ADM2:25037944B15172244637897':('Canberra','https://www.act.gov.au/'),
'gb:COL:ADM2:7082276B33268622823443':('Barranquilla','https://barranquilla.gov.co/'),
'gb:SRB:ADM2:33768554B39192124193600':('Smederevska Palanka','https://smederevskapalanka.rs/'),
'gb:SVK:ADM2:56367889B26614689162342':('Bánovce nad Bebravou','https://www.banovce.sk/'),
'gb:SVK:ADM2:56367889B79509103276820':('Nové Mesto nad Váhom','https://www.nove-mesto.sk/')}
for f in features:
    if f['id'] in name_corrections:
        name,url=name_corrections[f['id']];m=f['properties']['metadata'];m['search_aliases']=list(set(m.get('search_aliases',[])+[f['properties']['name']]))
        m['name_crosswalk']={'original':f['properties']['name'],'source':url,'reason':('Capital territory reference name; not a built-up footprint' if name=='Canberra' else 'Expanded truncated source label / corrected spelling against official municipality name')};f['properties']['name']=name

# The independent MLIT/Geolonia municipality polygons identify all 24 missing
# Japanese names by >94% polygon containment, including one Saitama ward sliver.
jp_crosswalk=read(CACHE/'japan/crosswalk.json')
for row in jp_crosswalk:
    assert row['overlap']>.94
    for f in features:
        if f['properties']['metadata'].get('original_id')==row['id']:
            f['properties']['name']=row['name'];f['properties']['metadata']['name_crosswalk']={**row,'source':'https://github.com/geolonia/japanese-admins/tree/d302c49670b5252970649a6481e25d56c64fd08c','attribution':'MLIT National Land Numerical Information, adapted by Geolonia'}

# Source-confirmed Macau identity. The unnamed CHN source polygon predominantly
# overlaps the same source's named Macau ADM1 (73.5%); the remaining shoreline is
# absent from Natural Earth's older coastline. Retain the complete union and record
# the crosswalk instead of leaving an anonymous duplicate territory.
for f in features:
    if f['properties']['metadata'].get('original_id')=='17275852B34966799109471':
        f['properties']['name']='Macau';f['properties']['reference_owner']='Macau S.A.R'
        f['properties']['metadata']['name_crosswalk']={'source':'geoBoundaries CHN ADM1','source_id':'43563684B97104103456250','overlap':0.735478010487423}

countries=read(ROOT/'.cache/ne_10m_admin_0_countries.json')['features'];country_names={}
macau=next(f['properties'] for f in countries if f['properties']['ADM0_A3']=='MAC')
for f in features:
    if f['id']=='MAC+00?' or f['properties']['metadata'].get('original_id')=='17275852B34966799109471':f['properties']['reference_owner']=macau['ADMIN']
for f in countries:
    p=f['properties']
    for k in [p.get('ADMIN'),p.get('NAME_EN'),p.get('NAME_LONG')]:country_names[k]=p
by_owner=collections.defaultdict(list)
for i,f in enumerate(features):by_owner[f['properties']['reference_owner']].append(i)
# A compact small state/territory is coherent at this atlas scale. Distant island
# chains fail the extent guard even if their summed land area is small.
for owner,ix in sorted(by_owner.items(),key=lambda x:str(x[0])):
    if len(ix)<2:continue
    if sum(km2(geoms[i]) for i in ix)>3000:continue
    g=union_all([geoms[i] for i in ix]);p=country_names.get(owner)
    if p and compact(g,3000):
        merge(ix,'atlas:territory:'+p['ADM0_A3'],p.get('NAME_EN') or p['NAME'],'Compact source country/territory','https://www.naturalearthdata.com/downloads/10m-cultural-vectors/10m-admin-0-countries/')

print('Compact territories grouped',len(changes),flush=True)
ne=read(ROOT/'.cache/ne_10m_admin_1_states_provinces.json')['features']
city_types={'Municipality|Prefecture','Special district','Neutral City','Autonomous City','Capital District','City','Capital','National Capital Area','Capital Region','Federal District','Highly Urbanized City','Independent Component City','City|Municipality|Thanh Pho','Independent City','Provincial City','Metropolis','Metropolitan City','Special Municipality','Federal City','Republican City','Capital Territory','Capital Metropolitan City','Special self-governing city','Special City','Capital City'}
curated_cities={'TUR-2265':'Istanbul','THA-416':'Bangkok','IND-2428':'Delhi','EGY-1533':'Cairo','EGY-1543':'Alexandria','AUT-2331':'Vienna','VNM-462':'Hanoi','CHN-1819':'Shanghai'}
candidates=[]
for f in ne:
    p=f['properties']
    if p['adm1_code'] in curated_cities or p.get('type_en') in city_types or (p['adm0_a3']=='DEU' and p['name'] in ['Berlin','Hamburg','Bremen']):
        g=polygon(make_valid(shape(f['geometry'])));core=max(parts(g),key=lambda x:x.area)
        if compact(core,8000):candidates.append((p['adm1_code'],curated_cities.get(p['adm1_code'],p['name']),core,p['admin'],'Source city territory: '+str(p['type_en'])))
# These published administrative groupings represent the city, rather than its wards.
for country,group,label in [('GBR','Greater London','London'),('PHL','National Capital Region','Metro Manila')]:
    rows=[f for f in ne if f['properties']['adm0_a3']==country and f['properties'].get('region')==group]
    if rows:candidates.append((country+'-'+group,label,union_all([make_valid(shape(f['geometry'])) for f in rows]),rows[0]['properties']['admin'],'Named metropolitan territory: '+group))
# New York City's five boroughs are counties in the source, not five city-level atlas locations.
ny=[i for i,f in enumerate(features) if f['properties']['reference_owner']=='United States of America' and units[f['properties']['parent_id']]['name']=='New York' and re.sub(r' County$','',f['properties']['name']) in {'Bronx','Kings','New York','Queens','Richmond'}]
if len(ny)==5:merge(ny,'atlas:city:USA-New-York-City','New York City','Five boroughs of New York City','https://www.nyc.gov/site/planning/data-maps/open-data/districts-download-metadata.page')
mumbai=[i for i,f in enumerate(features) if i not in retired and f['properties']['reference_owner']=='India' and f['properties']['name'] in ['Mumbai','Mumbai Suburban']]
merge(mumbai,'atlas:city:IND-Mumbai','Mumbai','Mumbai City and Mumbai Suburban districts','https://mumbaicity.gov.in/about-district/')
# Korea's metropolitan-city districts have explicit administrative membership.
# Independent GeoNames ADM2 records (name plus polygon/near-border match) repair
# mislabeled province parents in the boundary layer before any city aggregation.
korea_crosswalk=read(CACHE/'korea-crosswalk.json');korean_cities={'10':'Busan','11':'Seoul','12':'Incheon','15':'Daegu','18':'Gwangju','19':'Daejeon','21':'Ulsan'}
for code,name in korean_cities.items():
    ix=[i for i,f in enumerate(features) if i not in retired and f['properties']['metadata'].get('source_id')=='gb:KOR:ADM2' and korea_crosswalk.get(f['properties']['metadata']['original_id'],{}).get('admin1_code')==code]
    for i in ix:features[i]['properties']['metadata']['verified_city_membership']=korea_crosswalk[features[i]['properties']['metadata']['original_id']]
    merge(ix,'atlas:city:KOR-'+code,name,'Named metropolitan city; verified district membership','https://download.geonames.org/export/dump/KR.zip')

# Larger metro groups take priority over constituent city districts.
ne_names={f['properties']['adm1_code']:f['properties']['name'] for f in ne}
city_membership_audit=[]
for code,name,g,owner,basis in sorted(candidates,key=lambda x:-x[2].area):
    names={norm(name),norm(ne_names.get(code,'')),norm(code.split('-',1)[-1])}
    if name=='Bangkok':names.add('bangkok')
    ix=[];evidence=[]
    for i in tree.query(g.buffer(.15),predicate='intersects'):
        i=int(i)
        if i in retired:continue
        ratio=g.intersection(geoms[i]).area/geoms[i].area
        parent_name=norm(units[features[i]['properties']['parent_id']]['name'])
        parent_match=parent_name in names
        if ratio>=.5 or parent_match:
            ix.append(i);evidence.append({'id':features[i]['id'],'overlap':round(ratio,5),'named_parent_match':parent_match})
    by_country=collections.defaultdict(list)
    for i in ix:by_country[features[i]['properties']['reference_owner']].append(i)
    if not by_country:continue
    group=max(by_country.values(),key=lambda ii:sum(geoms[i].area for i in ii))
    if len(group)>1:
        merge(group,'atlas:city:'+code,name,basis,'https://www.naturalearthdata.com/downloads/10m-cultural-vectors/10m-admin-1-states-provinces/')
        city_membership_audit.append({'city':name,'source':code,'members':[x for x in evidence if x['id'] in {features[i]['id'] for i in group}]})

print('City territories grouped',len(changes),flush=True)
# Saitama's designated-city wards are not independent atlas cities. Combine
# the source city and its unnamed ward fragment under the official city footprint.
jp=[f for f in read(CACHE/'japan/grouped.geojson')['features'] if f['id'].startswith('111')]
jg=union_all([shape(f['geometry']) for f in jp]);jix=[int(i) for i in tree.query(jg,predicate='intersects') if i not in retired and features[int(i)]['properties']['reference_owner']=='Japan' and jg.intersection(geoms[int(i)]).area/geoms[int(i)].area>.9]
merge(jix,'atlas:city:JPN-11100','Saitama','MLIT designated-city territory, including constituent wards','https://github.com/geolonia/japanese-admins/tree/d302c49670b5252970649a6481e25d56c64fd08c')

# The remaining unnamed Japanese feature is a 0.11 km² port/coastline sliver,
# 11 metres from the independent Funabashi municipal boundary. Preserve it as
# part of that city, never as a separate unnamed atlas location.
funabashi=[i for i,f in enumerate(features) if i not in retired and f['properties']['reference_owner']=='Japan' and (f['properties']['name']=='Funabashi' or f['properties']['metadata'].get('original_id')=='22064153B42729341445185')]
assert len(funabashi)==2
merge(funabashi,'atlas:city:JPN-12204','Funabashi','MLIT municipal territory with adjacent source coastline sliver','https://github.com/geolonia/japanese-admins/tree/d302c49670b5252970649a6481e25d56c64fd08c')

# Identify named substantial cities using Natural Earth's sourced reference gazetteer.
# Population is used only to select a reference territorial scale; it is NEVER
# imported as a location's population or historical settlement rank.
city_hosts=set()
for city in read(CACHE/'populated-places.geojson')['features']:
    cp=city['properties']
    if (cp.get('POP_MAX') or 0)<100000:continue
    cg=shape(city['geometry']);names={norm(cp.get(k)) for k in ['NAME','NAMEASCII','NAMEALT','NAME_EN'] if cp.get(k)}
    for i in tree.query(cg,predicate='intersects'):
        i=int(i);name=norm(features[i]['properties']['name'])
        if name in names:city_hosts.add(i)

# Spain: MAPA's published agricultural districts group rural municipalities.
# City municipalities are retained; province boundaries are never crossed by a merge.
sp=read(CACHE/'spain-comarcas.geojson')['features'];sg=[make_valid(shape(f['geometry'])) for f in sp];st=STRtree(sg);sp_groups=collections.defaultdict(list);sp_crosswalk=[]
for i,f in enumerate(features):
    if i in retired or i in city_hosts or f['properties']['reference_owner']!='Spain':continue
    g=geoms[i];hits=[(g.intersection(sg[int(j)]).area/g.area,int(j)) for j in st.query(g,predicate='intersects')]
    ratio,j=max(hits,default=(0,-1))
    if ratio>.5:
        p=sp[j]['properties'];sp_groups[(p['co_comarca'],f['properties']['parent_id'],p['ds_comarca'])].append(i)
        sp_crosswalk.append({'id':f['id'],'comarca':p['co_comarca'],'overlap':round(ratio,5)})
    else:warnings.append({'id':f['id'],'name':f['properties']['name'],'issue':'Spanish municipality has no dominant official comarca match'})
for (key,parent,name),ix in sp_groups.items():
    merge(ix,f'atlas:district:ESP-{key}:'+hashlib.sha256(parent.encode()).hexdigest()[:8],name.title(),'MAPA agricultural district; separately mapped major cities excluded','https://sig.mapa.gob.es/arcgis/rest/services/25830/comunComarcasAgrarias/MapServer/2')

# Brazil's published geographic regions supply named rural districts. Exact
# municipal membership is from IBGE, keyed by municipality + state, never a
# nearest-city clustering. Major city municipalities retain their own identity.
br={};br_names=collections.defaultdict(list);br_state_areas={norm(u['name']):u['id'] for u in units.values() if u['level']=='area'}
for r in read(CACHE/'brazil-municipalities.json'):
    region=r.get('regiao-imediata')
    if region:
        br[(norm(r['nome']),norm(region['regiao-intermediaria']['UF']['nome']))]=region; br_names[norm(r['nome'])].append(region)
br_verified=read(CACHE/'brazil-verified-crosswalk.json');br_by_id={r['id']:r for r in read(CACHE/'brazil-municipalities.json')}
br_groups=collections.defaultdict(list);br_sources={};br_unmatched=[]
for i,f in enumerate(features):
    if i in retired or f['properties']['reference_owner']!='Brazil':continue
    parent=units[f['properties']['parent_id']];state=norm(parent['name']);state={'riograndadonorte':'riograndedonorte','riodejeneiro':'riodejaneiro'}.get(state,state);key=(norm(f['properties']['name']),state);r=br.get(key)
    if r is None and len(br_names[key[0]])==1:r=br_names[key[0]][0]
    if r is None and f['properties']['metadata']['original_id'] in br_verified:
        verified=br_verified[f['properties']['metadata']['original_id']];r=br_by_id[verified['ibge_id']]['regiao-imediata'];f['properties']['metadata']['ibge_crosswalk']=verified
    if r:
        immediate=r;inter=r['regiao-intermediaria'];a=br_state_areas.get(norm(inter['UF']['nome']),area_of(f))
        f['properties']['parent_id']=province(f'atlas:province:BRA-{inter["id"]}:{a.split(":")[-1]}',inter['nome'],a,'IBGE geographic regions 2017','Published intermediate geographic region')
        if i not in city_hosts:br_groups[(r['id'],a)].append(i);br_sources[r['id']]=r
    else:br_unmatched.append({'id':f['id'],'name':f['properties']['name'],'parent':parent['name']})
for (key,a),ix in br_groups.items():
    merge(ix,f'atlas:district:BRA-{key}:{a.split(":")[-1]}',br_sources[key]['nome'],'IBGE immediate geographic region; separately mapped major cities excluded','https://servicodados.ibge.gov.br/api/v1/localidades/municipios')

print('Brazil grouped',len(br_groups),'unmatched',len(br_unmatched),flush=True)
# Canada: named counties/regional districts are the rural tier. Anonymous
# statistical divisions go through physical geography below. City municipalities
# remain whole. Membership is determined against the actual 2021 CD polygons.
cds=read(CACHE/'canada-divisions2021.geojson')['features'];cdg=[]
for f in cds:
    raw=shape(f['geometry']);estimate=raw.area*12364*math.cos(math.radians(raw.representative_point().y))
    if estimate>30000 or re.search(r'^Division|^Region \d|^Unorganized',f['properties'].get('CDNAME',''),re.I):cdg.append(Polygon());continue
    g=polygon(make_valid(raw)).simplify(.005,preserve_topology=True).buffer(0);cdg.append(g if km2(g)<25000 else Polygon())
cdtree=STRtree(cdg)
cd_groups=collections.defaultdict(list);canadian_physical=[];cd_matches=[]
for i,f in enumerate(features):
    if i in retired or f['properties']['reference_owner']!='Canada' or i in city_hosts:continue
    g=geoms[i];hits=[(make_valid(clip_by_rect(g,*cdg[int(j)].bounds)).intersection(cdg[int(j)]).area/g.area,int(j)) for j in cdtree.query(g,predicate='intersects')]
    if i%500==0:print('County crosswalk',i,flush=True)
    ratio,j=max(hits,default=(0,-1));p=cds[j]['properties'] if j>=0 else {};name=p.get('CDNAME','');a=area_of(f)
    if ratio>=.8 and name and not re.search(r'^Division|^Region \d|^Unorganized',name,re.I) and km2(cdg[j])<25000:
        cd_groups[(p['CDUID'],a,name)].append(i);cd_matches.append({'id':f['id'],'CDUID':p['CDUID'],'overlap':round(ratio,5)})
    else:canadian_physical.append(i)
print('Canada county classification',len(cd_groups),'physical candidates',len(canadian_physical),flush=True)
for (key,a,name),ix in cd_groups.items():
    merge(ix,f'atlas:district:CAN-{key}:{a.split(":")[-1]}',name,'Statistics Canada named county / regional district; separately mapped major cities excluded','https://www.arcgis.com/home/item.html?id=24f45c7b49d84aaf8e55e566a7fd670b')

# A political territory must not erase the local subdivisions inside it.
# Repartition coarse Natural Earth Somaliland / Western Sahara reference envelopes
# using actual district boundaries, preserving the envelope's reference owner.
for target,iso in [('SOL+00?','SOM'),('SAH+00?','MAR')]:
    found=next((i for i,f in enumerate(features) if f['id']==target),None)
    if found is None or found in retired:continue
    i=found;f=features[i];original=geoms[i];remaining=original
    source=read(ROOT/f'.cache/geoboundaries/{iso}-ADM2.json')['features'];parent_source=read(ROOT/f'.cache/geoboundaries/{iso}-ADM1.json')['features'];pg=[make_valid(shape(p['geometry'])) for p in parent_source];pt=STRtree(pg);made=[]
    for row in source:
        rg=polygon(make_valid(shape(row['geometry'])));g=polygon(make_valid(remaining.intersection(rg)))
        if g.is_empty or km2(g)<.05:continue
        pp=max([(g.intersection(pg[int(j)]).area,int(j)) for j in pt.query(g,predicate='intersects')],default=(0,-1))[1]
        name=row['properties']['shapeName'];assert name
        a=area_of(f);parent=f['properties']['parent_id']
        if pp>=0:
            pr=parent_source[pp]['properties'];parent=province(f'atlas:province:{target}:{pr["shapeID"]}',pr['shapeName'],a,f'geoBoundaries {iso} ADM1','Named administrative region clipped to reference territorial envelope')
        identifier=f'atlas:district:{target}:{row["properties"]["shapeID"]}'
        meta={**f['properties']['metadata'],'source_name':'Atlas source aggregation','source_id':f'gb:{iso}:ADM2','license':read(DATA/'administrative-sources.json')[f'gb:{iso}:ADM2']['boundaryLicense']+'; reference envelope: Natural Earth public domain','source_url':f'https://www.geoboundaries.org/api/current/gbOpen/{iso}/ADM2/','source_member_ids':[target],'location_basis':'Named district clipped to reference territorial envelope','administrative_level':'District','reference_version':3,'semantic_version':1,'representative_point':list(g.representative_point().coords)[0]}
        added.append({'type':'Feature','id':identifier,'properties':{'id':identifier,'name':name,'parent_id':parent,'reference_owner':f['properties']['reference_owner'],'metadata':meta},'geometry':mapping(g)});made.append(len(added)-1);remaining=polygon(make_valid(remaining.difference(g)))
        changes.append({'id':identifier,'name':name,'basis':meta['location_basis'],'source':meta['source_url'],'replaces':[target],'area_km2':round(km2(g),2)})
    assert made,('No source subdivisions',target)
    # Harmonize only narrow border/coastline differences. Grow existing district
    # edges in small distance bands so a long shoreline is not assigned wholesale
    # to one district. This is a recorded display adjustment, not a new unit.
    assert remaining.area/original.area<.02,('Territory source coverage',target)
    anchors={j:shape(added[j]['geometry']) for j in made}
    for distance in [.001,.005,.01,.025,.05,.1]:
        if remaining.is_empty:break
        for j in made:
            gg=shape(added[j]['geometry']);extra=polygon(make_valid(remaining.intersection(anchors[j].buffer(distance))))
            if extra.is_empty:continue
            added[j]['geometry']=mapping(polygon(make_valid(union_all([gg,extra]))));remaining=polygon(make_valid(remaining.difference(extra)))
            added[j]['properties']['metadata'].setdefault('coastline_adjustments',[]).append({'area_km2':round(km2(extra),4),'distance_band_degrees':distance})
    assert remaining.is_empty or remaining.area<1e-8,('Territory coverage gap',target,km2(remaining))
    retired.add(i)
print('Territorial envelopes refined',flush=True)

# Named physical geography replaces anonymous census remainders, not merely their labels.
bad_pattern=re.compile(r'unorganized|unorganised|^region\s+\d|^division\s*(no\.?\s*)?\d|^unnamed|^unknown|^\?+$',re.I)
canada=[i for i in canadian_physical if i not in retired]
physical=read(CACHE/'aafc-ecoregions.geojson')['features'];eco_groups=collections.defaultdict(list);eco_props={}
for f in physical:
    p=f['properties'];key=p['ECOREGION_ID'];eco_groups[key].append(polygon(make_valid(shape(f['geometry']))));eco_props[key]=p
physical_ids=sorted(eco_groups);physical_geoms=[polygon(make_valid(union_all(eco_groups[k]))) for k in physical_ids];eco_tree=STRtree(physical_geoms)
ecoprovinces={str(float(f['attributes']['ECOPROVINCE_ID'])):f['attributes']['ECOPROVINCE_NAME_EN'] for f in read(CACHE/'aafc-ecoprovinces.json')['features']}
by_area=collections.defaultdict(list)
for i in canada:by_area[area_of(features[i])].append(i)
physical_source='https://www.arcgis.com/home/item.html?id=ee462b0692cc4005aefee69dc44f010d'
physical_outputs=[]
for area,ix in by_area.items():
    original=polygon(make_valid(union_all([geoms[i] for i in ix])));remaining=original;pieces=[]
    for j in sorted(map(int,eco_tree.query(original,predicate='intersects'))):
        g=polygon(make_valid(remaining.intersection(physical_geoms[j])))
        if g.is_empty:continue
        pieces.append([j,g]);remaining=polygon(make_valid(remaining.difference(g)))
    # Coastline/border vintages differ. Harmonize only narrow gaps against
    # adjacent region edges in distance bands; no distant nearest-centre fill.
    repairs=[]
    assert remaining.area/max(original.area,1e-12)<.01,('Physical source coverage',area)
    anchors={j:g for j,g in pieces}
    for distance in [.001,.005,.01,.025,.05,.1]:
        if remaining.is_empty:break
        for item in pieces:
            extra=polygon(make_valid(remaining.intersection(anchors[item[0]].buffer(distance))))
            if extra.is_empty:continue
            item[1]=polygon(make_valid(union_all([item[1],extra])));remaining=polygon(make_valid(remaining.difference(extra)))
            repairs.append({'region':physical_ids[item[0]],'area_km2':round(km2(extra),6),'distance_band_degrees':distance})
    assert remaining.is_empty or remaining.area<1e-8,('Physical coverage gap',area,km2(remaining))
    for j,g in pieces:
        p=eco_props[physical_ids[j]];eco_id=str(p['ECOREGION_ID']);parent_name=ecoprovinces[str(float(p['ECOPROVINCE_ID']))];area_code=area.split(':')[-1]
        parent=province(f'atlas:province:CAN-eco-{p["ECOPROVINCE_ID"]}:{area_code}',parent_name,area,'Agriculture and Agri-Food Canada, National Ecological Framework','Geographic portion of a published ecoprovince within the atlas area')
        identifier=f'atlas:physical:CAN-{eco_id}:{area_code}'
        old=[i for i in ix if g.intersection(geoms[i]).area>1e-10];name=p['ECOREGION_NAME_EN']
        meta={'source_name':'AAFC physical geography adaptation','source_id':'aafc:ecoregion:'+eco_id,'source_url':physical_source,'license':'Open Government Licence – Canada','reference_year':'National Ecological Framework reference','administrative_level':'Named physical region','location_basis':'Named ecoregion portion; separately mapped municipalities excluded','representative_point':list(g.representative_point().coords)[0],'search_aliases':sorted({features[i]['properties']['name'] for i in old}),'source_member_ids':[features[i]['id'] for i in old],'reference_version':3,'hierarchy_version':3,'topology_version':1,'semantic_version':1,'ecoregion_id':p['ECOREGION_ID'],'coastline_adjustments':[r for r in repairs if r['region']==p['ECOREGION_ID']]}
        f={'type':'Feature','id':identifier,'properties':{'id':identifier,'name':name,'parent_id':parent,'reference_owner':'Canada','metadata':meta},'geometry':mapping(g)};added.append(f);physical_outputs.append(f)
        changes.append({'id':identifier,'name':name,'basis':meta['location_basis'],'source':physical_source,'replaces':meta['source_member_ids'],'area_km2':round(km2(g),2),'coastline_adjustments':meta['coastline_adjustments']})
    union=union_all([g for j,g in pieces]);assert original.symmetric_difference(union).area<1e-7,(area,original.symmetric_difference(union).area)
    print('Physical coverage',units[area]['name'],len(ix),'census units →',len(pieces),'named regions',flush=True)
retired.update(canada)
# Replace unnamed Turkmenistan source fragments with named OSM district portions.
# This is a polygon crosswalk, not a point/gazetteer name guess. Named source
# neighbours remain intact; all replacement pieces are explicitly geographical
# portions of the referenced district, with the exact intersection retained.
tkm=[i for i,f in enumerate(features) if i not in retired and f['properties']['reference_owner']=='Turkmenistan' and bad_pattern.search(f['properties']['name'])]
osm=read(CACHE/'tkm-osm.geojson')['features'];og=[shape(f['geometry']) for f in osm];ot=STRtree(og)
tkm_groups=collections.defaultdict(list);tkm_members=collections.defaultdict(set)
for i in tkm:
    remaining=geoms[i];hits=sorted(map(int,ot.query(remaining,predicate='intersects')),key=lambda j:og[j].area)
    for j in hits:
        g=polygon(make_valid(remaining.intersection(og[j])))
        if g.is_empty:continue
        key=(j,features[i]['properties']['parent_id']);tkm_groups[key].append(g);tkm_members[key].add(i);remaining=polygon(make_valid(remaining.difference(g)))
    # Only small seam errors qualify for adjustment; never fill a large unnamed
    # region by assigning it to a distant centre.
    for g in parts(remaining):
        if g.is_empty:continue
        j=int(ot.nearest(g));assert g.distance(og[j])<.02 and g.area/geoms[i].area<.02,('TKM unresolved coverage',features[i]['id'],g.area/geoms[i].area)
        key=(j,features[i]['properties']['parent_id']);tkm_groups[key].append(g);tkm_members[key].add(i)
for (j,parent),gs in tkm_groups.items():
    g=polygon(make_valid(union_all(gs)));tags=osm[j]['properties'];name=tags.get('name:en') or tags['name'];source='https://www.openstreetmap.org/relation/'+osm[j]['id'].split(':')[-1]
    identifier='atlas:district:TKM-'+osm[j]['id'].split(':')[-1]+':'+hashlib.sha256(parent.encode()).hexdigest()[:8]
    members=[features[i]['id'] for i in sorted(tkm_members[(j,parent)])]
    meta={'source_name':'OpenStreetMap district crosswalk','source_id':osm[j]['id'],'source_url':source,'license':'Open Database Licence 1.0; © OpenStreetMap contributors','reference_year':'OSM reference retrieved 2026-10-01','location_basis':'Named district portion replacing unnamed source fragments','administrative_level':'District portion','representative_point':list(g.representative_point().coords)[0],'source_member_ids':members,'reference_version':3,'hierarchy_version':3,'topology_version':1,'semantic_version':1}
    added.append({'type':'Feature','id':identifier,'properties':{'id':identifier,'name':name,'parent_id':parent,'reference_owner':'Turkmenistan','metadata':meta},'geometry':mapping(g)})
    changes.append({'id':identifier,'name':name,'basis':meta['location_basis'],'source':source,'replaces':members,'area_km2':round(km2(g),2)})
retired.update(tkm)

# Incomplete source labels are an explicit outstanding audit finding, not invented names.
for i,f in enumerate(features):
    if i not in retired and bad_pattern.search(f['properties']['name']):warnings.append({'id':f['id'],'name':f['properties']['name'],'source':f['properties']['metadata']['source_id'],'issue':'Source name requires independent geographic verification'})
output=[f for i,f in enumerate(features) if i not in retired]+added
selection_policy=read(DATA/'location-policy.json')['countries']
for f in output:
    m=f['properties']['metadata'];m.update(reference_version=3,semantic_version=1)
    if m.get('source_id','').startswith('gb:'):
        code=m['source_id'].split(':')[1]
        if code in selection_policy:m['source_role']=selection_policy[code]['role']
    f['properties']['name']=f['properties']['name'].strip()

# Every output is either an exact union or a partition of already reconciled coverage.
# Audit new footprints against both new and retained units, then serialize only on success.
fg=[shape(f['geometry']) for f in output];ft=STRtree(fg);new_ids={f['id'] for f in added};overlaps=[]
for i,g in enumerate(fg):
    assert g.is_valid and not g.is_empty,output[i]['id']
    if output[i]['id'] not in new_ids:continue
    for j in ft.query(g,predicate='intersects'):
        j=int(j)
        if j!=i and g.intersection(fg[j]).area>1e-10:overlaps.append((output[i]['id'],output[j]['id'],g.intersection(fg[j]).area))
assert not overlaps,overlaps[:10]
used=set()
for f in output:
    parent=f['properties']['parent_id']
    for level in ['province','area','region','subcontinent','continent']:
        assert parent in units and units[parent]['level']==level
        used.add(parent);parent=units[parent]['parent_id']
    assert parent is None
units={k:u for k,u in units.items() if k in used}
new_parts=[]
for i in range(0,len(output),1500):
    part=f'geography/part-{i//1500}.json';new_parts.append(part);write(DATA/part,{'type':'FeatureCollection','features':output[i:i+1500]})
write(DATA/'world-index.json',{'parts':new_parts});write(DATA/'hierarchy.json',list(units.values()))
report={'version':1,'policy':'Semantic source roles: compact territories; published city territories; named physical geography instead of Canadian census remainders. Size/extent guards prevent merging dispersed archipelagos or sprawling provinces. No target count.','input_locations':len(features),'locations':len(output),'retired_locations':len(retired),'changes':changes,'retired':[{'id':features[i]['id'],'name':features[i]['properties']['name']} for i in sorted(retired)],'korea_membership_crosswalk':korea_crosswalk,'city_membership_audit':city_membership_audit,'spain_municipality_matches':sp_crosswalk,'brazil_unmatched_membership':br_unmatched,'canada_county_matches':cd_matches,'unresolved_source_names':warnings,'sources':{'aafc':{'url':physical_source,'metadata':read(CACHE/'aafc-item.json'),'sha256':hashlib.sha256((CACHE/'aafc-ecoregions.geojson').read_bytes()).hexdigest()},'administrative':'data/administrative-sources.json'},'remaining_new_overlap_pairs':0}
write(DATA/'semantic-report.json',report)
h=read(DATA/'hierarchy-report.json');h['locations']=len(output);h['counts']={l:sum(u['level']==l for u in units.values()) for l in h['counts']};h['missing_chains']=0;write(DATA/'hierarchy-report.json',h)
print(json.dumps({'locations':len(output),'retired':len(retired),'new':len(added),'physical':len(physical_outputs),'unresolved_labels':len(warnings),'counts':h['counts']}),flush=True)
