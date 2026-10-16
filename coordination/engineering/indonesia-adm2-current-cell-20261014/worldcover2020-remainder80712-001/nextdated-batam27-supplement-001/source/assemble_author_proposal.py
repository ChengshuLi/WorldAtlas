from pathlib import Path
import json,hashlib,collections,datetime
R=Path(__file__).resolve().parent
pin=lambda p:{'file':str(p.relative_to(R)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
prior={r['original_point_index']:r for r in map(json.loads,(R/'original34-prior-held-records.jsonl').read_text().splitlines())}
obs={};containers={}
for p in (R/'next-distinct-raw-native-observation-001').glob('S2*/point-observations.jsonl'):
 for r in map(json.loads,p.read_text().splitlines()):obs[r['point_index']]=r;containers[r['point_index']]=pin(p)
views=json.loads((R/'native-rawDN-context-pages/contact-inventory.json').read_text());v={}
for page in views['pages']:
 for panel in page['panels']:v[panel['point_index']]={**{k:page[k]for k in('file','bytes','sha256')},'panel_1based':panel['panel_1based']}
assert set(prior)==set(obs)==set(v)and len(obs)==34
holds={
18887:'The fractional marker lies on the muted canopy/open-water fringe; the native detail does not separate exposed water from low-signal canopy at this exact centre sufficiently.',
14459:'The marker remains on the narrow dark transition between the red canopy mass and the adjoining blue/dark body; water-side versus canopy-fringe placement is unresolved.',
14752:'A pale/grey, locally hazy canopy-edge transition crosses the marker. Nearby red canopy and open water do not settle the exact mixed fringe centre.',
14797:'The marker lies on the muted brown/red shoreline transition between the canopy and dark body. The native view leaves a local canopy, wet/exposed fringe or water ambiguity.',
15299:'The marker is on the pale shoreline/canopy transition band. The image does not adequately distinguish an exposed strip from vegetated or wet fringe at the centre.',
15378:'The marker is on the edge of the bright exposed-looking patch and surrounding red canopy. Precise visible-ground versus canopy-fringe placement remains ambiguous.',
16531:'The marker lies in a brown/olive transition strip beside red canopy and developed-looking ground. Vegetation versus exposed/constructed fringe is unresolved at the centre.'}
water={
14103:'The marker is on the connected dark blue body in the false-colour view, off the red canopy in the native detail. The RGB context gives a coherent dated visible water-like body placement.',
14833:'The native detail places the marker on the connected dark blue water-like body beside, rather than within, the red canopy. Wider RGB/FCC context supports that bounded dated visible-body answer.',
15496:'The marker is on the connected blue/dark water-like body to the right of the red canopy strip; the native detail and wider body context consistently place the centre on visible water.',
15544:'The marker is within the coherent dark body above the red canopy fringe, continuous with the wider water-like body. SCL dark/shadow context is retained and does not itself supply the answer.'}
ground={14410:'The marker falls on the coherent narrow pale linear ground/constructed-looking strip, traceable across the native RGB/FCC context. This is a dated visible exposed/constructed surface answer, without a material, land-use or dry-understory claim.'}
vegetation_reasons={
18886:'The marker is within the coherent dark-green canopy mass with a matching red false-colour canopy response; the adjacent water-like body is outside the marked centre.',
19039:'Native detail places the marker on the coherent red canopy side of the coastal edge, with corresponding dark-green RGB cover at the centre.',
19092:'The marker is on the coherent red canopy side of the coastal edge in native RGB/FCC detail. The source SCL cirrus label is retained as context; the bounded claim is visible cover only.',
19146:'The marked centre remains on the red canopy side of the nearby coastal boundary in the actual native detail. SCL cirrus context remains explicit; no underlying dry soil or quantitative radiometry is inferred.',
13666:'The marked centre is within a coherent dark-green/red canopy mass, distinct from the surrounding water-like body and the small bright patches elsewhere in the crop.',
14104:'The marker is within the coherent red false-colour canopy mass with corresponding dark-green RGB cover; nearby pale strips and open water do not cross the marked centre.',
14751:'Native detail places the marked centre within the red canopy mass below the coastal edge. Source SCL uncertainty is retained; the RGB/FCC body placement supplies the dated visible-cover answer.',
15031:'The marker lies inside the broad coherent red canopy strip, with dark-green RGB cover and the blue water-like body on the other side of the visible boundary.',
15273:'The marker lies within the red canopy mass below the pale coastal edge in the native detail; no exposed-ground or dry-understory answer is inferred.',
15327:'Native detail places the marker on the red canopy side just below the pale shoreline transition. The answer is limited to dated visible vegetation cover at the marked source position.',
15430:'The marker is within the coherent red canopy patch and corresponding dark-green RGB cover, below the coastal boundary.',
15482:'The marked centre is within the broad red canopy mass and dark-green RGB cover; the wider coastal edge lies outside the centre.',
15514:'The native detail places the marker on the red canopy side of the adjacent dark-body boundary. The bounded answer is visible vegetation cover, without underlying-ground or whole-cell purity claims.',
15542:'The marker is on the coherent red canopy mass, with dark-green RGB cover, to the right of the connected blue/dark body.',
15572:'The marker is inside coherent red canopy and dark-green RGB cover; no visible edge crosses the marked centre.',
15744:'The marker is on the coherent red canopy strip beside the blue/dark body, with corresponding green RGB cover at the centre.',
15770:'The marked centre lies inside the broad coherent red canopy mass and corresponding dark-green RGB cover.',
15801:'The marked centre lies inside the broad coherent red canopy mass; small pale patches elsewhere do not cross the marker.',
15817:'The marked centre is within the coherent red canopy mass and green RGB cover, away from the small exposed-looking patches.',
15830:'The marker remains within the red canopy mass to the left of the small pale patch, with corresponding dark-green RGB cover.',
15846:'The marker lies within the coherent red canopy mass and dark-green RGB cover, outside the small pale patches in the wider context.',
16487:'The marker is on the coherent red canopy strip between the blue/dark body and the brighter developed-looking ground; the bright ground does not cross the marked centre.'}
assert len(holds)==7 and len(water)==4 and len(ground)==1 and len(vegetation_reasons)==22
assert set(holds)|set(water)|set(ground)|set(vegetation_reasons)==set(obs)
rows=[]
for i,o in sorted(obs.items()):
 p=prior[i];assert p['original_key']==o['original_key']and p['unchanged_original_proposal']['centre_unchanged']==o['centre_unchanged']
 assert all(a['native_valid_mask']>0 and not a['nodata_match']for a in o['assets'].values())
 detail=R/f'native-rawDN-context-pages/point-{i}-native17-RGB-FCC-SCL25.png'
 status='held_specific_physical_question' if i in holds else 'author_proposed_bounded_dated_answer_not_adopted'
 answer=None if i in holds else 'dated_visible_water_like_body'if i in water else 'dated_visible_exposed_or_constructed_ground_strip'if i in ground else 'dated_visible_vegetation_cover'
 reason=(holds|water|ground|vegetation_reasons)[i]
 rows.append({'original_key':o['original_key'],'original_point_index':i,'prior_complete778_stage_record_unchanged':p,'new_actual_saved_observation_unchanged':o,'new_actual_observation_container':containers[i],'actual_views':{'wide':v[i],'native_detail_and_separate20mSCL':{**pin(detail),'panels_left_to_right':['17-native10m-RGB','17-native10m-NIR-R-G','25-native20m-SCL-context-only']},'contact_inventory':pin(R/'native-rawDN-context-pages/contact-inventory.json')},'author_proposed_disposition':{'status':status,'answer':answer,'actual_source_reason':reason,'original_remaining_question':p['dated_stage_outcome']['remaining_question'],'PB05_qualitative_only':False,'all_original_independent_source_owner_parent_portion_territorial_holds_retained':True,'adopted_or_native_credit':0}})
write=lambda p,rows:p.write_text(''.join(json.dumps(r,separators=(',',':'),ensure_ascii=False)+'\n'for r in rows))
write(R/'author-proposed34-nextdated-dispositions.jsonl',rows)
write(R/'author-proposed27-owner-y-x.jsonl',[[r['original_key'][k]for k in('owner','y','x')]for r in rows if r['original_point_index']not in holds])
summary={'kind':'author_actual_saved_view_interpretation_not_adoption','reviewed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'all34_wide_and_native_details_visually_inspected':True,'proposed_answers':27,'held_questions':7,'proposed_visible_vegetation':22,'proposed_visible_water_like_body':4,'proposed_visible_exposed_or_constructed_ground_strip':1,'all_previous_cloudy_observations_and_original_holds_preserved':True,'source_SCL_values_are_context_not_classifier':True,'no_normalization_or_indices_or_quantitative_reflectance_inference':True,'no_dry_understory_permanence_present_whole_cell_or_authority_claim':True,'new_adopted_or_native_credit':0,'proposal':pin(R/'author-proposed34-nextdated-dispositions.jsonl'),'proposed_keys':pin(R/'author-proposed27-owner-y-x.jsonl'),'rendering_inventory':pin(R/'native-rawDN-context-pages/contact-inventory.json')}
(R/'author-scientific-summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary))
