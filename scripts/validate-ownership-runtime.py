#!/usr/bin/env python3
"""Exhaustively verify exact century transport against its ownership-v2 source."""
import argparse, bisect, gzip, hashlib, json, pathlib, struct


def read(path):
 with gzip.open(path,'rt') if str(path).endswith('.gz') else open(path) as stream:return json.load(stream)


def sha(path):
 h=hashlib.sha256()
 with open(path,'rb') as stream:
  for block in iter(lambda:stream.read(1048576),b''):h.update(block)
 return h.hexdigest()


def evidence_hash(row):return hashlib.sha256(json.dumps(row,separators=(',',':'),ensure_ascii=False).encode()).digest()


def signature(identifier,row,evidence):
 name=identifier.encode();a,b,owner,status,_=row
 return struct.pack('<I',len(name))+name+struct.pack('<iiii',a,b,-1 if owner is None else owner,status)+evidence


def validate(source,runtime):
 source_index=read(source/'index.json');manifest=read(runtime/'index.json');source_sha=sha(source/'index.json')
 if manifest['source_index_sha256']!=source_sha or manifest['footprints_sha256']!=source_index['footprints_sha256']:raise ValueError('Runtime/source identity hash differs')
 for key in ['owner_ids','labels','source_ids','statuses_order']:
  if manifest['shared'][key]!=source_index[key]:raise ValueError('Runtime compact dictionary differs: '+key)
 buckets=manifest['buckets'];starts=[b['valid_from'] for b in buckets]
 if not buckets or buckets[0]['valid_from']!=source_index['valid_from'] or buckets[-1]['valid_to']!=source_index['valid_to']:raise ValueError('Runtime date range differs')
 if any(a['valid_to']!=b['valid_from'] for a,b in zip(buckets,buckets[1:])):raise ValueError('Runtime has a gap or overlap')
 expected=[hashlib.sha256() for _ in buckets];counts=[0]*len(buckets);pool=bytearray()
 for entry in source_index['evidence_parts']:
  path=source/entry['path']
  if sha(path)!=entry['sha256']:raise ValueError('Source evidence checksum mismatch')
  for row in read(path):pool.extend(evidence_hash(row))
 if len(pool)!=source_index['evidence_records']*32:raise ValueError('Source evidence count differs')
 intervals=0;locations=0
 for entry in source_index['parts']:
  path=source/entry['path']
  if sha(path)!=entry['sha256']:raise ValueError('Source intervals checksum mismatch')
  for identifier,rows in read(path):
   locations+=1
   for row in rows:
    a,b,_,_,ei=row;intervals+=1
    if not 0<=ei<source_index['evidence_records']:raise ValueError('Source evidence index is out of bounds')
    digest=signature(identifier,row,pool[ei*32:(ei+1)*32]);first=max(0,bisect.bisect_right(starts,a)-1);last=bisect.bisect_left(starts,b)
    for i in range(first,last):
     if a<buckets[i]['valid_to'] and b>buckets[i]['valid_from']:expected[i].update(digest);counts[i]+=1
 if locations!=source_index['locations'] or intervals!=source_index['intervals']:raise ValueError('Source location/interval count differs')
 del pool
 total=0;results=[]
 for i,bucket in enumerate(buckets):
  path=runtime/bucket['path']
  if sha(path)!=bucket['sha256']:raise ValueError('Runtime bucket checksum mismatch')
  data=read(path)
  if data['source_index_sha256']!=source_sha or data['valid_from']!=bucket['valid_from'] or data['valid_to']!=bucket['valid_to']:raise ValueError('Runtime bucket identity differs')
  hashes=[evidence_hash(e) for e in data['evidence']];actual=hashlib.sha256();count=0;location_count=0
  for part in data['parts']:
   for identifier,rows in part:
    location_count+=1
    for row in rows:
     a,b,_,_,ei=row
     if a>=bucket['valid_to'] or b<=bucket['valid_from'] or not 0<=ei<len(hashes):raise ValueError('Runtime contains an inapplicable interval or invalid local evidence index')
     actual.update(signature(identifier,row,hashes[ei]));count+=1
  if count!=counts[i] or actual.digest()!=expected[i].digest():raise ValueError('Decoded exact interval/evidence tuples differ: '+bucket['path'])
  if count!=bucket['intervals'] or location_count!=bucket['locations'] or len(hashes)!=bucket['evidence_records']:raise ValueError('Runtime reported counts differ')
  total+=count;results.append({'path':bucket['path'],'exact_decoded_intervals':count,'decoded_tuple_sha256':actual.hexdigest()});print(f'Exact transport verified {i+1}/{len(buckets)}: {bucket["path"]}',flush=True)
 if total!=manifest['transport_intervals'] or intervals!=manifest['source_intervals']:raise ValueError('Manifest totals differ')
 return {'source_index_sha256':source_sha,'runtime_index_sha256':sha(runtime/'index.json'),'locations':locations,'source_intervals':intervals,'transport_intervals':total,'buckets':results,'all_exact_interval_and_evidence_tuples_match':True}


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=pathlib.Path,required=True);p.add_argument('--runtime',type=pathlib.Path,required=True);p.add_argument('--receipt',type=pathlib.Path);a=p.parse_args();result=validate(a.source,a.runtime)
 if a.receipt:a.receipt.parent.mkdir(parents=True,exist_ok=True);a.receipt.write_text(json.dumps(result,separators=(',',':')))
 print(json.dumps({k:v for k,v in result.items() if k!='buckets'}))
if __name__=='__main__':main()
