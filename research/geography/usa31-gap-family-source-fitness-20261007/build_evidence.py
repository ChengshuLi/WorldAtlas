#!/usr/bin/env python3
"""Build bounded, source-only evidence from pinned WorldAtlas inputs."""
from __future__ import annotations
import gzip, hashlib, json, pathlib, re, subprocess
from shapely.geometry import shape, mapping
from shapely.ops import transform
from pyproj import Transformer
ROOT=pathlib.Path(__file__).resolve().parents[3]
OUT=ROOT/'research/geography/usa31-gap-family-source-fitness-20261007'
CONTACTS=['gb:USA:ADM2:52423323B42354579566723','gb:USA:ADM2:52423323B61185146991898','gb:USA:ADM2:52423323B83071826775288']
ROUTE_COMMIT='0198938719a5666b6726fb6a1e45779926eefeb2'
NUMERIC_COMMIT='bec82842ad5d9cf07e38a78395df8d5e7a6f4591'
CANDIDATE_COMMIT='c6a26e1caba54e1b81a89fbda3a64fff56da323d'
ADMIN_REGISTRY_COMMIT='c6a26e1caba54e1b81a89fbda3a64fff56da323d'
CUSTODY_COMMIT='ea880cdc37b0bdfc63fdb52b79d74545a3e59c88'
PHYSICAL_COMMIT='f8f99612e4d83d561b370189a1969c3e4301a1e3'
SOURCE_CORPUS_COMMIT='1bf4bb01d76a76953d4a11308f5af2dd50fe3365'
FULL_SOURCE_COMMIT='c89bd7384b295da221a76a8dbf375adff431ab0a'
BASELINE_COMMIT='839883ae281af7bf012f694698624a7ec77275e1'
FAMILY='gap-source-batch:443a274744b54435ce17c373'
def sha(b): return hashlib.sha256(b).hexdigest()
def canonical(x): return (json.dumps(x,ensure_ascii=False,separators=(',',':'),sort_keys=True,allow_nan=False)+'\n').encode()
def git(ref,path): return subprocess.check_output(['git','show',f'{ref}:{path}'],cwd=ROOT)
def parse(b): return json.loads(b)
def write_bytes(rel,b):
 p=OUT/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b);return {'path':rel,'bytes':len(b),'sha256':sha(b)}
def write_json(rel,obj): return write_bytes(rel,canonical(obj))
def git_blob(ref,path):
 line=subprocess.check_output(['git','ls-tree','-l',ref,'--',path],cwd=ROOT,text=True).strip()
 if not line: raise ValueError('no tree entry '+ref+':'+path)
 meta,actual=line.split('\t',1); mode,kind,oid,size=meta.split()
 raw=git(ref,path); assert len(raw)==int(size)
 return {'source_commit':ref,'path':path,'mode':mode,'object_type':kind,'blob_oid':oid,'bytes':len(raw),'sha256':sha(raw)}
# Accepted routes and family record are independently validated from the evidence retained before checkout.
routes=parse((OUT/'accepted-routing-component-rows.json').read_bytes())
family=parse((OUT/'accepted-routing-family-record.json').read_bytes())
byid={r['component']:r for r in routes}
assert len(routes)==31 and len(byid)==31 and family['id']==FAMILY
assert sha(canonical(family))=='5b36a657c5e6d22de047d5d79deaf74bab32c7126f2039844ea97b0b5b6adcda'
# Restore 31 complete source component features from authenticated custody aliases.
successor=parse(git(CANDIDATE_COMMIT,'coordination/engineering/worldwide-successor-1215-20261006/run-one/report.json'))
component_descriptors=successor['complete_ancestor_products']['components']
custody=parse(git(CUSTODY_COMMIT,'coordination/engineering/physical-gap-components-1005-20261005-local19/custody-v1/index.json'))
aliases={a['original']['path']:a['payload'] for a in custody['aliases']}
components={};component_file_pins=[]
for d in component_descriptors:
 p=d['path']
 if p not in aliases: raise ValueError('missing custody alias '+p)
 raw=git(CUSTODY_COMMIT,aliases[p])
 assert len(raw)==d['bytes'] and sha(raw)==d['sha256']
 expanded=gzip.decompress(raw)
 assert len(expanded)==d['uncompressed_bytes'] and sha(expanded)==d['uncompressed_sha256']
 component_file_pins.append({'source_commit':CUSTODY_COMMIT,'original_path':p,'payload_path':aliases[p],'encoded_bytes':len(raw),'encoded_sha256':sha(raw),'decoded_bytes':len(expanded),'decoded_sha256':sha(expanded)})
 for f in parse(expanded).get('features',[]):
  if f.get('id') in byid:
   if f['id'] in components: raise ValueError('duplicate component '+f['id'])
   components[f['id']]=f
assert set(components)==set(byid)
for cid,f in components.items(): assert sha(canonical(f))==byid[cid]['current_feature_sha256'],cid
candidate_collection={'type':'FeatureCollection','features':[components[c] for c in sorted(components)]}
write_json('candidate-components.geojson',candidate_collection)
# Full physical rows and native source records, tied by original record hash.
phys_by_id={};physical_paths=sorted({r['whole_physical_containing_file'] for r in routes})
for p in physical_paths:
 raw=gzip.decompress(git(ROUTE_COMMIT,p))
 for line in raw.splitlines():
  row=parse(line);cid=row.get('component_id')
  if cid in byid:
   assert cid not in phys_by_id
   assert sha(canonical(row))==byid[cid]['whole_physical_row_sha256']
   phys_by_id[cid]=row
assert set(phys_by_id)==set(byid)
write_bytes('physical-query-rows.jsonl',b''.join(canonical(phys_by_id[c]) for c in sorted(phys_by_id)))
query_refs={}
for row in phys_by_id.values():
 for rel in row.get('query_relations',[]):
  sid=rel.get('source_id');h=rel.get('source_record_sha256')
  if sid and h: query_refs.setdefault(sid,set()).add(h)
source_base='coordination/engineering/global-physical-sources-20261006/run-one/'
source_report=parse(git(PHYSICAL_COMMIT,source_base+'report.json'))
desc={pathlib.PurePosixPath(x['path']).name:x for x in source_report['products']}
source_records={};record_pins=[];scanned=0
for i in range(18):
 name=f'records-{i:03}.jsonl.gz';d=desc[name];raw=git(PHYSICAL_COMMIT,source_base+name)
 assert len(raw)==d['bytes'] and sha(raw)==d['sha256']
 dec=gzip.decompress(raw);assert len(dec)==d['uncompressed_bytes'] and sha(dec)==d['uncompressed_sha256']
 record_pins.append({'source_commit':PHYSICAL_COMMIT,'path':source_base+name,'bytes':len(raw),'sha256':sha(raw),'decoded_bytes':len(dec),'decoded_sha256':sha(dec)})
 for line in dec.splitlines():
  r=parse(line);scanned+=1
  if r.get('id') in query_refs:
   if r['id'] in source_records: raise ValueError('duplicate native source record '+r['id'])
   source_records[r['id']]=r
assert set(source_records)==set(query_refs)
for sid,hs in query_refs.items():
 assert len(hs)==1 and next(iter(hs))==source_records[sid].get('record_sha256'),sid
assert len(source_records)==37
write_bytes('gshhg-native-query-records.jsonl',b''.join(canonical(source_records[s]) for s in sorted(source_records)))
# Restore all 15 numeric-first rows from the complete selected+complement diagnostic product.
numeric_path='coordination/engineering/complete-numeric-closure-diagnosis-20261007/scope.json.gz'
numeric_gzip=git(NUMERIC_COMMIT,numeric_path); assert len(numeric_gzip)==8610767 and sha(numeric_gzip)=='ada2db15a78524cd28c7a5f924df7bbe0fe616cdead91c429dd2c04384a156e9'; numeric_raw=gzip.decompress(numeric_gzip); numeric_scope=parse(numeric_raw); numeric_rows=numeric_scope['rows']; write_bytes('full-numeric-scope.json.gz',numeric_gzip)
# Provenance report / family accepted row determines the numeric-first identities; use membership in scope, not guessed tags.
selected_numeric=[r for r in numeric_rows if r.get('component_id') in byid]
if len(selected_numeric)!=15:
 selected_numeric=[r for r in numeric_rows if r.get('component') in byid]
assert len(selected_numeric)==15
assert len({r.get('component_id',r.get('component')) for r in selected_numeric})==15
write_bytes('numeric-closure-rows.jsonl',b''.join(canonical(r) for r in sorted(selected_numeric,key=lambda r:r.get('component_id',r.get('component')))))
write_json('accepted-routing-component-rows.json',routes)
write_json('accepted-routing-family-record.json',family)
# Complete consumed 2018 GeoBoundaries full-resolution and simplified feature records for the 3 exact contacts.
source_d='data/regional-review/regional-review-6fce33d53fdff81e/sources/geoboundaries-2018/geoBoundaries-USA-ADM2.geojson'
full_raw=git(FULL_SOURCE_COMMIT,source_d); assert len(full_raw)==10500644 and sha(full_raw)=='81fdd384df8012e5007ed2994a8ab306352f3c48e32cd8ea99182195e8647f43'
write_bytes('sources/geoboundaries-usa-adm2-full-whole-source.geojson',full_raw)
registry_raw=git(ADMIN_REGISTRY_COMMIT,'data/administrative-sources.json');assert len(registry_raw)==661416 and sha(registry_raw)=='ed0051d2956271c72f8917e7da0c6f53e5dfb595bee5920cac489a65a747d633';registry=parse(registry_raw);write_bytes('sources/administrative-sources.json',registry_raw)
catalogue_raw=git(SOURCE_CORPUS_COMMIT,'coordination/engineering/original-geography-source-corpus-20261006/catalogue.json');catalogue=parse(catalogue_raw);write_bytes('sources/source-corpus-catalogue.json',catalogue_raw)
catalogue_entry=next(p for p in catalogue['products'] if p['key']=='gb:USA:ADM2');assert catalogue_entry['metadata_sha256']==sha(json.dumps(registry['gb:USA:ADM2'],ensure_ascii=False,sort_keys=True,separators=(',',':')).encode())
full=parse(full_raw);full_by={f.get('properties',{}).get('shapeID'):f for f in full.get('features',[])}
simple_gzip=git(SOURCE_CORPUS_COMMIT,'coordination/engineering/original-geography-source-corpus-20261006/payloads/gb-USA-ADM2-000.bin.gz'); assert len(simple_gzip)==2476897 and sha(simple_gzip)=='fe2128f4a5c164c9a9f58a6321af446782f6a689e4d5d9452e5967047c1958c9'; write_bytes('sources/geoboundaries-usa-adm2-simplified-whole-source.bin.gz',simple_gzip)
simple_bytes=gzip.decompress(simple_gzip)
assert len(simple_bytes)==7938450 and sha(simple_bytes)=='16249e8d795aaded6a72910a8c72115a073814b25ee902d61ccc9a9490c6641a'
simple=parse(simple_bytes);simple_by={f.get('properties',{}).get('shapeID'):f for f in simple.get('features',[])}
ids=[c.rsplit(':',1)[1] for c in CONTACTS]
assert len(full_by)==3233 and len(simple_by)==3233
selected_full={i:full_by[i] for i in ids};selected_simple={i:simple_by[i] for i in ids}
assert all(i in selected_full and i in selected_simple for i in ids)
write_json('sources/geoboundaries-usa-adm2-full-contacts.geojson',{'type':'FeatureCollection','features':[selected_full[i] for i in ids]})
write_json('sources/geoboundaries-usa-adm2-simplified-contacts.geojson',{'type':'FeatureCollection','features':[selected_simple[i] for i in ids]})
for rel,commit,path in [('geoboundaries-usa-adm2-2018-metadata.json',BASELINE_COMMIT,'research/geography/gap-source-matanuska-physical-seam-20261006/sources/geoboundaries-usa-adm2-2018-metadata.json'),('individual-source-attribution.json',SOURCE_CORPUS_COMMIT,'coordination/engineering/original-geography-source-corpus-20261006/individual-source-attribution.json'),('CITATION-AND-USE-geoBoundaries-original.txt',SOURCE_CORPUS_COMMIT,'coordination/engineering/original-geography-source-corpus-20261006/CITATION-AND-USE-geoBoundaries-original.txt'),('GSHHG-LICENSE.TXT',PHYSICAL_COMMIT,'coordination/engineering/global-physical-sources-20261006/LICENSE.TXT'),('GSHHG-README.TXT',PHYSICAL_COMMIT,'coordination/engineering/global-physical-sources-20261006/README.TXT')]:
 write_bytes('sources/'+rel,git(commit,path))
# Load the already captured, immutable, byte-pinned Census TIGERweb source (no live fetch during rebuild).
tiger_receipt=parse((OUT/'sources/census-tigerweb-2026-retrieval.json').read_bytes())
endpoint=tiger_receipt['service_endpoint'];params=tiger_receipt['parameters'];url=tiger_receipt['request_url'];final_url=tiger_receipt['final_url'];status=tiger_receipt['http_status'];census_headers=tiger_receipt['headers']
census_raw=(OUT/'sources/census-tigerweb-2026-target-counties.geojson').read_bytes()
assert len(census_raw)==tiger_receipt['response_bytes'] and sha(census_raw)==tiger_receipt['response_sha256'] and status==200
census=parse(census_raw);assert len(census.get('features',[]))==3
census_by={f.get('properties',{}).get('GEOID'):f for f in census['features']}
assert set(census_by)=={'36059','36103','36119'}
layer_meta_url=tiger_receipt['layer_metadata_url'];layer_raw=(OUT/'sources/census-tigerweb-2026-layer-metadata.json').read_bytes();layer_headers=tiger_receipt['layer_metadata_headers']
assert len(layer_raw)==tiger_receipt['layer_metadata_bytes'] and sha(layer_raw)==tiger_receipt['layer_metadata_sha256']
layer_meta=parse(layer_raw)
# Exact source-copy of inherited #359 full issue body and its contract; roster extracted from current issue's scope JSON.
issue=parse((OUT/'sources/issue-359-current.json').read_bytes())
body=issue['body'];body_bytes=body.encode('utf-8')
write_bytes('sources/issue-359-full-body.md',body_bytes)
# Preserve the complete exact roster from the issue's embedded original scope contract.
contract_match=re.search(r'```(?:json)?\n(\{.*?\})\n```',body,re.S)
assert contract_match
issue_contract=parse(contract_match.group(1).encode())
member_ids=issue_contract['member_location_ids']
assert len(member_ids)==229 and len(set(member_ids))==229
assert sha('\n'.join(member_ids).encode())==issue_contract['member_location_ids_sha256']
write_json('sources/issue-359-scope-contacts.json',{'issue':359,'title':issue['title'],'state':issue['state'],'labels':issue.get('labels',[]),'updated_at':issue.get('updated_at'),'comment_count':issue.get('comments',0),'owned_evidence_path':'data/regional-review/regional-review-b96ac84bb73bd7ca/','body_bytes':len(body_bytes),'body_sha256':sha(body_bytes),'scope_subject_ids':member_ids,'scope_member_count':len(member_ids),'scope_member_ids_sha256':issue_contract['member_location_ids_sha256'],'target_contact_ids':CONTACTS,'target_contact_overlap_count':sum(i in member_ids for i in CONTACTS)})
assert all(i in member_ids for i in CONTACTS)
# Source geometry screen: no coordinate transform or repair. Preserve exact source and candidate shapes;
# predicates are only source-relative screens, not legal-boundary/dry-land conclusions.
from shapely.geometry import shape
full_g={i:shape(selected_full[i]['geometry']) for i in ids}
simple_g={i:shape(selected_simple[i]['geometry']) for i in ids}
census_g={f'census:{k}':shape(v['geometry']) for k,v in census_by.items()}
full_g={f'gb-full:{i}':g for i,g in full_g.items()};simple_g={f'gb-simplified:{i}':g for i,g in simple_g.items()}
admin={**full_g,**simple_g,**census_g}
ledger=[]
for cid in sorted(components):
 g=shape(components[cid]['geometry']); overlay={}
 for name,admin_geom in admin.items():
  inter=g.intersection(admin_geom)
  overlay[name]={'intersects':bool(g.intersects(admin_geom)),'covers_candidate':bool(admin_geom.covers(g)),'positive_planar_intersection':bool(inter.area>0),'intersection_area_degrees2':float(inter.area)}
 ledger.append({'component':cid,'current_feature_sha256':byid[cid]['current_feature_sha256'],'current_geometry_sha256':byid[cid]['current_geometry_sha256'],'candidate_bounds_lon_lat':list(g.bounds),'candidate_source_feature_sha256':sha(canonical(components[cid])),'physical_row_sha256':byid[cid]['whole_physical_row_sha256'],'physical_status':phys_by_id[cid].get('physical_status'),'physical_authority':phys_by_id[cid].get('physical_authority'),'physical_source_vintage':phys_by_id[cid].get('source_vintage'),'query_relation_count':len(phys_by_id[cid].get('query_relations',[])),'query_source_record_ids':[r.get('source_id') for r in phys_by_id[cid].get('query_relations',[])],'query_source_record_sha256':[r.get('source_record_sha256') for r in phys_by_id[cid].get('query_relations',[])],'query_relations':phys_by_id[cid].get('query_relations',[]),'route_next_prerequisite':byid[cid].get('next_prerequisite'),'route_unresolved':byid[cid].get('unresolved'),'numeric_closure_row':next((r for r in selected_numeric if r.get('component')==cid),None),'source_predicates':overlay,'classification':'source-history-unresolved; retain original candidate and defer processing/repair','recommendation':'Geography/source research: reconcile exact dated county boundary and processing provenance before any reproduction proposal. Engineering: retain unchanged source-relative evidence; no geometry edits on this packet.','reason':'Candidate footprint/source predicates and physical query evidence are preserved, but the consumed 2018 source is a derived product, official TIGER/Line 2018 archive exceeds the file cap, current 2026 TIGERweb is a later statistical boundary, and GSHHG is dated/heterogeneous and unapproved. No source can resolve legal boundary, land/water class, or a correction by itself.'})
# County-to-county comparison in a common equal-area CRS for scale context only; input shapes remain untouched.
project=Transformer.from_crs('EPSG:4326','EPSG:5070',always_xy=True).transform
county_comparisons=[]
for shapeid in ids:
 gbs=transform(project,full_g[f'gb-full:{shapeid}']);simp=transform(project,simple_g[f'gb-simplified:{shapeid}'])
 census_id={'52423323B42354579566723':'36059','52423323B61185146991898':'36103','52423323B83071826775288':'36119'}[shapeid]
 tig=transform(project,census_g[f'census:{census_id}'])
 def metric(a,b):
  union=a.union(b).area
  return {'iou':float(a.intersection(b).area/union) if union else None,'symmetric_difference_m2':float(a.symmetric_difference(b).area)}
 county_comparisons.append({'contact_id':'gb:USA:ADM2:'+shapeid,'census_geoid':census_id,'full_vs_simplified':metric(gbs,simp),'full_vs_tigerweb_2026':metric(gbs,tig),'simplified_vs_tigerweb_2026':metric(simp,tig),'interpretation':'Measured geometry difference only; does not establish legal boundary, history, land ownership, or correctness.'})
write_json('per-component-source-screen.json',{'version':1,'method':'Shapely 2.1.2 exact predicates in source lon/lat coordinates, no snapping, repair, clipping or tolerance. County-to-county IoU is measured after transform to EPSG:5070 via pyproj 3.7.2.','candidate_source':'current full-component roster restored from complete declared shards and matched by canonical source-feature SHA-256 to all accepted routing rows.','county_sources':['2018 geoBoundaries full-resolution, 2018 geoBoundaries simplified consumed product','2026 Census TIGERweb county service, exact TIGERweb outSR=4326 subset query'],'components':ledger,'contact_county_comparisons':county_comparisons,'conclusion':'Per-component source-fitness status remains unresolved; the overlays do not support dry-land, ownership, legal, or repair claims.'})
# Physical/query joins, numeric closure, source provenance and retrieval receipts.
write_json('sources/source-provenance.json',{
 'administrative_sources_registry':{'source_commit':ADMIN_REGISTRY_COMMIT,'bytes':len(registry_raw),'sha256':sha(registry_raw),'product_record_canonical_sha256':sha(json.dumps(registry['gb:USA:ADM2'],ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()),'catalogue_metadata_sha256':catalogue_entry['metadata_sha256']},
 'geoBoundaries_original_metadata_json':{'source_commit':BASELINE_COMMIT,'path':'research/geography/gap-source-matanuska-physical-seam-20261006/sources/geoboundaries-usa-adm2-2018-metadata.json','bytes':939,'sha256':sha((OUT/'sources/geoboundaries-usa-adm2-2018-metadata.json').read_bytes())},
 'consumed_geoBoundaries_simplified':{'source_commit':SOURCE_CORPUS_COMMIT,'retrieved_url':'https://github.com/wmgeolab/geoBoundaries/raw/9469f09592ced973a3448cf66b6100b741b64c0d/releaseData/gbOpen/USA/ADM2/geoBoundaries-USA-ADM2_simplified.geojson','decoded_bytes':len(simple_bytes),'decoded_sha256':sha(simple_bytes),'feature_count':len(simple['features']),'represented_year':'2018','source_data_update_date':'2023-01-19','build_date':'2023-12-12','source':'United States Census Bureau, MAF/TIGER Database','metadata_license_statement':'Public Domain','distribution_terms':'geoBoundaries release terms separately state CC-BY 4.0 attribution; do not conflate these statements or infer beyond their text.','feature_extract_sha256':sha(canonical({'type':'FeatureCollection','features':[selected_simple[i] for i in ids]}))},
 'geoBoundaries_full_resolution':{'source_commit':FULL_SOURCE_COMMIT,'path':source_d,'bytes':len(full_raw),'sha256':sha(full_raw),'feature_count':len(full['features']),'represented_year':'2018','upstream':'United States Census Bureau, MAF/TIGER Database','metadata_license_statement':'Public Domain','feature_extract_sha256':sha(canonical({'type':'FeatureCollection','features':[selected_full[i] for i in ids]}))},
 'census_tigerweb_2026':{'endpoint':endpoint,'url':url,'final_url':final_url,'http_status':status,'retrieved_at_utc':tiger_receipt['retrieved_at_utc'],'response_bytes':len(census_raw),'response_sha256':sha(census_raw),'content_type':census_headers.get('Content-Type'),'last_modified':census_headers.get('Last-Modified'),'query_parameters':params,'feature_count':len(census['features']),'source_vintage':layer_meta.get('description'),'native_service_spatial_reference':layer_meta.get('sourceSpatialReference'),'requested_output_spatial_reference':'EPSG:4326','exact_geoids':['36059','36103','36119'],'source':'U.S. Census Bureau TIGERweb; no separate feature-level license statement was returned in the captured layer metadata; U.S. federal work status is recorded as provenance context, not as a license opinion.'},
 'census_tigerline_2018_access_attempt':{'url':'https://www2.census.gov/geo/tiger/TIGER2018/COUNTY/tl_2018_us_county.zip','method':'HTTP HEAD (access/size preflight; no large body downloaded)','status':200,'content_length_bytes':79219478,'last_modified':'Tue, 18 Sep 2018 02:48:13 GMT','limit':'79,219,478 bytes exceeds 32 MiB per-file retention cap; exact 2018 primary TIGER/Line archive could not be retained under the packet limit. A state-only archive URL returned HTTP 404; Census distributes this vintage here as the national county ZIP.'},
 'census_tigerline_2025_access_attempt':{'url':'https://www2.census.gov/geo/tiger/TIGER2025/COUNTY/tl_2025_us_county.zip','method':'HTTP HEAD (access/size preflight; no large body downloaded)','status':200,'content_length_bytes':83989800,'last_modified':'Tue, 23 Sep 2025 02:15:55 GMT','limit':'83,989,800 bytes exceeds 32 MiB per-file retention cap. The contemporaneous #954 packet independently retains the whole-archive URL, byte count, and SHA-256, but contains no target-county extracted records.'},
 'physical_candidate_source':{'source_commit':PHYSICAL_COMMIT,'product':'GSHHG 2.3.7','release_date':'2017-06-15','observation_dates':'heterogeneous / not established for these records','authority':'unapproved','archive_bytes':118617033,'archive_sha256':'28600e8f7a08645aab43079326df6504212ec5ccb2b4bcf3b5f4f12ed60e82bc','native_binary_member_bytes':95809336,'native_binary_member_sha256':'af9215d58ebc525b2d09654a89959829f09e6edc457f3666759cded37be4ecf6','license_text_conflict':'Source LICENSE says LGPL v3 or later; distributed README says LGPL v3 or earlier. Preserve the conflict; do not resolve by inference.','per_record_metadata_rows':len(source_records),'record_source_roster_sha256':sha(b''.join(canonical(source_records[s]) for s in sorted(source_records))),'all_37_exact_record_sha_matches':True,'limits':['whole archive and source binary exceed 32 MiB per-file cap','source-relative support does not resolve shoreline/channel registration','river widths, seasonal wetness and exact observation dates remain unknown','no dry-land, legal, or ownership authority']}
})
# Complete retained evidence source pins (including raw bytes and canonical extraction pins).
write_json('source-pins.json',{
 'accepted_family_record':{'source_file':'scratch/accepted-family-route-record.json','canonical_sha256':sha(canonical(family)),'family':FAMILY},
 'accepted_component_rows':{'source_file':'scratch/accepted-component-route-rows.json','count':len(routes),'canonical_sha256':sha(canonical(routes))},
 'current_candidate_component_roster':{'feature_count':len(components),'canonical_feature_sha256_match_count':sum(sha(canonical(components[c]))==byid[c]['current_feature_sha256'] for c in byid),'component_ancestor_shards':component_file_pins},
 'physical_rows':{'count':len(phys_by_id),'route_source_commit':ROUTE_COMMIT,'physical_row_source_paths':physical_paths,'extracted_file':sha((OUT/'physical-query-rows.jsonl').read_bytes())},
 'gshhg_native_record_rows':{'count':len(source_records),'query_record_hash_match_count':len(source_records),'source_commit':PHYSICAL_COMMIT,'all_18_source_file_descriptors':record_pins},
 'numeric_scope':{'source_commit':NUMERIC_COMMIT,'path':numeric_path,'decoded_bytes':len(numeric_raw),'decoded_sha256':sha(numeric_raw),'extracted_target_row_count':len(selected_numeric),'encoded_bytes':len(numeric_gzip),'encoded_sha256':sha(numeric_gzip),'full_retained_path':'full-numeric-scope.json.gz','full_decoded_rows':len(numeric_rows),'complete_selected_count':len(numeric_rows),'exact_complement_count':len(numeric_scope['complement_ids'])},
 'source_corpus_simplified':{'source_commit':SOURCE_CORPUS_COMMIT,'compressed_sha256':'fe2128f4a5c164c9a9f58a6321af446782f6a689e4d5d9452e5967047c1958c9','decoded_sha256':sha(simple_bytes),'decoded_bytes':len(simple_bytes)},
 'geoBoundaries_full_source':{'source_commit':FULL_SOURCE_COMMIT,'bytes':len(full_raw),'sha256':sha(full_raw)},
 'census_tigerweb_2026_subset':{'bytes':len(census_raw),'sha256':sha(census_raw),'retrieval_receipt_path':'sources/census-tigerweb-2026-retrieval.json'},
 'issue_359':{'body_bytes':len(body_bytes),'body_sha256':sha(body_bytes),'target_contacts_in_scope':3,'scope_member_count':len(member_ids),'comments':0}
})
# Retain the exact upstream reports and custody index as immutable source-reference files.
upstream_files=[
 ('routing-report.json',ROUTE_COMMIT,'coordination/engineering/global-actionability-routing-20261007/results/report.json'),
 ('numeric-diagnosis-report.json',NUMERIC_COMMIT,'coordination/engineering/complete-numeric-closure-diagnosis-20261007/r2/report.json'),
 ('physical-comparison-report.json',ROUTE_COMMIT,'coordination/engineering/global-physical-comparison-20261006/results/report.json'),
 ('physical-source-run-report.json',PHYSICAL_COMMIT,'coordination/engineering/global-physical-sources-20261006/run-one/report.json'),
 ('candidate-successor-report.json',CANDIDATE_COMMIT,'coordination/engineering/worldwide-successor-1215-20261006/run-one/report.json'),
 ('candidate-custody-index.json',CUSTODY_COMMIT,'coordination/engineering/physical-gap-components-1005-20261005-local19/custody-v1/index.json'),
]
upstream_pin_list=[]
for name,commit,path in upstream_files:
 raw=git(commit,path);upstream_pin_list.append({'path':'sources/upstream/'+name,'source_commit':commit,'source_path':path,'bytes':len(raw),'sha256':sha(raw)});write_bytes('sources/upstream/'+name,raw)

# General quantitative manifest, tied to exact target source IDs and workspace claim.
subject_hash=sha(('\n'.join(CONTACTS)+'\n').encode())
base_files=[
 {'path':'coordination/engineering/global-actionability-routing-20261007/results/report.json','source_commit':ROUTE_COMMIT,'sha256':'2bf401f76aabc30cb9f0120aba958545146ebf37e304d8817d15eed800fa5265','role':'routing and family context'},
 {'path':'coordination/engineering/complete-numeric-closure-diagnosis-20261007/r2/report.json','source_commit':NUMERIC_COMMIT,'sha256':'6a56174de64aee619130282a2fe63db58bed51e7c8d8d0c8d3f4f10045eddb3914','role':'complete numeric diagnosis report'},
 {'path':'coordination/engineering/global-physical-comparison-20261006/results/report.json','source_commit':ROUTE_COMMIT,'sha256':'2a5b59198681d50f577bc4c2c321174f166aec14f57c7564100fc411ae940df0','role':'physical comparison report'},
 {'path':'coordination/engineering/global-physical-sources-20261006/run-one/report.json','source_commit':PHYSICAL_COMMIT,'sha256':'b90334b4a836604049eb268604f090f686400147e4747dd12bd2ea1d698b497c','role':'physical source extraction report'},
]
manifest={'version':1,'issue':1377,'lane':'geography','worker_id':'01a11550-a19b-7330-955c-e56e90985bf3','claim_id':'ebb0dbbd-c2a5-4baf-8625-3a82030ce801','branch':'geography/usa31-gap-family-source-fitness-20261007','subject_ids':CONTACTS,'subject_ids_sha256':subject_hash,'component_count':31,'baseline':{'commit':'839883ae281af7bf012f694698624a7ec77275e1','files':base_files},'evidence':{'candidate_feature_count':31,'current_feature_hash_matches':31,'physical_query_row_count':31,'native_source_record_count':37,'numeric_closure_target_row_count':15,'contact_products':['2018 geoBoundaries full-resolution','2018 geoBoundaries simplified','2026 Census TIGERweb'], '2018_primary_tiger_retained':False,'2018_archive_size_bytes':79219478,'2025_primary_tiger_retained':False,'2025_archive_size_bytes':83989800,'source_review_dispositions':'undetermined for all 31; full uncertainty retained'},'pins':{'consumed_source_payload_file':'fe2128f4a5c164c9a9f58a6321af446782f6a689e4d5d9452e5967047c1958c9','source_metadata_file':'ed0051d2956271c72f8917e7da0c6f53e5dfb595bee5920cac489a65a747d633','source_attribution_file':'7d8a3baf61f32e6e4398f24bec0d15bce32eafcd4309655edc2b12a2c33256bd','routing_report_file':'2bf401f76aabc30cb9f0120aba958545146ebf37e304d8817d15eed800fa5265','numeric_diagnosis_report_file':'6a56174de64aee619130282a2fe63db58bed51e7e1c0d8d3c8f4f10045eddb3914','numeric_scope_file':'ada2db15a78524cd28c7a5f924df7bbe0fe616cdead91c429dd2d04384a156e9','physical_comparison_report_file':'2a5b59198681d50f577bc4c2c321174f166aec14f57c7564100fc411ae940df0','physical_source_run_report_file':'b90334b4a836604049eb268604f090f686400147e4747dd12bd2ea1d698b497c','candidate_custody_index_file':'dfcca9fe2bb64805b94e784be89b3523f5683b95cbd4a617283965ca6187a77c','collision_issue_359_snapshot_body':sha(body_bytes)},'review_kind':'source','source_descriptors':{'source_blobs':[git_blob(ADMIN_REGISTRY_COMMIT,'data/administrative-sources.json'),git_blob(SOURCE_CORPUS_COMMIT,'coordination/engineering/original-geography-source-corpus-20261006/payloads/gb-USA-ADM2-000.bin.gz'),git_blob(SOURCE_CORPUS_COMMIT,'coordination/engineering/original-geography-source-corpus-20261006/catalogue.json'),git_blob(SOURCE_CORPUS_COMMIT,'coordination/engineering/original-geography-source-corpus-20261006/individual-source-attribution.json'),git_blob(SOURCE_CORPUS_COMMIT,'coordination/engineering/original-geography-source-corpus-20261006/CITATION-AND-USE-geoBoundaries-original.txt'),git_blob(FULL_SOURCE_COMMIT,source_d),git_blob(PHYSICAL_COMMIT,'coordination/engineering/global-physical-sources-20261006/LICENSE.TXT'),git_blob(PHYSICAL_COMMIT,'coordination/engineering/global-physical-sources-20261006/README.TXT'),git_blob(NUMERIC_COMMIT,numeric_path),git_blob(NUMERIC_COMMIT,'coordination/engineering/complete-numeric-closure-diagnosis-20261007/r2/report.json'),git_blob(ROUTE_COMMIT,'coordination/engineering/global-actionability-routing-20261007/results/report.json'),git_blob(ROUTE_COMMIT,'coordination/engineering/global-physical-comparison-20261006/results/report.json'),git_blob(PHYSICAL_COMMIT,source_base+'report.json'),git_blob(CUSTODY_COMMIT,'coordination/engineering/physical-gap-components-1005-20261005-local19/custody-v1/index.json')],
 'candidate_shards':component_file_pins,'gshhg_source_records':record_pins}}
write_json('evidence-quality.json',manifest)
print(json.dumps({'components':len(components),'physical_rows':len(phys_by_id),'native_records':len(source_records),'numeric_rows':len(selected_numeric),'contacts':ids,'census_features':len(census_by),'census_sha256':sha(census_raw),'issue359_scope_member_count':len(member_ids),'all_outputs_under_32MiB':all(p.stat().st_size<32*1024*1024 for p in OUT.rglob('*') if p.is_file())},indent=2))
