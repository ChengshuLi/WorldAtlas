#!/usr/bin/env python3
"""Authenticate source custody and extract bounded retired context in phase 2."""
from __future__ import annotations
import gzip, hashlib, io, json, tempfile
from pathlib import Path
from source_phase_runtime import require_phase, read_bytes, read_json, write_packet_output
ROOT=Path(__file__).resolve().parents[3]
PACKET=Path(__file__).resolve().parent
BASELINE='960ba2f4fef0fc9881b8a106a944e6e3874e98c9'
REGISTRY=ROOT/'data/semantic-sources.json'
INPUT_INDEX=ROOT/'coordination/engineering/eastern-two-gap-repair-20261007/input-index.json'
RETIRED_DIR=ROOT/'coordination/engineering/eastern-two-gap-repair-20261007/inputs'
NATIVE=PACKET/'sources/aafc-ecoregions.native.geojson'
NATIVE_VERIFICATION=PACKET/'native-archive-extraction.json'
RETIRED_IDS={
 'gb:CAN:ADM3:43193130B40321569586625','gb:CAN:ADM3:43193130B96648191896746',
 'gb:CAN:ADM3:43193130B13052897136233','gb:CAN:ADM3:43193130B30076837012949',
 'gb:CAN:ADM3:43193130B6772247703215'}
def sha(data:bytes)->str:return hashlib.sha256(data).hexdigest()
def descriptor(path:str,data:bytes)->dict:return {'path':path,'bytes':len(data),'sha256':sha(data),'hash_kind':'file-bytes'}
def write_new_or_same(path:Path,data:bytes)->None:
 write_packet_output(path,data)
def extract_selected_locations(stream, wanted:set[str])->tuple[dict[str,dict],int]:
 stream.seek(0); text_stream=io.TextIOWrapper(stream,encoding='utf-8',newline='')
 decoder=json.JSONDecoder(); buffer=''; marker='"locations":['; pos=-1
 while pos<0:
  chunk=text_stream.read(65536)
  if not chunk: raise ValueError('Retired archive lacks locations array')
  buffer+=chunk; pos=buffer.find(marker)
  if len(buffer)>2*1024*1024 and pos<0: raise ValueError('Retired archive header exceeds bounded parser limit')
 buffer=buffer[pos+len(marker):]; count=0; selected={}
 while True:
  while True:
   if not buffer:
    chunk=text_stream.read(65536)
    if not chunk: raise ValueError('Truncated retired locations array')
    buffer=chunk
   if buffer[0].isspace() or buffer[0]==',': buffer=buffer[1:]; continue
   break
  if buffer[0]==']': break
  try: row,end=decoder.raw_decode(buffer)
  except json.JSONDecodeError:
   chunk=text_stream.read(65536)
   if not chunk: raise ValueError('Truncated retired location record')
   if len(buffer)+len(chunk)>8*1024*1024: raise ValueError('Single retired member exceeds bounded parser limit')
   buffer+=chunk; continue
  if not isinstance(row,dict) or not isinstance(row.get('id'),str): raise ValueError('Malformed retired location record')
  count+=1
  if row['id'] in wanted: selected[row['id']]=row
  buffer=buffer[end:]
 return selected,count
def main()->None:
 require_phase('retired-context')
 registry_bytes=read_bytes(REGISTRY); registry=json.loads(registry_bytes)
 native_verification=read_json(NATIVE_VERIFICATION)
 member_row=next(x for x in registry['files'] if x['path']=='aafc-ecoregions.geojson')
 native_bytes=read_bytes(NATIVE); native=json.loads(native_bytes)
 ids=[f['properties'].get('ECOREGION_ID') for f in native['features']]
 assert sha(native_bytes)==member_row['sha256']=='a565563a6aef794df831dc9251fb4108018e20a4f0172acbc36b599f9b7f4abf'
 assert len(native['features'])==218 and len(set(ids))==194 and ids.count(15)==1 and ids.count(25)==1
 assert native_verification['archive_sha256']==registry['archive_sha256']
 assert native_verification['member_sha256']==sha(native_bytes) and native_verification['member_bytes']==len(native_bytes)
 assert native_verification['member_byte_identical_to_retained_file'] is True
 # Authenticate all seven archive pieces before decoding; combined encoded+decoded phase is capped at 64 MiB.
 input_index=read_json(INPUT_INDEX); aliases=[]
 for i in range(47,54):
  name=f'i{i:03d}.bin.gz'; aliases.append(next(a for a in input_index['aliases'] if a['ordinary']['path'].endswith(name)))
 encoded_total=sum(a['ordinary']['bytes'] for a in aliases); decoded_total=sum(a['ordinary']['decoded_bytes'] for a in aliases)
 assert encoded_total+decoded_total<65*1024*1024,(encoded_total,decoded_total)
 piece_rows=[]; combined_hash=hashlib.sha256(); combined_bytes=0
 with tempfile.TemporaryFile() as retired_stream:
  for alias in aliases:
   row=alias['ordinary']; payload=read_bytes(RETIRED_DIR/Path(row['path']).name)
   assert len(payload)==row['bytes'] and sha(payload)==row['sha256']
   part_hash=hashlib.sha256(); part_bytes=0
   with gzip.GzipFile(fileobj=io.BytesIO(payload),mode='rb') as gz:
    while True:
     block=gz.read(1024*1024)
     if not block: break
     part_hash.update(block); combined_hash.update(block); retired_stream.write(block); part_bytes+=len(block); combined_bytes+=len(block)
   assert part_bytes==row['decoded_bytes'] and part_hash.hexdigest()==row['decoded_sha256']
   piece_rows.append({'path':row['path'],'encoded_bytes':len(payload),'encoded_sha256':sha(payload),'decoded_bytes':part_bytes,'decoded_sha256':part_hash.hexdigest()})
  retired_digest=combined_hash.hexdigest(); assert combined_bytes==decoded_total and retired_digest=='c072bbe6e7f96789e3a6165e9075eb3271050e1e1614f2923f03169480537184'
  selected,location_count=extract_selected_locations(retired_stream,RETIRED_IDS)
 assert location_count==19050 and set(selected)==RETIRED_IDS
 custody={'version':1,'purpose':'Phase-2 bounded retired-member extraction, consuming the separately verified native archive receipt. Comparison layers remain as whole-file issue-pinned baseline inputs; only the exact native source member is retained as candidate bytes.','baseline_commit':BASELINE,
  'native_archive':native_verification|{'archive_member_path':'aafc-ecoregions.geojson','registry_sha256':sha(registry_bytes)},
  'native_feature_count':len(native['features']),'native_unique_ecoregion_id_count':len(set(ids)),'ECO15_count':ids.count(15),'ECO25_count':ids.count(25),
  'native_candidate_source':descriptor('research/geography/arctic-seven-source-fit-20261008/sources/aafc-ecoregions.native.geojson',native_bytes)}
 retired={'version':1,'archive_kind':'undated-cartographic-reference-archive','historical_effective_year':None,'archive_bytes':combined_bytes,'archive_sha256':retired_digest,'encoded_input_bytes':encoded_total,'decoded_input_bytes':decoded_total,'location_count':location_count,'pieces':piece_rows,'locations':[selected[x] for x in sorted(selected)]}
 for name,data in [('source-custody-phase2.json',custody),('retired-member-context-phase2.json',retired)]:
  raw=(json.dumps(data,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n').encode(); write_new_or_same(PACKET/name,raw)
 print(json.dumps({'status':'source-custody-verified','native_sha256':sha(native_bytes),'archive_sha256':native_verification['archive_sha256'],'retired_archive_sha256':retired_digest,'retained_member_count':len(selected)},sort_keys=True))
if __name__=='__main__':main()
