from pathlib import Path
import json,hashlib,collections
P=Path(__file__).resolve().parent;S=P/'source-snapshot'
rows=[json.loads(x) for x in (S/'author-proposed72-nextdated-dispositions.jsonl').read_text().splitlines()]
text='''12136|The mark intersects a pale coastal strip and dark canopy; the grey-brown FCC transition does not establish ground, cover or wet fringe at the marked position.
12162|The marker is in the muted brown-grey transition between red cover and the dark body; a specific visible cover or water/ground placement remains ambiguous.
12192|The marked pale pixel belongs to a connected linear pale strip visible in both RGB and FCC, despite the separate SCL cloud context. Supports only exposed/constructed ground-like appearance.
12205|The centre lies on a coherent grey pale patch in the textured developed-looking strip, spatially distinct from the adjoining dark body. Material and use are not identified.
12219|Red FCC cover reaches the marker with matching green RGB cover on the canopy side of the margin; the coarse SCL water label does not override the visible facet.
12242|At the mark, grey-brown and red cover are intermixed near the developed fringe. Adjacent vegetation does not adequately identify the marked surface.
12256|The mark is inside continuous dark-green RGB and red FCC cover, away from the local water-like boundary.
12276|The mark falls within the coherent red/green cover mass; the dark water-like body lies outside the marked patch.
12278|Red FCC cover and matching dark-green RGB texture are continuous through the marker below the brighter shore context.
12279|The mark follows a coherent thin pale strip across the coastal context in both RGB and FCC. Only the dated exposed/constructed ground-like strip is supported.
12291|The marked dark-red patch remains connected to red cover above the nearby blue body; supports visible cover on that side, with close-fringe uncertainty retained.
12300|The mark meets the dark-body and brown/pale strip transition. Wet edge, exposed strip and body placement remain inseparable at this native support.
12304|The mark is a dark developed/coastal fringe among pale structures and red cover; neither ground, canopy nor water-like placement is adequately isolated.
12318|Red FCC cover continues through the mark on the canopy side of the pale linear fringe, with corresponding green RGB context. The conflicting SCL water context is retained.
12349|The marked muted brown fringe above red canopy is not a distinct canopy, exposed ground or water-like patch.
12354|The marker is within a coherent red canopy-looking mass and dark-green RGB cover; the connected blue body is outside it.
12360|The marked location lies within the continuous red/green cover below the coastal boundary.
12374|The mark is in a darker red patch continuous with the surrounding red cover; nearby pale shore context does not obscure that dated visible facet.
12388|The fractional mark is on the muted grey-brown boundary below the bright tan patch and beside red canopy. Nearby red cover does not establish canopy at this marked native position; ground/wet/canopy fringe remains unresolved.
12452|The mark is on a coherent red/green cover patch beside the narrow pale strip; the blue/dark body is farther outside the strip.
12454|Broad red FCC and dark-green RGB cover pass through the marker without a competing local body boundary at the mark.
12455|The marker remains on the red cover side of the nearby dark margin. Supports dated visible cover only, not a pure cell or exact surveyed shoreline.
12456|The mark follows the coherent narrow grey/pale linear strip in the textured developed-looking area. Nearby bright cloud and red cover are separately visible.
12461|The mark is on red cover at the side of the coastal indentation. Supports that cover facet while the nearby fringe and what lies underneath remain unresolved.
12467|A coherent blue/dark channel is visible nearby, but the actual mark is on its dark reddish upper margin adjoining canopy. The image does not adequately distinguish water-side placement from shadowed or mixed canopy fringe at the mark; SCL dark context is not a remedy.
12479|The mark lies on the dark reddish diagonal channel margin, with distinctly blue channel pixels immediately adjacent. Canopy/wet/shadow mixing at the marked position prevents a reliable water-like body answer.
12493|The mark intersects the narrow pale bank and dark body transition. Neither exposed strip nor water/wet fringe is sufficiently isolated at the centre.
12501|The marked tan-brown area is continuous with the exposed/constructed-looking strip beside the brighter developed patch and distinct from the dark body. No material or use claim follows.
12516|The mark lies on the blue/dark body below red cover and above the pale crossing strip. Its connected water-like morphology supports dated placement only; close-bank and shadow limits remain.
12562|The marker is inside the red/green cover patch beside the pale linear strip, supporting visible cover only.
12581|The mark is on the connected blue/dark side of the straight pale edge, supporting a water-like visible body at the marked position without exact-bank or pure-cell claims.
12590|The mark is in the dark developed-coast transition beside pale structures. Water, shadow and ground fringe cannot be separated sufficiently.
13278|The marked patch is coherent red/green cover to the right of the pale strip, independent of the separate SCL edge labels.
13308|The centre is in the blue/dark connected body below the red cover edge. Supports water-like visible morphology only; shadow contamination and precise bank placement remain unresolved.
13394|The mark falls on the blue/dark connected body below the red canopy margin. Only dated water-like placement is supported, with finite-support fringe limits.
13522|Red FCC cover reaches the actual mark at the side of the dark coastal boundary. SCL shadow context remains and no dry-understory conclusion is drawn.
13547|The mark is in coherent red FCC and green RGB cover below the dark indentation; adjacent grey patches do not replace the marked evidence.
13610|A muted brown-grey patch at the centre adjoins cover and dark-body boundaries. Exposed/wet ground and shallow or water-side fringe remain ambiguous.
13709|The marker is inside coherent dark-green RGB and red FCC cover despite some dark texture variation.
13737|The marked dark-red patch is contiguous with red cover and matching green RGB texture. Supports visible cover, with local shadow and underneath limits retained.
13932|The mark is within continuous red FCC and dark-green RGB cover; cloud context near the broader scene does not cover this marked patch.
13936|The marker lies in coherent red/green cover with local texture variation, supporting only the dated visible canopy-looking facet.
14255|A bright cloud/haze veil and muted mixed colours reach the marked position. Surface-specific placement is not reliably resolved beneath it.
14348|The exact mark is at a muted dark-body/red-cover transition under cirrus context. The adjacent clear cover cannot settle the marked fringe.
14350|The mark is inside coherent red FCC and dark-green RGB cover, separated from the nearby dark margin.
14371|Despite separate SCL cirrus context and some muted texture, the actual mark lies within continuous red FCC and matching green RGB cover beside a distinct pale line. No cloud-free quantitative claim is made.
14605|The mark lies on the narrow red-cover/dark-body boundary. A coherent interior cover patch nearby does not resolve the exact fringe placement.
14615|The mark is in a very dark narrow margin between red cover and the blue/dark body, leaving water versus shadowed cover/fringe unresolved.
14624|Coherent red FCC and green RGB cover pass through the marker below the local dark indentation.
14741|The marker lies at the very dark cover/water transition; the adjacent red cover does not sufficiently resolve the exact marked fringe.
14876|The marker lies within coherent red/green cover below the pale coastal transition, supporting the visible-cover facet only.
14878|The mark is within the red/green cover tongue on the cover side of the nearby dark body.
14966|The marked pale/tan linear strip is traceable in both RGB and FCC along the margin, distinct from the dark body. Only exposed/constructed ground-like appearance is supported.
14998|The mark is inside a coherent red/green cover mass beyond the immediate dark coastal boundary.
15063|Red FCC and green RGB cover are continuous through the marker along the cover side of the dark boundary.
15116|Bright cloud/haze covers the marked area, so a reliable specific ground, canopy or water placement is unavailable.
15117|The marked centre is within a red/green cover patch below the nearby blue/dark boundary.
15147|Continuous red FCC and dark-green RGB cover occupy the marked position; nearby boundary structure remains separate context.
15215|The marker is inside coherent red/green cover along the narrow cover body, without resolving underlying water or whole-cell purity.
15216|The mark is on the tan-grey shoreline transition beside red cover and dark body. Wet/exposed ground versus mixed cover fringe remains unresolved.
15268|The marker is at the red-cover/dark-water boundary and the narrow exact fringe cannot be assigned reliably.
15344|The marked mixed developed-looking patch is muted by haze/cirrus and does not provide an adequately isolated visible surface.
15401|Muted cloud/haze reaches the mark beside dark body and red cover. The exact visible surface remains ambiguous.
15404|The mark is in the narrow very dark coastal fringe beside red cover. Water and shadowed cover remain inseparable at the centre.
15405|The marked position is on coherent red FCC and dark-green RGB cover below the coastal boundary, supporting only that visible cover.
15649|The mark is inside the continuous red/green cover mass; nearby pale patches and water remain context.
15651|The mark follows a coherent tan exposed/constructed-looking strip curving around the developed-looking patch in both RGB and FCC. Material, dryness and permanence are unresolved.
15706|The centre is on a teal-grey transitional fringe adjoining red cover and dark body. Shallow water, wet margin and mixed cover cannot be separated reliably.
15766|Red FCC and green RGB cover occupy the actual mark just inside the cover side of the dark indentation. The immediate fringe and underneath remain limited.
15786|The mark is on a muted grey-brown patch under haze between bright ground and red cover; the specific marked surface is unresolved.
15876|A very dark brown-black patch at the centre lacks reliable cover/ground/water separation; shadow and mixed adjacent cover remain material.
15989|The marked centre is in coherent red FCC and green RGB cover, supporting the dated visible facet only.'''
reasons={int(line.split('|',1)[0]):line.split('|',1)[1] for line in text.splitlines()}
assert len(reasons)==72
rejected={12388,12467,12479};answer=[];held=[];allrows=[]
limits=['Dated visible appearance at the unchanged original coordinate and finite native 10 m support, not pure-pixel or whole-cell truth.','SCL is separate 20 m source context only and never supplies body truth; masks establish data validity, not clear-sky visibility.','No underneath/understory dryness, exact tide, surveyed shore/bank, material/use, annual persistence or current-surface conclusion.','All historical source observations and independent source, owner, parent, selected-portion and territorial/jurisdiction holds remain unchanged.','No source-native authority, accepted repair or implementation credit; Root scientific binding remains pending.']
for r in rows:
 id=r['original_point_index'];d=r['author_proposed_disposition'];supported=d['answer'] is not None and id not in rejected
 z={'original_key':r['original_key'],'original_point_index':id,'original_specific_question':d['original_remaining_question'],'observation_item':'S2A_48NUG_20200106_0_L2A','observation_datetime':'2020-01-06T03:37:41.663000Z','independent_status':'supported_bounded_dated_visible_facet_pending_root' if supported else 'held_specific_physical_question','supported_answer':d['answer'] if supported else None,'review_reason':reasons[id],'remaining_specific_question':None if supported else reasons[id],'author_proposed_answer_unchanged':d['answer'],'author_proposal_overruled_to_hold':id in rejected,'views_inspected':r['actual_views'],'SCL_context_value_retained':r['new_actual_saved_observation_unchanged']['assets']['scl']['raw_value'],'original_key_and_centre_unchanged':True,'earlier_observations_retained':True,'independent_limits_retained':True,'accepted_question_credit':0,'native_authority_or_repair_credit':0}
 allrows.append(z);(answer if supported else held).append(z)
def jl(name,a):(P/name).write_text(''.join(json.dumps(x,separators=(',',':'))+'\n' for x in a))
def pin(path):
 b=path.read_bytes();return {'file':path.name,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
jl('independent72-keyed-dispositions.jsonl',allrows)
jl('supported46-owner-y-x.jsonl',[[z['original_key'][k] for k in ('owner','y','x')] for z in answer])
jl('held26-keyed-reasons.jsonl',held)
assert len(answer)==46 and len(held)==26
manifest={'contact_pages':[r['actual_views']['wide'] for r in rows if r['actual_views']['wide']['panel_1based']==1],'native_details':[r['actual_views']['native_detail_and_separate20mSCL'] for r in rows],'all_contact_pages_viewed_via_view_image':True,'all72_native_RGB_FCC_and_separate20mSCL_details_viewed_via_view_image':True,'repeat_borderline_inspections':[12388,12467,12479],'author_acknowledged_no_additional_resolving_evidence_for_three_downgrades':True,'method':'Manual visual review of the existing exact images only; no source reread, no raster rendering/acquisition replay, no threshold classifier, no derived index.'}
(P/'visual-inspection-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
summary={'status':'SUPPORT_46_BOUNDED_DATED_VISIBLE_FACETS_KEEP_26_HELD_PENDING_ROOT','reviewer':'/root/review_batam72_visible_facets','complete_original_scope':72,'supported_facet_count':46,'retained_hold_count':26,'supported_class_counts':dict(collections.Counter(x['supported_answer'] for x in answer)),'original_author_proposal_count':49,'author_proposal_preserved':pin(S/'author-proposed72-nextdated-dispositions.jsonl'),'newly_retained_holds':[{k:r[k] for k in ['original_key','original_point_index','review_reason']} for r in allrows if r['author_proposal_overruled_to_hold']],'original_specific_question':'Actual wide RGB and false-colour context remains cloud/haze obscured or locally low-contrast at the marked centre; a coherent ground, canopy or water placement is not sufficiently resolved.','rule':'A supported dated visible vegetation, exposed/constructed ground-like strip or water-like placement at the unchanged actual native centre resolves this bounded original cloud/haze/body-placement question. Nearby or merely complementary surface evidence does not resolve it. Historical cloudy observations and independent limits remain.','limits':limits,'complete_custody_review':pin(P/'custody-review.json'),'verified_file_pins':pin(P/'verified-file-pins.json'),'dispositions':pin(P/'independent72-keyed-dispositions.jsonl'),'literal_supported_keys':pin(P/'supported46-owner-y-x.jsonl'),'held_reasons':pin(P/'held26-keyed-reasons.jsonl'),'visual_inspection':pin(P/'visual-inspection-manifest.json'),'custody_verifier':pin(P/'verify_custody.py'),'source_snapshot':str(S),'accepted_question_credit':0,'native_authority_or_repair_credit':0,'new_source_calls':0,'Root_adoption':None}
(P/'final-review.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
