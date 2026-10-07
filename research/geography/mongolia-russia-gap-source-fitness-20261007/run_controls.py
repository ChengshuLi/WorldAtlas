#!/usr/bin/env python3
"""Run actual-input positive and synthetic-negative controls for the evidence methods."""
import copy, gzip, hashlib, json, sys
from importlib.util import spec_from_file_location, module_from_spec
from pathlib import Path
from shapely.affinity import translate
from shapely.geometry import shape
from shapely.strtree import STRtree
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[2]
sys.path.insert(0, str(REPO/'scripts'))
from ellipsoidal_area import area as geod_area
PHYS=json.loads((ROOT/'inputs/physical-component-features.geojson').read_text())
ROUTE=[json.loads(x) for x in (ROOT/'inputs/route-component-rows.jsonl').read_text().splitlines() if x]
CAT=json.loads((REPO/'coordination/engineering/original-geography-source-corpus-20261006/catalogue.json').read_text())
features={f['id']:f for f in PHYS['features']};route={r['component']:r for r in ROUTE}
assert len(features)==len(route)==48 and set(features)==set(route)
spec=spec_from_file_location('extract',ROOT/'extract_inputs.py');mod=module_from_spec(spec);spec.loader.exec_module(mod)
# Positive integrity control: authentic full feature and geometry match the pinned route record.
pos_id=sorted(features)[0]; feature=features[pos_id]; row=route[pos_id]
assert hashlib.sha256(mod.json_bytes(feature['geometry'])).hexdigest()==row['current_geometry_sha256']
assert hashlib.sha256(mod.json_bytes(feature)).hexdigest()==row['current_feature_sha256']
restore_positive={'component_id':pos_id,'geometry_hash_matches':True,'full_feature_hash_matches':True,'scope_ids':48,'contact_ids':8}
# Negative integrity control: an in-memory one-coordinate mutation must fail exact geometry identity.
mutated=copy.deepcopy(feature);mutated['geometry']['coordinates'][0][0][0]+=1e-6
mutated_hash=hashlib.sha256(mod.json_bytes(mutated['geometry'])).hexdigest()
assert mutated_hash!=row['current_geometry_sha256']
restore_negative={'component_id':pos_id,'mutated_geometry_hash':mutated_hash,'reference_geometry_hash':row['current_geometry_sha256'],'mutation_rejected':True,'input_written':False}
# Geographic controls call the same WGS84 ellipsoidal area helper as the producer.
entry=next(x for x in CAT['products'] if x['key']=='gb:MNG:ADM2')
product=json.loads(gzip.decompress((REPO/entry['parts'][0]['path']).read_bytes()))
geoms=[shape(f['geometry']) for f in product['features']];tree=STRtree(geoms)
spatial_id=next(cid for cid in sorted(features) if tree.query(shape(features[cid]['geometry'])).size)
target=shape(features[spatial_id]['geometry']);hits=[]
for ix in tree.query(target):
 ix=int(ix)
 if target.intersects(geoms[ix]) and geod_area(target.intersection(geoms[ix]))>0:hits.append(ix)
assert hits
geo_positive={'component_id':spatial_id,'positive_area_source_feature_count':len(hits),'area_policy':'WGS84 straight-source-edge ellipsoidal integral'}
# A synthetic in-memory shift to west Africa must have no positive-area hit in Mongolia ADM2.
synthetic=translate(target,xoff=-100,yoff=0);synthetic_hits=[]
for ix in tree.query(synthetic):
 ix=int(ix)
 if synthetic.intersects(geoms[ix]) and geod_area(synthetic.intersection(geoms[ix]))>0:synthetic_hits.append(ix)
assert not synthetic_hits
geo_negative={'component_id':spatial_id,'synthetic_translation_degrees_west':100,'positive_area_source_feature_count':0,'used_as_territorial_evidence':False}
limits=['Controls verify input integrity and overlay mechanics only, not source correctness or authority.','Synthetic geometry is never written to reviewed inputs or treated as geographic evidence.']
def emit(method_id,kind,details):
 record={'method_id':method_id,'kind':kind,'outcome':'passed','details':details,'limits':limits}
 path=ROOT/'runs'/f'{method_id}-{kind}.json';path.write_text(json.dumps(record,sort_keys=True,separators=(',',':'))+'\n')
 return {'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
outputs=[emit('custody-family-restoration','positive-control',restore_positive),emit('custody-family-restoration','negative-control',restore_negative),emit('source-overlay','positive-control',geo_positive),emit('source-overlay','negative-control',geo_negative)]
print(json.dumps({'controls':outputs},indent=2))
