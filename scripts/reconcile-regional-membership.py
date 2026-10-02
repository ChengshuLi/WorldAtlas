"""Constrain reference matching to source territory before assigning macro-geography.
Dated owners never participate. Preserve local units and record every reparenting.
"""
import collections,copy,hashlib,json,pathlib,re
from shapely import STRtree,make_valid
from shapely.geometry import shape
R=pathlib.Path(__file__).resolve().parents[1];D=R/'data'
def read(p):return json.loads(p.read_text())
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,separators=(',',':')))
fs=[f for p in read(D/'world-index.json')['parts'] for f in read(D/p)['features']];units={u['id']:u for u in read(D/'hierarchy.json')};ne=read(R/'.cache/ne_10m_admin_1_states_provinces.json')['features'];byiso=collections.defaultdict(list)
for f in ne:byiso[f['properties']['adm0_a3']].append(f)
trees={iso:(v,[make_valid(shape(f['geometry'])) for f in v]) for iso,v in byiso.items()}
trees={iso:(v,g,STRtree(g)) for iso,(v,g) in trees.items()}
owneriso={};ownerids={}
for f in read(R/'.cache/ne_10m_admin_0_countries.json')['features']:
 p=f['properties'];iso=p.get('ISO_A3_EH');iso=p['ADM0_A3'] if not iso or iso=='-99' else iso
 for k in ['ADMIN','NAME','NAME_LONG']:
  owneriso[p[k]]=iso;ownerids[p[k]]='owner:'+p['WIKIDATAID'] if p.get('WIKIDATAID') and p['WIKIDATAID']!='-99' else 'owner:reference:'+iso
macro={}
for name,codes in [('Britain','GBR'),('Ireland','IRL'),('France','FRA MCO'),('Iberia','ESP PRT AND GIB'),('Low Countries','NLD BEL LUX'),('Central Europe','DEU CHE AUT LIE CZE SVK HUN'),('Italy','ITA SMR VAT'),('Southeastern Europe','SVN HRV BIH SRB MNE XKX ALB MKD GRC BGR ROU'),('Nordic Europe','NOR SWE DNK FIN ISL'),('Baltic','EST LVA LTU'),('Eastern European Plain','UKR BLR MDA')]:
 for iso in codes.split():macro[iso]=name
subs={'Britain':'Northern Europe','Ireland':'Northern Europe','Nordic Europe':'Northern Europe','Italy':'Southern Europe','Iberia':'Southern Europe','Southeastern Europe':'Southern Europe','Baltic':'Eastern Europe','Eastern European Plain':'Eastern Europe'}
url='https://github.com/nvkelso/natural-earth-vector/tree/ca96624a56bd078437bca8184e78163e5039ad19';changes=[];checks=collections.Counter()
def chain(f):
 a={};p=f['properties']['parent_id']
 while p:a[units[p]['level']]=units[p];p=units[p]['parent_id']
 return a
def clone(u,parent,name=None):
 name=name or u['name']
 if u['parent_id']==parent and u['name']==name:return u['id']
 id='atlas:reparent:'+u['level']+':'+hashlib.sha256(f'{u["id"]}/{parent}/{name}'.encode()).hexdigest()[:16]
 if id not in units:
  units[id]=copy.deepcopy(u);units[id].update(id=id,parent_id=parent,name=name);units[id]['metadata'].update(previous_group_id=u['id'],membership_correction='Source-territory-constrained reference matching; footprint follows member locations')
 return id
group_lookup={(u['level'],u['name'],u['parent_id']):u['id'] for u in units.values()}
def group(level,name,parent,basis):
 existing=group_lookup.get((level,name,parent))
 if existing:return existing
 id='atlas:geographic:'+level+':'+hashlib.sha256(f'{parent}/{name}'.encode()).hexdigest()[:16]
 units[id]={'id':id,'name':name,'level':level,'parent_id':parent,'metadata':{'source':'Atlas geographic framework / Natural Earth reference geography','source_url':url,'basis':basis,'kind':'geographic','framework_status':'atlas-defined','review_reasons':['Macro-geographic boundary and all child memberships require sourced semantic review']}}
 group_lookup[(level,name,parent)]=id
 return id
for i,f in enumerate(fs):
 p=f['properties'];m=p['metadata'];a=chain(f);code=re.search(r'(?:gb:|atlas:local:)([A-Z]{3}):',m.get('source_id','') or f['id']);iso=code.group(1) if code else owneriso.get(p['reference_owner']);np={};ratio=0
 if iso in trees:
  v,g,t=trees[iso];geom=shape(f['geometry']);hits=[(geom.intersection(g[int(j)]).area,int(j)) for j in t.query(geom)]
  if hits:
   overlap,j=max(hits);ratio=overlap/geom.area
   if ratio>=.5:np=v[j]['properties']
 sourceiso=(m.get('framework_match',{}).get('id') or '').split('-')[0];checks['checked']+=1
 if sourceiso and iso and sourceiso!=iso:checks['foreign_reference_match']+=1
 cont=a['continent']['name'];sub=a['subcontinent']['name'];region=a['region']['name'];area=a['area']['name']
 if cont=='Europe' and iso in macro:
  region=macro[iso]
  if iso=='GBR' and (m.get('geographic_area_code')=='IRE' or np.get('name')=='Northern Ireland'):region='Ireland'
  sub=subs.get(region,'Western Europe')
 if iso=='JPN':
  sub='Eastern Asia';region='Japan'
  if np.get('region'):area=np['region']
  elif np.get('name') in ['Saga','Nagasaki']:area='Kyushu'
  elif area in ['Japan','Nansei-shoto']:area='Japanese archipelago — source membership review'
 if iso in ['HKG','MAC']:sub='Eastern Asia';region='South China';area='Guangdong'
 if iso=='CHN' and np.get('region'):
  sub='Eastern Asia';region=np['region']
  if region=='South Central China':region='South China' if np['name'] in ['Guangdong','Guangxi','Hainan'] else 'Central China'
  area=np['name']
 if iso=='CHN' and m.get('geographic_area_code')=='SCS':sub='Southeastern Asia';region='Indo-China';area='South China Sea'
 if cont=='North America' and iso in ['USA','CAN'] and np:
  if iso=='USA':
   zone=np.get('region') or ('South' if np.get('name')=='Florida' else None)
   if zone:region={'West':'Western North America','Midwest':'Interior North America','Northeast':'Northeastern North America','South':'Southeastern North America'}[zone];area=np.get('region_sub') or ('South Atlantic' if np.get('name')=='Florida' else np['name'])
  else:
   zone=np.get('region');state=np.get('name','')
   region='Subarctic America' if zone=='Northern Canada' or state in ['Yukon','Northwest Territories','Nunavut'] else 'Western North America' if state=='British Columbia' else 'Interior North America' if state in ['Alberta','Saskatchewan','Manitoba'] else 'Northeastern North America'
   area=np.get('region_sub') or ('Atlantic Canada' if state in ['Newfoundland and Labrador','Newfoundland','Nova Scotia','New Brunswick','Prince Edward Island'] else state)
 old=p['parent_id'];sc=group('subcontinent',sub,a['continent']['id'],'Country-independent geographic macro-group; retain geographic continental convention')
 reg=group('region',region,sc,'Explicit source-geography membership, constrained to original reference territory before regional matching; independent of dated political owner')
 ar=clone(a['area'],reg,area);pr=clone(a['province'],ar);p['parent_id']=pr
 m['reference_owner_id']=ownerids.get(p['reference_owner'],'owner:reference:'+str(iso))
 m['regional_match']={'reference_iso':iso,'source_id':np.get('adm1_code'),'overlap':round(ratio,6),'method':'reference-territory-constrained overlap'}
 if pr!=old:changes.append({'location_id':f['id'],'old_parent_id':old,'new_parent_id':pr,'old_region_id':a['region']['id'],'region_id':reg,'reference_iso':iso,'source_match':np.get('adm1_code'),'overlap':round(ratio,6)})
 if i%10000==0:print(f'Regional membership: {i}/{len(fs)}',flush=True)
used=set()
for f in fs:
 p=f['properties']['parent_id']
 while p:used.add(p);p=units[p]['parent_id']
units={k:v for k,v in units.items() if k in used};children=collections.Counter(f['properties']['parent_id'] for f in fs);children.update(u['parent_id'] for u in units.values() if u['parent_id'])
for u in units.values():u['metadata']['child_count']=children[u['id']]
for i,part in enumerate(read(D/'world-index.json')['parts']):write(D/part,{'type':'FeatureCollection','features':fs[i*1500:(i+1)*1500]})
write(D/'hierarchy.json',list(units.values()));write(D/'regional-membership-report.json',{'version':1,'checks':dict(checks),'changes':changes,'source_url':url,'scope':'Every location matched against original source reference territory; no dated ownership is consulted. Structural correction does not certify semantic boundaries.'})
print(json.dumps({'locations':len(fs),'changed':len(changes),'checks':dict(checks)}))
