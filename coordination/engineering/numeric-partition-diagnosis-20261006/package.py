"""Retain complete actual diagnostic runs and measure the ordinary closure."""
import collections,datetime,gzip,json,pathlib,shutil,subprocess,sys
P=pathlib.Path(__file__).resolve().parent;R=P.parents[2];PREFIX=str(P.relative_to(R));sys.path.insert(0,str(P))
import custody
from custody import canon,SHA
BASE='c9bd47774b1ea8216d9cd4608ce2a20e15a2962b';FREEZE='a3a6b3761ddfc422f15be6686f492fbf04ae63d5';METHOD='complete-partition-pointset-diagnosis-v1'
NOW=datetime.datetime.now(datetime.timezone.utc).isoformat()


def descriptor(path,b=None,decoded=None):
    b=(R/path).read_bytes()if b is None else b
    d={'path':path,'bytes':len(b),'sha256':SHA(b),'hash_kind':'file-bytes'}
    if decoded is True or(decoded is None and path.endswith('.gz')):
        raw=gzip.decompress(b);d.update(uncompressed_bytes=len(raw),uncompressed_sha256=SHA(raw))
    if max(d['bytes'],d.get('uncompressed_bytes',0))>32*1024*1024:raise ValueError('Ordinary size exceeded '+path)
    return d


def package():
    reports=[];trees=[]
    for name in ['one','two']:
        src=P/('.cache/final-run-'+name);dst=P/('run-'+name)
        if not dst.exists():shutil.copytree(src,dst)
        paths=sorted(p.relative_to(src)for p in src.rglob('*')if p.is_file())
        if paths!=sorted(p.relative_to(dst)for p in dst.rglob('*')if p.is_file()):raise ValueError('Complete retained run tree differs')
        for path in paths:
            if (src/path).read_bytes()!=(dst/path).read_bytes():raise ValueError('Actual second/full run bytes not retained')
        trees.append([(str(path),SHA((src/path).read_bytes()))for path in paths]);reports.append(json.loads((dst/'report.json').read_bytes()))
    if trees[0]!=trees[1]or reports[0]['execution_commit']!=FREEZE or reports[1]['execution_commit']!=FREEZE:raise ValueError('Actual same-final-producer complete reproducibility failed')
    report=reports[0];v=P/'verification';v.mkdir(exist_ok=True)
    def write(name,obj):(v/name).write_bytes(canon(obj))
    controls=json.loads((P/'.cache/final-controls.log').read_bytes());full=json.loads((P/'.cache/full-readback-one.json').read_bytes())
    write('controls.json',controls)
    write('positive-control.json',{'method_id':METHOD,'kind':'positive-control','outcome':'passed','complete_diagnostic_replay':full,'directed_control_count':controls['directed_controls'],'physical_source_authority_approval':False})
    write('negative-control.json',{'method_id':METHOD,'kind':'negative-control','outcome':'passed','actual_directed_controls':controls,'physical_source_authority_approval':False})
    digest=SHA(canon(trees[0]));write('reproducibility.json',{'method_id':METHOD,'kind':'reproducibility','outcome':'passed','run_one_sha256':digest,'run_two_sha256':SHA(canon(trees[1])),'all_complete_files_equal':trees[0],'actual_code_commit':FREEZE,'both_complete_reports_and_scientific_trees_retained':True})
    for name in ['one','two']:
        (v/('run-'+name+'.log')).write_bytes((P/('.cache/final-run-'+name+'.log')).read_bytes())
        (v/('full-readback-'+name+'.json')).write_bytes((P/('.cache/full-readback-'+name+'.json')).read_bytes())
    write('input-only-preflight.json',json.loads((P/'.cache/final-input-only.log').read_bytes()))
    write('digest-prose-correction.json',json.loads((P/'.cache/roster-digest-algorithm-correction.json').read_bytes()))
    (v/'failed-input-only-declared-algorithm.log').write_bytes((P/'.cache/failed-input-only-incorrect-declared-digest-algorithm.log').read_bytes())
    write('failed-input-only-declared-algorithm.json',{'status':'preserved-failed-input-only-attempt','failure':'Issue prose said LF-joined identifiers; all five unchanged acceptance digests actually encode canonical JSON arrays with final LF. Complete ordinary reconstruction verified the latter; issue prose was narrowly corrected.','counted_scientific_run':False,'original_scope_counts_or_digest_values_changed':False})
    write('executions.json',json.loads((P/'.cache/executions.json').read_bytes()))
    for name in ['complete-reason-and-consensus-aggregation.json','complete-dimension-and-example-aggregation.json']:
        write(name,json.loads((P/'.cache'/name).read_bytes()))
    # Complete evidence buckets retain all cases and all intact family contexts.
    rows=[]
    for pin in report['component_outputs']:rows.extend(json.loads(gzip.decompress((P/'run-one'/pin['path']).read_bytes())))
    buckets=collections.defaultdict(list)
    for row in rows:
        key=(row['family'],row['status'],row.get('observed_reason','unknown-operation'),row['coverage_observation']['status'])
        buckets[key].append(row['component'])
    grouped=[{'family':key[0],'diagnosis_status':key[1],'observed_reason':key[2],'literal_coverage_status':key[3],'component_ids':sorted(ids),'component_count':len(ids),'pointset_and_archived_row_location':'Join component_outputs by component; every complete new and original reference is retained.','causal_conclusion':'unresolved','physical_source_authority':'unverified'}for key,ids in sorted(buckets.items())]
    write('complete-outcome-buckets.json',{'families':len(report['scope_rosters']['families']),'components':len(rows),'buckets':grouped,'limits':['Reason buckets are full runtime diagnostic observations, not historical causes or confirmed map defects.']})
    summary={'components':len(rows),'families':len(report['scope_rosters']['families']),'context_components':len(report['scope_rosters']['context_components']),'members':len(report['scope_rosters']['members']),'contacts':len(report['scope_rosters']['contacts']),'counts':report['counts'],'observed_reasons':report['observed_reasons'],'literal_coverage_observations':report['literal_coverage_observations']};write('summary.json',summary)
    required={'retired_member_complete_run_report':('run-one/report.json','13cd9b18fae16f1ce0a2197fcb832ca6da595168bb58a23b1f85c8998590a6c7'),'complete_unknown_aggregation':('diagnostic-unknowns.json.gz','c798574769811cec2075e28885427c7267c5bcf26b27f559e8f976759ceba614'),'complete_original_input_index':('input-index.json','d5c79868705da0900253f2a56a2700b193bc0aff71589e33104eb1646a7cb2e3')}
    baseline=[];pin_files={}
    for name,(path,h)in required.items():
        path=custody.OLD_PREFIX+'/'+path;b=subprocess.check_output(['git','show',BASE+':'+path],cwd=R)
        if SHA(b)!=h:raise ValueError('Required immutable baseline differs')
        baseline.append({**descriptor(path,b),'role':'original-source'});pin_files[name]=path
    imported={row['path']:row for row in report['actual_executed_project_modules']+full['actual_replay_modules']}
    for module in imported.values():
        if module['path'].startswith(PREFIX+'/'):continue
        b=subprocess.check_output(['git','show',BASE+':'+module['path']],cwd=R)
        if SHA(b)!=module['sha256']:raise ValueError('Imported original helper bytes differ')
        baseline.append(descriptor(module['path'],b))
    sources=[]
    for pin in report['actual_consumed_ordinary_inputs']:
        b=subprocess.check_output(['git','show',BASE+':'+pin['path']],cwd=R)
        if SHA(b)!=pin['sha256']or len(b)!=pin['bytes']:raise ValueError('Whole frozen input differs at PR baseline')
        d=descriptor(pin['path'],b,decoded='decoded_sha256'in pin)
        if 'decoded_sha256'in pin and(d['uncompressed_sha256']!=pin['decoded_sha256']or d['uncompressed_bytes']!=pin['decoded_bytes']):raise ValueError('Decoded complete input differs')
        sources.append(d)
    files=sorted(p for p in P.rglob('*')if p.is_file()and'.cache'not in p.relative_to(P).parts and'__pycache__'not in p.relative_to(P).parts and p.name!='evidence-quality.json')
    outputs=[descriptor(str(p.relative_to(R)))for p in files]
    metrics=[];bindings=[];summaries=[]
    for group in ['counts','observed_reasons','literal_coverage_observations']:
        for key,value in summary[group].items():
            metric_id=group+'-'+key;metrics.append({'id':metric_id,'value':value,'unit':'records','vintage':'archived','evaluation_commit':FREEZE,'input_sha256':required['retired_member_complete_run_report'][1]});bindings.append({'metric_id':metric_id,'path':PREFIX+'/verification/summary.json','json_pointer':'/'+group+'/'+key});summaries.append({'metric_id':metric_id,'value':value,'unit':'records'})
    manifest={'version':1,'issue':1270,'worker_id':'01a112b0-39fb-7f02-a3c7-d21d0916009f','lane':'engineering','subject_ids':[],'subject_ids_sha256':SHA(b'[]'),'baseline':{'commit':BASE,'files':baseline,'pins':{k:v[1]for k,v in required.items()},'pin_files':pin_files},'sources':[{'id':'complete-frozen-predecessor-input-custody','url':'https://github.com/ChengshuLi/WorldAtlas/issues/1255','role':'Complete original component/source/member/context bytes and accepted full diagnostic pointsets, including exact whole archive encoded/decoded fragmentation and original attribution.','vintage':'Frozen actual ec4783 predecessor and original per-alias immutable vintages; identical whole bytes independently authenticated at declared PR baseline.','retrieved_at':NOW,'license':{'status':'redistributable','terms':'Previously retained repository and derivative bytes; complete original citation/use terms retained. Underlying government Direct Permission remains unverified, not a new permission claim.'},'retention':'retained','verification':'unverified','temporal_status':'reference','files':sources}],'outputs':outputs,'methods':[{'id':METHOD,'kind':'generator','helper_version':'worldatlas-evidence-preparation-v1','description':'Complete stored partition reconstruction/lost/added pointsets and full runtime predicate evidence; conservative typed literal source relation where predicates and whole overlay checks agree. Original strict unknowns preserved; no tolerance, physical assignment, exact arithmetic or historical cause inference.','software':'Frozen producer '+FREEZE+'; Python3.12.14 NumPy2.3.5 Shapely2.1.2 GEOS3.13.1 zlib1.2.12','units':'Planar longitude/latitude coordinate units, dimensions and record counts; no physical area measurement'}],'metrics':metrics,'metric_bindings':bindings,'summaries':summaries,'conclusions':[],'stages':{'research':'partial','implementation':'implemented','geographic_approval':'not-requested'},'validation':[{'method_id':METHOD,'kind':kind,'outcome':'passed','evidence_path':PREFIX+'/verification/'+name}for kind,name in [('positive-control','positive-control.json'),('negative-control','negative-control.json'),('reproducibility','reproducibility.json')]],'commands':['producer.py --code-commit '+FREEZE+' --output OWNED_ABSENT_DESTINATION','controls.py (directed fixtures only)','verify.py --run OWNED_COMPLETE_RUN --output OWNED_READBACK_RECEIPT'],'change_receipts':[{'path':str(p.relative_to(R)),'status':'added'}for p in files]+[{'path':PREFIX+'/evidence-quality.json','status':'added'}]}
    (P/'evidence-quality.json').write_bytes(json.dumps(manifest,sort_keys=True,indent=2).encode()+b'\n')
    total=sum(d['bytes']for d in baseline+sources+outputs)
    if total>256*1024*1024 or len(baseline+sources+outputs)>512:raise ValueError('Complete final closure exceeds admission')
    print(json.dumps({'descriptors':len(baseline+sources+outputs),'actual_declared_encoded_bytes':total,'complete_scientific_files_per_run':len(trees[0]),'manifest_sha256':SHA((P/'evidence-quality.json').read_bytes())}))

if __name__=='__main__':package()
