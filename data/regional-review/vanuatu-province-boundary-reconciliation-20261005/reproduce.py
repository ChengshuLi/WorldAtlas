#!/usr/bin/env python3
"""Reproduce identity and area-screen evidence for WorldAtlas issue #912."""
import json
from pathlib import Path
from shapely.geometry import shape
from shapely.ops import unary_union
from immutable import Baseline, sha256
from geometry import canonical_land, land_area_m2, METHOD

ROOT = Path(__file__).resolve().parents[3]
BASE = 'a32ae163473a42ed28d7bedf7e9930414beb54f8'
OWNED = 'data/regional-review/vanuatu-province-boundary-reconciliation-20261005/'
IDS = [
'gb:VUT:ADM1:32282491B17169683382430',
'gb:VUT:ADM1:32282491B5439526076152',
'gb:VUT:ADM1:32282491B61228346728599',
'gb:VUT:ADM1:32282491B7486560380604',
'gb:VUT:ADM1:32282491B78905986242135',
'gb:VUT:ADM1:32282491B8417950609019',]
PINS = {
'data/world-index.json':('a62d4a74f0f969e228dfcdeb2797bb689ce9836c2498cadd31ed622ad2c38c03',944),
'data/administrative-sources.json':('ed0051d2956271c72f8917e7da0c6f53e5dfb595bee5920cac489a65a747d633',661416),
'data/geography/part-28.json':('2aab2f36aeeb651ee8e6cc656e9541ad14e2ced2ea8160e8700ad4dc950c379d',6613963),
'data/validation/macro-publication-v5.json':('aae3967fde4f5bf92b3cb0b42c490c6c6a5921c7421dcdc9533f242afbd6a674',2826),
'data/hierarchy.json':('568301690ef231a85856666b57876a5efe8d8c7c6e671a56d81307b2dc28b80b',10164089),
'data/regional-review/regional-review-1aa97b490604ea4e/sources/vanuatu-2017-adm1.geojson':('69f44b96d0690310c67a4a430488fb7a02d028bdec8bbc755436cdfb90962c8d',1094439),
'data/regional-review/regional-review-1aa97b490604ea4e/source-acquisition.json':('8ca953420a96d12200f4ca56d5b91abf5aafe276918a36c1745dae72bfd42d2c',9302),
'scripts/administrative.py':('d9df8285f1c270856a8e79b95636cf4b8d8496f48b30348a1e4d6d20619b2f22',12313),
}
baseline = Baseline(ROOT, BASE, [dict(path=p,sha256=h,bytes=n,hash_kind='file-bytes') for p,(h,n) in PINS.items()])
features, containing = baseline.subjects(IDS)
assert set(features) == set(IDS) and all(containing[x]['path']=='data/geography/part-28.json' for x in IDS)
prior=json.loads(baseline.read('data/regional-review/regional-review-1aa97b490604ea4e/sources/vanuatu-2017-adm1.geojson'))
registry=json.loads(baseline.read('data/administrative-sources.json'))['gb:VUT:ADM1']
index={f['properties']['shapeID']:f for f in prior['features']}
assert len(index)==6
names={'Shefa Province':'Shefa Province','Malampa':'Malampa','Tafea':'Tafea','Sanma':'Sanma','Penama':'Penama','Torba':'Torba'}
groups={'Shefa Province':'Shepherds, Epi and Efate; the profile additionally names Emae, Tongoa, Tongariki/Buninga, Makira/Mataso, Emau and Moso/Lelepa.', 'Malampa':'Malekula, Ambrym and Paama.', 'Tafea':'Tanna, Aneityum, Futuna, Erromango and Aniwa.', 'Sanma':'Santo, Malo and Aore.', 'Penama':'Pentecost, Ambae and Maewo.', 'Torba':'Banks and Torres island groups.'}
municipal={'Shefa Province':'Port Vila municipality exclusion','Sanma':'Luganville municipality exclusion','Tafea':'Lenakel municipality exclusion','Malampa':'no consulted municipality carve-out identified','Penama':'no consulted municipality carve-out identified','Torba':'no consulted municipality carve-out identified'}
hierarchy={x['id']:x for x in json.loads(baseline.read('data/hierarchy.json'))}
rows=[]
for identity in IDS:
    atlas=features[identity]; name=atlas['properties']['name']; suffix=identity.rsplit(':',1)[1]
    native=index.get(suffix)
    assert native and native['properties']['shapeName']==names[name] and native['properties']['shapeType']=='ADM1'
    a=canonical_land(shape(atlas['geometry'])); s=canonical_land(shape(native['geometry']))
    intersection=land_area_m2(a.intersection(s)); union=land_area_m2(unary_union([a,s]))
    parent_id=atlas['properties']['parent_id']; parent=hierarchy[parent_id]
    rows.append({'id':identity,'name':name,'tier':'ADM1','parent_id':parent_id,'parent_name':parent.get('name'),
      'atlas_components':len(atlas['geometry']['coordinates']),'native_components':len(native['geometry']['coordinates']),
      'source_native_id':suffix,'source_name':native['properties']['shapeName'],'government_group_context':groups[name],
      'unresolved_boundary_question':municipal[name]+'; current legal boundary Orders and complete outer-island linework not located in consulted sources.',
      'atlas_area_km2':land_area_m2(a)/1e6,'source_area_km2':land_area_m2(s)/1e6,
      'jaccard':intersection/union,'symmetric_difference_km2':(land_area_m2(a)+land_area_m2(s)-2*intersection)/1e6,
      'classification':'insufficient-evidence',
      'finding':'Six-province tier and broad island-group identity are supported; current legal lines, municipality exclusions, and small-island completeness are unresolved. The overlap screen only compares Atlas with 2017 OSM-derived geometry.'})
# Registry digest is a generated importer-cache hash; compare distinct artifacts explicitly.
assert registry['sha256']=='63e1878b1a484787aafa029e3f2a8cb063d9d720b38e9d17884a999d28cd10f8'
assert sha256(baseline.read('data/regional-review/regional-review-1aa97b490604ea4e/sources/vanuatu-2017-adm1.geojson'))=='69f44b96d0690310c67a4a430488fb7a02d028bdec8bbc755436cdfb90962c8d'
result={'issue':912,'baseline_commit':BASE,'scope_ids':IDS,'positive_controls':{'exact_six_subjects_once_in_index':True,'native_id_and_name_match_all_six':True,'source_vintage':'2017','source_license':'ODbL-1.0','source_geometry_validity':'all six valid per prior issue #454 review'},
 'negative_controls':{'unknown_subject_id_absent': 'gb:VUT:ADM1:UNKNOWN' not in features,'wrong_source_name_rejected':(index['32282491B17169683382430']['properties']['shapeName'] != 'Torba')},
 'source_digest_reconciliation':{'registry_sha256':registry['sha256'],'retained_distribution_sha256':PINS['data/regional-review/regional-review-1aa97b490604ea4e/sources/vanuatu-2017-adm1.geojson'][0],'retained_bytes':1094439,'status':'different hashes describe different byte objects; registry hash was generated from an unretained importer cache file and is not reproducible from pinned distribution; upstream LFS object matches retained distribution'},
 'geometry_method':METHOD,'interpretation':'Diagnostics only. Jaccard and symmetric difference do not establish legal authority, source correctness, present-day vintage, or island completeness. No geometry repair or acceptance threshold is applied.',
 'subjects':rows,'limitations':['No current province boundary-defining orders or authoritative exact legal linework located in consulted official sources.','Municipalities are excluded from provincial regions under Decentralization Act s34; current exact municipality boundaries were not established.','Government island/area-council rosters do not define legal province boundaries or every outer island.','Current DLA roster has 71 area councils; OCHA/SPC ADM2 reference has 66 features and blank license metadata; no five-feature crosswalk inferred.','No redistribution license located for DLA PDFs; their bytes are restoration-only.']}
Path(ROOT/OWNED/'reproduction.json').write_text(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
print(json.dumps({'subjects':len(rows),'source_sha':PINS['data/regional-review/regional-review-1aa97b490604ea4e/sources/vanuatu-2017-adm1.geojson'][0],'jaccards':[round(x['jaccard'],6) for x in rows]},indent=2))
