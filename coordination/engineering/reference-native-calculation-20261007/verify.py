"""Full tuple/archive/index and two-tree readback; no new GIS calculation."""
import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import stat
import sys
import reader
import products
import producer

NS=producer.NS
F='b596ef836c51c5405baa8ceda770a2554ca12b7f'

def canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)


def whole_tree(root):
    files={}
    for path in root.rglob('*'):
        if path.is_symlink():raise ValueError('Whole ordinary output tree contains symlink')
        if path.is_file():
            relative=str(path.relative_to(root));raw=reader.bounded(reader.safe(root,relative))
            files[relative]={'bytes':len(raw),'sha256':reader.sha(raw),'mode':stat.S_IMODE(path.stat().st_mode)}
    return files


def verify_one(run,source,plan,complete):
    base=reader.safe(reader.ROOT/'.cache',run);output=reader.safe(base,'products')
    report=json.loads(reader.bounded(reader.safe(base,'report.json')))
    capsule=json.loads(reader.bounded(reader.safe(base,'execution.json')))
    if report['execution_commit']!=F or report['changed_ids']!=sorted(products.TARGETS) or report['missing_changed'] or report['derived_records']!=14:
        raise ValueError('Complete actual fourteen target calculation required')
    if (not report['historical_claims_transferred'] is False or report['before_footprints_sha256']!=complete['before_footprints_sha256'] or
            report['after_footprints_sha256']!=complete['after_footprints_sha256'] or report['migration_receipt_sha256']!=complete['migration_receipt_sha256']):
        raise ValueError('Exact before/after/source migration binding required')
    observed={p['path']:p for p in capsule['source_inputs']}
    expected={p['path']:{k:p[k] for k in ('commit','path','mode','blob','bytes','sha256')} for p in plan['source_descriptors']}
    if observed!=expected:raise ValueError('Actual consumed complete171 source roster differs')
    bodies={p.removeprefix('data/reference-attributes/'):source.read(p) for p in plan['original_reference_files']}
    view=reader.safe(base,'original-reference-view');producer.authenticate_reference_view(view,bodies)
    before=json.loads(bodies['index.json']);old=products.records(before,bodies,complete['ids'])
    index=json.loads(reader.bounded(reader.safe(output,'index.json')))
    newbodies={name:reader.bounded(reader.safe(output,name)) for name in index['parts']}
    new=products.records(index,newbodies,complete['ids'])
    if index['types'][:len(before['types'])]!=before['types'] or index['values'][:len(before['values'])]!=before['values']:
        raise ValueError('Original types/categories/source interval prefix changed')
    preserved=0
    for id in complete['ids']-products.TARGETS:
        if canonical(old.get(id,[]))!=canonical(new.get(id,[])):
            raise ValueError('Unaffected complete tuple record changed')
        preserved+=len(old.get(id,[]))
    fresh={id:new[id] for id in products.TARGETS};products.validate_fresh(index,fresh,{})
    archived=products.decode_part(reader.bounded(reader.safe(output,'migration-before-records.json.gz')))
    if canonical(archived)!=canonical([[id,old[id]] for id in sorted(products.TARGETS)]):
        raise ValueError('Complete original fourteen archival tuples changed')
    receipt=json.loads(reader.bounded(reader.safe(output,'incremental-receipt.json')))
    if (receipt['derived_records']!=14 or receipt['archive']['records']!=14 or receipt['changed_ids']!=sorted(products.TARGETS) or
            receipt['unknown_changed'] or receipt['missing_changed'] or receipt['after_records']!=346346 or
            receipt['reused_records']!=preserved or receipt['reused_locations']!=49623 or receipt['recomputed_locations']!=2):
        raise ValueError('Complete measured tuple/count receipt mismatch')
    if index['incremental_preparation']['receipt_sha256']!=reader.sha(reader.bounded(reader.safe(output,'incremental-receipt.json'))):
        raise ValueError('Actual active index receipt digest drift')
    counts=Counter();missing={str(y):[] for y in (1901,1931,1961,1991)}
    for id in sorted(complete['ids']):
        seen=set()
        for ti,vi,share,coverage in new.get(id,[]):
            t=index['types'][ti];counts[(t['attribute'],t['valid_from'],t['status'])]+=1;seen.add((t['attribute'],t['valid_from']))
        for year in missing:
            if ('climate',int(year)) not in seen:missing[year].append(id)
    if (index['records']!=sum(map(len,new.values())) or index['records']!=346346 or index['locations']!=49625 or
            index['represented_locations']!=sum(bool(v) for v in new.values()) or index['missing_climate']!=missing or
            index['climate_counts']!={str(y):counts[('climate',y,'reference')] for y in (1901,1931,1961,1991)} or
            index['vegetation_references']!=counts[('vegetation',2026,'reference')] or
            index['unknown_source_records']!=counts[('vegetation',2026,'unknown')] or
            index['merged_sources']['topography-reference']['records']!=counts[('topography',2026,'reference')]):
        raise ValueError('Full actual reference index/counts/missing statuses mismatch')
    if index['footprints_sha256']!=complete['after_footprints_sha256'] or index['inputs']['geography']!=complete['after_geography_sha256']:
        raise ValueError('Whole proposed geography/source binding mismatch')
    source_roles=receipt['sources']
    if (source_roles['actual_custody_merge']!=producer.C or source_roles['whole_climate_archive_sha256']!=before['inputs']['climate_archive'] or
            source_roles['whole_vegetation_sha256']!=before['inputs']['ecoregions'] or
            source_roles['native_members']!=plan['complete_native_members'] or not source_roles['source_proof_or_ZIP_not_read_in_this_phase']):
        raise ValueError('Actual source/member/upstream custody role mismatch')
    # Every original archive file remains exactly somewhere in the product
    # history. Equal payloads are not renamed original containing-file aliases.
    allfiles=whole_tree(output);payloads={(v['bytes'],v['sha256']) for v in allfiles.values()}
    prior_files=[n for n in bodies if n.startswith('prior-archives/')]
    for name in prior_files:
        if (len(bodies[name]),reader.sha(bodies[name])) not in payloads:
            raise ValueError('Original prior archive body lost')
    changed=[]
    for id in sorted(products.TARGETS):
        oldby={(before['types'][r[0]]['attribute'],before['types'][r[0]]['valid_from'],before['types'][r[0]]['valid_to']):r for r in old[id]}
        for row in fresh[id]:
            t=index['types'][row[0]];key=(t['attribute'],t['valid_from'],t['valid_to']);previous=oldby[key]
            changed.append({'id':id,'attribute':key[0],'valid_from':key[1],'valid_to':key[2],
                'original_category':before['values'][previous[1]],'new_category':index['values'][row[1]],
                'original_share':previous[2],'new_share':row[2],'original_coverage':previous[3],'new_coverage':row[3],
                'complete_tuple_changed':canonical(previous)!=canonical(row)})
    return {'complete_locations':49625,'unchanged_locations':49623,'unchanged_complete_records':preserved,
        'original_reference_files':len(bodies),'archived_original_target_records':14,'recomputed_target_records':14,
        'all_after_records':index['records'],'scientific_files':len(allfiles),'scientific_encoded_bytes':sum(v['bytes'] for v in allfiles.values()),
        'original_prior_archive_files_retained':len(prior_files),'full_target_records':changed,'files':allfiles}


def run(code_commit,one,two):
    own=reader.Inputs(code_commit);producer.authenticated_module(sys.modules[__name__],own.read(NS+'verify.py'))
    _,source,plan=producer.actual_inputs(F);complete=producer.scope.complete_world(source)
    a=verify_one(one,source,plan,complete);b=verify_one(two,source,plan,complete)
    if a!=b:raise ValueError('Two full scientific products/tuple/index/whole-byte proofs differ')
    return {'status':'PASS','verification_code_commit':code_commit,'actual_scientific_execution_commit':F,
        'two_actual_complete_runs':2,'scientific_byte_mode_and_complete_field_equality':True,'whole_scope':a,
        'numerical_values_recomputed_by_this_verifier':False,'numerical_basis':'Two actual frozen literal original function runs; exact imported source/operator runtime fingerprints retained. This verifier proves structural/source/whole-row conservation, not an independent replacement GIS method.',
        'source_fitness_authority_or_parent_activation_approved':False}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--code-commit',required=True);parser.add_argument('--one',required=True);parser.add_argument('--two',required=True)
    args=parser.parse_args();print(json.dumps(run(args.code_commit,args.one,args.two),ensure_ascii=False,allow_nan=False))
