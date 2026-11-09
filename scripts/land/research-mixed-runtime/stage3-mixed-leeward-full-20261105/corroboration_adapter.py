"""Normalize revision-scoped administrative evidence links; never select roots.

The selected polygon policy must already be independently authenticated by the
normal polygon adapter. This narrow WFS method preserves a reported origin and
requires the caller to pin/recheck code, snapshot, raw sources and streams.
"""
import re
from urllib.parse import urlsplit
from collections import defaultdict
from corroboration_source import METHOD,HASH_METHOD
HEX=re.compile(r'^[0-9a-f]{64}$')
OFFICIAL_URI=('https://webgis.regione.sardegna.it/geoserver/wfs?service=WFS&version=2.0.0&request=GetFeature&typeNames=dbu%3Adbgt_10k_22_v05_09_comune&CQL_FILTER=cistat+IN+%28%27111008%27%2C%27111010%27%2C%27111071%27%29&srsName=EPSG%3A4326&outputFormat=application%2Fjson')
def need(v,m):
 if not v:raise ValueError(m)
def txt(v):return isinstance(v,str) and bool(v.strip()) and len(v)<=8192
def uniq(rows,key,label):
 need(isinstance(rows,list) and len(rows)<=10000,'invalid '+label);out={}
 for r in rows:
  need(isinstance(r,dict),'invalid '+label);k=key(r);need(k not in out,'duplicate '+label);out[k]=r
 return out

def adapt(snapshot,polygon_policy):
 need(isinstance(snapshot,dict) and snapshot.get('schema') in ('worldatlas-geography-decision-draft-evidence-v1','worldatlas-geography-decision-draft-evidence-v2','worldatlas-geography-decision-draft-evidence-v3') and snapshot.get('source')=='neon-export','invalid snapshot')
 need(not snapshot.get('schema','').endswith('-v3') or snapshot.get('unsupported_affiliation_source_ref_table_present') is False and snapshot.get('unsupported_point_methods_present') is False and snapshot.get('affiliation_source_refs')==[],'unsupported affiliation-source table status')
 rev=snapshot.get('decision_revision',{});revision=rev.get('id');need(rev.get('status')=='draft' and txt(revision),'invalid revision')
 need(isinstance(polygon_policy,dict) and polygon_policy.get('schema')=='stage3-polygon-decisions-v1' and polygon_policy.get('revision')==revision and isinstance(polygon_policy.get('decisions'),list),'invalid selected polygon policy')
 aff=uniq(snapshot.get('affiliations'),lambda x:x.get('affiliation_id'),'affiliations');features=uniq(snapshot.get('features'),lambda x:x.get('feature_id'),'features');sources=uniq(snapshot.get('sources'),lambda x:(x.get('source_id'),x.get('version')),'sources');assets=uniq(snapshot.get('source_lineage_assets'),lambda x:(x.get('source_id'),x.get('version')),'source assets');deps=snapshot.get('source_lineage_dependencies');need(isinstance(deps,list),'missing source lineage')
 selected=uniq(polygon_policy['decisions'],lambda x:x.get('affiliation_id'),'selected decisions');required={}
 for aid,d in selected.items():
  a=aff.get(aid);need(isinstance(a,dict) and a.get('decision_revision')==revision and a.get('evidence',{}).get('execution_status')=='selected_for_research' and a.get('method')==d.get('method'),'invalid selected affiliation')
  mode=a['evidence'].get('polygon_corroboration_mode');need(mode in (None,'administrative_geometry_v1'),'unsupported corroboration mode')
  if mode is not None:
   need(d.get('method')=='component_intersection_v1' and isinstance(d.get('features'),list) and 0<len(d['features'])<=1000,'unsupported selected method');ids=[x.get('feature_id') if isinstance(x,dict) else None for x in d['features']];need(all(txt(x) for x in ids) and len(ids)==len(set(ids)),'invalid selector features');required[aid]=set(ids)
 refs=snapshot.get('polygon_corroboration_refs',[]);need(isinstance(refs,list) and len(refs)<=4096 and (snapshot['schema'].endswith('-v1') and not refs and not required or snapshot['schema'].endswith(('-v2','-v3')) and 'polygon_corroboration_refs' in snapshot),'invalid schema or corroboration refs');pairs=set();group=defaultdict(set)
 for r in refs:
  need(isinstance(r,dict) and set(r)=={'decision_revision','affiliation_id','selected_feature_id','corroborating_feature_id'} and r['decision_revision']==revision and all(txt(r[k]) for k in ('affiliation_id','selected_feature_id','corroborating_feature_id')),'invalid corroboration ref')
  aid=r['affiliation_id'];sf=r['selected_feature_id'];cf=r['corroborating_feature_id'];pair=(aid,sf,cf);need(pair not in pairs and aid in required and sf in required[aid] and cf in features and cf not in required[aid],'duplicate, orphan or extra corroboration ref');pairs.add(pair);group[(aid,sf)].add(cf)
 need(set(group)=={(aid,fid) for aid,fs in required.items() for fid in fs},'missing corroboration mapping')
 used={cf for _,_,cf in pairs};need(len(used)<=1000,'too many administrative features');sourcekeys=set();descriptors=[];seen_source_ids=set();names=set()
 for fid in sorted(used):
  f=features[fid];ev=f.get('evidence');need(isinstance(ev,dict) and set(ev)=={'source_format','selector_property','expected_name','coordinate_method','geometry_hash_method'} and ev['source_format']=='geojson' and ev['selector_property']=='cistat' and txt(ev['expected_name']) and ev['coordinate_method']==METHOD and ev['geometry_hash_method']==HASH_METHOD,'invalid administrative feature evidence')
  sid=f.get('source_feature_id');gh=f.get('geometry_sha256');key=(f.get('source_id'),f.get('source_version'));need(txt(sid) and isinstance(gh,str) and HEX.fullmatch(gh) and (key,sid) not in seen_source_ids and ev['expected_name'] not in names,'duplicate or invalid administrative identity');seen_source_ids.add((key,sid));names.add(ev['expected_name']);s=sources.get(key);asset=assets.get(key);need(isinstance(s,dict) and isinstance(asset,dict) and asset.get('kind')=='raw' and not any(isinstance(x,dict) and (x.get('source_id'),x.get('version'))==key for x in deps),'invalid raw source lineage');need(all(s.get(k)==asset.get(k) for k in ('sha256','r2_bucket','r2_key','size_bytes')) and isinstance(s.get('sha256'),str) and HEX.fullmatch(s['sha256']) and txt(s.get('r2_bucket')) and txt(s.get('r2_key')) and type(s.get('size_bytes')) is int and 0<s['size_bytes']<=16<<20,'invalid source custody');need(asset.get('source_uri')==OFFICIAL_URI and all(txt(asset.get(k)) for k in ('provider','attribution','license_name')),'unsupported WFS source');provenance=asset.get('provenance');need(isinstance(provenance,dict) and provenance.get('representation')=='worker_reported_provider_response' and provenance.get('original_http_metadata')=='headers and capture timestamp not retained','missing source-origin caveat');sourcekeys.add(key);descriptors.append({'feature_id':fid,'source_feature_id':sid,'name':ev['expected_name'],'geometry_sha256':gh,'geometry_hash_method':HASH_METHOD,'source_id':key[0],'source_version':key[1]})
 selector_keys={(p.get('source_id'),p.get('version')) for p in polygon_policy.get('source_pins',[])};need(not sourcekeys&selector_keys,'administrative and selector source files must be separate')
 mappings=[{'affiliation_id':aid,'selected_feature_id':sf,'administrative_feature_ids':sorted(group[(aid,sf)])} for aid,sf in sorted(group)];pins=[{**sources[k],'source_uri':assets[k]['source_uri'],'provider':assets[k]['provider'],'attribution':assets[k]['attribution'],'license_name':assets[k]['license_name'],'license_uri':assets[k].get('license_uri'),'provenance_assertions':assets[k]['provenance']} for k in sorted(sourcekeys)]
 return {'schema':'administrative-corroboration-policy-v1','revision':revision,'mappings':mappings,'features':descriptors,'source_pins':pins,'limitations':['Source provenance and coordinate order are selected assertions, not authenticated by this adapter.','Administrative geometry corroborates location and is never an island selector.']}
