"""Authenticate exact upstream full/simplified geoBoundaries Japan products; no overlay."""
import gzip, hashlib, json, pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]; REPO=ROOT.parents[2]
def sha(b):return hashlib.sha256(b).hexdigest()
def canonical(x):return json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()+b'\n'
def lfs(path):
 v={}
 for line in pathlib.Path(path).read_text().splitlines():
  k, val=line.split(' ',1);v[k]=val
 return v
full_path=ROOT/'sources/geoboundaries/full-product.geojson'; full_raw=full_path.read_bytes()
full_pointer=lfs(ROOT/'sources/geoboundaries/full-product.pointer')
if sha(full_raw)!=full_pointer['oid'].split(':',1)[1] or len(full_raw)!=int(full_pointer['size']):raise ValueError('Full upstream LFS product differs')
simpl_pointer=lfs(ROOT/'sources/geoboundaries/simplified-product.pointer')
metadata_path=ROOT/'sources/geoboundaries/metadata.json';metadata_raw=metadata_path.read_bytes()
metadata_pointer=lfs(ROOT/'sources/geoboundaries/metadata.pointer')
if sha(metadata_raw)!=metadata_pointer['oid'].split(':',1)[1] or len(metadata_raw)!=int(metadata_pointer['size']):raise ValueError('Upstream metadata LFS body differs')
metadata=json.loads(metadata_raw)
source_registry=json.loads((REPO/'data/administrative-sources.json').read_bytes())
registry=source_registry['gb:JPN:ADM2']
corpus=json.loads((REPO/'coordination/engineering/original-geography-source-corpus-20261006/catalogue.json').read_bytes())
product=next(x for x in corpus['products'] if x['key']=='gb:JPN:ADM2')
part=product['parts'][0];encoded=(REPO/part['path']).read_bytes()
if len(encoded)!=part['bytes'] or sha(encoded)!=part['sha256']:raise ValueError('Consumed product encoded source differs')
simpl_raw=gzip.decompress(encoded)
if len(simpl_raw)!=product['original_bytes'] or sha(simpl_raw)!=product['original_sha256'] or sha(simpl_raw)!=simpl_pointer['oid'].split(':',1)[1] or len(simpl_raw)!=int(simpl_pointer['size']):raise ValueError('Complete consumed simplified source differs from upstream')
full=json.loads(full_raw)['features'];simpl=json.loads(simpl_raw)['features']
def roster(rows):
 result={}
 for f in rows:
  sid=f['properties'].get('shapeID')
  if not isinstance(sid,str) or not sid or sid in result:raise ValueError('Missing or duplicate source shapeID')
  result[sid]=f
 return result
full_by=roster(full);simpl_by=roster(simpl)
if metadata['boundaryID']!='JPN-ADM2-22064153' or metadata['boundaryYear']!='2017' or metadata['boundaryCanonical']!='Subprefectures':raise ValueError('Unexpected geoBoundaries source metadata')
if metadata['boundarySource']!='OpenStreetMap, Wambacher' or metadata['boundaryLicense']!='Creative Commons Attribution-ShareAlike 2.0':raise ValueError('Unexpected recorded underlying-source attribution/license')
if len(full)!=1742 or len(simpl)!=1742:raise ValueError('Actual delivered feature count differs from source bodies')
missing_full=sorted(set(full_by)-set(simpl_by));missing_simpl=sorted(set(simpl_by)-set(full_by))
geometry_changed=[]
for sid in sorted(set(full_by)&set(simpl_by)):
 if canonical(full_by[sid]['geometry'])!=canonical(simpl_by[sid]['geometry']):geometry_changed.append(sid)
issues=json.loads((ROOT/'inputs/immutable-scope-and-inputs.json').read_bytes())
contacts={x.rsplit(':',1)[1] for x in issues['contacts']}
if not contacts<=set(full_by) or not contacts<=set(simpl_by):raise ValueError('A scoped full Atlas contact has no same-ID recorded source feature')
contact_context=[]
for subject in issues['contacts']:
 sid=subject.rsplit(':',1)[1]
 for label,features in [('full',full_by),('simplified',simpl_by)]:
  f=features[sid]
  contact_context.append({'subject_id':subject,'product':label,'source_shape_id':sid,'shape_name':f['properties'].get('shapeName'),'feature_sha256':sha(canonical(f)),'geometry_sha256':sha(canonical(f['geometry']))})
receipt={
 'status':'PASS','comparison_performed':False,
 'full_product':{'url':'https://media.githubusercontent.com/media/wmgeolab/geoBoundaries/9469f09/releaseData/gbOpen/JPN/ADM2/geoBoundaries-JPN-ADM2.geojson','bytes':len(full_raw),'sha256':sha(full_raw),'upstream_lfs_oid':full_pointer['oid'],'upstream_lfs_size':int(full_pointer['size']),'features':len(full),'roster_sha256':sha(canonical(sorted(full_by)))},
 'consumed_simplified_product':{'url':product['recorded_consumed_url'],'bytes':len(simpl_raw),'sha256':sha(simpl_raw),'upstream_lfs_oid':simpl_pointer['oid'],'upstream_lfs_size':int(simpl_pointer['size']),'features':len(simpl),'roster_sha256':sha(canonical(sorted(simpl_by))),'atlas_registry_raw_sha256':registry['sha256'],'atlas_registry_raw_bytes':product['original_bytes'],'recorded_represented_year':product['source_represented_year_claim'],'recorded_license':product['recorded_license']},
 'metadata':metadata,'upstream_product_license':'CC BY 4.0 product attribution and per-feature citation required by exact retained CITATION-AND-USE file; per-feature recorded underlying license is CC BY-SA 2.0 and source is OpenStreetMap, Wambacher. Preserve both layers of terms; no territorial or positional accuracy claim.',
 'roster':{'full_count':len(full_by),'simplified_count':len(simpl_by),'missing_from_simplified':missing_full,'extra_in_simplified':missing_simpl,'geometry_changed_shape_ids':geometry_changed},
 'scoped_contacts':contact_context,
 'known_count_difference':'geoBoundaries metadata advertises 1745 units; both exact feature bodies contain 1742 unique shapeIDs. The 3-count discrepancy remains explicit and is not repaired or rebound.'}
(ROOT/'receipts/geoboundaries-input-authentication.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':'PASS','full_features':len(full),'simplified_features':len(simpl),'missing_from_simplified':len(missing_full),'extra_in_simplified':len(missing_simpl),'geometry_changed':len(geometry_changed),'contacts_bound':len(contact_context),'full_sha256':sha(full_raw),'simplified_sha256':sha(simpl_raw)}))
