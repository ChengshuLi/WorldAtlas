"""Bounded producer controls; no complete target/source overlays occur here."""
import hashlib,json
from shapely.geometry import Polygon
from producer import ROOT,SCOPE,canon,load_gb,metric,verify_body,feature_roster,validate_target_features,verify_gb_metadata
from mlit_shapefile import rings_to_geometry

def sha(b):return hashlib.sha256(b).hexdigest()
def fail_closed(fn):
 try: fn()
 except (ValueError,KeyError,TypeError): return True
 return False

gb=load_gb(); contacts={x.rsplit(':',1)[-1] for x in SCOPE['contacts']}
if len(contacts)!=21:raise ValueError('scoped contact roster count differs')
for name,features,bodysha in gb:
 if len(features)!=1742 or not contacts<=set(features):raise ValueError('complete product roster/contact binding control failed')
validate_target_features(SCOPE['full_candidate_features'],SCOPE['full_current_contact_features'])
target_mutation=json.loads(json.dumps(SCOPE['full_candidate_features']))

def change_first_x(node):
 if isinstance(node,list) and node and isinstance(node[0],(int,float)):
  node[0]+=0.0001;return
 if isinstance(node,list):
  for item in node:
   if isinstance(item,list):change_first_x(item);return
change_first_x(target_mutation[0]['geometry']['coordinates'])
if not fail_closed(lambda:validate_target_features(target_mutation,SCOPE['full_current_contact_features'])):raise ValueError('wrong candidate/context negative control failed')
if not fail_closed(lambda:validate_target_features(SCOPE['full_candidate_features'][:-1],SCOPE['full_current_contact_features'])):raise ValueError('omission negative control failed')
if not fail_closed(lambda:validate_target_features(SCOPE['full_candidate_features']+[SCOPE['full_candidate_features'][0]],SCOPE['full_current_contact_features'])):raise ValueError('duplicate-membership negative control failed')
foreign=json.loads(json.dumps(SCOPE['full_candidate_features'][0]));foreign['id']='foreign-component'
if not fail_closed(lambda:validate_target_features(SCOPE['full_candidate_features']+[foreign],SCOPE['full_current_contact_features'])):raise ValueError('foreign-membership negative control failed')
meta=json.loads((ROOT/'sources/geoboundaries/metadata.json').read_bytes())
if not fail_closed(lambda:verify_gb_metadata({**meta,'boundaryYear':'2021'})):raise ValueError('wrong vintage negative control failed')
# Positive exact predicate/coverage fixture.
t=Polygon([(0,0),(1,0),(1,1),(0,1),(0,0)]);s=Polygon([(-1,-1),(2,-1),(2,2),(-1,2),(-1,-1)])
pos=metric(t,s,'positive-control',{},'control')
if not (pos['intersects'] and pos['source_covers_target'] and pos['intersection_over_target_fraction']==1.0):raise ValueError('positive overlay control failed')
# Overlapping envelopes but disjoint exact polygons are not an intersection.
a=Polygon([(0,0),(2,0),(0,2),(0,0)]);b=Polygon([(2,2),(2,1),(1,2),(2,2)])
neg=metric(a,b,'negative-control',{},'control')
if not (not neg['intersects'] and neg['intersection_area_degrees2']==0.0):raise ValueError('negative exact predicate control failed')
invalid=Polygon([(0,0),(1,1),(0,1),(1,0),(0,0)])
inv=metric(invalid,t,'invalid-control',{},'control')
if inv['predicate_status']!='invalid-geometry-unresolved' or inv['intersects'] is not None:raise ValueError('invalid geometry fail-closed control failed')
raw=b'original';expected=sha(raw)
if not fail_closed(lambda:verify_body(raw+b'!',len(raw),expected,'control')):raise ValueError('mutated source body negative control failed')
feature={'properties':{'shapeID':'same'}}
if not fail_closed(lambda:feature_roster([feature,feature])):raise ValueError('duplicate shapeID negative control failed')
geom,errs=rings_to_geometry([[(0,0),(1,0),(0,0)]])
if geom is not None or not errs:raise ValueError('short source ring negative control failed')
positive={'status':'passed','method_id':'exact-source-overlay','control_kind':'positive-control','source_products_loaded':len(gb),'full_product_features':len(gb[0][1]),'simplified_product_features':len(gb[1][1]),'contacts_bound_per_product':len(contacts),'complete_target_roster_bound':49,'positive_exact_cover':{'intersects':pos['intersects'],'source_covers_target':pos['source_covers_target'],'intersection_over_target_fraction':pos['intersection_over_target_fraction']},'geometry_repair_performed':False}
negative={'status':'passed','method_id':'exact-source-overlay','control_kind':'negative-control','bbox_overlapping_but_disjoint':{'intersects':neg['intersects'],'intersection_area_degrees2':neg['intersection_area_degrees2']},'invalid_geometry_unresolved':{'status':inv['predicate_status'],'intersects':inv['intersects']},'mutated_source_bytes_rejected':True,'duplicate_shapeID_rejected':True,'wrong_full_candidate_context_rejected':True,'wrong_source_vintage_rejected':True,'omitted_target_rejected':True,'duplicate_target_rejected':True,'foreign_target_rejected':True,'short_source_ring_rejected':True,'raster_affine_nodata_controls':'not applicable: all compared products are vector geometries; no raster is read','geometry_repair_performed':False}
(ROOT/'receipts/producer-positive-control.json').write_bytes(canon(positive))
(ROOT/'receipts/producer-negative-control.json').write_bytes(canon(negative))
print(json.dumps({'positive':positive,'negative':negative},ensure_ascii=False))
