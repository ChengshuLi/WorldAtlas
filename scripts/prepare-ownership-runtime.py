#!/usr/bin/env python3
"""Compile exact ownership intervals into bounded century transport buckets.

Parts are streamed one at a time. An ephemeral evidence lookup database avoids
materializing the entire evidence corpus. No atlas database or source data is
modified. Century boundaries do not round, split, or shorten evidence intervals.
"""
import argparse,bisect,gzip,hashlib,json,pathlib,sqlite3,tempfile,os,time,io
try:import resource
except ImportError:resource=None

ROOT=pathlib.Path(__file__).resolve().parents[1]
ENCODING='ownership-v2-century'
def sha(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
 return h.hexdigest()
def load(path):
 with (gzip.open(path,'rt') if str(path).endswith('.gz') else open(path)) as f:return json.load(f)
def dump(value):return json.dumps(value,separators=(',',':'),ensure_ascii=False)
def bucket_ranges(start,end):
 edges=list(range(-3000,0,100))+list(range(1,2028,100))+[2027]
 edges=sorted(set([start,end]+[e for e in edges if start<e<end]))
 return list(zip(edges,edges[1:]))
def name(start):return f'century-{abs(start)}-{"bc" if start<0 else "ad"}.json.gz'
def checked_parts(index,source):
 for entry in index['parts']+index['evidence_parts']:
  path=source/entry['path']
  if sha(path)!=entry['sha256']:raise ValueError(f'Ownership source hash mismatch: {path.name}')
def prepare(source,output):
 started=time.monotonic();index_path=source/'index.json';original=load(index_path)
 if original.get('version')!=2:raise ValueError('Runtime preparation requires ownership v2')
 source_sha=sha(index_path);algorithm_sha=sha(pathlib.Path(__file__));checked_parts(original,source)
 manifest_path=output/'index.json'
 if manifest_path.exists():
  old=load(manifest_path)
  if old.get('source_index_sha256')==source_sha and old.get('algorithm_sha256')==algorithm_sha and all((output/b['path']).exists() and sha(output/b['path'])==b['sha256'] for b in old['buckets']):
   print('Ownership runtime cache is current',flush=True);return old
 output.mkdir(parents=True,exist_ok=True)
 ranges=bucket_ranges(original['valid_from'],original['valid_to']);starts=[a for a,b in ranges]
 shared={k:v for k,v in original.items() if k not in ['parts','evidence_parts','inputs','evidence']}
 buckets=[]
 with tempfile.TemporaryDirectory(prefix='ownership-runtime-',dir=output) as work:
  work=pathlib.Path(work);lookup=sqlite3.connect(work/'evidence.sqlite')
  lookup.execute('PRAGMA journal_mode=OFF');lookup.execute('PRAGMA synchronous=OFF');lookup.execute('PRAGMA cache_size=-16384')
  lookup.execute('CREATE TABLE evidence(id INTEGER PRIMARY KEY,value TEXT NOT NULL)')
  offset=0
  for entry in original['evidence_parts']:
   rows=load(source/entry['path'])
   lookup.executemany('INSERT INTO evidence VALUES (?,?)',((offset+i,dump(v)) for i,v in enumerate(rows)))
   offset+=len(rows);lookup.commit();del rows
  if offset!=original['evidence_records']:raise ValueError('Evidence count does not match source index')
  print(f'Indexed {offset:,} source evidence tuples on disk',flush=True)
  stages=[gzip.open(work/f'{i}.ndjson.gz','wt',compresslevel=1) for i in range(len(ranges))]
  source_intervals=0
  try:
   for n,entry in enumerate(original['parts']):
    part=load(source/entry['path'])
    for location_id,intervals in part:
     selected={}
     for row in intervals:
      a,b=row[:2]
      if a==0 or b==0 or not isinstance(a,int) or not isinstance(b,int) or a>=b or a<original['valid_from'] or b>original['valid_to']:raise ValueError('Invalid original ownership dates')
      source_intervals+=1
      first=max(0,bisect.bisect_right(starts,a)-1);last=bisect.bisect_left(starts,b)
      for i in range(first,last):
       if a<ranges[i][1] and b>ranges[i][0]:selected.setdefault(i,[]).append(row)
     for i,rows in selected.items():stages[i].write(dump([location_id,rows])+'\n')
    del part
    print(f'Partitioned ownership source part {n+1}/{len(original["parts"])}',flush=True)
  finally:
   for f in stages:f.close()
  if source_intervals!=original['intervals']:raise ValueError('Interval count does not match source index')
  cursor=lookup.cursor()
  for i,(a,b) in enumerate(ranges):
   intern={};evidence=[];locations=intervals_count=0;destination=work/name(a)
   with open(destination,'wb') as binary,gzip.GzipFile(filename='',fileobj=binary,mode='wb',compresslevel=9,mtime=0) as zipped,io.TextIOWrapper(zipped,encoding='utf-8') as f:
    f.write(dump({'version':1,'valid_from':a,'valid_to':b,'source_index_sha256':source_sha})[:-1]+',"parts":[[')
    with gzip.open(work/f'{i}.ndjson.gz','rt') as staged:
     for line in staged:
      location_id,rows=json.loads(line)
      for row in rows:
       global_id=row[4]
       if global_id not in intern:
        value=cursor.execute('SELECT value FROM evidence WHERE id=?',(global_id,)).fetchone()
        if value is None:raise ValueError('Missing source evidence tuple')
        intern[global_id]=len(evidence);evidence.append(json.loads(value[0]))
       row[4]=intern[global_id]
      if locations:f.write(',')
      f.write(dump([location_id,rows]));locations+=1;intervals_count+=len(rows)
    f.write(']],"evidence":[')
    for offset in range(0,len(evidence),2000):
     if offset:f.write(',')
     f.write(dump(evidence[offset:offset+2000])[1:-1])
    f.write(']}')
   if destination.stat().st_size>25*1024*1024:raise ValueError(f'Bucket exceeds hosting limit: {destination.name}')
   with gzip.open(destination,'rb') as f:expanded=sum(len(chunk) for chunk in iter(lambda:f.read(1024*1024),b''))
   buckets.append({'valid_from':a,'valid_to':b,'path':destination.name,'sha256':sha(destination),'locations':locations,'intervals':intervals_count,'evidence_records':len(evidence),'compressed_bytes':destination.stat().st_size,'uncompressed_bytes':expanded})
   os.replace(destination,output/destination.name)
   print(f'Compiled bucket {a}..{b}: {intervals_count:,} exact intervals, {len(evidence):,} evidence tuples',flush=True)
   del evidence,intern
  lookup.close()
  if sha(index_path)!=source_sha:raise ValueError('Ownership source index changed during runtime preparation')
  checked_parts(original,source)
  manifest={'version':1,'encoding':ENCODING,'source_index_sha256':source_sha,'algorithm_sha256':algorithm_sha,'footprints_sha256':original['footprints_sha256'],'shared':shared,'buckets':buckets,'source_intervals':source_intervals,'transport_intervals':sum(x['intervals'] for x in buckets),'max_bucket_uncompressed_bytes':max(x['uncompressed_bytes'] for x in buckets),'note':'Century transport buckets preserve original exact half-open intervals and provenance; no year zero or date coarsening.'}
  if resource is not None:manifest['preparation_peak_rss_kib']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
  temporary=output/'index.json.tmp';temporary.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n');os.replace(temporary,manifest_path)
 print(f'Compiled {len(buckets)} ownership runtime buckets in {time.monotonic()-started:.1f}s',flush=True)
 return manifest
if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source',type=pathlib.Path,default=ROOT/'data/ownership-history');parser.add_argument('--output',type=pathlib.Path,default=ROOT/'data/ownership-runtime');args=parser.parse_args();prepare(args.source.resolve(),args.output.resolve())
