"""Bounded original issue/source protocol adapters; membership is not source authority."""
import hashlib, json, re

def sha(b): return hashlib.sha256(b).hexdigest()
def release_binding(value):
    if not isinstance(value, dict) or type(value.get('version')) is not int or value['version'] < 1:
        raise ValueError('Missing typed declared source vintage')
    if not re.fullmatch('geography:review:[a-f0-9]{64}', value.get('id', '')):
        raise ValueError('Invalid declared release ID')
    if any(not re.fullmatch('[a-f0-9]{64}', value.get(k, '')) for k in ('footprints_sha256','hierarchy_sha256')):
        raise ValueError('Missing declared release hashes')
    return value

def regional_members(value):
    """Validate the existing regional review/supplement protocol, not arbitrary prose."""
    batch=value.get('batch_id','')
    if not re.fullmatch('regional-(?:review|supplement):[a-f0-9]{16}',batch):
        raise ValueError('Not a recognized existing regional workload')
    ids=value.get('member_location_ids')
    if not isinstance(ids,list) or not ids or any(not isinstance(x,str) or not x for x in ids) or ids!=sorted(set(ids)):
        raise ValueError('Declared members must be complete sorted unique strings')
    if type(value.get('location_count')) is not int or value['location_count']!=len(ids):
        raise ValueError('Declared member count changed')
    digest=sha('\n'.join(ids).encode())
    if value.get('member_location_ids_sha256')!=digest:
        raise ValueError('Declared member hash changed')
    path=value.get('owned_evidence_path')
    if path!='data/regional-review/'+batch.replace(':','-')+'/':
        raise ValueError('Declared regional packet path changed')
    if value.get('review_only') is not True:
        raise ValueError('Regional review-only applicability changed')
    field='original_scope_release' if 'original_scope_release' in value else 'release'
    return {'subject_ids':ids,'membership_sha256':digest,'membership_hash_convention':'sorted IDs joined by LF without trailing LF',
            'declared_vintage':release_binding(value.get(field)),'vintage_json_pointer':'/'+field,
            'owned_evidence_path':path,'body_json_pointer':'/member_location_ids',
            'qualification':'validated-declared-regional-membership-only'}

def issue_rosters(pages):
    if not isinstance(pages,list) or not pages or any(not isinstance(p,list)or len(p)>100 for p in pages):
        raise ValueError('Complete paginated all-state issue arrays required')
    if any(len(p)!=100 for p in pages[:-1]) or len(pages[-1])>=100:
        raise ValueError('Missing nonfinal or terminal issue page')
    rows=[r for p in pages for r in p]
    if len(rows)!=len({r['number']for r in rows}):raise ValueError('Duplicate issue across API pages')
    strong=[]; weaker=[]; rejected=[]
    for pi,page in enumerate(pages):
      for ri,issue in enumerate(page):
        if 'pull_request' in issue:continue
        body=issue.get('body')or''
        base={'issue':issue['number'],'state':issue['state'],'body_sha256':sha(body.encode()),
              'snapshot_json_pointer':f'/{pi}/{ri}','updated_at':issue.get('updated_at'),
              'work_role':'archived-closed-predecessor-context' if issue['state']=='closed' else 'open-related-work-needs-live-claim-check',
              'source_authority_status':'not-established-by-membership','repair_scope_status':'not-established-by-subject-intersection'}
        matches=re.findall(r'<!-- worldatlas-work:v1\s*([\s\S]*?)\s*-->',body)
        if len(matches)==1:
          try:
            spec=json.loads(matches[0]);ids=spec.get('evidence_quality',{}).get('subject_ids',[])
            if not isinstance(ids,list)or any(not isinstance(x,str)or not x for x in ids)or len(ids)!=len(set(ids)):
                raise ValueError('Invalid authoritative machine subject roster')
            if ids:strong.append({**base,'kind':'machine-contract','subject_ids':ids,'body_json_pointer':'/evidence_quality/subject_ids',
                                 'declared_vintage':'machine-pins-not-assumed-current','declared_pins':spec.get('evidence_quality',{}).get('pins',{}),
                                 'qualification':'declared-machine-subjects-only'})
          except (ValueError,TypeError) as e:rejected.append({**base,'kind':'machine-contract','reason':str(e)})
        for fi,raw in enumerate(re.findall(r'```json\s*([\s\S]*?)```',body)):
          try:value=json.loads(raw)
          except ValueError:continue
          if not isinstance(value,dict)or'member_location_ids'not in value:continue
          locator={**base,'kind':'structured-body-members','body_json_fence_index':fi}
          try:strong.append({**locator,**regional_members(value)})
          except ValueError as e:
            rejected.append({**locator,'reason':str(e)})
            ids=value.get('member_location_ids')
            if isinstance(ids,list)and all(isinstance(x,str)for x in ids):
                weaker.append({**locator,'subject_ids':sorted(set(ids)),'body_json_pointer':'/member_location_ids',
                               'qualification':'related-structured-context-not-validated-regional-workload',
                               'declared_vintage':value.get('original_scope_release',value.get('release','not-recorded')),'reason':str(e)})
    return strong,weaker,rejected

def administrative_product_context(metadata,registry,policy):
    """Report what the unchanged recipe consumes; do not approve its source or shape."""
    source=metadata.get('source_id')
    if source not in registry:return {'status':'no-exact-administrative-registry-match','source_id':source}
    entry=registry[source]
    consumed=entry.get('simplifiedGeometryGeoJSON');advertised=entry.get('gjDownloadURL')
    if not isinstance(consumed,str)or not isinstance(advertised,str)or not re.fullmatch('[a-f0-9]{64}',entry.get('sha256','')):
        raise ValueError('Incomplete administrative product registry')
    match=re.fullmatch('gb:([A-Z]{3}):(ADM[123])',source)
    if not match or not isinstance(policy,dict)or not isinstance(policy.get('countries'),dict):
        raise ValueError('Typed original selector policy required')
    iso,level=match.groups();rule=policy['countries'].get(iso)
    selector='not-selected-by-this-pinned-recipe-policy';expected=None
    if isinstance(rule,dict):
        if rule.get('level')==level:
            selector='primary-country-policy-selected-layer'
            if rule.get('source_url'):expected=rule['source_url'].replace('.geojson','_simplified.geojson')
        elif level=='ADM1'and rule.get('level')in ('ADM2','ADM3'):
            selector='recorded-parent-ADM1-context-layer'
        elif level=='ADM2'and rule.get('level')=='ADM3':
            selector='recorded-parent-ADM2-context-layer'
    return {'status':'exact-registry-source-id-and-pinned-selector-context','source_id':source,
            'original_recipe_consumed_product_url':consumed,'original_selector_role':selector,
            'original_policy_json_pointer':'/countries/'+iso,'original_country_selector_rule':rule,
            'original_literal_policy_url_transform':expected,
            'registry_matches_policy_transformed_product':None if expected is None else consumed==expected,
            'registry_consumed_product_sha256':entry['sha256'],'registry_advertised_full_reference_url':advertised,
            'recorded_feature_source_url':metadata.get('source_url'),'distinct_registry_product_urls':consumed!=advertised,
            'feature_url_matches_advertised_full_reference':metadata.get('source_url')==advertised,
            'source_authority_status':'unverified','cause_status':'unknown',
            'next_question':'Compare consumed simplified product with advertised full reference and coordinated neighbors; authenticate both vintages before any repair.'}
