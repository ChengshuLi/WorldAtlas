"""Isolated execution of one selected normalized Neon L2 mainland region."""
import hashlib,json,os,sys
from pathlib import Path
from regions import assemble
from closure_client import ClosureChecker

def available():
 with open('/proc/meminfo') as f:
  for line in f:
   if line.startswith('MemAvailable:'):return int(line.split()[1])
 raise RuntimeError('MemAvailable unavailable')
def execute(request):
 if request.get('schema')!='stage2-region-worker-request-v1' or type(request.get('memory_floor_kib')) is not int or request['memory_floor_kib']<0:raise ValueError('invalid region worker request')
 def guard():
  if available()<request['memory_floor_kib']:raise RuntimeError('memory guard reached')
 guard();records={};sources={}
 for r in request['records']:
  key=(r['kind'],r['id'])
  if key in records:raise ValueError('duplicate geometry ID')
  records[key]=r
 for s in request['sources']:
  if s.get('kind')!='raw':raise ValueError('non-raw source in normalized input')
  key=(s['source_id'],s['version'])
  if key in sources:raise ValueError('duplicate source ID/version')
  sources[key]={'kind':s['kind'],'sha256':s['sha256'],'bucket':s['bucket'],'key':s['key']}
 c=request['closure'];checker=ClosureChecker(c['checker_path'],c['checker_sha256'],c['physical_dir'],c['physical_rows_sha256'],c['physical_runs_sha256'],c['contract_path'],c['contract_sha256'],c['work_parent'],guard,c['timeout_seconds'],c.get('terminal_checker_path'),c.get('terminal_checker_sha256'))
 geom,report=assemble(request['revision_id'],records,request['decision'],sources,checker,physical_rows_sha256=c['physical_rows_sha256'],physical_runs_sha256=c['physical_runs_sha256'],checker_sha256=c['checker_sha256'],closure_contract_sha256=c['contract_sha256'],guard=guard,terminal_checker_sha256=c.get('terminal_checker_sha256'))
 return {'schema':'stage2-region-worker-result-v1','status':'selected-research-region','geometry':geom,'report':report,'limitations':['Caller must authenticate the selected Neon export, source catalog and revision.','Closure proof checks only physical-water coverage, not geographic authority or historical V2/V7 equivalence.']}
if __name__=='__main__':
 if len(sys.argv)!=3:raise SystemExit('usage: region_worker.py REQUEST OUTPUT')
 with open(sys.argv[1],'rb') as f:raw=f.read((16<<20)+1)
 if len(raw)>16<<20:raise SystemExit('request exceeds size limit')
 result=execute(json.loads(raw))
 with open(sys.argv[2],'x') as f:json.dump(result,f,sort_keys=True,allow_nan=False,separators=(',',':'));f.write('\n');f.flush();os.fsync(f.fileno())
