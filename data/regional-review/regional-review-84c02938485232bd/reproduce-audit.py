#!/usr/bin/env python3
"""Reproduce issue #494 membership, ancestry, DANE crosswalk and settlement audit."""
import gzip, hashlib, json, pathlib, unicodedata, collections
P=pathlib.Path(__file__).resolve().parent; ROOT=P.parents[2]; S=P/'sources'
def sha(b): return hashlib.sha256(b).hexdigest()
def read_gz(name): return gzip.decompress((S/name).read_bytes())
def check(ok,msg):
 if not ok: raise AssertionError(msg)
 print('PASS',msg)
def norm(t): return ''.join(c for c in unicodedata.normalize('NFKD',t.casefold()) if not unicodedata.combining(c) and c.isalnum())
scope=json.loads((P/'issue-scope.json').read_text()); ids=scope['member_location_ids']; check(len(ids)==265==scope['location_count'],'issue pins 265 assigned location IDs')
check(sha('\n'.join(sorted(ids)).encode())==scope['member_location_ids_sha256'],'issue member fingerprint')
index=json.loads((ROOT/'data/world-index.json').read_text()); assigned=set(ids); features={}
for rel in index['parts']:
 for f in json.loads((ROOT/'data'/rel).read_text()).get('features',[]):
  if f['id'] in assigned: features[f['id']]=f
check(set(features)==assigned,'all assigned features appear in indexed geography')
hierarchy=json.loads((ROOT/'data/hierarchy.json').read_text()); groups={x['id']:x for x in hierarchy}
check(sha((ROOT/'data/hierarchy.json').read_bytes())==scope['release']['hierarchy_sha256'],'pinned published hierarchy hash')
expected_area=scope['area_scopes'][0]['id']; region=scope['region_id']; expected_tail=[expected_area,region,'framework:subcontinent:andean-south-america:9579d3e91c2b','framework:continent:south-america:bbda637e3435']
for id,f in features.items():
 chain=[]; q=f['properties'].get('parent_id')
 while q:
  check(q in groups,f'{id} has parent {q} in published hierarchy'); g=groups[q];chain.append(q);q=g.get('parent_id')
 check(chain[1:]==expected_tail,f'{id} has complete expected parent chain')
# Verify all retained original and metadata bytes, both compressed and restored.
manifest=json.loads((P/'sources.json').read_text())
for item in manifest['retained_files']:
 raw=(P/item['file']).read_bytes(); restored=gzip.decompress(raw)
 check(sha(raw)==item['compressed_sha256'],f"retained archive hash {item['file']}")
 check(sha(restored)==item['uncompressed_sha256'] and len(restored)==item['uncompressed_bytes'],f"restored source hash/size {item['file']}")
source=json.loads(read_gz('geoboundaries-COL-ADM2-geojson.json.gz')); src={x['properties']['shapeID']:x for x in source['features']}
check(len(source['features'])==1122,'pinned full geoBoundaries Colombia ADM2 source contains 1,122 features')
departments=json.loads(read_gz('dane-divipola-departamentos-data.json.gz')); check(len(departments)==33,'DANE DIVIPOLA 2024 resource lists 33 department/capital-district units')
municipal=json.loads(read_gz('dane-divipola-municipios-data.json.gz')); check(len(municipal)==1122,'DANE DIVIPOLA 2024 municipality resource has 1,122 rows')
centres=json.loads(read_gz('dane-divipola-centros-poblados-data.json.gz'));check(len(centres)==8161,'DANE 2024 centros-poblados resource has 8,161 rows')
by_name=collections.defaultdict(list)
for row in municipal: by_name[(norm(row['dpto']),norm(row['nom_mpio']))].append(row)
aliases={('cesar','becerrill'):('cesar','becerril'),('bogotacapitaldistrict','bogotadc'):('bogotadc','bogotadc'),('santander','jordansube'):('santander','jordan'),('boyaca','guican'):('boyaca','guicandelasierra')}
center_counts=collections.Counter((str(x['codigo_departamento']).zfill(2),str(x['codigo_municipio']).zfill(5),x['tipo_centro_poblado']) for x in centres)
center_rows={}
for (dept,code,typ),count in center_counts.items(): center_rows.setdefault((dept,code),{})[typ]=count
# Confirm neighboring packet workloads partition the published Colombia area.
all_area=set()
for rel in index['parts']:
 for feature in json.loads((ROOT/'data'/rel).read_text()).get('features',[]):
  q=feature['properties'].get('parent_id'); seen=set()
  while q and q not in seen:
   seen.add(q)
   if q==expected_area: all_area.add(feature['id']); break
   q=groups.get(q,{}).get('parent_id')
peer=json.loads((P/'peer-packet-partition.json').read_text()); peer_sets={int(n):set(v) for n,v in peer['colombia_packet_member_ids'].items()}
check(len(all_area)==1122 and peer['current_descendant_count']==1122,'published Colombia area currently has 1,122 descendants')
check(sum(map(len,peer_sets.values()))==1122 and len(set().union(*peer_sets.values()))==1122,'neighboring batch scopes are disjoint and cover 1,122 IDs')
check(set().union(*peer_sets.values())==all_area,'neighboring batches cover every Colombia-area descendant')
check(peer_sets[494]==assigned,'#494 peer partition exactly matches this issue scope')
for packet in peer['packets']:
 n=packet['issue'];subset=peer_sets[n]
 check(len(subset)==packet['filtered_current_area_count'] and sha('\n'.join(sorted(subset)).encode())==packet['member_ids_sha256'],f'peer issue #{n} area scope fingerprint')
rows=[json.loads(line) for line in (P/'audit.jsonl').read_text().splitlines() if line.strip()]; audit={'subjects':rows,'name_variant_location_ids':[r['location_id'] for r in rows if r['assessment']=='correction-needed']};check(len(rows)==265 and {x['location_id'] for x in rows}==assigned,'audit has one row for each of 265 subjects')
check(collections.Counter(x['assessment'] for x in rows)=={'justified':260,'correction-needed':3,'insufficient-evidence':2},'every subject has a justified/correction-needed/insufficient-evidence classification')
scoped=collections.Counter(); centers_total=collections.Counter(); variants=[]
for row in rows:
 id=row['location_id']; f=features[id]; md=f['properties']['metadata']; source_feature=src.get(row['geoBoundaries_shape_id'])
 check(source_feature is not None,f'{id} has retained original source ID')
 check(source_feature['properties']['shapeGroup']=='COL' and source_feature['properties']['shapeType']=='ADM2',f'{id} source country/tier')
 check(source_feature['properties']['shapeName']==row['geoBoundaries_source_name'],f'{id} source name preserved')
 check(md['original_id']==row['geoBoundaries_shape_id'],f'{id} indexed original ID matches audit')
 key=(norm(row['department']),norm(row['name'])); candidates=by_name[key]
 if not candidates and (key[0],key[1]) in aliases:
  candidates=by_name[aliases[key]]
  if id!='gb:COL:ADM2:7082276B37057214617227': variants.append(id)
 check(len(candidates)==1,f'{id} unique DANE administrative crosswalk')
 d=candidates[0]; check(d['cod_mpio']==row['dane_divipola_code'] and d['cod_dpto']==row['dane_department_code'],f'{id} DANE DIVIPOLA department/municipality codes')
 check(d['tipo_municipio']=='Municipio',f'{id} DANE administrative role is municipality')
 check(row['dane_official_department_name']==d['dpto'] and row['dane_official_municipality_name']==d['nom_mpio'],f'{id} official DANE spelling preserved')
 center_key=(str(d['cod_dpto']).zfill(2),str(d['cod_mpio']).zfill(5)); types=center_rows.get(center_key,{})
 check(types==row['centros_poblados_type_counts'],f'{id} DANE settlement-center categories/counts')
 check(types.get('CM')==1,f'{id} has one DANE municipal-seat center')
 check(row['source_polygon_component_count']==row['current_polygon_component_count']==1,f'{id} source/current geometry is one polygon component')
 scoped[d['dpto']]+=1; centers_total.update(types)
check(scoped=={'BOGOTÁ, D.C.':1,'CESAR':25,'META':29,'SANTANDER':87,'BOYACÁ':123},'five assigned parent scopes reconcile exact DANE 2024 counts')
check(len({r['dane_divipola_code'] for r in rows})==265,'all DANE DIVIPOLA municipality codes are unique within issue scope')
check(len(variants)==3 and set(variants)==set(audit['name_variant_location_ids']),'all three municipality name variants individually flagged')
check(collections.Counter(x['assessment'] for x in rows)=={'justified':260,'correction-needed':3,'insufficient-evidence':2},'every assigned subject has an explicit issue-acceptance classification')
check(centers_total=={'CM':265,'CP':750},'settlement roster totals 265 CM + 750 CP = 1,015')
parent_audit=json.loads((P/'parent-assessments.json').read_text())
check(len(parent_audit['parents'])==5,'all five assigned parents have individual administrative assessments')
check(collections.Counter(x['assessment'] for x in parent_audit['parents'])=={'justified':4,'correction-needed':1},'parent labels include one Bogotá name-review finding')
for parent in parent_audit['parents']:
 check(parent['scope_complete_for_parent'] and parent['current_child_count']==parent['dane_2024_count_in_scope'],'each assigned department parent is complete at its DANE count')
print('RESULT: all 265 administrative identities, official counts, settlement joins, and ancestry reproduce. This does not certify exact shared boundary topology, full land/island coverage, or settlement completeness.')
