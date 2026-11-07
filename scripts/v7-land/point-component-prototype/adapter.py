"""Map a combined Neon export to point claims without selecting geography.

This is a pure research adapter; it neither authenticates an export nor accesses
Neon/R2. Input bytes and implementation must be pinned by its caller.
"""
import re
HEX=re.compile(r'^[0-9a-f]{64}$')

def need(ok,msg):
    if not ok: raise ValueError(msg)
def text(s):return isinstance(s,str) and bool(s.strip())
def unique(items,key):
    need(isinstance(items,list),'required array missing');out={}
    for x in items:
        need(isinstance(x,dict),'invalid row');k=key(x);need(k not in out,'duplicate identity');out[k]=x
    return out

def adapt(doc):
    need(doc.get('schema')=='worldatlas-geography-decision-draft-evidence-v1' and doc.get('source')=='neon-export','draft Neon export required')
    rev=doc.get('decision_revision',{});ent=doc.get('entity_revision',{})
    need(rev.get('status')=='draft' and ent.get('status')=='draft' and text(rev.get('id')) and text(ent.get('id')) and rev.get('entity_revision')==ent.get('id'),'revision mismatch')
    aff=unique(doc.get('affiliations'),lambda x:x.get('affiliation_id'));features=unique(doc.get('features'),lambda x:x.get('feature_id'))
    src=unique(doc.get('sources'),lambda x:(x.get('source_id'),x.get('version')));assets=unique(doc.get('source_lineage_assets'),lambda x:(x.get('source_id'),x.get('version')))
    entities=unique(doc.get('entities'),lambda x:x.get('id'));bindings=doc.get('category_bindings');need(isinstance(bindings,list),'bindings required')
    for a in aff.values():need(text(a.get('affiliation_id')),'invalid affiliation identity')
    for f in features.values():need(text(f.get('feature_id')),'invalid feature identity')
    for k in src:need(all(text(v) for v in k),'invalid source identity')
    refs=doc.get('affiliation_source_refs');need(isinstance(refs,list),'source references required');identity={};seen_refs=set()
    for r in refs:
        need(isinstance(r,dict) and set(r)=={'affiliation_id','role','source_id','source_version'} and all(text(r[k]) for k in r),'malformed source reference')
        aid=r['affiliation_id'];key=(r['source_id'],r['source_version']);ref=(aid,r['role'],*key)
        need(aid in aff and key in src and key in assets and ref not in seen_refs,'orphan or duplicate source reference');seen_refs.add(ref)
        need(aff[aid].get('method')=='source_point_component_v1' and r['role']=='identity_evidence' and aid not in identity,'orphan, duplicate or unsupported source role');identity[aid]=key
    feature_refs=doc.get('affiliation_feature_refs',[]);need(isinstance(feature_refs,list),'feature references required');named_identity={}
    for r in feature_refs:
        need(isinstance(r,dict) and set(r)=={'affiliation_id','role','feature_id'} and all(text(r[k]) for k in r),'malformed identity feature reference')
        aid=r['affiliation_id'];need(aid in aff and aff[aid].get('method')=='source_point_named_region_component_v1' and r['role']=='identity_polygon' and aid not in named_identity and r['feature_id'] in features,'orphan, duplicate or unsupported feature reference')
        named_identity[aid]=r['feature_id']
    selected=[];needed=set();targets={}
    for aid,a in sorted(aff.items()):
        method=a.get('method')
        if method not in ('source_point_component_v1','source_point_named_region_component_v1'):continue
        evidence=a.get('evidence');need(a.get('scope')=='land' and a.get('relationship')=='affiliation' and text(a.get('rationale')) and isinstance(evidence,dict) and evidence.get('execution_status')=='selected_for_research','unselected or invalid point affiliation')
        sel=evidence.get('selector');keys={'island_identity','point_name','id_property'}
        if method=='source_point_named_region_component_v1':keys|={'identity_id_property','identity_name_property','identity_class_property','identity_class_value'}
        need(isinstance(sel,dict) and set(sel)==keys and all(text(sel.get(k)) for k in keys),'point selector missing identity or contains unsupported keys')
        f=features.get(a.get('feature_id'));need(isinstance(f,dict) and text(f.get('source_feature_id')) and isinstance(f.get('geometry_sha256'),str) and HEX.fullmatch(f['geometry_sha256']),'point feature missing')
        pk=(f.get('source_id'),f.get('source_version'));extra={}
        if method=='source_point_component_v1':
            need(aid in identity,'point feature or identity source missing');ik=identity[aid]
        else:
            ident=features.get(named_identity.get(aid));need(isinstance(ident,dict) and ident.get('feature_id')!=f['feature_id'] and text(ident.get('source_feature_id')) and isinstance(ident.get('geometry_sha256'),str) and HEX.fullmatch(ident['geometry_sha256']),'identity polygon feature missing')
            ik=(ident.get('source_id'),ident.get('source_version'))
            extra={'identity_feature_id':ident['feature_id'],'identity_source_feature_id':ident['source_feature_id'],'identity_geometry_sha256':ident['geometry_sha256'],**{k:sel[k] for k in ('identity_id_property','identity_name_property','identity_class_property','identity_class_value')}}
        need(pk!=ik and pk in src and ik in src,'point and identity sources missing or identical')
        eid=a.get('entity_id');entity=entities.get(eid);matches=[b for b in bindings if b.get('entity_id')==eid and b.get('physical_class')=='land']
        need(type(eid) is int and isinstance(entity,dict) and text(entity.get('name')) and len(matches)==1 and type(matches[0].get('code')) is int and 17<=matches[0]['code']<=22,'invalid point target')
        targets[eid]={'id':eid,'name':entity['name'],'physical_class':'land','code':matches[0]['code']};needed.update((pk,ik))
        selected.append({'affiliation_id':aid,'method':method,'execution_status':'selected_for_research','entity_id':eid,'island_identity':sel['island_identity'],'point_name':sel['point_name'],'point_source_id':pk[0],'point_source_version':pk[1],'identity_source_id':ik[0],'identity_source_version':ik[1],'source_feature_id':f['source_feature_id'],'id_property':sel['id_property'],'geometry_sha256':f['geometry_sha256'],'feature_id':f['feature_id'],'rationale':a['rationale'],**extra})
    need(selected,'no selected point affiliations')
    need(set(identity)=={x['affiliation_id'] for x in selected if x['method']=='source_point_component_v1'} and set(named_identity)=={x['affiliation_id'] for x in selected if x['method']=='source_point_named_region_component_v1'},'unused identity reference')
    deps=doc.get('source_lineage_dependencies');need(isinstance(deps,list),'source lineage dependencies required')
    for key in needed:
        a=assets.get(key);need(isinstance(a,dict) and a.get('kind')=='raw' and isinstance(a.get('provenance'),dict) and a['provenance'].get('representation')=='provider_original','only provider-original raw source assets are supported')
        parents=[d for d in deps if isinstance(d,dict) and (d.get('source_id'),d.get('version'))==key]
        need(not parents,'raw source may not have parent dependencies')
    result_sources=[]
    for key in sorted(needed):
        a=assets.get(key);need(isinstance(a,dict) and all(text(a.get(k)) for k in ('sha256','r2_bucket','r2_key')) and HEX.fullmatch(a['sha256']),'source catalog custody mismatch')
        s=src.get(key,a);need(all(s.get(k)==a.get(k) for k in ('sha256','r2_bucket','r2_key')),'source catalog custody mismatch')
        need(all(text(a.get(k)) for k in ('source_uri','attribution','license_name','license_uri','provider','title')) and type(a.get('size_bytes')) is int and a['size_bytes']>0 and s.get('size_bytes')==a['size_bytes'],'source attribution, size or license missing')
        result_sources.append({'source_id':key[0],'version':key[1],'sha256':s['sha256'],'uri':a['source_uri'],'attribution':a['attribution'],'license':a['license_name'],'license_uri':a['license_uri'],'provider':a['provider'],'title':a['title'],'size_bytes':a['size_bytes'],'r2_bucket':s['r2_bucket'],'r2_key':s['r2_key'],'kind':a['kind'],'provenance':a['provenance']})
    return {'schema':'point-component-decision-view-v1','source':'derived-from-neon-export','status':'draft','revision':rev['id'],'entity_revision':ent['id'],'sources':result_sources,'target_entities':list(targets.values()),'decisions':selected}
