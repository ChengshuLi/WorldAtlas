"""Join recovered city cores to the retained districts of the same source city."""
import json,pathlib,hashlib
from shapely import STRtree,make_valid,union_all
from shapely.geometry import shape,mapping
R=pathlib.Path(__file__).resolve().parents[1];D=R/'data'
def read(p):return json.loads(p.read_text())
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,separators=(',',':')))
fs=[f for p in read(D/'world-index.json')['parts'] for f in read(D/p)['features']];units={u['id']:u for u in read(D/'hierarchy.json')};report=read(D/'semantic-report.json');gs=[shape(f['geometry']) for f in fs];tree=STRtree(gs);retired=set();new=[]
ne={f['properties']['adm1_code']:f for f in read(R/'.cache/ne_10m_admin_1_states_provinces.json')['features']}
for row in read(D/'coverage-report.json')['reviews']:
 if row['decision']!='Absent city core':continue
 core=next((i for i,f in enumerate(fs) if f['id']==row['location_id']),None)
 if core is None:continue
 f=ne[row['source_id']];p=f['properties'];g=make_valid(shape(f['geometry']));prefix='gb:'+p['adm0_a3']+':'
 members=[int(i) for i in tree.query(g,predicate='intersects') if fs[int(i)]['properties']['metadata'].get('source_id','').startswith(prefix) and gs[int(i)].intersection(g).area/gs[int(i)].area>=.5]
 name=p.get('name_en') or p['name']
 if not members:
  fs[core]['properties']['metadata']['search_aliases']=list(set(fs[core]['properties']['metadata'].get('search_aliases',[])+[p['name'],name]));fs[core]['properties']['name']=name;continue
 owners={fs[i]['properties']['reference_owner'] for i in members};assert len(owners)==1
 indices=members+[core];merged=union_all([gs[i] for i in indices]);id='atlas:city:'+row['source_id'];area=units[fs[core]['properties']['parent_id']]['parent_id'];prov='atlas:province:city:'+row['source_id']
 units[prov]={'id':prov,'name':name,'level':'province','parent_id':area,'metadata':{'source':'Natural Earth / geoBoundaries','kind':'whole_territory','basis':'Published city territory containing its recovered core and source districts'}}
 meta={**fs[core]['properties']['metadata'],'source_name':'Atlas source aggregation','source_id':id,'source_member_ids':[fs[i]['id'] for i in indices],'location_basis':'Published city territory, including recovered source core','semantic_version':1,'reference_version':3,'representative_point':list(merged.representative_point().coords)[0],'search_aliases':sorted({name,p['name']}|{fs[i]['properties']['name'] for i in indices})}
 new.append({'type':'Feature','id':id,'properties':{'id':id,'name':name,'parent_id':prov,'reference_owner':next(iter(owners)),'metadata':meta},'geometry':mapping(merged)});retired.update(indices)
 report['changes'].append({'id':id,'name':name,'basis':meta['location_basis'],'source':meta['source_url'],'replaces':meta['source_member_ids'],'coverage_error_degrees2':0})
report['retired'].extend({'id':fs[i]['id'],'name':fs[i]['properties']['name']} for i in sorted(retired));fs=[f for i,f in enumerate(fs) if i not in retired]+new;report['locations']=len(fs);report['retired_locations']=len(report['retired']);parts=[]
for i in range(0,len(fs),1500):
 p=f'geography/part-{i//1500}.json';parts.append(p);write(D/p,{'type':'FeatureCollection','features':fs[i:i+1500]})
# One canonical reference owner label per source ISO, irrespective of source spelling.
sources=read(D/'administrative-sources.json');canonical={v['boundaryISO']:v['boundaryName'] for v in sources.values()};aliases={}
for country in read(R/'.cache/ne_10m_admin_0_countries.json')['features']:
 p=country['properties'];code=next((p[k] for k in ['ISO_A3_EH','ISO_A3','ADM0_A3'] if p.get(k) in canonical),None)
 if code:aliases[p['ADMIN']]=canonical[code]
for f in fs:
 p=f['properties'];old=p['reference_owner'];new_owner=aliases.get(old,old)
 if new_owner!=old:p['metadata'].setdefault('original_reference_owner',old);p['reference_owner']=new_owner
# Rewrite the same parts after canonicalizing owner names.
for i in range(0,len(fs),1500):write(D/f'geography/part-{i//1500}.json',{'type':'FeatureCollection','features':fs[i:i+1500]})
report['reference_owner_aliases']={k:v for k,v in aliases.items() if k!=v}
write(D/'world-index.json',{'parts':parts});write(D/'hierarchy.json',list(units.values()));write(D/'semantic-report.json',report);print('Recovered city cores:',len(new),'complete territories',flush=True)
