#!/usr/bin/env python3
"""Refresh worldwide source-granularity screening without changing geography.

Candidate source research is retained from granularity-review-evidence.json.
This command does not fetch new sources, import boundaries, or close semantic
reviews. It can run from any working directory and refreshes the evidence and
the two complete documentation matrices against the current atlas snapshot.
"""
import json,gzip,collections as C,statistics,re,hashlib,pathlib,os,datetime

os.chdir(pathlib.Path(__file__).resolve().parents[1])
path=pathlib.Path('data/granularity-review-evidence.json');out=json.load(open(path));read=lambda p:json.load(open('data/'+p));w=read('world-review.json');policy=read('location-policy.json')['countries'];admin=read('administrative-sources.json');pixel=read('pixel-audit.json');units={x['id']:x for x in read('hierarchy.json')};locs=[x for p in w['location_parts'] for x in json.load(gzip.open('data/'+p))];loc={x['id']:x for x in locs};byowner=C.defaultdict(list);byparent=C.defaultdict(list)
for x in locs:byowner[x['owner']].append(x);byparent[x['parent_id']].append(x)
median={p:statistics.median(x['area_km2'] for x in xs) for p,xs in byparent.items()};geo={}
for part in read('world-index.json')['parts']:
 for f in read(part)['features']:
  p=f['properties'];m=p.get('metadata',{});g=f['geometry'];geo[f['id']]={'components':len(g['coordinates']) if g['type']=='MultiPolygon' else 1,'source_id':m.get('source_id'),'role':m.get('location_basis') or m.get('location_source_role') or m.get('source_role'),'declared_role':m.get('source_role'),'year':m.get('reference_year') or m.get('location_source_date'),'license':m.get('license'),'url':m.get('source_url'),'source_name':m.get('source_name'),'basis':m.get('location_basis'),'members':len(m.get('source_member_ids',[])),'name_evidence':m.get('name_evidence'),'match_field':next((k for k in ['framework_overlap','prefecture_overlap','geographic_overlap'] if k in m),None)}
assert set(geo)==set(loc)
missing={x['id'] for x in pixel['missing']};distorted={x['id'] for x in pixel['high_distortion']};weak=re.compile(r'^(unknown|named local administrative territory|adm[0-9] fallback|none|unspecified)$',re.I);anon=re.compile(r'(unorgani[sz]ed|unassigned|not available|unnamed|undefined|unknown|remainder|^region\s+\d|^district\s+\d|other territories|subdivision\s+\d)',re.I);urban=re.compile(r'(\bward\b|borough|arrondissement|urban district|city district|police department)',re.I)
flags=C.defaultdict(list)
for x in locs:
 i=x['id'];g=geo[i];r=[];role=g['role'] or x.get('basis','');area=x['area_km2'];p=units.get(x['parent_id'],{});med=median[x['parent_id']]
 if area>50000:r.append('large-territory-screen')
 if anon.search(x['name']) or g['name_evidence']=='unknown':r.append('anonymous-or-remainder-label')
 if re.search(r'police department',x['name'],re.I):r.append('urban-fragment-role')
 if re.search(r'(ward|city district)',role,re.I) and not g['members'] and not re.search(r'(including constituent|Five boroughs|districts\s+and\s+city|City and Mumbai)',role,re.I):r.append('mixed-urban-role-needs-classification')
 if re.search(r'districts and city districts',role,re.I):r.append('mixed-urban-role-needs-classification')
 if g['components']>1:r.append('multipart-footprint')
 if x['name'].casefold()==p.get('name','').casefold():r.append('repeated-location-province-name')
 if len(byparent[x['parent_id']])>=4 and med>0 and area>1000 and area/med>25:r.append('local-cluster-scale-outlier')
 if x.get('parent_overlap') is not None and x['parent_overlap']<.8:r.append('weak-source-parent-match')
 if i in missing:r.append('grid-unrepresented')
 if i in distorted:r.append('grid-high-distortion')
 if r:flags[x['owner']].append({'id':i,'name':x['name'],'parent_id':x['parent_id'],'source_id':g['source_id'],'role':role,'declared_role':g['declared_role'],'area_km2':area,'components':g['components'],'parent_overlap':x.get('parent_overlap'),'match_field':g['match_field'],'reasons':r})
concrete={
'ROU':'42 county footprints remain. ANCPI 2016 candidate has 3,235 municipality polygons. Verify official commune/urban identity, repeated names, coverage and vintage before replacing counties.',
'SLE':'14 old district footprints remain. Candidate 2016 layer has 165 chiefdom polygons including Bonthe Urban and York Rural. Verify Western Area urban land, complete coverage and subsequent reforms.',
'MLI':'56 broad cercle footprints remain. Candidate 2017 layer has 701 communes. Verify Bamako urban subdivisions, northern rural territory, complete coverage and later reforms.',
'GIN':'34 prefecture footprints remain. WFP/OCHA 2021 candidate has 340 subprefectures. Verify city communes, rural purpose and all complete source footprints before migration.',
'BOL':'117 province footprints deserve municipal-role research. GeoBolivia 2015 candidate has 339 named polygons, but canonical role is Unknown. ADM3 alone cannot justify import.',
'FIN':'70 district-equivalent footprints remain. OSM 2017 candidate has municipality-like names, but canonical role is Unknown and metadata says 313 while downloaded geometry contains 312 features. Resolve identity, count and ODbL attribution before import.',
'BLZ':'Six district footprints remain. Candidate 31-unit source is explicitly electoral constituencies from 2008. Finer electoral divisions do not establish coherent city and rural territories.',
'SLB':'Ten province/island-group footprints remain. Candidate 50-unit layer is electoral constituencies, splitting Honiara East/Central/West. Another 183-ward source has direct-permission licensing; verify reuse scope and island/city geography before import.',
'GUY':'Separate populated coastal councils from remote interior territory. Candidate 27 neighbourhood councils uses administrative-code labels and cannot be presumed to cover the whole country.',
'GRL':'Municipal and remote unincorporated coverage is not a settled-locality partition. Sparse Arctic land may warrant sourced named physical-region exceptions. Inspected finer gbOpen ADM2 endpoint was unavailable.',
'LBY':'39 local/physical territories retain sparse-desert and urban scale questions. Finer gbOpen ADM2/ADM3 endpoints were unavailable; research named municipalities and physical desert units rather than count quotas.',
'URY':'19 departments remain. Candidate 124 municipalities was already rejected for incomplete rural coverage. Seek a complete census-section/local geography partition with published names.',
'IND':'3,998 finer subdistricts replace 367 districts; 355 district footprints were retained for failed source coverage/clipping. Mixed roles and unresolved Ladakh naming remain open; retained units are not semantically certified.',
'PAK':'Candidate 554 tehsils was rejected for incomplete coverage and clipped units; 126 districts remain. Reconcile omitted land and disputed reference footprints before replacing complete local territories.',
'BTN':'Candidate 205 gewogs was rejected for incomplete coverage; 20 districts remain. Prove every named gewog footprint and complete land partition before migration.',
'ITA':'610 ISTAT local labour systems replace province-sized footprints using functional geography. Review all systems for locality scale, cross-province memberships, city extents and exceptional systems, not only Rome.',
'CHN':'County-equivalent territories, prefectural parent crosswalks and selected city merges have source evidence. Audit every remaining urban/rural county and prefecture; Guangdong and Shenzhen examples cannot certify nationwide consistency.',
'CAN':'Named census divisions/city aggregates and published remote ecoregions replace anonymous remainders. Review every populated division and remote physical subdivision for complete city extent, names and interprovincial membership.',
'GBR':'Source city/district aggregates include London and named counties. All Scotland/Wales/Northern Ireland roles, city extents, islands and single-child groups still require nationwide review.',
'AUS':'LGAs and sourced bioregional subdivisions distinguish local and remote roles. Review every LGA, remote subdivision, tiny island and isolated municipal precinct; area alone cannot justify a split.',
'JPN':'Published municipality crosswalks and grouped city wards establish a source role beyond ADM numbers. Verify every city/town/village aggregate, municipal merger, outlying island and province grouping.',
'BRA':'Published municipality crosswalks address duplicates and district membership. Verify all city aggregates, Amazonian remote territories, islands and administrative vintage.',
'TWN':'Nine published city-district crosswalks preserve coherent city aggregates. Review every remaining city/rural territory and clarify adjacent-tier roles; these nine examples cannot close country review.'}
territories=[]
for t in sorted(w['territories'],key=lambda x:x['owner'].casefold()):
 xs=byowner[t['owner']];fl=flags[t['owner']];counts=C.Counter(r for f in fl for r in f['reasons']);roles=C.Counter(geo[x['id']]['role'] or x.get('basis') or 'Unspecified' for x in xs);mapped=[iso for iso,names in w['policy_crosswalk'].items() if t['owner'] in names];sc=C.Counter(geo[x['id']]['source_id'] or geo[x['id']]['source_name'] or 'unidentified' for x in xs);sources=[]
 for sid,n in sorted(sc.items()):
  m=admin.get(sid,{});infos=[geo[x['id']] for x in xs if (geo[x['id']]['source_id'] or geo[x['id']]['source_name'] or 'unidentified')==sid];sources.append({'id':sid,'locations':n,'declared_canonical_role':m.get('boundaryCanonical'),'underlying_layer_roles':sorted({g['declared_role'] for g in infos if g['declared_role']}),'declared_unit_count':m.get('admUnitCount'),'years':sorted({str(g['year']) for g in infos if g['year'] is not None}),'licenses':sorted({g['license'] for g in infos if g['license']}),'urls':sorted({g['url'] for g in infos if g['url']}),'upstream_source':m.get('boundarySource'),'upstream_source_url':m.get('boundarySourceURL'),'license_detail':m.get('licenseDetail'),'license_source':m.get('licenseSource'),'recorded_sha256':m.get('sha256')})
 decision=concrete.get(t['iso']) if t['owner'] in w['policy_crosswalk'].get(t['iso'],[]) else None
 if not decision:
  top=', '.join(f'{r}: {n}' for r,n in roles.most_common(4));decision=f"{len(xs)} territories use {top}; median {t['area_km2']['median']:.1f} km², maximum {t['area_km2']['maximum']:.1f} km². "
  decision+=('No policy profile matches this distinct reference territory; establish a territorial source decision. ' if not mapped else 'Generic/fallback source roles do not prove suitability. ' if any(weak.match(r) for r in roles) else 'Urban subdivision roles require sourced complete-city membership review. ' if counts['urban-fragment-role'] else 'Named source roles are candidate local territories, subject to complete-city, coverage and rural-purpose verification. ')
  decision+='Observed flags: '+(', '.join(f'{k}={v}' for k,v in sorted(counts.items())) or 'none')+'. Absence of automated flags does not certify semantics.'
 territories.append({'territory':t['owner'],'reference_iso':t['iso'],'policy_profiles':mapped,'locations':len(xs),'provinces':len({x['parent_id'] for x in xs}),'area_km2':t['area_km2'],'actual_source_roles':dict(roles),'sources':sources,'flag_counts':dict(sorted(counts.items())),'flagged_locations':fl,'semantic_status':'open','decision':decision,'pixel_representation':{'represented':len(xs)-counts['grid-unrepresented'],'missing':counts['grid-unrepresented'],'high_distortion':counts['grid-high-distortion']}})
profiles=[]
for iso,p in sorted(policy.items()):
 ts=[t for t in territories if iso in t['policy_profiles']];s=admin.get(f'gb:{iso}:{p["level"]}',{});profiles.append({'iso':iso,'policy_role':p['role'],'policy_level':p['level'],'policy_source_url':p.get('source_url'),'canonical_source_role':s.get('boundaryCanonical'),'canonical_source_vintage':s.get('boundaryYearRepresented'),'license':s.get('boundaryLicense'),'source_unit_count':s.get('admUnitCount'),'territories':[t['territory'] for t in ts],'locations':sum(t['locations'] for t in ts),'flag_counts':dict(sum((C.Counter(t['flag_counts']) for t in ts),C.Counter())),'semantic_status':'open','decision':concrete.get(iso) or ' '.join(t['decision'] for t in ts),'policy_reason_requires_review':bool(weak.match(p['role']))})
assert len(territories)==w['reference_owner_groups']
assert len(profiles)==len(policy)==w['policy_profiles']
assert sum(t['locations'] for t in territories)==len(locs)==w['locations']==pixel['locations']
assert all(p['territories'] and p['decision'] for p in profiles)
assert all(set(p['territories'])==set(w['policy_crosswalk'][p['iso']]) for p in profiles)
assert sum(t['pixel_representation']['missing'] for t in territories)==len(pixel['missing'])
assert sum(t['pixel_representation']['high_distortion'] for t in territories)==len(pixel['high_distortion'])
out.update(status='source-evidence-assessed-semantic-open',inspected_at='2026-10-01',footprints_sha256=pixel['footprints_sha256'],policy_profiles=profiles,territories=territories,crosswalk=w['policy_crosswalk'],unmapped_reference_territories=[t['territory'] for t in territories if not t['policy_profiles']],summary={'policy_profiles':len(profiles),'reference_territories':len(territories),'locations':len(locs),'territories_with_policy_profile':sum(bool(t['policy_profiles']) for t in territories),'territories_without_policy_profile':sum(not t['policy_profiles'] for t in territories),'profiles_with_generic_policy_roles':sum(p['policy_reason_requires_review'] for p in profiles),'semantic_complete':False,'semantic_open_territories':len(territories),'flag_counts':dict(sum((C.Counter(t['flag_counts']) for t in territories),C.Counter()))},source_omission_reviews=read('coverage-report.json')['reviews'],review_limits=['Source evidence and automated flags do not certify all location semantics.','Multipart geometries include legitimate islands and enclaves.','Relative scale compares members of a province, not an exhaustive pairwise spatial-neighbour audit.','Source coastline comparisons do not prove that every island is present.'],rubric={'large-territory-screen':'Area >50,000 km² is a review trigger only; sparsely inhabited physical territories may warrant sourced exceptions.','anonymous-or-remainder-label':'Numbered/remainder/unknown source labels need evidence; legitimate official numbered names are not automatically errors.','urban-fragment-role':'Explicit police-department source names identify possible city fragments; verify source role and complete city footprint before any merge.','mixed-urban-role-needs-classification':'Source role mixes municipalities and city wards/districts without per-feature classification; source country roles and individual identities must be verified. Arrondissements in France/Belgium/Haiti are not automatically urban fragments.','multipart-footprint':'Multiple polygon components need source intent/island/enclave verification, not automatic splitting.','repeated-location-province-name':'Identical adjacent-tier names require distinct roles or a documented compact exception.','local-cluster-scale-outlier':'At least four province members, area >1,000 km² and >25 times median member area; compare rural purpose rather than impose equal sizes.','weak-source-parent-match':'Existing source-group overlap <80%; match_field identifies framework, prefecture or geographic source basis. This is not always the immediate province and must not trigger automatic reparenting.','grid-unrepresented':'No canonical cell-center representation; no arbitrary reassignment.','grid-high-distortion':'Pixel audit flags area distortion; this alone cannot prove unsuitable source granularity.'})
inputs=['data/location-policy.json','data/administrative-sources.json','data/granularity-audit.json','data/pixel-audit.json','data/semantic-report.json','data/coverage-report.json','data/hierarchy.json','data/world-review.json','data/world-index.json']
inputs+=['data/'+p for p in w['location_parts']]
inputs+=['data/'+p for p in read('world-index.json')['parts']]
out['input_hashes']={p:hashlib.sha256(open(p,'rb').read()).hexdigest() for p in inputs}
out['refresh_method']='Current source-metadata/geometry-component screening; retained candidate research, no new research or semantic closures'
out['screened_at']=datetime.datetime.now(datetime.timezone.utc).isoformat()
temporary=path.with_suffix(path.suffix+'.tmp')
temporary.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
temporary.replace(path)

doc=pathlib.Path('docs/GLOBAL_GRANULARITY_REVIEW.md')
text=doc.read_text()
clean=lambda x:str(x).replace('|','\\|').replace('\n',' ')
header='| Reference territory | Source policy | Locations / provinces | Actual source roles | Median km² | Flags |\n|---|---|---:|---|---:|---|'
rows=[]
for t in territories:
 roles='; '.join(f'{k} ({v})' for k,v in t['actual_source_roles'].items())
 notes='; '.join(f'{k}: {v}' for k,v in t['flag_counts'].items()) or 'No automated flags; semantics open'
 rows.append('| '+' | '.join(map(clean,[t['territory'],', '.join(t['policy_profiles']) or 'Unmatched',f"{t['locations']:,} / {t['provinces']:,}",roles,f"{t['area_km2']['median']:,.1f}",notes]))+' |')
a=text.index(header);b=text.index('\n## All source-policy profiles',a)
text=text[:a]+header+'\n'+'\n'.join(rows)+'\n'+text[b:]
a=text.index('| Screen |');b=text.index('\nFlags overlap.',a)
rubric='| Screen | Observed locations | Interpretation |\n|---|---:|---|\n'+'\n'.join(f"| {k} | {out['summary']['flag_counts'].get(k,0):,} | {v} |" for k,v in out['rubric'].items())
text=text[:a]+rubric+'\n'+text[b:]
header='| Policy ISO | Reference territories | Policy role | Canonical source role / date | License |\n|---|---|---|---|---|'
rows=[]
for p in profiles:
 rows.append('| '+' | '.join(map(clean,[p['iso'],', '.join(p['territories']),p['policy_role'],f"{p['canonical_source_role'] or 'Separate source/fallback'} / {p['canonical_source_vintage'] or 'Not established by selected-layer metadata'}",p['license'] or 'See actual territory-source provenance']))+' |')
a=text.index(header);b=text.index('\n## Completion gate',a)
text=text[:a]+header+'\n'+'\n'.join(rows)+'\n'+text[b:]
text=re.sub(r'all \*\*[\d,]+ active locations, \d+ reference territories and \d+ source-policy profiles\*\*',f"all **{len(locs):,} active locations, {len(territories)} reference territories and {len(profiles)} source-policy profiles**",text,count=1)
text=re.sub(r'The inspected footprint snapshot is `[^`]+`',f"The inspected footprint snapshot is `{out['footprints_sha256']}`",text,count=1)
temporary=doc.with_suffix(doc.suffix+'.tmp')
temporary.write_text(text)
temporary.replace(doc)
print(json.dumps(out['summary']))
print('Source-policy and territory matrices reconciled; retained research unchanged')
