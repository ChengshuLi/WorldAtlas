import json,gzip,subprocess,hashlib,pathlib
R='/workspace/scratch/127991fc8b8e/worldatlas-primary';H='282d14b4682f738fed6a0e6f3ee0d0e4b775d611';P=pathlib.Path(__file__).parent;d=json.loads((P/'candidate-scope.json').read_text());pins=[]
def raw(p):
 b=subprocess.check_output(['git','--no-lazy-fetch','-C',R,'show',H+':'+p]);pins.append(dict(commit=H,path=p,bytes=len(b),sha256=hashlib.sha256(b).hexdigest()));return b
def j(p):return json.loads(raw(p))
def bound(p):
 b=raw(p['path']);assert len(b)==p['bytes'] and hashlib.sha256(b).hexdigest()==p['sha256'];return b
selector=j('data/ownership-selection.json');bank=json.loads(bound(selector['selected_geography']));selected={};cohort=[]
for logical in ('data/geography/part-8.json','data/geography/part-28.json','data/geography/part-29.json'):
 o=[x for x in bank['overrides'] if x['logical_path']==logical]
 if o:
  b=gzip.decompress(bound(o[0]));assert len(b)==o[0]['decoded_bytes'] and hashlib.sha256(b).hexdigest()==o[0]['decoded_sha256']
 else:b=bound(next(x for x in bank['unchanged_files'] if x['path']==logical))
 canonical={f['id']:f for f in j(logical)['features']}
 for f in json.loads(b)['features']:
  selected[f['id']]=f
  if f.get('properties',{}).get('reference_owner')=='Spain':cohort.append(f['id']);assert f==canonical[f['id']]
semantic=j('data/semantic-report.json')['changes'];direct=aggregate=0;detail=[]
for o in d['owners']:
 f=selected[o['id']];assert f['properties']['parent_id']==o['province_id'];atoms=o['source_atoms'];m=f['properties']['metadata'];changes=[c for c in semantic if c['id']==o['id']]
 if len(atoms)==1:assert atoms==[o['id']] and not changes and m['original_id']==atoms[0].split(':')[-1];direct+=1
 else:
  assert len(changes)==1 and set(changes[0]['replaces'])==set(atoms)==set(m['source_member_ids']);assert changes[0]['source']==m['source_url'] and changes[0]['basis']==m['location_basis'];aggregate+=1
 detail.append(dict(owner=o['index'],id=o['id'],source_atoms=atoms,selected_geometry_sha256=hashlib.sha256((json.dumps(f['geometry'],separators=(',',':'),ensure_ascii=False)+'\n').encode()).hexdigest()))
assert direct==23 and aggregate==90 and len(cohort)==len(set(cohort))
r=dict(accepted=H,selected_owners=113,consumed_atoms=1829,aggregate_owners=aggregate,direct_owners=direct,canonical_spain_owners_in_complete_selected_parts=len(cohort),all_selected_spain_records_equal_canonical=True,all_original_owner_and_source_atom_ancestry_preserved=True,inputs=pins,owners=detail,limitations=['Selected identity/ancestry screening is not source/physical/native qualification.','No source atom may be replaced by a name-only or partial member union.']);(P/'selected-identity-check.json').write_text(json.dumps(r,indent=2)+'\n');print({k:v for k,v in r.items() if k not in ('inputs','owners','limitations')})
