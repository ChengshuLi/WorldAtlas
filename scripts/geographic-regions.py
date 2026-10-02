"""Assign published geographic regions independently of political ownership."""
import collections, hashlib, json, pathlib, urllib.request
from shapely import STRtree, make_valid
from shapely.geometry import shape
ROOT=pathlib.Path(__file__).resolve().parents[1];DATA=ROOT/'data';CACHE=ROOT/'.cache/wgsrpd';CACHE.mkdir(exist_ok=True)
def read(p):return json.loads(p.read_text())
def write(p,d):p.write_text(json.dumps(d,ensure_ascii=False,separators=(',',':')))
revision='52da7828aba9d461dd133c27b3bd7a4407161f54'
for n in [2,3]:
    p=CACHE/f'level{n}.geojson'
    if not p.exists():p.write_bytes(urllib.request.urlopen(f'https://raw.githubusercontent.com/tdwg/wgsrpd/{revision}/geojson/level{n}.geojson',timeout=60).read())
regions={f['properties']['LEVEL2_COD']:f['properties'] for f in read(CACHE/'level2.geojson')['features']}
areas=[f for f in read(CACHE/'level3.geojson')['features'] if f['properties']['LEVEL2_COD']<91]
geoms=[make_valid(shape(f['geometry'])) for f in areas];tree=STRtree(geoms)
# Atlas macro-groups over the published regions, with no owner/country lookup.
macro={
 10:('Europe','Northern Europe'),11:('Europe','Central and Eastern Europe'),12:('Europe','Southern Europe'),13:('Europe','Southern Europe'),14:('Europe','Central and Eastern Europe'),
 20:('Africa','Northern Africa'),21:('Africa','Northern Africa'),22:('Africa','Western Africa'),23:('Africa','Central Africa'),24:('Africa','Eastern Africa'),25:('Africa','Eastern Africa'),26:('Africa','Southern Africa'),27:('Africa','Southern Africa'),28:('Africa','Atlantic Islands'),29:('Africa','Indian Ocean Islands'),
 30:('Asia','Northern Asia'),31:('Asia','Northern Asia'),32:('Asia','Central Asia'),33:('Asia','Western Asia'),34:('Asia','Western Asia'),35:('Asia','Western Asia'),36:('Asia','Eastern Asia'),37:('Asia','Eastern Asia'),38:('Asia','Eastern Asia'),40:('Asia','Southern Asia'),41:('Asia','Southeastern Asia'),42:('Asia','Southeastern Asia'),43:('Oceania','Melanesia'),
 50:('Oceania','Australasia'),51:('Oceania','Australasia'),60:('Oceania','Melanesia'),61:('Oceania','Polynesia'),62:('Oceania','Micronesia'),63:('Oceania','Polynesia'),
 70:('North America','Northern America'),71:('North America','Northern America'),72:('North America','Northern America'),73:('North America','Northern America'),74:('North America','Northern America'),75:('North America','Northern America'),76:('North America','Northern America'),77:('North America','Northern America'),78:('North America','Northern America'),79:('North America','Mesoamerica'),80:('North America','Mesoamerica'),81:('North America','Caribbean'),
 82:('South America','Northern South America'),83:('South America','Andean South America'),84:('South America','Eastern South America'),85:('South America','Southern South America')}
old={u['id']:u for u in read(DATA/'hierarchy.json')};parts=read(DATA/'world-index.json')['parts'];collections_by_part={p:read(DATA/p) for p in parts}
features=[f for c in collections_by_part.values() for f in c['features']]
if all(f['properties']['metadata'].get('hierarchy_version')==3 for f in features):print('Geographic hierarchy already installed');raise SystemExit
units={};crosswalk=[];province_parts=collections.defaultdict(set);country_regions=collections.defaultdict(set)
source='Brummitt (2001), WGSRPD 2nd ed.; TDWG / Royal Botanic Gardens, Kew'
def unit(id,name,level,parent,basis,kind='geographic'):
    units[id]={'id':id,'name':name,'level':level,'parent_id':parent,'metadata':{'source':source,'basis':basis,'kind':kind}};return id
for i,f in enumerate(features):
    g=shape(f['geometry']); hits=[]
    for j in tree.query(g,predicate='intersects'):
        a=g.intersection(geoms[int(j)]).area
        if a>0:hits.append((a/g.area,int(j)))
    if hits:ratio,j=max(hits);method='largest source overlap'
    else:ratio=0;j=int(tree.nearest(g));method='nearest source coastline (source coverage gap)'
    ap=areas[j]['properties'];code=ap['LEVEL3_COD'];rc=ap['LEVEL2_COD'];continent,sub=macro.get(rc,('Oceania','Southern Ocean Islands'))
    region_id=str(rc);region_name=regions[rc]['LEVEL2_NAM']
    if rc==90:
        continent='South America' if code in ['FAL','SGE','SSA'] else 'Africa' if code in ['TDC','BOU','MPE'] else 'Oceania'
        sub='Southern South America' if continent=='South America' else 'Atlantic Islands' if continent=='Africa' else 'Southern Ocean Islands'
        region_id=f'90-{continent}';region_name='South Atlantic Islands' if continent!='Oceania' else 'Southern Indian Ocean Islands'
    root=unit(f'geo:continent:{continent}',continent,'continent',None,'Six geographic continents; Antarctica excluded')
    sc=unit(f'geo:subcontinent:{sub}',sub,'subcontinent',root,'Documented atlas macro-group of WGSRPD regions')
    region=unit(f'geo:region:{region_id}',region_name,'region',sc,'WGSRPD level 2 geographic region; independent of political ownership')
    area=unit(f'geo:area:{code}',ap['LEVEL3_NAM'],'area',region,'WGSRPD level 3 geographic area; source calls these botanical countries')
    old_province=old[f['properties']['parent_id']];key=hashlib.sha256(old_province['id'].encode()).hexdigest()[:16]
    province=unit(f'geo:province:{key}:{code}',old_province['name'],'province',area,'Named source administrative unit grouped within this geographic area',old_province['metadata'].get('kind','source_group'))
    units[province]['metadata']['source']=old_province['metadata'].get('source','Source administrative geography')
    units[province]['metadata']['original_unit_id']=old_province['id'];province_parts[key].add(code)
    f['properties']['parent_id']=province;m=f['properties']['metadata'];m.update(reference_version=2,hierarchy_version=3,geographic_area_code=code,geographic_region_code=rc,geographic_match=method,geographic_overlap=round(ratio,5))
    country_regions[f['properties']['reference_owner']].add(rc)
    if f['properties']['name']=='Roma' and m.get('source_id','').startswith('gb:ITA:'):m['search_aliases']=['Rome','Metropolitan City of Rome']
    if ratio<.95:crosswalk.append({'location_id':f['id'],'area':code,'overlap':round(ratio,5),'method':method,'distance_degrees':round(g.distance(geoms[j]),6) if not hits else 0})
    if i%5000==0:print(f'Classified {i}/{len(features)} by geography',flush=True)
for u in units.values():
    if u['level']=='province' and len(province_parts[u['id'].split(':')[2]])>1:
        u['metadata']['basis']='Geographic portion of a source administrative unit; not a new government division';u['metadata']['kind']='geographic_portion'
for p,c in collections_by_part.items():write(DATA/p,c)
write(DATA/'hierarchy.json',list(units.values()))
report={'version':3,'locations':len(features),'counts':{l:sum(u['level']==l for u in units.values()) for l in ['province','area','region','subcontinent','continent']},'missing_chains':0,'whole_territory_units':[{'id':u['id'],'name':u['name'],'level':u['level']} for u in units.values() if u['metadata']['kind']=='whole_territory'],'regional_basis':source,'revision':revision,'source_url':'https://github.com/tdwg/wgsrpd','source_hashes':{f'level{n}':hashlib.sha256((CACHE/f'level{n}.geojson').read_bytes()).hexdigest() for n in [2,3]},'attribution':'GIS: RBG Kew, Justin Moat. Metadata states no use constraints; underlying administrative boundaries © 1992–1997 ESRI, GMi, used with permission. Scheme: R. K. Brummitt / TDWG. Classification derived from the source; original GIS boundaries are not republished.','crosswalk_exceptions':crosswalk,'split_province_groups':sum(len(v)>1 for v in province_parts.values()),'country_regions':{k:sorted(v) for k,v in country_regions.items()}}
write(DATA/'hierarchy-report.json',report);print(json.dumps({'counts':report['counts'],'exceptions':len(crosswalk),'nearest':sum(x['method'].startswith('nearest') for x in crosswalk)}))
