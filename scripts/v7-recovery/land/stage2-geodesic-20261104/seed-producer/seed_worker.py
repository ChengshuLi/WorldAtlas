#!/usr/bin/env python3
"""Direct seed-producer adapter invoked by the stage-2 orchestrator."""
import json,os,shutil,sys
from pathlib import Path
import seed_producer

def run(request, work, out, *, allow_local=False):
 cfg=json.loads(request.read_bytes());controls=cfg['controls']
 def guard():
  if shutil.disk_usage(work.parent).free<controls['disk_reserve_bytes']:raise RuntimeError('disk reserve reached')
 if allow_local:
  seed_producer.run(request,work,out,guard,allow_local=True)
 else:
  seed_producer.run(request,work,out,guard)

def main():
 if len(sys.argv) not in (4,5) or (len(sys.argv)==5 and sys.argv[4]!='--allow-local-provisional'):raise ValueError('expected seed request, work, output and optional provisional flag')
 run(*map(Path,sys.argv[1:4]),allow_local=len(sys.argv)==5)

if __name__=='__main__':
 try:main()
 except Exception as exc:print('seed worker failed: '+str(exc),file=sys.stderr);raise SystemExit(1)
