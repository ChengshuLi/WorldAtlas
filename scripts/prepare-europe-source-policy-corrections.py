"""Prepare source-role overlays; never modify geography, base policy or claims."""
import argparse,collections,gzip,hashlib,json,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=ROOT/'data/source-policy-corrections/europe-v1.json.gz'
DOC=ROOT/'docs/SOURCE_POLICY_CORRECTIONS.md'
OWNERS={'ITA':'Italy','ESP':'Spain','XKX':'Kosovo'}
ROLES={
 'italy-labour-system':{'role':'Local labour system (ISTAT SLL 2011/2018)','level':'Published functional commuting territory','type':'functional-labour-system'},
 'spain-agricultural-district':{'role':'MAPA agricultural district adaptation','level':'Published agricultural comarca adapted to retained whole-location membership','type':'agricultural-district-adaptation'},
 'spain-municipality':{'role':'Municipality territory','level':'Retained source municipal territory','type':'municipality'},
 'kosovo-district':{'role':'Named source district territory','level':'Seven named source district footprints','type':'administrative-district'},
}

def read(p):return json.loads(gzip.decompress(p.read_bytes())if str(p).endswith('.gz')else p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def object_sha(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def build(extra):
 index=read(ROOT/'data/world-index.json');paths=['data/world-index.json','data/hierarchy.json','data/location-policy.json','data/geographic-semantic-followup/europe.json.gz','data/semantic-sources.json','data/framework-sources/manifest.json','data/administrative-sources.json']+['data/'+p for p in index['parts']]
 pins={p:sha(ROOT/p)for p in paths};original=(ROOT/'data/location-policy.json').read_bytes();base=json.loads(original);features=[f for p in index['parts']for f in read(ROOT/'data'/p)['features']];hierarchy=read(ROOT/'data/hierarchy.json');units={u['id']:u for u in hierarchy};review=read(ROOT/'data/geographic-semantic-followup/europe.json.gz');evidence=review['source_evidence'];annotations=[];counts=collections.Counter();country_members=collections.defaultdict(list)
 for f in features:
  p=f['properties'];iso=next((i for i,o in OWNERS.items()if p['reference_owner']==o),None)
  if not iso:continue
  m=p['metadata'];source=m.get('source_id','')
  if iso=='ITA':assert source.startswith('ISTAT:SLL2011-2018:');kind='italy-labour-system';proof=['italy-current-source-properties','italy-retained-published-geography']
  elif iso=='XKX':assert source=='gb:XKX:ADM1'and p['name'].startswith('District of ');kind='kosovo-district';proof=['kosovo-original-pinned-geojson','kosovo-source-metadata-contradiction']
  elif m.get('location_basis')=='MAPA agricultural district; separately mapped major cities excluded':assert m['source_url']=='https://sig.mapa.gob.es/arcgis/rest/services/25830/comunComarcasAgrarias/MapServer/2';kind='spain-agricultural-district';proof=['spain-mapa-official-layer','spain-retained-public-snapshot']
  else:assert source=='gb:ESP:ADM3'and m['source_role']=='MUNICIPIOS';kind='spain-municipality';proof=['spain-municipality-source-metadata']
  counts[kind]+=1;chain=[];u=units[p['parent_id']]
  while u:chain.append(u['id']);u=units.get(u['parent_id'])
  role=ROLES[kind];before={key:m.get(key)for key in ['source_id','source_name','source_url','source_role','administrative_level','location_basis','reference_year','license']};after={'effective_source_role':role['role'],'effective_source_level':role['level'],'effective_role_type':role['type'],'source_policy_correction_id':'source-policy:europe-v1:'+iso,'source_id':m.get('source_id'),'source_url':m.get('source_url'),'reference_year':m.get('reference_year'),'license':m.get('license'),'status':'source-role-corrected-semantic-open','local_granularity_approved':False}
  annotations.append({'location_id':f['id'],'profile_iso':iso,'classification':kind,'footprint_sha256':object_sha(f['geometry']),'current_metadata_sha256':object_sha(m),'parent_chain':chain,'continent_id':chain[-1],'before_annotation':before,'after_annotation':after,'evidence_ids':proof});country_members[iso].append(f)
 assert dict(counts)=={'italy-labour-system':610,'spain-agricultural-district':341,'spain-municipality':43,'kosovo-district':7}
 observed=extra['italy_properties'].get('observed_json',{});assert not observed.get('exceededTransferLimit');properties=[row['attributes']for row in observed['features']];codes={str(row['sll_2011_t'])for row in properties};current_codes={f['properties']['metadata']['source_id'].rsplit(':',1)[-1]for f in country_members['ITA']};assert len(properties)==len(codes)==610 and codes==current_codes
 assert extra['italy_count']['observed_json']['count']==610
 xkx_properties=evidence['xkx_public_geometry']['observed_feature_properties'];assert len(xkx_properties)==7;source_shape_ids={r['shapeID']for r in xkx_properties};assert source_shape_ids=={f['properties']['metadata']['original_id']for f in country_members['XKX']}
 policies=[]
 definitions={
 'ITA':('Local labour systems (ISTAT SLL 2011/2018)','Published functional commuting territories','All 610 installed Italian locations are published local labour systems. Province/metropolitan-city administrative geometry remains separate parent-crosswalk evidence; whole functional membership may cross those borders.','https://maps.regione.umbria.it/server/rest/services/Hosted/Sistemi_Locali_del_Lavoro_2011_2018/FeatureServer',['italy-current-source-properties','italy-retained-published-geography']),
 'ESP':('MAPA agricultural district adaptations and retained municipality territories','Mixed agricultural/municipal local reference territories','Current Spanish reference locations comprise 341 named MAPA agricultural district adaptations with separately mapped major cities excluded, plus 43 retained municipality territories across all continents. Agricultural geography does not prove a complete settlement envelope.','https://sig.mapa.gob.es/arcgis/rest/services/25830/comunComarcasAgrarias/MapServer/2',['spain-mapa-official-layer','spain-retained-public-snapshot','spain-municipality-source-metadata']),
 'XKX':('Named source districts (seven district footprints)','Named source district territories','The pinned original source has seven named District of ... polygons. Municipality/48-unit API metadata does not describe that actual footprint inventory; this correction concerns source role, not legal status or fully reviewed location scale.',base['countries']['XKX']['source_url'],['kosovo-original-pinned-geojson','kosovo-source-metadata-contradiction']),
 }
 for iso in OWNERS:
  before=base['countries'][iso];role,level,reason,url,proof=definitions[iso];after={**before,'role':role,'reason':reason,'source_url':url,'effective_level':level,'retained_administrative_selection':before.copy()};rows=[r for r in annotations if r['profile_iso']==iso];policies.append({'id':'source-policy:europe-v1:'+iso,'profile_iso':iso,'before_policy':before,'after_policy':after,'location_ids':sorted(r['location_id']for r in rows),'role_counts':dict(collections.Counter(r['classification']for r in rows)),'continent_counts':dict(collections.Counter(units[r['continent_id']]['name']for r in rows)),'evidence_ids':proof,'effective_from':None,'temporal_meaning':'Undated reference-source description correction; no historical effective date is invented','semantic_complete':False})
 sources={
  'italy-current-source-properties':{'request_receipts':extra,'inspected_fact':'Queried all 610 source code/name rows without geometry and verified an exact code bijection with every installed Italian SLL identity. Count query also reports 610. This is source-role evidence, not footprint or city completeness approval.'},
  'italy-retained-published-geography':{'manifest_path':'data/framework-sources/manifest.json','manifest_sha256':pins['data/framework-sources/manifest.json'],'source':next(s for s in read(ROOT/'data/framework-sources/manifest.json')['sources']if s['path']=='italy-sll2018.geojson'),'inspected_fact':'Committed source manifest pins the published SLL2011/2018 geography; every active location retains its source hash, source URL and functional location basis.'},
  'spain-mapa-official-layer':evidence['official_requests']['spain_mapa'],
  'spain-retained-public-snapshot':{'manifest_path':'data/semantic-sources.json','manifest_sha256':pins['data/semantic-sources.json'],'source_files':[f for f in read(ROOT/'data/semantic-sources.json')['files']if f['path'].startswith('spain-')],'restore_command':'python scripts/semantic-sources.py','inspected_fact':'Retained MAPA layer and named comarca polygons support agricultural-functional source intent; original municipality-to-comarca memberships remain separate preserved preparation evidence.'},
  'spain-municipality-source-metadata':evidence['policy_metadata']['ESP'],
  'kosovo-original-pinned-geojson':evidence['xkx_public_geometry'],
  'kosovo-source-metadata-contradiction':evidence['policy_metadata']['XKX'],
 }
 proposals=[]
 for aid,owner,proof in [('framework:area:france:a85924a668ef','Monaco','Monaco Statistics inspected reference identity'),('framework:area:belgium:3a14f80912de','Luxembourg','GISCO 2024 Luxembourg country label')]:
  group=units[aid];members=[]
  for f in features:
   parent=f['properties']['parent_id'];chain=[]
   while parent:chain.append(parent);parent=units[parent]['parent_id']
   if aid in chain:members.append(f)
  assert len(members)==1 and members[0]['properties']['reference_owner']==owner;member=members[0];fp=object_sha(member['geometry']);group_hash=hashlib.sha256(json.dumps([[member['id'],fp]],separators=(',',':')).encode()).hexdigest();source=evidence['official_requests']['monaco']if owner=='Monaco'else{'request':evidence['official_requests']['nuts_labels'],'observed_labels':[r for r in evidence['official_labels']if r['iso3']=='LUX'and r['level']==0]}
  proposals.append({'id':'source-policy:europe-v1:area-label:'+owner.lower(),'entity_id':aid,'before_group':group,'proposed_patch':{'name':owner},'unchanged_parent_id':group['parent_id'],'member_location_ids':[member['id']],'member_province_ids':[member['properties']['parent_id']],'member_reference_names':[member['properties']['name']],'group_footprint_sha256':group_hash,'location_footprint_sha256':fp,'source_proof':source,'inspected_fact':proof+'; exact sole-member location/province correspondence is verified separately in the current hierarchy.','status':'proposed-not-installed','geometry_changed':False,'parent_changed':False,'identity_changed':False,'temporal_names_changed':False,'granularity_exception_approved':False})
 result={'version':1,'id':'source-policy:europe-v1','reviewed_at':'2026-10-01','purpose':'Sourced undated reference-role overlays; original policy and all geometry, identities, hierarchy and historical evidence remain immutable','input_sha256':pins,'producer_sha256':sha(pathlib.Path(__file__)),'retained_base_policy':{'path':'data/location-policy.json','sha256':pins['data/location-policy.json'],'raw_utf8':original.decode()},'policy_corrections':policies,'location_annotations':sorted(annotations,key=lambda r:r['location_id']),'source_evidence':sources,'area_label_proposals':proposals,'counts':{'policy_corrections':len(policies),'locations':len(annotations),'roles':dict(counts),'area_label_proposals':len(proposals)},'geography_changed':False,'claims_changed':False,'base_policy_rewritten':False,'semantic_complete':False,'unsupported_candidates_left_open':['Canonical Unknown and collection-name gbOpen source roles elsewhere need independent taxonomy before correction','Norway/Estonia/Ukraine vintage and all location granularity decisions are distinct migration/research tasks','Compact-territory source roles are not approved solely from area or a single owner label']}
 assert pins=={p:sha(ROOT/p)for p in paths},'Input changed during preparation';return result

def doc(d):return '''# Sourced source-policy corrections

Reviewed 1 October 2026. The original `data/location-policy.json` remains byte-identical. A sourced overlay corrects reference-role descriptions for every conclusively identified Europe profile, including Spanish locations outside Europe. It does not alter geographic identity, geometry, membership, temporal names or historical attributes.

| Profile | Correct effective role | All current locations | Source proof |
| --- | --- | ---: | --- |
| Italy | Published ISTAT local labour systems (2011 geography, 2018 update) | 610 | Every current SLL source code matches the official SIAT code registry; independent count query reports 610. The retained source geography hash is unchanged. |
| Spain | MAPA agricultural district adaptations plus retained municipalities | 384: 341 agricultural, 43 municipal | Official MAPA layer explicitly describes Comarcas Agrarias and province/comarca fields. Municipality metadata remains separate. Europe-only counts are 333+39; the correction includes the other 12 locations. |
| Kosovo | Seven named source district territories | 7 | Actual pinned original GeoJSON has seven District of ... features with exact current source-ID correspondence. The metadata's Municipalities/48-unit claim is retained as contradictory source metadata. |

`data/source-policy-corrections/europe-v1.json.gz` contains complete before/after policy objects, all 1,001 stable location IDs with source-role crosswalks and unchanged footprint/metadata/parent hashes, byte-exact original policy text, fresh/retained source receipts and two stable-ID area-label proposals. Supported source roles do not certify consistent location scale or complete cities/islands; every branch remains semantically open.

## Effective-policy lookup

`src/source-policy-corrections.js` exports `effectiveSourcePolicies(basePolicy, correctionBundle)` and `correctedLocationSourceRole(locationId, correctionBundle)`. Python review scripts can import `effective_source_policies(base, bundle)` or `load_effective_source_policies()` from `scripts/source_policy_corrections.py`; Python/JavaScript parity is tested. The resolver returns a new policy object and never mutates its input. It accepts only the recorded original or already-corrected policy entry; an unrelated policy edit requires a new reviewed correction. Application/global-review consumers should use the returned effective policy and its correction evidence, preserving `retained_administrative_selection` as original context. The legacy `level` remains the selected administrative source layer; `effective_level` describes the actual installed role and must be used for atlas-role presentation. An ADM integer is not an atlas tier.

The full bundle is a durable research artifact. Static coverage can use a bounded projection of its `policy_corrections` and keyed location annotations; it should not expose all raw source receipts in the main location panel. Root integration consumes the overlay separately from the frozen geographic input files. The UI/database/content separation remains intact.

## Stable-ID label proposals

- `framework:area:france:a85924a668ef`: proposed reference name **Monaco**. Current member/province inventory contains only Monaco; Monaco Statistics corroborates that reference identity.
- `framework:area:belgium:3a14f80912de`: proposed reference name **Luxembourg**. Current member/province inventory contains only Luxembourg; GISCO identifies Luxembourg independently of Belgium.

Both proposals preserve original complete group objects, member IDs, footprint hashes, parent IDs and source proof. They are **not installed**. They do not approve coextensive tiers or compact-territory granularity, and they do not rename historical entities at invented dates. A later reviewed hierarchy migration must preserve the original labels/evidence and regenerate the appropriate hierarchy-dependent assets.

## Validate or regenerate

```sh
python scripts/prepare-europe-source-policy-corrections.py --check
python test/europe-source-policy-corrections.py
node --test test/source-policy-corrections.test.mjs
```

The producer reuses the embedded official source observations on a fresh clone. A new factual retrieval can be supplied with `--observations path/to/receipts.json`; changed sources need new receipts and explicit review. It never writes base policy, geography, hierarchy, prepared attributes or historical records. Its input hashes and every ID/footprint classification are rechecked before producing the overlay.
'''

def main():
 p=argparse.ArgumentParser();p.add_argument('--observations',type=pathlib.Path);p.add_argument('--check',action='store_true');args=p.parse_args();extra=read(args.observations)if args.observations else read(OUT)['source_evidence']['italy-current-source-properties']['request_receipts'];d=build(extra)
 if args.check:assert read(OUT)==d,'Source-policy correction bundle changed';assert DOC.read_text()==doc(d),'Source-policy docs changed'
 else:OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_bytes(gzip.compress(json.dumps(d,ensure_ascii=False,separators=(',',':')).encode(),mtime=0));DOC.write_text(doc(d))
 print(json.dumps({'counts':d['counts'],'sha256':sha(OUT),'bytes':OUT.stat().st_size,'base_policy_unchanged':True,'geography_changed':False,'semantic_complete':False}))
if __name__=='__main__':main()
