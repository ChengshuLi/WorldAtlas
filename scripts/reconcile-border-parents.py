"""Review tiny border units through their sourced administrative parent footprint.
A coast/border mismatch cannot substitute a foreign source area for that parent.
"""
import collections,copy,hashlib,json,pathlib,re,unicodedata
from shapely import STRtree,make_valid
from shapely.geometry import shape
R=pathlib.Path(__file__).resolve().parents[1];D=R/'data'
def read(p):return json.loads(p.read_text())
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,separators=(',',':')))
def norm(s):return re.sub('[^a-z0-9]','',unicodedata.normalize('NFKD',s).encode('ascii','ignore').decode().lower())
u={x['id']:x for x in read(D/'hierarchy.json')};fs=[f for p in read(D/'world-index.json')['parts'] for f in read(D/p)['features']];w=read(R/'.cache/wgsrpd/level3.geojson')['features'];wg=[make_valid(shape(f['geometry'])) for f in w];wt=STRtree(wg);cache={};results=[];seen={};aliases={'FIN':{'ALD'},'CYP':{'CYN'},'PSE':{'GAZ','WEB'},'KIR':{'KIR+00?'},'MCO':{'MCO+00?'},'AUS':{'IOA'}}
for f in fs:
 p=f['properties'];m=p['metadata'];iso=m.get('regional_match',{}).get('reference_iso');foreign=(m.get('framework_match',{}).get('id') or '').split('-')[0];oldp=u[p['parent_id']];olda=u[oldp['parent_id']]
 if not iso or not foreign or foreign==iso or foreign in aliases.get(iso,set()) or not m.get('source_id','').startswith('gb:'):continue
 key=(iso,oldp['name'])
 if key not in seen:
  path=R/f'.cache/geoboundaries/{iso}-{m.get("parent_source_level","ADM1")}.json'
  if str(path) not in cache:cache[str(path)]=read(path)['features'] if path.exists() else []
  rows=[x for x in cache[str(path)] if norm(x['properties'].get('shapeName',''))==norm(oldp['name'])]
  result={'province_id':oldp['id'],'reference_iso':iso,'foreign_match':foreign,'status':'open','reason':'Local overlap disagrees with source reference territory; parent-based evidence required'}
  if len(rows)==1:
   g=make_valid(shape(rows[0]['geometry']));hits=[(g.intersection(wg[int(j)]).area/g.area,int(j)) for j in wt.query(g)]
   if hits:
    ratio,j=max(hits)
    if ratio>=.8:result.update(status='source-parent-assessed',area_name=w[j]['properties']['LEVEL3_NAM'],area_code=w[j]['properties']['LEVEL3_COD'],overlap=round(ratio,6),source_parent_id=rows[0]['properties']['shapeID'],source_url='https://github.com/tdwg/wgsrpd')
  seen[key]=result
 result=seen[key]
 if result['status']=='source-parent-assessed' and olda['name']!=result['area_name'] and olda['metadata']['framework_status']=='retained-reference':
  aid='atlas:parent-evidence:area:'+hashlib.sha256(f'{olda["parent_id"]}/{result["area_code"]}'.encode()).hexdigest()[:16]
  if aid not in u:
   u[aid]=copy.deepcopy(olda);u[aid].update(id=aid,name=result['area_name']);u[aid]['metadata'].update(basis='Published geographic area assessed against the entire named source administrative parent; small border units remain whole',source_url=result['source_url'],previous_group_id=olda['id'],framework_status='source-backed',review_reasons=['Published reference grouping: semantic tier role remains open'])
  pid='atlas:parent-evidence:province:'+hashlib.sha256(f'{oldp["id"]}/{aid}'.encode()).hexdigest()[:16]
  if pid not in u:u[pid]=copy.deepcopy(oldp);u[pid].update(id=pid,parent_id=aid);u[pid]['metadata']['previous_group_id']=oldp['id']
  p['parent_id']=pid;m['border_parent_assessment']=result;results.append({'location_id':f['id'],'old_parent_id':oldp['id'],'new_parent_id':pid,**result})
 elif result['status']=='open':m['border_parent_review']=result
# Source placeholders must never masquerade as real place names.
for f in fs:
 p=f['properties']
 if p['name'].upper() in ['DATA NOT AVAILABLE','NO DATA','NOT AVAILABLE']:
  parent=u[p['parent_id']];p['metadata'].update(original_source_name=p['name'],name_evidence_status='unknown',semantic_review_reasons=['No named local territory in source; source placeholder retained as provenance']);p['name']='Unnamed territory — '+parent['name']+' reference'
used=set()
for f in fs:
 p=f['properties']['parent_id']
 while p:used.add(p);p=u[p]['parent_id']
u={id:x for id,x in u.items() if id in used};children=collections.Counter(f['properties']['parent_id'] for f in fs);children.update(x['parent_id'] for x in u.values() if x['parent_id'])
for x in u.values():x['metadata']['child_count']=children[x['id']]
for i,part in enumerate(read(D/'world-index.json')['parts']):write(D/part,{'type':'FeatureCollection','features':fs[i*1500:(i+1)*1500]})
write(D/'hierarchy.json',list(u.values()));write(D/'border-parent-review.json',{'profiles':list(seen.values()),'changes':results,'scope':'Every foreign reference match assessed through original sourced parent identity; insufficient evidence stays open'})
print(json.dumps({'source_parent_profiles':len(seen),'corrected_locations':len(results),'open_profiles':sum(x['status']=='open' for x in seen.values())}))
