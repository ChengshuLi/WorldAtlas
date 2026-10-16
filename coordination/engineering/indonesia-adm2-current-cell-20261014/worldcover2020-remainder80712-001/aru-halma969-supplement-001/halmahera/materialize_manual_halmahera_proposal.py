"""Transcribe human visual decisions; no spectral classification or source reads."""
from pathlib import Path
import json,gzip,hashlib,collections
OUT=Path(__file__).resolve().parent
SOURCE=OUT.parent/'worker1-source'
def pin(p):
 b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
decisions={};locators=collections.defaultdict(list)
for folder,manual in [('native-centre-review-v2','manual-wide-decisions-first-pass.json'),('native-detail-review','manual-detail-decisions-final.json'),('native-canopy-adverse-review','manual-canopy-adverse-decisions-final.json')]:
 inv=json.loads((OUT/folder/'contact-inventory.json').read_bytes());d=json.loads((OUT/manual).read_bytes())
 for page in inv['pages']:
  mapped={panel:kind for kind,panels in d[str(page['page_1based'])].items() for panel in panels}
  assert len(mapped)==len(page['panels'])
  assert set(mapped)=={p['panel_1based']for p in page['panels']}
  for p in page['panels']:
   idx=p['point_index'];decisions[idx]=mapped[p['panel_1based']]
   locators[idx].append({'path':page['path'],'sha256':page['sha256'],'page_1based':page['page_1based'],**p})
report=json.loads((SOURCE/'rgbnir-source-observations.json').read_bytes());rows=[];counts=collections.Counter();categories=collections.Counter()
scope=json.loads((OUT/'exact-cohort.json').read_bytes());selected_ids=set(scope['point_indices'])
frozen={r['point_index']:r for r in (json.loads(l)for l in gzip.decompress((SOURCE/'proposed-rgbnir-physical-location-dispositions.jsonl.gz').read_bytes()).splitlines())if r['point_index']in selected_ids}
answers={
 'V':('annual2020-rgbnir-supported-vegetated-body-location','Annual2020 native RGB/NIR spatial context shows a vegetation/canopy body at the unchanged source-associated centre. This is visible canopy/body-location support; dry ground beneath it and instantaneous inundation are not asserted.'),
 'W':('annual2020-rgbnir-supported-visible-water-body-location','Annual2020 native RGB/NIR spatial context places the unchanged source-associated centre on the visible water-like surface of a coastal, lagoon or channel body. This bounded annual-composite body-location answer does not assert permanence, tide state, water chemistry or a named river association.'),
 'L':('annual2020-rgbnir-supported-exposed-or-constructed-surface-location','Annual2020 native RGB/NIR spatial context places the unchanged source-associated centre on a visible exposed/constructed ground, beach or built surface. This bounded surface/body-location answer does not certify permanent dryness, material type or surveyed bank geometry.')}
for tile in report['tile_products']:
 for line in Path(tile['observations']['path']).open():
  p=json.loads(line)
  if p['point_index']not in selected_ids:continue
  assert p['original_key']['owner']==22796
  idx=p['point_index'];a=p['rgbnir_composite_observation'];kind=decisions[idx]
  assert a['coverage_status']=='valid-native-bands' and a['band_masks']==[255]*4
  p['prior_residual_disposition']={k:frozen[idx][k]for k in ['category','remaining_physical_question','proposed_bounded_answer']}
  assert not frozen[idx]['proposed_bounded_answer']
  p['original9332_frozen_proposal']={'file_sha256':scope['original_proposal']['sha256'],'point_index':idx,'prior_decision':p['prior_residual_disposition']}
  proposed=kind!='A'
  category,answer=answers[kind]if proposed else('unresolved-actual-pond-surface-or-fringe-placement',None)
  p.update({'category':category,'actual_answer':answer,'proposed_bounded_answer':proposed,'manual_visual_disposition':kind,'remaining_physical_question':None if proposed else 'Actual centre remains ambiguous between shallow reef/shoal water, exposed substrate, low-signal/shadowed vegetation or a narrow coast/fringe boundary in the annual composite. Original categorical cover/location evidence is retained; no surface answer is forced.','completed_question_credit_proposed':int(proposed),'formal_broader_original_question_closure':None,'root_adoption':None,'authority_or_repair_credit':0,'actual_native_views':locators[idx],'scientific_scope':'Annual2020 actual composite visible surface/canopy and original source-associated location only. Original Map classes, coordinates, ownership, territory/parent/portion/witness holds unchanged.','separate_unadopted_questions':['No underlying dry soil beneath canopy or current/instantaneous water state is asserted.','No native-authority, selected ownership, border or repair conclusion follows from this proposal.'],'distinct_review':None})
  rows.append(p);counts[kind]+=1;categories[category]+=1
assert len(rows)==687 and len(decisions)==687 and len({(p['original_key']['owner'],p['original_key']['y'],p['original_key']['x'])for p in rows})==687
rows.sort(key=lambda p:p['point_index']);plain=b''.join((json.dumps(p,separators=(',',':'))+'\n').encode()for p in rows)
output=OUT/'proposed-halmahera687-physical-location-dispositions.jsonl.gz'
with output.open('wb')as f:
 with gzip.GzipFile(fileobj=f,mode='wb',mtime=0,filename='')as z:z.write(plain)
summary={'kind':'human-visual-proposal-only-halmahera687','keys':687,'owner':22796,'manual_categories':dict(counts),'categories':dict(categories),'proposed_answers':687-counts['A'],'remaining':counts['A'],'perkey_proposal':{**pin(output),'decoded_bytes':len(plain),'decoded_sha256':hashlib.sha256(plain).hexdigest()},'source_report':pin(SOURCE/'rgbnir-source-observations.json'),'manual_inputs':[pin(OUT/x)for x in ['manual-wide-decisions-first-pass.json','manual-detail-decisions-final.json','manual-canopy-adverse-decisions-final.json']],'view_inventories':[pin(OUT/x/'contact-inventory.json')for x in ['native-centre-review-v2','native-detail-review','native-canopy-adverse-review']],'basis':'Human viewed all29 wide687 centre panels and all25 close291 panels (all200 initially uncertain and all91 preliminary exposed/constructed). Then six additional adverse sheets cover64 initially proposed canopy centres; final explicit morphology decisions override earlier passes. The NIR cutoff selects displays only, never a disposition rule. No threshold, automated confidence class, all-neighbour unanimity or Map95/90 binary conversion.','root_adoption':None,'distinct_review':None,'repair_credit':0,'examples':{str(idx):{'kind':decisions[idx],'original_key':next(p['original_key']for p in rows if p['point_index']==idx),'views':locators[idx]}for idx in [rows[0]['point_index'],rows[-1]['point_index']]}}
(OUT/'proposed-halmahera687-summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps({k:summary[k]for k in ['keys','manual_categories','proposed_answers','remaining','perkey_proposal']},indent=2))
