"""Complete custody/semantic readback; no third operator or point-query execution."""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import tempfile
import time

from fractions import Fraction
from shapely.geometry import shape
import diagnose
import kernel
import reader

HERE=Path(__file__).resolve().parent

def require(condition,message):
    if not condition: raise ValueError(message)

def authenticate(repo,science_commit,verification_commit):
    for commit in (science_commit,verification_commit):
        require(re.fullmatch('[a-f0-9]{40}',commit) is not None,'Require immutable full commits')
    require(diagnose.git(repo,'show',verification_commit+':'+diagnose.OWNED+'verify.py')==
            reader.safe_path(HERE,'verify.py').read_bytes(),'Changed executed verifier')
    checked=[]
    for name in diagnose.CODE:
        raw=reader.safe_path(HERE,name).read_bytes()
        require(raw==diagnose.git(repo,'show',science_commit+':'+diagnose.OWNED+name),
                'Changed scientific module/config: '+name)
        checked.append(dict(path=diagnose.OWNED+name,bytes=len(raw),sha256=reader.digest(raw)))
    for module in list(sys.modules.values()):
        selected=getattr(module,'__file__',None)
        if selected:
            path=Path(selected).resolve()
            if path.is_relative_to(HERE) and path.suffix=='.py':
                require(str(path.relative_to(HERE)) in (*diagnose.CODE,'verify.py'),
                        'Undeclared executed verification module')
    for row in json.loads(reader.safe_path(HERE,'module-provenance.json').read_bytes()):
        require(reader.safe_path(HERE,row['path']).read_bytes()==
                diagnose.git(repo,'show',row['original_commit']+':'+row['original_path']),
                'Changed original helper provenance')
    return checked

def read_report(run):
    path=reader.safe_path(run,'report.json')
    require(path.stat().st_size<=reader.LIMIT,'Oversized ordinary report')
    raw=path.read_bytes();report=json.loads(raw)
    pins=report['outputs'];names=[x['path'] for x in pins]
    require(len(names)==len(set(names)),'Duplicate output descriptor')
    declared=set(names)|{'report.json'}
    descendants=list(run.rglob('*'))
    require(not any(x.is_symlink() for x in descendants),'Undeclared output symlink')
    actual={str(x.relative_to(run)) for x in descendants if x.is_file()}
    require(actual==declared,'Unindexed or omitted ordinary run output')
    for pin in pins:reader.checked(run,pin)
    return report,dict(path='report.json',bytes=len(raw),sha256=reader.digest(raw))

def rows(run,report,kind):
    pins=[x for x in report['outputs'] if x['path'].startswith(kind+'-')]
    names=[x['path'] for x in pins]
    require(names==[f'{kind}-{i:03}.jsonl.gz' for i in range(len(pins))],
            'Incomplete or unordered '+kind+' shards')
    for pin in pins:
        raw=reader.checked(run,pin)
        require(raw.endswith(b'\n'),'Incomplete JSONL row')
        for line in raw.splitlines():
            row=json.loads(line)
            require(reader.canonical(row)==line+b'\n','Noncanonical scientific row')
            yield row

def bindings(state,identity,original,pin):
    routing=state['routing'][identity]
    return dict(component_id=identity,original_whole_scientific_row=pin,
        full_current_feature_sha256=routing['current_feature_sha256'],
        full_current_geometry_sha256=routing['current_geometry_sha256'],
        actual_delivered_routing_row=dict(
            whole_raw_sha256=state['scope']['routing_source']['whole_components_raw_sha256'],
            actual_merge=state['scope']['routing_source']['actual_merge'],
            complete_body_restoration='declared complete25-part routing stream'),
        family=routing['family'],operational_batch=routing['operational_batch'],
        complete_original_contact_ids=original['complete_contact_ids'],
        original_physical_status=original['physical_status'],original_physical_limits=original['physical_limits'],
        original_source_vintage=original['source_vintage'],original_unresolved=original['unresolved'],
        current_routing_unknowns=routing['unresolved'],source_fitness_prerequisite=routing['source_fitness_prerequisite'])

def same(a,b):
    return reader.canonical(a)==reader.canonical(b)

def probe_structure(probe,geometry):
    require(probe['helper_version']==kernel.exact.VERSION and probe['coordinate_context']==kernel.exact.context(kernel.CONTEXT),
            'Changed probe method/context')
    require(probe['original_point_domain']=='IEEE754-binary64-as-exact-rational' and
            probe['derived_point_domain']=='exact-rational-centroid-of-original-binary64-triangle' and
            probe['whole_component_certification'] is False and probe['partition_repair_approval'] is False,
            'Promoted point probe or changed coordinate domain')
    require(probe['status'] in ('diagnostic','invalid','unsupported','unknown','unknown-operation-failed'),
            'Undeclared exact guard disposition')
    if probe['status']!='diagnostic':
        require('reason' in probe or 'exception_type' in probe,'Missing guarded failure evidence')
        return
    require(geometry.get('type') in ('Polygon','MultiPolygon'),'Diagnostic nonpolygon promoted')
    polygons=[geometry['coordinates']] if geometry['type']=='Polygon' else geometry['coordinates']
    vertices=[];triangles=[];nontriangles=[]
    for pi,polygon in enumerate(polygons):
        for ri,ring in enumerate(polygon):
            for vi,point in enumerate(ring[:-1]):vertices.append((pi,ri,vi,point))
        if len(polygon)==1 and len(polygon[0])==4:
            centre=[sum(Fraction(x[k]) for x in polygon[0][:-1])/3 for k in (0,1)]
            triangles.append((pi,[kernel.exact.rational(x) for x in centre]))
        else:nontriangles.append(dict(polygon=pi,interior_witness='not-certified'))
    require(len(vertices)==len(probe['vertices']) and len(triangles)==len(probe['triangles']),
            'Incomplete vertex/triangle roster')
    for (pi,ri,vi,point),row in zip(vertices,probe['vertices']):
        require((row['polygon'],row['ring'],row['vertex'])==(pi,ri,vi) and same(row['binary64_point'],point),
                'Changed original vertex binding')
        require(row['exact_candidate_state'] in ('inside','outside','boundary') and
                row['exact_residue_state'] in ('inside','outside','boundary'),'Invalid exact state label')
        require(all(type(row[k]) is bool for k in ('floating_candidate_covers','floating_candidate_contains','floating_residue_covers')),
                'Malformed literal floating observation')
    for (pi,centre),row in zip(triangles,probe['triangles']):
        require(row['polygon']==pi and same(row['exact_rational_centroid'],centre) and
                row['floating_observation']=='not-computed-for-derived-rational-point','Rounded or changed rational centroid')
        require(all(row[k] in ('inside','outside','boundary') for k in
                    ('exact_candidate_state','exact_residue_state','exact_triangle_state')),'Invalid triangle state label')
        require(row['interior_witness_certified'] is
                (row['exact_triangle_state']=='inside' and row['exact_residue_state']=='inside'),'Promoted triangle witness')
    require(probe['nontriangle_polygons']==nontriangles,'Lost nontriangle uncertainty')
    total=len(vertices)+len(triangles);segments=sum(len(ring)-1 for poly in polygons for ring in poly)
    require(probe['complete_query_count']==total,'Incomplete declared exact query count')
    offset=0
    for batch in probe['query_batches']:
        require(batch['start']==offset and 0<batch['count']<=kernel.exact.MAX_POINTS and
                batch['maximum_segments']>=segments and batch['maximum_segments']<=kernel.exact.MAX_SEGMENTS and
                batch['point_segment_work_bound']==batch['count']*batch['maximum_segments'] and
                batch['point_segment_work_bound']<=kernel.exact.MAX_POINT_SEGMENT_CHECKS,'Invalid exact query work boundary')
        offset+=batch['count']
    require(offset==total,'Incomplete exact query batches')

def validate_result(actual,state,identity,original,pin,db):
    for name,value in bindings(state,identity,original,pin).items():
        require(same(actual.get(name),value),'Changed complete original/current binding: '+name)
    levels,retained=kernel.reconstruct_levels(shape(state['candidates'][identity]['geometry']),original)
    require(same(actual['retained_query_context'],retained) and actual['query_count']==len(original['query_relations']) and
            actual['complete_level_piece_counts']=={str(k):len(levels[k]) for k in (1,2,3,4)} and
            same(actual['original_unknowns'],original.get('unresolved',[])),'Lost original query pieces/unknowns')
    require(actual['physical_authority']=='unapproved' and actual['partition_recovery']=='not-certified','Promoted physical/partition authority')
    require(actual['status'] in ('replayed','original-replay-mismatch','unknown-replay-failed'),'Invalid replay disposition')
    base=set(bindings(state,identity,original,pin))|{'retained_query_context','query_count','complete_level_piece_counts',
        'original_unknowns','physical_authority','partition_recovery','status','conservative_class','next_action'}
    if actual['status']=='unknown-replay-failed':
        require(set(actual)==base|{'exception_type','exception_message'} and
                actual['next_action']=='engineering-original-operation-failure-diagnosis', 'Changed failure schema/action')
        require(actual['conservative_class']=='retained-unresolved-replay-failure' and 'exception_type' in actual,
                'Missing original-operation failure evidence')
        return set()
    require(set(actual)==base|{'complete_geometry_mappings','complete_hierarchy_mappings',
        'geometry_byte_container_equality','hierarchy_geometry_equality','point_diagnostics','demonstrated_local_contradictions'},
        'Omitted or invented complete diagnostic field')
    fields={'complete_geometry_mappings':set(kernel.RELATIONS),
            'complete_hierarchy_mappings':{'L2-outside-L1','L3-outside-L2','L4-outside-L3'}}
    geometry={};used=set();equalities={}
    for field,roster in fields.items():
        require(set(actual[field])==roster,'Missing complete remeasured geometry mapping')
        equalities[field]={}
        for name,ref in actual[field].items():
            require(set(ref)=={'geometry_sha256','complete_pointset_family'} and ref['complete_pointset_family']=='geometry-objects',
                    'Changed complete pointset reference domain')
            stored=db.execute('select body from objects where sha=?',(ref['geometry_sha256'],)).fetchone()
            require(stored is not None,'Missing complete pointset object')
            body=json.loads(stored[0]);geometry[name]=body;used.add(ref['geometry_sha256'])
            old=original['complete_support'][name]['geometry'] if field=='complete_geometry_mappings' else \
                original['complete_support']['hierarchy_disagreements'][name]['geometry']
            equalities[field][name]=same(body,old)
    require(actual['geometry_byte_container_equality']==equalities['complete_geometry_mappings'] and
            actual['hierarchy_geometry_equality']==equalities['complete_hierarchy_mappings'],'False original pointset replay equality')
    matched=all(v for values in equalities.values() for v in values.values())
    if not matched:
        require(actual['status']=='original-replay-mismatch' and actual['point_diagnostics']=={} and
                actual['demonstrated_local_contradictions']==[] and
                actual['conservative_class']=='retained-unresolved-original-replay-mismatch' and
                actual['next_action']=='engineering-original-container-or-numerical-replay-mismatch-diagnosis',
                'Mismatch attributed to original104 or witness promoted')
        return used
    require(actual['status']=='replayed','Matching original pointsets not honestly labelled')
    probes=actual['point_diagnostics'];require(set(probes)==set(kernel.RELATIONS[3:])|fields['complete_hierarchy_mappings'],
                                             'Omitted complete residue/hierarchy diagnostic')
    contradictions=[]
    for relation in (*kernel.RELATIONS[3:],'L2-outside-L1','L3-outside-L2','L4-outside-L3'):
        probe=probes[relation]
        probe_structure(probe,geometry[relation])
        for witness in probe['triangles']:
            state_label=witness['exact_candidate_state']
            if witness['interior_witness_certified'] and ((relation=='extra_reconstruction' and state_label=='inside') or
                    (relation=='missing_reconstruction' and state_label=='outside')):
                contradictions.append(dict(relation=relation,polygon=witness['polygon'],candidate_state=state_label,
                                           evidence='certified-exact-rational-residue-triangle-interior'))
    require(actual['demonstrated_local_contradictions']==contradictions,'Incorrect local contradiction disposition')
    require(actual['next_action']==('engineering-source-preserving-numerical-operation-correction' if contradictions else
            'engineering-or-source-diagnosis-of-retained-unknowns'),'Wrong next prerequisite')
    require(actual['conservative_class']==('local-construction-contradiction-demonstrated' if contradictions else
            'retained-unresolved-numerical-or-context-prerequisite'),'Incorrect conservative unresolved class')
    return used

def verify(repo,run,science_commit,verification_commit,receipt):
    require(run.is_absolute() and not run.is_symlink(),'Require ordinary absolute run root')
    for parent in run.parents:require(not parent.is_symlink(),'Run ancestor symlink')
    require(receipt.is_absolute() and not receipt.exists() and
            receipt.resolve().is_relative_to(HERE/'.cache'),'Require absent owned verification receipt')
    for parent in receipt.parents:require(not parent.is_symlink(),'Receipt ancestor symlink')
    started=diagnose.utc();clock=time.monotonic()
    code=authenticate(repo,science_commit,verification_commit)
    report,report_pin=read_report(run)
    require(report['status']=='complete' and report['execution_commit']==science_commit,'Wrong complete execution')
    runtime=dict(python=diagnose.platform.python_version(),numpy=diagnose.numpy.__version__,
                 shapely=diagnose.shapely.__version__,geos=diagnose.shapely.geos_version_string,
                 pyproj=diagnose.pyproj.__version__)
    require(runtime==dict(python='3.12.14',numpy='2.3.5',shapely='2.1.2',geos='3.13.1',pyproj='3.7.2'),
            'Wrong actual verification runtime')
    require(report['runtime']==runtime and report['code']==code,'Science execution capsule differs')
    state=reader.load(repo)
    require(report['source_input_receipts']==state['receipts'] and report['original_reconstructor']==state['reconstructor'],
            'Complete source/helper custody differs')
    require(report['original_config_sha256']==state['original_config_sha256'] and
            report['derived_component_only_config_sha256']==state['derived_component_only_config_sha256'],
            'Wrong original/derived source configuration domain')
    expected_counts=dict(complete_current_components=95173,complete_numeric_components=26276,
                         complete_complement=68897,complete_families=3503,complete_batches=253)
    require(all(report[k]==v for k,v in expected_counts.items()),'Incomplete declared roster')
    seen=set();used=set();counts=Counter();families=defaultdict(list);batches=defaultdict(list)
    with tempfile.TemporaryDirectory(prefix='verify1300-',dir=HERE/'.cache') as temporary:
        db=sqlite3.connect(str(Path(temporary)/'objects.sqlite'))
        db.execute('create table objects (sha text primary key, body blob not null)')
        object_count=0
        for row in rows(run,report,'geometry-objects'):
            body=reader.canonical(row['geometry']);digest=reader.digest(body)
            require(digest==row['geometry_sha256'] and set(row)=={'geometry_sha256','geometry'},'Changed whole geometry object')
            try:db.execute('insert into objects values (?,?)',(digest,body))
            except sqlite3.IntegrityError:raise ValueError('Duplicate geometry object')
            object_count+=1
        db.commit();require(object_count==report['geometry_objects'],'Incomplete geometry-object roster')
        outputs=iter(rows(run,report,'diagnoses'))
        for number,(identity,original,pin) in enumerate(reader.physical_rows(state),1):
            actual=next(outputs,None)
            require(actual is not None and actual.get('component_id')==identity and identity not in seen,'Missing/duplicate/out-of-order diagnosis')
            seen.add(identity)
            used.update(validate_result(actual,state,identity,original,pin,db))
            counts[actual['status']]+=1;counts[actual['conservative_class']]+=1
            for field in ('geometry_byte_container_equality','hierarchy_geometry_equality'):
                for relation,equal in actual.get(field,{}).items():counts[field+':'+relation+':'+str(equal)]+=1
            for relation,diagnostic in actual.get('point_diagnostics',{}).items():counts['point:'+relation+':'+diagnostic['status']]+=1
            families[actual['family']].append(identity);batches[actual['operational_batch']].append(identity)
            if number%1000==0:print(json.dumps(dict(verified=number,target=26276)),flush=True)
        require(next(outputs,None) is None and seen==set(state['routing']),'Extra/omitted diagnosis')
        require(len(used)==object_count,'Unreferenced or omitted geometry object')
        db.close()
    for kind,groups,total in [('families',families,3503),('batches',batches,253)]:
        expected=[dict(id=key,members=sorted(members),member_count=len(members)) for key,members in sorted(groups.items())]
        require(len(expected)==total and list(rows(run,report,kind))==expected,'Incomplete disjoint '+kind+' roster')
    require(dict(counts)==report['counts'],'Complete scientific status/unknown counts differ')
    require(state['physical_restore_receipts']==report['complete_original104_file_restoration'],
            'Original71 complete restored body receipt mismatch')
    body=reader.canonical(dict(status='PASS',kind='complete whole-output custody, roster and semantic readback; no third operator or exact membership query run',
        science_commit=science_commit,verification_commit=verification_commit,actual_runtime=runtime,
        started_at=started,ended_at=diagnose.utc(),elapsed_seconds=time.monotonic()-clock,
        report=report_pin,outputs=report['outputs'],complete_components=len(seen),complete_families=len(families),
        complete_batches=len(batches),complete_geometry_objects=object_count,complete_inputs=len(state['receipts']),
        complete_original104_restored_files=len(state['physical_restore_receipts']),counts=dict(counts),
        limits=report['limits']+['Fresh overlay operators and exact candidate membership predicates are NOT re-executed in this complete reader; two actual frozen producer executions and bounded independent case controls supply that operation evidence.']))
    with receipt.open('xb') as handle:handle.write(body)
    print('PASS complete26276 custody and semantic readback without third numerical execution')

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    for name in ('repo','run','science-commit','verification-commit','receipt'):parser.add_argument('--'+name,required=True)
    args=parser.parse_args()
    verify(Path(args.repo).resolve(),Path(args.run),args.science_commit,args.verification_commit,Path(args.receipt))
