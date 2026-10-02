"""Every reference territory and active geographic group receives an evidence assessment.
An assessment never silently closes a missing-source semantic review.
"""
import collections,gzip,hashlib,json,pathlib,re,csv,importlib.util
R=pathlib.Path(__file__).resolve().parents[1];D=R/'data'
def read(p):return json.loads(p.read_text())
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,separators=(',',':')))
fs=[f for p in read(D/'world-index.json')['parts'] for f in read(D/p)['features']];units={x['id']:x for x in read(D/'hierarchy.json')};policies=read(D/'location-policy.json')['countries'];sources=read(D/'administrative-sources.json');ne=read(R/'.cache/ne_10m_admin_0_countries.json')['features'];audit=read(D/'granularity-audit.json');by_id={x['id']:x for x in audit['locations_audited']};refinements=read(D/'global-refinement-report.json');owner_iso={}
for f in ne:
 p=f['properties'];iso=p.get('ISO_A3_EH');iso=iso if iso and iso!='-99' else p['ADM0_A3']
 for key in ['ADMIN','NAME','NAME_LONG','SOVEREIGNT']:owner_iso.setdefault(p.get(key,''),iso)
for row in csv.DictReader((R/'.cache/country-codes.csv').open()):
 for key in ['official_name_en','UNTERM English Short','CLDR display name']:
  if row.get(key):owner_iso.setdefault(row[key],row['ISO3166-1-Alpha-3'])
by_owner=collections.defaultdict(list);members=collections.defaultdict(list)
for f in fs:
 by_owner[f['properties']['reference_owner']].append(f);p=f['properties']['parent_id']
 while p:members[p].append(f);p=units[p]['parent_id']
spec=importlib.util.spec_from_file_location('external_source_quality',R/'scripts/external-source-quality.py');external=importlib.util.module_from_spec(spec);spec.loader.exec_module(external)
source_quality=external.validated_reviews(D,fs,units)
rows=[];locations=[];continent_batches=collections.defaultdict(list)
for owner,features in sorted(by_owner.items()):
 codes=collections.Counter()
 for f in features:
  m=f['properties']['metadata']
  for code in external.source_country_codes(f):codes[code]+=1
 iso=codes.most_common(1)[0][0] if codes else owner_iso.get(owner);policy=policies.get(iso);profile_sources=[]
 for key in sorted({f['properties']['metadata'].get('source_id') for f in features}):
  if key in sources:
   x=sources[key];profile_sources.append({'id':key,'role':x.get('boundaryCanonical'),'year':x.get('boundaryYearRepresented'),'license':x.get('boundaryLicense'),'url':x.get('boundarySourceURL'),'sha256':x.get('sha256')})
 for key in sorted({f['properties']['metadata'].get('source_id') for f in features}):
  match=re.fullmatch(r'gb:([A-Z]{3}):(ADM[0-5])',key or '')
  path=D/'global-sources'/f'{match[1]}-{match[2]}-metadata.json' if match else None
  if path and path.exists() and not any(s['id']==key for s in profile_sources):
   meta=read(path);profile_sources.append({'id':key,'role':meta['boundaryCanonical'],'year':meta['boundaryYearRepresented'],'license':meta['boundaryLicense'],'url':meta['download_url'],'sha256':meta['sha256']})
 for key in sorted({f['properties']['metadata'].get('source_id') for f in features}):
  if not any(s['id']==key for s in profile_sources):
   m=next(f['properties']['metadata'] for f in features if f['properties']['metadata'].get('source_id')==key);profile_sources.append({'id':key,'role':m.get('source_role') or m.get('administrative_level'),'year':m.get('reference_year'),'license':m.get('license'),'url':m.get('source_url'),'sha256':m.get('source_geography_sha256') or m.get('original_geometry_sha256')})
 reviewed_roles=[x['role'] for x in profile_sources if x['role'] and x['role'].lower() not in ['unknown','nan']];issues=[]
 if not policy:issues.append('No matching country policy; territorial-specific source assessment required')
 if policy and ('Named local administrative' in policy['role'] or not reviewed_roles) and len(features)>1:issues.append('Published administrative role needs independent confirmation')
 sizes=[by_id[f['id']]['area_km2'] for f in features if f['id'] in by_id];coarse=sum(a>50000 for a in sizes);tiny=sum(a<25 for a in sizes)
 if coarse:issues.append(f'{coarse} locations exceed 50,000 km²; review recorded physical-geography exceptions')
 if tiny:issues.append(f'{tiny} locations below 25 km²; inspect city wards, islands and enclaves individually')
 # Exact per-territory group membership, without requiring a group to follow ownership.
 ids={f['id'] for f in features};group_issues=[id for id,group in members.items() if units[id]['metadata'].get('review_reasons') and any(f['id'] in ids for f in group)]
 cont=next(units[p]['name'] for p in members if units[p]['level']=='continent' and any(f['id'] in ids for f in members[p]))
 candidate=next((r for r in refinements['profiles'] if r['iso']==iso),None)
 assessment={'owner':owner,'iso':iso,'source_country_codes':sorted(codes),'continent':cont,'locations':len(features),'policy':policy,'sources':profile_sources,'source_roles':reviewed_roles,'status':'source-assessed-open' if issues or group_issues else 'source-assessed','issues':issues,'open_group_ids':group_issues,'area_km2':{'minimum':min(sizes) if sizes else None,'median':sorted(sizes)[len(sizes)//2] if sizes else None,'maximum':max(sizes) if sizes else None},'candidate_refinement':{k:v for k,v in candidate.items() if k not in ['matches','coastline_adjustments']} if candidate else None,'assessment_basis':'Source canonical roles, current membership, source vintage/license, city and remote exceptions, full location distribution. Remaining semantic judgments are explicit.'}
 if owner in source_quality['profiles']:assessment['source_quality_review']=source_quality['profiles'][owner];assessment['issues'].append(source_quality['profiles'][owner]['summary']);assessment['status']='source-assessed-open'
 rows.append(assessment);continent_batches[cont].append(owner)
 for f in features:
  m=f['properties']['metadata'];a=by_id.get(f['id'],{});locations.append({'id':f['id'],'name':f['properties']['name'],'parent_id':f['properties']['parent_id'],'owner':owner,'iso':iso,'basis':m.get('location_basis',m.get('administrative_level')),'source_url':m.get('source_url'),'source_year':m.get('reference_year'),'license':m.get('license'),'reasons':m.get('semantic_review_reasons',[])+([m['border_parent_review']['reason']] if m.get('border_parent_review') else []),'area_km2':a.get('area_km2'),'parent_overlap':m.get('framework_overlap',m.get('prefecture_overlap',m.get('geographic_overlap'))),'status':'open' if (a.get('area_km2',0)>50000 or m.get('framework_overlap',1)<.8 or m.get('border_parent_review') or m.get('semantic_review_reasons')) else 'source-assessed'})
# Every active parent is evaluated; coextensive city/island units can be explicit exceptions only with source evidence.
decisions=[]
for id,u in units.items():
 m=u['metadata'];group=members[id];owners=sorted({f['properties']['reference_owner'] for f in group});reasons=m.get('review_reasons',[])
 exception=None
 if len(group)==1 and u['level'] in ['province','area']:
  f=group[0];lm=f['properties']['metadata'];single_owner=len(by_owner[f['properties']['reference_owner']])==1
  if single_owner and lm.get('source_url') and ('territory:' in f['id'] or f['id'].startswith('atlas:city:')):exception='Coextensive tier for a sourced coherent compact territory; broader geographic membership is reviewed separately'
 status='documented-exception' if exception else 'open' if reasons else 'source-assessed'
 decisions.append({'id':id,'name':u['name'],'parent_id':u['parent_id'],'level':u['level'],'status':status,'exception':exception,'basis':m.get('basis'),'source':m.get('source'),'source_url':m.get('source_url'),'owners':owners,'locations':len(group),'children':m.get('child_count'),'reasons':reasons})
write(D/'world-review.json',{'version':1,'scope':'Every active location, geographic parent and reference-owner group, across all six continents. Source assessment and structural checks do not certify unfinished semantic decisions.','locations':len(fs),'territories':rows,'groups':decisions,'batches':dict(continent_batches),'policy_profiles':len(policies),'reference_owner_groups':len(rows),'semantic_complete':not any(x['status']=='open' for x in decisions),'group_status_counts':dict(collections.Counter(x['status'] for x in decisions))})
children=collections.defaultdict(list)
for u in units.values():
 if u['parent_id']:children[u['parent_id']].append(u['id'])
for decision in decisions:
 decision['child_ids']=sorted(children[decision['id']],key=lambda id:units[id]['name'])
 decision['semantic_status']='documented-exception' if decision['exception'] else 'pending'
 decision['checks']={'complete_membership':True,'footprint_method':'Union of member location footprints; no independent parent polygon','boundary_review':'pending','child_semantic_review':'pending'}
 # An individually supported boundary does not certify unresolved children.
 assessment=units[decision['id']]['metadata'].get('semantic_review')
 if assessment:
  decision['assessment']=assessment
  decision['checks']['boundary_review']=assessment['boundary_status']
  decision['reasons']=assessment['remaining_reasons']
location_decisions={f['id']:f['properties']['metadata'].get('semantic_review',{}) for f in fs}
complete_locations={id for id,assessment in location_decisions.items() if assessment.get('status')=='supported' and id not in source_quality['locations']}
direct_locations=collections.defaultdict(list)
for f in fs:direct_locations[f['properties']['parent_id']].append(f['id'])
complete_groups={}
for level in ['province','area','region','subcontinent','continent']:
 for decision in decisions:
  if decision['level']!=level:continue
  child_ids=direct_locations[decision['id']] if level=='province' else children[decision['id']]
  reviewed=all(id in complete_locations if level=='province' else complete_groups.get(id,False) for id in child_ids)
  decision['checks']['child_semantic_review']='supported' if reviewed else 'pending'
  complete=decision['checks']['boundary_review']=='supported' and reviewed and not decision['reasons'] and decision['id'] not in source_quality['groups']
  complete_groups[decision['id']]=complete
  decision['semantic_status']='supported' if complete else 'pending'
  if complete:decision['status']='reviewed'
for decision in decisions:
 if decision['id'] in source_quality['groups']:
  decision['source_quality_review']=source_quality['groups'][decision['id']];decision['semantic_status']='pending';complete_groups[decision['id']]=False
for location in locations:
 if location['id'] in source_quality['locations']:location['source_quality_review']=source_quality['locations'][location['id']];location['status']='open';complete_locations.discard(location['id'])
 assessment=location_decisions[location['id']]
 location['semantic_status']='pending' if location['id'] in source_quality['locations'] else assessment.get('status','pending')
 location['review_decision']=assessment or None
# A source assessment is not an approval of a boundary. Every branch stays discoverable.
x=read(D/'world-review.json');x['groups']=decisions;x['audit_order']=['continent','subcontinent','region','area','province','location'];x['root_ids']=sorted([u['id'] for u in units.values() if u['level']=='continent'],key=lambda id:units[id]['name']);x['level_progress']={level:{'total':sum(g['level']==level for g in decisions),'boundary_reviewed':sum(g['level']==level and g['checks']['boundary_review']=='supported' for g in decisions),'pending':sum(g['level']==level and g['semantic_status']=='pending' for g in decisions)} for level in x['audit_order'][:-1]};x['semantic_complete']=all(complete_groups.values()) and len(complete_locations)==len(fs);x['group_status_counts']=dict(collections.Counter(g['status'] for g in decisions));write(D/'world-review.json',x)
parts=[]
location_parts=collections.defaultdict(set)
for i in range(0,len(locations),1500):
 p=f'world-review-locations-{i//1500}.json.gz';(D/p).write_bytes(gzip.compress(json.dumps(locations[i:i+1500],separators=(',',':')).encode(),mtime=0));parts.append(p)
 for loc in locations[i:i+1500]:location_parts[loc['parent_id']].add(p)
x=read(D/'world-review.json');x['location_parts']=parts
x['policy_crosswalk']={iso:[r['owner'] for r in rows if r['iso']==iso or iso in r['source_country_codes']] for iso in sorted(policies)}
x['unmatched_reference_groups']=[r['owner'] for r in rows if not r['policy']]
x['unmatched_policy_profiles']=[iso for iso,owners in x['policy_crosswalk'].items() if not owners]
x['policy_crosswalk_basis']='All original source-country IDs plus fallback reference-owner ISO; a territory remains represented when modern sovereignty combines owner labels.'
x['source_omissions_report']='coverage-report.json'
x['finer_source_coverage_exceptions']='global-refinement-report.json'
for g in x['groups']:g['location_parts']=sorted(location_parts[g['id']])
x['level_progress']['location']={'total':len(locations),'source_assessed':sum(l['status']=='source-assessed' for l in locations),'semantic_reviewed':len(complete_locations),'pending_semantic_review':len(locations)-len(complete_locations)}
x['geographic_decision_files']=['geographic-decisions/'+p.name for p in sorted((D/'geographic-decisions').glob('*.json'))]
x['source_quality_reviews']=source_quality['manifest']
if source_quality['manifest']:x['input_source_quality_sha256']={r['path']:r['sha256'] for r in source_quality['manifest']}
x['input_sha256']={p:hashlib.sha256((D/p).read_bytes()).hexdigest() for p in ['hierarchy.json','world-index.json','granularity-audit.json']+read(D/'world-index.json')['parts']}
x['source_assessment_scope']='Current membership with retained source-policy assessments; frozen continent inventories describe their original source inspection snapshots.'
write(D/'world-review.json',x)
print(json.dumps({'territories':len(rows),'locations':len(locations),'groups':len(decisions),'statuses':x['group_status_counts'],'continents':list(continent_batches)}))
