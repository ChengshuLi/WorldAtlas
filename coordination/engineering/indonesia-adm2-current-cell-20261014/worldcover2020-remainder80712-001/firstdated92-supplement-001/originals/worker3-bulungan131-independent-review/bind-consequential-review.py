from pathlib import Path
import json,gzip,hashlib,collections
T=Path.cwd();A=T/'idn-physical-dated778-plan-001/worker2-bulungan131-actual-review';O=Path(__file__).resolve().parent;P=T/'idn-physical-dated778-plan-001/worker6-metadata'
candidate=A/'proposed-bulungan131-dated-dispositions.jsonl.gz'
assert hashlib.sha256(candidate.read_bytes()).hexdigest()=='2244fe3c1f44065fb7dbe8b110b4412a3f439e3d1820e0d51ca32ad4fa488df1'
with gzip.open(candidate,'rt') as f:rows=list(map(json.loads,f))
with gzip.open(P/'exact778-original-source-coordinate-current-reason.jsonl.gz','rt') as f:original={tuple(r['original_key'][k] for k in ['owner','y','x']):r for r in map(json.loads,f) if r['original_key']['owner']==22698}
assert len(rows)==len(original)==131
raw={tuple(r['original_key'][k] for k in ['owner','y','x']):r for r in map(json.loads,(P/'first-raw-native-observation-001/S2B_50NNJ_20200222_0_L2A/point-observations.jsonl').open())}
accepted=[];deferred=[];unknown=[]
for r in rows:
 key=tuple(r['original_key'][k] for k in ['owner','y','x']);d=r['dated_native_followup'];old={k:v for k,v in r.items() if k!='dated_native_followup'};assert old==original[key],key
 assert d['actual_source_observation_unchanged']==raw[key],key
 item={'original_key':r['original_key'],'original_point_index':r['original_point_index'],'author_manual_code':d['manual_code'],'author_bounded_answer':d['bounded_answer']}
 if d['status']=='proposed_bounded_dated_answer':
  if r['original_point_index']==7228:
   item.update(independent_status='DEFER_AS_UNRESOLVED',reason='The exact fractional marker is at the transition between the red vegetated strip and broad brown low-NIR body. The saved17/49native contexts do not show an unambiguous exposed constructed corridor under this point; the bare-bank versus turbid/shallow-water or mixed fringe placement is still material. A nearby corridor is not a positive body location for the marked centre. No new legal/tide/substrate prerequisite is imposed.');deferred.append(item)
  else:item['independent_status']='SCIENTIFICALLY_SUPPORTED_WITH_LIMITS_FOR_ROOT_ADOPTION';accepted.append(item)
 else:unknown.append(item)
assert len(accepted)==62 and len(deferred)==1 and len(unknown)==68
assert collections.Counter(x['author_manual_code'] for x in accepted)=={'V':29,'W':21,'L':12}
nodata=[x for x in unknown if x['author_manual_code']=='N'];assert len(nodata)==22
for x in nodata:
 k=tuple(x['original_key'][z] for z in ['owner','y','x']);a=raw[k]['assets'];assert all(a[b]['native_valid_mask']==0 and a[b]['raw_value']==0 and a[b]['nodata_match'] for b in ['red','green','blue','nir'])
for name,vals in [('scientifically-supported62-original-keys.jsonl',accepted),('deferred1-original-key.jsonl',deferred),('remaining-original69-question-keys.jsonl',unknown+deferred)]:
 with (O/name).open('w') as f:
  for x in vals:f.write(json.dumps(x,separators=(',',':'))+'\n')
report={'verdict':'PASS_WITH_ONE_CONSEQUENTIAL_NARROWING','independent_reviewer':'/root/remaining474_malinau_mahakam105','author':'/root/cell_method_review','candidate':{'file':str(candidate.relative_to(T)),'bytes':candidate.stat().st_size,'sha256':hashlib.sha256(candidate.read_bytes()).hexdigest()},'scope':131,'author_proposed_answers':63,'scientifically_supported_answers':62,'supported_facets':{'vegetation_or_canopy':29,'visible_water_like_body':21,'exposed_or_constructed_surface_corridor':12},'deferred_author_positive':deferred,'remaining_questions':69,'original22_actual_nodata_preserved_unknown':True,'original68_unknown_answers_promoted':False,'original131_full_record_and_separate_holds_preserved':True,'actual_raw_point_observations_preserved':True,'actual_review':'All6saved49pixelcontext sheets and all10saved17pixeldetail sheets independently visually examined; SCL labels not used as automatictruth. No rerender/source/native/HTTP operations.','source_date':'2020-02-22T02:36:53.904000Z','item':'S2B_50NNJ_20200222_0_L2A','source_version_location':'Unchanged original22698Bulungan source-native association, notnewstrictgeometry/currentjurisdiction/legalownership orwholecelltruth.','native_scope_limits':['Datednative10m support, not survey registration or exact subpixel bank reconstruction.','Canopy does not establish dry substrate.','Water-like body does not establish permanence, hydrologic kind, tide, name or bank.','Exposed/constructed surface does not establish material, engineering function or permanent dryness.','No annual-composite orSCL fallback; PB02fixed display only, no index or quantitative truth gate.'],'formal_root_adoption':None,'native_or_repair_or_accepted_credit':0,'source_or_producer_or_native_calls':0,'author_proposal_edited':False,'outputs':[]}
for n in ['scientifically-supported62-original-keys.jsonl','deferred1-original-key.jsonl','remaining-original69-question-keys.jsonl']:
 b=(O/n).read_bytes();report['outputs'].append({'file':n,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
(O/'independent-scientific-review.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'verdict':report['verdict'],'supported':62,'unknown':69,'deferred':deferred,'json_sha256':hashlib.sha256((O/'independent-scientific-review.json').read_bytes()).hexdigest()}))
