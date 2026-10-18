/* Proposed task-only scope adapter. Reuse reviewed complete bounds; never decode world source transports.
 * NODE24 THIS_FILE STABLE_REPO FROZEN_CONFIG FRESH_OUTPUT
 * Requires independent review and Main scheduling before any execution.
 */
import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {pathToFileURL, fileURLToPath} from 'node:url';

const need = (v, m) => { if (!v) throw Error(m); };
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const sha = raw => createHash('sha256').update(raw).digest('hex');
const bytes = v => Buffer.from(JSON.stringify(v) + '\n');
const objectId = raw => createHash('sha1').update(Buffer.concat([Buffer.from(`blob ${raw.length}\0`), raw])).digest('hex');
const hex = (v, n) => typeof v === 'string' && new RegExp(`^[a-f0-9]{${n}}$`).test(v);
const safe = v => typeof v === 'string' && !path.isAbsolute(v) && /^[A-Za-z0-9_./-]+$/.test(v)
  && v.split('/').every(p => p && p !== '.' && p !== '..');
const ordinary = name => {
  for (let p = path.resolve(name);; p = path.dirname(p)) {
    need(!fs.lstatSync(p, {throwIfNoEntry: false})?.isSymbolicLink(), 'Symlink path: ' + p);
    if (p === path.dirname(p)) break;
  }
};
// Identical inclusive conservative predicate used by the reviewed prior adapter.
const intersection = (a, b) => a[0] <= b[2] && b[0] <= a[2] && a[1] <= b[3] && b[1] <= a[3];
const FIJI = ['gb:FJI:ADM1:53030831B91072554514863', 'gb:FJI:ADM2:14151628B95966095088914', 'gb:FJI:ADM2:14151628B42533076410957'];
const HELPER = 'coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';
const [repoArgument, configArgument, outputArgument] = process.argv.slice(2);
need(process.argv.length === 5 && !process.execArgv.length && !process.env.NODE_OPTIONS?.trim() && !process.env.NODE_PATH?.trim(), 'Plain Node24 DRIVER REPO CONFIG FRESH_OUTPUT required');
const repo = path.resolve(repoArgument), configFile = path.resolve(configArgument), root = path.dirname(configFile), output = path.resolve(outputArgument);
ordinary(repo); ordinary(configFile); ordinary(output);
need(fs.statSync(repo).isDirectory() && fs.statSync(configFile).isFile() && !fs.existsSync(output)
  && output.startsWith(root+path.sep) && fs.statSync(path.dirname(output)).isDirectory(), 'Ordinary repository/config and absent task-only output required');
const configRaw = fs.readFileSync(configFile), config = JSON.parse(configRaw);
need(config.version === 2 && config.kind === 'parameterized-scope-retained-bounds-adapter-v2'
  && Array.isArray(config.countries) && same(config.target_frames, ['consumed', 'selected']), 'Frozen parameterized scope and both target frames required');
const env = {...process.env, GIT_NO_LAZY_FETCH:'1', GIT_NO_REPLACE_OBJECTS:'1', GIT_OPTIONAL_LOCKS:'0',
  GIT_TERMINAL_PROMPT:'0', GIT_CONFIG_NOSYSTEM:'1', GIT_CONFIG_GLOBAL:'/dev/null'};
const git = (...args) => execFileSync('git', ['-c','protocol.allow=never','-C',repo,...args], {env,maxBuffer:32*1024*1024});
const consumed = new Map(), treeAdmitted = new Map();
function treeOnly(pin) {
  need(pin && hex(pin.commit,40) && safe(pin.path) && pin.mode === '100644' && hex(pin.git_blob_oid,40)
    && Number.isSafeInteger(pin.bytes) && pin.bytes > 0 && hex(pin.sha256,64), 'Immutable ordinary pin required');
  const key = pin.commit + ':' + pin.path;
  if (treeAdmitted.has(key)) { need(same(treeAdmitted.get(key),pin),'Conflicting immutable tree pin'); return; }
  need(git('ls-tree','-z',pin.commit,'--',pin.path).toString() === `100644 blob ${pin.git_blob_oid}\t${pin.path}\0`, 'Tree identity differs: '+pin.path);
  treeAdmitted.set(key,pin);
}
function read(pin) {
  need(pin && Number.isSafeInteger(pin.bytes) && pin.bytes > 0 && pin.bytes <= 32*1024*1024
    && hex(pin.sha256,64) && hex(pin.git_blob_oid,40), 'Bounded complete input descriptor required');
  let raw, key;
  if (pin.commit) {
    treeOnly(pin); raw = git('cat-file','blob',pin.git_blob_oid); key = pin.commit+':'+pin.path;
  } else {
    need(safe(pin.task_file),'Frozen task-relative path required'); const file = path.join(root,pin.task_file); ordinary(file);
    need(fs.statSync(file).isFile(),'Ordinary frozen task input required'); raw=fs.readFileSync(file); key='task:'+pin.task_file;
  }
  need(raw.length===pin.bytes && sha(raw)===pin.sha256 && objectId(raw)===pin.git_blob_oid,'Complete input differs: '+key);
  consumed.set(key,pin); return raw;
}
function json(pin) {
  let raw=read(pin); if ((pin.path??pin.task_file).endsWith('.gz')) {
    raw=gunzipSync(raw,{maxOutputLength:32*1024*1024});
    if (pin.decoded_bytes!==undefined) need(raw.length===pin.decoded_bytes && sha(raw)===pin.decoded_sha256,'Decoded input differs');
  }
  return JSON.parse(raw);
}
function unique(rows,key,label) {
  need(Array.isArray(rows)&&rows.length,'Nonempty '+label+' required'); const map=new Map();
  for(const row of rows){need(!map.has(row[key]),'Duplicate '+label);map.set(row[key],row);} return map;
}
// The frozen scope contract declares subjects/roles; it does not alter the bounds method.
const scopeContract=json(config.inputs.scope_contract),declaredScopes=unique(scopeContract.countries,'iso','declared evaluation scopes');
need(scopeContract.version===1&&scopeContract.kind==='retained-bounds-evaluation-scope-contract-v1'
  &&same(config.countries.map(c=>c.iso),scopeContract.countries.map(c=>c.iso))
  &&same(config.expected,scopeContract.expected)&&config.expected.catalogue_families===368
  &&config.expected.source_features===73567&&same(scopeContract.target_frames,config.target_frames), 'Exact frozen scope contract required');
let declaredTargets=0,declaredCells=0;
for(const c of scopeContract.countries){
  need(/^[A-Z]{3}$/.test(c.iso)&&Number.isSafeInteger(c.target_count)&&c.target_count>0
    &&Number.isSafeInteger(c.native_cells)&&c.native_cells>0&&Array.isArray(c.parent_context_families), 'Explicit bounded scope declaration required');
  const m=/^gb:([A-Z]{3}):ADM([12])$/.exec(c.positive_family);
  need(m&&m[1]===c.iso&&same(c.parent_context_families,m[2]==='1'?[]:[`gb:${c.iso}:ADM1`])
    &&c.package_id===c.positive_family.replaceAll(':','-')+'--repair-evaluation', 'Supported positive-level and exact parent roles required');
  declaredTargets+=c.target_count;declaredCells+=c.native_cells;
}
need(declaredTargets===config.expected.targets&&declaredCells===config.expected.native_cells, 'Declared aggregate scope differs');
const closure=unique(config.code_closure,'path','accepted code closure'),visited=new Set();
function verifyCode(name) {
  if(visited.has(name))return;const pin=closure.get(name);need(pin?.commit===config.method_commit&&safe(pin.task_file),'Accepted closure missing');
  const raw=read(pin),file=path.join(root,pin.task_file);ordinary(file);need(fs.readFileSync(file).equals(raw),'Frozen helper differs');visited.add(name);
  for(const m of raw.toString().matchAll(/(?:from\s+|import\(\s*)['"]([.][^'"]+)['"]/g)){
    const child=path.posix.normalize(path.posix.join(path.posix.dirname(name),m[1]));if(/\.(mjs|js|cjs)$/.test(child))verifyCode(child);
  }
}
verifyCode(HELPER);need(visited.size===closure.size,'Unused/incomplete method closure');
const packageRaw=read(config.inputs.method_package),packageFile=path.join(root,config.inputs.method_package.task_file);ordinary(packageFile);
need(fs.readFileSync(packageFile).equals(packageRaw)&&JSON.parse(packageRaw).type==='module','Original method package context differs');
const currentHelper=read(config.inputs.current_coordinate_helper).toString(),oldHelper=read(closure.get(HELPER)).toString();
const exportBody=s=>s.split('export function coordinateBounds(g){')[1]?.split('export function possibleNeighbors')[0];
need(exportBody(oldHelper)&&exportBody(oldHelper)===exportBody(currentHelper),'Accepted current coordinateBounds changed');
need(config.inputs.current_native_grid.git_blob_oid===closure.get('src/native-grid.js').git_blob_oid,'Normative native grid changed');
treeOnly(config.inputs.current_native_grid);
const {coordinateBounds}=await import(pathToFileURL(path.join(root,closure.get(HELPER).task_file)));
const completion=json(config.inputs.completion),catalogue=json(config.inputs.catalogue),currentCatalogue=json(config.inputs.current_catalogue);
need(completion.inventory_complete===true&&completion.complete_source_features===73567&&completion.complete_families===368
  && config.inputs.catalogue.sha256===config.inputs.current_catalogue.sha256&&same(catalogue,currentCatalogue),'Reviewed complete unchanged catalogue required');
const products=unique(catalogue.products,'key','families'),custody=json(config.inputs.whole_family_custody),families=unique(custody.families,'key','custody families');
need(products.size===368&&families.size===368,'Complete family metadata required');
const currentParts=unique(config.source_parts_current,'path','current source transports');let partCount=0;
for(const family of catalogue.products){
  const old=families.get(family.key);need(old&&old.complete_observed_features===family.feature_count,'Reviewed whole family incomplete');
  let offset=0;for(const [i,p]of family.parts.entries()){
    const prior=old.authenticated_parts[i],now=currentParts.get(p.path);
    need(p.ordinal===i&&p.offset===offset&&now&&prior&&now.git_blob_oid===prior.git_blob_oid
      &&now.bytes===p.bytes&&now.sha256===p.sha256&&now.decoded_bytes===p.uncompressed_bytes
      &&now.decoded_sha256===p.uncompressed_sha256,'Whole original transport changed');treeOnly(now);offset+=p.uncompressed_bytes;partCount++;
  }need(offset===family.original_bytes&&old.original_sha256===family.original_sha256,'Whole original family changed');
}
need(partCount===370&&currentParts.size===370,'Complete 370 unchanged transports required');
const roster=json(config.inputs.roster),sources=unique(roster,'source_id','source roster');need(sources.size===73567,'Complete source roster required');
const seams=unique(json(config.inputs.seams),'source_id','Fiji seam records'),proofs=unique(json(config.inputs.periodic_review).features,'source_id','Fiji native proofs');
need(same([...seams.keys()].sort(),[...FIJI].sort())&&same([...proofs.keys()].sort(),[...FIJI].sort()),'Exact retained three exceptions required');
const priorPeriodic=json(config.inputs.previous_periodic_outcomes);read(config.inputs.periodic_review_method);read(config.inputs.periodic_documentation);
read(config.inputs.previous_result_review);const previousConfig=json(config.inputs.previous_config),previousDriver=read(config.inputs.previous_driver);
need(sha(previousDriver)===completion.driver_sha256&&config.inputs.previous_config.sha256===completion.config_sha256
  &&previousConfig.method_commit===config.method_commit,'Reviewed prior producer identity differs');
const selection=json(config.inputs.native_selection),manifest=json(config.inputs.native_manifest);
need(manifest.size===262166&&selection.sha256===config.inputs.native_manifest.sha256&&selection.manifest_path===config.inputs.native_manifest.path
  &&selection.method===manifest.method,'Normative native contract changed');
const denominator=BigInt(manifest.size),floor=(n,d)=>n>=0n?n/d:-((-n+d-1n)/d),ceil=(n,d)=>-floor(-n,d);
const targetMap=new Map();let requestedCells=0;
const countries=config.countries.map(c=>{
  const declared=declaredScopes.get(c.iso);
  need(declared&&c.positive_family===declared.positive_family&&same(c.parent_context_families,declared.parent_context_families), 'Country roles differ from frozen declaration');
  const ownFamilies=[c.positive_family,...c.parent_context_families],actualOwnFamilies=[...products.keys()].filter(f=>f.startsWith(`gb:${c.iso}:`));
  need(new Set(ownFamilies).size===ownFamilies.length&&ownFamilies.every(f=>products.has(f))
    &&same([...ownFamilies].sort(),actualOwnFamilies.sort()), 'Every retained own family must have exactly one declared role');
  const stages=unique(json(c.stage),'target','whole stages'),members=unique(json(c.membership),'source_id','target membership'),pkg=json(c.package);
  read(c.original_membership);need(stages.size===c.target_ids.length&&stages.size===declared.target_count&&members.size===declared.target_count
    &&pkg.package_id===declared.package_id&&pkg.location_count===declared.target_count&&pkg.native_cells===declared.native_cells, 'Complete declared original stage scope required');
  const owners=new Set(),targets=c.target_ids.map(id=>{
    const s=stages.get(id),m=members.get(id),original=sources.get(id);need(s&&m&&original&&!targetMap.has(id),'Missing/duplicate original target');
    need(id.startsWith(c.positive_family+':')&&m.source_id===id&&m.target_id===id&&s.selected.id===id&&same(original.owners,[m.pixelIndex])&&original.source_index===m.source_index
      &&original.ordinal===m.source_ordinal&&s.consumed.properties.shapeID===id.slice(c.positive_family.length+1),'Original target association differs');
    const t={id,pixelIndex:m.pixelIndex,source_index:original.source_index,original_geometry_sha256:sha(bytes(s.consumed.geometry)),
      original_properties:s.consumed.properties,frames:{consumed:coordinateBounds(s.consumed.geometry),selected:coordinateBounds(s.selected.geometry)}};
    owners.add(m.pixelIndex);targetMap.set(id,t);return t;
  });
  need(same([...owners].sort((a,b)=>a-b),[...pkg.owners].sort((a,b)=>a-b)),'Original owners changed');
  let cells=0,segments=0,min=Infinity,max=-Infinity;const classes={land:0,'inland-water':0},contacts=new Set(),seenOwners=new Set();
  need(c.intervals.length===pkg.native_blocks.length,'Original interval blocks incomplete');
  for(const [i,p]of c.intervals.entries()){
    need(p.task_file.endsWith(`/block-${String(pkg.native_blocks[i]).padStart(3,'0')}.json.gz`),'Original block order differs');
    for(const [y,a,z,oi,si,k]of json(p)){
      need(Number.isSafeInteger(y)&&y>=0&&y<manifest.size&&Number.isSafeInteger(a)&&Number.isSafeInteger(z)
        &&a>=0&&z<=manifest.size&&z>a&&Object.hasOwn(classes,k)&&Array.isArray(oi)&&Array.isArray(si),'Original native interval malformed');
      cells+=z-a;classes[k]+=z-a;segments++;min=Math.min(min,a);max=Math.max(max,z-1);oi.forEach(o=>seenOwners.add(o));si.forEach(o=>contacts.add(o));
    }
  }
  need(cells===pkg.native_cells&&segments===pkg.interval_segments&&classes.land===pkg.land_cells&&classes['inland-water']===pkg.inland_water_cells
    &&same([...seenOwners].sort((a,b)=>a-b),[...pkg.owners].sort((a,b)=>a-b))
    &&same([...contacts].sort((a,b)=>a-b),[...pkg.source_features].sort((a,b)=>a-b)),'Original cells/classes/contacts changed');
  const west=360n*BigInt(min)+180n-180n*denominator,east=360n*BigInt(max)+180n-180n*denominator;
  const enclosure=[Number(floor(west,denominator)),Number(ceil(east,denominator))];
  need(c.expected_scope.cells===cells&&c.expected_scope.intervals===segments&&same(c.expected_scope.exact_longitude_numerators,[String(west),String(east)])
    &&same(c.expected_scope.longitude_enclosure,enclosure)&&c.expected_scope.longitude_denominator===String(denominator),'Frozen native enclosure differs');
  requestedCells+=cells;return {...c,own_families:ownFamilies,targets,enclosure,feature_counts:{positive:0,parent_context:0,foreign:0,foreign_candidates:0,foreign_disjoint:0,foreign_unresolved:0},candidates:new Set(),unresolved:new Set()};
});
need(targetMap.size===config.expected.targets&&requestedCells===config.expected.native_cells,'Exact complete declared target/key scope required');
const expectedOutputs=new Map(completion.outputs.map(p=>[p.path,p]));
need(config.retained_bounds_shards.length===12,'Complete retained shard inventory required');
for(const p of config.retained_bounds_shards){const prior=expectedOutputs.get(path.posix.basename(p.path));need(prior&&prior.bytes===p.bytes&&prior.sha256===p.sha256,'Retained shard not in reviewed completion');}

fs.mkdirSync(output);const emitted=[];let shard=null,ordinal=0;
function finish(){if(!shard)return;fs.closeSync(shard.fd);emitted.push({path:shard.name,bytes:shard.length,sha256:shard.hash.digest('hex'),records:shard.records});shard=null;}
function emit(value){const raw=bytes(value);need(raw.length<=8*1024*1024,'One complete outcome record exceeds retained shard bound');
  if(!shard||shard.length+raw.length>8*1024*1024){finish();const name=`whole-source-bounds-${String(ordinal++).padStart(3,'0')}.jsonl`;shard={name,fd:fs.openSync(path.join(output,name),'wx'),length:0,records:0,hash:createHash('sha256')};}
  fs.writeFileSync(shard.fd,raw);shard.length+=raw.length;shard.records++;shard.hash.update(raw);}
function write(name,value){const raw=bytes(value);need(raw.length<=32*1024*1024,'Ordinary metadata output too large');fs.writeFileSync(path.join(output,name),raw,{flag:'wx'});emitted.push({path:name,bytes:raw.length,sha256:sha(raw)});}
const validBounds=b=>Array.isArray(b)&&b.length>0&&b.every(a=>Array.isArray(a)&&a.length===4&&a.every(Number.isFinite)
  &&a[0]>=-180&&a[2]<=180&&a[1]>=-90&&a[3]<=90&&a[0]<=a[2]&&a[1]<=a[3]);
const seen=new Set(),familyCounts=new Map(),periodic=[],targetJoins=new Set();let ownerless=0;const started=performance.now();
for(const pin of config.retained_bounds_shards){
  const raw=read(pin);need(raw.at(-1)===10,'Incomplete JSONL shard');let records=0;
  for(const line of raw.toString().split('\n')){if(!line)continue;const r=JSON.parse(line),source=sources.get(r.source_id),family=products.get(r.source_family);records++;
    need(source&&family&&!seen.has(r.source_id)&&r.source_id.startsWith(r.source_family+':')&&source.source_index===r.source_index
      &&source.ordinal===r.feature_ordinal&&same(source.owners,r.owners)&&family.original_sha256===r.whole_original_sha256,'Retained full source identity differs');
    seen.add(r.source_id);familyCounts.set(r.source_family,(familyCounts.get(r.source_family)??0)+1);if(r.owners.length===0)ownerless++;
    need(Array.isArray(r.country_outcomes)&&same(r.country_outcomes.map(x=>x.country_iso),['MEX','ECU','BOL','PER','COL']),'Prior complete outcomes missing');
    const target=targetMap.get(r.source_id);if(target){need(target.original_geometry_sha256===r.original_geometry_sha256&&same(target.original_properties,r.original_properties),'Whole new target original differs');targetJoins.add(r.source_id);}
    const seam=seams.get(r.source_id),proof=proofs.get(r.source_id);let usable=validBounds(r.complete_part_bounds),isPeriodic=false;
    if(seam){
      need(r.raw_coordinate_error==='Invalid/nonfinite coordinate'&&r.bounds_frame==='retained-periodic-native-equality-view'
        &&seam.source_product_sha256===r.whole_original_sha256&&seam.ordinal===r.feature_ordinal&&seam.source_index===r.source_index
        &&same(seam.owners,r.owners)&&sha(bytes(seam.original_geometry))===r.original_geometry_sha256
        &&sha(bytes(seam.geometry))===r.retained_canonical_geometry_sha256&&seam.original_shapely_valid===true&&seam.canonical_shapely_valid===true
        &&seam.normalization==='retained-majority-canonical-periodic-unwrap-make-valid-v1'&&proof.exact_output_match===true
        &&Number.isSafeInteger(proof.row_start)&&Number.isSafeInteger(proof.row_end)&&proof.row_end>proof.row_start,'Retained whole Fiji equality evidence differs');
      need(priorPeriodic.rows.filter(x=>x.source_id===r.source_id).length===5&&priorPeriodic.rows.filter(x=>x.source_id===r.source_id).every(x=>
        x.original_geometry_sha256===r.original_geometry_sha256&&x.retained_canonical_geometry_sha256===r.retained_canonical_geometry_sha256
        &&same(x.retained_independent_full_native_comparison,proof)),'Prior periodic proof join differs');isPeriodic=true;
    }else if(r.raw_coordinate_error!==null||r.bounds_frame!=='strict-complete-original-coordinate-bounds')usable=false;
    const outcomes=countries.map(c=>{
      const role=r.source_family===c.positive_family?'positive-complete-source-family':c.parent_context_families.includes(r.source_family)?'own-country-parent-context':'foreign-original';
      c.feature_counts[role==='foreign-original'?'foreign':role==='own-country-parent-context'?'parent_context':'positive']++;
      const matched={consumed:[],selected:[]};if(usable)for(const t of c.targets)for(const frame of config.target_frames)
        if(r.complete_part_bounds.some(a=>t.frames[frame].some(b=>intersection(a,b))))matched[frame].push(t.id);
      const ids=[...new Set([...matched.consumed,...matched.selected])].sort();let status;
      if(!usable)status='unresolved-retained-coordinate-outcome';
      else if(!isPeriodic)status=ids.length?'whole-bounds-candidate':'whole-bounds-disjoint';
      else{const keyDisjoint=r.complete_part_bounds.every(b=>b[2]<c.enclosure[0]||b[0]>c.enclosure[1]);
        status=ids.length===0&&keyDisjoint?'retained-periodic-bounds-and-native-key-enclosure-disjoint':'unresolved-retained-periodic-contact';
        periodic.push({country_iso:c.iso,source_id:r.source_id,original_geometry_sha256:r.original_geometry_sha256,
          retained_canonical_geometry_sha256:r.retained_canonical_geometry_sha256,whole_consumed_and_selected_bounds_disjoint:ids.length===0,
          native_enclosure:c.enclosure,native_key_enclosure_disjoint:keyDisjoint,independent_whole_native_equality:proof,status});}
      if(role==='foreign-original'){
        if(status.startsWith('unresolved')){c.unresolved.add(r.source_family);c.feature_counts.foreign_unresolved++;}
        else if(ids.length)c.feature_counts.foreign_candidates++;else c.feature_counts.foreign_disjoint++;
        if(ids.length||status.startsWith('unresolved'))c.candidates.add(r.source_family);
      }
      return {country_iso:c.iso,role,status,target_ids:ids,frame_target_ids:matched};
    });
    emit({...r,new_country_outcomes:outcomes});
  }
  need(records===expectedOutputs.get(path.posix.basename(pin.path)).records,'Retained shard record count differs');
}
finish();need(seen.size===73567&&roster.every(r=>seen.has(r.source_id))&&targetJoins.size===config.expected.targets&&periodic.length===FIJI.length*countries.length,'Complete source/target/periodic coverage required');
for(const [family,p]of products)need(familyCounts.get(family)===p.feature_count,'Complete family omitted');
const summaries=countries.map(c=>{
  need(c.feature_counts.positive+c.feature_counts.parent_context+c.feature_counts.foreign===73567
    &&c.feature_counts.foreign_candidates+c.feature_counts.foreign_disjoint+c.feature_counts.foreign_unresolved===c.feature_counts.foreign,'Complete outcome conservation differs');
  need(c.feature_counts.positive===products.get(c.positive_family).feature_count
    &&c.feature_counts.parent_context===c.parent_context_families.reduce((n,f)=>n+products.get(f).feature_count,0), 'Declared positive/parent feature conservation differs');
  const unresolved=[...c.unresolved].sort(),candidate=[...c.candidates].sort();return {country_iso:c.iso,target_count:c.targets.length,
    positive_family:c.positive_family,parent_context_families:c.parent_context_families,own_families:c.own_families,complete_foreign_families:products.size-c.own_families.length,
    complete_target_frames:c.targets,original_scope:c.expected_scope,feature_counts:c.feature_counts,
    whole_bounds_candidate_families:candidate,unresolved_families:unresolved,stock_scope_ready:unresolved.length===0,
    stock_territorial_exclusion_families:unresolved.length?null:candidate};
});
write('country-foreign-applicability.json',{version:1,countries:summaries});write('retained-periodic-outcomes-current-scopes.json',{rows:periodic});
const complete=summaries.every(c=>c.stock_scope_ready);
write('completion.json',{version:2,kind:'parameterized-scope-retained-complete-bounds-applicability',inventory_complete:true,country_applicability_complete:complete,
  source_result:config.inputs.completion,previous_outputs_preserved:true,complete_source_features:73567,complete_families:368,retained_ownerless_features:ownerless,
  complete_target_members:config.expected.targets,original_requested_cells:config.expected.native_cells,source_geometry_bodies_read:0,
  whole_target_stage_members_read:config.expected.targets,new_country_outcomes:73567*countries.length,
  driver_sha256:sha(fs.readFileSync(fileURLToPath(import.meta.url))),config_sha256:sha(configRaw),inputs:[...consumed.values()],
  unchanged_source_transports:[...currentParts.values()],outputs:emitted,seconds:(performance.now()-started)/1000,
  process_max_rss_platform_units:process.resourceUsage().maxRSS,platform:process.platform,
  limits:['Whole world geometry was not replayed; reviewed complete per-part bounds and unchanged whole-source identities reused.',
    'source_geometry_bodies_read=0 refers to global source-corpus transport decoding; whole consumed and selected target-stage geometries are read.',
    'Consumed plus selected frames create a conservative candidate superset under the identical inclusive relation; no geometry equivalence inferred.',
    'All five original per-country outcomes retained, with declared-scope outcomes appended for every original including ownerless/disjoint records.',
    'No physical/native/source semantic, source-rights, current-owner-zero, selected delivery or accepted repair credit.',
    'Runtime/resource values are observations, not process-tree/time/memory enforcement.']});
console.log(JSON.stringify({inventory_complete:true,country_applicability_complete:complete,complete_features:seen.size,targets:config.expected.targets,output}));
if(!complete)process.exitCode=2;
