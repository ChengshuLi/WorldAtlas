"""Compose pinned macro corrections in linked stages; never mutate or publish baseline."""
import argparse,copy,gzip,hashlib,json,os,pathlib,subprocess,tarfile
a=argparse.ArgumentParser();a.add_argument("--root",required=True);a.add_argument("--output",required=True);args=a.parse_args()
root=pathlib.Path(args.root).resolve();baseline=root/'data';output=pathlib.Path(args.output).resolve()
if output.is_relative_to(root) or root.is_relative_to(output):raise ValueError('Output must be independent of source checkout')
if output.exists():raise ValueError('Fresh linked stage required')
def read(p):
 p=pathlib.Path(p);return json.loads(gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes())
def write(p,v):
 p=pathlib.Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,separators=(',',':'),ensure_ascii=False))
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
index=read(baseline/'world-index.json');units=read(baseline/'hierarchy.json');hierarchy_pin=sha(baseline/'hierarchy.json')
manifest=read(pathlib.Path(__file__).resolve().parents[1]/'data/macro-improvements/combined-restoration/inputs.json')
for row in manifest['files']:
 if sha(root/row['path'])!=row['sha256']:raise ValueError('Pinned source bytes changed: '+row['path'])
paths={int(k):root/v for k,v in manifest['patches'].items()};patches={k:read(v)for k,v in paths.items()}
for issue,p in patches.items():
 if issue in [502,503] and p['input_hierarchy_sha256']!=hierarchy_pin:raise ValueError('Source baseline hierarchy changed')
 if issue==505 and p['baseline']['hierarchy_sha256']!=hierarchy_pin:raise ValueError('Europe/Asia baseline hierarchy changed')
 for filename,expected in p.get('input_part_sha256',{}).items():
  file=baseline/filename
  if not file.exists():file=root/filename
  if sha(file)!=expected:raise ValueError('Source baseline part changed: '+filename)
updates={};orig_source={}
for issue in [502,505]:
 for f in patches[issue]['existing_location_updates']:
  identifier=f['properties']['id']
  if identifier in updates:raise ValueError('Overlapping source mutation scope')
  updates[identifier]=f
for f in read(root/'data/macro-improvements/cook-restoration/prepared/originals-and-records.json.gz')['locations']:orig_source[f['properties']['id']]=f
for f in read(root/'data/macro-improvements/europe-asia-restoration/prepared/before-features.json.gz'):orig_source[f['properties']['id']]=f
report=read(root/'data/macro-improvements/oceania-restoration/candidate-report.json.gz');crosswalk=report['retained_identity_crosswalks'][0]
henderson=copy.deepcopy(crosswalk['before_feature']);henderson['properties']['name']=crosswalk['proposed_reference_name'];updates[henderson['properties']['id']]=henderson;orig_source[henderson['properties']['id']]=crosswalk['before_feature']
new=[];newgroups=[]
for issue in [501,502,503,505,506]:
 p=patches[issue];new.extend(p['added_features']);newgroups.extend(p.get('added_groups',p.get('added_units',p.get('new_groups',[]))))
creation_units=read(root/'data/macro-improvements/oceania-restoration/candidate-hierarchy.json.gz');wanted=set(report['new_group_ids']);newgroups.extend(u for u in creation_units if u['id']in wanted)
if len(new)!=34 or len(newgroups)!=8 or len({f['properties']['id']for f in new})!=34 or len({u['id']for u in newgroups})!=8:raise ValueError('Expected 34 new locations / eight new groups')
groupupdates={u['id']:u for u in patches[502]['existing_group_updates']};beforeunits={u['id']:u for u in units};namesunits=copy.deepcopy(units)
for u in namesunits:
 if u['id']in groupupdates:
  delta=groupupdates[u['id']]
  if u!=delta['before']:raise ValueError('Original group source properties differ')
  u.clear();u.update(copy.deepcopy(delta['after']))
for phase in ['baseline','reference','replacement','creation']:(output/phase/'geography').mkdir(parents=True,exist_ok=True)
for part in index['parts']:
 p=baseline/part;features=read(p)['features'];changed=[f for f in features if f['properties']['id']in updates]
 os.symlink(p,output/'baseline'/part)
 if not changed:
  for phase in ['reference','replacement','creation']:os.symlink(p,output/phase/part)
  continue
 for f in changed:
  identifier=f['properties']['id']
  if f!=orig_source[identifier]:raise ValueError('Original source feature differs: '+identifier)
 reference=[];replacement=[]
 for f in features:
  identifier=f['properties']['id']
  if identifier in updates:
   rf=copy.deepcopy(f);rf['properties']=copy.deepcopy(updates[identifier]['properties']);reference.append(rf);replacement.append(copy.deepcopy(updates[identifier]))
  else:reference.append(f);replacement.append(f)
 write(output/'reference'/part,{'type':'FeatureCollection','features':reference});write(output/'replacement'/part,{'type':'FeatureCollection','features':replacement});os.symlink(output/'replacement'/part,output/'creation'/part)
write(output/'baseline'/'world-index.json',index);os.symlink(baseline/'hierarchy.json',output/'baseline'/'hierarchy.json')
for phase in ['reference','replacement']:write(output/phase/'world-index.json',index);write(output/phase/'hierarchy.json',namesunits)
finalunits=copy.deepcopy(namesunits)+copy.deepcopy(newgroups);byunit={u['id']:u for u in finalunits};counts={u['id']:0 for u in finalunits};old_count=0;all_ids=set();parts=[]
for part in index['parts']:
 for f in read(output/'replacement'/part)['features']:
  identifier=f['properties']['id'];all_ids.add(identifier);old_count+=1;counts[f['properties']['parent_id']]+=1
 parts.append({'path':part,'baseline_sha256':sha(baseline/part),'reference_sha256':sha(output/'reference'/part),'replacement_sha256':sha(output/'replacement'/part),'baseline_linked':(output/'reference'/part).is_symlink()})
for u in finalunits:
 if u['parent_id']:counts[u['parent_id']]+=1
for f in new:
 identifier=f['properties']['id']
 if identifier in all_ids:raise ValueError('New source identity already exists')
 all_ids.add(identifier);counts[f['properties']['parent_id']]+=1
 parent=f['properties']['parent_id']
 for tier in ['province','area','region','subcontinent','continent']:
  unit=byunit.get(parent)
  if not unit or unit['level']!=tier:raise ValueError('Incomplete new parent chain')
  parent=unit['parent_id']
 if parent is not None:raise ValueError('Continent has parent')
touched_parents={f['properties']['parent_id']for f in new}|{u['id']for u in newgroups}|{u['parent_id']for u in newgroups}
for u in finalunits:
 previous=beforeunits.get(u['id']);oldcount=previous.get('metadata',{}).get('child_count')if previous else None
 if u['id']in touched_parents and (previous is None or counts[u['id']]!=oldcount):
  u.setdefault('metadata',{})['child_count']=counts[u['id']]
write(output/'creation'/'hierarchy.json',finalunits);newpart='geography/source-restoration-additions.json';write(output/'creation'/newpart,{'type':'FeatureCollection','features':new});write(output/'creation'/'world-index.json',dict(index,parts=index['parts']+[newpart]))
if old_count!=49589:raise ValueError('Original location inventory changed')
metadata_deltas=[];replacement_deltas=[]
for identifier,after in updates.items():
 before=orig_source[identifier]
 if before['properties']!=after['properties']:metadata_deltas.append({'location_id':identifier,'before_properties':before['properties'],'after_properties':after['properties']})
 if before['geometry']!=after['geometry']:
  archived=copy.deepcopy(before);archived['properties']=copy.deepcopy(after['properties']);replacement_deltas.append({'id':identifier,'before_feature':archived,'original_pre_reference_feature':before,'after_feature':after})
write(output/'composition.json',{'version':1,'publication_ready':False,'source_pins':[{'issue':issue,'path':str(filename.relative_to(root)),'sha256':sha(filename)}for issue,filename in paths.items()],'baseline_hierarchy_sha256':hierarchy_pin,'before_locations':49589,'after_locations':len(all_ids),'added_locations':len(new),'added_groups':len(newgroups),'source_part_preservation':parts,'reference_changed_location_properties':metadata_deltas,'reference_changed_groups':list(groupupdates.values()),'replacement_deltas':replacement_deltas,'new_ids':sorted(f['properties']['id']for f in new),'historical_claims_transferred':False,'geometric_stage_validated':False,'canonical_grid_compiled':False,'published':False,'macro_amendment':patches[506]['macro_amendment'],'holds':['Kingman Reef','Gardner Pinnacles'],'memory_policy':'No full-world feature array, all8GBbaselinefiles untouched; unchangedparts symlinked read-only, editedparts materialized in/tmp only. Finalinstallation packagingrequiresrealvalidatedbytes.'})
print(json.dumps({'output':str(output),'old_locations':old_count,'candidate_locations':len(all_ids),'new_locations':len(new),'new_groups':len(newgroups),'retained_reference_property_patches':len(metadata_deltas),'retained_geometry_replacements':len(replacement_deltas),'heavy_geometric_validation':False,'published':False}))

# Preserve raw, SHA-pinned creation wrappers before independent generic validation.
proofdir=output/'proof-input';(proofdir/'sources').mkdir(parents=True);proofs=[];origins=[]
def append(proof,raw,issue):
 if hashlib.sha256(raw).hexdigest()!=proof['source']['sha256']:raise ValueError('Creation source wrapper changed')
 archive=proof['source'].get('original_archive')
 if archive:
  source_path=(root/archive['path']).resolve()
  if not source_path.is_relative_to(root):raise ValueError('Raw source archive escapes checkout')
  archived=source_path.read_bytes();archived=gzip.decompress(archived)if source_path.suffix=='.gz' and not source_path.name.endswith('.tar.gz')else archived
  if hashlib.sha256(archived).hexdigest()!=archive['raw_sha256']:raise ValueError('Raw source archive changed')
 filename='sources/'+str(len(proofs))+'.geojson';(proofdir/filename).write_bytes(raw);value=copy.deepcopy(proof);value['source']['path']=filename;proofs.append(value);origins.append({'issue':issue,'location_id':value['location_id'],'source_sha256':value['source']['sha256']})
base=root/'data/macro-improvements/oceania-restoration';source=root/'data/macro-improvements/macro-coverage-oceania/grouped-named-land-restoration-candidates.geojson.gz'
source_features=read(source)['features'];by_name={f['properties']['name']:f for f in source_features}
for proof in patches[501]['creation_proofs']:
 f=next(f for f in patches[501]['added_features'] if f['id']==proof['location_id']);original=copy.deepcopy(by_name[f['properties']['name']]);original['id']=proof['source']['identity']
 # Existing producer uses JS JSON.stringify, including its number serialization.
 raw=subprocess.check_output(['node','-e','process.stdout.write(JSON.stringify(JSON.parse(require("fs").readFileSync(0,"utf8"))))'],input=json.dumps(original).encode());append(proof,raw,501)
base=root/'data/macro-improvements/cook-restoration/prepared';proof=patches[502]['creation_proof_after_name_crosswalk'];append(proof,(base/proof['source']['path']).read_bytes(),502)
for proof in read(root/'data/macro-improvements/three-island-restoration/creation-proofs.json.gz'):
 feature=next(f for f in patches[503]['added_features']if f['id']==proof['location_id']);wrapper={'type':'Feature','id':proof['source']['identity'],'properties':{'geometry_method':'Current OSM whole coast minus mapped inland-water polygons'},'geometry':feature['geometry']};append(proof,json.dumps(wrapper,separators=(',',':'),ensure_ascii=False).encode(),503)
base=root/'data/macro-improvements/europe-asia-restoration/prepared'
for proof in read(base/'creation-proofs.json'):append(proof,(base/proof['source']['path']).read_bytes(),505)
with tarfile.open(root/'data/macro-improvements/marcus-restoration/creation-proof.tar.gz')as archive:
 receipt=json.load(archive.extractfile('migration-receipt.json'))
 for proof in receipt['creation_proofs']:append(proof,archive.extractfile(proof['source']['path']).read(),506)
if len(proofs)!=34:raise ValueError('Creation proof inventory changed')
write(proofdir/'proofs.json',proofs);write(proofdir/'origins.json',origins)
composition=read(output/'composition.json');source=root/'data/macro-improvements/macro-coverage-oceania';gaz={s['name']:s for s in read(source/'gazetteers.json')};osm={s['name']:s for s in read(source/'osm-sources.json')};evidence=[]
for catalog,names in [(gaz,['Manuae','Aitutaki','Manihiki','Henderson']),(osm,['Manuae','Aitutaki','Manihiki'])]:
 for name in names:
  row=catalog[name];raw=gzip.decompress((source/row['path']).read_bytes())
  if hashlib.sha256(raw).hexdigest()!=row['sha256']:raise ValueError('Raw source evidence changed')
  evidence.append({'url':row['url'],'source_sha256':row['sha256'],'archive_path':str((source/row['path']).relative_to(root)),'supported_from':2026,'supported_to':2027,'status':'reference'})
receipt={'version':1,'reference_only':True,'historical_claims_transferred':False,'before_units':read(output/'baseline/hierarchy.json'),'retired_units':[],'group_changes':composition['reference_changed_groups'],'changed_location_properties':composition['reference_changed_location_properties'],'relationships':[],'source_evidence':evidence,'before_hierarchy_sha256':sha(output/'baseline/hierarchy.json'),'after_hierarchy_sha256':sha(output/'reference/hierarchy.json'),'summary':{'geometry_changes':0,'historical_records_touched':0,'regional_interior_approved':False}}
write(output/'reference-receipt.json',receipt)
