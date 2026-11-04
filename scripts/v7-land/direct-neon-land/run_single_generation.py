#!/usr/bin/python3
"""One physical-component generation + manifest-bound streaming assignment.

Research-only orchestrator. Does not read V2/V6 continent labels or prove that a
local decision snapshot is authenticated/accepted. Outputs exclusively to a new
location and retains intermediate component streams and manifest.
"""
import argparse,hashlib,json,os,subprocess,sys
from pathlib import Path
import compile_land as compiler


def code_hashes():
    here=Path(__file__).resolve().parent
    return {name:compiler.assign_land.sha(path) for name,path in {
        'runner':Path(__file__).resolve(),'compiler':here/'compile_land.py',
        'stream_backend':here/'assign_land_stream.py','shared_backend':here.parent/'assign_land.py'}.items()}


def run(request_path,output,allow=False):
    compiler.require(allow,'explicit unverified research mode required')
    initial_code_hashes=code_hashes()
    raw=Path(request_path).read_bytes();r=json.loads(raw)
    compiler.obj(r,('schema','snapshot','grid','physical_rows','physical_runs','physical_report','source_files','component_source_sha256'),('strip_rows',),'request')
    compiler.require(r['schema']=='single-generation-direct-land-v1','invalid request schema')
    pins=[r[k] for k in ('snapshot','physical_rows','physical_runs','physical_report')]+[x['file'] for x in r['source_files']]
    compiler.pin(r['snapshot'])
    # Fail before the costly component stage if the draft contains candidates
    # that were not explicitly selected. The complete compiler repeats these checks.
    snapshot=json.loads(Path(r['snapshot']['path']).read_bytes());schema=snapshot.get('schema')
    rev=snapshot.get('decision_revision',{});entity=snapshot.get('entity_revision',{})
    compiler.require(snapshot.get('source')=='neon-export' and compiler.text(rev.get('id')) and
        rev.get('entity_revision')==entity.get('id') and ((schema=='worldatlas-geography-decision-draft-evidence-v1' and rev.get('status')==entity.get('status')=='draft') or
        (schema=='worldatlas-geography-decision-export-v1' and rev.get('status')==entity.get('status')=='accepted')), 'invalid snapshot revision')
    affiliations=[a for a in snapshot.get('affiliations',[]) if a.get('scope')=='land']
    witnesses=snapshot.get('land_component_witness_rules',[])
    compiler.require(isinstance(witnesses,list) and (schema!='worldatlas-geography-decision-draft-evidence-v1' or 'land_component_witness_rules' in snapshot), 'invalid witness rule list')
    compiler.require(not witnesses or schema=='worldatlas-geography-decision-draft-evidence-v1', 'witness rules are draft research only')
    if schema=='worldatlas-geography-decision-draft-evidence-v1':
        compiler.require(all(isinstance(a.get('evidence'),dict) and a['evidence'].get('execution_status')=='selected_for_research' for a in affiliations), 'unselected or unknown land affiliation')
    compiler.require(all(isinstance(a,dict) and isinstance(a.get('evidence'),dict) and a['evidence'].get('execution_status')=='selected_for_research' for a in witnesses), 'unselected or unknown witness rule')
    compiler.require(bool(affiliations) or bool(witnesses), 'no land decisions')
    # Check large physical and source files only after the draft selection gate.
    for p in pins[1:]:compiler.pin(p)
    physical_report=json.loads(Path(r['physical_report']['path']).read_bytes())
    physical_output=physical_report.get('physical_output_sha256',physical_report.get('output_sha256',{}))
    compiler.require(physical_report.get('status')=='candidate-only' and physical_report.get('grid')==r['grid'] and
        physical_output.get('rows.u32le')==r['physical_rows']['sha256'] and physical_output.get('runs.u32le')==r['physical_runs']['sha256'],
        'physical report does not bind grid and output streams')
    lineage_kind='raw-pipeline-report' if all(k in physical_report for k in ('physical_output_sha256','source_manifest','land_config','water_config','stage_reports')) else 'compose-report'
    output=Path(output).resolve();inputs=[Path(request_path).resolve()]+[Path(p['path']).resolve() for p in pins]
    compiler.require(all(not p.is_relative_to(output) and not output.is_relative_to(p.parent) for p in inputs),'output overlaps an input directory')
    source=Path(__file__).resolve().parent.parent/'build_components.cpp';source_hash=compiler.assign_land.sha(source)
    compiler.require(source_hash==r['component_source_sha256'],'component source hash mismatch')
    os.mkdir(output,mode=0o700);components=output/'components';components.mkdir(mode=0o700);configs=output/'configs';configs.mkdir(mode=0o700);manifests=output/'manifests';manifests.mkdir(mode=0o700)
    binary=components/'component-builder';build=subprocess.run(['g++','-std=c++17','-O2','-Wall','-Wextra','-Werror',str(source),'-o',str(binary)],capture_output=True,text=True)
    compiler.require(build.returncode==0,f'component builder compilation failed: {build.stderr[-3000:]}')
    rows=components/'rows.u32le';runs=components/'runs.u32le';g=r['grid']
    p=subprocess.run([str(binary),str(g['width']),str(g['height']),r['physical_rows']['path'],r['physical_runs']['path'],str(rows),str(runs)],capture_output=True,text=True)
    compiler.require(p.returncode==0,f'component build failed: {p.stderr[-3000:]}')
    def pin(path):return {'path':str(path),'sha256':compiler.assign_land.sha(path)}
    cpins={'physical_rows':r['physical_rows'],'physical_runs':r['physical_runs'],'component_rows':pin(rows),'component_runs':pin(runs)}
    compiler.require(compiler.assign_land.sha(source)==source_hash,'component source changed during generation')
    for item in pins:compiler.pin(item)
    manifest={'schema':'single-generation-component-manifest-v1','status':'complete-research','grid':g,'pins':cpins,
              'physical_report':r['physical_report'],'physical_report_kind':lineage_kind,'component_source_sha256':source_hash,'builder_binary':pin(binary),'builder_binary_sha256':compiler.assign_land.sha(binary),
              'compiler_version':subprocess.run(['g++','--version'],capture_output=True,text=True,check=True).stdout.splitlines()[0],
              'builder_output':p.stdout.strip()}
    mpath=manifests/'components.json';mpath.write_text(json.dumps(manifest,sort_keys=True,separators=(',',':'))+'\n')
    config={'schema':'direct-neon-land-build-v1','snapshot':r['snapshot'],'grid':g,**cpins,'source_files':r['source_files'],'strip_rows':r.get('strip_rows',128)}
    config_path=configs/'land.json';config_path.write_text(json.dumps(config,sort_keys=True,separators=(',',':'))+'\n')
    result=compiler.prepare(config_path,output/'assignment',True,mpath)
    compiler.require(Path(request_path).read_bytes()==raw,'request changed during run')
    for item in pins:compiler.pin(item)
    compiler.require(code_hashes()==initial_code_hashes,'code changed during run')
    report={'schema':'single-generation-direct-land-report-v1','status':'unverified-research-not-published','request_sha256':hashlib.sha256(raw).hexdigest(),
            'component_manifest_sha256':compiler.assign_land.sha(mpath),'land_report_sha256':compiler.assign_land.sha(output/'assignment/report.json'),
            'snapshot_sha256':r['snapshot']['sha256'],'code_sha256':initial_code_hashes,'physical_report_sha256':r['physical_report']['sha256'],'physical_report_kind':lineage_kind,'component_generations':1,
            'output_rows_sha256':result['compiler_report']['output_rows_sha256'],'output_runs_sha256':result['compiler_report']['output_runs_sha256'],
            'limitations':'Research only; the same-run component manifest is not independent verification. No historical continent grid was read.'}
    (output/'request.json').write_bytes(raw);(output/'report.json').write_text(json.dumps(report,indent=2)+'\n');return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('request',type=Path);p.add_argument('output',type=Path);p.add_argument('--allow-unverified-snapshot',action='store_true');a=p.parse_args()
    try:print(json.dumps(run(a.request,a.output,a.allow_unverified_snapshot),indent=2))
    except Exception as e:print(f'error: {e}',file=sys.stderr);raise SystemExit(1)
