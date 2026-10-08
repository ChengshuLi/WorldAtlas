#!/usr/bin/env python3
"""Authenticate source custody and extract bounded retired context in phase 1."""
from __future__ import annotations
import gzip, hashlib, io, json, subprocess, tarfile, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
PACKET=Path(__file__).resolve().parent
BASELINE='960ba2f4fef0fc9881b8a106a944e6e3874e98c9'
REGISTRY=ROOT/'data/semantic-sources.json'
MANIFEST=ROOT/'data/regional-review/regional-review-a9f03b364bdefa4a/sources-manifest.json'
V22=ROOT/'data/regional-review/regional-review-a9f03b364bdefa4a/sources/aafc-terrestrial-ecoregions-v2.2.geojson'
PROVINCES=ROOT/'data/regional-review/regional-review-a9f03b364bdefa4a/sources/aafc-ecoprovinces-baseline-arcgis-layer0.geojson'
INPUT_INDEX=ROOT/'coordination/engineering/eastern-two-gap-repair-20261007/input-index.json'
RETIRED_DIR=ROOT/'coordination/engineering/eastern-two-gap-repair-20261007/inputs'
NATIVE=PACKET/'sources/aafc-ecoregions.native.geojson'
RETIRED_IDS={
 'gb:CAN:ADM3:43193130B40321569586625','gb:CAN:ADM3:43193130B96648191896746',
 'gb:CAN:ADM3:43193130B13052897136233','gb:CAN:ADM3:43193130B30076837012949',
 'gb:CAN:ADM3:43193130B6772247703215'}
def sha(data:bytes)->str:return hashlib.sha256(data).hexdigest()
def descriptor(path:str,data:bytes)->dict:return {'path':path,'bytes':len(data),'sha256':sha(data),'hash_kind':'file-bytes'}
def write_new_or_same(path:Path,data:bytes)->None:
 if path.exists() and path.read_bytes()!=data: raise RuntimeError(f'Existing evidence output differs; preserve it and use a fresh run directory: {path.name}')
 if not path.exists(): path.write_bytes(data)
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
 registry_bytes=REGISTRY.read_bytes(); registry=json.loads(registry_bytes)
 source_manifest_bytes=MANIFEST.read_bytes(); source_manifest=json.loads(source_manifest_bytes)
 member_row=next(x for x in registry['files'] if x['path']=='aafc-ecoregions.geojson')
 native_bytes=NATIVE.read_bytes(); native=json.loads(native_bytes)
 ids=[f['properties'].get('ECOREGION_ID') for f in native['features']]
 assert sha(native_bytes)==member_row['sha256']=='a565563a6aef794df831dc9251fb4108018e20a4f0172acbc36b599f9b7f4abf'
 assert len(native['features'])==218 and len(set(ids))==194 and ids.count(15)==1 and ids.count(25)==1
 # Reconstruct the original compressed tar stream on disk, hash every piece, then extract one member.
 archive_piece_rows=[]; archive_hash=hashlib.sha256(); archive_bytes=0
 with tempfile.TemporaryFile() as archive_file:
  for row in registry['archive_parts']:
   path='data/semantic-evidence/'+row['path'].split('/',1)[-1]
   payload=subprocess.check_output(['git','show',f'{BASELINE}:{path}'])
   assert sha(payload)==row['sha256']
   archive_file.write(payload); archive_hash.update(payload); archive_bytes+=len(payload)
   archive_piece_rows.append({'path':path,'bytes':len(payload),'sha256':sha(payload)})
  archive_digest=archive_hash.hexdigest(); assert archive_digest==registry['archive_sha256']
  archive_file.seek(0)
  extracted=None
  with tarfile.open(fileobj=archive_file,mode='r|gz') as tar:
   for item in tar:
    if item.name=='aafc-ecoregions.geojson':
     member=tar.extractfile(item); assert member is not None
     extracted=member.read(item.size+1); break
  assert extracted==native_bytes
 citations={x['path'].split('/',1)[-1]:x for x in source_manifest['sources'] if isinstance(x.get('path'),str)}
 comparisons=[]
 for name,path,expected in [
  ('aafc-terrestrial-ecoregions-v2.2.geojson',V22,'f2c7ac1cabc601c364479c4616c245c993443ac61f6842f01a12078844a71e6b'),
  ('aafc-ecoprovinces-baseline-arcgis-layer0.geojson',PROVINCES,'5602aa328b64c3db9236cf610056d8375f164a51651dec34dc63334ecd4bc51f')]:
  raw=path.read_bytes(); citation=citations[name]; assert sha(raw)==expected==citation['sha256']
  comparisons.append({'baseline_path':'data/regional-review/regional-review-a9f03b364bdefa4a/sources/'+name,'citation':citation,'bytes':len(raw),'sha256':sha(raw),'read_from_pinned_baseline_directly':True})
 # Authenticate all seven archive pieces before decoding; combined encoded+decoded phase is capped at 64 MiB.
 input_index=json.loads(INPUT_INDEX.read_bytes()); aliases=[]
 for i in range(47,54):
  name=f'i{i:03d}.bin.gz'; aliases.append(next(a for a in input_index['aliases'] if a['ordinary']['path'].endswith(name)))
 encoded_total=sum(a['ordinary']['bytes'] for a in aliases); decoded_total=sum(a['ordinary']['decoded_bytes'] for a in aliases)
 assert encoded_total+decoded_total<65*1024*1024,(encoded_total,decoded_total)
 piece_rows=[]; combined_hash=hashlib.sha256(); combined_bytes=0
 with tempfile.TemporaryFile() as retired_stream:
  for alias in aliases:
   row=alias['ordinary']; payload=(RETIRED_DIR/Path(row['path']).name).read_bytes()
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
 custody={'version':1,'purpose':'Phase-1 custody and bounded retired-member extraction. Comparison layers remain as whole-file issue-pinned baseline inputs; only the exact native source member is retained as candidate bytes.','baseline_commit':BASELINE,
  'native_archive':{'archive_bytes':archive_bytes,'archive_sha256':archive_digest,'archive_member_path':'aafc-ecoregions.geojson','member_bytes':len(native_bytes),'member_sha256':sha(native_bytes),'member_byte_identical_to_retained_file':True,'archive_parts':archive_piece_rows,'registry_sha256':sha(registry_bytes),'source_manifest_sha256':sha(source_manifest_bytes)},
  'native_feature_count':len(native['features']),'native_unique_ecoregion_id_count':len(set(ids)),'ECO15_count':ids.count(15),'ECO25_count':ids.count(25),
  'native_candidate_source':descriptor('research/geography/arctic-seven-source-fit-20261008/sources/aafc-ecoregions.native.geojson',native_bytes),'comparison_sources':comparisons}
 retired={'version':1,'archive_kind':'undated-cartographic-reference-archive','historical_effective_year':None,'archive_bytes':combined_bytes,'archive_sha256':retired_digest,'encoded_input_bytes':encoded_total,'decoded_input_bytes':decoded_total,'location_count':location_count,'pieces':piece_rows,'locations':[selected[x] for x in sorted(selected)]}
 for name,data in [('source-custody.json',custody),('retired-member-context.json',retired)]:
  raw=(json.dumps(data,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n').encode(); write_new_or_same(PACKET/name,raw)
 print(json.dumps({'status':'source-custody-verified','native_sha256':sha(native_bytes),'archive_sha256':archive_digest,'retired_archive_sha256':retired_digest,'retained_member_count':len(selected)},sort_keys=True))
if __name__=='__main__':main()
