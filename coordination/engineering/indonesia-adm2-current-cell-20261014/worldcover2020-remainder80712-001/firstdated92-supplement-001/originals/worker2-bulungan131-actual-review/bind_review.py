import collections, gzip, hashlib, json
from pathlib import Path

ROOT = Path('/Users/chengshuli/Documents/Codex/2026-10-14/task')
OUT = Path(__file__).resolve().parent
BASE = ROOT / 'idn-physical-dated778-plan-001/worker6-metadata'
RAW = BASE / 'first-raw-native-observation-001/S2B_50NNJ_20200222_0_L2A'
def read(p): return json.loads(p.read_text())
def pin(p):
    b=p.read_bytes()
    return dict(path=str(p.relative_to(ROOT)), bytes=len(b), sha256=hashlib.sha256(b).hexdigest())
def write(p,d): p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def lines(p):
    with gzip.open(str(p),'rt') as f: return [json.loads(s) for s in f]
def key(d): return tuple(d[k] for k in ('owner','y','x'))
def zipped(p, rows):
    b=b''.join((json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n').encode() for r in rows)
    p.write_bytes(gzip.compress(b,mtime=0))
    return dict(**pin(p), decoded_bytes=len(b), decoded_sha256=hashlib.sha256(b).hexdigest())

# These are actual manual readings of all ten detail sheets, after all six wide sheets.
pages={
1:dict(V=[2,6],W=[12],L=[10,11],A=[1,3,4,5,7,8,9]),
2:dict(V=[1,6,7,8,9,10,12],W=[],L=[],A=[2,3,4,5,11]),
3:dict(V=[2,4],W=[3,8,12],L=[1,10,11],A=[5,6,7,9]),
4:dict(V=[10],W=[3,8],L=[1,6,11],A=[2,4,5,7,9,12]),
5:dict(V=[7,10,11],W=[2,3,6,8,9,12],L=[4],A=[1,5]),
6:dict(V=[8,11,12],W=[2,5],L=[],A=[1,3,4,6,7,9,10]),
7:dict(V=[1,4,9,10,11],W=[6,7,8,12],L=[2],A=[3,5]),
8:dict(V=[4,8,10],W=[2,6,9],L=[],A=[1,3,5,7,11,12]),
9:dict(V=[3,6,7],W=[],L=[1,11,12],A=[2,4,5,8,9,10]),
10:dict(V=[],W=[],L=[],A=[1])}
details=read(OUT/'native-detail-pages/contact-inventory.json')
wide=read(OUT/'native-context-pages/contact-inventory.json')
raw=[json.loads(s) for s in (RAW/'point-observations.jsonl').read_text().splitlines()]
originals=lines(BASE/'exact778-original-source-coordinate-current-reason.jsonl.gz')
original_by_key={key(r['original_key']):r for r in originals}
raw_by_id={r['point_index']:r for r in raw}
assert len(raw)==len(raw_by_id)==131
decisions={}
wide_loc={}
for page in wide['pages']:
    assert hashlib.sha256(Path(page['path']).read_bytes()).hexdigest()==page['sha256']
    for panel in page['panels']:
        wide_loc[panel['point_index']]={'page':pin(Path(page['path'])),'panel':panel}
for page in details['pages']:
    assert hashlib.sha256(Path(page['path']).read_bytes()).hexdigest()==page['sha256']
    ps=pages[page['page_1based']]
    expected={p['panel_1based'] for p in page['panels']}
    assigned=[n for ns in ps.values() for n in ns]
    assert set(assigned)==expected and len(assigned)==len(expected)
    for panel in page['panels']:
        code=next(c for c,ns in ps.items() if panel['panel_1based'] in ns)
        pid=panel['point_index']
        assert pid not in decisions
        decisions[pid]=dict(code=code, detail={'page':pin(Path(page['path'])),'panel':panel})
for r in raw:
    pid=r['point_index']
    if pid not in decisions:
        assert all(r['assets'][a]['native_valid_mask']==0 and r['assets'][a]['raw_value']==0 for a in ('red','green','blue','nir'))
        assert r['assets']['scl']['raw_value']==0
        decisions[pid]=dict(code='N', detail=None)
counts=collections.Counter(d['code'] for d in decisions.values())
assert dict(counts)==dict(V=29,W=21,L=13,A=46,N=22), counts
assert decisions[7233]['code']=='A' and decisions[7291]['code']=='A'
assert all(decisions[i]['code']=='W' for i in [6103,6113,5351,5439])
assert all(decisions[i]['code']=='V' for i in [7298,7304,3430,6314,6763,2644,3322])
cloud={2672,3451,3473,6158,7164,7278}
shadow={2685,6135,6696,6898}
assert all(decisions[i]['code']=='A' for i in cloud|shadow)
reasons={
'V':'The fractional source point lies on a coherent visible vegetation/canopy body in dated RGB and NIR-R-G context. This does not establish dry ground beneath vegetation.',
'W':'The fractional source point lies within a coherent visible water-like pond/channel/river body in dated RGB and NIR-R-G context; spatial body placement supports this bounded dated interpretation.',
'L':'The fractional source point lies on a visible exposed/constructed corridor or surface at the native image scale. Its surveyed edge, material and permanent dryness are not established.',
'A':'Actual dated context does not settle the exact centre body: pond water versus drained/vegetated floor, narrow bank/fringe placement, or local mixed surface remains consequentially ambiguous.',
'N':'All four actual RGBNIR centre masks are zero and raw values are nodata zero; SCL is also zero. This acquisition supplies no interpretable centre observation; no ocean or annual-fallback conclusion.'}
answers={'V':'Visible vegetation/canopy body at the dated source point.', 'W':'Visible water-like body at the dated source point.', 'L':'Visible exposed/constructed corridor or surface at the dated source point.'}
rows=[]
for r in raw:
    pid=r['point_index']; k=key(r['original_key']); old=original_by_key[k]; d=decisions[pid]; c=d['code']
    assert old['original_point_index']==pid and old['centre_unchanged']==r['centre_unchanged']
    assert k[0]==22698
    reason=reasons[c]
    if pid in cloud: reason='Actual cloud/haze/veil obscures the relevant centre body despite nonzero native masks; its underlying body remains unresolved.'
    if pid in shadow: reason='The actual dark centre cannot be securely distinguished between shadow and water/local body; retain the question.'
    followup=dict(reviewer_identity='/root/cell_method_review', status='proposed_bounded_dated_answer' if c in answers else 'unresolved', manual_code=c,
      bounded_answer=answers.get(c), scientific_reason=reason, acquisition_datetime=r['acquisition_datetime'],
      source_item_id=r['item_id'], original_source_version_association_only=True,
      actual_source_observation_unchanged=r, overview_view=wide_loc[pid], detail_view=d['detail'],
      display_method=details['conversion'], interpretation_method='Individual manual fractional-centre morphology/body-placement reading of saved native RGB/FCC context; SCL is contextual, not a classifier; no unanimity/majority or spectral threshold rule.',
      limits=['Single 2020-02-22 acquisition; not current or permanent physical truth.', 'Native georegistration and finite pixel support limit exact narrow edges.', 'Vegetation does not prove dry substrate; water-like body does not establish permanence, hydrologic kind, name, tide or bank.', 'Original source-version membership is retained; no jurisdiction, legal title, sovereign winner, administrative certification or whole-cell status follows.', 'All original independent source/territorial/relative holds remain structurally unchanged.'],
      proposed_completed_question_credit=int(c in answers), adopted_completed_question_credit=0, native_authority_or_repair_credit=0, root_adoption=None)
    out=dict(old); assert 'dated_native_followup' not in out
    out['dated_native_followup']=followup
    assert {a:b for a,b in out.items() if a!='dated_native_followup'}==old
    rows.append(out)
positive=sorted(key(r['original_key']) for r in rows if r['dated_native_followup']['proposed_completed_question_credit'])
account=ROOT/'idn-physical-residual41305-policy-001/other9393-publication-preparation/files/coordination/engineering/indonesia-adm2-current-cell-20261014/worldcover2020-remainder80712-001/annual-other9393-supplement-001/accounting'
known_path=account/'known-exact-adopted-union133068-owner-y-x.jsonl.gz'
res_path=account/'specific-residual-union778-owner-y-x.jsonl.gz'
known={tuple(r) for r in lines(known_path)}; residual={tuple(r) for r in lines(res_path)}
assert len(known)==133068 and len(residual)==778 and not known & residual
assert set(positive)<=residual and not set(positive)&known
assert {key(r['original_key']) for r in raw}<=residual
candidate=zipped(OUT/'proposed-bulungan131-dated-dispositions.jsonl.gz', rows)
positive_pin=zipped(OUT/'proposed-positive63-owner-y-x.jsonl.gz',positive)
write(OUT/'manual-detail-decisions.json', dict(reviewer='/root/cell_method_review',pages=pages,counts=dict(counts),point_decisions={str(k):v['code'] for k,v in sorted(decisions.items())},cloud_haze_points=sorted(cloud),dark_body_shadow_points=sorted(shadow)))
report=dict(disposition='SUPPORTED_WITH_LIMITS_FOR_ROOT_ADOPTION_REVIEW; NOT_ADOPTED', reviewer='/root/cell_method_review',
  exact_scope=dict(original_remaining=778,cohort=131,owner=22698,source_name='Bulungan',source_shapeID='gb:IDN:ADM2:22746128B10941975158621',sourceID=36336),
  proposed_answers=63, proposed_partition=dict(vegetation_canopy=29,visible_water_like_body=21,exposed_constructed_surface_or_corridor=13),unresolved=68,unresolved_partition=dict(actual_nodata=22,valid_mask_real_body_cloud_or_placement_uncertainty=46),
  candidate=candidate,positive_keys=positive_pin,source_point_bank=pin(RAW/'point-observations.jsonl'), source_item_complete=pin(RAW/'item-complete.json'),original_full_source_association_inventory=pin(BASE/'exact778-original-source-coordinate-current-reason.jsonl.gz'),
  plan_sha256='3145162ef32ff4f686a6223afb25ea64789f1f0e65e7486695da925069cdc52f', reader_sha256='60b54f6e38a1b171330ae46ee575701118346c2cc4f6052f41b08c69fcf25f6e',
  views=dict(overview_pages=6,detail_pages=10,all_personally_viewed=True,overview_inventory=pin(OUT/'native-context-pages/contact-inventory.json'),detail_inventory=pin(OUT/'native-detail-pages/contact-inventory.json')),
  source_method=dict(item='S2B_50NNJ_20200222_0_L2A',acquisition_datetime=raw[0]['acquisition_datetime'],processing_generation_time=raw[0]['processing_generation_time'],processing_baseline='02.14',normalization='DN * 0.0001 exactly once; offset 0; fixed RGB 0..0.30 / NIR-R-G 0..0.50 for display only',native_RGBNIR_resolution_m=10,native_SCL_resolution_m=20,license_provenance='Copernicus Sentinel data 2020; Element84 Earth Search distribution; original ESA Sentinel Legal Notice retained in actual source metadata.'),
  substantive_findings=['63 actual dated centre/body placements supported by jointly viewed RGB/FCC spatial morphology, not annual category fallback.', '22 actual all-band nodata centres remain unanswered; nonzero masks do not guarantee clear sky for the other 109.', 'Cloud/haze points 2672,3451,3473,6158,7164,7278 and shadow/body ambiguity points 2685,6135,6696,6898 remain unknown.', '7233 and 7291 retain consequential centre/fringe uncertainty.', 'SCL contextual mismatches retained: 2644/3322 visible vegetation despite SCL6; 3430 vegetation despite SCL2; 6314/6763 vegetation despite SCL7; 5351/5439 water-like body despite SCL2.'],
  exact_conservation=dict(current_known_adopted=133068,current_residual=778,known_pin=pin(known_path),residual_pin=pin(res_path),proposed_positive_overlap_known=0,proposed_positive_outside_residual=0,cohort_duplicate_keys=0,conditional_only_if_Root_adopts=dict(known=133131,residual=715,original=133846)),
  limits=['Reviewer proposes; Root has not adopted this delta.', 'No native qualification, owner-zero, binary whole-cell land/water, repair, integration or acceptance credit.', 'All 131 full original inventory/scientific records and separate holds unchanged; only dated_native_followup appended.', 'No source/network/value reread or native predicate execution in binding; rendering used saved local arrays only.', 'Complete original actual source receipt covers 85 item blocks; reviewer rendered 68 distinct RGBNIR arrays for overview and 56 for detail, not a claim of independently reading all 85 block values.', 'PB05 93-point offset ambiguity belongs to other cohorts; this PB02.14 cohort has no such normalization conflict.'])
write(OUT/'bulungan131-dated-scientific-review.json',report)
md='''# Bulungan131 actual dated interpretation review

Independent reviewer: `/root/cell_method_review`. Supported with limits for Root review; no adoption or native credit.

All 131 original remaining Bulungan points were reviewed on all six 49-pixel context sheets; all 109 mask-valid centres were also reviewed on ten 17-pixel detail sheets with the actual fractional centre. The 2020-02-22 Sentinel-2 PB02.14 observation supports **63 proposed bounded dated answers: 29 vegetation/canopy, 21 visible water-like bodies, and 13 exposed/constructed surfaces or corridors**. **68 remain unknown: 22 actual all-band nodata and 46 consequential cloud, shadow, pond-floor/body or narrow-edge ambiguities.**

The distinction comes from actual centre/body placement in RGB and NIR-R-G context. Clear pond interiors at 6103/6113 differ from brown pond-floor/fringe cases; 7233 and 7291 remain questions. Actual cloud/haze at 2672/3451/3473/6158/7164/7278 blocks interpretation despite valid masks. SCL is retained contextual evidence, not truth: visible vegetation at 2644/3322 despite SCL6, vegetation at 3430 despite SCL2, and water-like bodies at 5351/5439 despite SCL2 demonstrate why no automatic SCL rule was used.

Display used raw DN × 0.0001 once, zero offset, fixed RGB 0–0.30 and FCC 0–0.50 display ranges, nearest enlargement and unpainted fractional centres. No source resampling, spectral threshold, majority or unanimous-neighbour rule was used. Native SCL remains its separate 20 m product. This is one dated image, not an annual or current assertion; vegetation does not establish dry ground, and visible water does not establish permanence, water kind, tide, name or bank. Narrow corridors retain native-resolution/registration limits.

Every output preserves the full original source association and scientific record, including independent territorial/relative/source holds, and appends only `dated_native_followup`. Original-source-version Bulungan membership is not a new jurisdiction or legal determination. The 63 unique proposed keys are within the exact 778 residual and disjoint from 133068 adopted keys. Only if Root adopts them would accounting become 133131 answered / 715 remaining of 133846. No native qualification, owner-zero, binary whole-cell status, repair, integration or acceptance claim is made.

Exact candidate, input, source, view and key hashes are recorded in `bulungan131-dated-scientific-review.json`; all original raw point records are embedded unchanged in the follow-up. Binding and displays read saved local material only; no source acquisition or scientific operator replay occurred.
'''
(OUT/'bulungan131-dated-scientific-review.md').write_text(md)
artifacts=[OUT/'manual-detail-decisions.json',OUT/'proposed-bulungan131-dated-dispositions.jsonl.gz',OUT/'proposed-positive63-owner-y-x.jsonl.gz',OUT/'bulungan131-dated-scientific-review.json',OUT/'bulungan131-dated-scientific-review.md',OUT/'bind_review.py',OUT/'render_saved_contexts.py',OUT/'render_saved_details.py']
artifacts += sorted((OUT/'native-context-pages').glob('*'))+sorted((OUT/'native-detail-pages').glob('*'))
write(OUT/'handoff-manifest.json',dict(reviewer='/root/cell_method_review',files=[pin(p) for p in artifacts if p.is_file()],candidate_sha256=candidate['sha256'],scientific_review=pin(OUT/'bulungan131-dated-scientific-review.json'),adopted_credit=0,native_credit=0))
print(json.dumps(dict(counts=dict(counts),candidate=candidate,review=pin(OUT/'bulungan131-dated-scientific-review.json'),manifest=pin(OUT/'handoff-manifest.json')),indent=2))
