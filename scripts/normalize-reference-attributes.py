"""Retain source evidence for missing biome classes without inventing a category."""
import gzip,json,pathlib
D=pathlib.Path(__file__).resolve().parents[1]/'data/reference-attributes'
index=json.loads((D/'index.json').read_text());assert index['version']==2
missing={i:v for i,v in enumerate(index['values']) if v in ('N/A','Unknown','No data','')}
count=0;types={}
for file in index['parts']:
 rows=json.loads(gzip.decompress((D/file).read_bytes()));changed=False
 for id,records in rows:
  for record in records:
   ti,vi,share,coverage=record
   if vi not in missing:continue
   key=(ti,vi)
   if key not in types:
    t=index['types'][ti];types[key]=len(index['types']);index['types'].append({**t,'status':'unknown','metadata':{**t['metadata'],'source_value':missing[vi],'missing_reason':'Source biome class is not supplied'}})
   record[0]=types[key];count+=1;changed=True
 if changed:(D/file).write_bytes(gzip.compress(json.dumps(rows,separators=(',',':')).encode(),mtime=0))
for vi in missing:index['values'][vi]=None
if count:
 index['vegetation_references']-=count;index['unknown_source_records']=index.get('unknown_source_records',0)+count
 (D/'index.json').write_text(json.dumps(index,separators=(',',':')))
print(json.dumps({'source_missing_classes':count,'known_vegetation_references':index['vegetation_references']}))
