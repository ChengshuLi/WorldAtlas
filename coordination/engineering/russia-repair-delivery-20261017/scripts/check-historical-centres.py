"""Usage: Python check-historical-centres.py REPO INPUT_COMMIT OUTPUT.
Read-only corroboration of every historical cell; never assignment authority.
"""
import collections,gzip,hashlib,json,pathlib,subprocess,sys
import numpy as np
import shapely
from shapely.geometry import shape
W=pathlib.Path(sys.argv[1]);H=subprocess.check_output(['git','-C',str(W),'rev-parse',sys.argv[2]+'^{commit}']).decode().strip();OUT=pathlib.Path(sys.argv[3]);P='coordination/engineering/russia-repair-delivery-20261017/';BASE='9d564cf4083cb5499b00d6fb4ceb6fc724fdf01c';pins=[]
def raw(path,commit=H,expected=None):
 b=subprocess.check_output(['git','-C',str(W),'show',commit+':'+path]);h=hashlib.sha256(b).hexdigest()
 if expected:assert len(b)==expected['bytes'] and h==expected['sha256']
 pins.append({'path':path,'commit':commit,'bytes':len(b),'sha256':h});return b
def get(path,commit=H):return json.loads(raw(path,commit))
hist=get(P+'source-review/historical-component-intersections.json');evidence=get(P+'native-inputs-001/source-evidence.json');latpin=evidence['native_latitudes'];buf=gzip.decompress(raw(latpin['path'],latpin['commit'],latpin));assert len(buf)==latpin['decoded_bytes'] and hashlib.sha256(buf).hexdigest()==latpin['decoded_sha256'];lat=np.frombuffer(buf,dtype='<f8');N=len(lat)
owners={r['owner']:r for r in get(P+'source-review/current-targets.json')};phy={r['target']:r for r in get(P+'physical-001/whole-target-support.json')['results']};cells=[]
for r in hist['exact_repair_intersections']:
 for y,a,z,o in r['intervals']:
  for x in range(a,z):cells.append({'scope':r['scope'],'component_id':r['component_id'],'x':x,'y':y,'owner':o,'owner_id':owners[o]['id'],'longitude':360*(x+.5)/N-180,'latitude':float(lat[y]),'source_covers':[]})
assert len(cells)==135 and len({(r['x'],r['y']) for r in cells})==135
points=shapely.points([(r['longitude'],r['latitude']) for r in cells]);cat=get('coordination/engineering/original-geography-source-corpus-20261006/catalogue.json',BASE);families={r['family'] for r in get(P+'source-review/source-custody.json')['families']}|{'gb:KAZ:ADM2','gb:MNG:ADM2'};products=[]
for product in cat['products']:
 if product['key'] not in families:continue
 chunks=[]
 for pin in product['parts']:
  b=gzip.decompress(raw(pin['path'],BASE,pin));assert len(b)==pin['uncompressed_bytes'] and hashlib.sha256(b).hexdigest()==pin['uncompressed_sha256'];chunks.append(b)
 b=b''.join(chunks);assert len(b)==product['original_bytes'] and hashlib.sha256(b).hexdigest()==product['original_sha256'];features=json.loads(b)['features'];assert len(features)==product['feature_count'];products.append((product['key'],features))
b=raw('research/geography/mongolia-russia-gap-source-fitness-20261007/sources/mongolia-mris/mng-adm2-nso-featurelayer-full.geojson',BASE);assert hashlib.sha256(b).hexdigest()==hist['original_dispositions']['mng']['mris_mongolia_nso_adm2']['response_sha256'];mris=json.loads(b)['features'];assert len(mris)==339;products.append(('MRIS:MNG:ADM2',mris));summary=[]
for family,features in products:
 hits=collections.Counter();valid=True
 for ordinal,f in enumerate(features):
  g=shape(f['geometry']);valid=valid and g.is_valid;indexes=np.flatnonzero(shapely.covers(g,points));prop=f['properties'];ident=family+':'+str(prop.get('shapeID',prop.get('ADM2_PCODE')))
  for i in indexes:cells[i]['source_covers'].append({'family':family,'id':ident,'ordinal':ordinal+1,'name':prop.get('shapeName',prop.get('ADM2_EN')),'on_boundary':bool(shapely.intersects(g.boundary,points[i]))});hits[cells[i]['scope']]+=1
 summary.append({'family':family,'complete_features':len(features),'all_valid':bool(valid),'cell_cover_hits':dict(hits)})
for i,r in enumerate(cells):
 target=phy[r['owner_id']];sup=target['support'];support={k:v for k,v in sup.items() if k!='hierarchy_disagreements'};support.update(sup['hierarchy_disagreements']);r['whole_target_issue_reasons']=[x['reason'] for x in target['issues']];r['physical_pointsets_covering_centre']=[k for k,v in support.items() if shape(v).covers(points[i])];r['owner_name']=owners[r['owner']]['current_target']['properties']['name']
counts=collections.Counter()
for r in cells:
 counts['rus_unique_named_owner']+=[x['id'] for x in r['source_covers'] if x['family']=='gb:RUS:ADM2']==[r['owner_id']]
 counts['other_country_adm2_geoboundaries_covers']+=any(x['family'] in ['gb:KAZ:ADM2','gb:MNG:ADM2'] for x in r['source_covers'])
 counts['mris_mongolia_adm2_covers']+=any(x['family']=='MRIS:MNG:ADM2' for x in r['source_covers'])
 counts['source_boundary_hit']+=any(x['on_boundary'] for x in r['source_covers'])
 counts['mapped_land_only']+=r['physical_pointsets_covering_centre']==['mapped_land_support']
result={'version':1,'method':'complete-original-rosters Shapely covers of declared native-centre coordinates; corroboration only','runtime':{'python':sys.version,'shapely':shapely.__version__,'GEOS':shapely.geos_version_string,'numpy':np.__version__},'historical_cells':len(cells),'complete_rosters':summary,'counts':dict(counts),'cells':cells,'source_pins':pins,'limits':['The five original complete-component source-fitness questions remain unresolved. Positive source-relative native centres do not settle complete component fitness, registration-sensitive borders, sovereignty, current statutory role or present physical truth.','No original source feature, candidate geometry, physical issue or native interval is modified by this corroboration.','The complete original Mongolia MRIS/NSO geometry is tested as an independent competitor.','Native authority remains the shared helper and normative latitude table. Floating-coordinate predicates are additional corroboration, not an assignment operator.']}
OUT.write_text(json.dumps(result,separators=(',',':'),ensure_ascii=False)+'\n');print(json.dumps({'cells':len(cells),'counts':dict(counts),'rosters':summary,'output_bytes':OUT.stat().st_size}))
