"""Share repeated ownership evidence while retaining exact dated provenance."""
import gzip,hashlib,json,pathlib
D=pathlib.Path(__file__).resolve().parents[1]/'data/ownership-history'
def compact():
 index=json.loads((D/'index.json').read_text())
 if index['version']==2:return
 owner_ids=list(index['entities']);oi={x:i for i,x in enumerate(owner_ids)};labels=[];li={};source_ids=[];si={};evidence=[];ei={};statuses=['derived','disputed','no-majority','unknown'];parts=[]
 def intern(value,items,lookup):
  if value not in lookup:lookup[value]=len(items);items.append(value)
  return lookup[value]
 for p in index['parts']:
  rows=json.loads(gzip.decompress((D/p['path']).read_bytes()))
  for id,intervals in rows:
   for row in intervals:
    a,b,owner,status,m=row;e=[intern(m['owner_name'],labels,li) if m.get('owner_name') else None,m['share'],m['coverage'],[[oi[c],s] for c,s in m['candidates']],[intern(x,source_ids,si) for x in m['source_record_ids']],1 if m['footprint']=='dated' else 0];key=json.dumps(e,separators=(',',':'));j=intern(key,evidence,ei);row[:]=[a,b,oi[owner] if owner else None,statuses.index(status),j]
  name='compact-'+p['path'];raw=gzip.compress(json.dumps(rows,separators=(',',':')).encode(),mtime=0);(D/name).write_bytes(raw);parts.append({**p,'path':name,'sha256':hashlib.sha256(raw).hexdigest()})
 ep=[]
 for i in range(0,len(evidence),20000):
  name=f'evidence-{i//20000}.json.gz';raw=gzip.compress(('['+','.join(evidence[i:i+20000])+']').encode(),mtime=0);(D/name).write_bytes(raw);ep.append({'path':name,'sha256':hashlib.sha256(raw).hexdigest()})
 old=index['parts'];index.update(version=2,parts=parts,owner_ids=owner_ids,labels=labels,source_ids=source_ids,statuses_order=statuses,evidence_parts=ep,evidence_records=len(evidence),numerical_tolerances={'majority_share_epsilon':1e-8,'candidate_share_epsilon':1e-8,'contradictory_overlap_share_epsilon':1e-6,'edge_densification_degrees':.1,'stored_share_decimal_places':12});(D/'index.json').write_text(json.dumps(index,separators=(',',':')))
 for p in old:(D/p['path']).unlink()
 print('Compacted ownership provenance:',index['intervals'],'intervals,',len(evidence),'unique evidence records')
if __name__=='__main__':compact()
