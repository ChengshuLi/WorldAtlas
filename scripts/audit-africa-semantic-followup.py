#!/usr/bin/env python3
"""Inventory current Africa semantics; network metadata is evidence, never approval.
Only writes the new Africa follow-up ledger/document. --fetch refreshes source
metadata read-only; the default reuses its already retained response evidence.
No active geography, historical claim, prepared asset or older review is changed.
"""
import argparse,collections,gzip,hashlib,json,pathlib,re,statistics,urllib.request,urllib.parse,concurrent.futures,datetime,html,io
ROOT=pathlib.Path(__file__).resolve().parents[1]
D=ROOT/'data'; OUT=D/'geographic-semantic-followup/africa.json.gz'; DOC=ROOT/'docs/semantic-followup/AFRICA.md'
def read(p):
 p=ROOT/p
 return json.load(gzip.open(p,'rt') if p.suffix=='.gz' else open(p))
def sha(p):return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
def digest(x):return hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
# Country-specific review decisions: source date is a reference, not current law.
NOTES={
'AGO':'Municipalities are plausible rural/city territories; province-sized urban municipality footprints and the 2018 source versus later administrative reforms must be reconciled. Do not infer the new province/municipality memberships from an old layer.',
'BDI':'Communes are local administrative territories; retain the 2007 source vintage explicitly and verify the later province/commune reorganisation before presenting current membership. Bujumbura city subdivisions need a complete city crosswalk.',
'BEN':'Communes give local rural territories; Cotonou, Porto-Novo and other urban communes need whole-city extent review. Department parents must be separately proved, not selected because ADM1 is adjacent.',
'BFA':'The pinned canonical role is Unknown. Verify each of the 351 named units against department/commune identities and urban subdivisions; neither ADM3 nor the count proves the role. Later regional/provincial reforms also prevent a 2007 current-administration claim.',
'BWA':'Subdistricts mix rural districts and urban coverage; broad named physical subdivisions can be retained only with source membership proof. Gaborone/Francistown and remote reserve territories need distinct purpose checks.',
'CAF':'Commune/municipality footprints are candidate local territories; distinguish Bangui urban arrondissements from complete rural communes and check the 2018 source against administrative changes. Province clusters need a named parent crosswalk.',
'CIV':'The selected 510-unit layer is labelled Departments in metadata even though its declared ADM3 level can suggest another role. Verify feature identities against departments/subprefectures before relabelling or importing. Abidjan urban land needs a full-city review.',
'CMR':'Unknown canonical ADM3 role cannot certify arrondissement/commune equivalence. Verify municipal rural territories and the subdivisions of Douala/Yaounde; preserve an explicit role ambiguity until names and full footprints are matched.',
'COD':'Territories and cities are distinct legitimate local purposes; consolidate constituent urban subdivisions only on complete named-city evidence. The inspected finer candidate metadata/geometry disagreement is a blocker, not a reason to replace 189 footprints.',
'COG':'Unknown canonical source role requires district/commune identity crosswalks, including Brazzaville and Pointe-Noire. Broad rural departmental remnants cannot be approved from area alone.',
'COM':'The active single Comoros footprint combines multiple islands. A compact-country exception has not established one coherent local territory across Grande Comore, Anjouan and Moheli; separate named island/city geography is a concrete review requirement. Mayotte stays independently crosswalked.',
'CPV':'The 22 Unknown-role source units need municipality identity verification. Municipalities can provide local territories, while island groups supply meaningful province/area alternatives. Repeated municipality/province names do not prove distinct tier roles.',
'DJI':'Districts are candidate local territories but Djibouti-city subdivisions and sparse interior districts require different purpose checks; administrative regions alone do not establish province clusters.',
'DZA':'Commune-level local territories are plausible, but the selected source must be distinguished from wilaya/delegated-wilaya reforms. Verify urban commune fragmentation and every physical desert subdivision, including all source-parent mismatches.',
'EGY':'Marakiz are rural centres while aqsam can be police/urban districts. Whole-city membership, Cairo/Alexandria governorate exceptions, Nile/desert transitions and Sinai continent placement need feature-specific crosswalks; the mixed role cannot be certified globally.',
'ERI':'Districts are candidate local territories; inspect Asmara urban subdivisions and sparsely populated desert/coastal districts, then verify six-zoba parent roles and offshore island completeness.',
'ETH':'The canonical ADM3 role is Unknown. Match each footprint to woreda/special-woreda or urban subcity evidence; Addis Ababa aggregation is a regression case, not approval of all 680 locations. Regional reforms and detached source pieces stay open.',
'GAB':'Departments can provide rural local territories; Libreville, Port-Gentil and urban communes require complete-city evidence. Province-level administrative parents are not automatically atlas province clusters.',
'GHA':'Districts include metropolitan/municipal/district assemblies with different urban purposes. Audit Accra/Kumasi agglomerations and the 2019 source against subsequent assembly/region changes before certifying neighbouring units.',
'GIN':'Prefectures are too broad to presume local purpose in inhabited areas. The 340-subprefecture candidate is a concrete finer lead, but urban communes, Conakry and complete northern/coastal land coverage must be verified before migration.',
'GMB':'Rural districts and the Banjul independent-city exception have different purposes. Verify Kanifing/Serekunda city coverage and coastal islands; the source governorate hierarchy may repeat tiers without distinct clusters.',
'GNB':'Sector-level units are plausible rural territories, but canonical Unknown requires a sector identity crosswalk. Bissau city and the Bijagos archipelago need complete urban/island membership verification.',
'GNQ':'Districts need an independent identity crosswalk because canonical source role is Unknown. Annobon/Bioko/mainland grouping, Malabo/Bata city extents and missing sub-cell islands must all be checked.',
'KEN':'Sub-counties provide rural local candidates; the Nairobi national-capital aggregation needs a full footprint crosswalk, and Mombasa/Kisumu/other urban sub-counties require equal scrutiny. Counties may support province clusters after semantic evidence.',
'LBR':'Districts are candidate local territories with variable settlement purpose; Monrovia and county-versus-district city distinctions must be audited. Islands/coastal clipping and weak parents remain per-ID open.',
'LBY':'ADM1 districts are broad and desert-dominated; the physical subdivisions need named geographic evidence rather than target area. Municipal/baladiya and city footprints are needed for populated coastal land; unavailable finer gbOpen layers do not justify closure.',
'LSO':'Ten districts are broad administrative regions rather than automatically local territories. Research community/urban councils and their complete rural partition, with Maseru coherent-city coverage and meaningful district clusters.',
'MAR':'Province/prefecture boundaries are broad populated units. Research rural communes and whole-city footprints; separate Western Sahara reference geography from ownership/claims. Finer administrative levels need licensed complete geometry and urban role classification.',
'MDG':'Districts are plausible rural territories but inhabited highland/coastal scale and Antananarivo urban extent require finer commune/city evaluation. Madagascar offshore islands and named regional parents need explicit verification.',
'MLI':'Cercle/physical territories are broad. The 701-commune candidate is a concrete lead; Bamako subdivisions, northern complete land coverage and later administrative reforms must be resolved before replacing source identities.',
'MOZ':'Districts mix rural and city-purpose territories. Verify Maputo/Matola and provincial-city equivalents, coastal islands and source coverage before choosing location/province roles.',
'MRT':'Canonical role Mauritania does not identify a tier. Verify moughataa/commune names, Nouakchott urban coverage and the named physical desert subdivisions; a count or ADM2 label cannot establish semantic approval.',
'MUS':'Districts and Outer Islands is a mixed source role. Districts can fragment the Port Louis urban system; Rodrigues/Agalega/Cargados Carajos require named-island roles and representation checks. Territorial claims remain ownership evidence, not geographic parent logic.',
'MWI':'Districts are broad populated territories; verify city councils and a complete traditional-authority/local partition before deciding if districts are locations or province clusters. Lake shoreline and island land must be tested.',
'NAM':'All 111 active IDs retain the documented source-quality block. The staged 107-constituency candidate is not installed; overlap/coverage and coast restoration remain acceptance blockers. Evidence and exact IDs are retained in the Namibia dossier; do not repeat a metadata-only approval.',
'NER':'Communes are candidate rural territories, but urban arrondissement/commune groupings and Niamey need coherent-city evidence. Named Saharan subdivisions and 2012 versus later reforms stay separately reviewed.',
'NGA':'Local government areas have a supported administrative role, but Lagos/Abuja/Kano agglomerations can span multiple LGAs. Verify full-city geography and each northern rural purpose; a nationally standard LGA name is not whole-city approval.',
'RWA':'Districts are administrative local candidates with Kigali already aggregated. Audit all remaining districts and urban centres consistently, preserving city aggregation evidence and rural-sector alternatives where needed.',
'SDN':'District/locality identities and urban Khartoum subdivisions require independent crosswalks. Sparse desert subdivisions, land in disputed envelopes and source vintages need separate administrative/physical decisions.',
'SEN':'Departments are relatively broad populated units; examine communes/arrondissements and coherent Dakar urban geography before approving local tier roles. The 2019 layer does not automatically express later reforms.',
'SLE':'The old 14 districts are broad. The 165-chiefdom candidate needs complete Western Area/Freetown urban coverage and later district/chiefdom changes; chiefdom geometry is a local-purpose lead, not automatic replacement.',
'SOM':'Districts cross Somalia/Somaliland reference envelopes. Geographic clipping and all fragments need explicit identity/crosswalk proof; claims and sovereign owner fields cannot create separate geographic regions. Mogadishu/Hargeisa city coverage is open.',
'SSD':'Counties are plausible sparse rural territories. Juba/other city subdivisions and the 2020 versus later county changes require dated source context; physical expansions and source land coverage remain explicit.',
'STP':'Two Unknown-role units represent main islands rather than demonstrated local administrative districts. Island-level province geography is plausible, but finer named district/city territories need research; a tiny-country exception cannot approve repeated tiers.',
'SWZ':'Inkhundla/tinkhundla are constituency/administrative units; verify their geographic local purpose and later count changes rather than equate electoral function with a settlement territory. Mbabane/Manzini city coherence remains open.',
'SYC':'Regions may describe island/physical groupings rather than districts. The eight selected units need individually sourced purpose, Victoria/Mahe urban coverage and complete Outer Islands membership; minimum cell coverage is not a semantic reason to merge.',
'TCD':'Departments/physical desert subdivisions need different purposes. Broad departments can be appropriate sparse territory only with evidence; Ndjamena and inhabited southern units require coherent local/city review and reform crosswalks.',
'TGO':'Prefectures are broader than many inhabited local territories. Research the newer commune partition and Lome urban grouping, verifying rural land coverage before migrating prefectures to province clusters.',
'TUN':'Delegations are plausible rural/city administrative territories but canonical Unknown means role verification is necessary. Tunis/Sfax/Sousse urban subdivisions, islands and weak geographic parent matches all remain open.',
'TZA':'Districts include rural councils and urban municipal/city councils. Verify Dar es Salaam and other urban constituents, the distinct Zanzibar system and islands; newer district creation requires a reference-vintage crosswalk.',
'UGA':'The selected ADM3 layer explicitly declares District, illustrating why level numbers are unsuitable. Verify district/city boundaries, Kampala and city creation/reforms; research subcounty alternatives without importing urban wards indiscriminately.',
'ZAF':'Local municipalities provide rural territorial purpose but metropolitan municipalities and cities spanning municipal land need feature identity verification. Traditional/rural subdivisions and named district-parent groupings require independent evidence.',
'ZMB':'Districts are plausible rural candidates with broad sparse footprints; Lusaka/Copperbelt urban city coherence and source-vintage district creation must be audited. Province groups need local-cluster roles beyond administrative labels.',
'ZWE':'Districts and the Bulawayo city exception need consistent urban/rural classification. Verify Harare/other cities, rural district versus urban council envelopes and source clipping with exact identity crosswalks.',
'ESP':'Only African Canaries/Ceuta/Melilla members are assessed here. MAPA agricultural districts and named municipalities have distinct functional roles; keep every source/member crosswalk and verify whole-island/city coverage. Mainland Spain is outside this batch.',
'PRT':'Only Madeira/African associated islands are assessed here; municipalities are plausible local territories but island subdivisions and whole-city Funchal geography need evidence. Azores association belongs to the separate macro-boundary decision, not political ownership.',
'YEM':'Only Socotra-associated African locations are assessed here. District geography and named islands must be crosswalked independently of Yemeni political ownership; mainland Yemen is outside this batch.',
'FRA':'Only Reunion/Mayotte-associated African land is assessed here. Natural Earth named territory fallbacks need a compact-island exception or licensed local/city geography; mainland French arrondissement evidence does not approve these islands.',
'NOR':'Only Bouvet-associated land is assessed here. The uninhabited remote volcanic island is a physical-location candidate, but association with Africa is an explicit convention requiring justification, not owner-based continental placement.',
}
MACRO_NOTES={
'Africa':'The mainland Africa/Sinai division is physical/conventional and must be evaluated independently of Egyptian ownership. Remote Atlantic/Indian/subantarctic islands need an explicit association convention; Norway/France/Yemen ownership cannot justify their continent. Antarctica remains excluded.',
'Central Africa':'Central African macro-zone may be justified by the Congo basin and adjacent equatorial geography. The inherited botanical/political reference envelopes are insufficient to prove the basin/divide perimeter or every outlying island association.',
'Western Africa':'West African macro-zone has a regional geographical role distinct from political ownership. Sahel/coastal transitions and eastern margins need exact location membership evidence, rather than extrapolation from a national reference envelope.',
'Southern Africa':'Southern African macro-zone includes both southern mainland and South Tropical Africa reference regions. Their distinct geographic role must be reconciled with Central/Eastern Africa; Botswana/Namibia desert physical subdivisions are not automatically boundaries of the macro-zone.',
'Northern Africa':'North African macro-zone is mainland Mediterranean/Sahara geography plus the stated Macaronesian association. Sahara/Sahel and Nile/Sinai boundaries need physical/member evidence; Atlantic volcanic islands are an explicit association convention.',
'Eastern Africa':'Eastern mainland and Horn geography is represented through East/Northeast Tropical Africa. Rift/Horn/Sudan-Sahel transitions need physical/regional rationale rather than a country-to-region lookup.',
'Indian Ocean Islands':'Named western Indian Ocean island association is a useful reporting convention, but isolated subantarctic islands and Socotra need individually documented placement. Country sovereignty cannot determine membership.',
'Atlantic Islands':'Atlantic island association combines Middle/South Atlantic reference zones. Volcanic island identity can justify local units; a very wide ocean envelope needs explicit archipelago association rather than contiguous mainland assumptions.',
'West-Central Tropical Africa':'Congo basin/equatorial West-Central Africa is a plausible geographical scope. The Angola/Cabinda/Gulf of Guinea margins and islands require explicit named physical associations; botanical source purposes do not approve all local children.',
'West Tropical Africa':'Coastal West Africa and Sahel share this inherited reference region. Verify its geographic purpose and transition to Sahara and Congo/Horn geography; a common owner or national admin boundary cannot decide its perimeter.',
'Southern Africa':'Southern Africa reference region should express southern mainland geography separately from the South Tropical region. Mountain/desert/coastal transitions and small-state co-membership need evidence. The repeated subcontinent/region label is an open tier-role question.',
'Macaronesia':'Canaries/Madeira/Cape Verde share a named Atlantic biogeographical association. Azores placement remains the separately documented Europe/Africa convention. Ceuta/Melilla are mainland African territory, not volcanic archipelago members; inspect exact area membership.',
'Northeast Tropical Africa':'Horn and northeast tropical geography has a coherent macro-role; Sudan/Horn/Rift transitions and Socotra placement require exact association evidence. Somalia/Somaliland political envelopes cannot define separate regions.',
'East Tropical Africa':'East African Rift/lake/coastal geography is a plausible region. Mainland versus Zanzibar/offshore island membership and the transition to Southern/Central Africa must be assessed by physical scope.',
'Western Indian Ocean':'Madagascar, Mascarene, Comoro and Seychelles associations give named geographic island clusters. Each detached/remote island needs exact membership; sovereign country lists do not certify geographic area/province roles.',
'South Tropical Africa':'Inherited South Tropical Africa is a botanical macro-region with broad Angola/Zambia/Mozambique-associated scope. Its role relative to southern mainland, Congo basin and East Africa needs a documented physical/reference convention, not count-based regrouping.',
'South Atlantic Islands':'St Helena/Ascension/Tristan-associated islands are named South Atlantic groups. Their widely separated ocean association is an explicit conventional exception; preserve named archipelagos and justify placement individually.',
'Middle Atlantic Ocean':'The inherited oceanic region must identify its actual islands and physical associations. Ocean reference extent alone cannot approve land parents or a Bouvet/subantarctic African association.',
}
def fetch_job(job):
 url=job['url']; result={**job,'retrieved_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 try:
  req=urllib.request.Request(url,headers={'User-Agent':'WorldAtlas geographic semantic audit (public source research)'})
  with urllib.request.urlopen(req,timeout=28) as r: raw=r.read();result['http_status']=r.status
  result['sha256']=hashlib.sha256(raw).hexdigest()
  if job.get('format')=='text':
   text=raw.decode('utf-8',errors='replace'); text=re.sub(r'<(script|style)\b.*?</\1>',' ',text,flags=re.S|re.I)
   text=html.unescape(re.sub(r'<[^>]+>',' ',text));text=re.sub(r'\s+',' ',text).strip()
   result['text_excerpt']=text[:16000];result['excerpt_truncated']=len(text)>16000;result['status']='source-text-inspected'
  else:result['response']=json.loads(raw);result['status']='metadata-inspected'
 except Exception as e:
  result['status']='unavailable';result['failure']=str(e)[:220]
 return result

def main():
 args=argparse.ArgumentParser();args.add_argument('--fetch',action='store_true');opt=args.parse_args()
 h=read('data/hierarchy.json'); ix={x['id']:x for x in h}; root=next(x['id'] for x in h if x['level']=='continent' and x['name']=='Africa')
 def chain(pid):
  out=[]
  while pid:out.append(pid);pid=ix[pid]['parent_id']
  return out
 groups=[x for x in h if root in chain(x['id'])]; gids={x['id'] for x in groups}
 w=read('data/world-review.json'); review={x['id']:x for p in w['location_parts'] for x in read('data/'+p)}
 fs=[]; part_hashes={}
 for part in read('data/world-index.json')['parts']:
  chosen=[f for f in read('data/'+part)['features'] if f['properties']['parent_id'] in gids]
  if chosen:fs.extend(chosen);part_hashes['data/'+part]=sha('data/'+part)
 policy=read('data/location-policy.json')['countries']; admin=read('data/administrative-sources.json'); old=read('data/geographic-decisions/africa.json'); gran=read('data/granularity-review-evidence.json')
 quality_path='data/namibia-source-quality-annotations.json';quality=read(quality_path)
 quality_locs={x['id']:i for i,x in enumerate(quality['feature_annotations'])};quality_groups={x['id']:i for i,x in enumerate(quality['group_annotations'])}
 watched_paths=['data/hierarchy.json','data/world-review.json','data/world-index.json','data/location-policy.json','data/administrative-sources.json','data/geographic-decisions/africa.json','data/granularity-review-evidence.json',quality_path]+list(part_hashes)
 initial_hashes={p:sha(p) for p in watched_paths}
 flags={f['id']:f for t in gran['territories'] for f in t['flagged_locations']}; profiles=sorted({review[f['id']]['iso'] for f in fs if review[f['id']]['iso'] in policy})
 old_response={x['key']:x for x in read(str(OUT.relative_to(ROOT))).get('source_research',[]) } if OUT.exists() else {}
 jobs=[]
 for iso in profiles:
  p=policy[iso];url=p.get('source_url','');collection='gbHumanitarian' if 'gbHumanitarian' in url else 'gbOpen'
  for level,reason in [(p['level'],'selected-role-comparison'),('ADM'+str(int(p['level'][3:])+1),'finer-role-candidate')]:
   if int(level[3:])>5:continue
   key=iso+':'+collection+':'+level;jobs.append({'key':key,'iso':iso,'collection':collection,'level':level,'scope':reason,'url':f'https://www.geoboundaries.org/api/current/{collection}/{iso}/{level}/'})
 if opt.fetch:
  with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
   for n,x in enumerate(pool.map(fetch_job,jobs),1):old_response[x['key']]=x;print(f"source {n}/{len(jobs)} {x['key']} {x['status']}",flush=True)
 research=[old_response.get(j['key'],{**j,'status':'not-retrieved'}) for j in jobs]
 upstream_jobs=[]
 for iso in profiles:
  upstream_jobs.append({'key':'hdx:cod-ab-'+iso.lower(),'iso':iso,'scope':'upstream-humanitarian-source-assessment','url':'https://data.humdata.org/api/3/action/package_show?id=cod-ab-'+iso.lower()})
  for item in research:
   if item['iso']!=iso or item['scope']!='selected-role-comparison' or item['status']!='metadata-inspected':continue
   u=item['response'].get('boundarySourceURL','')
   if u and 'data.humdata.org/dataset/' not in u:
    upstream_jobs.append({'key':'upstream:'+iso,'iso':iso,'scope':'selected-layer-upstream-source','url':u if u.startswith(('https://','http://')) else 'https://'+u,'format':'text'})
 upstream_jobs.extend([
  {'key':'macro:un-m49','scope':'continent-subcontinent-reference','url':'https://unstats.un.org/unsd/methodology/m49/overview/','format':'text'},
  {'key':'macro:wgsrpd','scope':'region-area-reference-purpose','url':'https://raw.githubusercontent.com/tdwg/wgsrpd/master/README.md','format':'text'},
  {'key':'macro:africa-physical','scope':'continent-physical-geography','url':'https://education.nationalgeographic.org/resource/africa-physical-geography/','format':'text'}])
 previous_upstream={x['key']:x for x in read(str(OUT.relative_to(ROOT))).get('upstream_source_research',[])} if OUT.exists() else {}
 if opt.fetch:
  with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
   for n,x in enumerate(pool.map(fetch_job,upstream_jobs),1):previous_upstream[x['key']]=x;print(f"upstream {n}/{len(upstream_jobs)} {x['key']} {x['status']}",flush=True)
 upstream_research=[previous_upstream.get(j['key'],{**j,'status':'not-retrieved'}) for j in upstream_jobs]
 source_ids=collections.defaultdict(list); owner_ids=collections.defaultdict(list); province_ids=collections.defaultdict(list)
 locrows=[]
 for f in sorted(fs,key=lambda f:f['id']):
  p=f['properties']; m=p.get('metadata',{}); r=review[f['id']]; sid=m.get('source_id'); srciso=r['iso'];source_ids[srciso].append(f['id']);owner_ids[r['owner']].append(f['id']);province_ids[p['parent_id']].append(f['id'])
  oldidx=r.get('review_decision',{});locrows.append({'id':f['id'],'name':p['name'],'owner_reference':r['owner'],'profile_iso':srciso if srciso in policy else None,'reference_iso':srciso,'parent_id':p['parent_id'],'parent_chain':chain(p['parent_id']),'geometry_sha256':digest(f['geometry']),'source_id':sid,'source_url':m.get('source_url'),'role':m.get('location_basis') or m.get('location_source_role') or m.get('source_role'),'declared_role':m.get('source_role'),'source_year':m.get('reference_year') or m.get('location_source_date'),'license':m.get('license'),'area_km2':r['area_km2'],'flags':flags.get(f['id'],{}).get('reasons',[]),'semantic_status':'open','existing_decision':oldidx or None})
 lmap={x['id']:x for x in locrows}; children=collections.defaultdict(list)
 for row in locrows:
  if row['id'] in quality_locs:row['source_quality_block']={'status':'pending-source-replacement','evidence_file':quality_path,'annotation_index':quality_locs[row['id']],'integration_status':quality['status'],'not_applied_by_this_audit':True}
 for g in groups:
  if g['parent_id']:children[g['parent_id']].append(g['id'])
 for p,ids in province_ids.items():children[p].extend(ids)
 def descendants(pid):
  out=[]
  for c in children[pid]:
   if c in lmap:out.append(c)
   else:out.extend(descendants(c))
  return out
 tier={'continent':'Mainland and explicitly justified physical island associations; excludes Antarctica.','subcontinent':'Country-independent macro-geographic zone or explicitly documented island association.','region':'Country-independent coherent macro-geography, with physical/conventional perimeter evidence.','area':'Broader named physical/administrative grouping; political ownership alone is insufficient.','province':'Named cluster of local territories with distinct purpose; avoid a duplicate envelope without justification.'}
 group_rows=[]
 for g in sorted(groups,key=lambda g:(['continent','subcontinent','region','area','province'].index(g['level']),g['id'])):
  ids=descendants(g['id']);md=g.get('metadata',{});sr=md.get('semantic_review',{});reasons=list(dict.fromkeys(md.get('review_reasons',[])+sr.get('remaining_reasons',[])))
  if g['level']=='subcontinent' and g['name']=='Southern Africa':
   macro_assessment='Southern African macro-zone contains Southern Africa and South Tropical Africa regions; the distinct southern mainland/tropical transition and parent scope need physical/reference rationale, independently of country ownership.'
  elif g['level']=='region' and g['name']=='Northern Africa':
   macro_assessment='Mediterranean/Saharan mainland Africa contains Algerian, Tunisian, Egyptian, Libyan, Moroccan and Western Saharan reference areas, plus Ceuta/Melilla. Verify the Sahara/Sahel and Nile/Sinai perimeters physically; disputed ownership cannot determine geography.'
  else:macro_assessment=MACRO_NOTES.get(g['name'])
  own_supported=sr.get('boundary_status')=='supported'
  group_rows.append({'id':g['id'],'name':g['name'],'level':g['level'],'parent_id':g['parent_id'],'children':sorted(children[g['id']]),'child_names':[ix[c]['name'] if c in ix else lmap[c]['name'] for c in sorted(children[g['id']])],'descendant_location_count':len(ids),'membership_sha256':digest(sorted(ids)),'tier_role':tier[g['level']],'current_basis':md.get('basis'),'current_source':md.get('source'),'current_source_url':md.get('source_url'),'record_sha256':digest(g),'source_boundary_assessment':sr.get('boundary_status','open'),'source_boundary_supported':own_supported,'branch_semantic_status':'open','followup_assessment':macro_assessment if g['level'] in ['continent','subcontinent','region'] else 'The exact child membership, named source-role rationale and recorded own-boundary evidence are inventoried. Whole-city/local-purpose and complete detached/island membership evidence are still required for branch approval.','reasons':reasons or ['Local purpose, coherent settlement extent and complete named-island coverage require independent evidence; absence of a machine flag does not close this branch.'],'existing_evidence':sr.get('evidence',[])})
  if g['id'] in quality_groups:group_rows[-1]['source_quality_block']={'status':'contains-pending-source-review','evidence_file':quality_path,'annotation_index':quality_groups[g['id']],'not_applied_by_this_audit':True}
 prows=[]
 for iso in profiles:
  ids=source_ids[iso];p=policy[iso];a=admin.get(f'gb:{iso}:{p["level"]}',{});rs=[x for x in research if x['iso']==iso]; roles=collections.Counter(lmap[i]['role'] or 'unspecified' for i in ids)
  upstream=[x for x in upstream_research if x.get('iso')==iso]
  hdx=next((x['response'].get('result',{}) for x in upstream if x['key'].startswith('hdx:') and x['status']=='metadata-inspected'),{})
  notes=hdx.get('notes',''); declarations=[{'level':'ADM'+level,'count':int(count),'declared_role':role.strip(),'method':'literal publisher metadata, not reconciled to active or official identities'} for level,count,role in re.findall(r'^\s*-\s*Admin\s+([1-5]):\s*(\d+)\s*([^\n]*)',notes,re.M)]
  if not declarations:
   declarations=[{'level':'ADM'+level,'count':int(count.replace(',','')),'declared_role':'Not verified: inspect the original metadata type sentence','method':'literal publisher feature count'} for level,count in re.findall(r'Administrative level\s+([1-5]) contains\s+([\d,]+) feature',notes)]
  source_cautions=[]
  for pattern,code in [(r'partial coverage','publisher-declares-incomplete-lower-tier'),(r'health zone|health district','lower-tier-has-health-service-function'),(r'protected areas|protected-area','nonadministrative-protected-area-extensions'),(r'NOT been reviewed','publisher-declares-no-recent-review'),(r'currently not known','publisher-role-ambiguity')]:
   if re.search(pattern,notes,re.I):source_cautions.append(code)
  if iso=='STP' and notes:source_cautions.append('publisher-tier-label-conflict: seven ADM1 Province versus note two provinces and seven districts')
  candidate=next((x['response'] for x in rs if x['scope']=='finer-role-candidate' and x['status']=='metadata-inspected'),{})
  candidate_role=candidate.get('boundaryCanonical','')
  # A finer layer may be electoral, village-scale or unnamed: no automatic tier selection.
  candidate_assessment=('not-an-automatic-location-partition: ward/constituency/village-scale requires distinct local-purpose proof' if re.search(r'ward|constituenc|collin',candidate_role,re.I) else 'named-local-role-candidate-needs-complete-geometry-and-city-crosswalk' if candidate_role and candidate_role.lower() not in ['unknown','gbopen','mauritania'] else 'unresolved-role-or-unavailable')
  prows.append({'iso':iso,'location_ids':sorted(ids),'location_count':len(ids),'reference_owners':sorted({lmap[i]['owner_reference'] for i in ids}),'policy':p,'pinned_metadata':a,'active_roles':dict(roles),'source_research_keys':[x['key'] for x in rs],'upstream_research_keys':[x['key'] for x in upstream],'upstream_declared_administration':{'title':hdx.get('title'),'notes':hdx.get('notes'),'license_title':hdx.get('license_title'),'dataset_date':hdx.get('dataset_date'),'interpretation':'Publisher metadata, not independent official administrative validation; conflicts with layer labels or current law remain open.'} if hdx else None,'finer_candidate_assessment':candidate_assessment,'assessment':NOTES.get(iso,'This source profile requires a country-specific identity, local purpose and settlement extent crosswalk before closure.'),'decision':'retain-active-reference-pending-evidence','semantic_status':'open','required_checks':['Exact original-source member identity and declared geographic role','Complete named city extent and rural local purpose','Named province/area membership and distinct adjacent-tier roles','Detached components, coastal/island completeness and relative neighboring scale','Source vintage, downstream license obligations and full replacement crosswalk']})
  prows[-1]['publisher_tier_declarations']=declarations
  prows[-1]['source_cautions']=source_cautions
  prows[-1]['location_flag_counts']=dict(collections.Counter(flag for i in ids for flag in lmap[i]['flags']))
  prows[-1]['source_policy_assessment_completed']=iso in NOTES
 fallback=[]
 for iso in sorted(set(source_ids)-set(profiles)):
  ids=source_ids[iso];fallback.append({'reference_iso':iso,'location_ids':sorted(ids),'owners':sorted({lmap[i]['owner_reference'] for i in ids}),'semantic_status':'open','assessment':NOTES.get(iso,'No dedicated source-policy profile. Each named fallback territory needs a sourced physical/local role and explicit compact/remote exception; membership completeness is not proof of semantic granularity.'),'source_urls':sorted({lmap[i]['source_url'] for i in ids if lmap[i]['source_url']})})
 # Specific named-tier proposals remain drafts, never changes to active IDs.
 proposals=[]
 for iso in ['COM','STP','SLE','GIN','MLI','LSO','MAR','MWI','TGO','SYC','MDG','MOZ','UGA']:
  ids=source_ids.get(iso,[])
  if not ids:continue
  proposals.append({'id':'africa-followup:'+iso.lower()+':local-role-review','affected_location_ids':sorted(ids),'affected_province_ids':sorted({lmap[i]['parent_id'] for i in ids}),'action':'propose-source-backed-local-partition' if iso not in ['COM','SYC'] else 'reassess-named-island-local-partition','rationale':NOTES[iso],'candidate_source_keys':[x['key'] for x in research if x['iso']==iso and x['scope']=='finer-role-candidate' and x['status']=='metadata-inspected'],'migration_status':'not-staged','acceptance':'No new ID or merge/split is authorized by metadata. Require complete geometry, named member crosswalk, urban/rural purpose, source license, original-record preservation and coverage proof.'})
 closure=read('data/global-semantic-closure.json') if (D/'global-semantic-closure.json').exists() else {}
 result={'version':1,'continent':'Africa','status':'exhaustive-current-inventory-and-source-policy-followup-semantic-open','semantic_complete':False,'generated_at':'2026-10-02','scope':'Every currently Africa-parented location and geographic ancestor; owner labels and policies are independently crosswalked. No active geometry or historical evidence is modified.','audit_order':['continent','subcontinent','region','area','province','location'],'input_sha256':{**{p:sha(p) for p in ['data/hierarchy.json','data/world-review.json','data/world-index.json','data/location-policy.json','data/administrative-sources.json','data/geographic-decisions/africa.json','data/granularity-review-evidence.json']},**part_hashes},'summary':{'locations':len(locrows),'groups':len(groups),'tiers':dict(collections.Counter(g['level'] for g in groups)),'reference_owners':len(owner_ids),'policy_profiles':len(prows),'fallback_reference_isos':len(fallback),'source_metadata_inspected':sum(x['status']=='metadata-inspected' for x in research),'source_metadata_unavailable':sum(x['status']=='unavailable' for x in research),'source_metadata_not_retrieved':sum(x['status']=='not-retrieved' for x in research),'locations_with_flags':sum(bool(x['flags']) for x in locrows),'location_flags':dict(collections.Counter(y for x in locrows for y in x['flags'])),'branch_semantic_open':len(groups),'location_semantic_open':len(locrows)},'inventory_delta_from_frozen_africa_review':{'old_location_count':old.get('inspection',{}).get('valid_current_polygons'),'old_group_count':len(old['inventory']['group_ids']),'current_location_count':len(locrows),'current_group_count':len(groups),'previous_group_ids_not_current':sorted(set(old['inventory']['group_ids'])-gids),'current_group_ids_not_previous':sorted(gids-set(old['inventory']['group_ids']))},'tier_roles':tier,'groups':group_rows,'locations':locrows,'source_policy_assessments':prows,'fallback_assessments':fallback,'reference_owner_crosswalk':[{'owner':o,'location_ids':sorted(ids),'profile_isos':sorted({lmap[i]['profile_iso'] for i in ids if lmap[i]['profile_iso']}),'fallback_reference_isos':sorted({lmap[i]['reference_iso'] for i in ids if not lmap[i]['profile_iso']})} for o,ids in sorted(owner_ids.items())],'source_research':research,'proposed_changes':proposals,'limits':['All current IDs are inventoried; no automatic semantic approval follows from complete membership or a licensed source.','Fresh metadata characterizes source-declared roles, vintage and license; it does not constitute inspection of every candidate source polygon or official current administration.','Existing pinned source assessments and per-location screening are preserved by reference, with current hash and membership reconciliation.','All branch and location semantic decisions remain open until feature-specific city/local-purpose/island/parent evidence and required migration proofs exist.','No active data or historical records were changed; no candidate IDs have been invented.']}
 result['upstream_source_research']=upstream_research
 result['summary']['profiles_with_source_cautions']=sum(bool(p['source_cautions']) for p in prows)
 result['summary']['source_policy_assessments_completed']=sum(p['source_policy_assessment_completed'] for p in prows)
 result['summary']['locations_with_source_quality_blocks']=sum('source_quality_block' in row for row in locrows)
 result['summary']['groups_with_source_quality_blocks']=sum('source_quality_block' in row for row in group_rows)
 result['summary']['upstream_responses_inspected']=sum(x['status'] in ['metadata-inspected','source-text-inspected'] for x in upstream_research)
 result['summary']['upstream_responses_unavailable']=sum(x['status']=='unavailable' for x in upstream_research)
 assert len(lmap)==len(locrows);assert len({x['id'] for x in group_rows})==len(group_rows);assert all(len(x['parent_chain'])==5 and x['parent_chain'][-1]==root for x in locrows)
 assert len(quality_locs)==len(set(quality_locs)&set(lmap)), 'Existing source-quality IDs must be reconciled; no partial annotation inventory.'
 assert all(p['source_policy_assessment_completed'] for p in prows)
 assert all(sha(p)==expected for p,expected in initial_hashes.items()), 'Atlas changed during review; rerun before publishing a mixed snapshot.'
 result['input_sha256']=initial_hashes
 assert sum(len(x['location_ids']) for x in prows+fallback)==len(locrows);assert sum(len(x['location_ids']) for x in result['reference_owner_crosswalk'])==len(locrows)
 OUT.parent.mkdir(parents=True,exist_ok=True); compressed=io.BytesIO()
 with gzip.GzipFile(fileobj=compressed,mode='wb',filename='',mtime=0) as handle:handle.write((json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode())
 OUT.write_bytes(compressed.getvalue())
 lines=['# Africa semantic follow-up','',f"Current pinned scope: **{len(locrows):,} locations, {len(groups):,} parent groups, {len(owner_ids)} reference-owner labels and {len(prows)} source-policy profiles**. Every current ID appears in the companion JSON, with an exact parent chain, source/geometry hashes and retained open decisions.",'','This is an exhaustive current inventory and a country-specific source-policy review, **not completed semantic approval of every location**. All branch/local purpose, city extent and named-island completeness reviews remain open. No active geography, dated claim, grid or earlier evidence ledger was changed.','', '## Top-down coverage','', '| Tier | Current units | Decision scope |','| --- | ---: | --- |']
 for level in ['continent','subcontinent','region','area','province']:
  lines.append(f"| {level.title()} | {result['summary']['tiers'].get(level,0):,} | {tier[level]} All branches remain open. |")
 lines+= [f'| Location | {len(locrows):,} | Source roles, vintage, stable IDs, footprint hashes, exact five-parent chain and all available machine flags. Local purpose remains open. |','', '## Regional batches','', '| Subcontinent | Region | Areas | Provinces | Locations |','| --- | --- | ---: | ---: | ---: |']
 for g in sorted((x for x in groups if x['level']=='region'),key=lambda x:x['name']):
  down=[x for x in groups if g['id'] in chain(x['id'])]; cnt=collections.Counter(x['level'] for x in down)
  lines.append(f"| {ix[g['parent_id']]['name']} | {g['name']} | {cnt['area']} | {cnt['province']} | {len(descendants(g['id'])):,} |")
 lines+=['','## Country-specific policy decisions','', 'Counts below cover only Africa-parented locations, including associated islands of transcontinental/reference owner groups. A country-wide owner count is never substituted for the Africa batch count. Metadata and candidate links are retained in the JSON with retrieval status, full successful response and response checksum. Unavailable endpoints remain recorded as failures.','', '| Profile | Africa locations | Active role(s) | Review decision |','| --- | ---: | --- | --- |']
 for p in prows:lines.append('| '+ ' | '.join([p['iso'],str(p['location_count']),'; '.join(f'{k}: {v}' for k,v in p['active_roles'].items()),p['assessment']]).replace('|', '|')+' |')
 lines+=['','## Inspected source references','', '| Profile | Selected source | Upstream evidence | Candidate role decision |','| --- | --- | --- | --- |']
 for p in prows:
  upstream=next((x for x in upstream_research if x.get('iso')==p['iso'] and x['key'].startswith('hdx:')),None)
  description=f"[OCHA/HDX metadata]({upstream['url']}) — {upstream['status']}" if upstream else 'No OCHA/HDX response retained'
  lines.append(f"| {p['iso']} | [Pinned layer]({p['policy'].get('source_url','')}) | {description} | {p['finer_candidate_assessment']} |")
 lines+=['','## Publisher role, completeness and vintage conflicts','', 'These are source-contract findings. Current publisher feature counts, pinned geometry counts and atlas location counts are different inventories. Differences require member crosswalks; counts alone do not authorize replacements.','', '| Profile | Published tier inventory | Cautions |','| --- | --- | --- |']
 for p in prows:
  if p['publisher_tier_declarations'] or p['source_cautions']:
   claims='; '.join(f"{d['level']}: {d['count']} {d['declared_role']}" for d in p['publisher_tier_declarations'])
   lines.append(f"| {p['iso']} | {claims} | {'; '.join(p['source_cautions']) or 'No named caution extracted; this does not certify the source or descendants.'} |")
 lines+=['','## Reference/fallback groups without a dedicated policy','', '| Reference ISO | Locations | Owners | Review decision |','| --- | ---: | --- | --- |']
 for f in fallback:lines.append(f"| {f['reference_iso']} | {len(f['location_ids'])} | {', '.join(f['owners'])} | {f['assessment']} |")
 lines+=['','## Evidence and what remains','',f"Fresh source research: {result['summary']['source_metadata_inspected']} inspected layer metadata responses, {result['summary']['source_metadata_unavailable']} unavailable layer endpoints; plus {result['summary']['upstream_responses_inspected']} inspected upstream/physical/reference responses and {result['summary']['upstream_responses_unavailable']} unavailable upstream endpoints. Source metadata is evidence about the layer, not a substitute for complete local geometry/settlement identity inspection.",'',f"Machine screening identifies {result['summary']['locations_with_flags']:,} current African locations with one or more flags. Each exact affected ID and flag appears in the JSON. A clean screening result does not close a location. Original Africa evidence refers to {old.get('inspection',{}).get('valid_current_polygons',0):,} polygons and {len(old['inventory']['group_ids']):,} groups; the companion ledger lists every parent ID gained/lost since that snapshot.",'','Concrete next changes are separately enumerated for Comoros, São Tomé/Príncipe, Sierra Leone, Guinea, Mali, Lesotho, Morocco, Malawi, Togo, Seychelles, Madagascar, Mozambique and Uganda; Namibia retains its complete source-quality dossier and blockers. Candidate metadata does not define new member IDs or approve a split. Every proposed migration needs whole-land coverage, stable source member IDs, named city/rural purpose, licensing and record-preserving crosswalks.','', '## Reproduce','', 'Run `python scripts/audit-africa-semantic-followup.py` to reconcile the current committed atlas while reusing retained metadata. Add `--fetch` only to repeat public read-only metadata research. The script writes only this document and `data/geographic-semantic-followup/africa.json.gz`; successful assertions establish exhaustive membership coverage, not semantic closure. The complete ledger uses deterministic gzip (mtime 0), keeps every ID/evidence field, and belongs in Git rather than the website deployment package.','', 'Input hashes and all per-source URL/checksum/retrieval outcomes are retained in the [companion ledger](../../data/geographic-semantic-followup/africa.json.gz). Existing source assessments: [global granularity review](../GLOBAL_GRANULARITY_REVIEW.md), [region review](../REGION_SEMANTIC_REVIEW.md), [semantic closure state](../GLOBAL_SEMANTIC_CLOSURE.md), and [frozen Africa decisions](../../data/geographic-decisions/africa.json).']
 DOC.parent.mkdir(parents=True,exist_ok=True);DOC.write_text('\n'.join(lines)+'\n');print(json.dumps(result['summary'],indent=2))
if __name__=='__main__':main()
