"""Independent complete diagnostic replay, preserving every archived unknown."""
import argparse,collections,gzip,json,pathlib,sys
P=pathlib.Path(__file__).resolve().parent
import custody,numeric_kernel
from custody import canon,SHA,load_original_inputs,load_complete_scientific_inputs,check_rosters
import importlib.util
spec=importlib.util.spec_from_file_location('predecessor_verify',custody.R/custody.OLD_PREFIX/'verify.py')
old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
read_pin=old.read_pin


def read_objects(run,index):
    objects={}
    for pin in index['shards']:
        values=read_pin(run,pin)
        if len(values)!=pin['records']:raise ValueError('Object shard count differs')
        for row in values:
            h=row['id']
            if h in objects or SHA(canon(row['geometry']))!=h:raise ValueError('Duplicate or changed complete object')
            objects[h]=row['geometry']
    for h,e in index['objects'].items():
        if e['codec']=='canonical-json-exact-byte-fragments':
            bodies=[];offset=0
            for pin in e['parts']:
                if pin['offset']!=offset:raise ValueError('Object fragment gap/reordering')
                p=run/pin['path']
                if p.is_symlink() or not p.is_file():raise ValueError('Missing ordinary object fragment')
                b=p.read_bytes();raw=gzip.decompress(b)
                if len(b)!=pin['bytes'] or SHA(b)!=pin['sha256'] or len(raw)!=pin['decoded_bytes'] or SHA(raw)!=pin['decoded_sha256'] or max(len(b),len(raw))>32*1024*1024:raise ValueError('Changed complete object fragment')
                bodies.append(raw);offset+=len(raw)
            body=b''.join(bodies)
            if h in objects or len(body)!=e['canonical_bytes'] or SHA(body)!=h:raise ValueError('Whole object reconstruction differs')
            objects[h]=json.loads(body)
        elif e['codec']!='canonical-json-object-in-indexed-shard':raise ValueError('Unsupported object codec')
    if set(objects)!=set(index['objects']):raise ValueError('Incomplete object index')
    for h,g in objects.items():
        if SHA(canon(g))!=h or len(canon(g))!=index['objects'][h]['canonical_bytes']:raise ValueError('Whole canonical geometry differs')
    return objects


EXTRAS={'component','family','archived_original_diagnostic','complete_member_ids','original_family_reference','component_full_feature_sha256','component_geometry_sha256','contacts','edge_neighbor_ids','existing_related_issues'}

def validate_row(row,expected,objects,original,family,rowref,familyref):
    extras={'component':original['component'],'family':original['family'],'archived_original_diagnostic':{'reference':rowref,'record':original},'complete_member_ids':family['complete_original_member_ids'],'original_family_reference':familyref,'component_full_feature_sha256':original['component_full_feature_sha256'],'component_geometry_sha256':original['component_geometry_sha256'],'contacts':original['contacts'],'edge_neighbor_ids':original['edge_neighbor_ids'],'existing_related_issues':original['existing_related_issues']}
    if any(canon(row.get(k))!=canon(v)for k,v in extras.items()):raise ValueError('Archived original row or complete family/source/context binding differs')
    old.validate_diagnostic({k:v for k,v in row.items()if k not in EXTRAS},expected,objects)


def validate_complete_counts(rows,roster,counts,reasons,coverage,report):
    if sorted(rows)!=roster or dict(counts)!=report['counts'] or dict(reasons)!=report['observed_reasons'] or dict(coverage)!=report['literal_coverage_observations']:raise ValueError('Complete diagnostic roster/count/reason/coverage differs')


def validate_family(stored,original,reference,component_ids,counts):
    expected={'original_family_reference':reference,'original_complete_family':original,'diagnosed_unknown_component_ids':component_ids,'diagnosis_counts':dict(counts),'limits':['Coordinated family contacts are not newly measured component adjacency.','Original family pointset references belong to the frozen predecessor object namespace.']}
    if canon(stored)!=canon(expected):raise ValueError('Complete family/member/context/original diagnostic changed')


def verify(run):
    report=json.loads((run/'report.json').read_bytes())
    if report['input_commit']!=custody.INPUT_COMMIT or report['original_complete_report_sha256']!='13cd9b18fae16f1ce0a2197fcb832ca6da595168bb58a23b1f85c8998590a6c7':raise ValueError('Changed immutable predecessor vintage')
    inputs,scope,families,features,members=load_original_inputs()
    oldreport,oldobjects,oldfamilies,oldrows,familyrefs,rowrefs,rosters=load_complete_scientific_inputs(inputs,families)
    check_rosters(report['scope_rosters'])
    if canon(report['scope_rosters'])!=canon(rosters) or canon(report['actual_consumed_ordinary_inputs'])!=canon(inputs.pins):raise ValueError('Complete input or scope closure differs')
    objects=read_objects(run,read_pin(run,report['object_index']))
    rows={};counts=collections.Counter();reasons=collections.Counter();coverage=collections.Counter();perfamily=collections.defaultdict(collections.Counter)
    def operand(p):
        r=p['geometry_reference']
        if r['object_index']!='objects.json' or r['canonical_geometry_sha256']not in oldobjects:raise ValueError('Missing frozen operand')
        return oldobjects[r['canonical_geometry_sha256']]
    for pin in report['component_outputs']:
        values=read_pin(run,pin)
        if len(values)!=pin['records']:raise ValueError('Component shard count differs')
        for row in values:
            i=row['component']
            if i in rows or i not in rosters['unknown_components']:raise ValueError('Omitted/duplicated/outside diagnostic component')
            original=oldrows[i];fid=original['family'];family=oldfamilies[fid]
            expected=numeric_kernel.diagnose(features[i]['geometry'],operand(family['literal_member_union']['union']),operand(original['intersection']),operand(original['difference']))
            validate_row(row,expected,objects,original,family,rowrefs[i],familyrefs[fid])
            rows[i]=row;counts[row['status']]+=1;reasons[row.get('observed_reason','unknown-operation')]+=1;coverage[row['coverage_observation']['status']]+=1;perfamily[fid][row['status']]+=1
            if len(rows)%1000==0:print('independently replayed',len(rows),flush=True)
    validate_complete_counts(rows,rosters['unknown_components'],counts,reasons,coverage,report)
    seen=set()
    for pin in report['family_outputs']:
        values=read_pin(run,pin)
        if len(values)!=pin['records']:raise ValueError('Family shard count differs')
        for f in values:
            fid=f['original_complete_family']['family']['id']
            if fid in seen or fid not in rosters['families']:raise ValueError('Missing/duplicate/outside family')
            validate_family(f,oldfamilies[fid],familyrefs[fid],sorted(i for i in rows if rows[i]['family']==fid),perfamily[fid])
            seen.add(fid)
    if sorted(seen)!=rosters['families']:raise ValueError('Incomplete full family roster')
    inputs.close()
    files=sorted((str(p.relative_to(run)),SHA(p.read_bytes()))for p in run.rglob('*')if p.is_file())
    return {'status':'passed-complete-diagnostic-replay-and-archived-unknown-preservation','components':len(rows),'families':len(seen),'counts':dict(counts),'coverage':dict(coverage),'scientific_files':files,'scientific_product_sha256':SHA(canon(files)),'limits':['Complete verifier replay is not a third counted producer run or physical/source authority approval.']}

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--run',required=True);a.add_argument('--output',required=True);x=a.parse_args();v=verify(pathlib.Path(x.run));pathlib.Path(x.output).write_bytes(canon(v));print(json.dumps({k:v[k]for k in ['status','components','families','scientific_product_sha256']}))
