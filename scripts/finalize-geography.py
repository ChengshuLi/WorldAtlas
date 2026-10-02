"""Final serialized geometry check, reference search aliases, and report counts."""
import collections,json,pathlib,hashlib,math,subprocess
from shapely import STRtree,make_valid,union_all
from shapely.geometry import shape,mapping,Polygon
ROOT=pathlib.Path(__file__).resolve().parents[1];D=ROOT/'data';C=ROOT/'.cache/semantic'
subprocess.run(['python',str(ROOT/'scripts/complete-city-cores.py')],check=True)
subprocess.run(['python',str(ROOT/'scripts/complete-taiwan-cities.py')],check=True)
subprocess.run(['python',str(ROOT/'scripts/consolidate-fragments.py')],check=True)
subprocess.run(['python',str(ROOT/'scripts/refresh-angola.py')],check=True)
def read(p):return json.loads(p.read_text())
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,separators=(',',':')))
def poly(g):
 if g.is_empty:return Polygon()
 if g.geom_type in ['Polygon','MultiPolygon']:return g
 return union_all([poly(q) for q in getattr(g,'geoms',[])])
fs=[f for p in read(D/'world-index.json')['parts'] for f in read(D/p)['features']];gs=[shape(f['geometry']) for f in fs];report=read(D/'semantic-report.json');repairs=[]
for attempt in range(3):
 tree=STRtree(gs);found=[]
 for i,g in enumerate(gs):
  assert g.is_valid and not g.is_empty,fs[i]['id']
  for j in tree.query(g,predicate='intersects'):
   j=int(j)
   if j>i:
    shared=g.intersection(gs[j]).area
    if shared>1e-10:found.append((i,j,shared))
 if not found:break
 for i,j,a in found:
  assert a<1e-6,('Substantive overlap',fs[i]['id'],fs[j]['id'],a)
  winner,loser=(i,j) if fs[i]['id']<fs[j]['id'] else (j,i)
  old=gs[loser];gs[loser]=poly(make_valid(old.difference(gs[winner])))
  if gs[loser].intersection(gs[winner]).area>1e-10:gs[loser]=poly(make_valid(old.difference(gs[winner].buffer(1e-10))))
  assert abs(old.union(gs[winner]).area-gs[loser].union(gs[winner]).area)<1e-7
  repairs.append({'id':fs[loser]['id'],'shared_degrees2':a})
else:raise AssertionError('Remaining shared interiors')
for f,g in zip(fs,gs):f['geometry']=mapping(g);f['properties']['metadata']['representative_point']=list(g.representative_point().coords)[0]
tree=STRtree(gs);place_matches=[]
for place in read(C/'populated-places.geojson')['features']:
 p=place['properties'];point=shape(place['geometry']);hits=list(map(int,tree.query(point,predicate='intersects')))
 if not hits:continue
 i=min(hits,key=lambda j:gs[j].area);m=fs[i]['properties']['metadata'];aliases=set(m.get('search_aliases',[]))
 aliases.update(p[k] for k in ['NAME','NAMEASCII','NAME_EN'] if p.get(k));m['search_aliases']=sorted(aliases)
 place_matches.append({'name':p['NAME'],'location_id':fs[i]['id']})
# Distinguish a retained city from a surrounding geographic district of the
# same name. The district's source name remains searchable and in its provenance.
names=collections.defaultdict(list)
for f in fs:names[(f['properties']['reference_owner'],f['properties']['name'])].append(f)
for group in names.values():
 if len(group)<2:continue
 for f in group:
  p=f['properties'];m=p['metadata'];basis=m.get('location_basis','')
  if 'separately mapped major cities excluded' in basis:
   m['source_region_name']=p['name'];m['search_aliases']=sorted(set(m.get('search_aliases',[])+[p['name']]));p['name']+=' surroundings'
units={u['id']:u for u in read(D/'hierarchy.json')};used=set();children=collections.Counter(f['properties']['parent_id'] for f in fs)
for f in fs:
 p=f['properties']['parent_id']
 while p:used.add(p);p=units[p]['parent_id']
units={k:u for k,u in units.items() if k in used}
for id,u in units.items():
 if u['level']=='province' and u['metadata'].get('kind')=='whole_territory' and children[id]>1:
  u['metadata'].update(kind='source_group',basis='Named source territory containing multiple atlas locations')
parts=[]
for i in range(0,len(fs),1500):
 p=f'geography/part-{i//1500}.json';parts.append(p);write(D/p,{'type':'FeatureCollection','features':fs[i:i+1500]})

for old in (D/'geography').glob('part-*.json'):
 if 'geography/'+old.name not in parts:old.unlink()
write(D/'world-index.json',{'parts':parts});write(D/'hierarchy.json',list(units.values()))
report.update(locations=len(fs),serialized_precision_repairs=repairs,reference_place_matches=place_matches,remaining_new_overlap_pairs=0)
report['unresolved_source_names']=[x for x in report['unresolved_source_names'] if x['id'] in {f['id'] for f in fs}]
report['sources'].update({'ibge':{'url':'https://servicodados.ibge.gov.br/api/v1/localidades/municipios','attribution':'IBGE, Brazilian geographic regions (2017); municipal membership snapshot.'},'mapa':{'url':'https://sig.mapa.gob.es/arcgis/rest/services/25830/comunComarcasAgrarias/MapServer/2','attribution':'© Ministerio de Agricultura, Pesca y Alimentación (MAPA); official agricultural districts; free reuse with attribution.'},'statistics_canada':read(C/'canada-divisions2021-item.json'),'japan':{'url':'https://github.com/geolonia/japanese-admins/tree/d302c49670b5252970649a6481e25d56c64fd08c','attribution':'MLIT National Land Numerical Information, adapted by Geolonia (MIT; underlying MLIT government reuse terms).'},'geonames':{'url':'https://download.geonames.org/export/dump/KR.zip','license':'CC BY 4.0','attribution':'GeoNames administrative names and membership; independently matched to source polygons.'},'osm':{'url':'https://www.openstreetmap.org/copyright','license':'Open Database Licence 1.0','attribution':'© OpenStreetMap contributors. Named district polygons for Turkmenistan.'}})
write(D/'semantic-report.json',report)
print('Final geography:',len(fs),'locations;',len(repairs),'numerical seam repairs;',len(place_matches),'reference city/town aliases')
