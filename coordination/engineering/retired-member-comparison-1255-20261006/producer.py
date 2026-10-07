"""Complete frozen retired-member coverage comparison for issue1255 only."""
import argparse,collections,gzip,hashlib,json,pathlib,platform,subprocess,sys,time,zlib,re
import numpy,shapely
from shapely.geometry import mapping
P=pathlib.Path(__file__).resolve().parent;R=P.parents[2];PREFIX=str(P.relative_to(R))
sys.path.insert(0,str(R/'scripts'))
from evidence.immutable import canonical_json as canon,deterministic_gzip
from reader import Inputs,authenticate_executed_modules,output_target,SHA,validate_family_scope,validate_pointsets
from kernel import member_union,compare
M='79ffb2ed04702e16f009e4675a8d74ef9bd09d4f';H='549cc2a863d4a487a662c2613e4d02888e39b5ba';N='a26f8d8b50e7349054b86e70d1e6e552a9a2b0fd';S='7c7cdf2388e0e7200b937c2cfb440b53165d9d98'


class Objects:
    def __init__(self,output):self.output=output;self.entries={};self.rows=[];self.bytes=0;self.shards=[]
    def flush(self):
        if not self.rows:return
        p=self.output/'objects'/('objects-%03d.json.gz'%len(self.shards));p.parent.mkdir(exist_ok=True)
        b=deterministic_gzip(canon(self.rows));p.write_bytes(b)
        self.shards.append({'path':str(p.relative_to(self.output)),'bytes':len(b),'sha256':SHA(b),'decoded_bytes':len(canon(self.rows)),'decoded_sha256':SHA(canon(self.rows)),'records':len(self.rows)})
        self.rows=[];self.bytes=0
    def retain(self,g):
        raw=canon(g);h=SHA(raw)
        if h not in self.entries:
            if len(raw)>8*1024*1024:
                self.flush();parts=[]
                for offset in range(0,len(raw),8*1024*1024):
                    part=raw[offset:offset+8*1024*1024];p=self.output/'objects'/(h+'-%03d.bin.gz'%len(parts));p.parent.mkdir(exist_ok=True);b=deterministic_gzip(part);p.write_bytes(b)
                    parts.append({'offset':offset,'path':str(p.relative_to(self.output)),'bytes':len(b),'sha256':SHA(b),'decoded_bytes':len(part),'decoded_sha256':SHA(part)})
                self.entries[h]={'codec':'canonical-json-exact-byte-fragments','canonical_bytes':len(raw),'parts':parts}
            else:
                row={'id':h,'geometry':g};n=len(canon(row))
                if self.rows and self.bytes+n>8*1024*1024:self.flush()
                self.rows.append(row);self.bytes+=n;self.entries[h]={'codec':'canonical-json-object-in-indexed-shard','canonical_bytes':len(raw)}
        return {'canonical_geometry_sha256':h,'object_index':'objects.json'}


def run(commit,target):
    if not isinstance(commit,str)or not re.fullmatch('[a-f0-9]{40}',commit):raise ValueError('Immutable execution commit required before Git')
    versions={'python':platform.python_version(),'numpy':numpy.__version__,'shapely':shapely.__version__,'geos':shapely.geos_version_string,'zlib':zlib.ZLIB_VERSION}
    expected={'python':'3.12.14','numpy':'2.3.5','shapely':'2.1.2','geos':'3.13.1','zlib':'1.2.12'}
    if versions!=expected:raise ValueError('Pinned numerical runtime required')
    project=[PREFIX+'/'+name for name in ['producer.py','reader.py','kernel.py']]+['scripts/evidence/immutable.py']
    modules=authenticate_executed_modules(R,commit,project)
    imported={pathlib.Path(sys.modules[n].__file__).resolve()for n in ['reader','kernel','evidence.immutable']}
    if imported!={R/p for p in project[1:]}:raise ValueError('Actual imported module paths differ')
    inputs=Inputs(R,commit,PREFIX);index=json.loads(inputs.read('input-index.json'))
    scope=json.loads(inputs.read(index['scope']['path'],index['scope'],decode=True));plan=json.loads(inputs.read(index['complete_remaining_plan']['path'],index['complete_remaining_plan'],decode=True))
    allocations=[r for r in plan['complete_family_allocations']if r['disjoint_allocation']==scope['predicate'].split(' == ')[1]]
    if sorted(r['family']for r in allocations)!=scope['family_ids']or sorted(i for r in allocations for i in r['component_ids'])!=scope['component_ids']:raise ValueError('Full-family scope differs')
    report=inputs.original(N,'coordination/engineering/worldwide-native-batches-1184-20261006/current-run-one/report.json',index);families={};fidset=set(scope['family_ids']);idset=set(scope['component_ids'])
    for pin in report['outputs']['current-batches']:
        for row in inputs.original(N,pin['path'],index):
            if row['id']in fidset:
                if row['id']in families:raise ValueError('Duplicate family')
                families[row['id']]=row
    if set(families)!=fidset or sorted(i for row in families.values()for i in row['component_ids'])!=scope['component_ids']:raise ValueError('Complete component/family membership mismatch')
    if sorted({i for f in families.values()for i in f['contact_ids']})!=scope['contact_ids']:raise ValueError('Complete contact roster differs')
    for f in families.values():
        if len(f['component_ids'])!=f['component_count']or f['component_ids']!=sorted(set(f['component_ids']))or SHA(canon(f['component_ids']))!=f['component_ids_sha256']:raise ValueError('Family roster count/digest differs')
    validate_family_scope(scope,families)
    ir=inputs.original(M,'coordination/engineering/worldwide-inventory-1164-20261006/run-one/report.json',index);features={}
    for pin in ir['complete_products']['components']:
        path=next(p['path']for p in ir['source_descriptors']if p['sha256']==pin['sha256'])
        for f in inputs.original(M,path,index)['features']:
            if f['id']in idset:
                if f['id']in features:raise ValueError('Duplicate original component')
                features[f['id']]=f
    successor=inputs.original(S,'coordination/engineering/worldwide-successor-1215-20261006/run-one/report.json',index)
    delta=inputs.original(S,'coordination/engineering/worldwide-successor-1215-20261006/run-one/components-delta.json.gz',index)
    if set(delta['removed_ids'])&idset:raise ValueError('Removed component in selected scope')
    for f in delta['upsert_records']:
        if f['id']in idset:features[f['id']]=f
    expected_features={r['id']:r for r in scope['existing_current_component_and_member_pins']}
    if set(features)!=idset:raise ValueError('Missing current component')
    for i,f in features.items():
        if SHA(canon(f))!=expected_features[i]['canonical_feature_sha256']or SHA(canon(f['geometry']))!=expected_features[i]['geometry_sha256']:raise ValueError('Current full feature/geometry mismatch')
    contexts={};cr=inputs.original(H,'coordination/engineering/worldwide-contexts-1184-20261006/run-one/report.json',index)
    for pin in cr['outputs']:
        for row in inputs.original(H,pin['path'],index):
            if row['id']in contexts:raise ValueError('Duplicate original context')
            contexts[row['id']]=SHA(canon(row))  # Full bytes/fields consumed and retained; keep compact roster in memory.
    if len(contexts)!=49625 or not set(scope['contact_ids'])<=set(contexts):raise ValueError('Incomplete context/contact closure')
    archive=inputs.archive(index);members={r['id']:r for r in archive['locations']}
    if len(members)!=19050 or len(archive['locations'])!=19050:raise ValueError('Duplicate archive membership')
    if not set(scope['member_ids'])<=set(members):raise ValueError('Original member absent')
    for binding in scope['retired_member_complete_record_pins']:
        r=members[binding['id']]
        if SHA(canon(r))!=binding['canonical_record_sha256']or SHA(canon(r['geometry']))!=binding['canonical_geometry_sha256']or canon(r['metadata'])!=canon(binding['metadata']):raise ValueError('Changed original member geometry/metadata representation')
    validate_pointsets(scope,features,members)
    # Every declared alias is authenticated, including actual historical recipe and
    # metadata context not consumed by the literal geometry loop.
    for a in index['aliases']:inputs.original(a['original']['commit'],a['original']['path'],index,parse=False)
    for a in index['attribution_context']:inputs.read(a['ordinary']['path'],a['ordinary'])
    target.mkdir(parents=True,exist_ok=False);objects=Objects(target);rows=[];size=0;outputs=[];counts=collections.Counter();family_results=[];processed=[]
    def retain_pointset(p):
        if 'geometry'in p:p['geometry_reference']=objects.retain(p.pop('geometry'))
        return p
    def flush():
        nonlocal rows,size
        if not rows:return
        p=target/('components-%03d.json.gz'%len(outputs));raw=canon(rows);b=deterministic_gzip(raw);p.write_bytes(b);outputs.append({'path':p.name,'bytes':len(b),'sha256':SHA(b),'decoded_bytes':len(raw),'decoded_sha256':SHA(raw),'records':len(rows)});rows=[];size=0
    allocations={r['family']:r for r in allocations};union_cache={}
    for fid in sorted(families):
        f=families[fid];a=allocations[fid];mids=a['recorded_physical_member_ids']
        actual_mids=sorted({i for source in f['source_families']for i in source.get('original_source_member_ids',[])})
        if actual_mids!=mids or not mids or any(source['kind']!='physical-adaptation-processing-reproduction'for source in f['source_families']):raise ValueError('Wrong source/member/role closure')
        key=tuple(mids)
        if key not in union_cache:union_cache[key]=member_union([members[i]for i in mids])
        diagnostic,u=union_cache[key];family_diag=json.loads(canon(diagnostic));
        if 'union'in family_diag:retain_pointset(family_diag['union'])
        fc=collections.Counter();family_results.append({'family':f,'complete_original_member_ids':mids,'literal_member_union':family_diag,'recipe_context':{'recorded':f['source_families'],'inspected_routes':{'resolve':'scripts/refine-remote.py','ibra':'scripts/refine-remote.py','aafc':'scripts/semantic-locations.py','natural-earth':'unresolved-actual-lake-or-adaptation-route'},'execution_identity':'unverified','physical_classification':'unverified'},'counts':fc})
        for i in f['component_ids']:
            row=compare(features[i],u);row['family']=fid;row['complete_member_ids']=mids;row['source_union_reference']=family_diag;row['component_full_feature_sha256']=expected_features[i]['canonical_feature_sha256'];row['component_geometry_sha256']=expected_features[i]['geometry_sha256'];row['original_native_scope_bucket']=f['grouping']['observed_scope_bucket'];row['contacts']=f['contact_ids'];row['edge_neighbor_ids']=f['edge_neighbor_ids'];row['existing_related_issues']=f['existing_related_issues']
            for name in ['intersection','difference']:
                if name in row:retain_pointset(row[name])
            n=len(canon(row))
            if n>8*1024*1024:raise ValueError('Component metadata unexpectedly exceeds ordinary shard budget')
            if rows and size+n>8*1024*1024:flush()
            rows.append(row);size+=n;processed.append(i);counts[row['status']]+=1;fc[row['status']]+=1
            if len(processed)%1000==0:print('processed',len(processed),dict(counts),flush=True)
    flush();objects.flush()
    if sorted(processed)!=scope['component_ids']or len(processed)!=20032 or len(family_results)!=2476:raise ValueError('Complete cohort accounting mismatch')
    for f in family_results:f['counts']=dict(f['counts'])
    family_outputs=[];batch=[];n=0
    for f in family_results:
        b=canon(f)
        if batch and n+len(b)>8*1024*1024:
            raw=canon(batch);p=target/('families-%03d.json.gz'%len(family_outputs));encoded=deterministic_gzip(raw);p.write_bytes(encoded);family_outputs.append({'path':p.name,'bytes':len(encoded),'sha256':SHA(encoded),'decoded_bytes':len(raw),'decoded_sha256':SHA(raw),'records':len(batch)});batch=[];n=0
        batch.append(f);n+=len(b)
    if batch:
        raw=canon(batch);p=target/('families-%03d.json.gz'%len(family_outputs));encoded=deterministic_gzip(raw);p.write_bytes(encoded);family_outputs.append({'path':p.name,'bytes':len(encoded),'sha256':SHA(encoded),'decoded_bytes':len(raw),'decoded_sha256':SHA(raw),'records':len(batch)})
    (target/'objects.json').write_bytes(canon({'objects':objects.entries,'shards':objects.shards}))
    result={'version':1,'complete_components':20032,'complete_families':2476,'complete_members':2438,'complete_contacts':869,'component_roster_sha256':scope['roster_canonical_sha256']['components'],'family_roster_sha256':scope['roster_canonical_sha256']['families'],'counts':dict(counts),'component_outputs':outputs,'family_outputs':family_outputs,'object_index':{'path':'objects.json','bytes':(target/'objects.json').stat().st_size,'sha256':SHA((target/'objects.json').read_bytes())},'code_commit':commit,'executed_project_modules':modules,'actual_consumed_ordinary_inputs':inputs.pins,'software':versions,'scope_source_commit':N,'accepted_current_successor':S,'limits':['Literal retired original member coverage only; archived member geometry is not upstream administrative authority.','No wrapping, snapping, simplification, MakeValid, buffering, nearest filling or cutoff.','Exact diagnostic union does not authenticate the original executed intermediate recipe.','Land/water, political ownership, historical cause and repair safety remain unverified.','All source licenses/citations retained; underlying Direct Permission remains independently unverified.']}
    (target/'report.json').write_bytes(canon(result));inputs.close();print(json.dumps({'complete':True,'counts':dict(counts),'report_sha256':SHA(canon(result))}),flush=True)

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--code-commit',required=True);a.add_argument('--output',required=True);args=a.parse_args()
    target=output_target(R,PREFIX,args.output)
    run(args.code_commit,target)
