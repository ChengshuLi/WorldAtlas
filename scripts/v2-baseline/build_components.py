#!/usr/bin/env python3
"""Generate research V2 physical components once for source seeding and land."""
import argparse,hashlib,json,math,shutil,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parent))
import exclusive_outputs as xo
from file_integrity import pin,sha

def build(config_path,output):
 config_path=Path(config_path).resolve();raw=config_path.read_bytes();c=json.loads(raw);required={'schema','grid','physical_rows','physical_runs','physical_report'}
 if not required<=set(c)<=required|{'minimum_free_bytes'} or c['schema']!='simple-v2-components-v1' or sys.byteorder!='little':raise ValueError('invalid config or byte order')
 g=c['grid'];w,h,step=(g[k] for k in ('width','height','step'));reserve=c.get('minimum_free_bytes',2*(1<<30))
 if (set(g)!={'width','height','west','north','step'} or type(w) is not int or type(h) is not int or w<1 or h<1 or g['west']!=-180 or type(g['north']) not in (int,float) or not math.isfinite(g['north']) or g['north']>90 or type(step) not in (int,float) or not math.isfinite(step) or step<=0 or abs(w*step-360)>1e-8 or g['north']-h*step < -90-1e-8 or type(reserve) is not int or reserve<0):raise ValueError('invalid grid or disk reserve')
 keys=('physical_rows','physical_runs','physical_report');pins={k:pin(c[k]) for k in keys};physical=json.loads(pins['physical_report'].read_bytes());outputs=physical.get('physical_output_sha256',physical.get('output_sha256',{}))
 if physical.get('status')!='candidate-only' or physical.get('grid')!=g or outputs.get('rows.u32le')!=c['physical_rows']['sha256'] or outputs.get('runs.u32le')!=c['physical_runs']['sha256']:raise ValueError('physical report mismatch')
 out=Path(output).resolve();source=HERE.parent/'v7-land'/'build_components.cpp';code_paths={'builder':Path(__file__).resolve(),'component_source':source,'pin_io':HERE/'file_integrity.py','output_io':Path(xo.__file__).resolve()};code={k:sha(v) for k,v in code_paths.items()}
 if out.exists() or any(out==p or out in p.parents or p.parent in out.parents for p in [config_path,*pins.values(),*code_paths.values()]):raise ValueError('output must be new and outside input directories')
 if shutil.disk_usage(out.parent).free<reserve:raise ValueError('free disk below configured reserve')
 xo.create_directory_exclusive(out);binary=out/'component-builder';built=subprocess.run(['g++','-std=c++17','-O2','-Wall','-Wextra','-Werror',str(source),'-o',str(binary)],capture_output=True,text=True)
 if built.returncode:raise ValueError('component builder compilation failed: '+built.stderr[-3000:])
 proc=subprocess.run([str(binary),str(w),str(h),str(pins['physical_rows']),str(pins['physical_runs']),str(out/'rows.u32le'),str(out/'runs.u32le')],capture_output=True,text=True)
 if proc.returncode:raise ValueError('component generation failed: '+proc.stderr[-3000:])
 if shutil.disk_usage(out).free<reserve:raise ValueError('free disk below configured reserve')
 for k in keys:pin(c[k])
 if config_path.read_bytes()!=raw or any(sha(p)!=code[k] for k,p in code_paths.items()):raise ValueError('input or code changed')
 report={'schema':'simple-v2-components-report-v1','status':'research-not-published','grid':g,'config_sha256':hashlib.sha256(raw).hexdigest(),'inputs':{k:c[k] for k in keys},'component_source_sha256':code['component_source'],'builder_binary_sha256':sha(binary),'compiler_version':subprocess.run(['g++','--version'],capture_output=True,text=True,check=True).stdout.splitlines()[0],'builder_output':proc.stdout.strip(),'rows_sha256':sha(out/'rows.u32le'),'runs_sha256':sha(out/'runs.u32le'),'code_sha256':code,'limitation':'Same-run component provenance is not independent connectivity recomputation or source authentication; no V2 labels were read.'};xo.write_json_exclusive(out/'report.json',report,indent=2);return report
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('config');p.add_argument('output');a=p.parse_args()
 try:print(json.dumps(build(a.config,a.output),indent=2))
 except Exception as e:print('error: '+str(e),file=sys.stderr);raise SystemExit(1)
