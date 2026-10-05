import json,hashlib,pathlib,collections,gzip
root=pathlib.Path('data/regional-review/regional-review-3c4fe25a21fa428d')
source=root/'source'
issue=json.load(open(source/'issue-api-response.json'))
assert hashlib.sha256((source/'issue-api-response.json').read_bytes()).hexdigest()=='cbc3cedce8ebf2d10955a304770c5c1e36dc095c3dde214b30b3949518fcac8b'
assert issue['number']==422 and issue['state']=='open'
body=issue['body']; scope=json.loads(body.split('```json\n')[1].split('\n```')[0])
baseline_commit='5391a5a2cc5bc3386d30e8c816de3f9388e70d99'
baseline_inputs={
 'data/world-index.json':'a62d4a74f0f969e228dfcdeb2797bb689ce9836c2498cadd31ed622ad2c38c03',
 'data/hierarchy.json':'568301690ef231a85856666b57876a5efe8d8c7c6e671a56d81307b2dc28b80b',
 'data/administrative-sources.json':'ed0051d2956271c72f8917e7da0c6f53e5dfb595bee5920cac489a65a747d633',
 'data/macro-foundation/macro-certificate.json':'f50f70fcb0756712ab7a7a388bc8cada093080518f07d3a6f7329758980ea81b',
 'data/macro-foundation/regional-handoffs.json.gz':'29af5204c1f28d2616d7d8d8bb18e5d718c8c1e6dab3637868b03a2381b5db2a',
 'data/macro-foundation/current-membership-inventory.json.gz':'db58f274debe5917f7fa21fdd2ab563f4761cfb673bd814b6402708fa10b06ab',
 'data/geographic-releases/release-5.json.gz':'23e84c82b59b74fa6de65e5e5571f4fdb81399ce8b159f0483a3bc2e4e9dbda9',
 'data/geography/part-15.json':'6f763059820d14a4eab78173a756a8869821dd810e94f77c20eb5510c6cfb1df',
 'data/geography/part-20.json':'9dda1b495f3e9934d23c99d3ba1c6a631078798c42c5ddb060dc5238a32b7c9f',
 'data/geography/part-22.json':'f7ac47c8a9012651773264a31bfd6b360394ad029dd1f9cf88d63150953070d3',
 'data/geography/part-28.json':'2aab2f36aeeb651ee8e6cc656e9541ad14e2ced2ea8160e8700ad4dc950c379d',
}
for path,digest in baseline_inputs.items():
 assert hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()==digest,(path,digest)
release=json.load(gzip.open('data/geographic-releases/release-5.json.gz','rt'))['release']
assert release['id']==scope['release']['id']
assert release['hierarchy_sha256']==scope['release']['hierarchy_sha256']
assert release['footprints_sha256']==scope['release']['footprints_sha256']
idx=json.load(open('data/world-index.json'))
hierarchy=json.load(open('data/hierarchy.json'))
hierarchy_by_id={row['id']:row for row in hierarchy}
assert len(hierarchy_by_id)==len(hierarchy)
features={}
occurrences=collections.Counter()
for rel in idx['parts']:
 for f in json.load(open(pathlib.Path('data')/rel))['features']:
  p=f['properties']; i=p.get('id')
  if i in scope['member_location_ids']:
   occurrences[i]+=1
   features[i]=(rel,p)
assert len(features)==230, len(features)
assert set(occurrences)==set(scope['member_location_ids']) and all(n==1 for n in occurrences.values()),occurrences
assert all(p['parent_id'] in hierarchy_by_id and hierarchy_by_id[p['parent_id']]['level']=='province'
           for _,p in features.values())
assert len(scope['member_location_ids'])==230
assert len(set(scope['member_location_ids']))==230
expected_subject_hash='885c311387b59b45b2afd67f31a796aaa7eb8b992f21a75d79ad07970de436be'
actual_subject_hash=hashlib.sha256(json.dumps(sorted(scope['member_location_ids']),separators=(',',':')).encode()).hexdigest()
assert actual_subject_hash==expected_subject_hash,(actual_subject_hash,expected_subject_hash)
# Exact collection file metadata and source facts captured from pinned project catalog.
catalog=json.load(open('data/administrative-sources.json'))
expected_sources={
 'gb:MKD:ADM2':('0a0d7340810fb353c3faa37ab9afea20830ce6124083ffe6321182277da61d01',84),
 'gb:MNE:ADM1':('9674292fbc0a50c68c6584a2ae23fae768e76cc796bdb7e3e009c0197aec6ae3',23),
 'gb:ROU:ADM1':('e70d8bedfcaad1b99f387b044f7e7563102b98ccee982496a092178d05f22387',42),
 'gb:SRB:ADM2':('f94ba868818e4f87dd24bc97aeaf37732cc23f6744facd1010cd91d2349fc884',145),
 'gb:XKX:ADM1':('9b07b08fe0f9ca5a26ddb6de2008ac235b38ffaf069063df9851711c2d358315',7),
}
source_rows=[]
source_data={}
upstream_metadata={}
for sid in scope['source_ids']:
 m=catalog[sid]; k=sid.split(':')[1:]; code,adm=k
 path=source/'gb'/f'gb-{code}-{adm}.geojson'
 b=path.read_bytes(); d=json.loads(b)
 digest=hashlib.sha256(b).hexdigest()
 assert digest==expected_sources[sid][0],(sid,digest,expected_sources[sid][0])
 assert len(d['features'])==expected_sources[sid][1],(sid,len(d['features']))
 source_data[sid]=d
 upstream=json.load(open(source/'gb'/f'{code}-{adm}-geoBoundaries-{code}-{adm}-metaData.json'))
 upstream_metadata[sid]=upstream
 assert upstream['boundaryID']==m['boundaryID'],(sid,upstream['boundaryID'])
 assert upstream['boundaryYear']==m['boundaryYearRepresented'],sid
 assert upstream['boundaryType']==m['boundaryType'],sid
 assert upstream['admUnitCount']==m['admUnitCount'],sid
 fmap={f['properties'].get('shapeID','').split('B')[0]:f for f in d['features']}
 # exact suffix is shapeID suffix after source boundary id prefix; explicitly validate shape IDs below
 prefix=m['boundaryID'].rsplit('-',1)[-1]
 fmap={f['properties'].get('shapeID',''):f for f in d['features'] if f['properties'].get('shapeID','').startswith(prefix)}
 meta={x['id']:x for _,x in features.values() if x['metadata']['source_id']==sid}
 missing=[]
 for locid,p in meta.items():
  oid=p['metadata']['original_id']
  if oid not in fmap: missing.append((locid,oid))
 assert not missing,(sid,missing[:2])
 source_rows.append({'source_id':sid,'code':code,'adm':adm,'catalog':m,'upstream_metadata':upstream,'path':str(path),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'features':len(d['features']),'scope_members':len(meta)})
# target evidence decisions, intentionally conservative and accompanied by per-subject reason.
by={'MKD':('correction-needed','The retained 2016 layer reports 84 municipalities. The State Statistical Office describes 80 municipalities at NTES level 4 and records 2014 and 2019 territorial changes; a 2016 vintage cannot be accepted as a complete roster without reconciling the 84-to-80 discrepancy and matching the 84 source polygons to the official spatial register.'),
'MNE':('justified','The source feature is a named municipality and this 2017 source layer contains all 23 units; MONSTAT’s 2017 publication independently reports 23 municipalities (as of December 2015). OSM/Wambacher geometry is a secondary boundary source; legal boundary alignment, islands, and Lake Skadar/Tuzi demarcation remain unverified.'),
'ROU':('correction-needed','The source layer contains the expected 42 county-level units (41 counties plus Bucharest Municipality, which has equivalent county-level status but is not itself a county). Preserve county-level geometry as a source candidate; separate Bucharest’s unit type and resolve the Atlas one-member county/province repeated-tier construction before semantic approval.'),
'SRB':('insufficient-evidence','The 2017 layer has 145 ADM2 features and the issue owns only 78 of them under the WGSRPD/YUG area partition. Official 2017 statistical material groups municipalities by administrative districts but its coverage excludes some AP Kosovo i Metohija data; available source metadata calls the OSM/Wambacher layer role “Unknown.” The scoped Serbian names/parent assignments and complete territorial coverage need feature-by-feature reconciliation against the 2017 geodetic register.'),
'XKX':('correction-needed','The retained feature collection has seven features named District of …, although the catalog calls it ADM1 / Municipalities and the issue assigns it source role Municipalities. Kosovo’s Statistical Agency describes seven regional zones and 38 administrative municipalities. These three scoped district polygons are not municipality units; restore the actual source/licence lineage and decide whether these districts belong in the atlas at all.')}
rows=[]
for locid in scope['member_location_ids']:
 rel,p=features[locid]; md=p['metadata']; code=md['source_id'].split(':')[1]; m=catalog[md['source_id']]
 raw=next(x for x in source_rows if x['source_id']==md['source_id'])
 g=source_data[md['source_id']]
 prefix=m['boundaryID'].rsplit('-',1)[-1]; orig=md['original_id']
 sf=next((f for f in g['features'] if f['properties'].get('shapeID','').startswith(prefix) and f['properties']['shapeID']==orig),None)
 assert sf is not None,(locid,orig)
 p2=sf['properties']; cls,reason=by[code]
 geom=sf['geometry']
 coords=geom.get('coordinates',[])
 polys=coords if geom.get('type')=='MultiPolygon' else [coords] if geom.get('type')=='Polygon' else []
 holes=sum(max(0,len(poly)-1) for poly in polys)
 vertex_count=sum(len(ring) for poly in polys for ring in poly)
 rows.append({'geometry_type':geom.get('type'),'polygon_components':len(polys),'hole_rings':holes,'coordinate_vertices':vertex_count,'location_id':locid,'name':p.get('name'),'reference_owner':p.get('reference_owner'),'parent_id':p.get('parent_id'),'source_id':md['source_id'],'source_role_in_atlas':md['source_role'],'source_vintage':md['reference_year'],'original_id':orig,'source_feature_name':p2.get('shapeName'),'source_shape_id':p2.get('shapeID'),'classification':cls,'finding':reason,'source_sha256':raw['sha256']})
assert len(rows)==230 and len({r['location_id'] for r in rows})==230
assert collections.Counter(r['classification'] for r in rows)
assert collections.Counter(r['source_id'] for r in rows)=={'gb:MKD:ADM2':84,'gb:MNE:ADM1':23,'gb:ROU:ADM1':42,'gb:SRB:ADM2':78,'gb:XKX:ADM1':3}
province_members=collections.defaultdict(list)
province_sources=collections.defaultdict(set)
for locid,(_,p) in features.items():
 province_members[p['parent_id']].append(locid)
 province_sources[p['parent_id']].add(p['metadata']['source_id'])
province_assessments=[]
for item in scope['province_scopes']:
 pid=item['id']; members=sorted(province_members.get(pid,[])); sids=sorted(province_sources.get(pid,[]))
 if not members: continue
 hierarchy_parent=hierarchy_by_id.get(pid)
 assert hierarchy_parent is not None and hierarchy_parent['level']=='province',pid
 codes=sorted({x.split(':')[1] for x in sids})
 if codes==['MKD']:
  classification='correction-needed'; finding='Atlas parent is a North Macedonia statistical region (NTES level 3), not a generic administrative province. Verify its official name/code and membership against the 2016 source and 80-unit current register; the 84-unit discrepancy prevents approval.'
 elif codes==['MNE']:
  classification='correction-needed'; finding='The parent has one municipality child and repeats that same municipality as a separate province tier. The municipality role/count is plausible, but a same-footprint, one-member administrative parent needs explicit hierarchy justification and source-boundary confirmation.'
 elif codes==['ROU']:
  classification='correction-needed'; finding='The parent has one county-level child and repeats that county geometry as a separate province tier. For Bucuresti, formal unit role also differs from the generic Counties label. Resolve the repeated tier and exact administrative status before approval.'
 elif codes==['SRB']:
  classification='insufficient-evidence'; finding='This Atlas parent is labelled as a Serbian administrative district and has scoped children; each child and district assignment needs a source-level reconciliation against the 2017 Spatial Units Register. This packet owns only part of the 145-feature OSM/Wambacher collection.'
 elif codes==['XKX']:
  classification='correction-needed'; finding='The parent is a one-member district grouping, repeating a Kosovo district boundary as a province and child. The source layer is seven districts, despite metadata/catalog calling it a 48-unit municipality layer; resolve source identity, role and Atlas tier.'
 else:
  classification='insufficient-evidence'; finding='Mixed source ownership in a province parent; requires integrated source/parent review.'
 province_assessments.append({'province_id':pid,'name':item['name'],'original_name':item['original_name'],'member_location_ids':members,'member_count':len(members),'declared_full_count':item['full_province_locations'],'hierarchy_child_count':hierarchy_parent['metadata']['child_count'],'hierarchy_basis':hierarchy_parent['metadata']['basis'],'hierarchy_review_reasons':hierarchy_parent['metadata']['review_reasons'],'semantic_review_action':hierarchy_parent['metadata']['semantic_review']['action'],'partial':item['partial'],'source_ids':sids,'classification':classification,'finding':finding})
assert len(province_assessments)==89,(len(province_assessments),len(scope['province_scopes']))
(source/'scope-subjects.json').write_text(json.dumps(scope,ensure_ascii=False,indent=2)+'\n')
(source/'source-manifest.json').write_text(json.dumps({'retrieved_at_utc':'2026-10-05','repository_commit':'9469f09592ced973a3448cf66b6100b741b64c0d','retrieval_note':'Direct HTTPS retrieval from the immutable geoBoundaries GitHub source commit via its LFS media endpoints. The full-resolution GeoJSON LFS OIDs match the SHA-256 digests in this manifest. Catalog sha256 values are retained verbatim but do not match these full-resolution GeoJSON payloads; the catalog does not identify which artifact those digests cover.','sources':[{**{k:r[k] for k in ['source_id','code','adm','path','bytes','sha256','features','scope_members']},'url':f"https://media.githubusercontent.com/media/wmgeolab/geoBoundaries/9469f09592ced973a3448cf66b6100b741b64c0d/releaseData/gbOpen/{r['code']}/{r['adm']}/geoBoundaries-{r['code']}-{r['adm']}.geojson",'catalog_url':r['catalog']['gjDownloadURL'],'boundary_id':r['catalog']['boundaryID'],'vintage':r['catalog']['boundaryYearRepresented'],'type':r['catalog']['boundaryType'],'canonical':r['catalog']['boundaryCanonical'],'catalog_source':r['catalog']['boundarySource'],'license':r['catalog']['boundaryLicense'],'license_source':r['catalog']['licenseSource'],'catalog_adm_count':r['catalog']['admUnitCount'],'catalog_sha256_uninterpreted':r['catalog']['sha256'],'upstream_metadata_adm_unit_count':r['upstream_metadata']['admUnitCount'],'upstream_metadata_path':f"source/gb/{r['code']}-{r['adm']}-geoBoundaries-{r['code']}-{r['adm']}-metaData.json"} for r in source_rows]},ensure_ascii=False,indent=2)+'\n')
assets=[]
for path in sorted((source/'gb').glob('*')):
 if path.name.endswith('.lfs-pointer'): continue
 b=path.read_bytes()
 ptr=path.with_suffix(path.suffix+'.lfs-pointer')
 lfs_oid=None
 if ptr.exists():
  pointer=ptr.read_text(); lfs_oid=pointer.split('oid sha256:')[1].splitlines()[0]
  assert hashlib.sha256(b).hexdigest()==lfs_oid,(path,lfs_oid)
  assert int(pointer.split('size ')[1].splitlines()[0])==len(b),path
 assets.append({'path':str(path.relative_to(root)),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'lfs_oid':lfs_oid})
(source/'asset-manifest.json').write_text(json.dumps({'retrieval_date_utc':'2026-10-05','repository_commit':'9469f09592ced973a3448cf66b6100b741b64c0d','baseline_commit':baseline_commit,'baseline_inputs':[{'path':p,'bytes':pathlib.Path(p).stat().st_size,'sha256':h} for p,h in baseline_inputs.items()],'assets':assets},ensure_ascii=False,indent=2)+'\n')
(source/'subject-assessments.json').write_text(json.dumps({'generated_from':'scope-subjects.json + pinned world-index + retained geoBoundaries source bytes','subjects':rows,'provinces':province_assessments},ensure_ascii=False,indent=2)+'\n')
print('source audit counts')
for r in source_rows: print(r['source_id'],r['features'],r['scope_members'],r['sha256'])
print('location classifications',collections.Counter(r['classification'] for r in rows))
print('province classifications',collections.Counter(r['classification'] for r in province_assessments))
