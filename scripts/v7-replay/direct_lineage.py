"""Shared physical and direct-land research lineage adapter."""
import hashlib,json
from pathlib import Path
def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()


def validate_physical_report(path,expected_sha,physical,width,height):
 p=Path(path).resolve()
 if sha(p)!=expected_sha:raise ValueError('physical report hash mismatch')
 report=json.loads(p.read_text());output=report.get('physical_output_sha256',report.get('output_sha256',{}))
 grid=report.get('grid',{});canonical={'width':width,'height':height,'west':-180,'north':90,'step':360/width}
 if (report.get('status')!='candidate-only' or grid!=canonical
     or output.get('rows.u32le')!=physical['rows_sha256'] or output.get('runs.u32le')!=physical['runs_sha256']):
  raise ValueError('physical report does not bind this candidate grid')
 valid_sha=lambda x:isinstance(x,str) and len(x)==64 and all(c in '0123456789abcdef' for c in x)
 if all(k in report for k in ('physical_output_sha256','source_manifest','land_config','water_config','stage_reports')):
  source=[report['source_manifest'],report['land_config'],report['water_config']]
  if any(not isinstance(q,dict) or not q.get('path') or not valid_sha(q.get('sha256')) for q in source):
   raise ValueError('raw physical report missing source pins')
  return 'raw-pipeline-report'
 inp=report.get('inputs',{})
 if (not valid_sha(report.get('configuration_sha256')) or
     any(not isinstance(inp.get(k),dict) or not valid_sha(inp[k].get('sha256')) or not inp[k].get('path') for k in ('land','water'))):
  raise ValueError('physical composition report missing input pins')
 return 'compose-report'


def validate_direct_land(report_path,expected_sha,physical,land,snapshot_sha,revision,input_root,physical_report_sha):
 p=Path(report_path).resolve()
 if sha(p)!=expected_sha:raise ValueError('land report hash mismatch')
 report=json.loads(p.read_text())
 # Import the same validator as the prefill path, including its streaming-land contract.
 from build_prefill_plan import validate_land_report
 validate_land_report(report,p,{**physical,'report_sha256':physical_report_sha},land,snapshot_sha,revision,input_root=Path(input_root).resolve())
 if report.get('schema') in ('single-generation-direct-land-report-v1','single-generation-nearest-report-v1') and report.get('physical_report_sha256')!=physical_report_sha:
  raise ValueError('land and water use different physical report pins')
 return report.get('schema')
