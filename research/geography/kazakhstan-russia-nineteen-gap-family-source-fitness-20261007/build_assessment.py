#!/usr/bin/env python3
"""Deterministically bind assigned 52 components to frozen source and comparison rows."""
import argparse, gc, gzip, hashlib, json, pathlib
ROOT=pathlib.Path(__file__).resolve().parent
INPUT=ROOT/'inputs'
FREEZE=ROOT/'source-freeze.json'

def raw_sha(b): return hashlib.sha256(b).hexdigest()
def canonical(x): return (json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode('utf-8')
def read_json(p): return json.loads(p.read_text(encoding='utf-8'))
def digest_file(p): return raw_sha(p.read_bytes())
def eq(a,b,msg):
    if a!=b: raise ValueError(msg)

def main():
    # Every parsed source is ordinary JSON with no reference cycles. Avoid repeated
    # cyclic graph scans over the full global report; reference counting remains active.
    gc.disable()
    ap=argparse.ArgumentParser(); ap.add_argument('--out',required=True); args=ap.parse_args()
    freeze=read_json(FREEZE)
    eq(digest_file(ROOT/'build_assessment.py'),freeze['producer_sha256'],'producer bytes differ from freeze')
    eq(digest_file(ROOT/'input-manifest.json'),freeze['input_manifest_sha256'],'input manifest differs from freeze')
    for item in read_json(ROOT/'input-manifest.json')['files']:
        b=(ROOT/item['path']).read_bytes()
        eq(len(b),item['bytes'],'input byte count differs: '+item['path'])
        eq(raw_sha(b),item['sha256'],'input digest differs: '+item['path'])
    hand=read_json(INPUT/'complete-kazakhstan-russia-handoff.json')
    route=read_json(INPUT/'routing/report.json'); phys=read_json(INPUT/'physical/report.json')
    input_config=read_json(INPUT/'routing/input-config.json')
    physical_group=next(g for g in input_config['source_groups'] if g['namespace']=='global-physical-comparison-20261006')
    packed_descriptors={d['path']:d for d in physical_group['files']}
    target_ids=set(hand['component_ids']); families=hand['families']; fam_by_component={}
    for f in families:
        for cid in f['complete_component_ids']:
            if cid in fam_by_component: raise ValueError('component assigned to multiple families')
            fam_by_component[cid]=f['id']
    eq(len(families),19,'family count'); eq(len(target_ids),52,'assigned component count')
    eq(set(fam_by_component),target_ids,'whole family/component closure differs')
    # Authenticate all routing output bytes, then assemble and verify whole ordered bodies before parsing.
    eq(len({d['path'] for d in route['outputs']}),len(route['outputs']),'duplicate routing output path')
    for d in route['outputs']:
        b=(INPUT/'routing'/d['path']).read_bytes()
        eq(len(b),d['bytes'],'routing output byte count: '+d['path']); eq(raw_sha(b),d['sha256'],'routing output digest: '+d['path'])
    bodies={}
    for body in route['complete_whole_raw_bodies']:
        decoded=b''.join(gzip.decompress((INPUT/'routing'/p['path']).read_bytes()) for p in body['parts'])
        eq(len(decoded),body['bytes'],'routing body size: '+body['name']); eq(raw_sha(decoded),body['sha256'],'routing whole-body digest: '+body['name'])
        bodies[body['name']]=decoded
    comp_rows=[json.loads(x) for x in bodies['components'].splitlines()]
    fam_rows=[json.loads(x) for x in bodies['families'].splitlines()]
    admin_rows=[json.loads(x) for x in bodies['admin-bindings'].splitlines()]
    route_comp={r['component']:r for r in comp_rows}; route_fam={r['id']:r for r in fam_rows}; admin_by={r['component']:r for r in admin_rows}
    eq(len(route_comp),len(comp_rows),'duplicate complete routing component identity'); eq(len(route_fam),len(fam_rows),'duplicate complete family identity')
    eq(set(route_comp)&target_ids,target_ids,'target components missing from complete routing body')
    eq(sum(f['id'] in route_fam for f in families),19,'target families missing from complete routing body')
    # Verify complete consumed simplified source products and retained metadata.
    source_specs=[('gb:KAZ:ADM2','geoboundaries-kaz-adm2-2017-simplified-full-source.geojson',174,'68868f08e28fa4b8510fa28db21b8432ad9c1539625b92842158a168edfd2efd'),('gb:RUS:ADM2','geoboundaries-rus-adm2-2017-simplified-full-source.geojson',2327,'81dabf7930ff5e306e2423b586bcec14163fbd10481db6e49aab47273953b128')]
    catalogue=read_json(INPUT/'metadata/catalogue.json'); products={p['key']:p for p in catalogue['products']}
    custody=read_json(INPUT/'metadata/complete-custody-validity.json'); custody_rows={r['key']:r for r in custody['rows']}; srcinfo={}
    for key,path,count,sha in source_specs:
        b=(INPUT/path).read_bytes(); obj=json.loads(b); row=products[key]; vr=custody_rows[key]
        eq(raw_sha(b),sha,'whole source bytes: '+key); eq(len(obj['features']),count,'whole source feature count: '+key)
        eq(row['original_sha256'],sha,'catalogue source checksum: '+key); eq(vr['complete_features'],count,'source validity feature count: '+key)
        meta=read_json(INPUT/'metadata'/f'{key.split(":")[1]}-geoBoundaries-{key.split(":")[1]}-ADM2-metaData.json')
        srcinfo[key]={'path':path,'bytes':len(b),'sha256':sha,'feature_count':count,'advertised_feature_count':row['advertised_feature_count'],'recorded_year':row['source_represented_year_claim'],'recorded_consumed_url':row['recorded_consumed_url'],'underlying_license_recorded':row['recorded_license'],'source_id_set_sha256':vr['complete_sorted_shape_ids_sha256'],'advertised_count_matches':vr['advertised_count_matches'],'boundaryID':meta['boundaryID'],'boundarySource':meta['boundarySource'],'boundarySourceURL':meta['boundarySourceURL'],'boundaryLicense':meta['boundaryLicense'],'sourceDataUpdateDate':meta['sourceDataUpdateDate'],'buildDate':meta['buildDate'],'crs':obj.get('crs')}
    candidates={f['id']:f for f in hand['full_candidates']}
    if len(candidates)!=52 or set(candidates)!=target_ids: raise ValueError('candidate feature closure differs')
    physical_report_paths={pathlib.Path(r['path']).name:r for r in phys['products']}; rows=[]
    family_counts={f['id']:{'component_count':f['component_count'],'candidate_ids':[],'compatible_original_admin_count':len(f['compatible_original_admin_component_ids']),'partial_or_unbound_count':f['component_count']-len(f['compatible_original_admin_component_ids']),'source_fitness':f['source_fitness'],'physical_status_counts':f['physical_status_counts'],'admin_status_counts':f['admin_status_counts']} for f in families}
    physical_cache={}; physical_second_cache={}; physical_packed_cache={}
    for cid in sorted(target_ids):
        famid=fam_by_component[cid]; family=next(f for f in families if f['id']==famid); cand=candidates[cid]; route_row=route_comp[cid]
        if route_row['family']!=famid: raise ValueError('routing component family mismatch: '+cid)
        compatible=cid in set(family['compatible_original_admin_component_ids']); admin=admin_by.get(cid)
        if admin is None: raise ValueError('missing admin binding record '+cid)
        observations=admin['observations']; source_products=sorted({s for obs in observations for s in obs.get('source_products',[])})
        ppath=route_row['whole_physical_containing_file']; pdesc=physical_report_paths.get(pathlib.Path(ppath).name)
        if pdesc is None: raise ValueError('physical file absent from report: '+ppath)
        packed_desc=packed_descriptors.get(ppath)
        if packed_desc is None: raise ValueError('packed physical source descriptor absent: '+ppath)
        if ppath not in physical_cache:
            pfile=INPUT/'physical'/pathlib.Path(ppath).name; b=pfile.read_bytes()
            eq(len(b),pdesc['bytes'],'physical container size: '+ppath); eq(raw_sha(b),pdesc['sha256'],'physical container digest: '+ppath)
            physical_cache[ppath]={}
            for line in gzip.decompress(b).splitlines():
                row=json.loads(line)
                if row['component_id'] in physical_cache[ppath]: raise ValueError('duplicate physical identity: '+row['component_id'])
                physical_cache[ppath][row['component_id']]=row
        prow=physical_cache[ppath].get(cid)
        if prow is None: raise ValueError('physical scientific row not found: '+cid)
        packed_path=INPUT/'physical-packed'/pathlib.Path(ppath).name
        if ppath not in physical_packed_cache:
            packed_bytes=packed_path.read_bytes()
            eq(len(packed_bytes),packed_desc['bytes'],'packed physical container size: '+ppath)
            eq(raw_sha(packed_bytes),packed_desc['sha256'],'packed physical container digest: '+ppath)
            physical_packed_cache[ppath]={}
            for line in gzip.decompress(packed_bytes).splitlines():
                row=json.loads(line)
                if row['component_id'] in physical_packed_cache[ppath]: raise ValueError('duplicate packed physical identity: '+row['component_id'])
                physical_packed_cache[ppath][row['component_id']]=row
        packed_row=physical_packed_cache[ppath].get(cid)
        if packed_row is None or raw_sha(canonical(packed_row))!=route_row['whole_physical_row_sha256']: raise ValueError('packed physical row identity hash mismatch: '+cid)
        if ppath not in physical_second_cache:
            pfile=INPUT/'physical-second'/pathlib.Path(ppath).name; b=pfile.read_bytes()
            eq(len(b),pdesc['bytes'],'second physical container size: '+ppath); eq(raw_sha(b),pdesc['sha256'],'second physical container digest: '+ppath)
            physical_second_cache[ppath]={}
            for line in gzip.decompress(b).splitlines():
                row=json.loads(line)
                if row['component_id'] in physical_second_cache[ppath]: raise ValueError('duplicate second physical identity: '+row['component_id'])
                physical_second_cache[ppath][row['component_id']]=row
        prow2=physical_second_cache[ppath].get(cid)
        if prow2 is None or canonical(prow2)!=canonical(prow): raise ValueError('complete physical records differ between retained runs: '+cid)
        full_projection={k:v for k,v in prow.items() if k not in ('original_context','candidate_feature_sha256','candidate_geometry_sha256')}
        full_projection['complete_current_record_metadata_alias']='v1'
        if canonical(full_projection)!=canonical(packed_row): raise ValueError('packed/full physical transport restoration differs: '+cid)
        if prow['physical_authority']!='unapproved': raise ValueError('physical authority was promoted')
        areas={k:v['area_m2'] for k,v in prow['complete_support'].items() if k!='hierarchy_disagreements'}
        hareas={k:v['area_m2'] for k,v in prow['complete_support']['hierarchy_disagreements'].items()}
        row={'component_id':cid,'family_id':famid,'candidate_feature':cand,'candidate_geometry_sha256':raw_sha(canonical(cand['geometry'])),'candidate_feature_sha256':raw_sha(canonical(cand)),'family_component_count':family['component_count'],'source_fitness_class':'compatible-original coverage candidate' if compatible else 'partial/unbound original source-fitness case','original_source_products':source_products,'admin_observation_statuses':sorted({o['status'] for o in observations}),'admin_observation_count':len(observations),'unique_cover_ids':[o.get('uniquely_covering_compatible_recorded_subject') for o in observations if o.get('uniquely_covering_compatible_recorded_subject')],'whole_routing_component_record_sha256':raw_sha(canonical(route_row)),'physical_source_vintage':prow['source_vintage'],'physical_status':prow['status'],'physical_authority':prow['physical_authority'],'physical_unresolved':prow['unresolved'],'physical_source_areas_m2':areas,'hierarchy_disagreement_areas_m2':hareas,'physical_containing_path':ppath,'physical_packed_container_sha256':packed_desc['sha256'],'physical_source_container_sha256':pdesc['sha256'],'physical_second_source_container_sha256':pdesc['sha256'],'physical_row_sha256':route_row['whole_physical_row_sha256'],'physical_repeat_run_equal':True,'physical_packed_to_full_restoration_equal':True,'physical_limits':prow['physical_limits'],'contact_ids':prow.get('complete_contact_ids',[]),'water_status':cand['properties'].get('water_status','unverified'),'candidate_has_positive_area_source_overlap':cand['properties'].get('positive_area_input_overlap')}
        rows.append(row); family_counts[famid]['candidate_ids'].append(cid)
    eq(sum(r['source_fitness_class'].startswith('compatible') for r in rows),28,'compatible source-fit count')
    eq(sum(r['source_fitness_class'].startswith('partial') for r in rows),24,'partial/unbound source-fit count')
    # Authenticate every full current contact against the complete pinned Atlas part bytes.
    part_bytes={p:(INPUT/'atlas'/f'part-{p}.json').read_bytes() for p in (12,20,21)}; contacts=hand['full_current_contacts']; contact_rows=[]
    for ident,record in sorted(contacts.items()):
        name=pathlib.Path(record['containing_path']).name; part=next((n for n in (12,20,21) if name==f'part-{n}.json'),None)
        if part is None: raise ValueError('contact outside complete assigned parts')
        b=part_bytes[part]; eq(len(b),record['containing_bytes'],'contact part size: '+ident); eq(raw_sha(b),record['containing_sha256'],'contact part digest: '+ident)
        obj=json.loads(b); features=obj['features'] if isinstance(obj,dict) else obj; matches=[(i,f) for i,f in enumerate(features) if f.get('id')==ident]
        if len(matches)!=1: raise ValueError('contact identity missing/duplicate: '+ident)
        ordinal,feat=matches[0]
        if ordinal!=record['ordinal'] or raw_sha(canonical(feat))!=record['full_feature_sha256'] or raw_sha(canonical(feat['geometry']))!=record['geometry_sha256']: raise ValueError('whole contact feature binding differs: '+ident)
        contact_rows.append({'id':ident,'feature':feat,'source_path':record['containing_path'],'source_part_sha256':record['containing_sha256'],'feature_sha256':record['full_feature_sha256'],'geometry_sha256':record['geometry_sha256'],'ordinal':ordinal})
    eq(len(contact_rows),41,'current contact count')
    out=pathlib.Path(args.out); out.mkdir(parents=True,exist_ok=False)
    write_json=lambda name,obj:(out/name).write_bytes(json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()+b'\n')
    with (out/'candidate-assessment.jsonl').open('wb') as f:
        for r in rows:f.write(canonical(r)+b'\n')
    write_json('family-reconciliation.json',{'family_count':19,'component_count':52,'numeric_first_family_count':0,'families':[{'id':k,**v} for k,v in sorted(family_counts.items())]})
    write_json('contact-lineage.json',{'contact_count':41,'contacts':contact_rows})
    write_json('source-products.json',{'sources':srcinfo,'geoBoundaries_release_commit':'9469f09','metadata_registry_commit':'c6a26e1caba54e1b81a89fbda3a64fff56da323d','source_purpose':'simplified single-country administrative boundary visualization products; not legal boundary authority','source_fitness':'source-relative only; effective validity/applicability and boundary authority unverified'})
    outputs=[]
    for p in sorted(out.iterdir()):
        b=p.read_bytes();outputs.append({'path':p.name,'bytes':len(b),'sha256':raw_sha(b)})
    write_json('output-manifest.json',{'outputs':outputs,'rows':len(rows),'families':len(family_counts),'contacts':len(contact_rows),'inputs_frozen':True})
    print(json.dumps({'status':'PASS','components':len(rows),'families':len(family_counts),'contacts':len(contact_rows),'compatible':28,'partial_or_unbound':24,'outputs':[x['path'] for x in outputs]},sort_keys=True))
if __name__=='__main__': main()
