#!/usr/bin/env python3
"""Record live pre-run resource admission; no coordinates or geometries are read."""
from __future__ import annotations
import datetime, hashlib, json, os, re, shutil, subprocess, sys
from pathlib import Path
import shapely, pyproj
ROOT=Path(__file__).resolve().parent; REPO=ROOT.parents[2]
PLAN=ROOT/'bounded-measurement-plan.json'; OUT=ROOT/'geometry-run-admission-004.json'
NODE='/Users/chengshuli/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node'
PYTHON='/Users/chengshuli/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3.12'
RSS_CAP=805306368; OUTPUT_RESERVE=33554432; SCRATCH_RESERVE=33554432; MIN_FREE_PERCENT=25; LOW_GUARD_PERCENT=20

def run(cmd): return subprocess.run(cmd,capture_output=True,text=True,check=True).stdout

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    if OUT.exists(): raise SystemExit('admission file already exists; do not replace a prior admission')
    plan=json.loads(PLAN.read_text()); pins=plan['measurement_inputs']['pins']
    descriptors=[v for v in pins.values() if isinstance(v,dict) and 'bytes' in v]
    exact_bytes=sum(x['bytes'] for x in descriptors)+3066135
    if exact_bytes!=plan['admission']['source_geometry_inputs_bytes']: raise SystemExit('planned source input byte total mismatch')
    pressure=run(['/usr/bin/memory_pressure','-Q'])
    free_match=re.search(r'System-wide memory free percentage: (\d+)%',pressure)
    if not free_match: raise SystemExit('could not read system memory availability')
    free_pct=int(free_match.group(1)); physical=8589934592; available=int(physical*free_pct/100)
    df_fields=run(['/bin/df','-k',str(REPO)]).splitlines()[-1].split()
    df_free_kib=int(df_fields[3]); df_free=df_free_kib*1024
    stat=os.statvfs(REPO); disk_free=stat.f_bavail*stat.f_frsize; shutil_free=shutil.disk_usage(REPO).free
    if disk_free!=shutil_free: raise SystemExit('statvfs/shutil free-byte readings disagree')
    manager_script=f"import {{workspaceManager}} from './scripts/local-workspace.mjs'; const x=workspaceManager(process.cwd()).check(); console.log(JSON.stringify({{freeBytes:x.freeBytes,checkoutBytes:x.checkoutBytes,limits:x.limits}}));"
    manager=json.loads(run([NODE,'--input-type=module','-e',manager_script]))
    ps=run(['/bin/ps','-axo','pid=,rss=,comm='])
    proc=[]
    for line in ps.splitlines():
        cols=line.strip().split(None,2)
        if len(cols)==3 and cols[0].isdigit() and cols[1].isdigit():
            pid=int(cols[0])
            if pid==os.getpid(): continue
            rss=int(cols[1])*1024; name=Path(cols[2]).name
            proc.append({'pid':pid,'rss_bytes':rss,'name':name})
    gis=[x for x in proc if any(k in x['name'].lower() for k in ('ogr','gdal','shapely','geos')) or x['name'].lower() in ('python3.12','python3') and x['rss_bytes']>150*1024*1024]
    if free_pct<MIN_FREE_PERCENT: raise SystemExit(f'GIS admission denied: system free memory {free_pct}% below {MIN_FREE_PERCENT}% floor')
    if disk_free < manager['limits']['minimumFree']+OUTPUT_RESERVE+SCRATCH_RESERVE: raise SystemExit('GIS admission denied: output/scratch reserve would breach workspace free-storage floor')
    if available < 2*RSS_CAP: raise SystemExit('GIS admission denied: available memory is less than twice the phase RSS cap')
    if gis: raise SystemExit('GIS admission denied: competing GIS process visible: '+json.dumps(gis))
    if manager['freeBytes'] < manager['limits']['minimumFree']+OUTPUT_RESERVE+SCRATCH_RESERVE: raise SystemExit('GIS admission denied: workspace manager free bytes lack output/scratch reserve')
    runtime={'python':sys.version,'python_executable':{'path':PYTHON,'bytes':Path(PYTHON).stat().st_size,'sha256':sha(Path(PYTHON))},'shapely':shapely.__version__,'geos':shapely.geos_version_string,'pyproj':pyproj.__version__}
    state={'version':1,'status':'admitted','admitted_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'issue':1510,
      'coordination':'ENG authorized the next GIS window after GEO5 and the root numerical cohort were terminal; root audit may continue only within spare combined capacity. No overlapping GIS was visible.',
      'memory':{'physical_bytes':physical,'system_free_percent':free_pct,'estimated_free_bytes':available,'minimum_free_percent':MIN_FREE_PERCENT,'runtime_low_guard_percent':LOW_GUARD_PERCENT,'minimum_available_bytes':2*RSS_CAP,'phase_rss_cap_bytes':RSS_CAP},
      'storage':{'filesystem':df_fields[0],'free_bytes_statvfs':disk_free,'free_bytes_shutil':shutil_free,'df_reported_free_bytes_diagnostic_only':df_free,'df_statvfs_discrepancy_bytes':disk_free-df_free,'manager_free_bytes':manager['freeBytes'],'manager_checkout_bytes':manager['checkoutBytes'],'minimum_free_bytes':manager['limits']['minimumFree'],'complete_output_reserve_bytes':OUTPUT_RESERVE,'scratch_reserve_bytes':SCRATCH_RESERVE,'postreserve_bytes':disk_free-OUTPUT_RESERVE-SCRATCH_RESERVE},
      'live_processes_over_250MiB':[x for x in proc if x['rss_bytes']>=250*1024**2],'competing_gis_processes':gis,
      'inputs':{'geometry_source_bytes':exact_bytes,'descriptor_count':len(descriptors),'wfs_responses':14,'wfs_features':658,'wfs_bytes':3066135,'scope':{'cases':7,'candidate_context':15,'family_members':400,'neighbors':36}},
      'producer_sha256':sha(ROOT/'measure_norway_physical.py'),'runner_sha256':sha(ROOT/'run_geometry_phase.py'),'plan_sha256':sha(PLAN),'source_index_sha256':sha(ROOT/'sources/sjoekart-dybdedata-wfs-20261008/source-snapshot-index.json'),
      'runtime':runtime,'phase_rss_cap_bytes':RSS_CAP,'phase_time_limit_seconds':900,'output_reserve_bytes':OUTPUT_RESERVE,'scratch_reserve_bytes':SCRATCH_RESERVE,
      'no_geometry_read_during_admission':True}
    OUT.write_text(json.dumps(state,indent=2)+'\n')
    print(json.dumps({k:state[k] for k in ('status','admitted_at','memory','storage','inputs','producer_sha256','runner_sha256','runtime','phase_rss_cap_bytes','phase_time_limit_seconds')},indent=2))
if __name__=='__main__': main()
