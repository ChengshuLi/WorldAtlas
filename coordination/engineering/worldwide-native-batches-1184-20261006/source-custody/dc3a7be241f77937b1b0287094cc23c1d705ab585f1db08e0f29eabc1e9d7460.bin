"""Actual selected-source native cohort using the accepted complete successor.

The whole frozen cohort is authenticated before lossless current overlays. The
two existing successor reader functions execute from their ordinary pinned Git
source, independent of another worker's checkout or local imports.
"""
import argparse
import ast
from collections import Counter,defaultdict
import copy
import gzip
import importlib.util
import json
import pathlib
import platform
import subprocess
import numpy as np
import shapely
from evidence.immutable import canonical_json,sha256
from physical_component_contacts import component_contacts
from physical_gap_priority import investigation_record,investigation_ranks,attach_rank_positions,related_issue_scopes,issue_subject_index
from worldwide_native_observations import component_probe,observe_probes,full_owner_counts
from worldwide_gap_source_context import issue_rosters
from worldwide_gap_operational_batches import operational_batches,dispatch_candidates

ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('worldwide_frozen_producer',ROOT/'scripts/build-worldwide-native-batches.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
S='7c7cdf2388e0e7200b937c2cfb440b53165d9d98'
SP='coordination/engineering/worldwide-successor-1215-20261006/run-one/'

def successor_readers(inputs):
    path='scripts/worldwide_gap_successor.py';source=inputs.read(S,path)
    tree=ast.parse(source.decode(),filename=S+':'+path)
    functions=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('record_delta','reconstruct')]
    if {f.name for f in functions}!={'record_delta','reconstruct'} or len(functions)!=2:
        raise ValueError('Exact existing successor reader definition closure missing')
    namespace={'canonical_json':canonical_json,'digest':sha256}
    exec(compile(ast.Module(body=functions,type_ignores=[]),S+':'+path,'exec'),namespace)
    extraction={'commit':S,'path':path,'whole_file_sha256':sha256(source),
        'functions':{f.name:sha256(ast.get_source_segment(source.decode(),f).encode())for f in functions},
        'scope':'Exact original function definitions only; no modified reader or module side effects.'}
    return namespace['record_delta'],namespace['reconstruct'],extraction

def rows(inputs,commit,pins):
    result=[]
    for pin in pins:
        result.extend(inputs.json(commit,pin['path'],pin))
    return result

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--frozen-commit',required=True)
    parser.add_argument('--frozen-report',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args();out=ROOT/args.output
    if not args.output.startswith(base.OWNED)or out.exists():raise ValueError('Fresh owned current output required')
    out.mkdir(parents=True);inputs=base.Inputs()
    software={'python':platform.python_version(),'numpy':np.__version__,'shapely':shapely.__version__,'geos':shapely.geos_version_string}
    base.verify_runtime(software)
    execution=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip()
    executed=base.authenticate_executed_code(inputs,execution)
    delta,reconstruct,reader_binding=successor_readers(inputs)
    frozen=inputs.json(args.frozen_commit,args.frozen_report)
    if frozen['component_count']!=95174 or frozen['context_count']!=49625:raise ValueError('Complete frozen native prerequisites missing')
    successor=inputs.json(S,SP+'report.json')
    if successor['selected_input_commit']!=base.M or successor['frozen_selected_commit']!=base.C:
        raise ValueError('Current source vintage differs')
    products={p['path']:p for p in successor['products']}
    def product(name):return inputs.json(S,SP+name,products[name])
    inventory=inputs.json(base.M,base.IP+'report.json')
    def original_family(name):
        result=[]
        for pin in inventory['complete_products'][name]:
            path=next(p['path']for p in inventory['source_descriptors']if p['sha256']==pin['sha256'])
            value=inputs.json(base.M,path,pin)
            if value.get('type')!='FeatureCollection':raise ValueError('Original scientific FeatureCollection wrapper missing')
            result.extend(value['features'])
        return result
    old_components=original_family('components');component_delta=product('components-delta.json.gz')
    current_components=reconstruct(old_components,component_delta)
    if len(current_components)!=95173 or len(current_components)!=successor['current_counts']['components']:
        raise ValueError('Complete current component roster differs')
    original_lineage=[]
    for name in sorted(products):
        if name.startswith('component-lineage-original-'):original_lineage.extend(product(name))
    current_lineage=reconstruct(original_lineage,product('component-lineage-current-delta.json.gz'))
    if {r['id']for r in original_lineage}!={c['id']for c in old_components}or{r['id']for r in current_lineage}!={c['id']for c in current_components}:
        raise ValueError('Complete original/current identity lineage closure differs')
    for features,lineage in ((old_components,original_lineage),(current_components,current_lineage)):
        by_id={f['id']:f for f in features}
        for row in lineage:
            feature=by_id[row['id']]
            if (row['full_feature_sha256']!=sha256(canonical_json(feature))
                    or row['fragment_ids']!=sorted(b['id']for b in feature['properties']['fragment_bindings'])
                    or row['unmeasured_fragment_ids']!=feature['properties']['unmeasured_fragment_ids']):
                raise ValueError('Complete lineage feature/fragment/unknown binding differs')
    product('fragment-lineage.json.gz');product('tile-queries.json.gz');product('source-custody.json')
    context_report=inputs.json(base.H,base.CP+'report.json')
    contexts={c['id']:c for c in rows(inputs,base.H,context_report['outputs'])}
    source_proofs=[]
    for name in sorted(products):
        if name.startswith('source-feature-bindings-'):source_proofs.extend(product(name))
    if len(source_proofs)!=49625 or {p['id']for p in source_proofs}!=set(contexts):
        raise ValueError('Complete current source/context proof closure differs')
    current_contexts=copy.deepcopy(contexts)
    for proof in source_proofs:
        context=contexts[proof['id']];selected=context.get('selected_successor_context')
        expected=selected['feature_sha256']if selected else context['original_feature_sha256']
        metadata=selected['metadata']if selected else context['original_metadata']
        # Successor *_metadata_sha256 covers the WHOLE feature without geometry,
        # while context metadata is only properties.metadata. Their digests have
        # different domains. Authenticate both whole feature vintages against
        # accepted context-stage raw-source bindings rather than equating them.
        if proof['current_feature_sha256']!=expected or proof['original_feature_sha256']!=context['original_feature_sha256']:
            raise ValueError('Selected/original whole source-feature context binding differs')
        if selected:
            current_contexts[proof['id']].update(original_metadata=metadata,ancestry=selected['ancestry'],original_parent_id=selected['original_parent_id'])
    manifest=inputs.json(base.M,'data/native-ownership/repaired-v7/manifest.json')
    latpin=manifest['native_latitudes'];latencoded=inputs.read(latpin['commit'],latpin['path'],latpin)
    latraw=gzip.decompress(latencoded)
    if sha256(latraw)!=latpin['decoded_sha256']or len(latraw)!=latpin['decoded_bytes']:raise ValueError('Exact stored current latitude input differs')
    latitudes=np.frombuffer(latraw,dtype='<f8');base.verify_native_binding(manifest,context_report,'selected-repository-native',len(latitudes))
    if not np.all(np.isfinite(latitudes))or not np.all(latitudes[1:]<latitudes[:-1]):raise ValueError('Current normative latitude domain differs')
    ordered=sorted((c['frozen_owner_registry']for c in contexts.values()),key=lambda r:r['index'])
    if [r['index']for r in ordered]!=list(range(1,49626)):raise ValueError('Current full ordered owner registry differs')
    owners=[None]+[r['id']for r in ordered];adapted=copy.deepcopy(manifest)
    for pin in adapted['parts']:pin['compressed_bytes']=pin['bytes']
    grid=base.CanonicalGrid(base.GridSource(inputs,base.M,'data/native-ownership/repaired-v7',manifest),adapted,'data/native-ownership/repaired-v7',max_owner_id=49625)
    probes=[component_probe(c,manifest['size'],latitudes)for c in current_components]
    observations,counts=observe_probes(probes,grid,owners);owner_rows,accounting=full_owner_counts(grid,owners)
    print('complete current native observations',len(observations),counts,flush=True)
    original_observations=rows(inputs,args.frozen_commit,frozen['outputs']['frozen-reviewed-native'])
    overlay=rows(inputs,args.frozen_commit,frozen['outputs']['selected-repository-native-complete-overlay'])[0]
    if len(original_observations)!=overlay['component_count']or sha256(canonical_json(sorted(r['component']for r in original_observations)))!=overlay['complete_component_ids_sha256']:
        raise ValueError('Complete comparison overlay input roster differs')
    comparison={r['component']:r for r in original_observations}
    if sha256(canonical_json([comparison[i]for i in sorted(comparison)]))!=overlay['original_rows_sha256']:raise ValueError('Complete original native comparison rows differ')
    for row in overlay['changed_rows']:comparison[row['component']]=row
    if sha256(canonical_json([comparison[i]for i in sorted(comparison)]))!=overlay['current_rows_sha256']:raise ValueError('Complete selected native comparison reconstruction differs')
    native_delta=delta(list(comparison.values()),observations,key=lambda r:r['component'])
    outputs={'selected-current-native-delta':base.write_parts(out,'selected-current-native-delta',[native_delta]),
             'selected-current-owner-counts':base.write_parts(out,'selected-current-owner-counts',owner_rows)}
    del grid,old_components,probes,original_observations
    # Authenticate every complete original investigation and annotation before
    # retaining its unchanged full fields in the selected-source cohort.
    annotations=rows(inputs,args.frozen_commit,frozen['outputs']['complete-investigation-annotations'])
    by_annotation={r['component']:r for r in annotations}
    archive=inputs.json(base.C,base.PP+'report.json');original_records={}
    for pin in archive['outputs']['investigations']:
        for ordinal,row in enumerate(inputs.json(base.C,pin['path'],pin)):
            annotation=by_annotation[row['component']];base.verify_annotation_original(annotation,row,pin,ordinal)
            original_records[row['component']]=row
    if len(original_records)!=95174 or set(original_records)!=set(by_annotation):raise ValueError('Complete original annotation bijection differs')
    issue_pin=frozen['all_state_issue_snapshot'];pages=inputs.json(args.frozen_commit,issue_pin['path'],issue_pin)
    strong,weak,rejected=issue_rosters(pages);subjects=defaultdict(set)
    for roster in strong:subjects[roster['issue']].update(roster['subject_ids'])
    compiled=issue_subject_index(subjects);observed={r['component']:r for r in observations}
    current_ids={c['id']for c in current_components};new_components=[c for c in current_components if c['id']not in original_records]
    needed={b['id']for c in new_components for b in c['properties']['fragment_bindings']}
    fragment_changes=product('fragments-delta.json.gz');needed_features={f['id']:f for f in fragment_changes['upsert_records']if f['id']in needed}
    for pin in inventory['complete_products']['fragments']:
        path=next(p['path']for p in inventory['source_descriptors']if p['sha256']==pin['sha256']);collection=inputs.json(base.M,path,pin)
        if collection.get('type')!='FeatureCollection':raise ValueError('Complete original fragment wrapper missing')
        for fragment in collection['features']:
            if fragment['id']in needed and fragment['id']not in fragment_changes['removed_ids']:needed_features[fragment['id']]=fragment
    if set(needed_features)!=needed:raise ValueError('Incomplete coordinated current fragment/contact closure')
    contacts=component_contacts(list(needed_features.values()),new_components)
    new_records={c['id']:investigation_record(c,contact,needed_features)for c,contact in zip(sorted(new_components,key=lambda c:c['id']),contacts)}
    current_records=[];groups={};triage=Counter()
    for component in sorted(current_components,key=lambda c:c['id']):
        identity=component['id'];record=copy.deepcopy(original_records.get(identity,new_records.get(identity)))
        if not record or record['component']!=identity:raise ValueError('Current investigation omitted or redirected')
        key,families=base.classify(record,observed[identity],current_contexts)
        for family in families:
            family['vintage']=base.M;family['original_recipe_metadata_vintage']=base.C
        key['source_families']=sorted({sha256(canonical_json(f))for f in families})
        bid='gap-source-batch:'+sha256(canonical_json(key))[:24]
        record['investigation_orders']=investigation_ranks(record,current_contexts)
        record['current_native_reference']={'component':identity,'family':'selected-current-native-delta'}
        record['current_actionable_batch_id']=bid;record['current_observed_scope_bucket']=key['observed_scope_bucket']
        links=related_issue_scopes(record['distinct_contact_ids'],record['positive_length_neighbor_ids'],subjects,compiled)
        record['current_related_issue_ids']=[l['issue']for l in links]
        group=groups.setdefault(bid,{'id':bid,'grouping':key,'component_ids':[],'contact_ids':set(),'edge_neighbor_ids':set(),'existing_related_issues':set(),'source_families':{},'best_rank':{}})
        group['component_ids'].append(identity);group['contact_ids'].update(record['distinct_contact_ids']);group['edge_neighbor_ids'].update(record['positive_length_neighbor_ids']);group['existing_related_issues'].update(l['issue']for l in links)
        for family in families:group['source_families'][sha256(canonical_json(family))]=family
        current_records.append(record);triage[key['observed_scope_bucket']]+=1
    attach_rank_positions(current_records);queues=base.semantic_ranks(current_records)
    positions={r['component']:r['rank_positions']for r in current_records}
    batches=[]
    for bid in sorted(groups):
        group=groups[bid];group['component_ids'].sort();group['component_count']=len(group['component_ids']);group['component_ids_sha256']=sha256(canonical_json(group['component_ids']))
        for field in ('contact_ids','edge_neighbor_ids','existing_related_issues'):group[field]=sorted(group[field])
        group['source_families']=[group['source_families'][h]for h in sorted(group['source_families'])]
        group['best_rank']={name:min(positions[c][name]for c in group['component_ids'])for name in base.ORDER_NAMES}
        extents=[observed[c]['original_extent_lonlat']for c in group['component_ids']if observed[c]['original_extent_lonlat']is not None]
        group['original_member_extent_references']={'family':'selected-current-native-delta','field':'original_extent_lonlat','missing_extent_component_ids':[c for c in group['component_ids']if observed[c]['original_extent_lonlat']is None]}
        group['aggregate_extent_lonlat']=None if not extents else [min(e[0]for e in extents),min(e[1]for e in extents),max(e[2]for e in extents),max(e[3]for e in extents)]
        group['responsible_role']='engineering-processing-reproduction'if group['grouping']['work_kind']=='processing-reproduction-and-source-comparison'else'GEO-source-research'
        group['cause_status']='unknown';group['dispatch_status']='complete current triage backlog; canonical scope and live claim required'
        batches.append(group)
    base.validate_batch_membership(batches,current_ids);operational=operational_batches(batches)
    original_batches=rows(inputs,args.frozen_commit,frozen['outputs']['batches'])
    # Full current family content is a validated lossless delta; omitted identical
    # values remain ordinary complete original rows rather than duplicate tables.
    outputs['current-batches']=base.write_parts(out,'current-batches',batches)
    outputs['current-operational-batches']=base.write_parts(out,'current-operational-batches',operational)
    outputs['current-rank-positions']=base.write_parts(out,'current-rank-positions',[{'component':r['component'],'rank_positions':r['rank_positions'],'actionable_batch_id':r['current_actionable_batch_id'],'observed_scope_bucket':r['current_observed_scope_bucket']}for r in current_records])
    outputs['current-new-investigations']=base.write_parts(out,'current-new-investigations',[new_records[i]for i in sorted(new_records)])
    report={'version':'worldatlas-selected-current-native-v1','executed_code_commit':execution,'executed_project_modules':executed,'source_defined_successor_reader':reader_binding,
        'accepted_successor_commit':S,'selected_source_commit':base.M,'frozen_native_commit':args.frozen_commit,'frozen_native_report':args.frozen_report,
        'component_count':len(current_records),'context_count':len(contexts),'new_component_count':len(new_components),'retained_original_investigation_count':len(current_records)-len(new_components),
        'full_current_component_roster_sha256':sha256(canonical_json(sorted(current_ids))),'original_lineage_count':len(original_lineage),'current_lineage_count':len(current_lineage),
        'native_counts':counts,'full_grid_accounting':accounting,'rank_views':queues,'triage_counts':dict(sorted(triage.items())),
        'fine_family_count':len(batches),'operational_batch_count':len(operational),'prioritized_dispatch_candidates':dispatch_candidates(operational),
        'inputs':list(inputs.pins.values()),'outputs':outputs,'software':software,
        'source_metadata_hash_domains':'Successor metadata hashes cover whole source feature excluding geometry. Accepted context metadata covers its properties.metadata only; both source feature vintages join every context by their complete feature hashes. No digest equality across these different domains is asserted.',
        'complete_current_investigation_view':'Complete original investigations retained for identical current component IDs; six new full investigations join ordinary complete current component/fragment/source/contact bindings. Current complete rank positions and native overlays join by exact ID. Complete original/current lineage remains bound to accepted successor products.',
        'limits':['Accepted7c7 successor candidate, not an actual merged/released/production claim.','All measurements scoped to one representative cell and exact stored cell centre; remaining component cells unchecked.','Cause, water, source authority and administrative assignment remain unknown unless separately researched.','Complete current fine families and operational batches are disjoint triaged backlog; no repair, fill or automatic claim eligibility.']}
    (out/'report.json').write_bytes(canonical_json(report));print(json.dumps({'current_components':len(current_records),'new':len(new_components),'batches':len(batches),'operational':len(operational)}),flush=True)

if __name__=='__main__':main()
