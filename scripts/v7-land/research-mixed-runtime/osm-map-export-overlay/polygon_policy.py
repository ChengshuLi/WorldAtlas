"""Normalize FK-backed, source-polygon component selections, without selecting cells.

This adapter does not read source geometry or resolve components. The caller must
hash and parse the provider-original raw features, rasterize them on the current
grid and authenticate current physical-component lineage before applying claims.
"""
import re
from decimal import Decimal,InvalidOperation
from urllib.parse import urlsplit
HEX=re.compile(r'^[a-f0-9]{64}$')
def need(v,m):
 if not v:raise ValueError(m)
def txt(x):return isinstance(x,str) and bool(x.strip())
def raw_origin(asset):
 p=asset.get('provenance');need(isinstance(p,dict),'source provenance missing')
 if p.get('representation')=='provider_original':return 'provider_original'
 if (asset.get('provider')=='European Environment Agency' and p.get('source_kind')=='preserved direct GeoJSON query response, not full EEA dataset' and txt(p.get('r2_readback')) and urlsplit(asset.get('source_uri','')).scheme=='https' and urlsplit(asset.get('source_uri','')).hostname=='bio.discomap.eea.europa.eu'):
  return 'preserved_official_eea_query_response'
 raise ValueError('unsupported polygon source provenance')
def map_export_bounds(provenance):
 q=provenance.get('osm_map_export');need(isinstance(q,dict) and set(q)=={'request_method','bounds'} and q['request_method']=='POST','invalid map export provenance')
 b=q['bounds'];need(isinstance(b,dict) and set(b)=={'minlon','minlat','maxlon','maxlat'} and all(isinstance(x,str) and 0<len(x)<=24 for x in b.values()),'invalid map export bounds')
 try:v={k:Decimal(x) for k,x in b.items()}
 except InvalidOperation:raise ValueError('invalid map export bounds') from None
 need(all(x.is_finite() for x in v.values()) and -180<=v['minlon']<v['maxlon']<=180 and -90<=v['minlat']<v['maxlat']<=90 and v['maxlon']-v['minlon']<=1 and v['maxlat']-v['minlat']<=1 and (v['maxlon']-v['minlon'])*(v['maxlat']-v['minlat'])<=Decimal('0.25'),'invalid map export bounds')
 return dict(b)
def uniq(rows,key,label):
 need(isinstance(rows,list) and len(rows)<=10000,'invalid '+label);out={}
 for row in rows:
  need(isinstance(row,dict),'invalid '+label);k=key(row);need(k not in out,'duplicate '+label);out[k]=row
 return out
def witness(w):
 need(isinstance(w,dict) and set(w)=={'lon','lat'} and all(txt(w[k]) for k in ('lon','lat')),'invalid witness')
 try:lon,lat=Decimal(w['lon']),Decimal(w['lat'])
 except InvalidOperation:raise ValueError('invalid witness coordinate') from None
 need(lon.is_finite() and lat.is_finite() and -180<=lon<180 and -90<=lat<=90,'witness outside CRS84')
 return {'lon':w['lon'],'lat':w['lat']}
def adapt(snapshot,selected_ids):
 need(isinstance(snapshot,dict) and snapshot.get('source')=='neon-export' and snapshot.get('schema') in ('worldatlas-geography-decision-draft-evidence-v1','worldatlas-geography-decision-draft-evidence-v2','worldatlas-geography-decision-draft-evidence-v3'),'Neon snapshot required')
 refs0=snapshot.get('polygon_corroboration_refs',[]);affiliations=snapshot.get('affiliations');need(isinstance(refs0,list) and isinstance(affiliations,list) and (snapshot['schema'].endswith('-v1') and not refs0 and not any(isinstance(a,dict) and isinstance(a.get('evidence'),dict) and a['evidence'].get('polygon_corroboration_mode') is not None for a in affiliations) or snapshot['schema'].endswith(('-v2','-v3')) and 'polygon_corroboration_refs' in snapshot),'invalid schema or corroboration refs')
 need(not snapshot.get('schema','').endswith('-v3') or snapshot.get('unsupported_affiliation_source_ref_table_present') is False and snapshot.get('unsupported_point_methods_present') is False and snapshot.get('affiliation_source_refs')==[],'unsupported affiliation-source table status')
 revision=snapshot.get('decision_revision',{});need(revision.get('status')=='draft' and txt(revision.get('id')),'draft revision required')
 need(isinstance(selected_ids,(set,frozenset)) and len(selected_ids)<=1000,'invalid selected IDs')
 aff=uniq(snapshot.get('affiliations'),lambda x:x.get('affiliation_id'),'affiliations');features=uniq(snapshot.get('features'),lambda x:x.get('feature_id'),'features');sources=uniq(snapshot.get('sources'),lambda x:(x.get('source_id'),x.get('version')),'sources');assets=uniq(snapshot.get('source_lineage_assets'),lambda x:(x.get('source_id'),x.get('version')),'assets');deps=snapshot.get('source_lineage_dependencies');need(isinstance(deps,list),'source lineage missing')
 refs=snapshot.get('polygon_affiliation_feature_refs',[]);need(isinstance(refs,list) and len(refs)<=10000,'invalid polygon feature refs');links={};seen=set()
 for x in refs:
  need(isinstance(x,dict) and set(x)=={'affiliation_id','role','feature_id'} and x['role']=='additional_polygon' and all(txt(x[k]) for k in ('affiliation_id','feature_id')),'invalid polygon feature ref')
  pair=(x['affiliation_id'],x['feature_id']);need(pair not in seen and pair[0] in selected_ids and pair[1] in features,'duplicate or orphan polygon feature ref');seen.add(pair);links.setdefault(pair[0],set()).add(pair[1])
 result=[];needed={}
 for aid in sorted(selected_ids):
  a=aff.get(aid);need(isinstance(a,dict) and a.get('decision_revision')==revision['id'] and a.get('scope')=='land' and a.get('relationship')=='affiliation' and a.get('method') in ('component_intersection_v1','osm_relation_component_intersection_v1','component_containment_v1','osm_archipelago_component_intersection_v1','osm_archipelago_component_containment_v1','osm_archipelago_anchored_rings_intersection_v1') and a.get('evidence',{}).get('execution_status')=='selected_for_research','invalid polygon affiliation')
  method=a['method'];sel=a['evidence'].get('selector');need(isinstance(sel,dict),'invalid polygon selector');keys={'additional_feature_ids','include_witnesses','exclude_witnesses'}|({'relation_version','extractor_version'} if method in ('osm_relation_component_intersection_v1','osm_archipelago_component_intersection_v1','osm_archipelago_component_containment_v1','osm_archipelago_anchored_rings_intersection_v1') else set());version=sel.get('extractor_version');keys|=({'expected_identity_tags'} if version in ('osm-multipolygon-outer-v3','osm-multipolygon-outer-v4','osm-multipolygon-outer-label-v1','osm-anchored-outer-rings-v1') else set());keys|=({'anchors'} if method=='osm_archipelago_anchored_rings_intersection_v1' else set());keys|=({'label_node_id','label_node_version','expected_label_tags'} if version=='osm-multipolygon-outer-label-v1' else set());need(set(sel)==keys,'invalid polygon selector');extra=sel['additional_feature_ids'];need(isinstance(extra,list) and len(extra)<=1000 and all(txt(x) for x in extra) and len(set(extra))==len(extra) and set(extra)==links.get(aid,set()),'polygon FK/selector mismatch')
  if method in ('component_containment_v1','osm_archipelago_component_containment_v1'):need(not extra and sel['include_witnesses']==[] and sel['exclude_witnesses']==[],'containment requires one feature and no witnesses')
  if method=='osm_archipelago_component_containment_v1':need(version=='osm-multipolygon-outer-label-v1','label containment requires label extractor')
  if method in ('osm_relation_component_intersection_v1','osm_archipelago_component_intersection_v1','osm_archipelago_component_containment_v1'):
   need(not extra and isinstance(sel['relation_version'],str) and sel['relation_version'].isdigit() and int(sel['relation_version'])>0 and version in ('osm-multipolygon-outer-v2','osm-multipolygon-outer-v3','osm-multipolygon-outer-v4','osm-multipolygon-outer-label-v1') and (version!='osm-multipolygon-outer-label-v1' or method in ('osm_archipelago_component_intersection_v1','osm_archipelago_component_containment_v1')) and (method not in ('osm_archipelago_component_intersection_v1','osm_archipelago_component_containment_v1') or (version in ('osm-multipolygon-outer-v4','osm-multipolygon-outer-label-v1') and sel['include_witnesses']==[] and sel['exclude_witnesses']==[])),'unsupported OSM relation selector')
   if version in ('osm-multipolygon-outer-v3','osm-multipolygon-outer-v4','osm-multipolygon-outer-label-v1'):
    tags=sel['expected_identity_tags'];allowed={'name','name:en','place','wikidata'}|({'alt_name'} if version=='osm-multipolygon-outer-v4' else set());need(isinstance(tags,dict) and set(tags)<=allowed and tags.get('place')==('archipelago' if method in ('osm_archipelago_component_intersection_v1','osm_archipelago_component_containment_v1') else 'island') and any(txt(tags.get(k)) for k in ('name','name:en')) and all(txt(v) for v in tags.values()),'invalid expected island identity tags')
  if version=='osm-multipolygon-outer-label-v1':
   lt=sel['expected_label_tags'];need(all(isinstance(sel[k],str) and sel[k].isdigit() and int(sel[k])>0 for k in ('label_node_id','label_node_version')) and isinstance(lt,dict) and 0<len(lt)<=32 and all(txt(k) and len(k)<=256 and txt(v) and len(v)<=1024 for k,v in lt.items()),'invalid label node identity')
  if method=='osm_archipelago_anchored_rings_intersection_v1':
   tags=sel['expected_identity_tags'];anchors=sel['anchors'];need(not extra and not sel['include_witnesses'] and not sel['exclude_witnesses'] and version=='osm-anchored-outer-rings-v1' and isinstance(sel['relation_version'],str) and sel['relation_version'].isdigit() and int(sel['relation_version'])>0,'invalid anchored ring selector');need(isinstance(tags,dict) and set(tags)<={'name','name:en','place','wikidata'} and tags.get('place')=='archipelago' and any(txt(tags.get(k)) for k in ('name','name:en')) and all(txt(v) for v in tags.values()),'invalid anchored relation tags');need(isinstance(anchors,list) and 1<=len(anchors)<=32,'invalid anchors');ids=[]
   for anchor in anchors:
    need(isinstance(anchor,dict) and set(anchor)=={'node_id','node_version','way_id','expected_tags','geometry_sha256'} and all(isinstance(anchor[k],str) and anchor[k].isdigit() and int(anchor[k])>0 for k in ('node_id','node_version','way_id')) and isinstance(anchor['geometry_sha256'],str) and HEX.fullmatch(anchor['geometry_sha256']),'invalid anchored member');at=anchor['expected_tags'];need(isinstance(at,dict) and set(at)<={'name','name:en','amenity'} and at.get('amenity')=='ferry_terminal' and any(txt(at.get(k)) for k in ('name','name:en')) and all(txt(v) for v in at.values()),'invalid anchor tags');ids.append(anchor['node_id'])
   need(len(set(ids))==len(ids) and len(set(a['geometry_sha256'] for a in anchors))==len(anchors),'duplicate anchor or ring')
  primary=a.get('feature_id');need(txt(primary) and primary not in extra,'invalid primary feature');items=[]
  for fid in [primary,*extra]:
   f=features.get(fid);need(isinstance(f,dict) and txt(f.get('source_feature_id')) and isinstance(f.get('geometry_sha256'),str) and HEX.fullmatch(f['geometry_sha256']),'invalid polygon feature')
   k=(f.get('source_id'),f.get('source_version'));s=sources.get(k);asset=assets.get(k);need(isinstance(s,dict) and isinstance(asset,dict) and asset.get('kind')=='raw','unsupported polygon source');origin=raw_origin(asset);need(not any(isinstance(d,dict) and (d.get('source_id'),d.get('version'))==k for d in deps),'derived polygon source forbidden')
   need(all(s.get(v)==asset.get(v) for v in ('sha256','r2_bucket','r2_key','size_bytes')) and isinstance(s.get('sha256'),str) and HEX.fullmatch(s['sha256']) and txt(s.get('r2_bucket')) and txt(s.get('r2_key')) and type(s.get('size_bytes')) is int and s['size_bytes']>0,'invalid source custody');need(all(txt(asset.get(v)) for v in ('source_uri','attribution','license_name','provider')),'missing source attribution')
   provenance=asset.get('provenance',{});unknown='unspecified' in asset['license_name'].casefold();uri=asset.get('license_uri')
   if unknown:
    terms=provenance.get('reuse_terms');need(asset['license_name'] in ('Unspecified','Reuse terms unspecified; user directed proceeding') and txt(terms) and (terms.strip().casefold()=='unspecified' or ('not established' in terms.casefold() and 'no redistribution license is asserted' in terms.casefold())) and 'approved for redistribution' not in terms.casefold() and (uri is None or (txt(uri) and provenance.get('terms_uri_role')=='Service documentation, not an asserted redistribution license.')),'missing explicit unspecified reuse terms or documentation role')
   else:need(txt(uri),'missing source license URI')
   ev=f.get('evidence');need(isinstance(ev,dict),'source feature evidence missing');needed[k]={**s,'validated_representation':origin,'source_uri':asset['source_uri'],'attribution':asset['attribution'],'license_name':asset['license_name'],'license_uri':asset['license_uri'],'license_uri_role':asset.get('provenance',{}).get('terms_uri_role'),'reuse_terms':asset.get('provenance',{}).get('reuse_terms'),'source_query_identity':asset.get('provenance',{}).get('source_query_identity'),'historical_v7_equivalence':asset.get('provenance',{}).get('historical_v7_equivalence'),'source_origin':asset.get('provenance',{}).get('origin'),'source_r2_verification':asset.get('provenance',{}).get('r2_verification',asset.get('provenance',{}).get('r2_readback'))}
   item={'feature_id':fid,'source_feature_id':f['source_feature_id'],'geometry_sha256':f['geometry_sha256'],'source_id':k[0],'source_version':k[1]}
   if method in ('component_intersection_v1','component_containment_v1'):need(txt(ev.get('selector_property')),'source feature ID property missing');item['id_property']=ev['selector_property'];item['source_format']='geojson'
   else:
    need(f['source_feature_id'].isdigit() and int(f['source_feature_id'])>0 and ev.get('source_format')=='osm-xml' and ev.get('relation_version')==sel['relation_version'] and ev.get('geometry_hash_method')=='binary64-sorted-compact-geojson-v1' and origin=='provider_original','OSM feature/source mismatch');item.update(source_format='osm-xml',relation_version=sel['relation_version'],extractor_version=sel['extractor_version']);
    if version in ('osm-multipolygon-outer-v3','osm-multipolygon-outer-v4','osm-multipolygon-outer-label-v1'):item['expected_identity_tags']=sel['expected_identity_tags']
    if version=='osm-multipolygon-outer-label-v1':item.update(label_node_id=sel['label_node_id'],label_node_version=sel['label_node_version'],expected_label_tags=sel['expected_label_tags'])
    if method in ('osm_archipelago_component_intersection_v1','osm_archipelago_component_containment_v1'):
     u=urlsplit(asset['source_uri']);need(not u.query and not u.fragment and u.scheme=='https','archipelago official source URI mismatch')
     if u.netloc=='api.openstreetmap.org' and u.path==f"/api/0.6/relation/{f['source_feature_id']}/full":need('osm_map_export' not in provenance,'unexpected map export metadata')
     elif u.netloc=='www.openstreetmap.org' and u.path=='/export/finish' and version=='osm-multipolygon-outer-v4' and method=='osm_archipelago_component_intersection_v1':
      proof=ev.get('r2_verification');need(asset.get('provider')=='OpenStreetMap' and asset.get('license_name')=='ODbL 1.0' and asset.get('license_uri')=='https://opendatacommons.org/licenses/odbl/1-0/' and asset.get('attribution')=='© OpenStreetMap contributors','invalid map export attribution')
      need(isinstance(proof,dict) and set(proof)=={'status','method','sha256','size_bytes','r2_bucket','r2_key'} and proof.get('status')=='verified' and proof.get('method')=='full-byte-compare' and all(proof.get(k)==asset.get(k) for k in ('sha256','size_bytes','r2_bucket','r2_key')),'invalid map export custody proof');item['map_export_bounds']=map_export_bounds(provenance)
     else:raise ValueError('archipelago official source URI mismatch')
     item['source_class']='archipelago'
    if method=='osm_archipelago_anchored_rings_intersection_v1':
     u=urlsplit(asset['source_uri']);need(u.scheme=='https' and u.netloc=='api.openstreetmap.org' and u.path==f"/api/0.6/relation/{f['source_feature_id']}/full" and not u.query and not u.fragment,'anchored official source URI mismatch');item.update(source_class='archipelago',expected_relation_tags=sel['expected_identity_tags'],anchors=sel['anchors'])
   items.append(item)
  inc=sel['include_witnesses'];exc=sel['exclude_witnesses'];need(isinstance(inc,list) and isinstance(exc,list) and len(inc)+len(exc)<=1000,'invalid witnesses')
  selected_assertion=a['evidence'].get('exclusion_witness_evidence')
  if selected_assertion is not None:
   fields={'source_affiliation_id','relation_id','anchor_node_id','anchor_node_version','outer_way_id','ring_geometry_sha256','method','proof_sha256','limitation','witness'}
   need(isinstance(selected_assertion,dict) and set(selected_assertion)==fields and all(txt(selected_assertion.get(k)) for k in fields-{'witness'}) and HEX.fullmatch(selected_assertion['proof_sha256']) and HEX.fullmatch(selected_assertion['ring_geometry_sha256']),'invalid exclusion witness assertion')
   w=witness(selected_assertion['witness']);need(sum(w==witness(x) for x in exc)==1,'assertion witness is not exactly one excluded selector')
   refid=selected_assertion['source_affiliation_id'];ref=aff.get(refid);need(refid in selected_ids and isinstance(ref,dict) and ref.get('decision_revision')==revision['id'] and ref.get('method')=='osm_archipelago_anchored_rings_intersection_v1' and ref.get('entity_id')==a.get('entity_id') and ref.get('evidence',{}).get('execution_status')=='selected_for_research','invalid selected anchor affiliation')
   rf=features.get(ref.get('feature_id'));rsel=ref.get('evidence',{}).get('selector',{});anchors=rsel.get('anchors');need(isinstance(rf,dict) and rf.get('source_feature_id')==selected_assertion['relation_id'] and isinstance(anchors,list),'assertion relation mismatch')
   matches=[x for x in anchors if isinstance(x,dict) and x.get('node_id')==selected_assertion['anchor_node_id'] and x.get('node_version')==selected_assertion['anchor_node_version'] and x.get('way_id')==selected_assertion['outer_way_id'] and x.get('geometry_sha256')==selected_assertion['ring_geometry_sha256']];need(len(matches)==1,'assertion anchor mismatch')
   selected_assertion={'kind':'selected_assertion_not_recomputed',**selected_assertion}
  limits=a['evidence'].get('limitations',[]);need(isinstance(limits,list) and len(limits)<=1000 and all(txt(x) and len(x)<=8192 for x in limits),'invalid decision limitations');result.append({'affiliation_id':aid,'entity_id':a.get('entity_id'),'method':a['method'],'features':items,'include_witnesses':[witness(x) for x in inc],'exclude_witnesses':[witness(x) for x in exc],'decision_limitations':limits,**({'exclusion_witness_assertion':selected_assertion} if selected_assertion is not None else {})})
 return {'schema':'stage3-polygon-decisions-v1','revision':revision['id'],'decisions':result,'source_pins':[needed[k] for k in sorted(needed)],'status':'requires-source-resolution'}
