"""Bind completed human visual decisions to exact saved, verified evidence."""
from pathlib import Path
import json,hashlib,collections,datetime
ROOT=Path('/workspace/scratch/127991fc8b8e/worldatlas-indonesia-cloud-proof-20261016/batam-january6-81-complete-author-review-001')
OUT=Path(__file__).resolve().parent
rows=[json.loads(x)for x in (ROOT/'author-proposed81-nextdated-dispositions.jsonl').read_text().splitlines()]
reasons=json.loads((OUT/'independent-visual-reasons.json').read_text())
assert len(rows)==len(reasons)==81
rejected={16294,17277,17910}
accepted=[];held=[];decisions=[]
limits=[
 'Qualitative dated visible facet only; no calibrated reflectance, normalized BOA, spectral index or automated classification.',
 'No hidden ground or understory, dryness, depth, inundation, exact tide, material, purity or whole-cell ground-truth conclusion.',
 'Literal source SCL, cloud, shadow, fringe, masks and all earlier cloudy/nodata observations remain unchanged; SCL is context, not independent body truth.',
 'Source association is the retained source-candidate/member relation, not a new strict-interior, boundary/tie or selected-footprint predicate.',
 'All original independent source, owner, parent, selected geographic portion, jurisdiction and territorial holds remain; no native-authority or repair credit.'
]
for r in rows:
 i=r['original_point_index'];o=r['new_actual_saved_observation_unchanged'];a=r['author_proposed_disposition'];answer=a['answer'] if i not in rejected else None
 original=r['prior_complete_dated_stage_record_unchanged']['unchanged_original_author_proposal_and_actual_observation']['prior_complete778_stage_record_unchanged']['unchanged_original_proposal']
 annual=original['original_held_inventory_record_unchanged']
 k=[r['original_key'][x]for x in ('owner','y','x')]
 (accepted if answer else held).append(k)
 decision={
  'original_key':r['original_key'],'original_point_index':i,
  'distinct_review_status':'supported_bounded_dated_visible_facet_pending_root_adoption' if answer else 'held_no_supported_exact_visible_facet',
  'bounded_answer':answer,'independent_visual_reason':reasons[str(i)],
  'author_proposed_answer_unchanged':a['answer'],'differs_from_author':i in rejected,
  'item_id':o['item_id'],'acquisition_datetime':o['acquisition_datetime'],'processing_baseline':o['processing_baseline'],
  'PB05_qualitative_only':a['PB05_qualitative_only'],'raw_SCL_context_value':o['assets']['scl']['raw_value'],
  'native_containing_pixels':{b:o['assets'][b]['native_containing_pixel']for b in ('red','green','blue','nir','scl')},
  'native_valid_masks':{b:o['assets'][b]['native_valid_mask']for b in ('red','green','blue','nir','scl')},
  'original_annual_physical_question_unchanged':annual['current_remaining_physical_question'],
  'prior_dated_remaining_question_unchanged':a['original_remaining_question'],
  'question_scope':'Only the visible dated surface/body facet is supported. The original broader water/ground-interface, hidden-surface, inundation or tide question is not formally closed.' if answer else 'Exact visible dated facet remains unresolved; original broader questions also remain held.',
  'actual_views_unchanged':r['actual_views'],
  'all85_views_actually_visually_reviewed':True,
  'independent_limits_retained':limits,
  'incomplete_source_frame_retained':i==17294,
  'root_adoption_credit':0,'formal_broader_original_question_closure':False,'native_authority_or_repair_credit':0
 }
 decisions.append(decision)
for name,data in [('accepted49-owner-y-x.jsonl',sorted(accepted)),('held32-owner-y-x.jsonl',sorted(held))]:
 (OUT/name).write_text(''.join(json.dumps(x,separators=(',',':'))+'\n'for x in data))
(OUT/'independent-keyed-decisions81.jsonl').write_text(''.join(json.dumps(x,separators=(',',':'))+'\n'for x in decisions))
assert len(accepted)==49 and len(held)==32 and len({tuple(k)for k in accepted+held})==81
def pin(p):
 b=p.read_bytes();return {'file':p.name,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
counts=dict(collections.Counter(x['bounded_answer']or 'hold'for x in decisions))
summary={
 'reviewer':'review_january6_batam_facets','author':'finish_indonesia_packages','completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'scope':81,'accepted_bounded_dated_facets':49,'held':32,'class_counts':counts,
 'author_proposed_count':52,'author_holds_retained':29,'new_reviewer_holds_point_indices':sorted(rejected),
 'all_native_RGB_FCC_separate_SCL_details_visually_reviewed':81,'all_wide_contact_pages_visually_reviewed':4,
 'input_proposal':pin(ROOT/'author-proposed81-nextdated-dispositions.jsonl'),
 'input_literal52':pin(ROOT/'author-proposed52-owner-y-x.jsonl'),
 'approved_plan':pin(ROOT/'next-distinct-native-block-plan81.json'),'final_reader':pin(ROOT/'read_next_distinct_native_blocks.py'),
 'result_files':[pin(OUT/f)for f in ['accepted49-owner-y-x.jsonl','held32-owner-y-x.jsonl','independent-keyed-decisions81.jsonl','custody-and-scope-verification.json','whole-input279-manifest.json','native-centre-verification81.json','independent-visual-reasons.json']],
 'source_operations_by_reviewer':0,'all_prior_January1_January3_chains_unchanged':True,
 'failed_startup_history':'Initial producer reader failed at a redundant stale 91/60/1 assertion before attempt-start and source reads. Empty stdout, traceback, original reader and correction records remain in the 279-file input. Final reader is separately pinned; it completed 55 new data and 55 mask operations plus 15 authenticated whole-block reuses in 108.441916834 seconds, with zero execution failures.',
 'review_verifier_history':'The first local audit attempt stopped on an unavailable rasterio import before verification/source operations. The final offline verifier uses existing numpy/Pillow and recomputes native affine placements from approved projected coordinates; no fresh geographic projection or geometry predicate is claimed. Final run passed.',
 'custody_scope':'All 279 saved input files inventoried, all 152 producer-listed product bodies checked, all 70 NPZ encoded and decoded members checked. Original 15 reused arrays matched their original public Git blob OIDs and hashes; original local metadata bodies matched public pins and the unchanged custody embedded in compatibility sidecars. The parent authenticated the prior public packet; this review made no remote source replay or fresh full-scene COG authentication.',
 'radiometry':'70 PB05 centres retain declared-offset/provider-applied contradiction and are qualitative raw-DN only. Eleven PB02.13 centres also remain unnormalized. Fixed RGB 0..3000/FCC 0..5000 display, nearest enlargement and no indices. Every SCL contradiction remains literal.',
 'edge_case17294':'Accepted only the visible valid-centre ground-like strip. RGB/NIR49x40 of49x49 and SCL25x20 of25x25 remain incomplete; missing rows are mask0/magenta with no imputation.',
 'scope_accounting':'All81 exact original keys are a subset of current held461 and disjoint from accepted10 and union133385. These49 are recommendations only. Root owns adoption and accounting; no accepted union or original ledger was changed.',
 'closure_boundary':'Visible dated facets only. Formal broader original question closure, hidden-surface inference, whole-cell truth and native-authority/repair credit remain zero.',
 'limitations':limits,'root_adoption_credit':0,'formal_broader_original_question_closure_count':0,'native_authority_or_repair_credit':0
}
(OUT/'review-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
md='''# Independent January 6 Batam81 review

Result: **49 supported bounded dated visible facets; 32 held**. This differs from the author's 52-facet proposal at point indices **16294, 17277, 17910**. All 29 author holds remain. The supported facets comprise **34 vegetation, 8 exposed-or-constructed ground-like margins, and 7 water-like bodies**.

All 81 native RGB/FCC/separate native-SCL details and all four wider contact pages were visually examined. The three added holds concern the exact marked patch, not the presence of nearby canopy or water:

- **16294:** muted olive-grey/brown coastal tip; adjacent red canopy does not establish the exact marked facet.
- **17277:** nearly black/neutral coastal band beneath canopy and pale features; clearer blue body below does not resolve shore shadow or littoral mixture at the marker.
- **17910:** muted grey/dark-blue seam; the coherent red canopy is beside the marker.

## Custody and scope

The offline verifier passed: 279 input files / 88,759,996 bytes inventoried; all 152 producer-listed product bodies checked; 70 NPZs / 76,629,469 encoded bytes, 172,595,200 decoded value/mask bytes and 172,613,120 NPY-member bytes including headers checked. All 15 reused arrays match original public whole-body hashes/Git OIDs, and their compatibility wrappers retain unchanged original custody. Native arrays reproduced all 81 detail images and four contact pages pixel-for-pixel, including fractional markers and absent-context masks. All five centre assets are valid at each of the 81 keys. Native affine placement was checked against the approved projected coordinates; no new geographic predicate was performed.

All 81 keys remain within the current held461 set and are disjoint from accepted10 and the accepted union133385. All January1/3 records remain structurally unchanged. January6 is new at these exact keys, regardless of observations at other keys. No source replay was performed.

## Scientific boundary

These are dated visible facets only. Canopy visibility does not answer hidden water/ground interface, understorey dryness, inundation or tide. Water-like and ground-like appearances do not establish depth, material, dryness, purity or whole-cell truth. The original broader physical questions and all independent source/owner/parent/portion/jurisdiction/territorial holds remain. Formal broader closure and native-authority/repair credit are zero.

Seventy PB05 centres remain qualitative raw-DN only because the provider/offset contradiction is retained; eleven PB02.13 centres also remain unnormalized. Literal SCL cloud/shadow/water disagreements remain context, not labels silently replaced by this review. Point17294 supports a visible ground-like strip only; the true bottom-frame missing rows remain mask0/magenta (RGB/NIR49x40, SCL25x20).

The first producer reader failed at the stale assertion before attempt-start or source reads. The retained corrected reader then completed the actual observation. That failure history is preserved. See review-summary.json for exact plan, reader, proposal and result pins, and independent-keyed-decisions81.jsonl for every decision and retained question. Root owns adoption/accounting; this review changes no ledger or accepted union.
'''
(OUT/'README-independent-review.md').write_text(md)
print(json.dumps({'counts':counts,'accepted':pin(OUT/'accepted49-owner-y-x.jsonl'),'held':pin(OUT/'held32-owner-y-x.jsonl'),'summary':pin(OUT/'review-summary.json'),'decisions':pin(OUT/'independent-keyed-decisions81.jsonl')},indent=2))
