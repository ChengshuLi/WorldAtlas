"""Recover named territories omitted by country-wide source selection.

Checks every Natural Earth ADM1 footprint. Supplements absent named territories
and city territories missing their major-city centre. Existing reference polygons
win shared interiors; coast/lake vintage differences are reported, not inferred.
"""
import ast,collections,hashlib,json,pathlib,re,sys,unicodedata
from shapely import STRtree,make_valid,union_all
from shapely.geometry import shape,mapping,Polygon
R=pathlib.Path(__file__).resolve().parents[1];D=R/'data';C=R/'.cache'
def read(p):return json.loads(p.read_text())
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,separators=(',',':')))
def poly(g):
 if g.is_empty:return Polygon()
 if g.geom_type in ['Polygon','MultiPolygon']:return g
 return union_all([poly(q) for q in getattr(g,'geoms',[])])
fs=[f for p in read(D/'world-index.json')['parts'] for f in read(D/p)['features']]
if '--refresh' not in sys.argv and all(f['properties']['metadata'].get('coverage_version')==1 for f in fs):print('Named territory coverage already checked');raise SystemExit
units={u['id']:u for u in read(D/'hierarchy.json')};gs=[shape(f['geometry']) for f in fs];tree=STRtree(gs)
areas=[f for f in read(C/'wgsrpd/level3.geojson')['features'] if f['properties']['LEVEL2_COD']<91];ags=[make_valid(shape(f['geometry'])) for f in areas];at=STRtree(ags)
regions={f['properties']['LEVEL2_COD']:f['properties'] for f in read(C/'wgsrpd/level2.geojson')['features']}
macro=next(ast.literal_eval(n.value) for n in ast.parse((R/'scripts/geographic-regions.py').read_text()).body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='macro' for t in n.targets))
places=[f for f in read(C/'semantic/populated-places.geojson')['features'] if f['properties']['POP_MAX']>=100000 or f['properties']['FEATURECLA']=='Admin-0 capital'];pg=[shape(f['geometry']) for f in places];pt=STRtree(pg)
report=[];added=[]
previous=read(D/'coverage-report.json') if '--refresh' in sys.argv and (D/'coverage-report.json').exists() else {'reviews':[]}
restored={x['source_id']:x for x in previous['reviews'] if 'location_id' in x}
for f in read(C/'ne_10m_admin_1_states_provinces.json')['features']:
 p=f['properties'];g=poly(make_valid(shape(f['geometry'])));name=p.get('name')
 if p['admin']=='Antarctica' or not name:continue
 hits=list(map(int,tree.query(g,predicate='intersects')));occupied=union_all([gs[i].intersection(g) for i in hits]);ratio=occupied.area/g.area
 if ratio>=.9:continue
 absent=ratio<.01 and not any(g.buffer(.05).covers(gs[int(i)].representative_point()) for i in tree.query(g.buffer(.05),predicate='intersects'))
 city_kind=any(t in str(p.get('type_en','')).lower() for t in ['city','capital','metropolis'])
 centres=[int(i) for i in pt.query(g,predicate='intersects')]
 def norm(x):return re.sub(r'[^a-z0-9]','',unicodedata.normalize('NFKD',x).encode('ascii','ignore').decode().lower())
 city_kind=city_kind or any(norm(places[i]['properties']['NAME'])==norm(name) and places[i]['properties']['FEATURECLA']=='Admin-0 capital' for i in centres)
 missing_city=city_kind and any(not len(tree.query(pg[i],predicate='intersects')) and pg[i].distance(gs[int(tree.nearest(pg[i]))])>.02 for i in centres)
 record={'source_id':p['adm1_code'],'name':name,'reference_covered_fraction':round(ratio,6),'decision':'Source coastline, inland-water or boundary-vintage difference; reference retained'}
 if absent or missing_city:
  remainder=poly(make_valid(g.difference(occupied))).simplify(.0001,preserve_topology=True)
  # Simplification cannot reintroduce overlap with the existing source.
  near=[gs[int(i)] for i in tree.query(remainder,predicate='intersects')]
  if near:remainder=poly(make_valid(remainder.difference(union_all(near))))
  for prev in added:remainder=poly(make_valid(remainder.difference(shape(prev['geometry']))))
  assert not remainder.is_empty
  j=max(map(int,at.query(remainder,predicate='intersects')),key=lambda j:remainder.intersection(ags[j]).area,default=int(at.nearest(remainder)));ap=areas[j]['properties'];rc=ap['LEVEL2_COD'];code=ap['LEVEL3_COD'];continent,sub=macro.get(rc,('Oceania','Southern Ocean Islands'));rid=str(rc);rn=regions[rc]['LEVEL2_NAM']
  if rc==90:
   continent='South America' if code in ['FAL','SGE','SSA'] else 'Africa' if code in ['TDC','BOU','MPE'] else 'Oceania';sub='Southern South America' if continent=='South America' else 'Atlantic Islands' if continent=='Africa' else 'Southern Ocean Islands';rid=f'90-{continent}';rn='South Atlantic Islands' if continent!='Oceania' else 'Southern Indian Ocean Islands'
  def unit(id,name,level,parent,basis,kind='geographic'):
   units.setdefault(id,{'id':id,'name':name,'level':level,'parent_id':parent,'metadata':{'source':'WGSRPD / Natural Earth','basis':basis,'kind':kind}});return id
  root=unit('geo:continent:'+continent,continent,'continent',None,'Six continents, Antarctica excluded');sc=unit('geo:subcontinent:'+sub,sub,'subcontinent',root,'Atlas macro-group of WGSRPD regions');region=unit('geo:region:'+rid,rn,'region',sc,'WGSRPD region, independent of ownership');area=unit('geo:area:'+code,ap['LEVEL3_NAM'],'area',region,'WGSRPD geographic area');prov=unit('atlas:province:coverage:'+p['adm1_code'],name,'province',area,'Named source territory; no smaller province asserted','whole_territory')
  id='atlas:coverage:'+p['adm1_code'];meta={'source_name':'Natural Earth','source_url':'https://www.naturalearthdata.com/downloads/10m-cultural-vectors/10m-admin-1-states-provinces/','source_id':'natural-earth:'+p['adm1_code'],'license':'Public domain','reference_year':'Undated modern reference','reference_version':3,'hierarchy_version':3,'topology_version':1,'coverage_version':1,'location_basis':'Named source city territory' if missing_city else 'Named source island / overseas territory','source_role':p.get('type_en') or 'Named territory','representative_point':list(remainder.representative_point().coords)[0],'coverage_reason':'Absent city core' if missing_city else 'Territory omitted by mainland source selection','existing_source_priority':True}
  added.append({'type':'Feature','id':id,'properties':{'id':id,'name':name,'parent_id':prov,'reference_owner':p['admin'],'metadata':meta},'geometry':mapping(remainder)});record.update(decision=meta['coverage_reason'],location_id=id)
 report.append(restored.get(record['source_id'],record))
present={x['source_id'] for x in report};report.extend(x for key,x in restored.items() if key not in present)
fs+=added
for f in fs:f['properties']['metadata']['coverage_version']=1
parts=[]
for i in range(0,len(fs),1500):
 p=f'geography/part-{i//1500}.json';parts.append(p);write(D/p,{'type':'FeatureCollection','features':fs[i:i+1500]})
write(D/'world-index.json',{'parts':parts});write(D/'hierarchy.json',list(units.values()));write(D/'coverage-report.json',{'source':'Natural Earth pinned reference ADM1','scope':'All named reference territories screened; gaps can reflect water or source vintages. This is not a claim of exact global coastline coverage.','added':sum('location_id' in x for x in report),'reviews':report});print('Coverage:',len(added),'named missing territories restored;',len(report),'source differences recorded',flush=True)
