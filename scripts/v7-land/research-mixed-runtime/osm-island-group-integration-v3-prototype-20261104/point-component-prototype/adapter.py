"""Map a combined Neon export to point claims without selecting geography.

This is a pure research adapter; it neither authenticates an export nor accesses
Neon/R2. Input bytes and implementation must be pinned by its caller.
"""
import re
from urllib.parse import urlsplit
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
    need(doc.get('schema') in ('worldatlas-geography-decision-draft-evidence-v1','worldatlas-geography-decision-draft-evidence-v2','worldatlas-geography-decision-draft-evidence-v3') and doc.get('source')=='neon-export','draft Neon export required')
    refs=doc.get('polygon_corroboration_refs',[]); need(isinstance(refs,list) and (doc['schema'].endswith('-v1') and not refs and not any(a.get('evidence',{}).get('polygon_corroboration_mode') is not None for a in doc.get('affiliations',[]) if isinstance(a,dict)) or doc['schema'].endswith(('-v2','-v3')) and 'polygon_corroboration_refs' in doc), 'invalid combined export version or corroboration refs')
    need((doc['schema'].endswith('-v3') and isinstance(doc.get('ecoregion_source_refs'),list)) or (not doc['schema'].endswith('-v3') and 'ecoregion_source_refs' not in doc),'invalid ecoregion export version')
    need(not doc['schema'].endswith('-v3') or doc.get('unsupported_affiliation_source_ref_table_present') is False and doc.get('unsupported_point_methods_present') is False and doc.get('affiliation_source_refs')==[],'unsupported affiliation-source table status')
    need(not doc['schema'].endswith('-v3') or not any(isinstance(a,dict) and a.get('evidence',{}).get('execution_status')=='selected_for_research' and a.get('method') in ('source_point_component_v1','raw_json_city_named_region_component_v1') for a in doc.get('affiliations',[])),'unsupported v3 point source-reference method')
    rev=doc.get('decision_revision',{});ent=doc.get('entity_revision',{})
    need(rev.get('status')=='draft' and ent.get('status')=='draft' and text(rev.get('id')) and text(ent.get('id')) and rev.get('entity_revision')==ent.get('id'),'revision mismatch')
    aff=unique(doc.get('affiliations'),lambda x:x.get('affiliation_id'));features=unique(doc.get('features'),lambda x:x.get('feature_id'))
    src=unique(doc.get('sources'),lambda x:(x.get('source_id'),x.get('version')));assets=unique(doc.get('source_lineage_assets'),lambda x:(x.get('source_id'),x.get('version')))
    entities=unique(doc.get('entities'),lambda x:x.get('id'));bindings=doc.get('category_bindings');need(isinstance(bindings,list),'bindings required')
    for a in aff.values():need(text(a.get('affiliation_id')),'invalid affiliation identity')
    for f in features.values():need(text(f.get('feature_id')),'invalid feature identity')
    for k in src:need(all(text(v) for v in k),'invalid source identity')
    refs=doc.get('affiliation_source_refs');need(isinstance(refs,list),'source references required');identity={};guidelines={};seen_refs=set()
    for r in refs:
        need(isinstance(r,dict) and set(r)=={'affiliation_id','role','source_id','source_version'} and all(text(r[k]) for k in r),'malformed source reference')
        aid=r['affiliation_id'];key=(r['source_id'],r['source_version']);ref=(aid,r['role'],*key)
        need(aid in aff and key in src and key in assets and ref not in seen_refs,'orphan or duplicate source reference');seen_refs.add(ref)
        method=aff[aid].get('method')
        if method=='source_point_component_v1' and r['role']=='identity_evidence':
            need(aid not in identity,'duplicate source role');identity[aid]=key
        elif method=='raw_json_city_named_region_component_v1' and r['role']=='coordinate_guideline':
            need(aid not in guidelines,'duplicate guideline role');guidelines[aid]=key
        else:raise ValueError('orphan, duplicate or unsupported source role')
    feature_refs=doc.get('affiliation_feature_refs',[]);need(isinstance(feature_refs,list),'feature references required');named_identity={}
    for r in feature_refs:
        need(isinstance(r,dict) and set(r)=={'affiliation_id','role','feature_id'} and all(text(r[k]) for k in r),'malformed identity feature reference')
        aid=r['affiliation_id'];need(aid in aff and aff[aid].get('method') in ('source_point_named_region_component_v1','raw_json_city_named_region_component_v1','osm_api_node_named_region_component_v1','osm_api_island_node_group_component_v1') and r['role']=='identity_polygon' and aid not in named_identity and r['feature_id'] in features,'orphan, duplicate or unsupported feature reference')
        named_identity[aid]=r['feature_id']
    selected=[];needed=set();targets={}
    for aid,a in sorted(aff.items()):
        method=a.get('method')
        if method not in ('source_point_component_v1','source_point_named_region_component_v1','raw_json_city_named_region_component_v1','osm_api_node_named_region_component_v1','osm_api_island_node_group_component_v1'):continue
        evidence=a.get('evidence');need(a.get('scope')=='land' and a.get('relationship')=='affiliation' and text(a.get('rationale')) and isinstance(evidence,dict) and evidence.get('execution_status')=='selected_for_research','unselected or invalid point affiliation')
        sel=evidence.get('selector');keys=({'island_name','group_identity','identity_scope','id_property'} if method=='osm_api_island_node_group_component_v1' else {'island_identity','point_name','id_property'})
        if method in ('source_point_named_region_component_v1','raw_json_city_named_region_component_v1','osm_api_node_named_region_component_v1','osm_api_island_node_group_component_v1'):keys|={'identity_id_property','identity_name_property','identity_class_property','identity_class_value'}
        if method in ('osm_api_node_named_region_component_v1','osm_api_island_node_group_component_v1'):keys|={'node_version','place_tag','source_crs','extractor_version'}
        if method=='raw_json_city_named_region_component_v1':keys|={'name_property','longitude_property','latitude_property','source_crs_assertion','extractor_version','coordinate_guideline_excerpt'}
        need(isinstance(sel,dict) and set(sel)==keys and all(text(sel.get(k)) for k in keys),'point selector missing identity or contains unsupported keys')
        if method=='osm_api_island_node_group_component_v1':need(sel['identity_scope']=='island_group' and sel['identity_class_value']=='Island group' and sel['place_tag']=='island','invalid island group scope or class')
        if method in ('osm_api_node_named_region_component_v1','osm_api_island_node_group_component_v1'):need(sel['id_property']=='id' and re.fullmatch(r'[1-9][0-9]{0,19}',sel['node_version']) is not None and sel['source_crs']=='OGC:CRS84' and sel['extractor_version']=='osm-api-node-point-selection-v1','unsupported OSM node selector')
        if method=='raw_json_city_named_region_component_v1':need(sel['extractor_version']=='raw-json-city-point-selection-v1' and sel['source_crs_assertion']=='OGC:CRS84','unsupported raw city extractor or CRS')
        f=features.get(a.get('feature_id'));need(isinstance(f,dict) and text(f.get('source_feature_id')) and isinstance(f.get('geometry_sha256'),str) and HEX.fullmatch(f['geometry_sha256']),'point feature missing')
        pk=(f.get('source_id'),f.get('source_version'));extra={}
        if method=='source_point_component_v1':
            need(aid in identity,'point feature or identity source missing');ik=identity[aid]
        else:
            ident=features.get(named_identity.get(aid));need(isinstance(ident,dict) and ident.get('feature_id')!=f['feature_id'] and text(ident.get('source_feature_id')) and isinstance(ident.get('geometry_sha256'),str) and HEX.fullmatch(ident['geometry_sha256']),'identity polygon feature missing')
            ik=(ident.get('source_id'),ident.get('source_version'))
            extra={'identity_feature_id':ident['feature_id'],'identity_source_feature_id':ident['source_feature_id'],'identity_geometry_sha256':ident['geometry_sha256'],**{k:sel[k] for k in ('identity_id_property','identity_name_property','identity_class_property','identity_class_value')}}
        if method in ('osm_api_node_named_region_component_v1','osm_api_island_node_group_component_v1'):
            need(re.fullmatch(r'[1-9][0-9]{0,19}',f['source_feature_id']) is not None,'invalid OSM node ID');src_asset=assets.get(pk);need(isinstance(src_asset,dict) and text(src_asset.get('source_uri')),'OSM source missing');u=urlsplit(src_asset['source_uri']);expected='/api/0.6/node/'+f['source_feature_id'];need(u.scheme=='https' and u.netloc=='api.openstreetmap.org' and not u.query and not u.fragment and u.path in (expected,expected+'/'+sel['node_version']),'official OSM node URL mismatch')
            extra.update({k:sel[k] for k in ('node_version','place_tag','source_crs','extractor_version')})
            if method=='osm_api_island_node_group_component_v1':extra.update({'identity_scope':sel['identity_scope'],'group_identity':sel['group_identity'],'island_name':sel['island_name']})
        if method=='raw_json_city_named_region_component_v1':
            need(aid in guidelines,'coordinate guideline missing');gk=guidelines[aid];need(gk in src and gk!=pk and gk!=ik,'invalid coordinate guideline source')
            excerpt=sel['coordinate_guideline_excerpt'];need(len(excerpt)<=512 and '\n' not in excerpt and '\r' not in excerpt,'invalid guideline excerpt')
            def git_source(key):
                asset=assets.get(key);need(isinstance(asset,dict) and text(asset.get('source_uri')) and text(asset.get('provider')),'missing git source metadata')
                u=urlsplit(asset['source_uri']);parts=u.path.strip('/').split('/')
                need(u.scheme=='https' and u.netloc=='github.com' and not u.query and not u.fragment and len(parts)>=5 and parts[2]=='blob' and re.fullmatch(r'[0-9a-f]{40}',parts[3]) is not None,'pinned GitHub source URL required')
                return (parts[0],parts[1],parts[3],asset['provider'])
            need(git_source(pk)==git_source(gk),'guideline and city must share provider repository and commit')
            extra.update({k:sel[k] for k in ('name_property','longitude_property','latitude_property','source_crs_assertion','extractor_version','coordinate_guideline_excerpt')});extra.update({'guideline_source_id':gk[0],'guideline_source_version':gk[1]});needed.add(gk)
        need(pk!=ik and pk in src and ik in src,'point and identity sources missing or identical')
        eid=a.get('entity_id');entity=entities.get(eid);matches=[b for b in bindings if b.get('entity_id')==eid and b.get('physical_class')=='land']
        need(type(eid) is int and isinstance(entity,dict) and text(entity.get('name')) and len(matches)==1 and type(matches[0].get('code')) is int and 17<=matches[0]['code']<=22,'invalid point target')
        targets[eid]={'id':eid,'name':entity['name'],'physical_class':'land','code':matches[0]['code']};needed.update((pk,ik))
        selected.append({'affiliation_id':aid,'method':method,'execution_status':'selected_for_research','entity_id':eid,'island_identity':sel['group_identity'] if method=='osm_api_island_node_group_component_v1' else sel['island_identity'],'point_name':sel['island_name'] if method=='osm_api_island_node_group_component_v1' else sel['point_name'],'point_source_id':pk[0],'point_source_version':pk[1],'identity_source_id':ik[0],'identity_source_version':ik[1],'source_feature_id':f['source_feature_id'],'id_property':sel['id_property'],'geometry_sha256':f['geometry_sha256'],'feature_id':f['feature_id'],'rationale':a['rationale'],**extra})
    need(selected,'no selected point affiliations')
    need(set(guidelines)=={x['affiliation_id'] for x in selected if x['method']=='raw_json_city_named_region_component_v1'},'unused guideline reference')
    need(set(identity)=={x['affiliation_id'] for x in selected if x['method']=='source_point_component_v1'} and set(named_identity)=={x['affiliation_id'] for x in selected if x['method'] in ('source_point_named_region_component_v1','raw_json_city_named_region_component_v1','osm_api_node_named_region_component_v1','osm_api_island_node_group_component_v1')},'unused identity reference')
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
