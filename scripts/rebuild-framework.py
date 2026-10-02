"""Rebuild sourced tier assignments and enumerate remaining semantic reviews.

Stable locations are not cut to meet a count. Italy uses an independently staged
functional partition. Explicit geographic groups never depend on dated owners.
"""
import collections,hashlib,json,pathlib,re,unicodedata
from shapely import STRtree,make_valid
from shapely.geometry import shape
R=pathlib.Path(__file__).resolve().parents[1];D=R/'data';C=R/'.cache/framework'
def read(p):return json.loads(p.read_text())
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,separators=(',',':')))
def slug(s):return re.sub('[^a-z0-9]+','-',unicodedata.normalize('NFKD',s).encode('ascii','ignore').decode().lower()).strip('-')
old={u['id']:u for u in read(D/'hierarchy.json')}
original=[f for p in read(D/'world-index.json')['parts'] for f in read(D/p)['features']]
assert all(f['properties']['metadata'].get('hierarchy_version')!=4 for f in original),'Run from the saved baseline, not over a rebuilt output'
it=read(C/'italy-refinement-report.json');retired=set(it['retired_ids'])
features=[f for f in original if f['id'] not in retired]+read(C/'italy-locations.json')
ne=read(R/'.cache/ne_10m_admin_1_states_provinces.json')['features'];ng=[make_valid(shape(f['geometry'])) for f in ne];nt=STRtree(ng)
china=read(C/'chn-prefectures.json')['features'];cg=[make_valid(shape(f['geometry'])) for f in china];ct=STRtree(cg)
NE='Natural Earth admin-1 regions, subregions and named territories'
NEURL='https://github.com/nvkelso/natural-earth-vector/tree/ca96624a56bd078437bca8184e78163e5039ad19'
CHURL='https://github.com/wmgeolab/geoBoundaries/blob/9469f09/releaseData/gbHumanitarian/CHN/ADM2/geoBoundaries-CHN-ADM2.geojson'
PLAN='https://www.bayarea.gov.hk/filemanager/en/share/pdf/Outline_Development_Plan.pdf'
units={};changes=[];matches=[]
def add(level,name,parent,source,basis,key=None,status='source-backed',url=None,**extra):
 id=f'framework:{level}:{slug(name)}:'+hashlib.sha256(f'{parent}/{key or name}'.encode()).hexdigest()[:12]
 units[id]={'id':id,'name':name,'level':level,'parent_id':parent,'metadata':{'source':source,'source_url':url or NEURL,'basis':basis,'kind':'geographic','framework_status':status,**extra}}
 return id
def ancestors(f):
 p=f['properties']['parent_id'];chain={}
 while p:
  u=old[p];chain[u['level']]=u;p=u['parent_id']
 return chain
def match(g,tree,geoms):
 candidates=[(g.intersection(geoms[int(j)]).area,int(j)) for j in tree.query(g)]
 if not candidates:return None,0
 area,j=max(candidates)
 return (j,area/g.area) if area>0 else (None,0)
europe={}
for name,countries in [('Britain','GBR'),('Ireland','IRL'),('France','FRA MCO'),('Iberia','ESP PRT AND GIB'),('Low Countries','NLD BEL LUX'),('Central Europe','DEU CHE AUT LIE CZE SVK HUN'),('Italy','ITA SMR VAT'),('Southeastern Europe','SVN HRV BIH SRB MNE XKX ALB MKD GRC BGR ROU'),('Nordic Europe','NOR SWE DNK FIN ISL'),('Baltic','EST LVA LTU'),('Eastern European Plain','UKR BLR MDA')]:
 for iso in countries.split():europe[iso]=name
area_field_countries={'FRA','ESP','BEL','GBR','JPN','NZL'}
for number,f in enumerate(features):
 p=f['properties'];m=p['metadata'];chain=ancestors(f);g=shape(f['geometry']);j,ratio=match(g,nt,ng);np=ne[j]['properties'] if j is not None else {};iso=np.get('adm0_a3','')
 continent=chain['continent']['name'];sub=chain['subcontinent']['name'];region_name=chain['region']['name'];area_name=chain['area']['name'];province_name=chain['province']['name'];province_key=chain['province']['id']
 region_source=chain['region']['metadata'].get('source','WGSRPD');region_basis=chain['region']['metadata'].get('basis','Retained published geographic group');region_status='retained-reference'
 area_source=chain['area']['metadata'].get('source','WGSRPD');area_basis=chain['area']['metadata'].get('basis','Retained source area');area_status='retained-reference';area_key=chain['area']['id']
 province_source=chain['province']['metadata'].get('source','Named source geography');province_basis=chain['province']['metadata'].get('basis','Named source group');province_status='retained-reference';province_url=NEURL
 if continent=='Europe' and iso in europe:
  region_name=europe[iso]
  if iso=='GBR' and m.get('geographic_area_code')=='IRE':region_name='Ireland'
  sub='Eastern Europe' if region_name in ['Southeastern Europe','Eastern European Plain','Baltic'] else 'Western Europe'
  region_source='Atlas geographic framework / Natural Earth reference territories';region_basis='Explicit named geographic macro-group; membership uses reference geography and is independent of political owner. Not a historical administrative boundary.';region_status='atlas-defined'
 if iso in area_field_countries and np.get('region') and ratio>=.5:
  area_name=np['region'];area_source=NE;area_basis='Published named region field grouping source local territories';area_status='source-backed';area_key=f'{iso}/{area_name}'
  if iso=='GBR':
   if area_name in ['Greater London','South East']:area_name='London and South East England';area_key='GBR/London-South-East';area_basis='Atlas grouping of the published Greater London and South East regions; preserves the full metropolitan footprint rather than assigning it to historic Middlesex.';area_status='atlas-defined'
   province_name=np.get('region_sub') or np.get('name') or province_name;province_key='GBR/'+province_name;province_source=NE;province_basis='Named source subregional/county grouping; coextensive metropolitan groups are explicitly reviewed.';province_status='source-backed'
  if iso=='JPN':region_name='Japan';region_source=NE;region_basis='Japanese archipelago reference grouping';region_status='atlas-defined'
 elif iso=='JPN' and np.get('name') in ['Saga','Nagasaki']:
  area_name='Kyushu';area_key='JPN/Kyushu';area_source=NE;area_basis='Saga and Nagasaki prefectures on Kyushu; repairs missing source region labels';area_status='atlas-defined';region_name='Japan';region_source=NE;region_status='atlas-defined'
 if iso in ['DEU','BRA','AUS','ZAF'] and np.get('name') and ratio>=.5 and slug(province_name)!=slug(np['name']):
  area_name=np['name'];area_key=f'{iso}/{np["adm1_code"]}';area_source=NE;area_basis='Named state/province envelope above the smaller existing district or physical group';area_status='source-backed'
 if continent=='North America' and iso in ['USA','CAN']:
  if iso=='USA' and np.get('region'):
   region_name={'West':'Western North America','Midwest':'Interior North America','Northeast':'Northeastern North America','South':'Southeastern North America'}[np['region']]
   area_name=np.get('region_sub') or np['name'];area_key=f'USA/{area_name}'
  elif iso=='CAN' and np.get('region'):
   region_name='Subarctic America' if np['region']=='Northern Canada' else 'Western North America' if np.get('region_sub')=='British Columbia' else 'Interior North America' if np.get('region_sub')=='Prairies' else 'Northeastern North America'
   area_name=np.get('region_sub') or np['name'];area_key=f'CAN/{area_name}'
  region_source=NE;region_basis='Atlas macro-group of published North American regional memberships; US/Canadian groups may share a parent, independently of political ownership';region_status='atlas-defined'
  area_source=NE;area_basis='Published named subregion or northern territorial reference';area_status='source-backed'
 if iso=='RUS' and np.get('region_sub') and ratio>=.5:
  area_name=np['region_sub']+' Russia';area_key=f'RUS/{area_name}';area_source=NE;area_basis='Named economic/geographic subregion field; retained as a modern reference, not a historical jurisdiction';area_status='source-backed'
 if f['id']=='atlas:city:GBR-Greater London':
  area_name='London and South East England';area_key='GBR/London-South-East';area_source=NE;area_basis='Atlas grouping of Greater London and South East England; the whole modern metropolitan footprint is retained.';area_status='atlas-defined'
  province_name='Greater London';province_key='GBR/Greater London';province_source=NE;province_basis='Coextensive metropolitan reference group, explicitly listed for tier review';province_status='source-backed'
 if m.get('framework_province'):
  province_name=m['framework_province'];province_key=m['framework_province_key'];province_source=m['framework_source'];province_basis='Whole named local labour systems assigned by greatest overlap to a source province. The resulting atlas footprint is geographic and may differ from the administrative boundary.';province_status='source-backed'
  area_name=m['framework_area'];area_key='ITA/'+area_name;area_source='ISTAT / geoBoundaries Italian regions';area_basis='Published Italian region containing the reference province';area_status='source-backed';region_name='Italy';region_source=NE;region_status='atlas-defined';sub='Western Europe'
 if iso in ['CHN','HKG','MAC'] and continent=='Asia':
  area_name=np.get('name',area_name);area_key='CHN/'+area_name
  if iso in ['HKG','MAC']:area_name='Guangdong';area_key='CHN/Guangdong'
  region_name=np.get('region') or 'East China'
  if region_name=='South Central China':region_name='South China' if area_name in ['Guangdong','Guangxi','Hainan'] else 'Central China'
  if iso in ['HKG','MAC']:region_name='South China'
  area_source=NE;area_basis='Provincial geographic area; Hong Kong and Macau are included geographically without changing their political ownership';area_status='source-backed'
  region_source=NE;region_basis='Published China geographic regions; South Central China is separated into its named Central and South components';region_status='atlas-defined'
  cj,cr=match(g,ct,cg)
  if cj is not None:
   cp=china[cj]['properties'];province_name=cp['shapeName'];province_key='CHN/prefecture/'+cp['shapeID'];province_source='geoBoundaries gbHumanitarian / HDX China ADM2, 2020';province_url=CHURL;province_basis=f'Prefecture-level source territory, greatest geographic overlap {cr:.2%}; county locations remain indivisible';province_status='source-backed' if cr>=.8 else 'review-required'
   m['prefecture_overlap']=round(cr,6)
  if province_name in ['Shenzhen','Hong Kong Special Administrative Region'] or iso=='HKG':
   province_name='Hong Kong–Shenzhen';province_key='GBA/Hong-Kong-Shenzhen';province_source='Greater Bay Area Outline Development Plan (2019), Chapter 3, Section 1';province_url=PLAN;province_basis='Atlas geographic grouping of the explicitly named cooperation pole. This is not an official province or a historical jurisdiction.';province_status='atlas-defined'
  elif province_name in ['Zhuhai','Macao Special Administrative Region'] or iso=='MAC':
   province_name='Macao–Zhuhai';province_key='GBA/Macao-Zhuhai';province_source='Greater Bay Area Outline Development Plan (2019), Chapter 3, Section 1';province_url=PLAN;province_basis='Atlas geographic grouping of the explicitly named cooperation pole. This is not an official province or a historical jurisdiction.';province_status='atlas-defined'
  elif province_name in ['Guangzhou','Foshan']:
   province_name='Guangzhou–Foshan';province_key='GBA/Guangzhou-Foshan';province_source='Greater Bay Area Outline Development Plan (2019), Chapter 3, Section 1';province_url=PLAN;province_basis='Atlas geographic grouping of the explicitly named cooperation pole. This is not an official province or a historical jurisdiction.';province_status='atlas-defined'
 if continent=='Europe':
  region_name={'Northern Europe':'Nordic Europe','Middle Europe':'Central Europe','Southwestern Europe':'Iberia','Eastern Europe':'Eastern European Plain'}.get(region_name,region_name)
  sub='Northern Europe' if region_name in ['Britain','Ireland','Nordic Europe'] else 'Southern Europe' if region_name in ['Italy','Iberia','Southeastern Europe'] else 'Eastern Europe' if region_name in ['Baltic','Eastern European Plain'] else 'Western Europe'
 root=add('continent',continent,None,'Atlas six-continent convention','Antarctica excluded',status='atlas-defined')
 sc=add('subcontinent',sub,root,'Atlas geographic macro-groups','Stable geographic framework, not dated political membership',status='atlas-defined')
 region=add('region',region_name,sc,region_source,region_basis,status=region_status)
 area=add('area',area_name,region,area_source,area_basis,key=area_key,status=area_status)
 province=add('province',province_name,area,province_source,province_basis,key=province_key,status=province_status,url=province_url)
 previous=p['parent_id'];p['parent_id']=province
 m.update(hierarchy_version=4,framework_reference='Modern geographic framework; historical attributes require dated evidence',framework_match={'source':'Natural Earth','id':np.get('adm1_code'),'overlap':round(ratio,6)},hierarchy_source=province_source,parent_match=province_basis)
 changes.append({'location_id':f['id'],'name':p['name'],'old_parent_id':previous,'province_id':province,'area_id':area,'region_id':region,'source_overlap':round(ratio,6)})
 if number%5000==0:print(f'Framework: {number}/{len(features)} locations',flush=True)
# Review every active group, including inherited groups. No stale retired entries.
children=collections.defaultdict(list)
for f in features:children[f['properties']['parent_id']].append(f['id'])
for u in units.values():
 if u['parent_id']:children[u['parent_id']].append(u['id'])
reviews=[]
for u in units.values():
 m=u['metadata'];n=len(children[u['id']]);m['child_count']=n;reasons=[]
 if n==1 and u['level'] in ['province','area']:reasons.append('Single-child tier: geographic role requires individual review')
 if u['level']=='province' and n>25:reasons.append('More than 25 locations: review intermediate geographic groupings')
 if u['level']=='area' and n>20:reasons.append('More than 20 provinces: review area scale')
 if m['framework_status']=='review-required':reasons.append('Source overlap below 80%')
 if m['framework_status']=='retained-reference':reasons.append('Previous reference grouping retained; semantic tier review outstanding')
 m['review_reasons']=reasons
 if reasons:reviews.append({'id':u['id'],'name':u['name'],'level':u['level'],'children':n,'reasons':reasons,'source':m['source']})
levels=['province','area','region','subcontinent','continent']
for f in features:
 p=f['properties']['parent_id']
 for level in levels:assert p in units and units[p]['level']==level;p=units[p]['parent_id']
 assert p is None
parts=[]
for i in range(0,len(features),1500):
 part=f'geography/part-{i//1500}.json';parts.append(part);write(D/part,{'type':'FeatureCollection','features':features[i:i+1500]})
write(D/'world-index.json',{'parts':parts});write(D/'hierarchy.json',list(units.values()))
semantic=read(D/'semantic-report.json');semantic['retired'] += [{'id':f['id'],'name':f['properties']['name'],'reason':'Replaced by sourced Italian local labour systems; historical records remain on original identities'} for f in original if f['id'] in retired]
semantic['changes'] += [{'id':f['id'],'name':f['properties']['name'],'basis':'Published ISTAT local labour system (2011/2018)','source_url':f['properties']['metadata']['source_url']} for f in features if f['id'].startswith('atlas:location:ITA:SLL:')]
semantic['locations']=len(features);write(D/'semantic-report.json',semantic)
counts={l:sum(u['level']==l for u in units.values()) for l in levels}
report={'version':4,'locations':len(features),'counts':counts,'missing_chains':0,'whole_territory_units':[{'id':u['id'],'name':u['name'],'level':u['level']} for u in units.values() if u['level']=='province' and len(children[u['id']])==1],'regional_basis':'Versioned atlas geographic framework using explicit source memberships; retained WGSRPD groups identified individually','before':dict(collections.Counter(u['level'] for u in old.values())),'changes':changes,'review_queue':reviews,'review_scope':'Every active location and parent group. Structural completion is not certification of historical truth or completion of semantic research.','italy':it,'source_counts':dict(collections.Counter(u['metadata']['framework_status'] for u in units.values()))}
change_parts=[]
for i in range(0,len(changes),10000):
 part=f'framework-changes-{i//10000}.json';write(D/part,changes[i:i+10000]);change_parts.append(part)
report.pop('changes');report['change_parts']=change_parts
write(D/'hierarchy-report.json',report)
print(json.dumps({'locations':len(features),'counts':counts,'reviews':len(reviews)}),flush=True)
