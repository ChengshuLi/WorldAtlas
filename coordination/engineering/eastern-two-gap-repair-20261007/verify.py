"""Whole-input and complete proposal replay; retains exact consumer representation."""
from pathlib import Path
import argparse,json,gzip,sys
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'scripts'))
from reader import load,checked_file,digest
from kernel import TARGETS,exact_addition
from evidence.immutable import canonical_json
from evidence.geometry import canonical_prepared_land
from shapely.geometry import shape,mapping
from shapely import union_all
from producer import footprint_hash,EXPECTED_G,authenticate_code

def verify(root):
    data=load(Path(__file__).parent,ROOT);world=data['world'];report=json.loads(checked_file(root,'report.json'));outputs={}
    for pin in report['outputs']:
        raw=checked_file(root,pin['path']);decoded=gzip.decompress(raw)if pin['path'].endswith('.gz')else raw
        if len(raw)!=pin['bytes']or digest(raw)!=pin['sha256']or len(decoded)!=pin['decoded_bytes']or digest(decoded)!=pin['decoded_sha256']:raise ValueError('Complete output whole bytes failed')
        outputs[pin['path']]=json.loads(decoded)
    corrections=outputs['corrections.json.gz'];by_id={x['subject_id']:x for x in corrections}
    if len(corrections)!=2 or set(by_id)!=set(TARGETS):raise ValueError('Complete exact correction subject scope')
    after=dict(world)
    for identity,cid in TARGETS.items():
        row=by_id[identity];eco=world[identity]['properties']['metadata']['ecoregion_id'];records=[f for f in data['native']if f['properties']['ECOREGION_ID']==eco]
        if len(records)!=1:raise ValueError('Exact admitted native assignment')
        cohort=[world[s]for s in data['receipt']['world']['fixedpoint_current_subject_ids']if s.endswith(':'+identity.rsplit(':',1)[1])];mids={m for f in cohort for m in f['properties']['metadata']['source_member_ids']};parents=[f for f in data['retired']if f['id']in mids]
        native=shape(records[0]['geometry']);old=shape(world[identity]['geometry']);gap=shape(data['components'][cid]['geometry']);envelope=union_all([shape(f['geometry'])for f in parents]);new,proof=exact_addition(identity,cid,old,gap,native,envelope)
        if canonical_json(row['pointsets'])!=canonical_json(proof)or row['component_id']!=cid or row['component_geometry_sha256']!=EXPECTED_G[identity]or row['cohort_current_ids']!=sorted(f['id']for f in cohort)or row['cohort_retired_ids']!=sorted(mids):raise ValueError('Full exact source/gain/loss/cohort proof changed')
        after[identity]={**world[identity],'geometry':mapping(new)}
    part=outputs['proposed-part-29.json.gz'];old_part=data['inputs'].json('data/geography/part-29.json')
    expected={**old_part,'features':[after[f['id']]for f in old_part['features']]}
    if part!=expected or len(part['features'])!=len(old_part['features']):raise ValueError('Full proposed containing part changed')
    for stored,frozen in zip(part['features'],expected['features']):
        if list(stored['geometry'])!=list(frozen['geometry']):raise ValueError('Consumer geometry key representation changed')
    actual_serialized_world={**world,**{f['id']:f for f in part['features']}}
    crosswalk=outputs['crosswalk.json.gz']
    if crosswalk['changed_ids']!=sorted(TARGETS)or crosswalk['removed_ids']or crosswalk['added_ids']or crosswalk['reused_ids']!=sorted(set(world)-set(TARGETS)):raise ValueError('Full identity disposition changed')
    archives=crosswalk['archives']
    if len(archives)!=2 or {x['id']for x in archives}!=set(TARGETS):raise ValueError('Whole archived original scope')
    for row in archives:
        if row['feature']!=world[row['id']]or list(row['feature']['geometry'])!=list(world[row['id']]['geometry']):raise ValueError('Original source/consumer archive representation')
    before_hash,after_hash=footprint_hash(world),footprint_hash(actual_serialized_world)
    reconstructed_before={**actual_serialized_world,**{row['id']:row['feature']for row in archives}}
    if footprint_hash(reconstructed_before)!=before_hash or footprint_hash(after)!=after_hash:raise ValueError('Actual serialized part/archived originals fail legacy full-world consumer reconstruction')
    if crosswalk['before_footprints_sha256']!=before_hash or crosswalk['after_footprints_sha256']!=after_hash or report['before_footprints_sha256']!=before_hash or report['after_footprints_sha256']!=after_hash:raise ValueError('Whole legacy consumer footprint binding changed')
    scope=outputs['full-source-scope.json.gz'];ids=data['receipt']['world']['fixedpoint_current_subject_ids']
    if scope!={'current':[world[s]for s in ids],'retired':data['retired'],'native':data['native_scope']}:raise ValueError('Whole source/member/current record scope changed')
    four=outputs['full-four-family-context.json.gz']
    expected={'families':data['families'],'components':[data['components'][c]for c in sorted(data['components'])],'physics':[data['physics'][c]for c in sorted(data['physics'])],'dispositions':[{'component_id':c,'status':'proposed-whole-addition'if c in TARGETS.values()else'unchanged-unresolved'}for c in sorted(data['components'])]}
    if four!=expected:raise ValueError('Complete four-family/source/unknown context changed')
    neighborhoods=outputs['neighbors.json.gz']
    if {r['subject_id']for r in neighborhoods}!=set(TARGETS)or len(neighborhoods)!=2:raise ValueError('Whole neighbor subjects')
    for r in neighborhoods:
        sid=r['subject_id'];relations=r['complete_relations']
        if len(relations)!=6 or len({r['id']for r in relations})!=6:raise ValueError('Whole six-neighbor scope')
        old=canonical_prepared_land(shape(world[sid]['geometry']));new=canonical_prepared_land(shape(after[sid]['geometry']))
        for relation in relations:
            other=canonical_prepared_land(shape(world[relation['id']]['geometry']));before=old.intersection(other);now=new.intersection(other);added=now.difference(before)
            if canonical_json(relation)!=canonical_json({'id':relation['id'],'before':mapping(before),'after':mapping(now),'added':mapping(added),'added_area':added.area}):raise ValueError('Full before/after neighbor pointsets')
            if added.area>0:raise ValueError('New neighbor positive overlap')
    contexts=outputs['complete-regional-contact-context.json.gz']
    for suffix,counts in [('QUE',(55,434)),('NFL',(37,610))]:
        cohort={s for s in ids if s.endswith(':'+suffix)};families=[f for f in data['all_families']if cohort.intersection(f['contact_ids'])];cids=sorted({c for f in families for c in f['component_ids']})
        if (len(families),len(cids))!=counts or contexts[suffix]!={'complete_families':families,'complete_component_ids':cids}:raise ValueError('Complete cross-family context changed')
    regression=outputs['whole-world-geographic-regression.json.gz']
    if regression['status']!='no-new-regression'or regression['regressions']!=0 or regression['changed_location_ids']!=sorted(TARGETS)or regression['findings']['features']:raise ValueError('Actual whole-world regression disposition changed')
    validation=outputs['whole-world-prepared-validation.json.gz']
    bindings=[]
    for identity,feature in sorted(world.items()):
        geometry=canonical_prepared_land(shape(feature['geometry']));bindings.append([identity,digest(canonical_json(mapping(geometry)))])
    if validation['feature_count']!=49625 or validation['errors']or validation['feature_geometry_sha256']!=digest(canonical_json(bindings)):raise ValueError('Complete prepared-world source geometry binding')
    if report['current_pointers_activated']is not False:raise ValueError('Proposal must not activate current pointers')
    return {'passed':True,'world':49625,'corrected':2,'families':4,'components':64,'original_source_regions':24,'original_source_records':29,'retired':477,'neighbors':12,'regression_scope':'complete source/prepared bindings and original full regression retained; this verifier does not independently recompute global pair search','before_footprints_sha256':before_hash,'after_footprints_sha256':after_hash}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',required=True,type=Path);p.add_argument('--commit',required=True);a=p.parse_args();code=authenticate_code(a.commit);result=verify(a.run);assert code==authenticate_code(a.commit);print(json.dumps({**result,'verifier_execution_commit':a.commit,'executed_project_modules':code},sort_keys=True))
