exec(open('argentina-independent-source-review-20261017/audit.py').read().split('rows=read(')[0])
cat=read('coordination/engineering/original-geography-source-corpus-20261006/catalogue.json',B); rec=next(r for r in cat['products']if r['key']=='gb:ARG:ADM2');parts=[]
for p in rec['parts']:
 b=subprocess.check_output(['git','-c','protocol.allow=never','-C',W,'show',B+':'+p['path']]);assert len(b)==p['bytes']and hashlib.sha256(b).hexdigest()==p['sha256'];d=gzip.decompress(b);assert len(d)==p['uncompressed_bytes']and hashlib.sha256(d).hexdigest()==p['uncompressed_sha256'];assert len(b''.join(parts))==p['offset'];parts.append(d)
b=b''.join(parts); assert len(b)==5502879 and hashlib.sha256(b).hexdigest()==rec['original_sha256']=='cedee8710e49d9017327fc1d4b2dc536e95a82317dc94c3bac8d9404af6bf771'
source=json.loads(b);assert len(source['features'])==525;sourceby={'gb:ARG:ADM2:'+f['properties']['shapeID']:f for f in source['features']};stage=read(P+'source-stage-001/original-stage-inputs.json');owners=read(P+'original-scope/screened-package.json')['owners']; byid={o['id']:o for o in owners}; selected={}
for o in owners:
 p=o['target_pin'];key=p['commit'],p['path']
 if key not in selected:
  d=read(p['path'],p['commit']);selected[key]={f['id']:f for f in d['features']}
assessment=read(P+'source-stage-001/source-scope-assessment.json');roster=read(R+'source-feature-roster.json.gz',Q); rb={r['source_id']:r for r in roster}
for i in assessment['source_inventory']:
 f=sourceby[i['source_id']]; assert hashlib.sha256(json.dumps(f['geometry'],separators=(',',':')).encode()).hexdigest()==i['geometry_sha256'];assert rb[i['source_id']]['owners']==i['owners'] and rb[i['source_id']]['source_index']==i['source_index']
assert len(assessment['source_inventory'])==525
for r in stage:
 assert r['consumed']==sourceby[r['target']]
 f=r['selected'];o=byid[f['id']];pin=o['target_pin']; assert f==selected[pin['commit'],pin['path']][f['id']]
 if f['id']!='atlas:city:ARG-5493':assert r['target']==f['id']
print(json.dumps({'head':H,'complete_source_sha256':hashlib.sha256(b).hexdigest(),'source_features':len(sourceby),'whole_staged_features_exact_source_equal':len(stage),'selected_feature_exact_immutable_equal':len(stage),'CABA_member_names':sorted(r['consumed']['properties']['shapeName']for r in stage if r['selected']['id']=='atlas:city:ARG-5493')},indent=2))
