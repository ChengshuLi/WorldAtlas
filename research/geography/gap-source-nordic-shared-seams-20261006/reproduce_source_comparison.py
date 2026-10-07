import gzip,hashlib,json,subprocess,pathlib,shutil
from shapely.geometry import shape,mapping
from shapely import union_all
from shapely.strtree import STRtree
W=pathlib.Path(__file__).resolve().parents[3]
REPO=W; CACHE=None
OUT=W/'research/geography/gap-source-nordic-shared-seams-20261006'; OUT.mkdir(parents=True,exist_ok=True)
M='79ffb2ed04702e16f009e4675a8d74ef9bd09d4f'; C='cea80a8aa1f8a55ccb448a8f2ff71e10c49a26f1'
ids=['physical-component:000bb4f5335601ba33572e2aca833ec87188059fcdd1f5d830826fa3783c2f05','physical-component:2b3823b49787cb624b7298ab8394ef521dd10a907c12c2a2b0249a6796970eb5','physical-component:4d6cbd694c671b2f56683e931c11b97522823512c0542a6aa7aaa73843ed078b','physical-component:9bdcd0999b59fbb4e5e8601729b4a4dadf0900ed8ead792d512aaa031e314ae9']
contacts=['gb:NOR:ADM2:86288312B50158709887361','gb:NOR:ADM2:86288312B64496782861055','gb:NOR:ADM2:86288312B82966611739072','gb:SWE:ADM2:70781695B94600430897975']
def canon(v):return(json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n').encode()
def sha(b):return hashlib.sha256(b).hexdigest()
def git(commit,path): return subprocess.check_output(['git','-C',str(REPO),'show',commit+':'+path])
def readjson(commit,path,desc=None):
 raw=git(commit,path)
 if desc: assert len(raw)==desc['bytes'] and sha(raw)==desc['sha256']
 dec=gzip.decompress(raw) if raw[:2]==b'\x1f\x8b' else raw
 if desc and 'uncompressed_sha256' in desc: assert len(dec)==desc['uncompressed_bytes'] and sha(dec)==desc['uncompressed_sha256']
 return json.loads(dec),{'commit':commit,'path':path,'bytes':len(raw),'sha256':sha(raw),'decoded_bytes':len(dec),'decoded_sha256':sha(dec)}
inv,invpin=readjson(M,'coordination/engineering/worldwide-inventory-1164-20261006/run-one/report.json')
# Whole source products: exact registry consumed simplified bytes
source={}; source_pins={}; source_coordinate_precision={}
for iso,expected in [('NOR','ab294b0b1dadfb937daa07963aa5995544fd8a16a6c9eb6261a82bb66401d90e'),('SWE','da1070d503e08824b28f8dfac98df108f7ba07772da8c0d3a6f5016a5938801a')]:
 p=OUT/f'gb-{iso}-ADM2-original-simplified.geojson'; raw=p.read_bytes(); assert sha(raw)==expected
 fc=json.loads(raw); source_pins[iso]={'path':p.name,'bytes':len(raw),'sha256':sha(raw),'feature_count':len(fc['features'])}
 coord_decimals=[]
 def walk(v):
  if isinstance(v,(int,float)) and not isinstance(v,bool): coord_decimals.append(max(0,len(str(v).partition('.')[2])))
  elif isinstance(v,(list,tuple)):
   for q in v: walk(q)
 for feat in fc['features']: walk(feat['geometry']['coordinates'])
 source_coordinate_precision[iso]={'coordinate_ordinate_count':len(coord_decimals),'minimum_decimal_places_in_decoded_numeric_values':min(coord_decimals),'maximum_decimal_places_in_decoded_numeric_values':max(coord_decimals),'note':'decoded numeric precision only; not a source accuracy/precision specification'}
 for f in fc['features']: source['gb:'+iso+':ADM2:'+str(f['properties']['shapeID'])]=f
 # Whole consumed source bytes are preserved alongside this reproducer.
# Atlas source features from complete original source vintage
atlas={}
for part in [17,22]:
 fc,_=readjson(C,f'data/geography/part-{part}.json')
 for f in fc['features']:
  if f.get('id') in contacts: atlas[f['id']]=f
assert set(atlas)==set(contacts)
source_contacts={}; subjectrows=[]
for fid in contacts:
 f=source[fid]; a=atlas[fid]; assert f['properties']['shapeID']==fid.split(':')[-1]
 gs=shape(f['geometry']); ga=shape(a['geometry']); assert gs.is_valid and ga.is_valid
 source_contacts[fid]=f
 subjectrows.append({'id':fid,'atlas_full_feature_sha256':sha(canon(a)),'consumed_source_full_feature_sha256':sha(canon(f)),'atlas_geometry_sha256':sha(canon(a['geometry'])),'consumed_source_geometry_sha256':sha(canon(f['geometry'])),'identical_geometry_json':canon(a['geometry'])==canon(f['geometry']),'topologically_equal':ga.equals(gs),'symmetric_difference_planar_area':ga.symmetric_difference(gs).area,'atlas_minus_source_geometry':mapping(ga.difference(gs)),'source_minus_atlas_geometry':mapping(gs.difference(ga))})
# Complete candidate feature rows from authenticated component custody payloads
components={}; componentPins=[]
for pin in inv['complete_products']['components']:
 desc=next(d for d in inv['source_descriptors'] if d['sha256']==pin['sha256'])
 fs,p=readjson(M,desc['path'],pin); componentPins.append(p)
 for f in fs['features']:
  if f.get('id') in ids:
   assert sha(canon(f)) in {'35b225090c58348cb1a7baa9c3094c4fc6071c7d6b10d192fea084687ff296eb','2cbdfa43b97371932ae3e82d10c98e4de87484c2203ea4404b79ab3cad0faed3','bfea81702caf04313bf163bab3d952174b4108a1cf636b27a8e4061dcab0e134','01afb34e96a0091a1e648d8e0778f6d23e43864bd437c178ed45549b3430d09a'}
   components[f['id']]=f
assert set(components)==set(ids)
# bind original fragments by complete source descriptors and exact canonical feature digests
fragment_ids=set(); [fragment_ids.update(x['id'] for x in components[i]['properties']['fragment_bindings']) for i in ids]
fragments={}; fragmentPins=[]
for pin in inv['complete_products']['fragments']:
 desc=next(d for d in inv['source_descriptors'] if d['sha256']==pin['sha256'])
 fs,p=readjson(M,desc['path'],pin); fragmentPins.append(p)
 for f in fs['features']:
  if f.get('id') in fragment_ids: fragments[f['id']]=f
assert len(fragments)==len(fragment_ids)
# complete source contacts joined to each component exact ids and geometry fingerprint
cpin=inv['complete_products']['contacts'][0]; cdesc=next(d for d in inv['source_descriptors'] if d['sha256']==cpin['sha256']); contactfc,contactpin=readjson(M,cdesc['path'],cpin)
contactrows=[f for f in (contactfc if isinstance(contactfc,list) else contactfc.get('features',[])) if any(i in f.get('components',[]) for i in ids) or any(i in f.get('fragments',[]) for i in fragment_ids)]
# retain all relevant source rows by component reference if present; feature schema noted separately
# Whole country source units union and exact candidate unions/differences
src_geoms={'NOR':[shape(f['geometry']) for fid,f in source.items() if fid.startswith('gb:NOR:ADM2:')],'SWE':[shape(f['geometry']) for fid,f in source.items() if fid.startswith('gb:SWE:ADM2:')]}
unionNOR=union_all(src_geoms['NOR']); unionSWE=union_all(src_geoms['SWE']); unionAll=union_all([unionNOR,unionSWE]); contactUnion=union_all([shape(source[i]) for i in contacts])
unionRows=[]
for id in ids:
 f=components[id]; g=shape(f['geometry']); assert g.is_valid
 regions=[]
 for iso,u in [('NOR',unionNOR),('SWE',unionSWE)]:
  it=g.intersection(u); df=g.difference(u)
  regions.append({'source_product':iso,'intersection_planar_area':it.area,'difference_planar_area':df.area,'intersection_geometry':mapping(it),'difference_geometry':mapping(df)})
 allI=g.intersection(unionAll); allD=g.difference(unionAll); cI=g.intersection(contactUnion); cD=g.difference(contactUnion)
 perunit=[]
 for fid,feat in source.items():
  sg=shape(feat['geometry'])
  if g.intersects(sg):
   inter=g.intersection(sg)
   if not inter.is_empty:
    if inter.area>0: contact_kind='positive-area-overlap'
    elif inter.length>0: contact_kind='positive-length-contact'
    else: contact_kind='point-only-contact'
    perunit.append({'source_feature_id':fid,'shapeName':feat['properties'].get('shapeName'),'contact_kind':contact_kind,'intersection_dimension':2 if inter.area>0 else (1 if inter.length>0 else 0),'intersection_planar_area':inter.area,'intersection_planar_length':inter.length,'intersection_geometry':mapping(inter)})
 unionRows.append({'id':id,'full_candidate_feature':f,'canonical_full_feature_sha256':sha(canon(f)),'detector_properties':f['properties'],'candidate_planar_area':g.area,'norway_full_product':regions[0],'sweden_full_product':regions[1],'all_two_source_products_intersection_geometry':mapping(allI),'all_two_source_products_difference_geometry':mapping(allD),'all_two_source_products_intersection_planar_area':allI.area,'all_two_source_products_difference_planar_area':allD.area,'four_contact_union_intersection_geometry':mapping(cI),'four_contact_union_difference_geometry':mapping(cD),'four_contact_union_intersection_planar_area':cI.area,'four_contact_union_difference_planar_area':cD.area,'intersecting_adm2_units':perunit})
# Rebind diagnostic fragment rows exactly; feature bytes written canonically as extracted rows
for fid,f in fragments.items():
 provided=next((b['feature_sha256'] for ci in ids for b in components[ci]['properties']['fragment_bindings'] if b['id']==fid),None)
 assert sha(canon(f))==provided
# Water diagnostic rows are the original component properties and detector water inputs. Preserve unresolved status.
component_rows=[]
for i in ids:
 p=components[i]['properties']; component_rows.append({'id':i,'full_feature_sha256':sha(canon(components[i])),'fragment_bindings':p['fragment_bindings'],'water_status':p.get('water_status'),'touches_reference_shore':p.get('touches_reference_shore'),'positive_area_input_overlap':p.get('positive_area_input_overlap'),'measured_fragment_count':p.get('measured_fragment_count'),'measured_fragment_area_sum_m2':p.get('measured_fragment_area_sum_m2'),'administrative_assignment':p.get('administrative_assignment'),'unmeasured_fragment_ids':p.get('unmeasured_fragment_ids')})
# Inventory and water diagnostic input source records
ar,arpin=readjson(M,'coordination/engineering/physical-gap-audit-1005-20261005-local18/detection-v4/report.json')
waters=[x for x in ar['inputs'] if ('land' in x['path'].lower() or 'lake' in x['path'].lower())]
receipt={
 'status':'bounded Nordic source-product comparison reproduced from authenticated bytes',
 'baseline_pins':{'geometry_baseline_commit':M,'comparison_source_commit':C,'inventory_report':invpin,'original_detector_report':arpin},
 'source_products':{'registry_pin':{'path':'data/administrative-sources.json','bytes':661416,'sha256':'ed0051d2956271c72f8917e7da0c6f53e5dfb595bee5920cac489a65a747d633','commit':M},'consumed_simplified_products':source_pins,'observed_coordinate_numeric_precision':source_coordinate_precision,'registry_metadata':{iso:json.loads(git(M,'data/administrative-sources.json'))[f'gb:{iso}:ADM2'] for iso in ['NOR','SWE']},'source_feature_counts':{'NOR':431,'SWE':290}},
 'subject_feature_comparisons':subjectrows,
 'component_inputs':{'complete_component_shard_payloads':componentPins,'complete_fragment_shard_payloads':fragmentPins,'complete_contact_product':contactpin,'scoped_fragment_ids':sorted(fragment_ids),'scoped_fragment_feature_sha256':{fid:sha(canon(f)) for fid,f in sorted(fragments.items())},'component_rows':component_rows,'source_rows_matching_component_refs':contactrows},
 'full_product_overlays':unionRows,
 'physical_diagnostic':{'detector_report':{'commit':M,'path':'coordination/engineering/physical-gap-audit-1005-20261005-local18/detection-v4/report.json','baseline_commit':ar['baseline_commit'],'executed_code_commit':ar['executed_code_commit'],'water_commit':ar['water_commit'],'water_reference':ar['water_reference'],'water_inputs':ar['water_inputs'],'inputs':waters,'invalid_water_reference':ar['invalid_water_reference'],'limits':ar['limits']},'component_water_statuses':[{k:r[k] for k in ['id','water_status','touches_reference_shore','positive_area_input_overlap','administrative_assignment','unmeasured_fragment_ids']} for r in component_rows]},
 'software':{'shapely':__import__('shapely').__version__,'geos':__import__('shapely').geos_version_string},
 'limits':['Planar overlay results are square degrees; they are not physical area or a water/land verdict.','Consumed inputs are the simplified products recorded in the baseline registry; advertised full-product URLs were not fetched or authenticated.','No independent current or historical Norway/Sweden boundary authority product was authenticated in this bounded run; licensing/source metadata does not establish the border line here.','All four subject Atlas geometries are not topologically equal to their consumed-source counterparts. The specific executed whole-world causal chain from source bytes to Atlas bytes is not bound by this comparison. The current prepare.mjs simplify/precision command remains a hypothesis.','The original detector identifies all four component water statuses as unverified and no positive-area administrative-input overlap; those are detector diagnostics, not real-world water adjudications.','No coordinate normalization, snap, buffer, simplify, MakeValid, minimum-area cutoff, nearest fill, repair, territory assignment, or core edit was applied.']}
(OUT/'source-and-candidate-comparison.json').write_bytes(canon(receipt))
# Store extracted scope rows independently for review; these are immutable derivatives with full feature pins.
(OUT/'scoped-original-components.geojson').write_bytes(canon({'type':'FeatureCollection','features':[components[i] for i in ids]}))
(OUT/'scoped-original-fragments.geojson').write_bytes(canon({'type':'FeatureCollection','features':[fragments[i] for i in sorted(fragments)]}))
(OUT/'scoped-original-atlas-subjects.geojson').write_bytes(canon({'type':'FeatureCollection','features':[atlas[i] for i in contacts]}))
(OUT/'scoped-consumed-source-subjects.geojson').write_bytes(canon({'type':'FeatureCollection','features':[source[i] for i in contacts]}))
print(json.dumps({'out':str(OUT),'contacts':len(subjectrows),'fragments':len(fragments),'components':len(unionRows),'country_features':source_pins,'source_mismatches':[{'id':r['id'],'symmetric_difference_planar_area':r['symmetric_difference_planar_area'],'equal':r['topologically_equal']} for r in subjectrows],'overlap':[{'id':r['id'],'candidate_area':r['candidate_planar_area'],'intersect':r['all_two_source_products_intersection_planar_area'],'outside':r['all_two_source_products_difference_planar_area']} for r in unionRows],'water':receipt['physical_diagnostic']['component_water_statuses']},indent=2))
