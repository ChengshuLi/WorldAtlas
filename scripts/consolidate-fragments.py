"""Consolidate sourced multipart district pieces and missed formal city types."""
import collections,json,hashlib,math,pathlib,re,unicodedata
from shapely import STRtree,make_valid,union_all
from shapely.geometry import shape,mapping
R=pathlib.Path(__file__).resolve().parents[1];D=R/'data'
def read(p):return json.loads(p.read_text())
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,separators=(',',':')))
def norm(s):return ''.join(c for c in unicodedata.normalize('NFKD',s).casefold() if c.isalnum())
def area(g):return g.area*12364*math.cos(math.radians(g.representative_point().y))
fs=[f for p in read(D/'world-index.json')['parts'] for f in read(D/p)['features']];units={u['id']:u for u in read(D/'hierarchy.json')};report=read(D/'semantic-report.json');gs=[shape(f['geometry']) for f in fs];retired=set();added=[];groups=collections.defaultdict(list)
def merge(ix,main,basis,id=None,name=None):
 ix=sorted(set(ix));assert len(ix)>1 and not any(i in retired for i in ix)
 f=fs[main];p=f['properties'];g=union_all([gs[i] for i in ix]);identifier=id or 'atlas:multipart:'+hashlib.sha256('|'.join(fs[i]['id'] for i in ix).encode()).hexdigest()[:20]
 names=sorted({fs[i]['properties']['name'] for i in ix});meta={**p['metadata'],'source_name':'Atlas source aggregation','source_member_ids':[fs[i]['id'] for i in ix],'location_basis':basis,'search_aliases':sorted(set(p['metadata'].get('search_aliases',[])+names)),'representative_point':list(g.representative_point().coords)[0]}
 added.append({'type':'Feature','id':identifier,'properties':{**p,'id':identifier,'name':name or p['name'],'metadata':meta},'geometry':mapping(g)});retired.update(ix)
 report['changes'].append({'id':identifier,'name':name or p['name'],'basis':basis,'source':meta['source_url'],'source_names':names,'replaces':meta['source_member_ids'],'coverage_error_degrees2':0})
# Formal city types omitted by the earlier city-type vocabulary.
ne=read(R/'.cache/ne_10m_admin_1_states_provinces.json')['features'];tree=STRtree(gs)
for f in ne:
 p=f['properties']
 if p.get('type_en') not in ['Special Municipality'] and p['adm1_code'] not in ['ETH-3133','RWA-3495']:continue
 g=make_valid(shape(f['geometry']));prefix='gb:'+p['adm0_a3']+':'
 ix=[int(i) for i in tree.query(g,predicate='intersects') if int(i) not in retired and fs[int(i)]['properties']['metadata'].get('source_id','').startswith(prefix) and g.intersection(gs[int(i)]).area/gs[int(i)].area>=.5]
 if len(ix)>1:merge(ix,max(ix,key=lambda i:gs[i].area),'Published city administrative territory; constituent districts combined','atlas:city:'+p['adm1_code'],p.get('name_en') or p['name'])
# Disconnected small components sharing an exact source district name are parts
# of its territorial location, not tiny additional settlements. Names must be
# unique locally; generic repeated names separated by distance are never joined.
for i,f in enumerate(fs):
 if i in retired:continue
 p=f['properties'];m=p['metadata'];key=(p['reference_owner'],m.get('source_id'),None if m.get('source_id','').startswith('gb:DEU:') else p['parent_id'],norm(p['name']));groups[key].append(i)
for key,ix in groups.items():
 if len(ix)<2:continue
 main=max(ix,key=lambda i:gs[i].area)
 small=[i for i in ix if i!=main and area(gs[i])<25 and gs[i].area<gs[main].area*.1 and gs[i].distance(gs[main])<.5]
 if small:merge([main]+small,main,'Disconnected components of the same named source district')
# A numerical remainder of a partitioned source ID is not another location.
for i,f in enumerate(fs):
 if i in retired or area(gs[i])>=.001:continue
 m=f['properties']['metadata'];original=m.get('original_id')
 if not original:continue
 targets=[j for j,x in enumerate(fs) if j not in retired and j!=i and x['id'].endswith(':'+original) and norm(x['properties']['name'])==norm(f['properties']['name']) and gs[j].distance(gs[i])<.1]
 if len(targets)==1:merge([i,targets[0]],targets[0],'Source district plus numerical remainder of the same partitioned source ID')
# OSM queries can include neighbours across international edges. Check the
# original relation's dominant country before using its name for a thin seam.
osm={f['id']:shape(f['geometry']) for f in read(R/'.cache/semantic/tkm-osm.geojson')['features']};countries=read(R/'.cache/ne_10m_admin_0_countries.json')['features'];cg=[make_valid(shape(f['geometry'])) for f in countries];ct=STRtree(cg)
for i,f in enumerate(fs):
 if i in retired or f['properties']['metadata'].get('source_name')!='OpenStreetMap district crosswalk':continue
 g=osm[f['properties']['metadata']['source_id']];j=max(map(int,ct.query(g,predicate='intersects')),key=lambda j:g.intersection(cg[j]).area);iso=countries[j]['properties']['ADM0_A3']
 if iso=='TKM':continue
 candidates=[k for k,x in enumerate(fs) if k not in retired and x['properties']['metadata'].get('source_id','').startswith('gb:'+iso+':') and norm(x['properties']['name'])==norm(f['properties']['name']) and g.intersection(gs[k]).area/gs[k].area>.5 and gs[i].distance(gs[k])<.1]
 assert len(candidates)==1,('Cross-border OSM source requires review',f['id'],iso,candidates)
 assert area(gs[i])<5,('Substantive cross-border change',f['id'])
 merge([i,candidates[0]],candidates[0],'Named source district and independently matched OSM border-vintage fragment')
# Expand a demonstrably truncated administrative parent label.
for u in units.values():
 if u['name']=='Region 14' and u['parent_id']=='geo:area:ETH':u['name']='Addis Ababa';u['metadata']['name_source']='Natural Earth ETH-3133, Addis Ababa chartered city'
 if u['name']=='Anatolikis Makedonias kai Thr*':u['name']='East Macedonia and Thrace';u['metadata']['name_source']='https://www.pamth.gov.gr/'
report['retired'].extend({'id':fs[i]['id'],'name':fs[i]['properties']['name']} for i in sorted(retired));fs=[f for i,f in enumerate(fs) if i not in retired]+added;report['locations']=len(fs);report['retired_locations']=len(report['retired']);parts=[]
for i in range(0,len(fs),1500):
 p=f'geography/part-{i//1500}.json';parts.append(p);write(D/p,{'type':'FeatureCollection','features':fs[i:i+1500]})
write(D/'world-index.json',{'parts':parts});write(D/'hierarchy.json',list(units.values()));write(D/'semantic-report.json',report);print('Multipart and city review:',len(added),'consolidated territories;',len(fs),'locations',flush=True)
