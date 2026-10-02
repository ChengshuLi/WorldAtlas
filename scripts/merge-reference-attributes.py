"""Combine independently prepared fields without assigning unsupported dates."""
import gzip,hashlib,json,pathlib,sys
R=pathlib.Path(__file__).resolve().parents[1];D=R/'data/reference-attributes'
source=R/(sys.argv[1] if len(sys.argv)>1 else 'data/topography-reference')
index=json.loads((D/'index.json').read_text());extra=json.loads((source/'index.json').read_text())
assert index['version']==extra['version']==2
assert index['footprints_sha256']==extra['footprints_sha256'] and index['locations']==extra['locations']
key=source.name;source_hash=hashlib.sha256((source/'index.json').read_bytes()).hexdigest()
previous=index.get('merged_sources',{}).get(key)
if previous:
 if previous['index_sha256']!=source_hash:raise ValueError('Changed field preparation requires rebuilding the combined references')
 print('Reference field already merged:',key);raise SystemExit
existing_fields={t['attribute'] for t in index['types']}
assert not existing_fields.intersection(t['attribute'] for t in extra['types']), 'Field precedence must be explicit before merging overlapping preparations'
type_offset=len(index['types']);value_offset=len(index['values']);index['types']+=extra['types'];index['values']+=extra['values']
for part in extra['parts']:
 rows=json.loads(gzip.decompress((source/part).read_bytes()))
 for id,records in rows:
  for r in records:r[0]+=type_offset;r[1]+=value_offset
 name=key+'-'+part;(D/name).write_bytes(gzip.compress(json.dumps(rows,separators=(',',':')).encode(),mtime=0));index['parts'].append(name)
index['records']+=extra['records'];index.setdefault('merged_sources',{})[key]={'index_sha256':source_hash,'inputs':extra.get('inputs',{}),'records':extra['records'],'source':extra.get('source'),'license':extra.get('license')}
represented=set()
for p in index['parts']:
 for id,records in json.loads(gzip.decompress((D/p).read_bytes())):represented.add(id)
index['represented_locations']=len(represented)
index['parts_sha256']={p:hashlib.sha256((D/p).read_bytes()).hexdigest() for p in index['parts']}
(D/'index.json').write_text(json.dumps(index,separators=(',',':')))
print(json.dumps({'merged':key,'records':index['records'],'represented_locations':len(represented)}))
