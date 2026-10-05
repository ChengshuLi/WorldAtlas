#!/usr/bin/env python3
"""Reproduce #436's source/ID/parent screening. Requires restored pinned GB source."""
import argparse, hashlib, json, sys
from pathlib import Path
from shapely.geometry import shape
from evidence.geometry import land_area_m2, METHOD
EXPECTED_SOURCE = "74e489fd4370972403950719026a317abba443668cea7d49f4b36c61637958f1"
EXPECTED_ATLAS = "2aab2f36aeeb651ee8e6cc656e9541ad14e2ced2ea8160e8700ad4dc950c379d"
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--adm3',type=Path,help='Restored original geoBoundaries ADM3 GeoJSON');ap.add_argument('--output',type=Path);a=ap.parse_args()
 srcp=a.adm3 or HERE/'.scratch/geoBoundaries-ZAF-ADM3.geojson';scope=json.loads((HERE/'sources/issue-436-scope.json').read_text());partp=ROOT/'data/geography/part-28.json';partb=partp.read_bytes()
 if hashlib.sha256(partb).hexdigest()!=EXPECTED_ATLAS: raise SystemExit('Unexpected baseline part-28 SHA256; verify recorded main commit')
 parts=sorted((HERE/'sources/geoboundaries-zaf-adm3').glob('geoBoundaries-ZAF-ADM3-part-*-of-*.geojson'))
 if srcp.exists():
  sourceb=srcp.read_bytes()
  if hashlib.sha256(sourceb).hexdigest()!=EXPECTED_SOURCE: raise SystemExit('ADM3 source SHA256 mismatch')
  gb=json.loads(sourceb); source_verification='original-file-bytes'
 elif parts:
  feats=[]
  docs=[json.loads(p.read_bytes()) for p in parts]
  crs=docs[0].get('crs')
  if any(d.get('crs')!=crs for d in docs): raise SystemExit('ADM3 partitions have inconsistent CRS metadata')
  for d in docs: feats.extend(d['features'])
  gb={'type':'FeatureCollection','crs':crs,'features':feats};source_verification='retained-source-feature-partitions'
 else: raise SystemExit('Restore source using sources/README.md; do not substitute a newer release')
 atlas=json.loads(partb);ids=scope['member_location_ids']
 if len(ids)!=196 or len(set(ids))!=196 or len(ids)!=scope['location_count']: raise SystemExit('Issue scope count/uniqueness mismatch')
 src={f['properties']['shapeID']:f for f in gb['features']}
 if len(src)!=len(gb['features']) or len(src)!=213: raise SystemExit('Pinned source population/key uniqueness mismatch')
 loc={f['properties']['id']:f for f in atlas['features'] if f['properties'].get('id','').startswith('gb:ZAF:ADM3:')}
 if len(loc)!=213: raise SystemExit('Baseline ADM3 population mismatch')
 rows=[];missing=[]
 for uid in ids:
  f=loc.get(uid); sf=src.get(uid.rsplit(':',1)[1]) if f else None
  if f is None or sf is None: missing.append(uid);continue
  ga=shape(f['geometry']); gs=shape(sf['geometry'])
  area_a=land_area_m2(ga); area_s=land_area_m2(gs)
  parts_a=list(ga.geoms) if ga.geom_type=='MultiPolygon' else [ga];parts_s=list(gs.geoms) if gs.geom_type=='MultiPolygon' else [gs]
  sizes_a=sorted([round(land_area_m2(q)/1e6,6) for q in parts_a],reverse=True);sizes_s=sorted([round(land_area_m2(q)/1e6,6) for q in parts_s],reverse=True)
  rows.append({'id':uid,'name':f['properties']['name'],'parent_id':f['properties'].get('parent_id'),'shapeID':uid.rsplit(':',1)[1],'source_shapeName':sf['properties']['shapeName'],'source_shapeType':sf['properties']['shapeType'],'atlas_geometry_valid':ga.is_valid,'source_geometry_valid':gs.is_valid,'atlas_polygon_components':len(parts_a),'source_polygon_components':len(parts_s),'atlas_component_areas_km2':sizes_a,'source_component_areas_km2':sizes_s,'source_topologically_equals_atlas':ga.equals(gs),'source_topologically_equals_atlas':ga.equals(gs),'atlas_area_km2':round(area_a/1e6,3),'source_area_km2':round(area_s/1e6,3),'relative_area_difference':round(abs(area_a-area_s)/area_s,8),'boundary_status':'insufficient-evidence','reason':'The pinned 2020 feature is a traceable comparison source, but the stored Atlas polygon differs and neither source establishes current legal boundary or completeness.'})
 if missing or len(rows)!=196: raise SystemExit('Crosswalk incomplete: '+repr(missing[:5]))
 if not all(r['atlas_geometry_valid'] and r['source_geometry_valid'] for r in rows): raise SystemExit('Invalid geometry pair; do not perform overlay until reviewed')
 out={'baseline_main':'93c901e1c0b44073233fd3d48d403985a0cf2c52','issue':436,'scope_sha256':sha(HERE/'sources/issue-436-scope.json'),'baseline_part_28_sha256':sha(partp),'pinned_adm3_sha256':EXPECTED_SOURCE,'source_partition_sha256':{p.name:sha(p) for p in parts},'canonical_source_features_sha256':hashlib.sha256(json.dumps(gb,ensure_ascii=False,separators=(',',':')).encode()).hexdigest(),'source_feature_count':len(gb['features']),'scope_count':len(rows),'unique_ids':len({r['id'] for r in rows}),'valid_geometry_pair_count':sum(r['atlas_geometry_valid'] and r['source_geometry_valid'] for r in rows),'topological_geometry_match_count':sum(r['source_topologically_equals_atlas'] for r in rows),'relative_area_difference_max':max(r['relative_area_difference'] for r in rows),'source_multipart_count':sum(r['source_polygon_components']>1 for r in rows),'atlas_multipart_count':sum(r['atlas_polygon_components']>1 for r in rows),'component_count_mismatch_count':sum(r['source_polygon_components']!=r['atlas_polygon_components'] for r in rows),'component_count_mismatches':[{'id':r['id'],'name':r['name'],'source_components':r['source_polygon_components'],'atlas_components':r['atlas_polygon_components']} for r in rows if r['source_polygon_components']!=r['atlas_polygon_components']],'rows':sorted(rows,key=lambda r:r['id'])}
 payload=json.dumps(out,ensure_ascii=False,indent=2)+'\n';a.output.write_text(payload) if a.output else sys.stdout.write(payload)
if __name__=='__main__':main()
