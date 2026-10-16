import json,pathlib,gzip,collections,math
from rasterio.warp import transform
from affine import Affine
P=pathlib.Path('/workspace/scratch/127991fc8b8e/.worldatlas-workspaces/a7d1c19eff225d01/0f0bb6420b8a7acb9fec7eb313216e39d9b15a0c1f51234aa558b7f5aa812c31/work/.cloud-work/original-session-completion-review-001');D=pathlib.Path(__file__).resolve().parent
js=lambda p:json.loads(p.read_text())
def jl(p):return [json.loads(l)for l in (gzip.open(p,'rt') if str(p).endswith('.gz') else p.open())]
def k(x):return tuple(x[n] for n in ['owner','y','x'])
assessment={k(x['original_request_unchanged']):x for x in js(P/'native-exception-evidence/original106-plus2-held.json')['repair106']}
crosswalk={k(x['original']):x for x in js(P/'native-exception-evidence/exact35-key-association-review.json')};counts=collections.Counter();details=[]
for r in jl(P/'native44-documented-exceptions-only.jsonl.gz'):
 key=k(r['original_key']);a=r['actual_retained_source_assessment_unchanged'];assert a==assessment[key];cat=a['assessment_category'];counts[cat]+=1;f=a['original_full_family_observations_unchanged'];g=a['government_observations_unchanged'];cw=r['distinct_malaysian_source_identity_crosswalk_review_if_available_unchanged'];assert cw==crosswalk.get(key)
 assert not a['fine_positive_original'] and not a['fine_positive_full'];assert not a['owner_or_hold_change']
 for fam,v in f['foreign_family_details'].items():
  if fam.endswith('ADM2'):assert not v['original_memberships'] and not v['full_memberships']
 state=bool(g and(g['cached_Gov_Sarawak_state_contacts']or g['new_Gov_Sabah_state_contacts']))
 district=[] if g is None else g['Gov_district_Sabah_contacts']+g['Gov_district_Sarawak_contacts']
 if cat=='MYS_genuine_IDN_vs_government_country_overlap':assert f['full_idn_memberships'] and state
 else:assert not f['full_idn_memberships']
 if 'government_outside' in cat:assert not state and not district
 if cat=='MYS_country_positive_no_existing_fine_source_coverage':assert state
 if cw:assert cw['association_review_status']=='held_aggregate_or_partition_mismatch' and not cw['distinct_candidate_owner_sets']
 details.append({'key':list(key),'category':cat,'full_IDN_members':f['full_idn_memberships'],'government_state_positive':state,'government_district_contacts':district,'crosswalk_status':cw['association_review_status']if cw else None,'question':r['original_package_review_disposition']['remaining_question']})
assert sorted(counts.values())==[3,11,15,15]
Q=P/'source-quality33';original={k(x['original_key']):x for x in jl(Q/'original778-source-coordinate-current-reason.jsonl.gz')};points=[]
for f in (Q/'next-distinct-raw-native-observation-001').glob('*/point-observations.jsonl'):points+=jl(f)
for p in points:
 centre=p['centre_unchanged']; o=original[k(p['original_key'])];assert centre==o['centre_unchanged']
 for asset,a in p['assets'].items():
  h=a['actual_header'];xs,ys=transform('EPSG:4326',h['crs'],[centre['longitude']],[centre['latitude']]);col,row=(~Affine(*h['transform'][:6]))*(xs[0],ys[0]);assert abs(row-a['native_fractional_pixel'][0])<1e-7 and abs(col-a['native_fractional_pixel'][1])<1e-7;assert [math.floor(row),math.floor(col)]==a['native_containing_pixel']
  bh,bw=h['block_shapes'][0]; filename=pathlib.Path(a['containing_array']['file']).stem;assert filename==f'block-{math.floor(row)//bh:02d}-{math.floor(col)//bw:02d}'
result={'all44_historical_assessments_unchanged':True,'all44_specific_categories_match_actual_memberships':True,'counts':dict(counts),'all33_exact_original_centres_unchanged':True,'all165_asset_grid_and_containing_block_joins':True,'exceptions':details}
(D/'exception-and-coordinate-verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k!='exceptions'},indent=2))
