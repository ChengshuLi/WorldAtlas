#!/usr/bin/env python3
"""Partition complete JRC vector-support requests into typed tile cohorts."""
import json, pathlib, gzip, hashlib, struct
CACHE=pathlib.Path(__file__).resolve().parent
ROOT=pathlib.Path(__file__).resolve().parents[1]
EXACT=json.load(open(CACHE/'jrc-exact-block-intersections.json'))
CONTEXT=json.load(open(ROOT/'inputs/context/selected-routing-and-operational-context.json'))
OUT=CACHE/'jrc-bounded-cohorts.json'
MAX_BLOCKS=64
# Family membership and original unresolved routing state from the pinned context.
family_rows=CONTEXT['selected_families_source_rows']
family_members={fid:set(row['complete_component_ids']) for fid,row in family_rows.items()}
family_by_component={cid:fid for fid,members in family_members.items() for cid in members}
assert len(family_by_component)==15 and set(family_by_component)=={f['id'] for f in EXACT['features'] if f['kind']=='candidate'}
features={f['id']:f for f in EXACT['features']}
tile_data=EXACT['tiles']
cohorts=[]
for tile,td in tile_data.items():
    for kind in ('candidate','contact'):
        members=[]
        for f in sorted((x for x in EXACT['features'] if x['kind']==kind),key=lambda x:x['id']):
            ids=f['exact_closed_block_indices_by_tile'].get(tile,[])
            if not ids: continue
            m={'id':f['id'],'source_ref':f['source_ref'],'block_indices_row_major':ids,'block_count':len(ids),'status_snapshot':f['status_snapshot']}
            if kind=='candidate': m['family_id']=family_by_component[f['id']]
            members.append(m)
        if not members: continue
        batch=[]; block_union=set(); seq=1
        for m in members:
            add=set(m['block_indices_row_major'])
            if len(block_union|add)>MAX_BLOCKS:
                blocks=sorted(block_union)
                cohorts.append({'cohort_id':f'{kind}-{tile}-{seq:02d}','subject_type':kind,'tile':tile,'max_unique_blocks':MAX_BLOCKS,'member_count':len(batch),'members':list(batch),'unique_block_count':len(blocks),'block_indices_row_major':blocks,'encoded_base_block_bytes':None,'decoded_full_block_upper_bound_bytes':len(blocks)*512*512})
                seq+=1;batch=[];block_union=set()
            assert len(add)<=MAX_BLOCKS
            batch.append(m);block_union|=add
        if batch:
            blocks=sorted(block_union)
            cohorts.append({'cohort_id':f'{kind}-{tile}-{seq:02d}','subject_type':kind,'tile':tile,'max_unique_blocks':MAX_BLOCKS,'member_count':len(batch),'members':list(batch),'unique_block_count':len(blocks),'block_indices_row_major':blocks,'encoded_base_block_bytes':None,'decoded_full_block_upper_bound_bytes':len(blocks)*512*512})
# Bind encoded block costs per cohort from the exact base IFD bytecount arrays.
for cohort in cohorts:
    range_id={'60E_40N':2,'70E_40N':4,'60E_50N':5,'70E_50N':6}[cohort['tile']]
    raw=(CACHE/f'gsw-ifd-range-{range_id}.bin')
    # range id is fixed by tile name; parse base TileByteCounts tag 325.
    b=raw.read_bytes(); off=struct.unpack_from('<I',b,4)[0]; n=struct.unpack_from('<H',b,off)[0]; counts=None; offsets=None
    for i in range(n):
        tag,typ,count,val=struct.unpack_from('<HHII',b,off+2+12*i)
        if tag==324: offsets=struct.unpack_from('<'+'I'*count,b,val)
        if tag==325: counts=struct.unpack_from('<'+'I'*count,b,val)
    assert counts and offsets and len(counts)==len(offsets)==6241
    cohort['encoded_base_block_bytes']=sum(counts[i] for i in cohort['block_indices_row_major'])
    spans=sorted((offsets[i],offsets[i]+counts[i]) for i in cohort['block_indices_row_major'])
    merged=[]
    for start,end in spans:
        if merged and start<=merged[-1][1]: merged[-1][1]=max(merged[-1][1],end)
        else: merged.append([start,end])
    cohort['conditional_range_windows_inclusive']=[[start,end-1] for start,end in merged]
    cohort['conditional_range_window_count']=len(merged)
    assert sum(end-start for start,end in merged)==cohort['encoded_base_block_bytes']
# Cohort-level unique source files and full-file costs; no geometry or raster clipped/copied.
source_files={}
for f in EXACT['features']:
    p=ROOT/f['source_ref'];source_files[f['source_ref']]= {'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
for c in cohorts:
    refs=sorted({m['source_ref'] for m in c['members']})
    c['complete_source_files']=[{'path':ref,'bytes':source_files[ref]['bytes'],'sha256':source_files[ref]['sha256']} for ref in refs]
    # Deduplicate references within this cohort.
    c['complete_source_files']=list({x['path']:x for x in c['complete_source_files']}.values())
    c['referenced_complete_source_bytes']=sum(x['bytes'] for x in c['complete_source_files'])
# Coverage and cap checks.
all_candidate={m['id'] for c in cohorts if c['subject_type']=='candidate' for m in c['members']}
all_contact={m['id'] for c in cohorts if c['subject_type']=='contact' for m in c['members']}
expected_candidate={f['id'] for f in EXACT['features'] if f['kind']=='candidate'}
expected_contact={f['id'] for f in EXACT['features'] if f['kind']=='contact'}
assert all_candidate==expected_candidate and all_contact==expected_contact
assert all(c['unique_block_count']<=MAX_BLOCKS for c in cohorts)
candidate_blocks_by_tile={tile:set() for tile in tile_data}
contact_blocks_by_tile={tile:set() for tile in tile_data}
for f in EXACT['features']:
    destination=candidate_blocks_by_tile if f['kind']=='candidate' else contact_blocks_by_tile
    for tile,indices in f['exact_closed_block_indices_by_tile'].items(): destination[tile].update(indices)
assert all(candidate_blocks_by_tile[tile] <= contact_blocks_by_tile[tile] for tile in tile_data)
selected_families=[]
for fid,row in sorted(family_rows.items()):
    selected_families.append({'family_id':fid,'component_count':row['component_count'],'complete_component_ids':row['complete_component_ids'],'cause_status':'unknown per original task record (no causal adjudication)','physical_authority':row['physical_authority'],'source_fitness':row['source_fitness'],'dispatch_ready':row['dispatch_ready'],'boundary_length_m':row.get('boundary_length_m')})
result={'contract_sha256':EXACT['contract_sha256'],'cohort_builder_script_sha256':hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),'block_intersection_manifest_sha256':hashlib.sha256((CACHE/'jrc-exact-block-intersections.json').read_bytes()).hexdigest(),'scope':{'complete_candidate_ids':sorted(expected_candidate),'complete_contact_ids':sorted(expected_contact),'candidate_unique_count':len(expected_candidate),'contact_unique_count':len(expected_contact)},'selected_family_unknowns':selected_families,'cohort_policy':{'cohort_subject_types':['candidate','contact'],'partition_keys':['tile','subject_type'],'max_unique_base_blocks_per_cohort':MAX_BLOCKS,'max_full_block_decode_upper_bound_bytes':MAX_BLOCKS*512*512,'geometry_handling':'Each cohort references the full original feature from its complete source file. No geometry is clipped or rewritten. A cross-tile feature appears in each relevant tile cohort with its exact block-index support; global subject coverage remains deduplicated by stable ID.','source_observation_support':'JRC occurrence is an aggregate frequency product; block intersection is spatial support only and does not establish physical class or water presence.'},'cohorts':cohorts,'coverage':{'all_15_candidate_ids_present':all_candidate==expected_candidate,'all_9_contact_ids_present':all_contact==expected_contact,'candidate_unique_count':len(all_candidate),'contact_unique_count':len(all_contact),'candidate_tile_memberships':sum(c['member_count'] for c in cohorts if c['subject_type']=='candidate'),'contact_tile_memberships':sum(c['member_count'] for c in cohorts if c['subject_type']=='contact')},'block_work_totals':{'deduplicated_tile_union_blocks':sum(len(tile_data[tile]['union_row_major_block_indices']) for tile in tile_data),'sum_of_per_cohort_unique_block_memberships':sum(c['unique_block_count'] for c in cohorts),'repeated_block_memberships_across_cohorts':sum(c['unique_block_count'] for c in cohorts)-sum(len(tile_data[tile]['union_row_major_block_indices']) for tile in tile_data),'sum_of_cohort_encoded_bytes':sum(c['encoded_base_block_bytes'] for c in cohorts),'sum_of_cohort_decoded_upper_bound_bytes':sum(c['decoded_full_block_upper_bound_bytes'] for c in cohorts),'candidate_unique_blocks':sum(len(v) for v in candidate_blocks_by_tile.values()),'contact_unique_blocks':sum(len(v) for v in contact_blocks_by_tile.values()),'candidate_blocks_without_contact_block_overlap':sum(len(candidate_blocks_by_tile[t]-contact_blocks_by_tile[t]) for t in tile_data)},'limits':['All original members and family unknowns are retained; each cohort references a whole source feature, and tile-specific support contains only exact intersected block indices.','The method uses vector-to-block geometry only. No TIFF block bytes were downloaded or decoded; no pixel values were classified.','Candidate/contact block overlap reflects shared grid cells only; it is not independent negative/control evidence.','Water presence/absence, physical class, effective date, boundary authority, rights/ownership, cause, registration accuracy, and source geometry accuracy remain unknown or unapproved.'],'source_files':[{'path':path,'bytes':value['bytes'],'sha256':value['sha256']} for path,value in sorted(source_files.items())]}
OUT.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'cohorts':len(cohorts),'per_cohort':[(c['cohort_id'],c['member_count'],c['unique_block_count'],c['encoded_base_block_bytes'],c['decoded_full_block_upper_bound_bytes']) for c in cohorts],'coverage':result['coverage'],'unique_subjects':result['scope'],'output_bytes':OUT.stat().st_size,'output_sha256':hashlib.sha256(OUT.read_bytes()).hexdigest()},indent=2))
