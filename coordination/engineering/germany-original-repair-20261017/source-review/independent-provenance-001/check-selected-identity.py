import os,json,gzip,subprocess,hashlib,pathlib,collections
R='/workspace/scratch/127991fc8b8e/worldatlas-primary';H='282d14b4682f738fed6a0e6f3ee0d0e4b775d611';C='eb06af616eb876b612fd433d81d632981642799b';P='coordination/engineering/germany-original-repair-20261017/source-stage-001/'
def raw(c,p):return subprocess.check_output(['git','-C',R,'show',c+':'+p],env=dict(os.environ,GIT_NO_LAZY_FETCH='1'))
def j(c,p):return json.loads(raw(c,p))
def bound(p):
 b=raw(H,p['path']);assert len(b)==p['bytes'] and hashlib.sha256(b).hexdigest()==p['sha256'];return b
selector=j(H,'data/ownership-selection.json');bank=json.loads(bound(selector['selected_geography']));selected={};cohort=[]
for logical in ('data/geography/part-6.json','data/geography/part-28.json','data/geography/part-29.json'):
 o=[x for x in bank['overrides'] if x['logical_path']==logical]
 if o:
  b=gzip.decompress(bound(o[0]));assert len(b)==o[0]['decoded_bytes'] and hashlib.sha256(b).hexdigest()==o[0]['decoded_sha256']
 else:b=bound(next(x for x in bank['unchanged_files'] if x['path']==logical))
 canonical={f['id']:f for f in j(H,logical)['features']}
 for f in json.loads(b)['features']:
  selected[f['id']]=f
  if f.get('properties',{}).get('reference_owner')=='Germany':cohort.append(f['id']);assert f==canonical[f['id']]
assert len(cohort)==len(set(cohort))==409
lineage=json.loads(gzip.decompress(raw(H,'coordination/engineering/global-current-cell-work-queue-20261014/lineage.json.gz')));old={r['index']:r for r in lineage['locations']};semantic=j(H,'data/semantic-report.json')['changes'];stages=j(C,P+'original-stage-inputs.json');membership=j(C,P+'source-target-membership.json');by=collections.defaultdict(list)
for s,m in zip(stages,membership):
 f=selected[m['target_id']];assert f==s['selected'];o=old[m['pixelIndex']];assert o['id']==f['id'];assert f['properties']['parent_id']==o['province_id'];assert m['source_id'] in o['source_atoms'];by[m['pixelIndex']].append(m['source_id'])
for ix,atoms in by.items():
 o=old[ix];assert set(atoms)==set(o['source_atoms']);m=selected[o['id']]['properties']['metadata'];changes=[c for c in semantic if c['id']==o['id']]
 if len(atoms)==1:assert atoms==[o['id']] and not changes and m['original_id']==atoms[0].split(':')[-1]
 else:
  assert len(changes)==1 and set(changes[0]['replaces'])==set(atoms)==set(m['source_member_ids']);assert changes[0]['source']==m['source_url'] and changes[0]['basis']==m['location_basis']
assert len(by)==82
r=dict(head=C,accepted=H,selected_owners=82,consumed_atoms=100,complete_german_cohort=409,selected_bytes_bound=True,all_selected_germany_records_equal_canonical=True,all_original_owner_and_source_atom_ancestry_preserved=True)
pathlib.Path('/workspace/shared/worldatlas-recovery/germany-independent-review/selected-identity-check.json').write_text(json.dumps(r,indent=2)+'\n');print(r)
