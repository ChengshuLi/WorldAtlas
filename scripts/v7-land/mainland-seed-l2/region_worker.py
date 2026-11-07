"""Isolated execution of one selected normalized Neon L2 mainland region."""
import hashlib,json,os,re,sys
from pathlib import Path
from regions import assemble
from closure_client import ClosureChecker

def normalized_sources(items):
 sources={}
 for s in items:
  if s.get('kind')!='raw':raise ValueError('non-raw source in normalized input')
  key=(s['source_id'],s['version'])
  if key in sources:raise ValueError('duplicate source ID/version')
  out={'kind':s['kind'],'sha256':s['sha256'],'bucket':s['bucket'],'key':s['key'],'origin':s.get('origin')}
  if 'representation' in s or 'full_tile_sha256' in s:
   if s.get('representation')!='manifest_of_raw_parts' or not re.fullmatch('[0-9a-f]{64}',str(s.get('full_tile_sha256'))):raise ValueError('invalid raw-part manifest identity')
   out.update(representation=s['representation'],full_tile_sha256=s['full_tile_sha256'])
  sources[key]=out
 return sources

def execute(request):
 if request.get('schema')!='stage2-region-worker-direct-request-v2':raise ValueError('invalid region worker request')
 guard=lambda:None
 guard();records={}
 for r in request['records']:
  key=(r['kind'],r['id'])
  if key in records:raise ValueError('duplicate geometry ID')
  records[key]=r
 sources=normalized_sources(request['sources'])
 c=request['closure'];checker=ClosureChecker(c['checker_path'],c['checker_sha256'],c['physical_dir'],c['physical_rows_sha256'],c['physical_runs_sha256'],c['contract_path'],c['contract_sha256'],c['work_parent'],guard,c.get('terminal_checker_path'),c.get('terminal_checker_sha256'),c['physical_report_sha256'])
 geom,report=assemble(request['revision_id'],records,request['decision'],sources,checker,physical_rows_sha256=c['physical_rows_sha256'],physical_runs_sha256=c['physical_runs_sha256'],physical_report_sha256=c['physical_report_sha256'],checker_sha256=c['checker_sha256'],closure_contract_sha256=c['contract_sha256'],guard=guard,terminal_checker_sha256=c.get('terminal_checker_sha256'))
 return {'schema':'stage2-region-worker-result-v1','status':'selected-research-region','geometry':geom,'report':report,'limitations':['Caller must authenticate the selected Neon export, source catalog and revision.','Closure proof checks only physical-water coverage, not geographic authority or historical V2/V7 equivalence.']}
if __name__=='__main__':
 if len(sys.argv)!=3:raise SystemExit('usage: region_worker.py REQUEST OUTPUT')
 with open(sys.argv[1],'rb') as f:raw=f.read((16<<20)+1)
 if len(raw)>16<<20:raise SystemExit('request exceeds size limit')
 result=execute(json.loads(raw))
 with open(sys.argv[2],'x') as f:json.dump(result,f,sort_keys=True,allow_nan=False,separators=(',',':'));f.write('\n');f.flush();os.fsync(f.fileno())
