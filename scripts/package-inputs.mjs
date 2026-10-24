import {scientificNativeSelection,finalBankSelection} from '../src/reference-metadata.js';
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {isDeepStrictEqual} from 'node:util';
import {isUtf8} from 'node:buffer';
import {compatiblePackageProducers} from './package-producer-contract.mjs';

export const PACKAGE_INPUT_FILE = '.github/package-inputs.json';
const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
export const safePackagePath = value => typeof value === 'string' && /^[A-Za-z0-9_.\/-]+$/.test(value)
  && !value.startsWith('/') && value.replace(/\/$/, '').split('/').every(part => part && part !== '.' && part !== '..');
export const containsPackagePath = (paths, file) => paths.some(input => input.endsWith('/') ? file.startsWith(input) : file === input);

// The one actual declared-input inventory shared by build capture and preview.
// It describes copied/consumed bytes, including dirty and untracked inputs, not HEAD.
export function materializedPackageInputs(root,definition=loadPackageInputs(root)) {
  root=fs.realpathSync(root);validatePackageInputs(definition);
  const actual=[];
  const ordinary=(relative,directory=false)=>{
    let at=root;const parts=relative.split('/');
    for(let i=0;i<parts.length;i++){
      if(!parts[i]||parts[i]==='.'||parts[i]==='..'||/[\\\0]/.test(parts[i]))throw Error('Unsafe package input path');
      at=path.join(at,parts[i]);const stat=fs.lstatSync(at);
      if(stat.isSymbolicLink()||!(i<parts.length-1||directory?stat.isDirectory():stat.isFile()))throw Error('Nonordinary package input: '+relative);
    }
    return at;
  };
  const visit=name=>{
    const file=ordinary(name),before=fs.lstatSync(file),fd=fs.openSync(file,fs.constants.O_RDONLY|fs.constants.O_NOFOLLOW);
    const digest=createHash('sha1').update(`blob ${before.size}\0`),buffer=Buffer.alloc(1048576);let bytes=0;
    try{
      for(;;){const count=fs.readSync(fd,buffer,0,buffer.length,null);if(!count)break;bytes+=count;digest.update(buffer.subarray(0,count));}
      const held=fs.fstatSync(fd),after=fs.lstatSync(file);
      if(bytes!==before.size||!['dev','ino','size','mode','mtimeMs','ctimeMs'].every(key=>before[key]===held[key]&&held[key]===after[key]))throw Error('Package input changed while inventorying');
    }finally{fs.closeSync(fd);}
    actual.push({path:name,mode:before.mode&0o111?'100755':'100644',oid:digest.digest('hex')});
  };
  const walk=name=>{ordinary(name,true);for(const part of fs.readdirSync(path.join(root,name))){const child=name+'/'+part,stat=fs.lstatSync(path.join(root,child));if(stat.isDirectory()&&!stat.isSymbolicLink())walk(child);else visit(child);}};
  for(const input of definition.inputs){
    if(!fs.existsSync(path.join(root,input))){if(!definition.optional_inputs.includes(input))throw Error('Required original input absent');continue;}
    if(input.endsWith('/'))walk(input.slice(0,-1));else visit(input);
  }
  return actual.sort((a,b)=>a.path.localeCompare(b.path,'en'));
}

export function validatePackageInputs(value) {
  if (value?.version !== 1) throw Error('Unsupported package input definition');
  for (const name of ['inputs', 'optional_inputs', 'verification_paths', 'generated_outputs']) {
    const rows = value[name];
    if (!Array.isArray(rows) || rows.some(row => !safePackagePath(row)) || new Set(rows).size !== rows.length) throw Error(`Invalid package ${name}`);
  }
  const inputSet=new Set(value.inputs);
  if (!value.inputs.length || !inputSet.has(PACKAGE_INPUT_FILE) || value.optional_inputs.some(row => !inputSet.has(row))) throw Error('Incomplete package input definition');
  for(const row of value.inputs) for(let slash=row.indexOf('/');slash>=0;slash=row.indexOf('/',slash+1)){
    const parent=row.slice(0,slash+1);
    if(parent!==row&&inputSet.has(parent))throw Error('Overlapping package inputs');
  }
  // Ambient databases, secrets and existing build/cache output cannot become source inputs.
  if (value.inputs.some(row => /^(?:\.git(?:\/|$)|node_modules(?:\/|$)|\.cache(?:\/|$)|dist(?:\/|$)|data\/atlas\.sqlite)/.test(row))) throw Error('Ambient/generated package source input');
  const outputs = ['dist/', 'data/prepared-evidence/', '.cache/package-atlas.sqlite'];
  if (value.generated_outputs.some(row => !outputs.includes(row))) throw Error('Unsupported generated package output');
  return value;
}

export function loadPackageInputs(directory = root) {
  const file=path.join(directory,PACKAGE_INPUT_FILE);
  return validatePackageInputs(JSON.parse(fs.readFileSync(file,'utf8')));
}

export async function readPackageInputs({route, base, api, maximumBytes = Infinity}) {
  const blob = await api(`${route}/contents/${PACKAGE_INPUT_FILE}?ref=${base}`);
  if (blob?.type !== 'file' || blob.encoding !== 'base64' || blob.path !== PACKAGE_INPUT_FILE ||
      !/^[a-f0-9]{40}$/.test(blob.sha ?? '') || !Number.isSafeInteger(blob.size) || blob.size <= 0 || blob.size > maximumBytes || typeof blob.content !== 'string') throw Error('Package input definition unavailable');
  const raw = Buffer.from(blob.content, 'base64');
  if (raw.length !== blob.size || createHash('sha1').update(`blob ${raw.length}\0`).update(raw).digest('hex') !== blob.sha) throw Error('Package input definition bytes changed');
  return validatePackageInputs(JSON.parse(raw));
}

export function packagePathRequired(file, definition) {
  return containsPackagePath(definition.inputs, file) || containsPackagePath(definition.verification_paths, file);
}

// Prune opaque historical products, not engineering code used by cold-entry
// regression. Retain an entire root if package/verification roles explicitly
// need a member or ancestor. Unlisted siblings remain included.
export function fullCheckoutPatterns(definition) {
  validatePackageInputs(definition);
  const archives = [
    'coordination/engineering/global-source-comparisons-b-package3-20261006/',
    'coordination/engineering/global-source-comparisons-a-20261006/',
    'coordination/engineering/global-source-comparisons-a-001-20261006/',
    'coordination/engineering/global-source-comparisons-b-20261006/',
    'coordination/engineering/reference-source-custody-20261007/',
    'coordination/engineering/complete-numeric-closure-diagnosis-20261007/'
  ];
  const declared = [...definition.inputs, ...definition.verification_paths];
  return ['/*','!/data/regional-review/','!/research/campaigns/', ...archives
    .filter(prefix => !declared.some(name => name.startsWith(prefix) ||
      name.endsWith('/') && prefix.startsWith(name)))
    .map(prefix => '!/' + prefix), ...scopedCheckoutPatterns('research/geography/', declared),
    // Match the allocator's code-only engineering scope, including nested helpers.
    ...['mjs','js','cjs','py','sh'].map(extension => 'coordination/engineering/**/*.' + extension),
    'coordination/engineering/**/package.json'];
}

// One fixture roster serves full and focused regression. Keep
// ordinary code discovery separate from the literal verification operands.
export function focusedCheckoutPatterns(definition, verificationPaths = definition.verification_paths) {
  validatePackageInputs(definition);
  return [
    'scripts', 'src', 'test', '.github', 'drizzle', 'hosted', 'postgres', '/*.mjs',
    'coordination/engineering/**/*.mjs', 'coordination/engineering/**/*.js',
    'coordination/engineering/**/*.cjs', 'coordination/engineering/**/*.py',
    'coordination/engineering/**/package.json',
    'package.json', 'package-lock.json', 'requirements.txt',
    ...verificationPaths.map(name => '/' + name)
  ];
}

function scopedCheckoutPatterns(prefix, paths) {
  if (paths.some(name => name.endsWith('/') && prefix.startsWith(name))) {
    return ['/' + prefix + '**'];
  }
  const retained = paths.filter(name => name.startsWith(prefix)), directories = new Set();
  for (const name of retained) {
    let parent = name.endsWith('/') ? name.slice(0,-1) : name.slice(0,name.lastIndexOf('/'));
    while (parent !== prefix.slice(0,-1)) {
      directories.add(parent + '/'); parent = parent.slice(0,parent.lastIndexOf('/'));
    }
  }
  const patterns = ['!/' + prefix + '*'];
  for (const directory of [...directories].sort((a,b) => a.split('/').length-b.split('/').length || a.localeCompare(b,'en'))) {
    patterns.push('/' + directory);
    if (!retained.some(name => name.endsWith('/') && directory.startsWith(name))) patterns.push('!/' + directory + '*');
  }
  patterns.push(...retained.filter(name => !name.endsWith('/')).map(name => '/' + name));
  return patterns;
}

// Selected-data runs current emitted smoke, not the unit fixture roster. Keep
// every declared build input for either retained assembly or full-build fallback,
// plus current expectations and all coordination execution. Preparation supplies
// the authenticated complete candidate tree; package roles never authorize code.
export function selectedDataCheckoutPatterns(definition, entries, expectationsPath) {
  validatePackageInputs(definition);
  if (!(entries instanceof Map) || !safePackagePath(expectationsPath) ||
      !expectationsPath.endsWith('/selected-delivery-expectations.json') ||
      entries.get(expectationsPath)?.type !== 'blob' || entries.get(expectationsPath)?.mode !== '100644')
    throw Error('Invalid trusted selected expectations');
  const suffix = /\.(?:mjs|js|cjs|py|sh|ts|tsx|jsx|html|css|sql|yml|yaml|c|h|cpp|hpp|wasm|bat|cmd|ps1)$/i;
  const execution = [];
  for (const [name, row] of entries) {
    if (!name.startsWith('coordination/engineering/') ||
        !(row.mode === '100755' || suffix.test(name) || name.endsWith('/package.json'))) continue;
    if (!safePackagePath(name) || row.type !== 'blob' || !['100644','100755'].includes(row.mode))
      throw Error('Nonordinary coordination execution input');
    execution.push(name);
  }
  const patterns = ['/*','!/data/regional-review/','!/research/campaigns/'];
  for (const prefix of ['research/geography/','coordination/engineering/','data/']) {
    const paths = [...definition.inputs, expectationsPath,
      ...(prefix === 'coordination/engineering/' ? execution : [])];
    patterns.push(...scopedCheckoutPatterns(prefix, paths));
  }
  return patterns;
}

// Original producer -> current selection, independently of PR-base -> head
// classification. New directory members and implicit optional inputs are never
// waved through by an append-only package-definition change. Scientific readers
// authenticate their own consumed inputs; a parent-only read inventory is not
// the union of those readers and cannot gate inert declarations.
// Preliminary discovery/execution admission cannot publish anything. A retained
// non-data leaf must also be reached by the existing private selected reader
// before its publication token or final output transition is issued.
export const PACKAGE_PRODUCER_KIND = 'immediate-cloudflare-build-v1';
export const inertSelectedPackageInput = name => typeof name === 'string' &&
  /^coordination\/engineering\/[^/]+\/.+\.(?:json|jsonl\.gz|json\.gz|log)$/.test(name);
// The selector authenticates the sidecar body. Only its four cumulative roles
// may be retired; this is the same contract used by finalization and reuse.
export function selectedCumulativePackageRoles(selection, raw) {
  const fail = () => { throw Error('Complete authenticated prior cumulative package roles required'); };
  const hook = selection?.additive_release;
  if (!hook || !safePackagePath(hook.path) || hook.path.endsWith('/') || !Buffer.isBuffer(raw) ||
      raw.length !== hook.bytes || createHash('sha256').update(raw).digest('hex') !== hook.sha256) fail();
  const sidecar = JSON.parse(raw);
  if (sidecar.version !== 2 || sidecar.kind !== 'retained-native-additive-selection-v2') fail();
  const pins = [sidecar.runtime_envelope, sidecar.logical_asset_map?.ledger, sidecar.logical_asset_map?.patch];
  if (!pins.every(pin => pin && safePackagePath(pin.path) && !pin.path.endsWith('/') && pin.mode === '100644' &&
      /^[a-f0-9]{40}$/.test(pin.git_blob_oid ?? pin.blob ?? '') && Number.isSafeInteger(pin.bytes) && pin.bytes > 0 &&
      /^[a-f0-9]{64}$/.test(pin.sha256 ?? ''))) fail();
  return [{...hook, mode: '100644', git_blob_oid: createHash('sha1').update(`blob ${raw.length}\0`).update(raw).digest('hex')}, ...pins];
}
// One definition-level rule for generation, selected-data classification and
// retained package reuse. Callers still authenticate their own complete role
// graphs; this permits no unrelated removal, directory narrowing or policy edit.
export function admitSelectedPackageDeclarations(before, current, {selection, priorSidecarRaw, priorEntry, currentPaths = []} = {}) {
  const need=(ok,message)=>{if(!ok)throw Error(message);};
  const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
  validatePackageInputs(before); validatePackageInputs(current);
  const {inputs:oldInputs,optional_inputs:oldOptional,...oldPolicy}=before,
    {inputs:newInputs,optional_inputs:newOptional,...newPolicy}=current;
  const removed=oldInputs.filter(name=>!newInputs.includes(name));
  need(Array.isArray(currentPaths) && removed.every(name=>!currentPaths.includes(name)),
    'Retired cumulative role remains a current package input');
  const retired=new Map(removed.length ? selectedCumulativePackageRoles(selection,priorSidecarRaw).map(pin=>[pin.path,pin]) : []);
  for (const name of removed) {
    const pin=retired.get(name), row=priorEntry?.(name);
    need(pin, 'Removed package input is not an authenticated prior cumulative role: '+name);
    need(row?.mode==='100644' && (row.oid??row.sha??row.git_blob_oid)===(pin.git_blob_oid??pin.blob)
      // Source capture inventories bind Git OIDs, which include byte length;
      // tree/whole-pin descriptors also carry an independently checked size.
      && ['bytes','size'].every(key=>!Object.hasOwn(row,key)||row[key]===pin.bytes),
      'Retired cumulative role differs from original source inventory: '+name);
  }
  const retainedInputs=oldInputs.filter(name=>!removed.includes(name));
  need(same(oldPolicy,newPolicy)&&same(oldOptional.filter(name=>!removed.includes(name)),newOptional)&&
    same(retainedInputs,newInputs.slice(0,retainedInputs.length)),
    'Package definition is not an append-only selected change or authenticated cumulative replacement');
  return {removed,retired,retainedInputs,additions:newInputs.slice(retainedInputs.length)};
}
// Derive the only mutable prepared-bank inputs from both whole committed indexes.
// Tree metadata admits transport scope; the ordinary copier and emitted full-word
// parity still authenticate every encoded/decoded body against N + accepted repairs.
export const PREPARED_STARTUP_PREFIX = 'data/canonical-grid/current-startup/';
export const PREPARED_STARTUP_INDEX = PREPARED_STARTUP_PREFIX + 'index.json';
export function preparedStartupPackageTransition(before, current, raw = {}) {
  const equal=isDeepStrictEqual,need=(ok,message)=>{if(!ok)throw Error(message);};
  const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
  const git=bytes=>createHash('sha1').update(`blob ${bytes.length}\0`).update(bytes).digest('hex');
  const parse=(source,name,bytes)=>{
    const row=source.files.find(row=>row.path===name);
    need(row?.mode==='100644'&&Buffer.isBuffer(bytes)&&isUtf8(bytes)&&git(bytes)===row.oid,'Prepared transition whole metadata differs: '+name);
    return JSON.parse(bytes);
  };
  const inspect=(source,indexRaw,selectionRaw)=>{
    const index=parse(source,PREPARED_STARTUP_INDEX,indexRaw),selection=parse(source,'data/ownership-selection.json',selectionRaw);
    const proof=index.preparedOwnership;
    const final=index.version===3,selectedNative=scientificNativeSelection(selection);
    need(equal(selection,source.selection)&&selectedNative.method==='native-linear-evenodd-first-owner-v1'
      &&(final?proof?.version===3: index.version===2&&proof?.version===2&&proof.selection_sha256===sha(selectionRaw))
      &&index.native_manifest_sha256===selectedNative.sha256&&proof.native_manifest_sha256===selectedNative.sha256
      &&proof.native_pixel_map?.canonical_grid_sha256===selectedNative.sha256,'Prepared transition selector/native binding differs');
    if(final){const pin=finalBankSelection(selection);need(pin.path===PREPARED_STARTUP_INDEX&&pin.bytes===indexRaw.length&&pin.sha256===sha(indexRaw)
      &&index.additiveRelease===undefined&&equal(proof.effective_reference,selection.reference),'Prepared final transition index binding differs');}
    else need(equal(proof.base_reference,index.additiveRelease?.base_reference)
      &&equal(proof.effective_reference,index.additiveRelease?.effective_reference),'Prepared legacy transition content binding differs');
    need(index.release_id===proof.effective_reference?.id&&index.footprints_sha256===proof.effective_reference?.footprints_sha256
      &&index.hierarchy_sha256===proof.effective_reference?.hierarchy_sha256,'Prepared transition content/effective binding differs');
    need(Array.isArray(index.files)&&index.files.length>0&&new Set(index.files.map(pin=>pin.path)).size===index.files.length
      &&Array.isArray(index.compatibility_files)&&index.compatibility_files.length>0
      &&new Set(index.compatibility_files.map(pin=>pin.path)).size===index.compatibility_files.length,'Prepared transition inventory differs');
    const pins=new Map(index.files.map(pin=>[pin.path,pin])),entries=new Map(source.files.map(row=>[row.path,row]));
    for(const pin of index.files){
      need(safePackagePath(pin.path)&&!pin.path.endsWith('/')&&pin.path!=='index.json'&&Number.isSafeInteger(pin.bytes)&&pin.bytes>0
        &&/^[a-f0-9]{64}$/.test(pin.sha256),'Invalid prepared transition pin');
      const row=entries.get(PREPARED_STARTUP_PREFIX+pin.path);
      need(row?.mode==='100644'&&/^[a-f0-9]{40}$/.test(row.oid)
        &&(row.bytes===undefined||row.bytes===pin.bytes),'Prepared transition tree member differs');
    }
    const active=[...(index.pixelMap?.parts??[]),...(proof.context_parts??[])],native=proof.native_pixel_map;
    need(active.length>0&&Array.isArray(native.parts)&&native.parts.length>0,'Prepared transition active operands missing');
    const names=new Set();
    for(const pin of [...index.compatibility_files,...native.parts,...active]){
      need(pins.get(pin.path)?.sha256===pin.sha256,'Prepared transition operand differs');names.add(pin.path);
    }
    const latitude=native.native_latitudes;
    need(pins.get(latitude?.transport_path)?.sha256===latitude?.sha256,'Prepared transition native latitude differs');names.add(latitude.transport_path);
    need(index.compatibility_files.every(pin=>equal(pin,pins.get(pin.path)))&&names.size===pins.size
      &&[...pins.keys()].every(name=>names.has(name)),'Prepared transition retains an inactive or unbound member');
    const actual=source.files.filter(row=>row.path.startsWith(PREPARED_STARTUP_PREFIX)).map(row=>row.path).sort();
    need(equal(actual,[PREPARED_STARTUP_INDEX,...index.files.map(pin=>PREPARED_STARTUP_PREFIX+pin.path)].sort()),'Prepared transition actual inventory differs');
    return {index,pins,entries,active:new Set(active.map(pin=>pin.path))};
  };
  const old=inspect(before,raw.beforeIndex,raw.beforeSelection),next=inspect(current,raw.afterIndex,raw.afterSelection);
  need(equal(old.index.compatibility_files,next.index.compatibility_files)
    &&equal(old.index.preparedOwnership.native_pixel_map,next.index.preparedOwnership.native_pixel_map)
    &&equal(old.index.preparedOwnership.base_reference,next.index.preparedOwnership.base_reference),
  'Prepared transition changes compatibility, original native or content reference');
  const added=new Set(),removed=new Set();
  for(const [name,pin] of old.pins){
    if(next.pins.has(name))need(equal(pin,next.pins.get(name))
      &&equal(old.entries.get(PREPARED_STARTUP_PREFIX+name),next.entries.get(PREPARED_STARTUP_PREFIX+name)), 'Prepared immutable URL rebound');
    else{need(old.active.has(name)&&!old.index.compatibility_files.some(pin=>pin.path===name), 'Prepared compatibility member removed');removed.add(PREPARED_STARTUP_PREFIX+name);}
  }
  for(const name of next.pins.keys())if(!old.pins.has(name)){
    need(next.active.has(name),'Unbound prepared addition');added.add(PREPARED_STARTUP_PREFIX+name);
  }
  return {added,removed,changed:new Set([PREPARED_STARTUP_INDEX,...added,...removed])};
}

export function admitPackageInputTransition(before, current, {acceptedInputs, typedInputs, priorSidecarRaw, producerWorkflows, preparedStartup, preliminary = false} = {}) {
  const need=(ok,message)=>{if(!ok)throw Error(message);};
  const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
  const commit=value=>/^[a-f0-9]{40}$/.test(value??'');
  validatePackageInputs(before.definition); validatePackageInputs(current.definition);
  compatiblePackageProducers(before.producer,current.producer,producerWorkflows);
  const oldInventory=new Map(before.files.map(row=>[row.path,row]));
  const {removed,retired,retainedInputs,additions:newDeclarations}=admitSelectedPackageDeclarations(
    before.definition,current.definition,{selection:before.selection,priorSidecarRaw,priorEntry:name=>oldInventory.get(name),currentPaths:current.files.map(row=>row.path)});
  const {additive_release:oldAdditive,...oldBase}=before.selection;
  const {additive_release:newAdditive,...newBase}=current.selection;
  if(before.selection.version===2||current.selection.version===2){
    need(before.selection.version===2&&current.selection.version===2,'First final-profile adoption requires a genuine full capture');
    finalBankSelection(before.selection);finalBankSelection(current.selection);
    need(isDeepStrictEqual(scientificNativeSelection(before.selection),scientificNativeSelection(current.selection))
      &&isDeepStrictEqual(before.selection.reference_projection,current.selection.reference_projection),'Original final-profile native/reference selection differs');
  }else need(same(oldBase,newBase)&&oldAdditive&&newAdditive,'Original invariant selection differs');
  const oldFiles=new Map(before.files.map(row=>[row.path,row])),newFiles=new Map(current.files.map(row=>[row.path,row]));
  need(oldFiles.size===before.files.length&&oldFiles.size>0&&newFiles.size===current.files.length,'Duplicate or incomplete source input inventory');
  const bank=preparedStartup?preparedStartupPackageTransition(before,current,preparedStartup):{changed:new Set(),added:new Set(),removed:new Set()};
  const exceptions=new Set(['.github/package-inputs.json','data/ownership-selection.json',...bank.changed]);
  for(const [name,row] of oldFiles) {
    if(bank.removed.has(name)) { need(!newFiles.has(name),'Retired final-bank input remains'); }
    else if(removed.includes(name)) {
      need(row.mode==='100644'&&row.oid===(retired.get(name).git_blob_oid??retired.get(name).blob),
        'Retired cumulative role differs from original source inventory: '+name);
      need(!newFiles.has(name),'Retired declaration remains an implicit package input: '+name);
    } else need(newFiles.has(name)&&(exceptions.has(name)||same(row,newFiles.get(name))),
      'Original invariant package input changed: '+name);
  }
  const accepted=new Map(),retained=[];
  if(acceptedInputs!==undefined){
    need(commit(acceptedInputs?.commit)&&Array.isArray(acceptedInputs.files),'Exact trusted selected base required');
    for(const row of acceptedInputs.files){
      need(safePackagePath(row.path)&&!row.path.endsWith('/')&&row.mode==='100644'&&commit(row.oid)&&
        Number.isSafeInteger(row.bytes)&&row.bytes>=0&&!accepted.has(row.path),
        'Invalid accepted selected input descriptor');
      accepted.set(row.path,row);
    }
  }
  for(const name of newDeclarations){
    const row=newFiles.get(name);
    need(safePackagePath(name)&&!name.endsWith('/'),'New package declaration is not an explicit selected input file');
    need(row,'New selected declaration is absent');
    need(row.mode==='100644'&&commit(row.oid),'Ordinary explicit selected input required');
    if(inertSelectedPackageInput(name))continue;
    const original=accepted.get(name);
    need(original&&original.mode===row.mode&&original.oid===row.oid,
      'Selected code/source input is not unchanged on trusted base: '+name);
    retained.push(original);
    if(!preliminary)need(Array.isArray(typedInputs)&&typedInputs.some(pin=>pin.path===name&&pin.mode===row.mode&&
      pin.git_blob_oid===row.oid&&pin.bytes===original.bytes&&commit(pin.commit)),
      'Selected code/source input lacks authenticated typed consumption: '+name);
  }
  const added=[];
  for(const [name,row] of newFiles)if(!oldFiles.has(name)){
    need(row.mode==='100644'&&(newDeclarations.includes(name)||bank.added.has(name)),
      'Unadmitted new invariant/directory/optional package input: '+name);added.push(name);
  }
  return {original_head:before.head,current_head:current.head,invariant_files:oldFiles.size-exceptions.size-removed.length,
    removed_selected_inputs:removed,
    added_selected_inputs:added.sort(),base_selection:oldBase,
    ...(retained.length?{accepted_selected_inputs:{commit:acceptedInputs.commit,files:retained}}:{})};
}
