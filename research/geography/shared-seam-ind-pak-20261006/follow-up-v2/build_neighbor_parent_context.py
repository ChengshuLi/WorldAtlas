#!/usr/bin/env python3
"""Crosswalk the exact 16 issue subjects to their review-only neighboring roster context."""
import hashlib,json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
PACKET=ROOT/'research/geography/shared-seam-ind-pak-20261006'
OUT=PACKET/'follow-up-v2'
BASE='0f08ca8c451e71bb3b06cb5fb82988e92d3048ab'
def sha(b):return hashlib.sha256(b).hexdigest()
def canonical(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def main(run):
 head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
 if subprocess.call(['git','merge-base','--is-ancestor',BASE,head],cwd=ROOT)!=0:raise ValueError('fresh main is not an ancestor')
 raw=(OUT/'neighbor-issue-bodies.json').read_bytes(); bundle=json.loads(raw)
 hierarchy_raw=subprocess.check_output(['git','show',f'{BASE}:data/hierarchy.json'],cwd=ROOT)
 handoff_raw=subprocess.check_output(['git','show',f'{BASE}:data/macro-foundation/regional-handoffs.json.gz'],cwd=ROOT)
 hierarchy={x['id']:x for x in json.loads(hierarchy_raw)}
 import gzip
 handoffs=json.loads(gzip.decompress(handoff_raw))['regions'];regions={x['region_id']:x for x in handoffs}
 scopes={}; refs={}
 for number,record in bundle['issues'].items():
  body=record['body']
  if sha(body.encode())!=record['body_sha256']:raise ValueError('issue-body pin changed: '+number)
  blocks=[]
  for block in re.findall(r'```(?:json)?\s*\n(.*?)\n```',body,re.S):
   try:
    obj=json.loads(block)
    if isinstance(obj,dict) and 'member_location_ids' in obj:blocks.append(obj)
   except Exception:pass
  if len(blocks)!=1:raise ValueError('expected one exact regional roster block in issue '+number)
  scopes[number]=blocks[0]
  refs[number]={'title':record['title'],'url':record['html_url'],'issue_body_sha256':record['body_sha256'],'review_only':blocks[0]['review_only'],'roster_count':blocks[0]['location_count'],'roster_ids_sha256':blocks[0]['member_location_ids_sha256'],'region_id':blocks[0]['region_id'],'area_scopes':[{'id':x['id'],'name':x['name'],'owned_member_location_count':x['owned_member_location_count']} for x in blocks[0]['area_scopes']]}
 cross=json.loads((PACKET/'source-crosswalk.json').read_text()); subject_rows=[]; issue_counts={n:0 for n in scopes}
 for source in cross['subjects']:
  sid=source['subject_id'];found=[]
  for number,scope in scopes.items():
   if sid not in scope['member_location_ids']:continue
   for province in scope['province_scopes']:
    if sid not in province.get('owned_location_ids',[]):continue
    ph=hierarchy.get(province['id']); area=hierarchy.get(ph.get('parent_id')) if ph else None
    region=regions.get(scope['region_id'])
    found.append((number,scope,province,ph,area,region))
  if len(found)!=1:raise ValueError(f'{sid}: expected one review roster/province mapping, got {len(found)}')
  number,scope,prov,ph,area,region=found[0];issue_counts[number]+=1
  original=json.loads((PACKET/'sources/original-features'/(source['shapeID']+'.geojson')).read_text())
  subject_rows.append({'subject_id':sid,'source_id':source['source_layer'],'shapeID':source['shapeID'],'source_name':source['shapeName'],'source_feature_parent_fields_present':sorted(k for k in original['properties'] if k.lower() in {'parentid','parent_id','parentshapeid','shapeparentid','adm1_code','shapeadm1'}),'original_feature_properties':sorted(original['properties']),'review_packet':{'issue_number':int(number),'province_id':prov['id'],'province_name':prov['name'],'current_area_id':area['id'] if area else None,'current_area_name':area['name'] if area else None,'region_id':scope['region_id'],'subcontinent_parent_id':region['subcontinent_id'] if region else None,'review_only':scope['review_only']}})
 if sorted(x['subject_id'] for x in subject_rows)!=sorted(cross['subjects'][i]['subject_id'] for i in range(16)):raise ValueError('subject roster mismatch')
 controls={'positive':{'all_16_subjects_mapped_once':len(subject_rows)==16,'all_four_relevant_issue_rosters_review_only':all(scopes[n]['review_only'] for n in scopes),'issue_membership_counts':issue_counts},'negative':{'no_original_source_parent_code_claimed':all(not x['source_feature_parent_fields_present'] for x in subject_rows),'invented_subject_rejected':'atlas:local:IND:GEO4-NEGATIVE' not in set(scopes['96']['member_location_ids'])|set(scopes['97']['member_location_ids'])|set(scopes['98']['member_location_ids'])|set(scopes['115']['member_location_ids'])}}
 result={'schema':'geo4-seam-neighbor-parent-context-v1','actual_execution_sha':head,'baseline_main_sha':BASE,'reproduction_code_sha256':sha(Path(__file__).read_bytes()),'retrieved_at_utc':bundle['retrieved_at_utc'],'issue_source_bundle_sha256':sha(raw),'baseline_inputs':{'data/hierarchy.json':sha(hierarchy_raw),'data/macro-foundation/regional-handoffs.json.gz':sha(handoff_raw)},'neighboring_review_issues':refs,'issue_subject_match_counts':issue_counts,'subject_parent_context':subject_rows,'checks':controls,'interpretation_limits':['Selected original geoBoundaries features expose shapeGroup/shapeID/shapeISO/shapeName/shapeType but no upstream parent code; the parent below is an Atlas review-roster mapping, not independent ADM1-source verification.','All four regional packets are review-only and the regional interiors are not approved. Macro own-boundary approval does not approve these interiors.','No Pakistan territorial affiliation or ownership is inferred for either physical-gap fragment. #115 records separate KAS source-policy work, which is not changed or resolved here.']}
 if not all(controls['positive'][k] for k in ('all_16_subjects_mapped_once','all_four_relevant_issue_rosters_review_only')) or not all(controls['negative'].values()):raise ValueError('parent-context control failure')
 target=OUT/f'parent-context-{run}.json';target.write_bytes(canonical(result)+b'\n');return target
if __name__=='__main__':
 if len(sys.argv)!=2 or sys.argv[1] not in ('run-1','run-2'):raise SystemExit('usage: build_neighbor_parent_context.py run-1|run-2')
 print(main(sys.argv[1]))
