#!/usr/bin/env python3
"""Compare old and subtype-only feature predicates on hash-pinned Overture shards.

This reads metadata columns only. It does not rasterize or compare pixels.
"""
import argparse,collections,concurrent.futures,hashlib,json,os
from pathlib import Path
import pyarrow.parquet as pq

def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for chunk in iter(lambda:f.read(8<<20),b''):h.update(chunk)
 return h.hexdigest()

def scan(item):
 path,expected=item;path=Path(path);before=path.stat()
 if sha(path)!=expected:raise ValueError('source hash mismatch: '+str(path))
 counts=collections.Counter();pf=pq.ParquetFile(path,pre_buffer=False)
 for batch in pf.iter_batches(batch_size=16384,columns=['subtype','class','sources'],use_threads=False):
  for row in batch.to_pylist():
   subtype,water_class,sources=row['subtype'],row['class'],row['sources'] or []
   old=(subtype is not None and subtype not in ('ocean','physical') and water_class not in ('ocean','sea') and any(s and s.get('dataset')=='OpenStreetMap' and s.get('property') in ('','geometry') for s in sources))
   new=(isinstance(subtype,str) and bool(subtype.strip()) and subtype not in ('ocean','physical'))
   counts['rows']+=1;counts['old_selected']+=int(bool(old));counts['new_selected']+=int(bool(new));counts['added']+=int(bool(new and not old));counts['removed']+=int(bool(old and not new))
   if subtype is None or not isinstance(subtype,str) or not subtype.strip():counts['missing_subtype']+=1
 after=path.stat()
 if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):raise ValueError('source changed during scan: '+str(path))
 if counts['rows']!=pf.metadata.num_rows:raise ValueError('row count mismatch: '+str(path))
 return {'file':path.name,'sha256':expected,**dict(counts)}

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('manifest');p.add_argument('manifest_sha256');p.add_argument('--workers',type=int,default=1);a=p.parse_args()
 if not 1<=a.workers<=8:raise ValueError('workers must be 1 to 8')
 manifest=Path(a.manifest).resolve();raw=manifest.read_bytes()
 if hashlib.sha256(raw).hexdigest()!=a.manifest_sha256:raise ValueError('manifest hash mismatch')
 doc=json.loads(raw);files=doc.get('files')
 if not isinstance(files,list) or not files or doc.get('file_count')!=len(files):raise ValueError('incomplete manifest')
 jobs=[];seen=set()
 for spec in files:
  rel=Path(spec['path']);path=(manifest.parent/rel).resolve();digest=spec.get('sha256')
  if rel.is_absolute() or not path.is_relative_to(manifest.parent) or path in seen or not isinstance(digest,str) or len(digest)!=64 or any(c not in '0123456789abcdef' for c in digest):raise ValueError('invalid source pin')
  seen.add(path);jobs.append((str(path),digest))
 with concurrent.futures.ProcessPoolExecutor(max_workers=a.workers) as pool:results=list(pool.map(scan,jobs))
 if manifest.read_bytes()!=raw:raise ValueError('manifest changed during scan')
 totals={k:sum(x.get(k,0) for x in results) for k in ('rows','old_selected','new_selected','added','removed','missing_subtype')}
 print(json.dumps({'schema':'water-selection-comparison-v1','manifest_sha256':a.manifest_sha256,'shards':len(results),'totals':totals,'results':results,'limitation':'Feature-selection comparison only; geometry validity and pixel outcomes are not checked.'},indent=2))
if __name__=='__main__':main()
