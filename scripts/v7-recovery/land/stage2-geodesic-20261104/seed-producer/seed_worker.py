#!/usr/bin/env python3
"""Direct seed-producer adapter invoked by the stage-2 orchestrator."""
import json,os,shutil,sys
from pathlib import Path
import seed_producer

def main():
 if len(sys.argv)!=4:raise ValueError('expected seed request, work and output')
 request,work,out=map(Path,sys.argv[1:])
 data=request.read_bytes()
 cfg=json.loads(data);controls=cfg['controls']
 def guard():
  if shutil.disk_usage(work.parent).free<controls['disk_reserve_bytes']:raise RuntimeError('disk reserve reached')
 seed_producer.run(request,work,out,guard)
if __name__=='__main__':
 try:main()
 except Exception as exc:print('seed worker failed: '+str(exc),file=sys.stderr);raise SystemExit(1)
