"""Prepare a guarded Neon transaction for a raw-source Caucasus WGS84 replay.

The user-approved target is the existing draft revision. This program writes an
SQL file; it does not connect to Neon. Execute it through an authorized client.
"""
import argparse,hashlib,json
from pathlib import Path
from shapely.geometry import Polygon,Point

def canon(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)
def sha(v):return hashlib.sha256(canon(v).encode()).hexdigest()
def q(v):return "'"+str(v).replace("'","''")+"'"
def main():
 p=argparse.ArgumentParser()
 for n in ('geometry','recipe','snapshot','exterior','code-commit','output'):p.add_argument('--'+n,required=True)
 a=p.parse_args();geo=json.loads(Path(a.geometry).read_text());recipe=json.loads(Path(a.recipe).read_text());snapshot=json.loads(Path(a.snapshot).read_text());exterior=json.loads(Path(a.exterior).read_text());
 if sha(geo)!=recipe['expected_wgs84_geometry_sha256'] or len(geo['coordinates'])!=10084:raise ValueError('geometry hash or vertex count mismatch')
 rsha=sha(recipe)
 if sha(exterior)!='dc5ddd0580b3c1bed14d9428aa0a0d5a214d963f1efdddb629f88fa704ea7a87':raise ValueError('exterior closure hash mismatch')
 records={('boundary',v['boundary_id']):dict(v) for v in snapshot['mainland_boundaries']};records.update({('route',v['route_id']):dict(v) for v in snapshot['routes']})
 if sha(records[('boundary','ural_kara_coast_to_caspian')]['geometry'])!='5a6526344cacbc1a23be174f589cec9710a0f317360ec5c8737ba6956c3f7fe2':raise ValueError('Ural source mismatch')
 if sha(records[('route','europe_caspian_closure_v1')]['geometry'])!='6ee86cf4108b8622e01a4dd0be0b4ae19e809b4e04d8cceb25547425258ac62a':raise ValueError('Caspian route mismatch')
 records[('boundary','caucasus_blacksea_anapa_to_caspian')]['geometry']=geo;records[('route','europe_exterior_closure_v1')]['geometry']=exterior
 region=next(v for v in snapshot['seed_regions'] if v['region_id']=='europe_mainland_region_v1');ring=[]
 for seg in region['segments']:
  end=len(geo['coordinates']) if seg['id']=='caucasus_blacksea_anapa_to_caspian' else len(exterior['coordinates']) if seg['id']=='europe_exterior_closure_v1' else seg['end'];coords=records[(seg['kind'],seg['id'])]['geometry']['coordinates'][seg['start']:end];coords=list(reversed(coords)) if seg['reverse'] else coords
  if ring and ring[-1]!=coords[0]:raise ValueError('region join mismatch')
  ring+=coords if not ring else coords[1:]
 poly=Polygon(ring)
 if not poly.is_valid or not poly.exterior.is_simple:raise ValueError('invalid region')
 for w in region['witnesses']:
  if poly.contains(Point(float(w['lon']),float(w['lat'])))!=w['inside']:raise ValueError('region witness mismatch')
 rhash=sha({'type':'Polygon','coordinates':[ring]});expected='6cae4f0786d3872787030f87eb7f0902a4685301a4532da3db2190e13013fd01'
 if rhash!=expected:raise ValueError('region digest mismatch '+rhash)
 if len(a.code_commit)!=40 or any(c not in '0123456789abcdef' for c in a.code_commit):raise ValueError('expected full PR4 commit SHA')
 ids=['jaxa-aw3d30-original-'+x.lower() for x in ('n41e046','n41e047','n42e044','n43e039','n43e040','n43e041','n44e038','n44e039')];keys=[recipe['r2_keys'][x] for x in ('N041E046.zip','N041E047.zip','N042E044.zip','N043E039.zip','N043E040.zip','N043E041.zip','N044E038.zip','N044E039.zip')];hashes=[recipe['sources_sha256'][x] for x in ('N041E046.zip','N041E047.zip','N042E044.zip','N043E039.zip','N043E040.zip','N043E041.zip','N044E038.zip','N044E039.zip')];rows=','.join('('+','.join(map(q,v))+')' for v in zip(ids,keys,hashes))
 sql="""DO $caucasus$ DECLARE n integer; BEGIN
IF NOT EXISTS (SELECT 1 FROM atlas.decision_revisions WHERE revision='v2-land-mainland-boundary-draft-1' AND status='draft') OR NOT EXISTS (SELECT 1 FROM atlas.decision_mainland_boundaries WHERE revision='v2-land-mainland-boundary-draft-1' AND boundary_id='caucasus_blacksea_anapa_to_caspian' AND geometry_sha256 IN ('5e8d3ab116112881d7bc515f197cbe980933e0a8ac673deb0bfb0af5fd900beb','3be87f6ec29be709a07c07c04ce62b6fb00e33f6b35020781a088be5b2d8e8b9') FOR UPDATE) OR NOT EXISTS (SELECT 1 FROM atlas.decision_mainland_boundaries WHERE revision='v2-land-mainland-boundary-draft-1' AND boundary_id='ural_kara_coast_to_caspian' AND geometry_sha256='5a6526344cacbc1a23be174f589cec9710a0f317360ec5c8737ba6956c3f7fe2' FOR UPDATE) OR NOT EXISTS (SELECT 1 FROM atlas.decision_mainland_seed_regions WHERE revision='v2-land-mainland-boundary-draft-1' AND region_id='europe_mainland_region_v1' AND geometry_sha256 IN ('405d89d68c65d5465bd54ab9c24d4ef3a8b162ab2c5fd4ff992d2927c4892e7f','6cae4f0786d3872787030f87eb7f0902a4685301a4532da3db2190e13013fd01') FOR UPDATE) OR NOT EXISTS (SELECT 1 FROM atlas.decision_mainland_closure_routes WHERE revision='v2-land-mainland-boundary-draft-1' AND route_id='europe_caspian_closure_v1' AND geometry_sha256='6ee86cf4108b8622e01a4dd0be0b4ae19e809b4e04d8cceb25547425258ac62a' FOR UPDATE) OR NOT EXISTS (SELECT 1 FROM atlas.decision_mainland_closure_routes WHERE revision='v2-land-mainland-boundary-draft-1' AND route_id='europe_exterior_closure_v1' AND geometry_sha256='dc5ddd0580b3c1bed14d9428aa0a0d5a214d963f1efdddb629f88fa704ea7a87' FOR UPDATE) THEN RAISE EXCEPTION 'current selected snapshot changed'; END IF;
"""
 sql+="IF EXISTS (SELECT 1 FROM atlas.decision_mainland_boundaries b JOIN atlas.decision_mainland_seed_regions r ON r.revision=b.revision WHERE b.revision='v2-land-mainland-boundary-draft-1' AND b.boundary_id='caucasus_blacksea_anapa_to_caspian' AND r.region_id='europe_mainland_region_v1' AND NOT ((b.geometry_sha256='5e8d3ab116112881d7bc515f197cbe980933e0a8ac673deb0bfb0af5fd900beb' AND r.geometry_sha256='405d89d68c65d5465bd54ab9c24d4ef3a8b162ab2c5fd4ff992d2927c4892e7f') OR (b.geometry_sha256='3be87f6ec29be709a07c07c04ce62b6fb00e33f6b35020781a088be5b2d8e8b9' AND r.geometry_sha256='6cae4f0786d3872787030f87eb7f0902a4685301a4532da3db2190e13013fd01'))) THEN RAISE EXCEPTION 'boundary-region mismatch'; END IF;\n"
 sql+="IF EXISTS (SELECT 1 FROM atlas.decision_mainland_boundaries WHERE revision='v2-land-mainland-boundary-draft-1' AND boundary_id='caucasus_blacksea_anapa_to_caspian' AND geometry_sha256='3be87f6ec29be709a07c07c04ce62b6fb00e33f6b35020781a088be5b2d8e8b9' AND provenance#>>'{current_selection,source_assembly_wgs84_v2,recipe_sha256}' IS DISTINCT FROM "+q(rsha)+") THEN RAISE EXCEPTION 'selected recipe changed'; END IF;\n"
 sql+="SELECT count(*) INTO n FROM (VALUES "+rows+") AS expected(source_id,r2_key,sha256) JOIN atlas.source_assets s USING(source_id,r2_key,sha256) JOIN atlas.decision_mainland_boundary_sources r ON r.source_id=s.source_id AND r.source_version=s.version WHERE r.revision='v2-land-mainland-boundary-draft-1' AND r.boundary_id='caucasus_blacksea_anapa_to_caspian'; IF n<>8 THEN RAISE EXCEPTION 'required JAXA source links missing'; END IF;\n"
 sql+="IF NOT EXISTS (SELECT 1 FROM atlas.source_assets s JOIN atlas.decision_mainland_boundary_sources r ON r.source_id=s.source_id AND r.source_version=s.version WHERE s.source_id='osm-caucasus-approved-drainage' AND s.sha256='116d078c59a6fc46786ec369450483d809c187bcaa632f01c5081c63f04e5706' AND r.revision='v2-land-mainland-boundary-draft-1' AND r.boundary_id='caucasus_blacksea_anapa_to_caspian') THEN RAISE EXCEPTION 'OSM source link missing'; END IF;\n"
 metadata={'recipe_sha256':rsha,'recipe':recipe,'code_commit':a.code_commit,'source_replay':'verified from R2 readbacks with WGS84','pipeline_status':'boundary replay verified; source gate and fresh closure proofs pending'}
 sql+="UPDATE atlas.decision_mainland_boundaries SET geometry="+q(canon(geo))+"::jsonb, geometry_sha256="+q(sha(geo))+", provenance=jsonb_set(provenance,'{current_selection}',coalesce(provenance->'current_selection','{}'::jsonb) || jsonb_build_object('source_assembly_wgs84_v2',"+q(canon(metadata))+"::jsonb),true) WHERE revision='v2-land-mainland-boundary-draft-1' AND boundary_id='caucasus_blacksea_anapa_to_caspian'; GET DIAGNOSTICS n=ROW_COUNT; IF n<>1 THEN RAISE EXCEPTION 'boundary row count'; END IF;\n"
 sql+="UPDATE atlas.decision_mainland_seed_regions SET geometry_sha256="+q(rhash)+" WHERE revision='v2-land-mainland-boundary-draft-1' AND region_id='europe_mainland_region_v1'; GET DIAGNOSTICS n=ROW_COUNT; IF n<>1 THEN RAISE EXCEPTION 'region row count'; END IF;\n"
 sql+="UPDATE atlas.decision_mainland_boundary_sources SET relationship='approved_jaxa_product_boundary_derivation_input' WHERE revision='v2-land-mainland-boundary-draft-1' AND boundary_id='caucasus_blacksea_anapa_to_caspian' AND source_id IN ("+','.join(map(q,ids))+"); GET DIAGNOSTICS n=ROW_COUNT; IF n<>8 THEN RAISE EXCEPTION 'JAXA relationship count'; END IF;\n"
 sql+="UPDATE atlas.decision_mainland_boundary_sources SET relationship='approved_source_derivation_input' WHERE revision='v2-land-mainland-boundary-draft-1' AND boundary_id='caucasus_blacksea_anapa_to_caspian' AND source_id IN ('trubetskoy-europe-asia-boundary','hydrosheds-hydrobasins-europe-level12-standard'); GET DIAGNOSTICS n=ROW_COUNT; IF n<>2 THEN RAISE EXCEPTION 'baseline source relationship count'; END IF;\n"
 sql+="IF NOT EXISTS (SELECT 1 FROM atlas.decision_mainland_region_segments WHERE revision='v2-land-mainland-boundary-draft-1' AND region_id='europe_mainland_region_v1' AND boundary_id='caucasus_blacksea_anapa_to_caspian' AND end_index=10084) THEN RAISE EXCEPTION 'region segment changed'; END IF; END $caucasus$;"
 with open(a.output,'x') as f:f.write(sql)
 print('geometry_sha256',sha(geo),'recipe_sha256',rsha,'region_sha256',rhash,'witnesses',len(region['witnesses']),'sql_bytes',len(sql))
if __name__=='__main__':main()
