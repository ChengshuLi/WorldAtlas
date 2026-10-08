#!/usr/bin/env python3
"""Additive authenticated transfer of retained MLIT angular intersection areas.

This reuses complete pinned reports; it does not rerun or authenticate the native
MLIT archive. Output is a new evidence vintage and confers no geographic approval.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import types

BASELINE = 'd2e4261462ee1d322cec61c29595d78c6f1b2a8e'
OLD = 'research/geography/japan-nine-gap-family-source-fitness-20261007/'
OWNED = 'research/geography/japan-report-integrity-1342-20261008/'
ROSTER_SHA256 = '033b6229751721a876f318482081b75121504535f5e61743c69de65ec73c02a2'
ROSTER_COUNT = 75
ROSTER_BYTES = 22072824
SUBJECTS = [
'gb:JPN:ADM2:22064153B10464594987148','gb:JPN:ADM2:22064153B14063031562338','gb:JPN:ADM2:22064153B18374709515284','gb:JPN:ADM2:22064153B20086130003796','gb:JPN:ADM2:22064153B28818453738247','gb:JPN:ADM2:22064153B51662529993673','gb:JPN:ADM2:22064153B52868042497281','gb:JPN:ADM2:22064153B53045263163046','gb:JPN:ADM2:22064153B54573279257236','gb:JPN:ADM2:22064153B55014741833430','gb:JPN:ADM2:22064153B5531323380958','gb:JPN:ADM2:22064153B55931345507884','gb:JPN:ADM2:22064153B56242014914717','gb:JPN:ADM2:22064153B64476610605868','gb:JPN:ADM2:22064153B72338395356904','gb:JPN:ADM2:22064153B75016173897449','gb:JPN:ADM2:22064153B75857834624428','gb:JPN:ADM2:22064153B88065808639443','gb:JPN:ADM2:22064153B92731111025148','gb:JPN:ADM2:22064153B92910812775945','gb:JPN:ADM2:22064153B98075236396986']
FIXED = {
 OLD+'inputs/existing-physical-row-scope.json':'70c424d2ccd38442dceb4f585da08cc6bb4dd8e88d8af5bb849fc192120a6518',
 OLD+'inputs/immutable-scope-and-inputs.json':'61069cc6d7727238c552c4f25de9cfa1e7fec7608dc74bcb84605de1620e6414',
 OLD+'inputs/runtime-freeze.json':'547fb73c9e70b2033ad810d88a8a4125c14a88f33718684ff36421d4550f04b1',
 OLD+'methods/build_source_fitness_table.py':'1c867bd02cc1e42207ac0a7cddaf7b320be1b8eda292b7e4f61189c5a3c2535a',
 OLD+'results/source-fitness-table.json':'72ce7765076eb94f195de4e3f80cd521528c12e14c63ffc92c040e4ab2d5484d',
 OLD+'results/source-overlays.json':'2c326ee027c6b4f5ea196e39daca657b493a51f9cf7834bee46a4ca7a9973804',
 'data/world-index.json':'a62d4a74f0f969e228dfcdeb2797bb689ce9836c2498cadd31ed622ad2c38c03',
 'data/geography/part-11.json':'d1b2fb15c9427497de740eb33a529ef382b58cb319028f2aa38f5878de4c9b02',
 'data/geography/part-12.json':'24b44617b0164913f598c94c2c1b36e1a2321f0456644cc20e7f2856955b03f7',
 'data/hierarchy.json':'568301690ef231a85856666b57876a5efe8d8c7c6e671a56d81307b2dc28b80b',
 'scripts/evidence/immutable.py':'a3667cecd88b2862e61a3ce72778e179535d92fbf19b5cd7c5b112722926da46',
}

def canon(x): return (json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n').encode()
def sha(b): return hashlib.sha256(b).hexdigest()
def git(repo,*args): return subprocess.check_output(['git','-C',str(repo),*args],stderr=subprocess.PIPE)
def pin_inventory(repo):
    paths=git(repo,'ls-tree','-r','--name-only',BASELINE,OLD).decode().splitlines()
    rows=[]
    for p in paths:
        raw=git(repo,'show',BASELINE+':'+p)
        rows.append({'path':p,'bytes':len(raw),'sha256':sha(raw),'hash_kind':'file-bytes'})
    if len(rows)!=ROSTER_COUNT or sum(x['bytes'] for x in rows)!=ROSTER_BYTES or sha(canon(rows))!=ROSTER_SHA256:
        raise ValueError('Original 75-file packet roster differs from issue-time pin')
    return rows

def make_baseline(repo):
    helper='scripts/evidence/immutable.py'
    trusted=git(repo,'show',BASELINE+':'+helper)
    if sha(trusted)!=FIXED[helper]: raise ValueError('Immutable helper commit pin mismatch')
    # Execute the exact reviewed Git blob instead of importing a mutable checkout copy.
    immutable=types.ModuleType('immutable')
    immutable.__file__=str(Path(repo)/helper)
    exec(compile(trusted,immutable.__file__,'exec'),immutable.__dict__)
    rows=pin_inventory(repo)
    by={x['path']:x for x in rows}
    for path,digest in FIXED.items():
        if path in by and by[path]['sha256']!=digest: raise ValueError('Fixed packet pin conflict: '+path)
        if path not in by:
            raw=git(repo,'show',BASELINE+':'+path)
            by[path]={'path':path,'bytes':len(raw),'sha256':sha(raw),'hash_kind':'file-bytes'}
        if by[path]['sha256']!=digest: raise ValueError('Pinned baseline hash mismatch: '+path)
    # Include every complete indexed part plus current hierarchy for target and parent checks.
    idx=json.loads(git(repo,'show',BASELINE+':data/world-index.json'))
    for part in idx['parts']:
        path='data/'+part
        if path not in by:
            raw=git(repo,'show',BASELINE+':'+path);by[path]={'path':path,'bytes':len(raw),'sha256':sha(raw),'hash_kind':'file-bytes'}
    return immutable, immutable.Baseline(repo,BASELINE,list(by.values()))

def load(base,path):
    return json.loads(base.materialized_bytes(path))

def validate(scope,physical,overlay,old_table,subjects,hierarchy):
    comps=scope['components']; fams=scope['families']; contacts=scope['contacts']
    if (len(comps),len(fams),len(contacts))!=(28,9,21) or len(set(comps))!=28 or len(set(fams))!=9 or len(set(contacts))!=21:
        raise ValueError('Immutable scope roster is incomplete or duplicated')
    targets=overlay['targets']
    if len(targets)!=49 or len({x.get('id') for x in targets})!=49: raise ValueError('Overlay target roster is not exactly 49 unique IDs')
    targetmap={x['id']:x for x in targets}
    if {x['id'] for x in targets if x.get('kind')=='component'}!=set(comps) or {x['id'] for x in targets if x.get('kind')=='contact'}!=set(contacts):
        raise ValueError('Foreign, missing or wrong-kind overlay target')
    def geom_digest(feature): return sha(canon(feature['geometry']))
    actual_geometries={identity:geom_digest(feature) for identity,feature in subjects.items()}
    candidates=scope.get('full_candidate_features',[])
    if len(candidates)!=28 or {x.get('id') for x in candidates}!=set(comps): raise ValueError('Immutable candidate geometry roster differs')
    actual_geometries.update({x['id']:geom_digest(x) for x in candidates})
    if set(actual_geometries)!=set(comps)|set(contacts): raise ValueError('Immutable geometry identities differ from target scope')
    if any(targetmap[k].get('geometry_sha256')!=v for k,v in actual_geometries.items()): raise ValueError('Overlay target geometry differs from immutable scope/current Atlas')
    route={x['component']:x for x in scope['routing_rows']}
    if set(route)!=set(comps) or len(route)!=28: raise ValueError('Routing component identities differ')
    if any(route[k].get('current_geometry_sha256')!=actual_geometries[k] for k in comps): raise ValueError('Candidate routed/current geometry binding differs')
    phys={x['component_id']:x for x in physical['selected_whole_rows']}
    if set(phys)!=set(comps) or len(phys)!=28: raise ValueError('Physical source roster differs')
    famrows={x['id']:x for x in scope['families_full_records']}
    if set(famrows)!=set(fams) or len(famrows)!=9: raise ValueError('Complete family roster differs')
    membership=[]
    for fid,f in famrows.items():
        ids=f.get('complete_component_ids')
        if not isinstance(ids,list) or len(ids)!=f.get('component_count') or len(ids)!=len(set(ids)) or not set(ids)<=set(comps): raise ValueError('Invalid complete family membership')
        membership += ids
    if sorted(membership)!=sorted(comps): raise ValueError('Families do not partition all 28 components')
    h={x['id']:x for x in hierarchy}
    for identity in contacts:
        feature=subjects[identity]
        if feature.get('id')!=identity or feature.get('properties',{}).get('id')!=identity: raise ValueError('Atlas contact ID binding mismatch')
        metadata=feature['properties'].get('metadata',{})
        if metadata.get('source_id')!='gb:JPN:ADM2' or str(metadata.get('reference_year'))!='2017' or metadata.get('source_role')!='Municipality / city ward': raise ValueError('Contact source identity/vintage/granularity mismatch')
        parent=feature['properties'].get('parent_id')
        if parent not in h or h[parent].get('level')!='province': raise ValueError('Contact prefecture-level parent unresolved')
        if targetmap[identity]['geometry_sha256']!=next(x for x in old_table['contact_rows'] if x.get('contact_id')==identity).get('current_whole_geometry_sha256'):
            raise ValueError('Contact geometry differs between immutable target roster and table')
    pairs=overlay['pairwise_exact_overlays']
    if len(pairs)!=5731: raise ValueError('Complete pair roster count differs')
    keys=[]
    for r in pairs:
        k=(r.get('source_product'),r.get('source_id'),r.get('source_geometry_sha256'),r.get('target_id'))
        if any(not isinstance(x,str) or not x for x in k) or k in keys: raise ValueError('Duplicate/incomplete overlay source-pair identity')
        keys.append(k)
        if r['target_id'] not in targetmap: raise ValueError('Foreign overlay pair target')
        if r.get('target_geometry_sha256')!=targetmap[r['target_id']]['geometry_sha256']: raise ValueError('Pair target geometry hash differs from roster')
    summaries={x.get('source_product'):x for x in overlay.get('source_summaries',[])}
    if len(summaries)!=3 or set(summaries)!={'geoboundaries-full','geoboundaries-atlas-simplified','mlit-n03-2017'}: raise ValueError('Complete source summary roster differs')
    ms=summaries['mlit-n03-2017']
    if ms.get('source_shape_records')!=116024 or ms.get('source_dbf_records')!=116024 or ms.get('bbox_selected_native_rows')!=5174 or ms.get('bbox_skipped_native_rows')!=110850 or ms.get('spatial_intersection_candidates')!=5425 or ms.get('target_count')!=49 or ms.get('complete_archive_bytes')!=242211059 or ms.get('complete_archive_sha256')!='a649b4099c1b0df80a6fb9ed087b594ed75ae9a92e9511cecdb6463d1480c6fb' or ms.get('crs')!='EPSG:6668 JGD2011 geographic' or overlay.get('source_summaries') is None: raise ValueError('MLIT retained native-source summary contradiction')
    transform=summaries['mlit-n03-2017'].get('transform')
    if not isinstance(transform,dict) or transform.get('source')!='EPSG:4326' or transform.get('target')!='EPSG:6668' or transform.get('always_xy') is not True: raise ValueError('Retained MLIT coordinate-operation summary differs')
    for product in ('geoboundaries-full','geoboundaries-atlas-simplified'):
        gs=summaries[product]
        if gs.get('source_features')!=1742 or gs.get('target_count')!=49 or gs.get('spatial_intersection_candidates')!=153 or len(gs.get('per_target_exact_intersections',[]))!=49: raise ValueError('Retained complete geoBoundaries summary contradiction')
    product_counts={p:sum(r.get('source_product')==p for r in pairs) for p in ('geoboundaries-full','geoboundaries-atlas-simplified','mlit-n03-2017')}
    if product_counts!={'geoboundaries-full':153,'geoboundaries-atlas-simplified':153,'mlit-n03-2017':5425}: raise ValueError('Complete source-pair counts disagree with retained summaries')
    for product in ('geoboundaries-full','geoboundaries-atlas-simplified'):
        summary=summaries[product]; rows=[r for r in pairs if r.get('source_product')==product]
        roster=summary.get('per_target_exact_intersections',[])
        if len(roster)!=49 or len({x.get('target_id') for x in roster})!=49 or {x.get('target_id') for x in roster}!=set(targetmap): raise ValueError('Per-target summary roster differs')
        for entry in roster:
            target_rows=[r for r in rows if r.get('target_id')==entry['target_id']]
            if len(target_rows)!=entry.get('bbox_candidate_count') or sum(r.get('intersects') is True for r in target_rows)!=entry.get('exact_intersection_count'):
                raise ValueError('Per-target exact-intersection summary contradiction')
    mlit=[r for r in pairs if r.get('source_product')=='mlit-n03-2017' and r.get('intersects') is True]
    candidates=[r for r in mlit if r['target_id'] in comps]
    contacts_intersections=[r for r in mlit if r['target_id'] in contacts]
    if len(candidates)!=37 or len(contacts_intersections)!=917 or len(mlit)!=954: raise ValueError('MLIT retained exact intersection counts disagree')
    for row in candidates:
        area=row.get('intersection_area_jgd2011_degrees2')
        if isinstance(area,bool) or not isinstance(area,(int,float)) or not math.isfinite(area) or area<=0: raise ValueError('MLIT area missing, nonfinite or nonpositive')
        sr=row['source_record']
        if sr.get('record_number')!=sr.get('record_ordinal',-2)+1 or not isinstance(sr.get('N03_001'),str) or not isinstance(sr.get('N03_004'),str) or not isinstance(r.get('source_id'),str) or len(r['source_id'])!=5: raise ValueError('MLIT row identity incomplete')
    comps_table=old_table['component_rows']
    if len(comps_table)!=28 or {x.get('component_id') for x in comps_table}!=set(comps): raise ValueError('Old table component identities differ')
    if len(old_table['contact_rows'])!=21 or {x.get('contact_id') for x in old_table['contact_rows']}!=set(contacts): raise ValueError('Old table contact identities differ')
    expected={(r['target_id'],r['source_record']['record_ordinal'],r['source_id'],r['intersection_geometry_sha256']):r for r in candidates}
    transferred=[]
    for component in comps_table:
        recs=component.get('MLIT_exact_intersection_records')
        local=[(k,v) for k,v in expected.items() if k[0]==component['component_id']]
        if len(recs)!=len(local): raise ValueError('Table MLIT row count differs by target')
        replacements=[]
        for rec in recs:
            k=(component['component_id'],rec.get('record_ordinal'),rec.get('N03_007'),rec.get('intersection_geometry_sha256'))
            source=expected.get(k)
            if rec.get('intersection_area_jgd2011_degrees2') is not None: raise ValueError('Original retained table differs from issue-confirmed null loss')
            if source is None: raise ValueError('Table MLIT source/pair identity does not bind')
            if rec.get('N03_007')!=source['source_id']: raise ValueError('Table N03 code differs from retained source identity')
            for field in ('N03_001','N03_002','N03_003','N03_004','record_number','record_ordinal','intersection_geometry_sha256'):
                if rec.get(field)!=source['source_record'].get(field,source.get(field) if field=='intersection_geometry_sha256' else None): raise ValueError('Table/source MLIT field mismatch: '+field)
            replacements.append({**rec,'intersection_area_jgd2011_degrees2':source['intersection_area_jgd2011_degrees2']})
            transferred.append((k,source['intersection_area_jgd2011_degrees2']))
        component['MLIT_exact_intersection_records']=replacements
    if len(transferred)!=37 or len({k for k,_ in transferred})!=37: raise ValueError('MLIT transfer not a complete unique 37-row join')
    return transferred

def report_context(scope,subjects,hierarchy,overlay):
    h={x['id']:x for x in hierarchy}
    targets={x['id']:x for x in overlay['targets']}
    rows=[]
    for identity in SUBJECTS:
        f=subjects[identity]; p=f['properties']; parent=h[p['parent_id']]
        rows.append({'id':identity,'name':p.get('name'),'source':'geoBoundaries JPN ADM2','reference_year':str(p.get('metadata',{}).get('reference_year')),'source_vintage':'2017','atlas_geometry_sha256':targets[identity]['geometry_sha256'],'recorded_parent_id':p['parent_id'],'recorded_parent_name':parent.get('name'),'recorded_parent_level':parent.get('level'),'granularity':'municipality / city ward (source packet role); not a direct prefecture polygon','semantic_parentage':'retained hierarchy assertion only; hierarchy review remains open'})
    return {'schema':'worldatlas-japan-report-integrity-context-v1','scope_counts':{'components':28,'families':9,'current_contacts':21},'contacts':rows,'source_context':{'product':'MLIT N03 v2.3 / 2017-01-01 reference vintage','native_crs':'EPSG:6668 JGD2011 geographic coordinates','area_field':'intersection_area_jgd2011_degrees2','area_unit':'square degrees; angular, not square metres','source_record_count_retained':116024,'bbox_selected_rows_retained':5174,'exact_pair_candidates_retained':5425,'component_exact_intersections_retained':37,'contact_exact_intersections_retained':917,'native_archive_sha256':'a649b4099c1b0df80a6fb9ed087b594ed75ae9a92e9511cecdb6463d1480c6fb'},'limits':['Values are authenticated as complete retained report rows, not remeasured or validated against the oversized native MLIT archive.','No full MLIT/world rerun was performed.','Administrative overlap does not classify physical geography or establish cause, ownership, correction or approval.','GSHHG source custody and current physical/legal/date applicability remain unresolved.','Original source packet remains immutable; no historical import or publication authorization.']}

def execute(repo,vintage,fail=False):
    immutable,base=make_baseline(repo)
    # Reserve the complete fresh destination before reading/computing the report.
    # publish() rechecks the same full set immediately before its first write.
    files=['source-fitness-table.json','territorial-context.json','validation.json']
    run=immutable.NewVintage(base,OWNED,vintage,files)
    def material(p): return load(base,p)
    scope=material(OLD+'inputs/immutable-scope-and-inputs.json')
    physical=material(OLD+'inputs/existing-physical-row-scope.json')
    overlay=material(OLD+'results/source-overlays.json')
    table=material(OLD+'results/source-fitness-table.json')
    # Capture per-file bytes before editing in memory. Validate all complete subject IDs in indexed world inventory.
    subjects,_=base.subjects(SUBJECTS)
    hierarchy=json.loads(base.pinned_bytes('data/hierarchy.json'))
    copied=json.loads(json.dumps(table))
    transferred=validate(scope,physical,overlay,copied,subjects,hierarchy)
    context=report_context(scope,subjects,hierarchy,overlay)
    if fail: raise RuntimeError('intentional late failure before publication')
    manifest={'schema':'worldatlas-mlit-report-integrity-v1','baseline_commit':BASELINE,'original_packet_roster':{'files':ROSTER_COUNT,'encoded_bytes':ROSTER_BYTES,'canonical_descriptor_sha256':ROSTER_SHA256},'scope':{'components':28,'families':9,'contacts':21},'transfer':{'rows':len(transferred),'area_field':'intersection_area_jgd2011_degrees2','unit':'square degrees (JGD2011 geographic/angular)','min':min(v for _,v in transferred),'max':max(v for _,v in transferred)},'source_overlay_sha256':FIXED[OLD+'results/source-overlays.json'],'report_method_sha256':sha(Path(__file__).read_bytes()),'report_method_path':'research/geography/japan-report-integrity-1342-20261008/methods/reconcile_source_fitness_table.py','old_table_sha256':FIXED[OLD+'results/source-fitness-table.json'],'limitations':context['limits']}
    run.publish({'source-fitness-table.json':copied,'territorial-context.json':context,'validation.json':manifest})
    return manifest

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo',default=str(Path(__file__).resolve().parents[4]));ap.add_argument('--vintage',required=True);ap.add_argument('--fail-after-compute',action='store_true');a=ap.parse_args()
    result=execute(a.repo,a.vintage,a.fail_after_compute);print(json.dumps({'status':'complete','vintage':a.vintage,'rows':result['transfer']['rows']},sort_keys=True))
if __name__=='__main__': main()
