#!/usr/bin/env python3
"""Create bounded content-preserving GeoJSON partitions from the pinned original."""
import argparse,hashlib,json
from pathlib import Path
EXPECTED='74e489fd4370972403950719026a317abba443668cea7d49f4b36c61637958f1'
MAX_PART_BYTES=32*1024*1024

def digest(b):return hashlib.sha256(b).hexdigest()
def encode(fs,crs):return (json.dumps({'type':'FeatureCollection','crs':crs,'features':fs},ensure_ascii=False,separators=(',',':'))+'\n').encode()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,required=True);ap.add_argument('--output-dir',type=Path,required=True);a=ap.parse_args()
 raw=a.input.read_bytes()
 if digest(raw)!=EXPECTED:raise SystemExit('Original ADM3 file SHA-256 mismatch')
 original=json.loads(raw);features=original['features'];ids=[f['properties']['shapeID'] for f in features]
 if len(features)!=213 or len(set(ids))!=213:raise SystemExit('Pinned source must have exactly 213 uniquely keyed features')
 parts=[[]]
 for f in features:
  candidate=parts[-1]+[f]
  if len(encode(candidate,original.get('crs')))>MAX_PART_BYTES:
   if not parts[-1]:raise SystemExit('One source feature exceeds the 32 MiB input bound')
   parts.append([f])
  else:
   parts[-1].append(f)
 if any(len(encode(p,original.get('crs')))>MAX_PART_BYTES for p in parts):raise SystemExit('Partition exceeds the 32 MiB input bound')
 a.output_dir.mkdir(parents=True,exist_ok=True);checks=[];ids_out=[]
 for i,part in enumerate(parts,1):
  b=encode(part,original.get('crs'));path=a.output_dir/f'geoBoundaries-ZAF-ADM3-part-{i:02}-of-{len(parts):02}.geojson';path.write_bytes(b);checks.append({'path':path.name,'bytes':len(b),'sha256':digest(b),'features':len(part)});ids_out.extend(f['properties']['shapeID'] for f in part)
 if ids_out!=ids:raise SystemExit('Partition sequence differs from original source roster')
 # Decode retained parts and compare parsed feature objects, preserving every property and coordinate.
 docs=[json.loads((a.output_dir/row['path']).read_bytes()) for row in checks]
 if any(doc.get('crs')!=original.get('crs') for doc in docs):raise SystemExit('Partition CRS metadata differs from source')
 reread=[f for doc in docs for f in doc['features']]
 if reread!=features:raise SystemExit('Partition round-trip changed source feature content')
 print(json.dumps({'source_sha256':EXPECTED,'source_bytes':len(raw),'feature_count':len(features),'partition_count':len(checks),'partitions':checks},indent=2))
if __name__=='__main__':main()
