"""Deduplicate immutable source labels rather than downloading 300,000 snapshots."""
import collections,gzip,json,pathlib
D=pathlib.Path(__file__).resolve().parents[1]/'data/reference-attributes'
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,separators=(',',':')))
def compact():
 index=json.loads((D/'index.json').read_text())
 if index['version']==2:return
 records=[r for p in index['parts'] for r in json.loads(gzip.decompress((D/p).read_bytes()))];types=[];type_ids={};values=[];value_ids={};rows=collections.defaultdict(list)
 for r in records:
  t={k:v for k,v in r.items() if k not in ['id','location_id','value']};t['metadata']={k:v for k,v in t['metadata'].items() if k not in ['share','coverage']};key=json.dumps(t,sort_keys=True)
  if key not in type_ids:type_ids[key]=len(types);types.append(t)
  if r['value'] not in value_ids:value_ids[r['value']]=len(values);values.append(r['value'])
  rows[r['location_id']].append([type_ids[key],value_ids[r['value']],r['metadata'].get('share'),r['metadata'].get('coverage')])
 allrows=list(rows.items());parts=[]
 for i in range(0,len(allrows),1500):
  name=f'compact-{i//1500}.json.gz';(D/name).write_bytes(gzip.compress(json.dumps(allrows[i:i+1500],separators=(',',':')).encode(),mtime=0));parts.append(name)
 for p in index['parts']:(D/p).unlink()
 source_count=sum(len(json.loads((D.parent/p).read_text())['features']) for p in json.loads((D.parent/'world-index.json').read_text())['parts'])
 index.update(version=2,types=types,values=values,parts=parts,locations=source_count,represented_locations=len(rows));write(D/'index.json',index);print('Compacted',len(records),'references into',len(rows),'location records')
if __name__=='__main__':compact()
