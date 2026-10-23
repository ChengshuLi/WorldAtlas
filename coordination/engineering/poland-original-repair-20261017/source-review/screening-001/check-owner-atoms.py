import json,subprocess,pathlib,hashlib,collections
R='/workspace/scratch/127991fc8b8e/worldatlas-primary';H='282d14b4682f738fed6a0e6f3ee0d0e4b775d611';P=pathlib.Path(__file__).parent;d=json.loads((P/'candidate-scope.json').read_text());wanted={o['id']:o for o in d['owners']};found={};parts=[]
def read(p):return subprocess.check_output(['git','--no-lazy-fetch','-C',R,'show',H+':'+p])
for part in json.loads(read('data/world-index.json'))['parts']:
 b=read('data/'+part);fc=json.loads(b);matches=[f for f in fc['features'] if f['id'] in wanted]
 if matches:
  parts.append(dict(path='data/'+part,bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),owners=len(matches)))
  for f in matches:assert f['id'] not in found;found[f['id']]=f
assert set(found)==set(wanted)
rows=[];est=0
for i,o in wanted.items():
 f=found[i];metadata=f['properties'].get('metadata',{});n=len(o['source_atoms']);est+=n*len(json.dumps(f,separators=(',',':')).encode());rows.append(dict(id=i,owner=o['index'],atoms=n,metadata_keys=list(metadata),source_member_ids_equal=sorted(metadata.get('source_member_ids',[]))==sorted(o['source_atoms']),selected_json_bytes=len(json.dumps(f,separators=(',',':')).encode())))
q=dict(kind='Poland-complete-owner-atom-screen',owners=56,atoms=56,all_original_owner_ids_found=True,selected_feature_repetition_bytes=est,parts=parts,owners_detail=rows,limitations=['Canonical selected-owner record screening only; actual selector-bank readback remains required.','All complete member sets must be reconciled against exact semantic lineage and current selected footprint before qualification.']);(P/'owner-atoms-screen.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(dict(parts=parts,all_owner_ids_found=True,atom_references=56,selected_feature_repetition_bytes=est,exact_member_set_owners=sum(r['source_member_ids_equal'] for r in rows))))
