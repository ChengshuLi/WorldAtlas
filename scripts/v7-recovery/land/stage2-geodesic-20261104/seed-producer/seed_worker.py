#!/usr/bin/env python3
"""Subprocess adapter; the outer process-group guardian monitors this worker."""
import json,os,shutil,sys
from pathlib import Path
import seed_producer

def main():
 if len(sys.argv)!=4:raise ValueError('expected seed request, work and output')
 request,work,out=map(Path,sys.argv[1:])
 with open(request,'rb') as f:
  if os.fstat(f.fileno()).st_size>1<<20:raise ValueError('seed request exceeds bound')
  data=f.read((1<<20)+1)
 if len(data)>1<<20:raise ValueError('seed request exceeds bound')
 cfg=json.loads(data);controls=cfg['controls']
 def guard():
  with open('/proc/meminfo') as f:
   available=next((int(x.split()[1]) for x in f if x.startswith('MemAvailable:')),None)
  if available is None or available<controls['memory_floor_kib'] or shutil.disk_usage(work.parent).free<controls['disk_reserve_bytes']:raise RuntimeError('resource floor reached')
 seed_producer.run(request,work,out,guard)
if __name__=='__main__':
 try:main()
 except Exception as exc:print('seed worker failed: '+str(exc),file=sys.stderr);raise SystemExit(1)
