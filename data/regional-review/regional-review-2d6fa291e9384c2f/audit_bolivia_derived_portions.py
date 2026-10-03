#!/usr/bin/env python3
"""Compare nine Atlas ecozone portions with pinned province ∩ RESOLVE footprints."""
import gzip,json,pathlib,subprocess,tempfile,re,hashlib
HERE=pathlib.Path(__file__).resolve().parent; ROOT=HERE.parents[2]
scope=json.loads((HERE/'scope.json').read_text()); ids=set(scope['member_location_ids']); idx=json.loads((ROOT/'data/world-index.json').read_text()); current={}
for fn in idx['parts']:
 for f in json.loads((ROOT/'data'/fn).read_text())['features']:
  if f['properties']['id'] in ids: current[f['properties']['id']]=f
bol=json.loads(gzip.decompress((HERE/'sources/geoboundaries-BOL-ADM2-2015.geojson.gz').read_bytes())); admin={f['properties']['shapeID']:f for f in bol['features']}
eco=json.loads(gzip.decompress((HERE/'sources/resolve-bolivia-ecoregions-7.geojson.gz').read_bytes())); ecos={str(f['properties']['ECO_ID']):f for f in eco['features']}
frags=[i for i in sorted(ids) if i.startswith('atlas:physical:')]
features=[]
for sid in ('80513517B19404624083023','80513517B10383084964738'):
 f=admin[sid];features.append({'type':'Feature','geometry':f['geometry'],'properties':{'kind':'admin','id':sid,'name':f['properties']['shapeName']}})
for ecoid,f in ecos.items(): features.append({'type':'Feature','geometry':f['geometry'],'properties':{'kind':'eco','id':ecoid,'name':f['properties']['ECO_NAME']}})
for lid in frags:
 f=current[lid];m=f['properties']['metadata'];features.append({'type':'Feature','geometry':f['geometry'],'properties':{'kind':'atlas','id':lid,'name':f['properties']['name'],'admin_id':m['original_id'],'eco_id':m['source_id'].split(':')[1]}})
# Duplicate the source parent and eco feature tags as matching Atlas lookup keys in a separate combined temporary feature set.
for sid in ('80513517B19404624083023','80513517B10383084964738'):
 f=admin[sid];features.append({'type':'Feature','geometry':f['geometry'],'properties':{'kind':'admin_lookup','id':sid}})
for ecoid,f in ecos.items():features.append({'type':'Feature','geometry':f['geometry'],'properties':{'kind':'eco_lookup','id':ecoid}})
fc=pathlib.Path(tempfile.gettempdir())/'worldatlas-490-portion-input.geojson'; fc.write_text(json.dumps({'type':'FeatureCollection','features':features},separators=(',',':')))
proj=pathlib.Path(tempfile.gettempdir())/'worldatlas-490-portion-equalarea.geojson'
subprocess.run(['ogr2ogr','-f','GeoJSON','-t_srs','EPSG:6933',str(proj),str(fc)],check=True,capture_output=True,text=True)
# GeoJSON output uses a single FeatureCollection table named after the temporary file.
layer='worldatlas-490-portion-input'
def query(sql):
 out=subprocess.run(['ogrinfo','-q','-dialect','SQLite','-sql',sql,str(proj)],check=True,capture_output=True,text=True).stdout
 return out
rows=[]
for lid in frags:
 p=current[lid]['properties'];m=p['metadata'];aid=m['original_id'];eid=m['source_id'].split(':')[1]
 sql=f"SELECT ST_Area(ST_Intersection(ST_MakeValid(a.geometry),ST_MakeValid(e.geometry)))/1000000 AS expected_km2, ST_Area(ST_MakeValid(c.geometry))/1000000 AS current_km2, ST_Area(ST_Intersection(ST_Intersection(ST_MakeValid(a.geometry),ST_MakeValid(e.geometry)),ST_MakeValid(c.geometry)))/1000000 AS common_km2, ST_IsValid(a.geometry) AS admin_input_valid, ST_IsValid(e.geometry) AS eco_input_valid, ST_IsValid(c.geometry) AS current_input_valid FROM '{layer}' a JOIN '{layer}' e ON e.kind='eco' AND e.id='{eid}' JOIN '{layer}' c ON c.kind='atlas' AND c.id='{lid}' WHERE a.kind='admin' AND a.id='{aid}'"
 out=query(sql); vals=[float(v) for v in re.findall(r' = ([0-9.eE+-]+)',out)]
 # OGR prints one field for each result column.
 if len(vals)<6: raise SystemExit(f'overlay metrics failed for {lid}: {out}')
 expected,current_area,common=vals[:3]; valid_in=[bool(x) for x in vals[3:6]]
 rows.append({'location_id':lid,'current_name':p['name'],'admin_source_id':aid,'admin_source_name':admin[aid]['properties']['shapeName'],'ecoregion_source_id':eid,'ecoregion_name':ecos[eid]['properties']['ECO_NAME'],'expected_intersection_area_km2_equal_area':expected,'current_area_km2_equal_area':current_area,'overlap_area_km2_equal_area':common,'expected_area_covered_by_current_fraction':common/expected if expected else None,'current_area_inside_expected_fraction':common/current_area if current_area else None,'symmetric_difference_area_km2_equal_area':expected+current_area-2*common,'raw_geometry_validity':{'source_province':valid_in[0],'source_ecoregion':valid_in[1],'current_atlas_fragment':valid_in[2]},'overlay_repair':'ST_MakeValid used only in temporary overlay because some original ecoregion/current inputs are invalid; original bytes remain untouched.'})
parents=[]
for aid in ('80513517B19404624083023','80513517B10383084964738'):
 locs=[x for x in rows if x['admin_source_id']==aid]; placeholders=','.join(f"'{x['ecoregion_source_id']}'" for x in locs); ecoexpr=f"(SELECT ST_Union(ST_Intersection(ST_MakeValid(e.geometry),ST_MakeValid(a.geometry))) FROM '{layer}' e WHERE e.kind='eco' AND e.id IN ({placeholders}))"
 currids=','.join("'"+x['location_id']+"'" for x in locs); currexpr=f"(SELECT ST_Union(ST_MakeValid(geometry)) FROM '{layer}' WHERE kind='atlas' AND id IN ({currids}))"
 sql=f"SELECT ST_Area(ST_MakeValid(a.geometry))/1000000 AS source_km2, ST_Area(ST_Intersection(ST_MakeValid(a.geometry),{ecoexpr}))/1000000 AS eco_covered_km2, ST_Area(ST_SymDifference(ST_MakeValid(a.geometry),{ecoexpr}))/1000000 AS province_eco_symmetric_difference_km2, ST_Area({currexpr})/1000000 AS current_union_km2, ST_Area(ST_SymDifference(ST_MakeValid(a.geometry),{currexpr}))/1000000 AS source_current_symmetric_difference_km2 FROM '{layer}' a WHERE a.kind='admin' AND a.id='{aid}'"
 out=query(sql); vals=[float(v) for v in re.findall(r' = ([0-9.eE+-]+)',out)]
 if len(vals)<5:raise SystemExit(f'parent overlay failed {aid}: {out}')
 parents.append({'admin_source_id':aid,'admin_source_name':admin[aid]['properties']['shapeName'],'portion_count':len(locs),'metrics_equal_area_km2':{'source_admin_area':vals[0],'source_admin_area_covered_by_selected_ecoregions':vals[1],'admin_vs_selected_ecoregion_union_symmetric_difference':vals[2],'current_portion_union_area':vals[3],'source_admin_vs_current_portion_union_symmetric_difference':vals[4]}})
# Compare all 36 potential between-fragment adjacency pairs, including expected source overlays and current shapes.
fragment_pairs=[]
for ai,left in enumerate(frags):
 lp=current[left]['properties']; lm=lp['metadata']; laid=lm['original_id']; leid=lm['source_id'].split(':')[1]
 for right in frags[ai+1:]:
  rp=current[right]['properties']; rm=rp['metadata']; raid=rm['original_id']; reid=rm['source_id'].split(':')[1]
  sql=f"SELECT ST_Length(ST_Intersection(ST_Boundary(ST_Intersection(ST_MakeValid(a.geometry),ST_MakeValid(e.geometry))),ST_Boundary(ST_Intersection(ST_MakeValid(b.geometry),ST_MakeValid(f.geometry))))) AS expected_edge_m, ST_Length(ST_Intersection(ST_Boundary(ST_MakeValid(c.geometry)),ST_Boundary(ST_MakeValid(d.geometry)))) AS current_edge_m FROM '{layer}' a JOIN '{layer}' e ON e.kind='eco' AND e.id='{leid}' JOIN '{layer}' b ON b.kind='admin' AND b.id='{raid}' JOIN '{layer}' f ON f.kind='eco' AND f.id='{reid}' JOIN '{layer}' c ON c.kind='atlas' AND c.id='{left}' JOIN '{layer}' d ON d.kind='atlas' AND d.id='{right}' WHERE a.kind='admin' AND a.id='{laid}'"
  out=query(sql); vals=[float(v) for v in re.findall(r' = ([0-9.eE+-]+)',out)]
  expected_edge,current_edge=(vals[:2] if len(vals)>=2 else [0.0,0.0])
  fragment_pairs.append({'left':left,'right':right,'expected_source_intersection_edge_m':expected_edge,'current_exact_edge_m':current_edge,'expected_neighbor':expected_edge>0.1,'current_exact_neighbor':current_edge>0.1})
expected_pair_set={tuple(sorted((x['left'],x['right']))) for x in fragment_pairs if x['expected_neighbor']}; current_pair_set={tuple(sorted((x['left'],x['right']))) for x in fragment_pairs if x['current_exact_neighbor']}
result={'method':'GeoJSON boundaries reprojected by ogr2ogr to EPSG:6933 equal-area projection; source-expected geometry is ST_Intersection of pinned GeoBolivia-derived 2015 BOL ADM2 province and matching RESOLVE ECO_ID polygon. Current geometry is the exact pinned Atlas fragment. Areas and symmetric differences are planar equal-area estimates. OGR ST_MakeValid is applied only in temporary overlay for raw invalid geometries; original retained features are preserved and input validity is recorded per fragment. Values do not establish administrative semantic suitability or official boundary precision.','ogr2ogr_version':subprocess.run(['ogr2ogr','--version'],check=True,capture_output=True,text=True).stdout.strip(),'source_hashes':{'bol_adm2_raw_sha256':hashlib.sha256(gzip.decompress((HERE/'sources/geoboundaries-BOL-ADM2-2015.geojson.gz').read_bytes())).hexdigest(),'resolve_raw_sha256':hashlib.sha256(gzip.decompress((HERE/'sources/resolve-bolivia-ecoregions-7.geojson.gz').read_bytes())).hexdigest()},'fragment_count':len(rows),'fragments':rows,'parent_unions':parents,'fragment_pair_count':len(fragment_pairs),'source_expected_neighbor_pair_count':len(expected_pair_set),'current_exact_neighbor_pair_count':len(current_pair_set),'neighbor_pair_graph_differences':{'expected_missing_current':[list(x) for x in sorted(expected_pair_set-current_pair_set)],'current_missing_expected':[list(x) for x in sorted(current_pair_set-expected_pair_set)]},'fragment_pairs':fragment_pairs,'interpretation':'The overlay tests whether the nine shared location geometries reproduce the two complete administrative predecessor provinces and their natural ecoregion subdivisions. A close fit would support geometry derivation only; it cannot promote ecozones or province fragments to an administrative tier.'}
(HERE/'derived-portion-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'fragment_count':len(rows),'parent_unions':parents,'fractions':{x['location_id']:round(x['expected_area_covered_by_current_fraction'],6) for x in rows}},ensure_ascii=False,indent=2))
