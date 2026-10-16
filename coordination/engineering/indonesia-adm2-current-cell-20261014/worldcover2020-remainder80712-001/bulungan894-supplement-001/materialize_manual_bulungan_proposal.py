"""Transcribe human visual decisions; no spectral classification or source reads."""
from pathlib import Path
import json,gzip,hashlib,collections
OUT=Path(__file__).resolve().parent
SOURCE=OUT.parent/'worker1-source'
def pin(p):
 b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
decisions={};locators=collections.defaultdict(list)
for folder,manual in [('native-centre-review-v2','manual-panel-decisions-first-pass.json'),('native-detail-review','manual-detail-decisions-final.json'),('native-provisional-v-adverse-review','manual-provisional-v-adverse-decisions.json')]:
 inv=json.loads((OUT/folder/'contact-inventory.json').read_bytes());d=json.loads((OUT/manual).read_bytes())
 for page in inv['pages']:
  mapped={panel:kind for kind,panels in d[str(page['page_1based'])].items() for panel in panels}
  assert len(mapped)==len(page['panels'])
  assert set(mapped)=={p['panel_1based']for p in page['panels']}
  for p in page['panels']:
   idx=p['point_index'];decisions[idx]=mapped[p['panel_1based']]
   locators[idx].append({'path':page['path'],'sha256':page['sha256'],'page_1based':page['page_1based'],**p})
report=json.loads((SOURCE/'rgbnir-source-observations.json').read_bytes());rows=[];counts=collections.Counter();categories=collections.Counter()
answers={
 'V':('annual2020-rgbnir-supported-vegetated-body-location','Annual2020 native RGB/NIR spatial context shows a vegetation/canopy body at the unchanged source-associated centre. This is visible canopy/body-location support; dry ground beneath it and instantaneous inundation are not asserted.'),
 'W':('annual2020-rgbnir-supported-visible-water-body-location','Annual2020 native RGB/NIR spatial context places the unchanged source-associated centre on the visible water-like surface of a pond/channel/river body. This bounded annual-composite body-location answer does not assert permanence, tide state, water chemistry or a named river association.'),
 'L':('annual2020-rgbnir-supported-exposed-or-constructed-surface-location','Annual2020 native RGB/NIR spatial context places the unchanged source-associated centre on a visible exposed/constructed ground, levee or built surface. This bounded surface/body-location answer does not certify permanent dryness, material type or surveyed bank geometry.')}
for tile in report['tile_products']:
 for line in Path(tile['observations']['path']).open():
  p=json.loads(line)
  if p['original_key']['owner']!=22698:continue
  idx=p['point_index'];a=p['rgbnir_composite_observation'];kind=decisions[idx]
  assert a['coverage_status']=='valid-native-bands' and a['band_masks']==[255]*4
  p['prior_residual_disposition']={k:p[k]for k in ['category','remaining_physical_question','proposed_bounded_answer']}
  proposed=kind!='A'
  category,answer=answers[kind]if proposed else('unresolved-actual-pond-surface-or-fringe-placement',None)
  if idx==8611:
   assert kind=='L'
   answer='Annual2020 RGB/NIR places the unchanged centre on the visible bright narrow constructed/exposed corridor beside water. The corridor-body placement is supported at native composite scale; the exact corridor/water edge and surveyed registration are not resolved.'
  p.update({'category':category,'actual_answer':answer,'proposed_bounded_answer':proposed,'manual_visual_disposition':kind,'remaining_physical_question':None if proposed else 'Actual centre remains ambiguous between pond water, drained/exposed substrate, low-signal vegetation or a narrow bank/fringe boundary in the annual composite. Original categorical cover/location evidence is retained; no surface answer is forced.','completed_question_credit_proposed':int(proposed),'formal_broader_original_question_closure':None,'root_adoption':None,'authority_or_repair_credit':0,'actual_native_views':locators[idx],'scientific_scope':'Annual2020 actual composite visible surface/canopy and original source-associated location only. Original Map classes, coordinates, ownership, territory/parent/portion/witness holds unchanged.','separate_unadopted_questions':['No underlying dry soil beneath canopy or current/instantaneous water state is asserted.','No native-authority, selected ownership, border or repair conclusion follows from this proposal.'],'distinct_review':None})
  rows.append(p);counts[kind]+=1;categories[category]+=1
assert len(rows)==894 and len(decisions)==894 and len({(p['original_key']['owner'],p['original_key']['y'],p['original_key']['x'])for p in rows})==894
rows.sort(key=lambda p:p['point_index']);plain=b''.join((json.dumps(p,separators=(',',':'))+'\n').encode()for p in rows)
output=OUT/'proposed-bulungan894-physical-location-dispositions.jsonl.gz'
with output.open('wb')as f:
 with gzip.GzipFile(fileobj=f,mode='wb',mtime=0,filename='')as z:z.write(plain)
summary={'kind':'human-visual-proposal-only-bulungan894','keys':894,'owner':22698,'manual_categories':dict(counts),'categories':dict(categories),'proposed_answers':894-counts['A'],'remaining':counts['A'],'perkey_proposal':{**pin(output),'decoded_bytes':len(plain),'decoded_sha256':hashlib.sha256(plain).hexdigest()},'source_report':pin(SOURCE/'rgbnir-source-observations.json'),'manual_inputs':[pin(OUT/x)for x in ['manual-panel-decisions-first-pass.json','manual-detail-decisions-final.json','manual-provisional-v-adverse-decisions.json']],'view_inventories':[pin(OUT/x/'contact-inventory.json')for x in ['native-centre-review-v2','native-detail-review','native-provisional-v-adverse-review']],'basis':'Human viewed all38 wide894 centre panels, all24 close280 panels, then all4 targeted41 adverse panels. Later explicit manual decisions override earlier ones. No threshold, automated confidence class, all-neighbour unanimity or Map95/90 binary conversion.','root_adoption':None,'distinct_review':None,'repair_credit':0,'examples':{str(idx):{'kind':decisions[idx],'original_key':next(p['original_key']for p in rows if p['point_index']==idx),'views':locators[idx]}for idx in [2415,5198,8611,5156,5381,5422]}}
(OUT/'proposed-bulungan894-summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps({k:summary[k]for k in ['keys','manual_categories','proposed_answers','remaining','perkey_proposal']},indent=2))
