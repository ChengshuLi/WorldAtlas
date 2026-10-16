import collections, gzip, hashlib, json
from pathlib import Path
ROOT=Path('/Users/chengshuli/Documents/Codex/2026-10-14/task')
B=ROOT/'idn-physical-dated778-plan-001'
A=B/'worker3-halmahera115-review-001'
O=Path(__file__).resolve().parent
def pin(p):
 b=p.read_bytes();return dict(path=str(p.relative_to(ROOT)),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def key(d):return tuple(d[k] for k in ('owner','y','x'))
def write(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
proposal=A/'proposed-halmahera115-firstdated-dispositions.jsonl'
assert pin(proposal)['sha256']=='028a599b146f897bf0899e5eeae0dc6a431747aeab9e39c6b9c016fb77017789'
rows=[json.loads(l) for l in proposal.open()]
summary=json.loads((A/'substantive-review-summary.json').read_text())
originals={key(r['original_key']):r for r in map(json.loads,gzip.open(str(B/'worker6-metadata/exact778-original-source-coordinate-current-reason.jsonl.gz'),'rt'))}
assert len(rows)==len({key(r['original_key']) for r in rows})==115
expected={k for k in originals if k[0]==22796}
assert {key(r['original_key']) for r in rows}==expected
raw={}
for p in (B/'worker6-metadata/first-raw-native-observation-001').glob('*/point-observations.jsonl'):
 for l in p.open():
  r=json.loads(l)
  if r['original_key']['owner']==22796:raw[key(r['original_key'])]=(r,p)
for r in rows:
 k=key(r['original_key']); old=originals[k]; rr,rp=raw[k]
 assert r['original_record']==old['original_record_unchanged']
 assert r['source_native_association']==old['source_native_association']
 assert r['separate_original_holds']==old['separate_original_holds']
 assert r['unchanged_centre']==old['centre_unchanged']==rr['centre_unchanged']
 assert r['original_point_index']==old['original_point_index']==rr['point_index']
 assert r['dated_item']==rr['item_id'] and r['acquisition_datetime']==rr['acquisition_datetime']
 assert r['processing_baseline']==rr['processing_baseline'] and r['processing_baseline'] in ('02.13','02.14')
 assert r['formal_adoption'] is None and r['repair_or_native_credit']==0
 for band,v in r['actual_native_source_values_and_context'].items():
  orig=rr['assets'][band]
  for field in ['raw_value','native_valid_mask','nodata_match','containing_array']:
   assert v[field]==orig[field]
  assert v['raw3x3']==orig['actual_raw3x3'] and v['mask3x3']==orig['actual_mask3x3']
  assert v['fractional_pixel']==orig['native_fractional_pixel']
positive=[r for r in rows if r['proposed_answer']]
assert len(positive)==30 and [r['review_index'] for r in positive]==summary['positive_review_indices']
assert collections.Counter(r['manual_disposition_category'] for r in rows)==summary['exact_partition']
specific={
2:'Marker is within the coherent green/red vegetation body west of the dark coastal water; no transfer from neighbouring shore pixels.',
8:'Marked body is green vegetation behind the settled coastal strip, rather than the strip or adjoining water.',
11:'Marker is in the recognizable mixed settled/cleared body; retain mixed cover rather than inventing an individual roof or uniform land-use class.',
15:'Marker is on the landward green/red body behind the coastal pale rim.',
16:'Coherent textured vegetated body at the marker is distinct from the nearby dark inlet.',
20:'Green/red body continuity supports the narrow dated cover-body statement behind the shallows. The nearby dark patch and exact wetness remain unclassified.',
21:'Visible green/red landward body at the marker remains distinguishable from the adjacent pale coastal rim.',
26:'Recognizable cleared/vegetated terrestrial body at the marker despite SCL6; SCL does not supply the answer.',
28:'Marker is on the textured green body immediately inland of the pale beach; no beach or exact waterline claim.',
31:'Marker is on the vegetated side of the narrow coastal strip; native registration and the nearby edge remain limitations.',
37:'Marker lies in coherent green textured body below the pale northern fringe.',
38:'Vegetated texture and inland red-body continuity support cover-body placement beside the inlet; inlet water/shadow remains separate.',
40:'Marked green body is inland of the pale western shore.',
44:'Marker occupies mixed vegetation/cleared cover behind the southwestern shoreline, not a precise parcel or material.',
51:'Marker is on the green inland side east of the pale beach strip.',
65:'Close coast placement supports only the green/red cover-body facet on the landward side, not a surveyed shoreline or pure pixel.',
67:'Marker on mixed green/cleared landward body is distinguishable from dark coastal water and nearby buildings.',
71:'Marker lies in the coherent vegetated inland body; the southern fringe is separate.',
75:'Marked green/cleared body is landward of the visible pale/dark coastal transition. Small dark interior patches do not establish dry substrate.',
82:'Marker is on textured vegetation west of the blue coastal fringe.',
85:'Marker is on the green canopy side of the pale southern beach; adjacent84 remains unresolved, so no neighbour transfer is used.',
90:'Patterned vegetated/cleared body at the marker is distinct from neighbouring coastal water, without inferring a specific land-use parcel.',
93:'Structured settlement/vegetation body at the marker supports a mixed dated body-location answer, not ownership or a particular building.',
95:'Marker is on the visible mixed green/cleared side below the northern coastal rim; no dry-floor or exact-edge conclusion.',
96:'Marker is on vegetated/mixed body inland of the dark southern water.',
98:'Marker is on the coherent green/red body above the coastal transition.',
103:'Marker lies on textured mixed vegetation/cleared body east of the western shore.',
104:'Marker is on the mixed green/cleared body inland of the western fringe.',
112:'Marker occupies the green/red vegetation side above the pale southern strip; adjacent111 is not automatically promoted.',
113:'Green/red body at marker lies immediately above the narrow shore strip; native support and registration limit edge precision.'}
assert set(specific)==set(summary['positive_review_indices'])
reviewed_positive=[dict(review_index=r['review_index'],original_key=r['original_key'],point_index=r['original_point_index'],date=r['acquisition_datetime'],independent_reason=specific[r['review_index']],disposition='SUPPORTED_ONLY_AS_AUTHORED_NARROW_DATED_COVER_BODY_LOCATION') for r in positive]
views=[pin(A/('contact-%02d.png'%i)) for i in range(1,7)] + [pin(A/('enlarged-%02d.png'%i)) for i in range(1,6)] + [pin(O/('positive-check-%02d.png'%i)) for i in range(1,6)]
out=dict(reviewer_identity='/root/cell_method_review',author_artifact_identity='worker3-halmahera115-review-001',disposition='PASS_WITH_SCIENTIFIC_LIMITS_FOR_ROOT_ADOPTION_REVIEW',
 proposal=pin(proposal),author_summary=pin(A/'substantive-review-summary.json'),scope=115,supported_authored_answers=30,narrowed_or_rejected_answer_keys=[],expanded_unknown_answers=0,remaining_questions=85,
 remaining_partition=dict(fine_shore_or_mixed_body_placement=55,cloud_haze_or_fringe=24,dark_water_shadow_body=6),
 actual_review=dict(all115_overviews_viewed=True,all30_author_enlarged_adverse_contexts_viewed=True,all30_proposed_positive_panels_independently_enlarged_and_viewed=True,views=views,source_access='Saved PNGs and local JSON metadata only; no raw source/network/native predicate or producer execution.'),
 supported_exact_positive_keys=reviewed_positive,
 consequential_adverse_findings=[
 '003/004 are genuinely cloud/veil contaminated; no annual image or SCL label supplies the missing body.',
 '061/062 retain bright cloud/halo and exact vegetated tongue/fringe placement uncertainty; the visible tongue alone does not place the centre.',
 '029/030/033 and073/074 have consequential low-signal shadow-versus-water/body ambiguity; six authored dark-body cases remain questions.',
 '043 marker is at a small dark inlet head adjoining strong vegetation; SCL4 does not resolve the exact body.',
 '006/007 and109 show real pale/dark coastal or inlet junctions at the marker; no unnecessary demand for water kind, tide, bank name or legal title was imposed.',
 '084 versus085 and111 versus112 are genuinely point-specific differences in placement relative to the visible pale shore; no nine-neighbour unanimity or voting criterion.',
 'The55 shore cases remain an accepted conservative unresolved set in this proposal; this review does not assert that no future or differently bounded image interpretation could answer any of them.'
 ],
 original_bindings_checked=['Exact115 keys and unchanged centres/point indices versus original778 inventory and actual dated point records.', 'Full original interval/owner/SID record, full source-version association and separate holds structurally unchanged.', 'Each reported raw value/mask/nodata/3x3/fractional position/array pin equals the actual local raw point metadata.', 'All seven source items are PB02.13/02.14 acquired January21, January26 or April10 2020;93 PB05 cases elsewhere excluded.'],
 scientific_limits=['30 supported statements concern visibly vegetated or mixed settled/cleared bodies at the dated native source point; no automatic binary land promotion.', 'No dry understory, permanent exposure, exact subpixel shoreline, whole Atlas-cell purity or current physical status is established.', 'Original Halmahera Selatan source-version association owner22796/sourceSID36375/shapeIDgb:IDN:ADM2:22746128B2838702785556 is retained, not a new native strict-interior, hierarchy, territorial, legal or ownership determination.', 'Fixed raw-DN display (DN/4000)^0.65 preserves spatial texture but is not absolute BOA reflectance, a calibrated index or a classification threshold; native SCL20m is contextual only.', 'This distinct review supports Root consideration, not Root adoption. Adopted/native/repair/integration/acceptance credit remains zero.'],root_adoption=None,native_or_repair_credit=0)
write(O/'halmahera115-distinct-scientific-review.json',out)
write(O/'supported-exact30-keys.json',[r['original_key'] for r in positive])
md='''# Distinct Halmahera115 dated scientific review

Reviewer `/root/cell_method_review`, distinct from the author. **Pass with limits: support all30 authored narrow dated cover/body-location answers; retain85 questions (55 shore/mixed placement,24 cloud/haze,6 dark-water/shadow). No keys were rejected or newly promoted.** The exact candidate is `028a599b146f897bf0899e5eeae0dc6a431747aeab9e39c6b9c016fb77017789`.

I actually viewed all115 contexts on six saved sheets, all30 enlarged adverse contexts, and independently enlarged/viewed every proposed positive on five additional sheets. At002 the marked vegetation body is west of the coastal water;026 shows a recognizable clearing/vegetation body despite SCL6;093 supports a mixed settled body without naming a building. Close-coast positives020/031/038/065/075/095 support only visible cover-body placement, with wetness and exact edge unresolved. At085 versus084 and112 versus111, the marker's position relative to the pale shore differs; neighbouring evidence was not transferred.

Actual clouds at003/004 and cloud-fringe contamination at061/062 prevent an underlying-body answer. Dark cases029/030/033 and073/074 do not securely distinguish water from shadowed cover. At043 a dark inlet meets vegetation; SCL4 does not resolve that junction.006/007 and109 have real coastal/body-placement uncertainty. These are substantive visibility/placement questions, not invented tide, water-kind, bank-name or legal-title requirements. I preserve the full conservative85-question set without claiming none could ever be answered by another supported observation.

The exact115 full original interval/owner/SID records, unchanged coordinates, affirmative original-source-version associations and separate holds match the retained original778 inventory. Reported actual source values, masks,3x3 contexts, fractional positions and array pins match the saved raw-point metadata. All seven scenes are PB02.13/02.14 acquired in2020; no PB05 offset-conflict point is included. The saved fixed raw-DN visibility transform is qualitative; SCL is contextual, not a classifier. No annual fallback, majority/unanimous-neighbour rule or new source operation was used.

These30 statements concern dated visibly vegetated or mixed settled/cleared bodies at native source support. They do not establish dry understory, permanent exposure, exact surveyed edge, whole-cell binary land/water, current jurisdiction, strict native containment, ownership or legal title. Original Halmahera Selatan source-version association remains affirmative and scoped. Root adoption and all native/repair/integration/acceptance credit remain pending/zero. Exact30 keys and per-key independent reasons are in the JSON review.
'''
(O/'halmahera115-distinct-scientific-review.md').write_text(md)
write(O/'handoff-manifest.json',dict(files=[pin(p) for p in sorted(O.iterdir()) if p.is_file() and p.name!='handoff-manifest.json'],review=pin(O/'halmahera115-distinct-scientific-review.json')))
print(json.dumps(dict(review=pin(O/'halmahera115-distinct-scientific-review.json'),markdown=pin(O/'halmahera115-distinct-scientific-review.md'),manifest=pin(O/'handoff-manifest.json')),indent=2))
