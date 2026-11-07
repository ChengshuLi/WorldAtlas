#!/usr/bin/env python3
"""Attach a completed pinned coastal manifest to the reviewed basin inventory."""
import argparse,hashlib,json,os,time
from pathlib import Path

def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def read(p,digest):
 p=Path(p);before=p.stat();raw=p.read_bytes();after=p.stat()
 if p.is_symlink() or hashlib.sha256(raw).hexdigest()!=digest or (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)!=(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns):raise ValueError('pinned input changed')
 return json.loads(raw)
def make(inventory,inventory_sha,coast,coast_sha,out):
 processing_started=time.perf_counter()
 inv=read(inventory,inventory_sha);cm=read(coast,coast_sha)
 if inv.get('schema')!='worldatlas-prefill-input-inventory-v1' or inv.get('status')!='coastal-band-pending-not-runnable' or inv.get('publishable') is not False or inv.get('coastal_band') is not None or not isinstance(inv.get('basins'),list) or not inv['basins']:raise ValueError('invalid basin inventory')
 phy=inv.get('rle_inputs',{}).get('physical',{});mask=Path(phy.get('physical_mask_path',''));mask_sha=phy.get('physical_mask_sha256');report=read(phy.get('report_path',''),phy.get('report_sha256'))
 if not mask.is_file() or mask.is_symlink() or not isinstance(mask_sha,str) or len(mask_sha)!=64 or report.get('physical_output_sha256',report.get('output_sha256',{})).get('physical-dry.tif')!=mask_sha or sha(mask)!=mask_sha:raise ValueError('physical mask lineage mismatch')
 if cm.get('schema')!='worldatlas-full-water-assignment-tiles-v1' or cm.get('coverage',{}).get('complete') is not True or cm.get('source',{}).get('policy_sha256')!=inv['snapshot_sha256']:raise ValueError('incomplete or wrong-policy coastal manifest')
 result={**inv,'schema':'worldatlas-provisional-prefill-inputs-v1','status':'pending-full-prefill-validation','source_inventory_sha256':inventory_sha,'coastal_band':{'manifest_path':str(Path(coast).resolve()),'manifest_sha256':coast_sha},'limitations':['Ocean boundaries, enclosed-water fill and final assembly are not complete.']+[x for x in inv.get('limitations',[]) if not x.startswith('Coastal band,')]}
 if sha(inventory)!=inventory_sha or sha(coast)!=coast_sha or sha(mask)!=mask_sha:raise ValueError('pinned input changed before output')
 out=Path(out)
 if out.is_symlink():raise ValueError('output symlink')
 result['processing_elapsed_seconds']=time.perf_counter()-processing_started
 with out.open('x') as f:json.dump(result,f,indent=2,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
 fd=os.open(out.parent,os.O_RDONLY|os.O_DIRECTORY)
 try:os.fsync(fd)
 finally:os.close(fd)
 if sha(inventory)!=inventory_sha or sha(coast)!=coast_sha or sha(mask)!=mask_sha:raise ValueError('pinned input changed during output')
 return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--inventory',required=True);p.add_argument('--inventory-sha256',required=True);p.add_argument('--coast',required=True);p.add_argument('--coast-sha256',required=True);p.add_argument('--out',required=True);a=p.parse_args();make(a.inventory,a.inventory_sha256,a.coast,a.coast_sha256,a.out);print('provisional prefill inputs ready for full validation')
