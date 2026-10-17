"""Verify exact prior identity holds and full physical/support applicability.
Usage: python check-source-fitness.py READ_ONLY_REPO INPUT_COMMIT FRESH_OUTPUT
"""
import collections,gzip,hashlib,json,math,os,pathlib,subprocess,sys,time,xml.etree.ElementTree as ET
import numpy as np,shapely
from shapely.geometry import shape
W=pathlib.Path(sys.argv[1]).absolute();C=sys.argv[2];O=pathlib.Path(sys.argv[3]).absolute();H='3b3e9e675cfb37999d5665438f9fbf25bbd4238b';P='coordination/engineering/estonia-native-repair-20261017';started=time.monotonic()
assert O.parent.is_dir() and not O.exists() and all(not p.is_symlink() for p in (O,*O.parents))
assert len(C)==40 and all(c in '0123456789abcdef' for c in C)
inputs={};env={**os.environ,'GIT_NO_LAZY_FETCH':'1','GIT_NO_REPLACE_OBJECTS':'1'};sha=lambda b:hashlib.sha256(b).hexdigest();encode=lambda x:(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n').encode()
def raw(p,c=C):
 assert p and not p.startswith('/') and all(x not in ['', '.', '..'] for x in p.split('/'))
 cmd=['git','-c','protocol.allow=never','-C',str(W)];meta,name=subprocess.check_output(cmd+['ls-tree','-z',c,'--',p],env=env).rstrip(b'\0').split(b'\t');mode,kind,oid=meta.decode().split();assert mode=='100644' and kind=='blob' and name.decode()==p
 b=subprocess.check_output(cmd+['cat-file','blob',oid],env=env);assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==oid
 d={'path':p,'commit':c,'mode':mode,'git_blob_oid':oid,'bytes':len(b),'sha256':sha(b)}
 if p.endswith('.gz'):q=gzip.decompress(b);d.update(decoded_bytes=len(q),decoded_sha256=sha(q))
 inputs[(c,p)]=d;return b
def js(p,c=C):
 b=raw(p,c);return json.loads(gzip.decompress(b) if p.endswith('.gz') else b)
def pin(p,c=C):raw(p,c);return inputs[(c,p)]

a=js(P+'/source-stage/source-scope-assessment.json');stage=js(P+'/source-stage/original-stage-inputs.json');physical=js(P+'/physical-001/whole-target-support.json');diag=js(P+'/native-diagnostic-001/native-diagnostic.json');interpretation=js(P+'/interpretation-001/construction-and-source-limits.json');assert len(interpretation['complete_selected_semantic_followup'])==90
byid={r['id']:r for r in a['target_checks']};bystage={r['target']:r for r in stage};byphysical={r['target']:r for r in physical['results']};assert len(byid)==len(bystage)==len(byphysical)==90
retrieval=js(P+'/official-records/retrieval.json');records={}
for r in retrieval['records']:
 b=raw(P+'/official-records/'+r['official_record_id']+'.xml');assert len(b)==r['bytes'] and sha(b)==r['sha256'];root=ET.fromstring(b);assert root.tag.endswith('oigusakt');text=' '.join(' '.join(root.itertext()).split());assert r['official_record_id'] in text;records[r['official_record_id']]=text
assert '2013-06-27' in records['104072013014'] and 'Maidla' in records['104072013014'] and 'Lüganuse' in records['104072013014']
assert '2014-08-28' in records['129082014015'] and all(t in records['129082014015'] for t in ['Kaarma','Kärla','Lümanda','Lääne-Saare'])
cases=[{'source_id':'gb:EST:ADM2:1311010B12870424653907','official_record':'104072013014','hold_reason':'pre-represented-year municipal identity contradiction','finding':'Maidla appears as a 2017 Municipality, but the complete 2013 regulation forms new Luganuse from old Luganuse, Maidla and Pussi and removes Maidla from the municipal list. No affirmative atlas decision defines this target as a dated historical territory.'},{'source_id':'gb:EST:ADM2:1311010B58868630877292','official_record':'129082014015','hold_reason':'pre-represented-year municipal identity contradiction','finding':'Kaarma remains a distinct 2017 Municipality in the source, while the complete 2014 regulation replaces Kaarma, Karla and Lumanda with Laane-Saare. No affirmative atlas decision resolves the contradictory represented role.'},{'source_id':'gb:EST:ADM2:1311010B45415706107546','official_record':'129082014015','hold_reason':'named merged municipality footprint contradiction','finding':'The named Laane-Saare source footprint is wholly disjoint from the source Kaarma footprint, whereas the regulation defines the new municipality from Kaarma, Karla and Lumanda together. The literal source identifier cannot certify this named merged municipal extent.'}]
g1=shape(bystage[cases[1]['source_id']]['consumed']['geometry']);g2=shape(bystage[cases[2]['source_id']]['consumed']['geometry']);assert g1.is_valid and g2.is_valid and g1.disjoint(g2)
geometry_comparison={'kaamma_source':cases[1]['source_id'],'laane_saare_source':cases[2]['source_id'],'whole_geometries_disjoint':True,'kaarma_bounds':list(g1.bounds),'laane_saare_bounds':list(g2.bounds),'intersection_area_degrees_squared':g1.intersection(g2).area,'laane_saare_covers_kaarma':g2.covers(g1),'purpose':'Independent literal full-source comparison only; area is planar degrees squared, not geodetic area or legal boundary adjudication.'}
for c in cases:
 t=byid[c['source_id']];assert t['source_atoms']==[c['source_id']] and t['metadata']['reference_year']=='2017' and t['metadata']['source_role']=='Municipality';c.update(pixelIndex=t['pixelIndex'],raw_source_name=t['raw_source_name'],selected_name=t['name'],original_cells=t['candidate_cells'],selected_metadata=t['metadata'])
rows=[]
for b in range(18,20):rows+=js(P+f'/frozen-queue/block-{b:03}.json.gz')
cells=[(x,y,o[0],kind) for y,start,end,o,s,kind in rows for x in range(start,end)];allkeys={r[:3] for r in cells};assert len(allkeys)==len(cells)==a['original_cells']
def expand(rs):
 keys=[]
 for row in rs:
  for start,end,owner in row['runs']:keys.extend((x,row['y'],owner) for x in range(start,end))
 assert len(keys)==len(set(keys));return set(keys)
assert expand(diag['requested_rows'])==allkeys;nativeheld=expand(diag['held_rows']);nativesupport=expand(diag['supported_rows']);assert not nativeheld&nativesupport and nativeheld|nativesupport==allkeys
owners={c['pixelIndex'] for c in cases};held=sorted(k for k in allkeys if k[2] in owners);assert len(held)==sum(c['original_cells'] for c in cases)
for c in cases:c['native_cells']=[list(k) for k in held if k[2]==c['pixelIndex']]
foreign={tuple(k) for k in a['foreign_country_native_cells']};assert foreign==nativeheld
latpin=next(x for x in a['inputs'] if 'native-row-latitudes' in x['path']);lb=raw(latpin['path'],latpin['commit']);assert len(lb)==latpin['bytes'] and sha(lb)==latpin['sha256'];lb=gzip.decompress(lb) if latpin['path'].endswith('.gz') else lb;assert len(lb)==latpin.get('decoded_bytes',latpin['bytes']) and sha(lb)==latpin.get('decoded_sha256',latpin['sha256']);lat=np.frombuffer(lb,dtype='<f8')
physical_checks=[];missing=[];issue_contacts=[]
for ident,t in byid.items():
 cs=[r for r in cells if r[2]==t['pixelIndex']];pts=shapely.points([((x+.5)/262166*360-180,float(lat[y])) for x,y,o,k in cs]);r=byphysical[ident];g=shape(bystage[ident]['consumed']['geometry']);assert shapely.covers(g,pts).all();miss=[]
 for k,cl in [('land','mapped_land_support'),('inland-water','mapped_inland_water_support')]:
  ids=[i for i,c in enumerate(cs) if c[3]==k]
  if ids:
   ok=shapely.covers(shape(r['support'][cl]),pts[ids]);miss.extend([list(cs[ids[i]][:3]) for i,v in enumerate(ok) if not v])
 contacts=[]
 for issue in r['issues']:
  g=shape(issue['geometry']);ix=np.flatnonzero(shapely.covers(g,pts));contact={'reason':issue['reason'],'geometry_sha256':sha(encode(issue['geometry'])),'geometry_valid':bool(g.is_valid),'native_cells':[list(cs[int(i)][:3]) for i in ix]};contacts.append(contact);issue_contacts.extend(contact['native_cells'])
 physical_checks.append({'source_id':ident,'pixelIndex':t['pixelIndex'],'original_cells':len(cs),'declared_physical_support_missing':miss,'complete_issue_geometries':contacts});missing.extend(miss)
assert not missing and not issue_contacts
result={'version':1,'original_cells':len(allkeys),'original_intervals':len(rows),'original_owners':len(byid),'identity_hold_cases':cases,'identity_held_cells':len(held),'identity_held_keys':[list(k) for k in held],'territorial_held_cells':len(nativeheld),'identity_territorial_overlap':len(set(held)&nativeheld),'combined_held_cells':len(set(held)|nativeheld),'supported_after_explicit_holds':len(allkeys-(set(held)|nativeheld)),'whole_source_geometry_comparison':geometry_comparison,'physical_target_checks':physical_checks,'physical_issues':sum(len(r['issues']) for r in physical['results']),'physical_issue_native_contacts':len(issue_contacts),'physical_support_missing_cells':len(missing),'official_records':retrieval,'inputs':list(inputs.values()),'limits':['The three entire original owner scopes remain held for affirmative dated identity/coverage contradictions. Same-source native qualification does not resolve those contradictions.','Other 2016/2017 dates alone are not a refusal. Generic open semantic review remains disclosed and is not silently promoted to approval.','All 80 complete physical issue geometries remain literal; zero requested point contact supports only this native scope, not whole-polygon numeric closure or complete physical source fitness.','Complete original source products, all nine whole foreign negative records and historical applicability remain retained; no source/physical replay or coordinate alteration occurs.']}
outputs={'source-fitness-assessment.json':result,'prior-hold-rows.json':{'rows':[{'y':y,'runs':runs} for y,runs in []]}}
ys=collections.defaultdict(list)
for x,y,o in sorted(held,key=lambda k:(k[1],k[0],k[2])):
 if ys[y] and ys[y][-1][1]==x and ys[y][-1][2]==o:ys[y][-1][1]=x+1
 else:ys[y].append([x,x+1,o])
outputs['prior-hold-rows.json']={'rows':[{'y':y,'runs':runs} for y,runs in sorted(ys.items())]};assert expand(outputs['prior-hold-rows.json']['rows'])==set(held)
encoded={n:encode(v) for n,v in outputs.items()};encoded['preparation.json']=encode({'complete':True,'inputs':list(inputs.values()),'outputs':{n:{'bytes':len(b),'sha256':sha(b)} for n,b in encoded.items()},'elapsed_seconds':time.monotonic()-started});assert not O.exists() and all(not p.is_symlink() for p in (O,*O.parents));O.mkdir()
for n,b in encoded.items():
 with (O/n).open('xb') as f:f.write(b)
print(json.dumps({k:result[k] for k in ['original_cells','identity_held_cells','territorial_held_cells','identity_territorial_overlap','combined_held_cells','supported_after_explicit_holds','physical_issues','physical_issue_native_contacts','physical_support_missing_cells']}))
