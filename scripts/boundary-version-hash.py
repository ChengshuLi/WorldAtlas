#!/usr/bin/env python3
"""Read-only cache fingerprint for non-example dated location footprints.

Uses the exact archived geometry canonicalization that prepared ownership used.
Input order within a location intentionally matches the original preparation.
"""
import argparse,collections,hashlib,importlib.util,json,pathlib,sqlite3,sys
sys.dont_write_bytecode=True
ROOT=pathlib.Path(__file__).resolve().parents[1]
def canonical_algorithm(index_path):
 index=json.loads(index_path.read_text());entries=index['execution_algorithms']
 for entry in entries:
  path=index_path.parent/entry['path']
  if hashlib.sha256(path.read_bytes()).hexdigest()!=entry['sha256']:raise ValueError('Executed ownership algorithm hash mismatch: '+entry['path'])
 entry=next(e for e in entries if pathlib.Path(e['path']).name=='majority.py');path=index_path.parent/entry['path']
 sys.path.insert(0,str(path.parent))
 spec=importlib.util.spec_from_file_location('_executed_ownership_majority',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 return module.canonical

def boundary_hash(rows,index_path):
 from shapely.geometry import shape
 canonical=canonical_algorithm(index_path);versions=collections.defaultdict(list)
 for location_id,start,end,raw in rows:
  versions[location_id].append((start,end,canonical(shape(json.loads(raw)))))
 return hashlib.sha256(str([(id,[(a,b,g.wkb_hex) for a,b,g in v]) for id,v in sorted(versions.items())]).encode()).hexdigest()

if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--database',type=pathlib.Path,default=ROOT/'data/atlas.sqlite');parser.add_argument('--index',type=pathlib.Path,default=ROOT/'data/ownership-history/index.json');parser.add_argument('--stdin',action='store_true');args=parser.parse_args()
 if args.stdin:
  rows=json.load(sys.stdin)
  if not isinstance(rows,list) or any(not isinstance(r,list) or len(r)!=4 for r in rows):raise ValueError('Expected boundary rows [location_id, valid_from, valid_to, geometry JSON]')
  print(boundary_hash(rows,args.index.resolve()))
 else:
  con=sqlite3.connect(args.database.resolve().as_uri()+'?mode=ro',uri=True)
  try:print(boundary_hash(con.execute('SELECT location_id,valid_from,valid_to,geometry FROM boundaries WHERE is_example=0'),args.index.resolve()))
  finally:con.close()
