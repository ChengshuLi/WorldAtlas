"""Author existing annual wetland/source-location meaning; no new science producer."""
from pathlib import Path
import json,gzip,hashlib,collections
TASK=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
def pin(p):
 b=p.read_bytes();return {'path':p.relative_to(TASK).as_posix(),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def key(d):return tuple(d[k]for k in ['owner','y','x'])
inputs=[TASK/'idn-worldcover2020-53134-001/worker2-interpretation/proposed-physical-location-dispositions.jsonl.gz',TASK/'idn-physical-remainder80712-001/worker2-interpretation/proposed-physical-location-dispositions.jsonl.gz']
rgbp=TASK/'idn-physical-largest-residuals-001/worker1-source/proposed-rgbnir-physical-location-dispositions.jsonl.gz'
with gzip.open(rgbp,'rt')as f:rgbkeys={key(json.loads(l)['original_key'])for l in f}
assert len(rgbkeys)==9332
unionp=TASK/'idn-physical-largest-residuals-001/aru-halma969-publication-preparation/files/coordination/engineering/indonesia-adm2-current-cell-20261014/worldcover2020-remainder80712-001/aru-halma969-supplement-001/accounting/known-exact-adopted-union101099-owner-y-x.jsonl.gz'
assert pin(unionp)['sha256']=='3d75cb9f6a7ac059c9c5b3a0af0cd1634a7ba3f6d673ae6279687f9972d3b733'
with gzip.open(unionp,'rt')as f:adopted={tuple(json.loads(l))for l in f}
assert len(adopted)==101099
precedent=TASK/'idn-physical-residual41305-policy-001/worker4-wetland-category-review-001/vietnam-wetland-precedent-extract.json'
assert pin(precedent)['sha256']=='cca8840bf629dd4587ea98df5120bbad564d2693799a1eed93d82bc402b669e8'
previous_review=[TASK/'idn-worldcover2020-53134-001/worker3-verification/physical-location-proposal-review.md',TASK/'idn-physical-remainder80712-001/worker3-verification/physical-location-proposal-review.md',TASK/'idn-physical-remainder80712-001/worker3-verification/actual-source-association-consequential-review.json']
limits=[
 'Annual2020 WorldCover v100 is credible thematic model-source evidence, not dated RGB, current truth, per-key certainty or an instantaneous wetness/tide observation.',
 'Mangrove cover means modeled mangrove vegetation/canopy in a wet/intertidal environment; herbaceous wetland means modeled wet/flooded herbaceous vegetation. Neither is a dry-land conversion.',
 'The containing native source pixel supports this unchanged point-scale interpretation, not complete coverage of the larger Atlas cell, surveyed coastline/bank or a selected geographic portion.',
 'Valid masks establish an actual source observation, not thematic correctness. Product-wide quality does not supply per-key accuracy or total positional error; source registration/mixing remains applicable.',
 'Native3x3 is observed surrounding category context, not an acceptance, majority or unanimity rule. Mixed neighbours do not erase the centre observation.',
 'Original source-version membership is affirmative retained numerical source evidence, not an independent current owner, strict-new-predicate, parent correction, treaty, shoreline/title or sovereignty finding.',
 'Binary exposed ground versus open water, permanently dry substrate, water beneath canopy and instantaneous inundation are not established by this bounded category/location answer.',
 'Every original source, foreign/coarse-parent, geographic-portion, territorial and ownership hold remains; no native-authority, current-selection or repair credit.'
]
counts=collections.Counter();classes=collections.Counter();cohorts=collections.Counter();flags=collections.Counter();patterns=collections.Counter();groups=collections.defaultdict(lambda:{'keys':0,'classes':collections.Counter(),'source_ids':set(),'examples':[]});metadata_cache={};source_meta=[];seen=set();keys=[];examples=[];decoded=hashlib.sha256();decoded_bytes=0
output=OUT/'proposed-untouched22576-wetland-source-location-dispositions.jsonl.gz'
with output.open('wb')as stream:
 with gzip.GzipFile(fileobj=stream,mode='wb',mtime=0,filename='')as zipped:
  for cohort,path in zip(['first53134','remainder80712'],inputs):
   with gzip.open(path,'rt')as f:
    for line in f:
     p=json.loads(line)
     if p['category']!='unresolved-specific-wetland-intertidal-body-relation':continue
     k=key(p['original_key']);counts['initial30750']+=1
     if k in adopted:counts['already_adopted101099']+=1
     if k in rgbkeys:counts['all_RGB9332_excluded']+=1;continue
     if k in adopted:counts['other_already_adopted_excluded']+=1;continue
     assert k not in seen;seen.add(k);keys.append(list(k));s=p['source_observation'];c=s['class_code'];assert c in [90,95]and s['coverage_status']=='valid-native-value'and s['valid_mask']==255 and s['nodata_match']is False
     if cohort=='first53134':
      a=p['positive_original_source_version_association'];assert a['source_version_positive_association'];assert len(a['original_ADM2_source_claims'])==1;source_id=a['original_ADM2_source_claims'][0];name=p['name'];parent=bool(a['retained_cross_parent_source_cooccurrences']);portion=a['documented_selected_geographic_portion'];other=[]
      src=s['path']
      if src not in metadata_cache:
       q=TASK/src;b=q.read_bytes();assert hashlib.sha256(b).hexdigest()==s['whole_sha256'];body=json.loads(b);metadata_cache[src]=(body,{v['point_index']:v for v in body['observations']});source_meta.append({'path':src,'bytes':len(b),'sha256':s['whole_sha256']})
      body,by=metadata_cache[src];v=by[p['point_index']];assert (v['owner'],v['y'],v['x'])==k
      assert all(v[z]==s[z]for z in ['class_code','valid_mask','nodata_match','coverage_status','native_row','native_col'])
      native={z:v[z]for z in ['tile','native_row','native_col','coverage_status','class_code','valid_mask','nodata_match','neighbourhood_complete','neighbourhood_codes','neighbourhood_masks']}
      native.update({'source_object_identity':body['source_identity'],'saved_native_window':body['window'],'saved_array':body['array'],'source_metadata':{'path':src,'sha256':s['whole_sha256']}})
     else:
      a=p['source_native_association'];claim=a['original_ADM2_claim'];assert claim['owners']==[k[0]];source_id=claim['source_id'];name=claim['name'];parent=bool(a['parent_discrepancy_claims']);portion=a['documented_selected_geographic_portion'];other=a['other_recorded_source_claims'];native=dict(s);native.update({'tile':p['tile'],'native_row':p['native_row'],'native_col':p['native_col'],'source_checkpoint':p['source_observation_checkpoint']})
     codes=native['neighbourhood_codes'];masks=native['neighbourhood_masks'];assert codes[1][1]==c
     context=sorted(set(x for row in codes for x in row));patterns[','.join(map(str,context))]+=1
     semantic='mangrove-canopy'if c==95 else'herbaceous-wetland'
     meaning='mangrove vegetation/canopy in a wet/intertidal environment'if c==95 else'wet/flooded herbaceous vegetation'
     answer='ESA WorldCover2020 v100 positively predicts '+meaning+' at the containing native pixel of this unchanged original centre. Its affirmative retained '+name+' original-source-version association ('+source_id+') supplies the independent geographic location component. Together these support the bounded annual2020 '+semantic+' source-body/location answer; neither permanently dry ground nor binary exposed-ground/open-water status is established.'
     prior={z:p.get(z)for z in ['proposed_bounded_answer','category','actual_answer','remaining_physical_question','completed_question_credit_proposed','credit_scope']}
     followup={'kind':'annual2020-'+semantic+'-and-original-source-version-location','semantic_cover':meaning,'source_name_unchanged':name,'source_target_unchanged':source_id,'positive_geographic_association_route':'retained exterior/interior plus exact original member'if cohort=='first53134'else'authenticated original native source-candidate interval/member/reverse-lineage association','actual_model_source':native,'specific_limits':limits,'binary_surface_conclusion':None,'source_association_and_other_holds_unchanged':True,'source_vintage_kind':'annual2020 model product, not dated RGB','answer_year':2020,'answer_dates':[],'VN_precedent_semantics_only':{'commit':'5d3b3ea950463ce0c5b9d8643f47cdb911b49320','original_body_sha256':'2f2566f62538ea174cf3a354b5290646cf088af476b7b7a3a89b91e45bba130a','example_index':1 if c==95 else 18,'spatial_facts_transferred':False},'prior_specific_body_relation_question_preserved_in':'prior_wetland_disposition.remaining_physical_question'}
     p.update({'input_cohort':cohort,'prior_wetland_disposition':prior,'proposed_bounded_answer':True,'category':'annual2020-source-supported-'+semantic+'-and-original-source-location','actual_answer':answer,'remaining_physical_question':None,'completed_question_credit_proposed':1,'credit_scope':'Proposed only: bounded annual2020 category-specific source-body and original-source-version location, pending distinct review and Root adoption. Original denominator unchanged; no binary surface, authority or repair credit.','annual_wetland_interpretation':followup,'formal_broader_original_question_closure':None,'root_adoption':None,'authority_or_repair_credit':0})
     encoded=(json.dumps(p,separators=(',',':'))+'\n').encode();zipped.write(encoded);decoded.update(encoded);decoded_bytes+=len(encoded)
     counts['proposed_exact_untouched']+=1;classes[str(c)]+=1;cohorts[cohort]+=1;flags['parent_context']+=parent;flags['selected_portion_context']+=portion;flags['recorded_other_claims']+=bool(other)
     if other:examples.append({'kind':'preserved-recorded-other-source-claim','cohort':cohort,'point_index':p['point_index'],'original_key':p['original_key'],'source_name':name,'other_claims':other})
     g=groups[(k[0],name)];g['keys']+=1;g['classes'][str(c)]+=1;g['source_ids'].add(source_id)
     if len(g['examples'])<2 or(name=='Merauke'and c==90 and not any(x['class_code']==90 for x in g['examples'])):g['examples'].append({'cohort':cohort,'point_index':p['point_index'],'original_key':p['original_key'],'class_code':c,'centre_unchanged':p['centre_unchanged'],'source_target':source_id,'retained_context_codes':context,'actual_answer':answer})
assert counts['initial30750']==30750 and counts['all_RGB9332_excluded']==8174 and len(seen)==22576 and not(seen&adopted)and not(seen&rgbkeys)
keyout=OUT/'exact-untouched22576-owner-y-x.jsonl.gz'
with keyout.open('wb')as f:
 with gzip.GzipFile(fileobj=f,mode='wb',mtime=0,filename='')as z:
  for k in sorted(keys):z.write((json.dumps(k,separators=(',',':'))+'\n').encode())
summary={'kind':'author-proposed-bounded-annual2020-untouched-wetland-source-body-location','scope':22576,'proposed_answers':22576,'classes':dict(classes),'cohorts':dict(cohorts),'accounting':dict(counts),'excluded_entire_RGB9332_wetland_scope':8174,'actual101099_overlap':0,'known_RGB9332_overlap':0,'prospective_union_only_if_Root_adopts':123675,'prospective_residual_only_if_Root_adopts':10171,'original_physical_denominator':133846,'perkey_proposal':{**pin(output),'decoded_bytes':decoded_bytes,'decoded_sha256':decoded.hexdigest()},'exact_keyfile':pin(keyout),'original_dispositions':[pin(p)for p in inputs],'RGB9332_scope':pin(rgbp),'adopted101099_keyfile':pin(unionp),'source_association_and_quality_review_reused':[pin(p)for p in previous_review if p.exists()],'VN_precedent':pin(precedent),'first53134_saved_metadata_bodies_read_for_context':len(source_meta),'source_metadata_pins':source_meta,'context_patterns_informational_not_gate':dict(patterns),'separate_original_hold_flags_nonexclusive':dict(flags),'owner_groups':[{**g,'owner':o,'source_name':n,'classes':dict(g['classes']),'source_ids':sorted(g['source_ids'])}for (o,n),g in sorted(groups.items(),key=lambda x:(-x[1]['keys'],x[0]))],'preserved_actual_other_claim_examples':examples,'specific_limits':limits,'basis':'Reuse independently reviewed exact native annual source facts plus affirmative original source-version geometry/interval/member joins, with substantive category-specific meaning and actual contextual/hold review. This is not mask/code-to-binary truth or a new confidence classifier; VN transfers accepted claim scope, never Vietnam geographic facts.','source_HTTP_raster_native_predicate_producer_calls':0,'new_adopted_credit':0,'authority_or_repair_credit':0,'distinct_review':None,'root_adoption':None}
(OUT/'proposal-summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps({k:summary[k]for k in ['scope','classes','cohorts','accounting','perkey_proposal','separate_original_hold_flags_nonexclusive']},indent=2))
