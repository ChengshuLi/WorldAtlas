#!/usr/bin/env python3
"""Run one bounded half of the 36-part active-neighbor scan."""
from __future__ import annotations
import argparse, gzip, hashlib, json
from pathlib import Path
from source_phase_runtime import require_phase, read_bytes, read_json, write_packet_output
from reproduce_fit import CANDIDATES, PACKET, ROOT

def sha(data:bytes)->str:return hashlib.sha256(data).hexdigest()

def main()->None:
 parser=argparse.ArgumentParser()
 parser.add_argument('partition',choices=['a','b','c','d'])
 args=parser.parse_args()
 require_phase('neighbor-scan-'+args.partition)
 from shapely.geometry import shape, mapping
 idx=read_json(ROOT/'data/world-index.json')
 paths=idx['parts']; assert len(paths)==36
 width=len(paths)//4; partition_index=ord(args.partition)-ord('a')
 selected=paths[partition_index*width:(partition_index+1)*width]
 context_path=ROOT/'coordination/engineering/eastern-two-gap-repair-20261007/run-two/full-four-family-context.json.gz'
 context_raw=read_bytes(context_path); context=json.loads(gzip.decompress(context_raw))
 components={x['id']:x for x in context['components']}
 candidates={cid:shape(components[cid]['geometry']) for cid,*_ in CANDIDATES}
 target_ids={cid:target for cid,_eid,target,_admin,_parent in CANDIDATES}
 hits={cid:[] for cid in candidates}; neighbors={cid:[] for cid in candidates}
 roster=[]; feature_count=0; active_feature_ids=[]; seen_ids=set()
 for rel in selected:
  raw=read_bytes(ROOT/'data'/rel); part=json.loads(raw)
  roster.append({'path':'data/'+rel,'bytes':len(raw),'sha256':sha(raw),'feature_count':len(part['features'])})
  for feature in part['features']:
   feature_count+=1; fid=feature.get('id') or feature.get('properties',{}).get('id')
   if not isinstance(fid,str) or not fid or fid in seen_ids:
    raise ValueError('Active feature identity is missing or duplicated across this scan partition')
   seen_ids.add(fid); active_feature_ids.append(fid); geometry=shape(feature['geometry'])
   for cid,candidate in candidates.items():
    if geometry.intersects(candidate):
     inter=geometry.intersection(candidate)
     hits[cid].append({'id':fid,'dimension':'area' if inter.area>0 else ('line' if inter.length>0 else 'point'),'area_deg2':inter.area,'length_degrees':inter.length})
     if fid!=target_ids[cid] and inter.area>0:
      neighbors[cid].append({'id':fid,'dimension':'area','area_deg2':inter.area,'length_degrees':inter.length,'geometry':mapping(inter)})
 out={'version':2,'partition':args.partition.upper(),'roster':roster,'active_feature_count':feature_count,'active_feature_ids':sorted(active_feature_ids),'active_part_count':len(roster),'candidate_ids':sorted(candidates),'context_input':{'path':'coordination/engineering/eastern-two-gap-repair-20261007/run-two/full-four-family-context.json.gz','encoded_bytes':len(context_raw),'encoded_sha256':sha(context_raw),'decoded_bytes':len(gzip.decompress(context_raw)),'decoded_sha256':sha(gzip.decompress(context_raw))},'hits_by_candidate':hits,'neighbors_by_candidate':neighbors}
 raw=(json.dumps(out,sort_keys=True,separators=(',',':'))+'\n').encode()
 write_packet_output(PACKET/f'neighbor-scan-{args.partition}.json',raw)
 print(json.dumps({'status':'neighbor-scan-complete','partition':args.partition.upper(),'parts':len(roster),'features':feature_count,'output_bytes':len(raw),'output_sha256':sha(raw)},sort_keys=True))

if __name__=='__main__':main()
