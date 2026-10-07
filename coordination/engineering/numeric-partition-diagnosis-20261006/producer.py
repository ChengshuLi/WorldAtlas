"""Complete frozen numerical diagnosis for the exact6281-case issue1270 scope."""
import argparse,collections,importlib.util,json,pathlib,platform,re,sys,zlib
import numpy,shapely
P=pathlib.Path(__file__).resolve().parent;R=P.parents[2];PREFIX=str(P.relative_to(R))
import custody,numeric_kernel
from custody import load_original_inputs,load_complete_scientific_inputs,INPUT_COMMIT,OLD_PREFIX,SHA,canon
from reader import authenticate_executed_modules,output_target
from evidence.immutable import deterministic_gzip
spec=importlib.util.spec_from_file_location('retired_output',R/OLD_PREFIX/'producer.py');retired_output=importlib.util.module_from_spec(spec);sys.modules['retired_output']=retired_output;spec.loader.exec_module(retired_output)


def authenticate_execution(commit):
    if not isinstance(commit,str)or not re.fullmatch('[a-f0-9]{40}',commit):raise ValueError('Immutable execution commit required before Git')
    expected={PREFIX+'/'+x for x in ['producer.py','custody.py','numeric_kernel.py']}|{OLD_PREFIX+'/'+x for x in ['reader.py','kernel.py','producer.py']}|{'scripts/evidence/immutable.py'}
    actual=set()
    for module in list(sys.modules.values()):
        file=getattr(module,'__file__',None)
        if file:
            p=pathlib.Path(file).resolve()
            if p.is_relative_to(R):actual.add(str(p.relative_to(R)))
    if actual!=expected:raise ValueError('Actual project import closure differs from fixed scientific modules')
    modules=authenticate_executed_modules(R,commit,sorted(actual))
    versions={'python':platform.python_version(),'numpy':numpy.__version__,'shapely':shapely.__version__,'geos':shapely.geos_version_string,'zlib':zlib.ZLIB_VERSION}
    if versions!={'python':'3.12.14','numpy':'2.3.5','shapely':'2.1.2','geos':'3.13.1','zlib':'1.2.12'}:raise ValueError('Pinned numerical runtime required')
    return modules,versions


def write_parts(target,name,rows):
    parts=[];batch=[];size=0
    def flush():
        nonlocal batch,size
        if not batch:return
        raw=canon(batch);b=deterministic_gzip(raw);p=target/(name+'-%03d.json.gz'%len(parts));p.write_bytes(b)
        if len(raw)>32*1024*1024 or len(b)>32*1024*1024:raise ValueError('Oversized ordinary output')
        parts.append({'path':p.name,'bytes':len(b),'sha256':SHA(b),'decoded_bytes':len(raw),'decoded_sha256':SHA(raw),'records':len(batch)});batch=[];size=0
    for row in rows:
        n=len(canon(row))
        if n>8*1024*1024:raise ValueError('Oversized metadata row')
        if batch and size+n>8*1024*1024:flush()
        batch.append(row);size+=n
    flush();return parts


def run(commit,target,input_only=False):
    modules,versions=authenticate_execution(commit)
    inputs,scope,families,features,members=load_original_inputs()
    oldreport,oldobjects,oldfamilies,oldrows,familyrefs,rowrefs,rosters=load_complete_scientific_inputs(inputs,families)
    if input_only:
        print(json.dumps({'status':'complete-input-closure-authenticated-no-geometry-loop','input_commit':INPUT_COMMIT,'execution_commit':commit,'scope_counts':{k:len(v)for k,v in rosters.items()},'actual_consumed_inputs':inputs.pins,'actual_executed_modules':modules,'software':versions}),flush=True);inputs.close();return
    target.mkdir(parents=True,exist_ok=False);objects=retired_output.Objects(target)
    result=[];counts=collections.Counter();reasons=collections.Counter();coverage_counts=collections.Counter();perfamily=collections.defaultdict(collections.Counter)
    def operand(pointset):
        ref=pointset['geometry_reference']
        if ref['object_index']!='objects.json' or ref['canonical_geometry_sha256']not in oldobjects:raise ValueError('Missing frozen complete operand')
        return oldobjects[ref['canonical_geometry_sha256']]
    def retain(value):
        if isinstance(value,list):return [retain(x)for x in value]
        if not isinstance(value,dict):return value
        transformed={k:retain(v)for k,v in value.items()if k!='geometry'}
        if 'geometry'in value:transformed['geometry_reference']=objects.retain(value['geometry'])
        return transformed
    for i in rosters['unknown_components']:
        original=oldrows[i];fid=original['family'];u=oldfamilies[fid]['literal_member_union']
        if original['status']!='unknown-numerical-partition-disagreement' or original['partition_equals_original'] is not False or u['status']!='literal-original-member-union':raise ValueError('Original strict unknown scope changed')
        row=numeric_kernel.diagnose(features[i]['geometry'],operand(u['union']),operand(original['intersection']),operand(original['difference']))
        row=retain(row);row.update(component=i,family=fid,archived_original_diagnostic={'reference':rowrefs[i],'record':original},complete_member_ids=oldfamilies[fid]['complete_original_member_ids'],original_family_reference=familyrefs[fid],component_full_feature_sha256=original['component_full_feature_sha256'],component_geometry_sha256=original['component_geometry_sha256'],contacts=original['contacts'],edge_neighbor_ids=original['edge_neighbor_ids'],existing_related_issues=original['existing_related_issues'])
        result.append(row);counts[row['status']]+=1;reasons[row.get('observed_reason','unknown-operation')]+=1;coverage_counts[row['coverage_observation']['status']]+=1;perfamily[fid][row['status']]+=1
        if len(result)%1000==0:print('diagnosed',len(result),dict(counts),dict(coverage_counts),flush=True)
    if sorted(r['component']for r in result)!=rosters['unknown_components']:raise ValueError('Full unknown roster loss/duplicate')
    component_outputs=write_parts(target,'components',result);family_results=[]
    for fid in rosters['families']:
        family_results.append({'original_family_reference':familyrefs[fid],'original_complete_family':oldfamilies[fid],'diagnosed_unknown_component_ids':sorted(r['component']for r in result if r['family']==fid),'diagnosis_counts':dict(perfamily[fid]),'limits':['Coordinated family contacts are not newly measured component adjacency.','Original family pointset references belong to the frozen predecessor object namespace.']})
    family_outputs=write_parts(target,'families',family_results);objects.flush();(target/'objects.json').write_bytes(canon({'objects':objects.entries,'shards':objects.shards}))
    report={'version':1,'input_commit':INPUT_COMMIT,'execution_commit':commit,'original_complete_report_sha256':'13cd9b18fae16f1ce0a2197fcb832ca6da595168bb58a23b1f85c8998590a6c7','scope_rosters':rosters,'counts':dict(counts),'observed_reasons':dict(reasons),'literal_coverage_observations':dict(coverage_counts),'component_outputs':component_outputs,'family_outputs':family_outputs,'object_index':{'path':'objects.json','bytes':(target/'objects.json').stat().st_size,'sha256':SHA((target/'objects.json').read_bytes())},'actual_consumed_ordinary_inputs':inputs.pins,'actual_executed_project_modules':modules,'software':versions,'limits':['Original6281 numerical-partition unknown rows and their vintage remain unchanged.','Runtime pointset and predicate consensus is not an exact-arithmetic proof or source authority.','No epsilon, snap, simplify, buffer, MakeValid, wrapping, fill, physical/owner or historical-cause inference.','Unknown/missing/failed scientific operations retain complete scoped rows.','Complete archive/source attribution remains retained; underlying Direct Permission remains unverified.','Original pointset/family references use predecessor commit and full ordinary byte custody, not new objects.json.','Global1202 source/physical classification and actual map repair remain unfinished.']}
    (target/'report.json').write_bytes(canon(report));inputs.close();print(json.dumps({'complete':True,'counts':dict(counts),'coverage':dict(coverage_counts),'report_sha256':SHA(canon(report))}),flush=True)

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--code-commit',required=True);a.add_argument('--output',required=True);a.add_argument('--validate-inputs-only',action='store_true');args=a.parse_args()
    if not re.fullmatch('[a-f0-9]{40}',args.code_commit):raise ValueError('Immutable execution commit required before Git')
    target=output_target(R,PREFIX,args.output);run(args.code_commit,target,args.validate_inputs_only)
