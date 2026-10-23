import json,gzip,subprocess,hashlib
from pathlib import Path
D=Path(__file__).parent; H='2223d85bbe8b18585c221cc1329d115e8e774a42';R=D.parent/'worldatlas-primary'
def read(p,c=H):return json.loads(subprocess.check_output(['git','-C',str(R),'show',c+':'+p]))
s=read('data/ownership-selection.json');bank=read(s['selected_geography']['path']);sc=json.load(open(D/'screening.json'));wanted={o['id']for o in sc['owners']};found={};parts=[];metadata=[]
for pin in bank['unchanged_files']:
 if not pin['path'].startswith('data/geography/'):continue
 fs=read(pin['path'],pin['commit'])['features'];hits=[f for f in fs if f['id']in wanted]
 if not hits:continue
 current={f['id']:f for f in read(pin['path'])['features']}
 assert all(f==current[f['id']]for f in hits)
 found.update({f['id']:f for f in hits});parts.append({'path':pin['path'],'selected_pin':pin,'qualified_scope_features':len(hits)})
assert set(found)==wanted and not wanted.intersection(bank['changed_ids'])
(D/'current-target-pin-checks.json').write_text(json.dumps({'accepted_head':H,'all_original_target_records_equal_selected_bank':True,'targets':len(wanted),'parts':parts,'selected_changes_overlap':[]},indent=2)+'\n')
(D/'current-owner-metadata.json').write_text(json.dumps(list(found.values()),indent=2)+'\n')
print(json.dumps(parts,indent=2));print('metadata variants',[(f['id'],f['properties']['metadata'])for f in list(found.values())[:2]])
