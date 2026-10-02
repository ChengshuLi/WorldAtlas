#!/usr/bin/env python3
"""Restore a repair stage from Git evidence plus the pinned installed geography."""
import argparse, gzip, hashlib, importlib.util, json, pathlib, sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
spec=importlib.util.spec_from_file_location('_repair_staging',ROOT/'scripts/apply-source-territory-repairs.py')
repair=importlib.util.module_from_spec(spec);spec.loader.exec_module(repair)


def restore(after_index,evidence,output):
 if output.exists():raise ValueError('Output must be a fresh directory')
 if output.resolve()==ROOT/'data' or ROOT/'data' in output.resolve().parents:raise ValueError('Never restore over live data')
 manifest=repair.read(evidence/'index.json')
 for entry in manifest['files'].values():
  path=(evidence/entry['archive_path']).resolve()
  if not path.is_relative_to(evidence.resolve()) or repair.sha(path)!=entry['sha256']:raise ValueError('Archived evidence hash mismatch')
 raw=repair.read(after_index)
 features=[f for part in raw['parts'] for f in repair.read(after_index.parent/part)['features']]
 if len(features)!=manifest['after_locations'] or repair.footprint_hash(features)!=manifest['after_footprints_sha256']:raise ValueError('Installed after geography does not match this immutable migration')
 archive=repair.read(evidence/'archive.json.gz');by_id={f['properties']['id']:f for f in features}
 for original in archive['locations']:by_id[original['id']]=original['feature']
 before=list(by_id.values())
 if len(before)!=manifest['before_locations'] or repair.footprint_hash(before)!=manifest['before_footprints_sha256']:raise ValueError('Reconstructed before footprint hash differs')
 # Footprint hashes, not filename/row position, establish identity. Parts may be recompressed.
 for tag,values in [('before',before),('after',features)]:
  parts=[]
  for n,start in enumerate(range(0,len(values),1500)):
   name=f'geography/part-{n}.json.gz';repair.write(output/tag/name,{'type':'FeatureCollection','features':values[start:start+1500]});parts.append(name)
  repair.write(output/tag/'world-index.json',{'parts':parts})
 for name,entry in manifest['files'].items():
  source=evidence/entry['archive_path'];destination=output/name;destination.parent.mkdir(parents=True,exist_ok=True)
  raw=gzip.decompress(source.read_bytes()) if entry.get('uncompressed_sha256') else source.read_bytes()
  if entry.get('uncompressed_sha256') and hashlib.sha256(raw).hexdigest()!=entry['uncompressed_sha256']:raise ValueError('Lossless archive decompression mismatch')
  destination.write_bytes(raw)
 return {'output':str(output),'before_locations':len(before),'after_locations':len(features),'before_footprints_sha256':manifest['before_footprints_sha256'],'after_footprints_sha256':manifest['after_footprints_sha256']}


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--after',type=pathlib.Path,default=ROOT/'data/world-index.json');p.add_argument('--evidence',type=pathlib.Path,default=ROOT/'data/geographic-repair-evidence');p.add_argument('--output',type=pathlib.Path,required=True);a=p.parse_args();print(json.dumps(restore(a.after,a.evidence,a.output)))
if __name__=='__main__':main()
