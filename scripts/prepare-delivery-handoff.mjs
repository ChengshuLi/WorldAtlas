// Metadata preparation and explicit body acquisition. Existing
// operators, source authority and independent review remain authoritative.
import fs from 'node:fs';
import os from 'node:os';
import {writeNativeByteChunks} from './native-patch-store.mjs';
import {performance} from 'node:perf_hooks';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {gunzipSync} from 'node:zlib';
import {locate, deliveryAcquisitionExecute} from './delivery-handoff-advance.mjs';
import {createAcquisition, githubTree, githubCommit} from './geography-prefetch.mjs';
import {acquireFinalizationCheckpoint, finalizationCheckpointBytes, admitCanonicalCheckpoint} from './delivery-checkpoint-finalization.mjs';
import {releaseAcceptedCheckpoint} from './accepted-selected-checkpoint.mjs';
import {repairComponentKey, compareRepairComponents} from '../src/native-grid.js';
import {scientificNativeSelection,originalNativeReference,validateReferenceMetadataHeader} from '../src/reference-metadata.js';
import {prepareReferenceMetadataProjection,validateReferenceMetadataProjection} from './selected-reference-metadata.mjs';
import {validatePackageInputs, selectedCumulativePackageRoles, admitSelectedPackageDeclarations} from './package-inputs.mjs';
import {composeRetainedLedgers} from '../coordination/engineering/additive-native-gap-batch-20261008/composition-v2/compose-retained.mjs';
import {coordinateBounds, normaliseRetainedRepairLedger, compareVersionedRepairLedgers, verifyCompletedSourceTargetNativeAuthority, mergeCompletedNativePatches, verifyCurrentRebindExecution, CURRENT_REBIND_CODE} from '../coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';

const need = (ok, message) => { if (!ok) throw Error(message); };
const hex = (value, size) => typeof value === 'string' && new RegExp(`^[a-f0-9]{${size}}$`).test(value);
const canonical = value => Array.isArray(value) ? value.map(canonical) : value && typeof value === 'object'
  ? Object.fromEntries(Object.keys(value).sort().map(key => [key, canonical(value[key])])) : value;
export const jsonBytes = value => Buffer.from(JSON.stringify(canonical(value)) + '\n');
export const digest = raw => createHash('sha256').update(raw).digest('hex');
const same = (a, b) => jsonBytes(a).equals(jsonBytes(b));
const safe = name => typeof name === 'string' && /^[a-zA-Z0-9_./-]+$/.test(name) && !path.isAbsolute(name)
  && name.split('/').every(part => part && part !== '.' && part !== '..');
const unique = values => Array.isArray(values) && values.length > 0 && values.every(v => typeof v === 'string' && v) && new Set(values).size === values.length;
const environment = () => ({...process.env, GIT_NO_LAZY_FETCH: '1', GIT_NO_REPLACE_OBJECTS: '1', GIT_CONFIG_NOSYSTEM: '1', GIT_CONFIG_GLOBAL: '/dev/null', GIT_TERMINAL_PROMPT: '0'});

export function pinReader(root, {loadTree = githubTree, loadCommit = githubCommit,
  execute = deliveryAcquisitionExecute()} = {}) {
  const cache = new Map(), descriptors = new Map(), declared = new Map();
  let acquisition;
  async function acquire(pins) {
    need(Array.isArray(pins), 'Explicit composition input pins required');
    for (const pin of pins) {
      need(pin && hex(pin.commit, 40) && safe(pin.path) && (pin.mode ?? '100644') === '100644'
        && Number.isSafeInteger(pin.bytes) && pin.bytes >= 0 && hex(pin.sha256, 64),
      'Complete ordinary composition input pin required');
      const key = pin.commit + ':' + pin.path, old = declared.get(key);
      need(!old || old.bytes === pin.bytes && old.sha256 === pin.sha256,
        'Conflicting composition input identities');
      declared.set(key, pin);
    }
    acquisition ??= createAcquisition({repo: root, execute, token: '', loadTree, loadCommit,
      loadDescriptor: async (commit, name) => {
        const pin = declared.get(commit + ':' + name);
        need(pin, 'Undeclared composition input');
        const actual = await acquisition.resolvePath(commit, name);
        need(actual.mode === '100644', 'Nonordinary composition input');
        return {type: 'blob', mode: actual.mode, sha: actual.git_blob_oid, size: pin.bytes};
      }});
    const rows = [];
    for (const pin of pins) rows.push(await acquisition.descriptor(pin.commit, pin.path,
      {...pin, git_blob_oid: pin.git_blob_oid ?? pin.blob}));
    acquisition.acquire(rows);
    for (let index = 0; index < pins.length; index++) {
      const pin = pins[index], row = rows[index];
      const raw = cache.get(row.oid) ?? git('cat-file', 'blob', row.oid);
      need(raw.length === row.bytes && digest(raw) === pin.sha256
        && createHash('sha1').update(`blob ${raw.length}\0`).update(raw).digest('hex') === row.oid,
      'Whole composition body hash differs');
      cache.set(row.oid, raw);
      // The existing origin resolver authenticated the exact native commit and
      // path trees. Keep that proof private; do not import a partial history.
      descriptors.set(pin.commit + ':' + pin.path, {path: pin.path, commit: pin.commit,
        mode: '100644', git_blob_oid: row.oid, bytes: row.bytes});
    }
    return {...acquisition.stats};
  }
  const git = (...args) => {
    const options={cwd:root,env:environment(),maxBuffer:Infinity};
    if(args[0]==='cat-file'&&args[1]==='blob') options.maxBuffer=Number(git('cat-file','-s',args[2]))+1;
    return execFileSync('git',args,options);
  };
  function descriptor(commit, name) {
    need(hex(commit, 40) && safe(name), 'Exact commit and safe whole-file path required');
    const key = commit + ':' + name;
    // Exact commit/path metadata is immutable; never expose the saved descriptor.
    if (descriptors.has(key)) return {...descriptors.get(key)};
    const line = git('ls-tree', '-z', commit, '--', name).toString();
    const match = /^100644 blob ([a-f0-9]{40})\t([^\0]+)\0$/.exec(line);
    need(match && match[2] === name, 'Missing ordinary exact Git body: ' + name);
    const size = Number(git('cat-file', '-s', match[1]).toString());
    need(Number.isSafeInteger(size) && size >= 0, 'Invalid whole body size: ' + name);
    const pin = {path: name, commit, mode: '100644', git_blob_oid: match[1], bytes: size};
    descriptors.set(key, pin);
    return {...pin};
  }
  function read(pin) {
    const actual = descriptor(pin.commit, pin.path);
    need(pin.mode === actual.mode && (pin.git_blob_oid ?? pin.blob) === actual.git_blob_oid
      && pin.bytes === actual.bytes && hex(pin.sha256, 64), 'Whole pin identity differs: ' + pin.path);
    if (!cache.has(actual.git_blob_oid)) {
      const raw = git('cat-file', 'blob', actual.git_blob_oid);
      need(raw.length === actual.bytes, 'Whole body length changed');
      cache.set(actual.git_blob_oid, raw);
    }
    const raw = cache.get(actual.git_blob_oid);
    need(digest(raw) === pin.sha256, 'Whole body hash differs: ' + pin.path);
    return raw;
  }
  return {git, read, descriptor, acquire, json: pin => JSON.parse(read(pin)),
    hasPath(commit, name) {
      need(hex(commit, 40) && safe(name), 'Exact commit and safe whole-file path required');
      return git('ls-tree', '-z', commit, '--', name).length > 0;
    },
    pin(commit, name) { const p = descriptor(commit, name);
      if (!cache.has(p.git_blob_oid)) { cache.set(p.git_blob_oid, git('cat-file', 'blob', p.git_blob_oid)); }
      return {...p, sha256: digest(cache.get(p.git_blob_oid))}; }};
}

function ordinary(root, relative) {
  need(safe(relative), 'Unsafe input path');
  const filename = path.join(root, relative);
  const stat = fs.lstatSync(filename);
  need(stat.isFile() && fs.realpathSync(filename) === filename, 'Require ordinary input: ' + relative);
  return fs.readFileSync(filename);
}

function admitDestination(root, destination, resume) {
  need(safe(destination) && /^(?:\.cache\/delivery-handoff|coordination\/engineering\/[^/]+)\//.test(destination), 'Use a fresh owned preparation destination');
  let current = root;
  for (const part of destination.split('/')) {
    current = path.join(current, part);
    const stat = fs.lstatSync(current, {throwIfNoEntry: false});
    if (stat) need(stat.isDirectory() && fs.realpathSync(current) === current, 'Nonordinary output ancestor or occupied file');
  }
  const target = path.join(root, destination);
  need(resume || !fs.existsSync(target), 'Occupied destination; use explicit --resume to verify an identical completed phase');
  return target;
}

// Required output bytes may live in one invocation-owned file. A plain object
// with a path/hash is never admitted as a staged product.
const stagedProducts=new WeakMap();
export function stageProduct(chunks,{directory=os.tmpdir()}={}) {
 const parent=fs.lstatSync(directory);
 need(parent.isDirectory()&&fs.realpathSync(directory)===directory,'Require ordinary product staging directory');
 const folder=fs.mkdtempSync(path.join(directory,'authority-product-')),file=path.join(folder,'body');
 let fd,closed=false;
 try{
  fd=fs.openSync(file,'wx+',0o600);const identity=writeNativeByteChunks(fd,chunks);
  const close=()=>{if(closed)return;closed=true;let failed=false,failure;try{fs.closeSync(fd);}catch(error){failed=true;failure=error;}
   try{fs.rmSync(folder,{recursive:true});}catch(error){if(!failed){failed=true;failure=error;}}if(failed)throw failure;};
  const product=Object.freeze({file,...identity,close,[Symbol.dispose]:close});
  stagedProducts.set(product,{fd,active:()=>need(!closed,'Staged product is closed')});return product;
 }catch(error){try{if(fd!==undefined)fs.closeSync(fd);}catch{}try{fs.rmSync(folder,{recursive:true});}catch{}throw error;}
}
function visitProduct(raw,consume=()=>{}) {
 if(Buffer.isBuffer(raw)){consume(raw);return {bytes:raw.length,sha256:digest(raw)};}
 const source=stagedProducts.get(raw);need(source,'Require owned staged product');source.active();
 const stat=fs.fstatSync(source.fd);need(stat.isFile()&&stat.size===raw.bytes,'Staged product size changed');
 const buffer=Buffer.allocUnsafe(65536),hash=createHash('sha256');let bytes=0;
 while(bytes<stat.size){const count=fs.readSync(source.fd,buffer,0,Math.min(buffer.length,stat.size-bytes),bytes);
  need(count>0,'Truncated staged product');const chunk=buffer.subarray(0,count);hash.update(chunk);consume(chunk);bytes+=count;}
 const sha256=hash.digest('hex');need(sha256===raw.sha256,'Staged product bytes changed');return {bytes,sha256};
}
function productEqualsFile(root,relative,product) {
 if(Buffer.isBuffer(product))return ordinary(root,relative).equals(product);
 need(safe(relative),'Unsafe input path');const filename=path.join(root,relative),stat=fs.lstatSync(filename);
 need(stat.isFile()&&fs.realpathSync(filename)===filename,'Require ordinary input: '+relative);
 if(stat.size!==product.bytes)return false;
 const fd=fs.openSync(filename,'r'),buffer=Buffer.allocUnsafe(65536);let position=0,equal=true,failed=false;
 try{visitProduct(product,chunk=>{let used=0;while(used<chunk.length){const n=fs.readSync(fd,buffer,used,chunk.length-used,position+used);if(!n){equal=false;break;}used+=n;}
  if(used!==chunk.length||!chunk.equals(buffer.subarray(0,used)))equal=false;position+=used;});return equal;}
 catch(error){failed=true;throw error;}
 finally{try{fs.closeSync(fd);}catch(error){if(!failed)throw error;}}
}
function writeProduct(filename,raw) {
 if(Buffer.isBuffer(raw)){fs.writeFileSync(filename,raw,{flag:'wx'});return;}
 const fd=fs.openSync(filename,'wx',0o600);let position=0,failed=false;
 try{visitProduct(raw,chunk=>{let at=0;while(at<chunk.length){const n=fs.writeSync(fd,chunk,at,chunk.length-at,position+at);need(n>0,'Incomplete product publication');at+=n;}position+=chunk.length;});}
 catch(error){failed=true;throw error;}
 finally{try{fs.closeSync(fd);}catch(error){if(!failed)throw error;}}
}

// Equivalent to the shared new-vintage writer for this JS metadata adapter:
// validate whole destination before mutation, exclusive creation, receipt last.
// Resume means checking every immutable byte; partial output is never repaired.
export function admitPublication(root, destination, products, binding, resume = false) {
  const target = admitDestination(root, destination, resume);
  for (const [name, raw] of Object.entries(products)) {
    need(safe(name) && !name.includes('/') && name !== 'preparation.json' && (Buffer.isBuffer(raw)||stagedProducts.has(raw)),
      'Safe flat product filenames required');
  }
  need(Object.keys(products).length > 0, 'No empty completion');
  const outputs = Object.fromEntries(Object.entries(products).map(([name, raw]) => [name, visitProduct(raw)]));
  const receipt = jsonBytes({version: 1, binding, outputs});
  const inspectExisting = () => {
    admitDestination(root, destination, resume);
    if (!fs.existsSync(target)) return false;
    const expected = [...Object.keys(products), 'preparation.json'].sort();
    const found = fs.readdirSync(target).sort();
    need(same(found, expected), 'Incomplete or foreign resumed output inventory');
    for (const [name, raw] of Object.entries({...products, 'preparation.json': receipt}))
      need(productEqualsFile(root, destination + '/' + name,raw), 'Resumed bytes/binding changed: ' + name);
    return true;
  };
  inspectExisting();
  // A caller may do admitted acquisition between preflight and publication.
  // Recheck the destination after that boundary; never adopt a new collision.
  return () => {
    need(same(Object.keys(products).sort(), Object.keys(outputs).sort())
      && Object.entries(products).every(([name, raw]) => same(visitProduct(raw),outputs[name])),
      'Admitted products changed before publication');
    if (inspectExisting()) return {destination, resumed: true, binding};
    fs.mkdirSync(path.dirname(target), {recursive: true});
    fs.mkdirSync(target);
    for (const [name, raw] of Object.entries(products))
      writeProduct(path.join(target,name),raw);
    fs.writeFileSync(path.join(target, 'preparation.json'), receipt, {flag: 'wx'});
    return {destination, resumed: false, binding};
  };
}

export function publish(root, destination, products, binding, resume = false) {
  return admitPublication(root, destination, products, binding, resume)();
}

// CLI-owned staged products remain live through publication and are all joined.
// Public publish retains its existing borrowed-product/Buffer contract.
function closeOwnedProducts(products) {
 let failed=false,failure;
 for(const product of Object.values(products??{}))if(stagedProducts.has(product))try{product.close();}
 catch(error){if(!failed){failed=true;failure=error;}}
 if(failed)throw failure;
}
export function publishOwnedProducts(root,destination,products,binding,resume=false) {
 let failed=false;
 try{return publish(root,destination,products,binding,resume);}
 catch(error){failed=true;throw error;}
 finally{try{closeOwnedProducts(products);}catch(error){if(!failed)throw error;}}
}

export function requestProfile(template, group, config, reader) {
  if (config.compatibility === 'literal-historical-v1') {
    need(template.operating_profile === undefined && !group.requested_resources && !config.requested_resources,
      'Historical compatibility preserves literal v1 resource/runtime fields only');
    return template;
  }
  need(config.compatibility === undefined && template.operating_profile === 'source-native-v2',
    'New issuance requires an admitted source-native-v2 template; historical v1 must be explicit compatibility');
  const support = template.operating_runtime?.support_code;
  need(same(support?.map(p => p.path), ['scripts/local-workspace.mjs', 'scripts/worker-identity.mjs']), 'Complete ordered v2 support-code pins required');
  const head = reader.git('rev-parse', 'HEAD').toString().trim();
  need(Array.isArray(template.executed_code) && template.executed_code.length && template.operating_runtime.supervisor, 'Current v2 code/runtime template required');
  for (const pin of [...template.executed_code, template.operating_runtime.supervisor, ...support]) {
    const actual = reader.pin(head, pin.path);
    need(pin.bytes === actual.bytes && pin.sha256 === actual.sha256, 'New v2 template code differs from actual HEAD: ' + pin.path);
  }
  const {processing_allowance,operating_limits,output_reserve,...request}=template;
  return request;
}

export function prepareRequests(config, reader) {
  const registry = reader.json(config.registry), outputs = {}, index = [], seen = new Set();
  need(registry.version === 1 && registry.kind === 'accepted-administrative-handoffs-v1', 'Existing accepted handoff registry required');
  need(Array.isArray(config.groups) && config.groups.length, 'Explicit finite method/resource groups required');
  for (const group of config.groups) {
    need(/^[a-z0-9-]+$/.test(group.id) && !seen.has(group.id) && unique(group.component_ids), 'Invalid/duplicate request group');
    seen.add(group.id);
    const template = requestProfile(reader.json(group.template), group, config, reader), rule = template.source_rule;
    need(template.operation === 'retained-land-source-premises-v1' && rule?.profile === 'retained-consumed-administrative-source', 'Use an existing admitted SOURCE request template');
    const entries = registry.entries.filter(entry => entry.id === group.handoff_id);
    need(entries.length === 1, 'Unknown/ambiguous accepted whole handoff');
    const entry = entries[0], pin = {...entry.source, commit: entry.accepted_source_commit};
    const handoff = reader.json(pin), roster = handoff.candidate_source_native_bindings;
    need(unique(entry.cohort_ids) && same(handoff.scopeIds, entry.cohort_ids)
      && same(roster?.map(row => row.component_id), entry.cohort_ids), 'Accepted whole handoff order/coverage changed');
    need(same([...new Set(roster.map(row => row.retained_payload?.target_stable_location_id))].sort(), [...entry.target_ids].sort()), 'Accepted handoff target join changed');
    const ordered = entry.cohort_ids.filter(id => group.component_ids.includes(id));
    need(ordered.length === group.component_ids.length, 'Group contains unknown/duplicate component');
    const pinnedHandoff = rule.inputs.filter(p => p.path === rule.cases_path);
    need(pinnedHandoff.length === 1 && same(pinnedHandoff[0], pin) && same(rule.cohort_ids, entry.cohort_ids)
      && rule.outcomes_path === pin.path && rule.registry_path === config.registry.path, 'Template is not bound to this accepted whole handoff');
    // Keep actual template method/product/resource boundaries. No automatic
    // arbitrary chunking, inferred resource limits or expanded science scope.
    need(ordered.every(id => rule.expected_ids.includes(id)) && unique(rule.expected_ids), 'Group exceeds its existing method/resource template scope');
    need(safe(group.destination) && group.destination.startsWith('.cache/native-grid-candidates/'), 'Fresh operator candidate destination required');
    const request = {...template, destination: group.destination, source_rule: {...rule, expected_ids: ordered}};
    const name = group.id + '-source-request.json'; outputs[name] = jsonBytes(request);
    index.push({id: group.id, handoff: pin, component_ids: ordered, template: group.template, request: name,
      method_resource_sha256: digest(jsonBytes({profile: rule.profile, geometry_scope: rule.geometry_scope,
        administrative_products: rule.administrative_products, target_banks: rule.target_banks,
        operating_runtime: template.operating_runtime})),
      next: 'Commit the request, run the existing supervisor separately, then retain real terminal products.'});
  }
  const scopes = index.flatMap(row => row.component_ids);
  need(new Set(scopes).size === scopes.length, 'Overlapping phase component scopes');
  need(unique(config.component_ids) && same([...scopes].sort(), [...config.component_ids].sort()), 'Groups do not exactly cover requested delivery scope');
  outputs['requests.json'] = jsonBytes({version: 1, groups: index, limits: ['Preparation is not source acceptance or execution. Existing operators revalidate current inputs, code and resources.']});
  return outputs;
}

function qualifyTerminal(terminal, requestRaw, publicationRaw, request) {
  const native = Object.hasOwn(terminal, 'qualified');
  need(native ? terminal.qualified === true && terminal.exit?.code === 0 && terminal.exit.signal === null && terminal.refusal === null
    : terminal.exit_code === 0 && terminal.signal === null && terminal.guard_reason === null, 'No genuine successful terminal');
  need(Array.isArray(terminal.owned_processes_remaining) && !terminal.owned_processes_remaining.length
    && Array.isArray(terminal.termination_events) && !terminal.termination_events.length, 'Terminal process cleanup incomplete');
  need(hex(terminal.execution_commit, 40) && terminal.request_sha256 === digest(requestRaw), 'Terminal request/execution binding differs');
  if (request.execution_commit !== undefined) need(terminal.execution_commit === request.execution_commit, 'Terminal execution commit differs');
  if (native) need(terminal.destination === request.destination, 'Terminal destination differs');
  else need(terminal.publication_sha256 === digest(publicationRaw), 'Terminal publication binding differs');
}

function readInventory(raw, descriptor) {
  need(Number.isSafeInteger(descriptor.uncompressed_bytes) && descriptor.uncompressed_bytes > 0,
    'Nonempty decoded inventory identity required');
  const decoded = gunzipSync(raw, {maxOutputLength: descriptor.uncompressed_bytes});
  need(decoded.length === descriptor.uncompressed_bytes && digest(decoded) === descriptor.uncompressed_sha256, 'Actual decoded inventory differs');
  const lines = decoded.toString('utf8').split('\n'); need(lines.pop() === '' && lines.length && lines.every(Boolean), 'Incomplete/empty inventory JSONL');
  const rows = lines.map(line => JSON.parse(line)); need(unique(rows.map(row => row.component_id)), 'Duplicate/missing inventory identity'); return rows;
}

function sourceNativeJoin(request, facts, publication, inventoryRaw, reader, products = null) {
  const source = request.operation === 'retained-land-source-premises-v1';
  need(source || request.operation === 'unactivated-additive-native-batch-v1', 'Unsupported retained operator contract');
  const ids = source ? request.source_rule.expected_ids : request.additive.scope_ids;
  const rows = readInventory(inventoryRaw, publication.inventory);
  need(unique(ids) && same(rows.map(row => row.component_id), ids) && facts.components === ids.length,
    'Inventory does not match complete issued scope/order/count');
  need(same(facts.executed_code, request.executed_code) && same(facts.installed_modules, request.installed_modules)
    && same(facts.baseline, request.baseline) && same(facts.parent, request.parent), 'Published facts changed issued code/runtime/baseline/parent');
  const stage = source ? request.source_rule : request.additive;
  need(same(facts.input_descriptors, [request.report, ...stage.inputs, ...request.baseline.pins]), 'Published facts changed complete issued input closure');
  if (source) {
    need(same(facts.source_rule, stage) && facts.source_compatible === rows.filter(row => row.source_compatible === true).length
      && facts.assigned_cells === 0, 'SOURCE facts/scope/compatibility counts differ from actual rows');
    const pins = stage.inputs.filter(p => p.path === stage.cases_path); need(pins.length === 1, 'Complete SOURCE handoff pin required');
    const handoff = reader.json(pins[0]), cases = handoff.candidate_source_native_bindings;
    need(same(handoff.scopeIds, stage.cohort_ids) && same(cases?.map(row => row.component_id), stage.cohort_ids), 'SOURCE whole handoff scope changed');
    const reference = new Map(cases.map(row => [row.component_id, row.retained_payload?.target_stable_location_id]));
    need(rows.every(row => row.target_id === reference.get(row.component_id)), 'SOURCE inventory target differs from accepted handoff');
    for (const row of rows) {
      const ordinal = cases.findIndex(record => record.component_id === row.component_id);
      need(row.source_case?.ordinal === ordinal && row.source_case.row_sha256 === digest(jsonBytes(cases[ordinal]))
        && same(row.source_case.source, pins[0]), 'SOURCE inventory source-case identity differs from whole handoff');
    }
    need(!publication.assets?.length, 'SOURCE publication has foreign native assets');
  } else {
    need(same(facts.source_predecessor, stage), 'Native facts changed source predecessor');
    const sourcePins = stage.inputs.filter(p => p.path === stage.source_request_path);
    need(sourcePins.length === 1, 'Native output needs the immutable issued SOURCE request');
    const issuedSource = reader.json(sourcePins[0]), sourceRule = issuedSource.source_rule;
    need(issuedSource.operation === 'retained-land-source-premises-v1' && same(sourceRule?.expected_ids, ids), 'Native scope differs from immutable SOURCE scope');
    const handoffPins = sourceRule.inputs.filter(p => p.path === sourceRule.cases_path);
    need(handoffPins.length === 1, 'Native output needs the complete original SOURCE handoff');
    const handoff = reader.json(handoffPins[0]), sourceCases = handoff.candidate_source_native_bindings;
    need(same(handoff.scopeIds, sourceRule.cohort_ids) && same(sourceCases?.map(row => row.component_id), sourceRule.cohort_ids), 'Native original SOURCE handoff scope changed');
    const targets = new Map(sourceCases.map(row => [row.component_id, row.retained_payload?.target_stable_location_id]));
    need(rows.every(row => !['assigned', 'zero-cell'].includes(row.disposition) || row.target_id === targets.get(row.component_id)),
      'Native effective target differs from immutable SOURCE handoff');
    need(rows.every(row => Number.isSafeInteger(row.native_cells) && row.native_cells >= 0), 'Native inventory has invalid measured cell count');
    const cells = rows.reduce((sum, row) => sum + row.native_cells, 0);
    need(Number.isSafeInteger(cells) && facts.assigned_cells === cells, 'Native facts assigned count differs from actual inventory');
    const expected = ['base-native-manifest.json', 'ledger-batch.json', 'patch-batch.json', 'features.json', 'owners-batch.json.gz',
      'release-envelope.json', 'owner-window.json', 'virtual-owner-window.json'].sort();
    need(same(publication.assets?.map(p => p.path).sort(), expected), 'Incomplete fixed native publication asset roster');
    if (products) {
      const ledger = JSON.parse(products['ledger-batch.json']), patch = JSON.parse(products['patch-batch.json']), envelope = JSON.parse(products['release-envelope.json']);
      need(same(ledger.scope_ids, ids) && same(ledger.rows?.map(row => row.component_id), ids), 'Native ledger omitted/reordered issued scope');
      for (let i = 0; i < rows.length; i++) {
        const actual = ledger.rows[i], record = rows[i];
        need(actual.disposition === record.disposition && actual.native_cells === record.native_cells
          && (!['assigned', 'zero-cell'].includes(actual.disposition) || actual.target_id === record.target_id), 'Native ledger/actual inventory differs');
      }
      need(ledger.assigned_cells === cells, 'Native ledger assigned count differs from actual inventory');
      const ledgerHash = digest(products['ledger-batch.json']);
      need(patch.ledger_sha256 === ledgerHash, 'Native patch is not bound to actual ledger');
      const owners = new Set(ledger.rows.filter(row => ['assigned', 'zero-cell'].includes(row.disposition)).map(row => row.pixelIndex));
      need(Array.isArray(patch.rows) && patch.rows.every(row => Array.isArray(row.runs) && row.runs.every(run =>
        Array.isArray(run) && run.length === 3 && run.every(Number.isSafeInteger) && run[0] >= 0 && run[1] > run[0] && owners.has(run[2]))),
      'Native patch owner/run differs from effective ledger');
      need(patch.rows.reduce((sum, row) => sum + row.runs.reduce((n, run) => n + run[1] - run[0], 0), 0) === cells,
        'Native patch measured cells differ from inventory/ledger');
      for (const [role, name] of Object.entries({base_manifest: 'base-native-manifest.json', ledger: 'ledger-batch.json', patch: 'patch-batch.json', owner_roster: 'owners-batch.json.gz'})) {
        const descriptor = envelope.additiveRelease?.[role];
        need(descriptor?.bytes === products[name].length && descriptor.sha256 === digest(products[name]), 'Native envelope output join differs: ' + role);
      }
    }
  }
  return rows;
}

function historicalRebindCode(request, reader) {
  need(same(request.executed_code?.map(p => p.path), CURRENT_REBIND_CODE), 'Complete historical rebind code roster required');
  return CURRENT_REBIND_CODE.map(name => {
    const pin = reader.pin(request.execution_commit, name); reader.read(pin);
    return {path: name, bytes: pin.bytes, sha256: pin.sha256};
  });
}

function localRebindJoin(request, terminal, publication, products, reader) {
  const proof = JSON.parse(products['code-source.json']), plan = JSON.parse(products['issued-plan.json']), stdout = JSON.parse(products['stdout.json']);
  need(terminal.code_source_sha256 === digest(products['code-source.json']) && same(proof.command, terminal.command)
    && same(proof.command, request.execution?.command) && same(proof.pre_use, request.execution?.pre_use)
    && same(proof.pre_use, proof.post_use) && proof.execution_commit === request.execution_commit,
  'Rebind terminal/code-source/issued execution contract differs');
  need(proof.pre_use.plan.bytes === products['issued-plan.json'].length && proof.pre_use.plan.sha256 === digest(products['issued-plan.json'])
    && same(proof.pre_use.code, historicalRebindCode(request, reader)) && plan.execution_commit === request.execution_commit,
  'Rebind actual issued plan/code bytes differ');
  need(stdout.request_sha256 === terminal.request_sha256 && stdout.publication_sha256 === terminal.publication_sha256
    && stdout.execution_commit === terminal.execution_commit && stdout.result_sha256 === digest(products['result.json'])
    && publication.outputs.result.sha256 === stdout.result_sha256, 'Rebind actual stdout/product join differs');
  need(Number.isFinite(terminal.elapsed_seconds) && terminal.elapsed_seconds >= 0, 'Invalid rebind elapsed observation');
}

export function retainProducts(config, root, reader, readLocal = ordinary) {
  const requestRaw = reader.read(config.request), request = JSON.parse(requestRaw);
  const terminalRaw = readLocal(root, config.terminal), terminal = JSON.parse(terminalRaw); const publicationRaw = readLocal(root, config.output + '/publication.json'), publication = JSON.parse(publicationRaw); qualifyTerminal(terminal, requestRaw, publicationRaw, request);
  const rows = publication.outputs ? Object.values(publication.outputs) : publication.complete === true
    ? [{path: 'facts.json', ...publication.facts}, {path: 'inventory.jsonl.gz', ...publication.inventory}, ...(publication.assets ?? [])] : [];
  need(rows.length && new Set(rows.map(p => p.path)).size === rows.length, 'Missing/duplicate publication output inventory');
  const outputs = {'request.json': requestRaw, 'terminal.json': terminalRaw, 'publication.json': publicationRaw};
  for (const row of rows) {
    need(safe(row.path) && !row.path.includes('/') && !Object.hasOwn(outputs, row.path), 'Unsafe/duplicate publication path');
    const raw = readLocal(root, config.output + '/' + row.path); need(raw.length === row.bytes && digest(raw) === row.sha256, 'Incomplete actual publication output: ' + row.path);
    // The source/native inventory is decoded and authenticated by sourceNativeJoin below.
    if (row.uncompressed_bytes !== undefined && (publication.outputs || row.path !== 'inventory.jsonl.gz')) {
      need(Number.isSafeInteger(row.uncompressed_bytes) && row.uncompressed_bytes > 0, 'Invalid decoded output identity');
      const decoded = gunzipSync(raw, {maxOutputLength: row.uncompressed_bytes});
      need(decoded.length === row.uncompressed_bytes && digest(decoded) === row.uncompressed_sha256, 'Decoded output differs');
    }
    outputs[row.path] = raw;
  }
  const facts = JSON.parse(outputs['facts.json']);
  need(facts.execution_commit === terminal.execution_commit, 'Published facts execution differs');
  if (publication.outputs) {
    need(publication.kind === 'native-additive-current-bank-rebind-publication-v1'
      && publication.execution_commit === terminal.execution_commit && publication.request_sha256 === digest(requestRaw)
      && facts.request_sha256 === digest(requestRaw) && facts.result_sha256 === digest(outputs['result.json']),
    'Rebind publication/facts/result are not joined to terminal request');
    const custodyNames = {code_source: 'code-source.json', issued_plan: 'issued-plan.json', stderr: 'stderr.log', stdout: 'stdout.json'};
    need(config.custody && same(Object.keys(config.custody).sort(), Object.keys(custodyNames).sort()), 'Complete real rebind execution custody required');
    for (const [role, name] of Object.entries(custodyNames)) {
      const raw = readLocal(root, config.custody[role]); outputs[name] = raw;
    }
    localRebindJoin(request, terminal, publication, outputs, reader);
  } else need(facts.request?.sha256 === digest(requestRaw) && facts.request.bytes === requestRaw.length
    && facts.operation === request.operation, 'Published facts are not joined to the actual terminal request');
  if (!publication.outputs) sourceNativeJoin(request, facts, publication, outputs['inventory.jsonl.gz'], reader, outputs);
  return outputs;
}

export function nativeRequests(config, reader) {
  const outputs = {}, seen = new Set(), components = new Set();
  need(Array.isArray(config.groups) && config.groups.length, 'Explicit native groups required');
  for (const group of config.groups) {
    need(/^[a-z0-9-]+$/.test(group.id) && !seen.has(group.id), 'Unique native group IDs required'); seen.add(group.id);
    const sourceRaw = reader.read(group.source.request), source = JSON.parse(sourceRaw);
    const publicationRaw = reader.read(group.source.publication), publication = JSON.parse(publicationRaw);
    const terminal = reader.json(group.source.operating), facts = reader.json(group.source.facts);
    qualifyTerminal(terminal, sourceRaw, publicationRaw, source);
    need(source.operation === 'retained-land-source-premises-v1' && publication.complete === true
      && publication.facts.sha256 === group.source.facts.sha256 && publication.facts.bytes === group.source.facts.bytes
      && publication.inventory.sha256 === group.source.inventory.sha256 && publication.inventory.bytes === group.source.inventory.bytes,
    'Native request requires actual committed SOURCE publication products');
    sourceNativeJoin(source, facts, publication, reader.read(group.source.inventory), reader);
    need(facts.execution_commit === terminal.execution_commit && facts.request?.sha256 === digest(sourceRaw)
      && same(facts.source_rule, source.source_rule), 'SOURCE facts/terminal/request mismatch');
    const template = requestProfile(reader.json(group.template), group, config, reader), additive = template.additive;
    need(template.operation === 'unactivated-additive-native-batch-v1' && additive?.source_profile === source.source_rule.profile
      && same(additive.scope_ids, source.source_rule.expected_ids) && same(template.baseline, source.baseline),
    'Native template method/scope/baseline differs from qualified source');
    need(unique(additive.scope_ids) && additive.scope_ids.every(id => !components.has(id)), 'Overlapping/duplicate native scopes');
    additive.scope_ids.forEach(id => components.add(id));
    need(Number.isSafeInteger(facts.runtime?.bytes) && facts.runtime.bytes > 0 && hex(facts.runtime.sha256, 64), 'Actual SOURCE runtime identity required');
    // Native's existing reader compares the literal issued request descriptor,
    // not only an alias with equal bytes at a later retention commit.
    const originalRequest = facts.request; reader.read(originalRequest);
    need(originalRequest.path === group.source.request.path && originalRequest.bytes === sourceRaw.length
      && originalRequest.sha256 === digest(sourceRaw), 'Original SOURCE request descriptor differs');
    const inventoryPin = {...group.source.inventory, uncompressed_bytes: publication.inventory.uncompressed_bytes,
      uncompressed_sha256: publication.inventory.uncompressed_sha256};
    const changes = {source_request_path: originalRequest, operating_path: group.source.operating,
      publication_path: group.source.publication, facts_path: group.source.facts, inventory_path: inventoryPin};
    const replaced = new Set(Object.keys(changes).map(key => additive[key]));
    need(replaced.size === 5 && [...replaced].every(name => additive.inputs.filter(p => p.path === name).length === 1), 'Native template lacks exact source input slots');
    const inputs = additive.inputs.filter(p => !replaced.has(p.path));
    for (const pin of Object.values(changes)) inputs.push({...pin, blob: pin.blob ?? pin.git_blob_oid});
    for (const pin of inputs) delete pin.git_blob_oid;
    need(new Set(inputs.map(p => p.path)).size === inputs.length, 'Replacement source input path collision');
    need(safe(group.destination) && group.destination.startsWith('.cache/native-grid-candidates/'), 'Native candidate destination required');
    outputs[group.id + '-native-request.json'] = jsonBytes({...template, destination: group.destination,
      additive: {...additive, ...Object.fromEntries(Object.entries(changes).map(([key, pin]) => [key, pin.path])),
        source_execution_commit: terminal.execution_commit, source_runtime: facts.runtime, inputs}});
  }
  return outputs;
}

export function rebindCustody(config, reader, certificate = false) {
  const request = reader.json(config.request), terminal = reader.json(config.terminal), publication = reader.json(config.publication);
  qualifyTerminal(terminal, reader.read(config.request), reader.read(config.publication), request);
  need(same(Object.keys(config.execution_custody).sort(), ['code_source', 'issued_plan', 'stderr', 'stdout', 'terminal']), 'Complete external execution custody required');
  need(same(config.execution_custody.terminal, config.terminal), 'Custody terminal differs');
  const expected = {version: 1, kind: 'native-additive-current-bank-rebind-operating-v1',
    execution_commit: terminal.execution_commit, request_sha256: config.request.sha256, publication_sha256: config.publication.sha256,
    exit_code: terminal.exit_code, signal: terminal.signal, owned_processes_remaining: terminal.owned_processes_remaining,
    ...(Object.hasOwn(terminal,'lifetime_rss_bytes')?{lifetime_rss_bytes:terminal.lifetime_rss_bytes}:{}), elapsed_seconds: terminal.elapsed_seconds, execution_custody: config.execution_custody};
  const operating = certificate ? reader.json(config.operating) : expected;
  need(same(operating, expected), 'Operating proof differs from exact genuine terminal/custody');
  need(publication.execution_commit === request.execution_commit && publication.request_sha256 === config.request.sha256,
    'Rebind publication request binding differs');
  for (const role of ['facts', 'result']) {
    reader.read(config[role]); const output = publication.outputs?.[role];
    need(output && output.bytes === config[role].bytes && output.sha256 === config[role].sha256, 'Rebind output pin differs from actual publication');
  }
  const custody = Object.fromEntries(Object.entries(config.execution_custody).map(([role, pin]) => [role, reader.read(pin)]));
  verifyCurrentRebindExecution({request, operating, expectedCode: historicalRebindCode(request, reader), custody: {...custody, result_sha256: config.result.sha256}});
  if (!certificate) return {'operating.json': jsonBytes(operating)};
  return {'certificate.json': jsonBytes({version: 1, kind: 'qualified-native-additive-current-bank-rebind-v1',
    execution_commit: request.execution_commit, base_selection: request.base_selection,
    authority_registry_sha256: request.authority_registry_sha256,
    request: config.request, facts: config.facts, publication: config.publication, result: config.result, operating: config.operating})};
}

export async function composeAuthorities(config, reader) {
  if (config.selector) {
    const authorityFields = ['rule_preimage', 'source_authority', 'ledger', 'native_patch'];
    const multiple = Object.hasOwn(config, 'authorities');
    need(!multiple || !authorityFields.some(key => Object.hasOwn(config, key)), 'Do not mix singleton and multiple modern authorities');
    const authorities = multiple ? config.authorities : [Object.fromEntries(authorityFields.map(key => [key, config[key]]))];
    need(Array.isArray(authorities) && authorities.length > 0 && authorities.every(value => value
      && same(Object.keys(value).sort(), [...authorityFields].sort())
      && authorityFields.every(key => value[key] && Number.isSafeInteger(value[key].bytes) && value[key].bytes > 0)),
    'Complete nonempty modern authority pin groups required');
    need(config.selector.path === 'data/ownership-selection.json' && typeof config.effective_release_id === 'string'
      && config.effective_release_id.startsWith('geography:'), 'Original selected baseline and explicit effective release required');
    await reader.acquire?.([config.selector, ...authorities.flatMap(original => authorityFields.map(role => original[role]))]);
    const selection = reader.json(config.selector), hook = selection.additive_release;
    need(hook && safe(hook.path), 'Existing cumulative selection required');
    await reader.acquire?.([{...hook, commit: config.selector.commit}]);
    const sidecarPin = reader.pin(config.selector.commit, hook.path);
    need(sidecarPin.bytes === hook.bytes && sidecarPin.sha256 === hook.sha256, 'Original selected sidecar differs');
    const sidecar = reader.json(sidecarPin), base = scientificNativeSelection(selection);
    need(sidecar.version === 2 && sidecar.kind === 'retained-native-additive-selection-v2'
      && same(sidecar.base_selection, base), 'Original selected base differs');
    const assets = sidecar.logical_asset_map;
    need(assets && same(Object.keys(assets).sort(), ['base_manifest', 'ledger', 'owner_roster', 'patch']), 'Complete prior logical assets required');
    await reader.acquire?.([sidecar.authority_registry, assets.ledger, assets.patch, sidecar.runtime_envelope, assets.base_manifest]);
    const priorRegistry = reader.json(sidecar.authority_registry), priorLedger = reader.json(assets.ledger);
    const priorPatch = reader.json(assets.patch), wrapped = reader.json(sidecar.runtime_envelope);
    const envelope = wrapped.additiveRelease ?? wrapped;
    need(envelope.version === 2 && envelope.kind === 'retained-native-base-plus-delta-v2', 'Existing v2 runtime envelope required');
    for (const [role, pin] of Object.entries(assets)) {
      const declared = envelope[role];
      need(declared?.bytes === pin.bytes && declared?.sha256 === pin.sha256
        && (declared.decoded_bytes ?? declared.bytes) === (pin.decoded_bytes ?? pin.bytes)
        && (declared.decoded_sha256 ?? declared.sha256) === (pin.decoded_sha256 ?? pin.sha256), 'Prior envelope asset binding differs: ' + role);
    }
    need(priorRegistry.version === 1 && priorRegistry.kind === 'retained-rule-authority-registry-v1' && priorLedger.version === 2,
      'Existing v2 cumulative registry/ledger required');
    const manifest = reader.json(assets.base_manifest);
    if (selection.reference_projection) {
      const pointer = {...selection.reference_projection, commit: config.selector.commit};
      await reader.acquire?.([pointer, assets.owner_roster]);
      const projection = reader.json(reader.pin(pointer.commit, pointer.path));
      await reader.acquire?.([projection.hierarchy.before, projection.hierarchy.after, ...projection.receipts,
        ...projection.source_updates.flatMap(update => [update.before, update.after])]);
    }
    const references = qualifiedDeliveryReference(selection, manifest, reader, config.selector.commit, assets.owner_roster);
    need((same(envelope.base_reference, references.native) || same(envelope.base_reference, references.reference))
      && (!references.projectionPin || envelope.effective_reference?.hierarchy_sha256 === envelope.base_reference.hierarchy_sha256),
    'Prior cumulative reference differs from selected current metadata');
    const contract = Object.fromEntries(['size', 'coordinateBits', 'method', 'native_latitudes', 'hierarchy_sha256', 'original_assets']
      .map(key => [key, manifest[key]]));
    need(priorPatch.version === 2 && priorPatch.authority_registry_sha256 === sidecar.authority_registry.sha256
      && priorPatch.ledger_sha256 === assets.ledger.sha256 && same(priorPatch.base_reference, envelope.base_reference)
      && same(priorPatch.effective_reference, envelope.effective_reference), 'Prior cumulative patch bindings differ');
    const entries = [...priorRegistry.entries], addedRows = [], candidates = [];
    const authorityIds = new Set(entries.map(entry => entry.authority_sha256));
    const bindings = authorities.map(original => reader.json(original.source_authority));
    await reader.acquire?.(bindings.map(binding => binding.source_evidence));
    for (const [index, original] of authorities.entries()) {
      const constructed = reader.json(original.ledger), candidate = reader.json(original.native_patch);
      const binding = bindings[index], preimage = reader.json(original.rule_preimage);
      // Literal metadata contract of constructAuthorityRegistry. Retained constructor
      // results supply qualification; the final selected reader remains authoritative.
      const rule = reader.pin(original.rule_preimage.commit, original.rule_preimage.path);
      const authority = {policy_id: 'retained-source-literal-additions', policy_version: 1, rule_preimage: rule,
        rule_sha256: rule.sha256, source_authority: reader.pin(original.source_authority.commit, original.source_authority.path)};
      const entry = {authority_sha256: digest(jsonBytes(authority)), ...authority,
        completed_constructor: reader.pin(original.ledger.commit, original.ledger.path)};
      need(same(binding.native_patch, original.native_patch) && entry.rule_sha256 === digest(jsonBytes(preimage)),
        'Committed modern constructor scope/rule/patch differs');
      const evidence = reader.json(binding.source_evidence);
      const proof = verifyCompletedSourceTargetNativeAuthority({constructed, binding, preimage, evidence, candidate});
      need(same(evidence.base_reference, references.native) && same(evidence.native_contract, contract)
        && assets.base_manifest.sha256 === selection.sha256 && assets.owner_roster.sha256 === manifest.original_assets?.bounds?.sha256,
      'Modern source changes the selected native baseline/contract');
      need(!authorityIds.has(entry.authority_sha256), 'Modern authority is already selected or duplicated');
      authorityIds.add(entry.authority_sha256);
      entries.push(entry);
      const added = proof.original_ledger.rows.map(row => {
        return {...row, authority_sha256: entry.authority_sha256, rule_sha256: entry.rule_sha256};
      });
      addedRows.push(...added);
      candidates.push({candidate, added});
    }
    const registry = {...priorRegistry, entries: entries.sort((a, b) => a.authority_sha256.localeCompare(b.authority_sha256))};
    const rows = [...priorLedger.rows, ...addedRows].sort(compareRepairComponents);
    const ledger = {...priorLedger, authority_registry_sha256: digest(jsonBytes(registry)), rows, scope_ids: rows.map(row => row.component_id)};
    compareVersionedRepairLedgers(priorLedger, ledger, {beforeRegistry: priorRegistry, afterRegistry: registry});
    need(priorLedger.rows.every(row => same(row, rows.find(next => repairComponentKey(next) === repairComponentKey(row)))), 'Literal inherited row/exception changed');
    const normalized = normaliseRetainedRepairLedger(ledger, registry), ledgerRaw = jsonBytes(ledger);
    const union = patches => mergeCompletedNativePatches(patches, manifest.size);
    const patchRows = union([priorPatch, ...candidates.map(value => value.candidate)]);
    const currentBase = references.reference;
    const effective = {...(references.projectionPin ? currentBase : envelope.effective_reference), id: config.effective_release_id,
      footprints_sha256: digest(jsonBytes({domain: 'worldatlas-effective-native-footprints:v2', base_reference: currentBase,
        authority_registry_sha256: ledger.authority_registry_sha256, ledger_sha256: digest(ledgerRaw), components: [...normalized.rows.values()]}))};
    const patch = {...priorPatch, authority_registry_sha256: ledger.authority_registry_sha256, ledger_sha256: digest(ledgerRaw),
      base_reference: currentBase, effective_reference: effective, rows: patchRows}, patchRaw = jsonBytes(patch);
    const nextEnvelope = {...envelope, base_reference: currentBase, effective_reference: effective,
      ledger: {...envelope.ledger, bytes: ledgerRaw.length, sha256: digest(ledgerRaw)},
      patch: {...envelope.patch, bytes: patchRaw.length, sha256: digest(patchRaw)}};
    const products = {'authority-registry.json': jsonBytes(registry), 'selected-ledger.json': ledgerRaw, 'patch.json': patchRaw,
      'runtime-envelope.json': jsonBytes(wrapped.additiveRelease ? {...wrapped, reference_release: effective, additiveRelease: nextEnvelope} : nextEnvelope)};
    return products;
  }
  await reader.acquire?.([...config.registries, ...config.ledgers]);
  const registries = config.registries.map(p => reader.json(p));
  need(registries.length && registries.every(r => r.version === 1 && r.kind === 'retained-rule-authority-registry-v1'), 'Existing retained registries required');
  const entries = new Map();
  for (const registry of registries) for (const entry of registry.entries) {
    need(!entries.has(entry.authority_sha256) || same(entries.get(entry.authority_sha256), entry), 'Conflicting retained authority');
    entries.set(entry.authority_sha256, entry);
  }
  const registry = {version: 1, kind: 'retained-rule-authority-registry-v1', entries: [...entries.values()].sort((a, b) => a.authority_sha256.localeCompare(b.authority_sha256))};
  const members = config.ledgers.map(pin => {
    const original = reader.json(pin);
    need(original.version === 1 && unique(original.scope_ids) && same(original.scope_ids, original.rows?.map(row => row.component_id)),
      'Original complete ledger roster mismatch');
    // Native outputs retain accepted handoff order. The existing composer uses
    // canonical component order. Preserve every raw row and the original pin;
    // only this in-memory view is ordered for its existing validator.
    const rows = [...original.rows].sort(compareRepairComponents);
    return {...original, rows, scope_ids: rows.map(row => row.component_id)};
  });
  const ledger = composeRetainedLedgers(members, registry);
  return {'authority-registry.json': jsonBytes(registry), 'composed-original-ledger.json': jsonBytes(ledger)};
}

export function packageProjection(config, reader, acceptedRegistry = null) {
  return projectPackage(config, reader, acceptedRegistry);
}

// Only finalizeDelivery can supply its invocation-owned parsed snapshot.
// Public readers retain complete conservation comparisons, even for aliases.
function projectPackage(config, reader, acceptedRegistry, ownedSnapshot) {
  const registry = reader.json(config.registry), ledger = reader.json(config.ledger);
  const normalized = normaliseRetainedRepairLedger(ledger, registry);
  const roles = new Map();
  function add(pin, role) {
    need(pin && safe(pin.path), 'Missing whole consumed package role: ' + role);
    reader.read(pin);
    // This closed modern role is consumed by exact versioned Git reads, never
    // installed or executed at its pathname. Keep each original vintage while
    // current/filesystem roles retain their existing single-path identity.
    const key = role === 'source-target physical_reproduction'
      ? 'physical-reproduction\0' + jsonBytes(pin).toString('utf8') : pin.path;
    const prior = roles.get(key);
    need(!prior || prior.sha256 === pin.sha256 && prior.bytes === pin.bytes, 'Conflicting package path vintages');
    if (!prior) roles.set(key, {...pin, roles: []});
    if (!roles.get(key).roles.includes(role)) roles.get(key).roles.push(role);
  }
  need(safe(config.new_prefix.slice(0, -1)) && config.new_prefix.endsWith('/'), 'Explicit new authority prefix required');
  // Finalize supplies the registry authenticated through the original selector.
  // Standalone package and initial legacy finalization retain prefix selection.
  let incoming = registry.entries.filter(e => e.source_authority.path.startsWith(config.new_prefix));
  if (acceptedRegistry !== null) {
    need(acceptedRegistry?.version === 1 && acceptedRegistry.kind === 'retained-rule-authority-registry-v1'
      && Array.isArray(acceptedRegistry.entries) && acceptedRegistry.entries.length > 0,
    'Complete accepted authority registry required');
    const inherited = new Set();
    for (const entry of acceptedRegistry.entries) {
      need(hex(entry?.authority_sha256, 64) && !inherited.has(entry.authority_sha256), 'Duplicate or invalid accepted authority identity');
      inherited.add(entry.authority_sha256);
      need(same(normalized.authorities.get(entry.authority_sha256) ?? null, entry), 'Inherited authority removed or changed');
    }
    incoming = registry.entries.filter(entry => !inherited.has(entry.authority_sha256));
  }
  let added = 0;
  for (const entry of incoming) {
    added++; add(entry.rule_preimage, 'authority rule preimage'); add(entry.source_authority, 'authority binding');
    if (entry.completed_constructor !== undefined) add(entry.completed_constructor, 'completed constructor');
    const binding = reader.json(entry.source_authority);
    if (binding.kind === 'source-target-native-custody-v1') {
      const preimage = reader.json(entry.rule_preimage);
      need(binding.version === 1 && same(Object.keys(binding).sort(), ['kind', 'native_patch', 'source_evidence', 'version'])
        && same(preimage, {...binding, kind: 'source-target-native-rule-v1'}), 'Source-target authority inputs differ');
      add(binding.source_evidence, 'original source evidence'); add(binding.native_patch, 'original native patch');
      const evidence = reader.json(binding.source_evidence);
      need((evidence.version === 1 && evidence.kind === 'source-target-native-evidence-v1'
        || evidence.version === 2 && evidence.kind === 'source-target-native-evidence-v2'
        || evidence.version === 3 && evidence.kind === 'source-target-native-evidence-v3')
        && Array.isArray(evidence.targets) && evidence.targets.length > 0
        && Array.isArray(evidence.families) && evidence.families.length > 0, 'Missing source-target evidence roles');
      // Completed qualification is consumed through these five original bodies:
      // rule, binding, constructor, evidence and patch. The immutable evidence
      // retains every source/license/provenance reference. Reopening its corpus
      // cannot establish source validity and is not a finalizer/package input.
      // Scientific qualification, source review and selected admission remain
      // authoritative; an unqualified entry still needs the full traversal.
      if (entry.completed_constructor !== undefined) continue;
      // Closed whole-body read roles of qualifySourceTargetNativeAuthority. Its
      // physical reproducer is authenticated, never executed here; nested GIS
      // operands/native contracts are not a recursive package declaration.
      for (const role of ['catalogue', 'physical_input', 'physical_reproduction', 'physical_evidence', 'native_latitudes', 'owner_roster'])
        add(evidence[role], 'source-target ' + role);
      if (evidence.canonical_seam_views !== undefined) {
        add(evidence.canonical_seam_views, 'source-target canonical seam views');
        const views = reader.json(evidence.canonical_seam_views);
        need(views.version === 1 && views.kind === 'retained-periodic-native-views-v1'
          && views.method?.export === 'canonical' && views.method.pin.path === 'scripts/majority.py',
          'Missing canonical seam view method');
        add(views.method.pin, 'source-target canonical seam method');
      }
      if (evidence.version === 3) {
        add(evidence.revised_source_adoption, 'source-target revised source adoption');
        const adoption = reader.json(evidence.revised_source_adoption);
        need(adoption.version === 1 && adoption.kind === 'adopted-osm-revised-source-native-v1',
          'Missing adopted revised source roles');
        for (const role of ['raw_source', 'source_stage', 'assessment', 'scope', 'parent_decision', 'current_geography', 'attribution'])
          add(adoption[role], 'source-target revised ' + role);
        const fine = reader.json(adoption.current_geography);
        const indexes = fine.input_pins?.filter(pin => pin.path === 'data/world-index.json');
        need(indexes?.length === 1, 'Missing revised source current index');
        add(indexes[0], 'source-target revised current index');
      }
      // Its product pins must equal existing complete family parts at the
      // authority boundary; the adoption body is the sole new leaf read role.
      if (evidence.adopted_provider_families !== undefined)
        add(evidence.adopted_provider_families, 'source-target adopted provider families');
      const interpretations = [
        ...(evidence.version === 2 ? [{pin: evidence.dated_land_support,
          kind: 'adopted-dated-native-centre-land-support-v1', role: 'dated', label: 'dated support',
          root: 'dated land support', roles: ['adoption', 'review', 'observation', 'frame']}] : []),
        ...(evidence.territorial_applicability === undefined ? [] : [{pin: evidence.territorial_applicability,
          kind: 'adopted-native-territorial-applicability-v1', role: 'territorial', label: 'territorial applicability',
          root: 'territorial applicability', roles: ['adoption', 'scope', 'original-source']}])
      ];
      for (const typed of interpretations) {
        const pin = typed.pin;
        add(pin, 'source-target ' + typed.root);
        let raw = reader.read(pin);
        if (pin.decoded_bytes !== undefined) {
          need(Number.isSafeInteger(pin.decoded_bytes) && pin.decoded_bytes > 0
            && hex(pin.decoded_sha256, 64), 'Decoded ' + typed.label + ' identity required');
          raw = gunzipSync(raw, {maxOutputLength: pin.decoded_bytes});
          need(raw.length === pin.decoded_bytes && digest(raw) === pin.decoded_sha256,
            'Decoded ' + typed.label + ' identity differs');
        }
        const support = JSON.parse(raw);
        need(support.version === 1 && support.kind === typed.kind
          && Array.isArray(support.provenance) && support.provenance.length > 0,
        'Missing ' + typed.label + ' provenance roles');
        for (const provenance of support.provenance) {
          need(typed.roles.includes(provenance?.role), 'Unknown ' + typed.label + ' provenance role');
          const multipart=typed.role==='territorial'&&provenance.role==='original-source'&&provenance.parts!==undefined;
          need(!multipart||same(Object.keys(provenance).sort(),['id','parts','role'])
            &&Array.isArray(provenance.parts)&&provenance.parts.length>0,
          'Malformed territorial source parts');
          for(const member of multipart?provenance.parts:[provenance.pin])
            add(member, 'source-target ' + typed.role + ' ' + provenance.role);
        }
      }
      for (const family of evidence.families) {
        need(typeof family.source_id === 'string' && family.source_id && Array.isArray(family.parts)
          && family.parts.length > 0, 'Missing complete source family roles');
        for (const pin of family.parts) add(pin, 'source-target source family part');
      }
      if (evidence.territorial_exclusion_sources !== undefined) {
        const sources = evidence.territorial_exclusion_sources;
        need(Array.isArray(sources) && sources.length > 0 && unique(sources.map(f => f.source_id)),
          'Unique complete territorial source roles required');
        for (const family of sources) {
          need(same(Object.keys(family).sort(), ['parts', 'source_id']) && Array.isArray(family.parts)
            && family.parts.length > 0, 'Missing complete territorial source parts');
          for (const pin of family.parts) add(pin, 'source-target territorial source part');
        }
      }
      if (evidence.source_membership !== undefined) {
        const membership = evidence.source_membership;
        need(membership && same(Object.keys(membership).sort(), ['index', 'lineage', 'parts',
          ...(membership.cohort_inventory === undefined ? [] : ['cohort_inventory']),
          ...(membership.negative_natural_earth === undefined ? [] : ['negative_natural_earth'])].sort())
          && Array.isArray(membership.parts) && membership.parts.length > 0, 'Missing accepted source membership roles');
        add(membership.index, 'source-target membership index'); add(membership.lineage, 'source-target membership lineage');
        for (const pin of membership.parts) add(pin, 'source-target membership part');
        if (membership.negative_natural_earth !== undefined) {
          const role = membership.negative_natural_earth;
          need(role && same(Object.keys(role).sort(), ['atoms', 'registry', 'source'])
            && Array.isArray(role.atoms) && role.atoms.length > 0, 'Missing negative Natural Earth roles');
          add(role.registry, 'source-target negative Natural Earth registry');
          add(role.source, 'source-target negative Natural Earth whole source');
        }
        if (membership.cohort_inventory !== undefined) {
          const inventory = membership.cohort_inventory;
          need(inventory && same(Object.keys(inventory).sort(), ['index', 'parts'])
            && Array.isArray(inventory.parts) && inventory.parts.length > 0, 'Missing complete canonical cohort roles');
          add(inventory.index, 'source-target cohort index');
          for (const pin of inventory.parts) add(pin, 'source-target cohort part');
        }
      }
      continue;
    }
    for (const [role, pin] of Object.entries(binding.original_pins)) add(pin, 'original ' + role);
    for (const role of ['publication', 'inventory', 'operating']) add(binding.native_proof[role], 'native ' + role);
    for (const pin of binding.native_proof.assets) add(pin, 'native emitted asset');
    const aliases = new Map((binding.source_output_aliases ?? []).map(a => [a.original.path, a.published]));
    need(aliases.size === (binding.source_output_aliases ?? []).length, 'Duplicate source alias');
    for (const pin of aliases.values()) add(pin, 'source publication alias');
    const native = reader.json(binding.original_pins.native_request).additive;
    for (const key of ['publication_path', 'inventory_path', 'operating_path']) {
      const matches = native.inputs.filter(p => p.path === native[key]); need(matches.length === 1, 'Missing/ambiguous qualified source role');
      add(aliases.get(matches[0].path) ?? matches[0], 'qualified source ' + key);
    }
  }
  add(config.registry, 'composed registry'); add(config.ledger, 'composed ledger');
  if (config.rebind) {
    add(config.rebind, 'current rebind certificate'); const certificate = reader.json(config.rebind);
    for (const role of ['request', 'facts', 'publication', 'result', 'operating']) add(certificate[role], 'current rebind ' + role);
    for (const [role, pin] of Object.entries(reader.json(certificate.operating).execution_custody)) add(pin, 'current external ' + role);
  }
  // These shallow projections are stable only for our private parsed ledger.
  // Do not retain a snapshot of a caller-owned mutable row cursor.
  const ownedRows = ownedSnapshot !== undefined && ledger === ownedSnapshot ? [...normalized.rows.values()] : null;
  const cohorts = registry.entries.map(entry => {
    const rows = (ownedRows ?? [...normalized.rows.values()]).filter(row => row.authority_sha256 === entry.authority_sha256);
    return {original_batch_id: 'retained-authority-scope:' + entry.authority_sha256, component_ids: rows.map(row => row.component_id),
      members: rows.map(row => ({component_id: row.component_id, target_id: row.target_id, disposition: row.disposition,
        ...(row.representation === 'native-cells' ? {native_rows_sha256: digest(jsonBytes(row.native_rows))}
          : {geometry_sha256: row.geometry_sha256})}))};
  }).filter(c => c.members.length);
  const expectation = {version: 1, selected_ledger_sha256: null,
    cumulative_native_cells: (ownedRows ?? [...normalized.rows.values()]).reduce((sum, row) => sum + row.native_cells, 0), cohorts};
  if (config.selected_ledger) {
    const selected = reader.json(config.selected_ledger);
    const sameSnapshot = ownedSnapshot !== undefined && selected === ownedSnapshot && ledger === ownedSnapshot;
    need((sameSnapshot || same(selected.rows, ledger.rows) && same(selected.scope_ids, ledger.scope_ids))
      && selected.authority_registry_sha256 === ledger.authority_registry_sha256 && selected.current_rebind && selected.current_targets,
    'Actual selected ledger does not conserve original rows/current rebind');
    expectation.selected_ledger_sha256 = config.selected_ledger.sha256; add(config.selected_ledger, 'actual selected ledger');
  }
  for (const pin of config.outer_roles ?? []) add(pin, 'explicit final reader outer role');
  const projection = {version: 1, kind: 'prospective-fixed-role-package-projection', new_authorities: added,
    paths: [...roles.values()].sort((a, b) => a.path.localeCompare(b.path) || a.commit.localeCompare(b.commit)),
    pending: ['Compare actual completed selected-reader inventory, preserving prior declarations; run real package/consumer checks.',
      ...(!config.selected_ledger ? ['Actual selected ledger and outer release/custody pins remain pending.'] : [])],
    limits: ['Fixed consumed metadata roles only; no recursive scientific/preparation inputs. This does not certify reader/build success or delivery.']};
  return {'package-roles.json': jsonBytes(projection), 'selected-delivery-expectations.json': jsonBytes(expectation)};
}

const orderedBytes = value => Buffer.from(JSON.stringify(value, null, 2) + '\n');

// The selector retains scientific N while an accepted whole application may
// supply current metadata M. Source/receipt qualification remains in the
// existing explicit reference preparation and trusted selected reader.
export function selectedDeliveryReference(selection, manifest, reader, commit) {
  const native = {id: manifest.geographic_release, footprints_sha256: manifest.footprints_sha256,
    hierarchy_sha256: manifest.hierarchy_sha256};
  const pointer = selection.reference_projection;
  if (pointer === undefined) return {native, reference: native};
  originalNativeReference(manifest);
  need(selection.release_id === native.id, 'Delivery native reference differs from original selector');
  need(same(Object.keys(pointer).sort(), ['bytes', 'path', 'sha256']) && safe(pointer.path)
    && Number.isSafeInteger(pointer.bytes) && pointer.bytes > 0 && hex(pointer.sha256, 64),
  'Complete ordinary delivery reference projection pointer required');
  const projectionPin = reader.pin(commit, pointer.path);
  need(projectionPin.mode === '100644' && projectionPin.bytes === pointer.bytes && projectionPin.sha256 === pointer.sha256,
    'Delivery reference projection whole identity differs');
  const projection = reader.json(projectionPin);
  const references = validateReferenceMetadataHeader(projection, {selection, manifest});
  return {...references, projectionPin};
}

// Preparation may bridge an old N-based cumulative selection to applied M only
// after the existing complete receipt/source validator proves that application.
// Keep the original encoded owner body and original raw source pins literal.
export function qualifiedDeliveryReference(selection, manifest, reader, commit, ownerPin) {
  const references = selectedDeliveryReference(selection, manifest, reader, commit);
  if (!references.projectionPin) return references;
  need(ownerPin?.sha256 === manifest.original_assets?.bounds?.sha256,
    'Delivery metadata differs from original owner roster');
  const raw = reader.read(ownerPin);
  need(raw.length === ownerPin.bytes && digest(raw) === ownerPin.sha256, 'Delivery metadata whole owner roster differs');
  let decoded = raw;
  if (raw[0] === 31 && raw[1] === 139) {
    need(Number.isSafeInteger(ownerPin.decoded_bytes) && ownerPin.decoded_bytes > 0
      && hex(ownerPin.decoded_sha256, 64),
    'Complete bounded delivery original owner decoding required');
    decoded = gunzipSync(raw, {maxOutputLength: ownerPin.decoded_bytes + 1});
    need(decoded.length === ownerPin.decoded_bytes && digest(decoded) === ownerPin.decoded_sha256,
      'Delivery metadata decoded original owner roster differs');
  }
  const projection = reader.json(references.projectionPin);
  validateReferenceMetadataProjection({projection, selection, manifest, owners: JSON.parse(decoded), read: pin => reader.read(pin)});
  return references;
}

// Adapt existing stock correction/release products into one native application.
// The caller supplies whole input pins, never a handwritten release or receipt.
export function prepareReferenceMetadata(config, reader) {
  need(config?.version === 1 && same(Object.keys(config).sort(), ['version', 'selector', 'native_manifest',
    'owner_roster', 'current_release', 'hierarchy', 'receipts', 'source_updates'].sort())
    && config.selector?.path === 'data/ownership-selection.json'
    && config.current_release?.path === 'data/geographic-releases/current-manifest.json'
    && config.hierarchy && same(Object.keys(config.hierarchy).sort(), ['after', 'before'])
    && Array.isArray(config.receipts) && config.receipts.length > 0 && Array.isArray(config.source_updates),
  'Exact reference metadata preparation inputs required');
  const inventory = new Map();
  function read(pin, role = 'reference metadata input') {
    need(pin && safe(pin.path) && hex(pin.commit, 40) && pin.mode === '100644'
      && hex(pin.git_blob_oid, 40) && Number.isSafeInteger(pin.bytes) && pin.bytes > 0
      && hex(pin.sha256, 64), 'Complete ordinary reference preparation pin required');
    const raw = reader.read(pin);
    need(Buffer.isBuffer(raw) && raw.length === pin.bytes && digest(raw) === pin.sha256
      && createHash('sha1').update('blob ' + raw.length + '\0').update(raw).digest('hex') === pin.git_blob_oid,
    'Whole reference preparation input differs');
    const key = pin.commit + ':' + pin.path, prior = inventory.get(key);
    need(!prior || same(prior.pin, pin), 'Conflicting reference preparation input vintages');
    if (!prior) inventory.set(key, {pin: {...pin}, roles: []});
    const entry = inventory.get(key); if (!entry.roles.includes(role)) entry.roles.push(role);
    return raw;
  }
  const json = (pin, role) => JSON.parse(read(pin, role));
  const selection = json(config.selector, 'original scientific selector');
  const manifest = json(config.native_manifest, 'original native manifest');
  need(config.native_manifest.sha256 === selection.sha256, 'Reference preparation native manifest differs from selector');
  const encodedOwners = read(config.owner_roster, 'original complete owner roster');
  need(config.owner_roster.sha256 === manifest.original_assets?.bounds?.sha256,
    'Reference preparation original owner roster differs');
  let ownersRaw = encodedOwners;
  if (encodedOwners[0] === 31 && encodedOwners[1] === 139) {
    need(Number.isSafeInteger(config.owner_roster.decoded_bytes) && config.owner_roster.decoded_bytes > 0
      && hex(config.owner_roster.decoded_sha256, 64),
    'Complete bounded original owner roster decoding required');
    ownersRaw = gunzipSync(encodedOwners, {maxOutputLength: config.owner_roster.decoded_bytes + 1});
    need(ownersRaw.length === config.owner_roster.decoded_bytes && digest(ownersRaw) === config.owner_roster.decoded_sha256,
      'Reference preparation decoded original owners differ');
  }
  need(same(Object.keys(config.current_release).sort(), ['commit', 'path']) && hex(config.current_release.commit, 40),
    'Actual current release commit/path locator required');
  const releasePointer = reader.pin(config.current_release.commit, config.current_release.path);
  need(releasePointer.bytes <= 4096, 'Bounded actual current release pointer required');
  const pointer = json(releasePointer, 'accepted current release pointer');
  need(typeof pointer.path === 'string' && /^[A-Za-z0-9][A-Za-z0-9_.-]*\.json\.gz$/.test(pointer.path)
    && hex(pointer.sha256, 64) && hex(pointer.predecessor_index_sha256, 64), 'Actual current release pointer required');
  const releasePin = reader.pin(releasePointer.commit, 'data/geographic-releases/' + pointer.path);
  need(releasePin.sha256 === pointer.sha256, 'Current reference release whole identity differs');
  const originalIndex = reader.pin(releasePointer.commit, 'data/geographic-releases/index.json');
  need(originalIndex.sha256 === pointer.predecessor_index_sha256, 'Current reference release predecessor differs');
  const before = json(originalIndex, 'original geographic release index');
  const releases = JSON.parse(gunzipSync(read(releasePin, 'accepted current release registry'), {maxOutputLength: 64 * 1024 * 1024}));
  need(releases.version === before.version && releases.original_catalog_sha256 === before.original_catalog_sha256
    && Array.isArray(before.releases) && Array.isArray(releases.releases)
    && releases.releases.length > before.releases.length
    && same(releases.releases.slice(0, before.releases.length), before.releases)
    && new Set(releases.releases.map(row => row.id)).size === releases.releases.length
    && releases.releases.every((row, i, rows) => Number.isSafeInteger(row.version)
      && row.version > (i ? rows[i - 1].version : 0)), 'Current reference release does not preserve its actual predecessor');
  const current = releases.releases.at(-1);
  const native = originalNativeReference(manifest);
  need(releases.releases.some(row => same(Object.fromEntries(['id', 'footprints_sha256', 'hierarchy_sha256']
    .map(key => [key, row[key]])), native)), 'Current reference registry omits the exact original native release');
  const reference = Object.fromEntries(['id', 'footprints_sha256', 'hierarchy_sha256'].map(key => [key, current[key]]));
  const migrationPins=new Set(Object.values(current.metadata?.metadata_migration_sha256??{}));
  need(config.receipts.every(pin=>migrationPins.has(pin.sha256)),
    'Current reference release does not bind every applied metadata receipt');
  read(config.hierarchy.before, 'original complete hierarchy'); read(config.hierarchy.after, 'current complete hierarchy');
  for (const pin of config.receipts) read(pin, 'existing reference correction receipt');
  for (const update of config.source_updates) {
    need(update && same(Object.keys(update).sort(), ['after', 'before', 'logical_path']), 'Exact whole metadata source update required');
    read(update.before, 'original complete source'); read(update.after, 'current complete source');
  }
  const projection = prepareReferenceMetadataProjection({selection, manifest, owners: JSON.parse(ownersRaw), reference,
    hierarchy: config.hierarchy, receipts: config.receipts, source_updates: config.source_updates, read});
  return {products: {'reference-metadata.json': jsonBytes(projection)},
    input_inventory: [...inventory.values()].map(({pin, roles}) => ({...pin, roles, whole_body_consumed: true}))};
}

export function finalizedSelection(originalRaw, sidecar, pin) {
  const selection = JSON.parse(originalRaw), base = {...selection}; delete base.additive_release;
  need(selection.version === 1 && sidecar.version === 2 && sidecar.kind === 'retained-native-additive-selection-v2'
    && same(sidecar.base_selection, scientificNativeSelection(selection)), 'Final sidecar must preserve the complete original base selection');
  const reference = {path: pin.path, bytes: pin.bytes, sha256: pin.sha256};
  // The selected consumer compares some nested metadata with JSON.stringify.
  // Keep original key insertion order, including selected_geography, and leave
  // an already-finalized body's whitespace untouched on repeated preparation.
  if (same(selection.additive_release, reference)) return originalRaw;
  selection.additive_release = reference;
  const after = {...selection}; delete after.additive_release;
  need(JSON.stringify(after) === JSON.stringify(base), 'Unchanged selector insertion order differs');
  return orderedBytes(selection);
}

export function finalizedPackageInputs(original, prefix, paths) {
  validatePackageInputs(original);
  need(safe(prefix.slice(0, -1)) && prefix.endsWith('/') && original.version === 1
    && unique(original.inputs) && unique(paths) && paths.every(p => safe(p) && p.startsWith(prefix)), 'Exact owned package paths required');
  return appendPackageReadPaths(original, paths);
}

function appendPackageReadPaths(original, paths, prior = {}) {
  const priorSelectedPaths = prior.selection ? selectedCumulativePackageRoles(prior.selection, prior.priorSidecarRaw).map(pin=>pin.path) : [];
  validatePackageInputs(original);
  need(unique(paths) && paths.every(safe), 'Exact package read paths required');
  // Retire only exact prior cumulative roles authenticated by the selector.
  // Never narrow a directory declaration or infer roles from filenames. Shared
  // current assets and unrelated declarations retain their original order.
  need(priorSelectedPaths.every(safe), 'Safe authenticated prior selected paths required');
  const retired = new Set(priorSelectedPaths.filter(p => !paths.includes(p)));
  const retained = original.inputs.filter(p => !retired.has(p));
  const additions = paths.filter(p => !retained.some(old => old === p || old.endsWith('/') && p.startsWith(old))).sort();
  const result = validatePackageInputs({...original, inputs: [...retained, ...additions],
    optional_inputs: original.optional_inputs.filter(p => !retired.has(p))});
  admitSelectedPackageDeclarations(original, result, {...prior,currentPaths:paths});
  return result;
}

// The modern composer emits these four flat products at one real commit.
// Resolve their ordinary whole-file identities once; the existing finalizer
// still checks every registry/ledger/rebind/patch/envelope join and package role.
export function resolveFinalizeConfig(config, reader) {
  if (!Object.hasOwn(config, 'composition')) return config;
  const keys = ['version', 'selector', 'package_inputs', 'composition', 'rebind', 'new_prefix', 'sidecar_output'];
  need(config.version === 1 && same(Object.keys(config).filter(key => !['restored_read_roles', 'preparation_allowance', 'accepted_checkpoint'].includes(key)).sort(), keys.sort()),
    'Compact finalization requires exact locators and cannot mix full pins or an existing sidecar');
  need(config.composition?.path && path.posix.basename(config.composition.path) === 'selected-ledger.json',
    'Modern composition requires the committed selected-ledger.json product');
  const selected = locate(reader, config.composition), prefix = path.posix.dirname(selected.path);
  const sibling = name => locate(reader, {commit: selected.commit, path: prefix + '/' + name});
  const {composition, ...original} = config;
  return {...original, selector: locate(reader, config.selector), package_inputs: locate(reader, config.package_inputs),
    rebind: locate(reader, config.rebind), registry: sibling('authority-registry.json'),
    ledger: selected, selected_ledger: selected, patch: sibling('patch.json'), runtime_envelope: sibling('runtime-envelope.json')};
}

export function finalizeDelivery(config, reader, {acceptedCheckpoint} = {}) {
  const checkpoint = finalizationCheckpointBytes(config, reader, acceptedCheckpoint);
  config = resolveFinalizeConfig(config, reader);
  // The cumulative route uses one exact selected ledger in several roles.
  // Authenticate it once here; this snapshot cannot survive another invocation.
  const originalReader = reader;
  const snapshotIdentity = pin => JSON.stringify([pin?.commit, pin?.path, pin?.mode,
    pin?.git_blob_oid ?? pin?.blob, pin?.bytes, pin?.sha256,
    pin?.decoded_bytes, pin?.decoded_sha256, pin?.uncompressed_bytes, pin?.uncompressed_sha256]);
  const selectedIdentity = config.selected_ledger && snapshotIdentity(config.selected_ledger);
  let selectedRaw, selectedJSON;
  const read = pin => {
    if (!selectedIdentity || snapshotIdentity(pin) !== selectedIdentity) return originalReader.read(pin);
    if (selectedRaw === undefined) selectedRaw = Buffer.from(originalReader.read(pin));
    return selectedRaw;
  };
  reader = {...originalReader};
  // Inherited callbacks must keep their original receiver. Giving one this
  // wrapper would expose read/json and let it retain or mutate our snapshot.
  for (const key of Reflect.ownKeys(reader)) if (typeof reader[key] === 'function')
    reader[key] = Function.prototype.bind.call(reader[key], originalReader);
  Object.assign(reader, {read, json(pin) {
    if (!selectedIdentity || snapshotIdentity(pin) !== selectedIdentity) return originalReader.json(pin);
    if (selectedJSON === undefined) selectedJSON = JSON.parse(read(pin));
    return selectedJSON;
  }});
  need(typeof config.new_prefix === 'string' && config.new_prefix.endsWith('/')
    && safe(config.new_prefix.slice(0, -1)), 'Exact owned output prefix required');
  const originalSelector = reader.read(config.selector), selection = JSON.parse(originalSelector);
  let generatedSidecar, prior, acceptedRegistry = null;
  if (selection.additive_release !== undefined || config.sidecar_output !== undefined) {
    const hook = selection.additive_release;
    need(hook && safe(hook.path), 'Original cumulative selector hook required');
    const priorPin = reader.pin(config.selector.commit, hook.path);
    need(priorPin.bytes === hook.bytes && priorPin.sha256 === hook.sha256, 'Original selected sidecar differs');
    prior = reader.json(priorPin);
    const base = scientificNativeSelection(selection);
    need(prior.version === 2 && prior.kind === 'retained-native-additive-selection-v2' && same(prior.base_selection, base),
      'Original selected base differs');
    const pin = prior.authority_registry;
    need(pin && Number.isSafeInteger(pin.bytes) && pin.bytes > 0 ,
      'Complete accepted registry pin required');
    // Authenticate the complete accepted registry before parsing.

    acceptedRegistry = reader.json(pin);
  }
  if (config.sidecar_output !== undefined) {
    need(!config.sidecar && safe(config.sidecar_output) && path.posix.dirname(config.sidecar_output) + '/' === config.new_prefix
      && !['ownership-selection.json', 'package-inputs.json', 'package-roles.json', 'selected-delivery-expectations.json', 'preparation.json']
        .includes(path.posix.basename(config.sidecar_output)) && config.patch && config.runtime_envelope,
    'Fresh flat owned sidecar output and committed patch/envelope required');
    generatedSidecar = jsonBytes({...prior, authority_registry: config.registry, runtime_envelope: config.runtime_envelope,
      logical_asset_map: {...prior.logical_asset_map, ledger: config.selected_ledger, patch: config.patch}});
    // This is a generated output identity, never a fabricated future input pin.
    const sidecar = {path: config.sidecar_output, mode: '100644', bytes: generatedSidecar.length, sha256: digest(generatedSidecar),
      git_blob_oid: createHash('sha1').update('blob ' + generatedSidecar.length + '\0').update(generatedSidecar).digest('hex')};
    const head = reader.git('rev-parse', 'HEAD').toString().trim();
    if (reader.hasPath(head, sidecar.path)) {
      const existing = reader.pin(head, sidecar.path);
      need(existing.mode === sidecar.mode && existing.git_blob_oid === sidecar.git_blob_oid && existing.bytes === sidecar.bytes
        && existing.sha256 === sidecar.sha256, 'Generated sidecar would replace an existing committed body');
    }
    config = {...config, sidecar};
  }
  need(config.selector?.path === 'data/ownership-selection.json' && config.package_inputs?.path === '.github/package-inputs.json'
    && config.sidecar?.path.startsWith(config.new_prefix) && config.selected_ledger && config.rebind && !config.outer_roles,
  'Finalization requires original selector/package, actual sidecar/ledger/rebind and derived outer roles');
  const sidecar = generatedSidecar ? JSON.parse(generatedSidecar) : reader.json(config.sidecar), assets = sidecar.logical_asset_map;
  need(same(Object.keys(sidecar).sort(), ['authority_registry', 'base_selection', 'kind', 'logical_asset_map', 'runtime_envelope', 'version'])
    && assets && same(Object.keys(assets).sort(), ['base_manifest', 'ledger', 'owner_roster', 'patch'])
    && same(sidecar.authority_registry, config.registry) && same(assets.ledger, config.selected_ledger), 'Final sidecar authority/selected-ledger pins differ');
  need(assets.base_manifest.sha256 === selection.sha256, 'Final base manifest differs from unchanged selector');
  const baseManifest = reader.json(assets.base_manifest);
  const references = selectedDeliveryReference(selection, baseManifest, reader, config.selector.commit);
  need(assets.owner_roster.sha256 === baseManifest.original_assets?.bounds?.sha256, 'Final owner roster differs from original native bounds');
  reader.read(assets.owner_roster); // Authenticate the retained encoded alias; no decoding or graph computation.
  const selected = reader.json(config.selected_ledger), patch = reader.json(assets.patch);
  const wrapped = reader.json(sidecar.runtime_envelope), envelope = wrapped.additiveRelease ?? wrapped;
  need(typeof selection.release_id === 'string' && baseManifest.geographic_release === selection.release_id
    && hex(baseManifest.footprints_sha256, 64) && hex(baseManifest.hierarchy_sha256, 64)
    && same(envelope.base_reference, references.reference)
    && (!references.projectionPin || envelope.effective_reference?.hierarchy_sha256 === references.reference.hierarchy_sha256),
  'Final release baseline differs from original selector/native manifest or current metadata');
  need(same(selected.current_rebind, config.rebind) && patch.ledger_sha256 === config.selected_ledger.sha256
    && patch.authority_registry_sha256 === config.registry.sha256 && same(patch.base_reference, envelope.base_reference)
    && same(patch.effective_reference, envelope.effective_reference), 'Final release metadata joins differ');
  for (const [role, pin] of Object.entries(assets)) {
    const declared = envelope[role];
    need(declared?.bytes === pin.bytes && declared?.sha256 === pin.sha256
      && (declared.decoded_bytes ?? declared.bytes) === (pin.decoded_bytes ?? pin.bytes)
      && (declared.decoded_sha256 ?? declared.sha256) === (pin.decoded_sha256 ?? pin.sha256), 'Final envelope asset descriptor differs: ' + role);
  }
  const selector = finalizedSelection(originalSelector, sidecar, config.sidecar);
  const outputs = projectPackage({...config, outer_roles: [...Object.values(assets), sidecar.runtime_envelope,
    ...(references.projectionPin ? [references.projectionPin] : []),
    ...(!generatedSidecar ? [config.sidecar] : [])]}, reader, acceptedRegistry, selectedJSON);
  const projection = JSON.parse(outputs['package-roles.json']);
  if (generatedSidecar) {
    projection.paths.push({...config.sidecar, roles: ['generated final sidecar']});
    projection.paths.sort((a, b) => a.path.localeCompare(b.path));
    outputs['package-roles.json'] = jsonBytes(projection);
    outputs[path.posix.basename(config.sidecar.path)] = generatedSidecar;
  }
  // Keep the actual preparation/consumer roles above. Completed authorities
  // retain their historical corpus references in the original evidence body.
  // The current package reads only the sidecar, envelope, four assets and the
  // optional current metadata application; historical custody stays cold.
  const paths = [...new Set([config.sidecar, sidecar.runtime_envelope, ...Object.values(assets),
    ...(references.projectionPin ? [references.projectionPin] : [])].map(p => p.path))];
  const baselinePackage = reader.json(config.package_inputs);
  validatePackageInputs(baselinePackage);
  const covered = name => baselinePackage.inputs.some(p => p === name || p.endsWith('/') && name.startsWith(p));
  // This is a closed consumed-role traversal, never caller-granted write scope.
  // Absent historical roles require an exact committed restoration snapshot.
  // Finalization never emits a second copy of original role bodies.
  // Ordinary issue/PR guards separately authorize adoption into the repository.
  const restored = config.restored_read_roles;
  if (restored) need((same(Object.keys(restored).sort(), ['commit'])
      || same(Object.keys(restored).sort(), ['commit', 'paths']) && unique(restored.paths) && restored.paths.every(safe))
    && hex(restored.commit, 40)
    && typeof reader.hasPath === 'function', 'Exact committed restored read-role inventory required');
  const deriveRestorations = restored && !Object.hasOwn(restored, 'paths');
  const requested = new Set(restored?.paths ?? []), matched = new Set(), conflicts = [];
  const identity = (a, b) => a.mode === '100644' && a.mode === b.mode
    && (a.git_blob_oid ?? a.blob) === (b.git_blob_oid ?? b.blob)
    && a.bytes === b.bytes && a.sha256 === b.sha256;
  for (const pin of projection.paths.filter(p => !p.path.startsWith(config.new_prefix) || covered(p.path))) {
    try {
      const missing = typeof reader.hasPath === 'function' && !reader.hasPath(config.package_inputs.commit, pin.path);
      // Snapshot-only intent derives its closed scope from this already
      // authenticated projection, without a second author traversal.
      if (missing && deriveRestorations) requested.add(pin.path);
      if (!missing && pin.roles.length === 1 && pin.roles[0] === 'source-target physical_reproduction') {
        // packageProjection authenticated the original commit/path/body. The
        // live accepted helper remains a separate unchanged filesystem input;
        // this historical read cannot replace it or grant another role access.
        const current = reader.pin(config.package_inputs.commit, pin.path);
        need(current.mode === '100644', 'Current producer path is not ordinary');
        need(!requested.has(pin.path), 'Restoration would overwrite an existing accepted path');
        continue;
      }
      if (missing && requested.has(pin.path)) {
        const snapshot = reader.pin(restored.commit, pin.path);
        need(identity(snapshot, pin), 'Restored snapshot differs from original consumed role');
        matched.add(pin.path);
      } else {
        const original = reader.pin(config.package_inputs.commit, pin.path);
        need(identity(original, pin), 'Original consumed role differs from accepted path');
        need(!requested.has(pin.path), 'Restoration would overwrite an existing accepted path');
      }
    } catch (error) { conflicts.push({path: pin.path, reason: error.message}); }
  }
  for (const name of requested) if (!matched.has(name) && !conflicts.some(row => row.path === name))
    conflicts.push({path: name, reason: 'Unbound or non-restorable role in restoration inventory'});
  need(!conflicts.length, 'Final package role conflicts with accepted path identity: ' + JSON.stringify(conflicts));
  // The prior sidecar body was authenticated against the original selector
  // above. Its cumulative payload is superseded, not a transitive scientific
  // package input; packageProjection still retains complete custody evidence.
  const priorDeclaration = prior ? {selection,
    priorSidecarRaw: reader.read(reader.pin(config.selector.commit, selection.additive_release.path)),
    priorEntry: name => reader.descriptor(config.selector.commit, name)} : {};
  const packageInputs = appendPackageReadPaths(baselinePackage, paths, priorDeclaration);
  const expectation = JSON.parse(outputs['selected-delivery-expectations.json']);
  // Preserve the established final smoke-expectation presentation as well.
  const expectations = {version: expectation.version, selected_ledger_sha256: expectation.selected_ledger_sha256,
    cumulative_native_cells: expectation.cumulative_native_cells, cohorts: expectation.cohorts.map(c => ({original_batch_id: c.original_batch_id,
      component_ids: c.component_ids, members: c.members.map(m => ({component_id: m.component_id, target_id: m.target_id,
        disposition: m.disposition, ...(Object.hasOwn(m, 'native_rows_sha256')
          ? {native_rows_sha256: m.native_rows_sha256} : {geometry_sha256: m.geometry_sha256})}))}))};
  return {...outputs, ...(checkpoint ? {'selected-checkpoint.json': checkpoint} : {}),
    'ownership-selection.json': selector, 'package-inputs.json': orderedBytes(packageInputs),
    'selected-delivery-expectations.json': orderedBytes(expectations)};
}

export function publishFinalizedDelivery(root, destination, outputs, binding, reader, selector, resume = false) {
  const adopt = admitCanonicalCheckpoint(root, reader, selector, outputs['selected-checkpoint.json'], resume);
  const publication = publish(root, destination, outputs, binding, resume);
  adopt();
  return publication;
}

const physicalProducts = ['whole-target-support.json', 'execution-receipt.json'];
const sourceProducts = ['original-stage-inputs.json', 'cohort-intervals.json', 'cohort-config.json',
  'source-qualification.json', 'execution-receipt.json'];
function sourceBinding(raw, phase = 'source') {
  return {phase, config_sha256: digest(raw),
    program_sha256: digest(fs.readFileSync(fileURLToPath(new URL('./qualify-source-cohort.py', import.meta.url)))),
    entry_sha256: digest(fs.readFileSync(fileURLToPath(import.meta.url)))};
}
// Reuse complete local original output without repeating scientific operators.
// This validates retained custody; it does not create new scientific authority.
export function resumeSource(root, destination, config, binding, reader) {
  const physical = binding.phase === 'physical', phaseConfig = config[physical ? 'physical' : 'source'];
  const names = physical ? physicalProducts : sourceProducts;
  const receipt = JSON.parse(ordinary(root, destination + '/preparation.json'));
  // The entry hash describes the historical writer, not the scientific program.
  // Unrelated entrypoint edits do not invalidate complete original science.
  need(receipt.version === 1 && same({...receipt.binding, entry_sha256: binding.entry_sha256}, binding) &&
    same(Object.keys(receipt.outputs ?? {}).sort(), [...names].sort()), 'Source resume configuration/code/inventory differs');
  const products = {};
  for (const name of names) {
    const raw = ordinary(root, destination + '/' + name), pin = receipt.outputs[name];
    need(pin.bytes === raw.length && pin.sha256 === digest(raw), 'Source resumed product changed: ' + name);
    products[name] = raw;
  }
  need(Array.isArray(phaseConfig?.inputs) && phaseConfig.inputs.length > 0, 'Source resume needs original input inventory');
  for (const pin of [...phaseConfig.inputs, ...(physical ? [] : [phaseConfig.physical_reproducer])]) reader.read({...pin, mode: '100644'});
  const execution = JSON.parse(products['execution-receipt.json']);
  const qualified = physical ? execution : JSON.parse(products['source-qualification.json']);
  need(execution.complete === true && execution.program?.sha256 === binding.program_sha256 &&
    qualified.fresh_admission?.config_sha256 === digest(jsonBytes(phaseConfig)), 'Source original execution binding differs');
  need(Array.isArray(execution.outputs) && execution.outputs.length === names.length - 1 &&
    same(execution.outputs.map(pin => pin.path).sort(), names.filter(name => name !== 'execution-receipt.json')
      .map(name => destination + '/' + name).sort()), 'Source original output roster differs');
  for (const pin of execution.outputs) {
    const raw = products[pin.path.slice(destination.length + 1)];
    need(raw && raw.length === pin.bytes && digest(raw) === pin.sha256, 'Source original execution product differs');
  }
  return publish(root, destination, products, receipt.binding, true);
}

// The source probe has one data-configured scientific implementation. Admission
// and exclusive publication stay in this existing delivery entry point.
export async function sourceCohort(config, reader, root, destination, phase = 'source') {
  need(['source', 'physical'].includes(phase), 'Unknown scientific delivery phase');
  const phaseConfig = config[phase];
  need(same(Object.keys(config).filter(key => !['preparation_allowance','processing_allowance'].includes(key)).sort(),
    ['runtime_inventory', phase, 'version'].sort()) && config.version === 1 && phaseConfig?.version === 1,
    'Explicit source configuration and runtime inventory required');
  const runtime = config.runtime_inventory;
  need(runtime && same(Object.keys(runtime).sort(), ['files', 'python']) && Array.isArray(runtime.files)
    && runtime.files.length > 0 && unique(runtime.files.map(pin => pin.path))
    && runtime.python?.bytes > 0 && runtime.files.some(pin => same(pin, runtime.python)), 'Complete pinned source runtime inventory required');
  for (const pin of runtime.files) {
    need(pin && same(Object.keys(pin).sort(), ['bytes', 'path', 'sha256']) && path.isAbsolute(pin.path)
      && Number.isSafeInteger(pin.bytes) && pin.bytes >= 0 && hex(pin.sha256, 64), 'Ordinary installed runtime pin required');
  }
  const helper = fileURLToPath(new URL('./qualify-source-cohort.py', import.meta.url));
  const helperRaw = fs.readFileSync(helper), sourceRaw = jsonBytes(phaseConfig);
  const runtimeIdentity = pin => {
    const resolved = fs.realpathSync(pin.path), before = fs.statSync(resolved);
    need(before.isFile() && before.size === pin.bytes, 'Installed source runtime size differs');
    const hash = createHash('sha256'), chunk = Buffer.alloc(1048576), fd = fs.openSync(resolved, 'r');
    let bytes = 0;
    try { for (let n; (n = fs.readSync(fd, chunk, 0, chunk.length, null));) { bytes += n; hash.update(chunk.subarray(0, n)); } }
    finally { fs.closeSync(fd); }
    const after = fs.statSync(resolved);
    need(bytes === pin.bytes && hash.digest('hex') === pin.sha256 && fs.realpathSync(pin.path) === resolved
      && ['dev', 'ino', 'size', 'mtimeMs', 'ctimeMs'].every(key => before[key] === after[key]), 'Installed source runtime identity differs');
    return {path: pin.path, resolved, bytes, sha256: pin.sha256};
  };
  const identities = runtime.files.map(runtimeIdentity);
  const stagingParent = '.cache/delivery-handoff';
  admitDestination(root, stagingParent + '/source-staging', false);
  fs.mkdirSync(path.join(root, stagingParent), {recursive: true});
  const staging = fs.mkdtempSync(path.join(root, stagingParent, 'source-'));
  const stagingIdentity = [];
  for (let current = staging;; current = path.dirname(current)) {
    const stat = fs.lstatSync(current);
    need(stat.isDirectory() && fs.realpathSync(current) === current, 'Nonordinary producer staging ancestor');
    stagingIdentity.push({path: current, dev: stat.dev, ino: stat.ino});
    if (current === root) break;
    need(current.startsWith(root + path.sep), 'Producer staging escaped owned root');
  }
  const discardStaging = () => {
    for (const identity of stagingIdentity) {
      const stat = fs.lstatSync(identity.path, {throwIfNoEntry: false});
      need(stat?.isDirectory() && fs.realpathSync(identity.path) === identity.path
        && stat.dev === identity.dev && stat.ino === identity.ino,
      'Producer staging identity changed; cleanup refused at ' + identity.path);
    }
    fs.rmSync(staging, {recursive: true, force: true});
  };
  let completed = false;
  try {
    const sourceFile = path.join(staging, 'source-config.json'), admissionFile = path.join(staging, 'admission.json');
    const admission = {version: 1, program_sha256: digest(helperRaw), config_sha256: digest(sourceRaw), runtime_files: runtime.files};
    fs.writeFileSync(sourceFile, sourceRaw, {flag: 'wx'});
    fs.writeFileSync(admissionFile, jsonBytes(admission), {flag: 'wx'});
    const output = path.join(staging, 'products'), started = performance.now();
    // Python owns cooperative feature/input/time/output checks. This entry does
    // not claim a hard deadline or process-tree supervisor it does not implement.
    execFileSync(runtime.python.path, ['-I', '-B', helper, '--phase', phase, '--repo', root, '--config', sourceFile,
      '--admission', admissionFile, '--output', output, '--publication-prefix', destination], {cwd: root, env: environment(),
      stdio: ['ignore', 'ignore', 'pipe'], maxBuffer: 131072});
    for (const pin of runtime.files) runtimeIdentity(pin);
    need(fs.readFileSync(helper).equals(helperRaw), 'Source helper changed during execution');
    const names = phase === 'source' ? sourceProducts : physicalProducts;
    need(same(fs.readdirSync(output).sort(), [...names].sort()), 'Incomplete or foreign source output inventory');
    const products = Object.fromEntries(names.map(name => [name, ordinary(root, path.relative(root, path.join(output, name)))]));
    completed = true;
    return {products, retained_staging: path.relative(root, staging),
      discard_staging: discardStaging,
      observation: {elapsed_seconds: (performance.now() - started) / 1000,
      runtime_inventory: identities, limits: ['Scientific checks are cooperative boundaries, not hard process-tree enforcement.',
        phase === 'physical' ? 'Original physical source-relative support is not native, owner-zero, factual or selected-output acceptance.'
          : 'Source prerequisites are not physical, native, owner-zero or selected-output acceptance.']}};
  } finally { if (!completed) discardStaging(); }
}

// Completed producer bodies remain available if the existing outer writer refuses.
// This is not a completed outer publication or an automatic replay/resume route.
export function publishCompletedSource(root, destination, result, binding, resume, reader) {
  let publication;
  try { publication = publish(root, destination, result.products, binding, resume); }
  catch (error) {
    throw new Error(error.message + '; completed producer staging retained at ' + result.retained_staging
      + '; outer publication incomplete', {cause: error});
  }
  try { result.discard_staging(); }
  catch (error) {
    throw new Error('Outer publication complete at ' + destination + '; producer staging cleanup failed: ' + error.message, {cause: error});
  }
  return publication;
}

// Preparation only: the reviewed family list declares conservative negatives,
// never positive owners or an applicability exception. The native constructor
// still authenticates the selected source/owner joins and qualifies every cell.
export function sourceTerritorialExclusions(evidence, families, reader, compact = false) {
  need(typeof compact === 'boolean', 'Explicit boolean compact territorial exclusions required');
  need(evidence.territorial_exclusion_sources === undefined, 'Territorial exclusion source references are already prepared');
  need(unique(families), 'Explicit unique nonempty territorial exclusion families required');
  need([1, 2].includes(evidence.version) && evidence.adopted_provider_families === undefined,
    'Territorial exclusion preparation requires original catalogue sources');
  const catalogue = reader.json(evidence.catalogue), stages = reader.json(evidence.physical_input);
  need(catalogue.version === 1 && Array.isArray(catalogue.products)
    && unique(catalogue.products.map(p => p.key)), 'Complete unique original catalogue required');
  need(Array.isArray(stages) && unique(stages.map(s => s.target)), 'Unique whole physical source inputs required');
  need(Array.isArray(evidence.targets) && unique(evidence.targets.map(t => t.id))
    && Array.isArray(evidence.families) && unique(evidence.families.map(f => f.source_id)),
  'Unique positive source members and families required');
  const positive = new Map(evidence.families.map(f => [f.source_id, f]));
  need(families.every(id => !positive.has(id)), 'Negative source family is also a positive family');
  const loaded = new Map();
  const load = id => {
    if (loaded.has(id)) return loaded.get(id);
    const record = catalogue.products.find(p => p.key === id);
    need(record && Number.isSafeInteger(record.feature_count) && record.feature_count > 0
      && Number.isSafeInteger(record.original_bytes) && record.original_bytes > 0
      && hex(record.original_sha256, 64) && Array.isArray(record.parts) && record.parts.length > 0,
    'Missing complete original territorial source family: ' + id);
    const supplied = positive.get(id)?.parts;
    need(!supplied || supplied.length === record.parts.length, 'Incomplete positive source family');
    let offset = 0;
    const pins = [], pieces = record.parts.map((part, ordinal) => {
      need(part.ordinal === ordinal && part.offset === offset && safe(part.path)
        && Number.isSafeInteger(part.bytes) && part.bytes > 0 && hex(part.sha256, 64)
        && Number.isSafeInteger(part.uncompressed_bytes) && part.uncompressed_bytes > 0
        && hex(part.uncompressed_sha256, 64), 'Malformed original territorial source part');
      offset += part.uncompressed_bytes;
      need(Number.isSafeInteger(offset) && offset <= record.original_bytes, 'Original source parts exceed complete body');
      const pin = supplied?.[ordinal] ?? {...reader.pin(evidence.catalogue.commit, part.path),
        decoded_bytes: part.uncompressed_bytes, decoded_sha256: part.uncompressed_sha256};
      need(pin.path === part.path && pin.bytes === part.bytes && pin.sha256 === part.sha256
        && pin.decoded_bytes === part.uncompressed_bytes && pin.decoded_sha256 === part.uncompressed_sha256,
      'Territorial source pin differs from original catalogue');
      const decoded = gunzipSync(reader.read(pin), {maxOutputLength: part.uncompressed_bytes});
      need(decoded.length === part.uncompressed_bytes && digest(decoded) === part.uncompressed_sha256,
        'Decoded original territorial source differs');
      pins.push(pin); return decoded;
    });
    const raw = Buffer.concat(pieces);
    need(raw.length === record.original_bytes && digest(raw) === record.original_sha256,
      'Incomplete whole original territorial source');
    const product = JSON.parse(raw);
    need(product.type === 'FeatureCollection' && product.features?.length === record.feature_count
      && unique(product.features.map(f => f.properties?.shapeID)), 'Incomplete or duplicate original source feature identities');
    const features = product.features.map((feature, ordinal) => ({source_id: id + ':' + feature.properties.shapeID,
      feature_ordinal: ordinal, geometry_sha256: digest(jsonBytes(feature.geometry)),
      geometry: feature.geometry, bounds: coordinateBounds(feature.geometry)}));
    const result = {source_family: id, original_bytes: raw.length, original_sha256: digest(raw),
      feature_count: features.length, parts: pins, features};
    loaded.set(id, result); return result;
  };
  const negatives = families.map(load), intersect = (a, b) =>
    a[0] <= b[2] && b[0] <= a[2] && a[1] <= b[3] && b[1] <= a[3];
  const byGeometry = new Map();
  if (compact) for (const family of negatives) for (const feature of family.features) {
    const matches = byGeometry.get(feature.geometry_sha256) ?? [];
    matches.push(feature); byGeometry.set(feature.geometry_sha256, matches);
  }
  const bindings = [];
  const targets = evidence.targets.map(target => {
    need(positive.has(target.source_family) && Number.isSafeInteger(target.pixelIndex) && target.pixelIndex > 0,
      'Missing positive source family or target owner');
    const original = load(target.source_family).features.find(f => f.source_id === target.id);
    const stage = stages.find(s => s.target === target.id);
    need(original && stage && same(stage.consumed?.geometry, original.geometry)
      && stage.consumed?.properties?.shapeID === target.id.slice(target.source_family.length + 1)
      && stage.selected?.id === (target.target_id ?? target.id)
      && same(stage.selected.geometry, target.base_geometry), 'Whole original source or selected target join differs');
    need(target.territorial_exclusions === undefined || Array.isArray(target.territorial_exclusions),
      'Malformed existing territorial exclusions');
    const exclusions = [...(target.territorial_exclusions ?? [])], selected = [], disjoint = [];
    for (const family of negatives) for (const feature of family.features) {
      const identity = {source_family: family.source_family, source_id: feature.source_id,
        feature_ordinal: feature.feature_ordinal, geometry_sha256: feature.geometry_sha256};
      if (!feature.bounds.some(a => original.bounds.some(b => intersect(a, b)))) { disjoint.push(feature.source_id); continue; }
      selected.push({...identity, negative_ordinal: exclusions.length}); exclusions.push(feature.geometry);
    }
    bindings.push({source_id: target.id, target_id: target.target_id ?? target.id, pixelIndex: target.pixelIndex,
      prior_exclusions: target.territorial_exclusions?.length ?? 0, exclusions: selected, disjoint_source_ids: disjoint});
    const operands = compact ? exclusions.map((geometry, negative_ordinal) => {
      const matches = byGeometry.get(digest(jsonBytes(geometry))) ?? [];
      // An existing manual operand is compacted only on one exact whole-original
      // identity. Ambiguous or unrelated inline geometry stays literal.
      if (matches.length !== 1 || !same(matches[0].geometry, geometry)) return geometry;
      const {source_id, feature_ordinal, geometry_sha256} = matches[0];
      return {source_id, feature_ordinal, negative_ordinal, geometry_sha256};
    }) : exclusions;
    return {...target, territorial_exclusions: operands};
  });
  const sources = compact ? {territorial_exclusion_sources: negatives.map(family =>
    ({source_id: family.source_family, parts: family.parts}))} : {};
  return {evidence: {...evidence, ...sources, targets}, provenance: {version: 1, kind: 'whole-original-territorial-exclusions-v1',
    catalogue: evidence.catalogue, physical_input: evidence.physical_input, negative_families: families,
    complete_sources: [...loaded.values()].map(({features, ...family}) => family), targets: bindings,
    limits: ['Reviewed negative scope is conservative disagreement, not legal sovereignty or an applicability exception.',
      'Whole originals are unchanged; only disjoint complete bounds omit an operand. No requested native cell is removed.',
      'Native source, owner, physical, geometry and full-scope qualification remain required.']}};
}

// Fill only the accepted baseline block of ordinary source evidence. Scientific
// claims stay explicit; this metadata preparation does not qualify their support.
// In particular, the normative manifest descriptor is not a Git custody pin.
export async function sourceEvidence(config, reader) {
  need(config.version === 1 && (config.source_evidence?.version === 1
    && config.source_evidence.kind === 'source-target-native-evidence-v1'
    || config.source_evidence?.version === 2 && config.source_evidence.kind === 'source-target-native-evidence-v2'
    || config.source_evidence?.version === 3 && config.source_evidence.kind === 'source-target-native-evidence-v3'),
  'Explicit ordinary source evidence required');
  if (config.source_evidence.version === 2) reader.read(config.source_evidence.dated_land_support);
  if (config.source_evidence.version === 3) reader.read(config.source_evidence.revised_source_adoption);
  if (config.source_evidence.territorial_applicability !== undefined) reader.read(config.source_evidence.territorial_applicability);
  if (config.source_evidence.adopted_provider_families !== undefined) reader.read(config.source_evidence.adopted_provider_families);
  if (config.source_evidence.canonical_seam_views !== undefined) reader.read(config.source_evidence.canonical_seam_views);
  const {locate} = await import('./delivery-handoff-advance.mjs');
  const selectorPin = locate(reader, config.selector);
  need(selectorPin.path === 'data/ownership-selection.json', 'Original accepted selector locator required');
  const selection = reader.json(selectorPin), hook = selection.additive_release;
  need(hook && same(Object.keys(hook).sort(), ['bytes', 'path', 'sha256']), 'Existing cumulative selection required');
  const sidecarPin = reader.pin(selectorPin.commit, hook.path);
  need(sidecarPin.bytes === hook.bytes && sidecarPin.sha256 === hook.sha256, 'Original selected sidecar differs');
  const sidecar = reader.json(sidecarPin), base = scientificNativeSelection(selection);
  need(sidecar.version === 2 && sidecar.kind === 'retained-native-additive-selection-v2'
    && same(sidecar.base_selection, base), 'Original selected base differs');
  const assets = sidecar.logical_asset_map;
  need(assets && same(Object.keys(assets).sort(), ['base_manifest', 'ledger', 'owner_roster', 'patch']),
    'Complete prior logical assets required');
  const wrapped = reader.json(sidecar.runtime_envelope), envelope = wrapped.additiveRelease ?? wrapped;
  need(envelope.version === 2 && envelope.kind === 'retained-native-base-plus-delta-v2', 'Existing v2 runtime envelope required');
  for (const [role, pin] of Object.entries(assets)) {
    const declared = envelope[role];
    need(declared?.bytes === pin.bytes && declared?.sha256 === pin.sha256
      && (declared.decoded_bytes ?? declared.bytes) === (pin.decoded_bytes ?? pin.bytes)
      && (declared.decoded_sha256 ?? declared.sha256) === (pin.decoded_sha256 ?? pin.sha256),
    'Prior envelope asset binding differs: ' + role);
  }
  const manifest = reader.json(assets.base_manifest);
  const selectedManifest = reader.pin(selectorPin.commit, selection.manifest_path);
  need(selectedManifest.sha256 === selection.sha256 && assets.base_manifest.sha256 === selection.sha256
    && selectedManifest.bytes === assets.base_manifest.bytes && selection.method === manifest.method,
  'Original selected native manifest/method differs');
  const contractKeys = ['size', 'coordinateBits', 'method', 'native_latitudes', 'hierarchy_sha256', 'original_assets'];
  need(contractKeys.every(key => Object.hasOwn(manifest, key)), 'Complete original native contract required');
  const native_contract = Object.fromEntries(contractKeys.map(key => [key, manifest[key]]));
  const references = qualifiedDeliveryReference(selection, manifest, reader, selectorPin.commit, assets.owner_roster);
  need((same(envelope.base_reference, references.native) || same(envelope.base_reference, references.reference))
    && (!references.projectionPin || envelope.effective_reference?.hierarchy_sha256 === envelope.base_reference.hierarchy_sha256)
    && manifest.geographic_release === selection.release_id
    && hex(manifest.footprints_sha256, 64) && hex(manifest.hierarchy_sha256, 64),
  'Original selected base reference differs');
  need(assets.owner_roster.sha256 === manifest.original_assets?.bounds?.sha256,
    'Original selected owner asset differs');
  const latitude = manifest.native_latitudes;
  const latitudePin = locate(reader, {commit: latitude.commit, path: latitude.path});
  need(latitudePin.bytes === latitude.bytes && latitudePin.sha256 === latitude.sha256,
    'Original native latitude body differs');
  const native_latitudes = {...latitudePin, decoded_bytes: latitude.decoded_bytes, decoded_sha256: latitude.decoded_sha256};
  // Authenticate both encoded and decoded custody without promoting their Git
  // metadata into the literal normative contract or replaying native science.
  for (const [role, pin] of Object.entries({native_latitudes, owner_roster: assets.owner_roster})) {
    const raw = reader.read(pin);
    need(Number.isSafeInteger(pin.decoded_bytes) && pin.decoded_bytes > 0
      && hex(pin.decoded_sha256, 64), 'Bounded decoded baseline identity required: ' + role);
    const decoded = gunzipSync(raw, {maxOutputLength: pin.decoded_bytes});
    need(decoded.length === pin.decoded_bytes && digest(decoded) === pin.decoded_sha256,
      'Decoded baseline identity differs: ' + role);
  }
  const derived = {native_contract, native_latitudes, owner_roster: assets.owner_roster, base_reference: references.native};
  for (const [key, value] of Object.entries(derived))
    need(!Object.hasOwn(config.source_evidence, key) || same(config.source_evidence[key], value),
      'Supplied source evidence changes accepted baseline: ' + key);
  const prepared = {...config.source_evidence, ...derived};
  need(config.compact_territorial_exclusions === undefined || typeof config.compact_territorial_exclusions === 'boolean',
    'Explicit boolean compact territorial exclusions required');
  need(!config.compact_territorial_exclusions || config.territorial_exclusion_families !== undefined,
    'Compact territorial exclusions require reviewed negative families');
  if (config.territorial_exclusion_families === undefined) return {'source-evidence.json': jsonBytes(prepared)};
  const handoff = sourceTerritorialExclusions(prepared, config.territorial_exclusion_families, reader, config.compact_territorial_exclusions ?? false);
  return {'source-evidence.json': jsonBytes(handoff.evidence),
    'territorial-exclusion-provenance.json': jsonBytes(handoff.provenance)};
}

// Narrow only a retained diagnostic's positive request. Whole source operands
// remain in its original pin; surviving target records change only coverage rows.
// This preparation never substitutes for the subsequent native constructor.
export function supportedInputs(config, reader) {
  need(config?.version === 1 && Object.keys(config).every(key =>
    ['version', 'diagnostic', 'original_patch', 'prior_holds'].includes(key)), 'Explicit supported-input locators required');
  const diagnosticPin = locate(reader, config.diagnostic), diagnostic = reader.json(diagnosticPin);
  need(diagnostic?.version === 1 && diagnostic.kind === 'source-target-native-diagnostic-v1'
    && same(Object.keys(diagnostic.original_pins ?? {}).sort(), ['native_patch', 'source_evidence']),
  'Retained native diagnostic required');
  const pins = diagnostic.original_pins, source = reader.json(pins.source_evidence), patch = reader.json(pins.native_patch);
  need([1, 2, 3].includes(source.version) && source.kind === `source-target-native-evidence-v${source.version}`
    && same(source.native_contract, diagnostic.native_contract)
    && diagnostic.rule_sha256 === digest(jsonBytes({version: 1, kind: 'source-target-native-rule-v1', ...pins})),
  'Diagnostic source/patch binding differs');
  const size = source.native_contract?.size;
  need(size === 262166, 'Normative native grid extent required');
  const append = (runs, run) => {
    const previous = runs.at(-1);
    if (previous?.[1] === run[0] && same(previous.slice(2), run.slice(2))) previous[1] = run[1];
    else runs.push([...run]);
  };
  const rows = (value, reasons = false) => {
    need(Array.isArray(value), 'Complete native rows required');
    let previousY = -1;
    return value.map(row => {
      need(row && same(Object.keys(row).sort(), ['runs', 'y']) && Number.isSafeInteger(row.y)
        && row.y > previousY && row.y < size && Array.isArray(row.runs) && row.runs.length,
      'Invalid or duplicate native row');
      previousY = row.y; let end = 0; const runs = [];
      for (const run of row.runs) {
        need(Array.isArray(run) && run.length === (reasons ? 4 : 3)
          && run.slice(0, 3).every(Number.isSafeInteger) && run[0] >= end && run[1] > run[0]
          && run[1] <= size && run[2] > 0 && (!reasons || typeof run[3] === 'string' && run[3].length),
        'Invalid, overlapping or foreign native interval');
        end = run[1]; append(runs, run);
      }
      return {y: row.y, runs};
    });
  };
  const partition = (decisions, accepted) => decisions.map(({y, runs}) => {
    const selected = [];
    for (const run of runs) if ((run[3] === 'assigned_cells') === accepted) append(selected, run.slice(0, 3));
    return {y, runs: selected};
  }).filter(row => row.runs.length);
  const count = value => value.reduce((sum, row) => sum + row.runs.reduce((n, run) => n + run[1] - run[0], 0), 0);
  const requested = rows(diagnostic.requested_rows), decisions = rows(diagnostic.decision_rows, true);
  const supported = rows(diagnostic.supported_rows), held = rows(diagnostic.held_rows);
  need(same(requested, rows(patch.rows)) && same(supported, partition(decisions, true))
    && same(held, partition(decisions, false)) && same(requested, rows(decisions.map(({y, runs}) =>
      ({y, runs: runs.map(run => run.slice(0, 3))})))), 'Diagnostic requested/supported/held partition differs');
  need(requested.length && count(requested) === diagnostic.requested_cells && count(supported) === diagnostic.supported_cells
    && count(held) === diagnostic.held_cells, 'Diagnostic counts differ from its complete rows');
  const originalPin = config.original_patch ? locate(reader, config.original_patch) : pins.native_patch;
  const original = config.original_patch ? rows(reader.json(originalPin).rows) : requested;
  const priorPin = config.prior_holds ? locate(reader, config.prior_holds) : null;
  const prior = priorPin ? rows(reader.json(priorPin).rows, true) : [];
  need(prior.every(row => row.runs.every(run => run[3] !== 'assigned_cells')), 'Prior hold cannot claim assignment');
  const maps = [original, decisions, prior].map(value => new Map(value.map(row => [row.y, row.runs])));
  const ys = [...new Set(maps.flatMap(map => [...map.keys()]))].sort((a, b) => a - b);
  const narrowed = [], withheld = [], owners = new Map(); let priorNativeHeld = 0;
  for (const y of ys) {
    const lists = maps.map(map => map.get(y) ?? []), offsets = [0, 0, 0];
    const cuts = [...new Set(lists.flatMap(runs => runs.flatMap(run => run.slice(0, 2))))].sort((a, b) => a - b);
    const keep = [], holds = [];
    for (let i = 0; i + 1 < cuts.length; i++) {
      const start = cuts[i], end = cuts[i + 1];
      const spans = lists.map((runs, j) => {
        while (offsets[j] < runs.length && runs[offsets[j]][1] <= start) offsets[j]++;
        const run = runs[offsets[j]]; return run?.[0] <= start ? run : null;
      });
      const [full, native, previous] = spans;
      if (!spans.some(Boolean)) continue;
      need(full && (native || previous) && spans.every(run => !run || run[2] === full[2]),
        'Original scope is not exactly diagnostic plus prior holds');
      const owner = full[2], cells = end - start;
      const record = owners.get(owner) ?? {owner, original_cells: 0, supported_cells: 0, held_cells: 0};
      record.original_cells += cells;
      if (native?.[3] === 'assigned_cells' && !previous) {
        append(keep, [start, end, owner]); record.supported_cells += cells;
      } else {
        const nativeHeld = native && native[3] !== 'assigned_cells';
        append(holds, [start, end, owner, nativeHeld ? native[3] : previous[3]]); record.held_cells += cells;
        if (nativeHeld && previous) priorNativeHeld += cells;
      }
      owners.set(owner, record);
    }
    if (keep.length) narrowed.push({y, runs: keep});
    if (holds.length) withheld.push({y, runs: holds});
  }
  const byOwner = value => {
    const result = new Map();
    for (const {y, runs} of value) for (const run of runs) {
      const ownerRows = result.get(run[2]) ?? []; result.set(run[2], ownerRows);
      if (ownerRows.at(-1)?.y !== y) ownerRows.push({y, runs: []});
      append(ownerRows.at(-1).runs, run);
    }
    return result;
  };
  const requestedOwners = byOwner(requested), supportedOwners = byOwner(narrowed), seen = new Set(), classes = new Map();
  need(Array.isArray(source.targets) && source.targets.length, 'Complete original source targets required');
  const targets = [];
  for (const target of source.targets) {
    need(typeof target.id === 'string' && target.id && !seen.has(target.id)
      && Number.isSafeInteger(target.pixelIndex) && target.pixelIndex > 0,
      'Duplicate or foreign source target'); seen.add(target.id);
    let coverage;
    if (target.coverage_rows !== undefined) {
      const ownerRows = rows(target.coverage_rows.map(({y, runs}) => ({y, runs: runs.map(run => {
        need(Array.isArray(run) && run.length === 3
          && ['mapped_land_support', 'mapped_inland_water_support'].includes(run[2]), 'Invalid original coverage class');
        return [run[0], run[1], target.pixelIndex, run[2]];
      })})), true);
      need(same(rows(ownerRows.map(({y, runs}) => ({y, runs: runs.map(run => run.slice(0, 3))}))), requestedOwners.get(target.pixelIndex))
        && (!classes.has(target.pixelIndex) || same(classes.get(target.pixelIndex), ownerRows)),
      'Original coverage rows differ from complete requested owner');
      classes.set(target.pixelIndex, ownerRows);
      const classRows = new Map(ownerRows.map(row => [row.y, row.runs]));
      coverage = (supportedOwners.get(target.pixelIndex) ?? []).map(({y, runs}) => {
        const result = [], originalClasses = classRows.get(y); let offset = 0;
        for (const [start, end] of runs) {
          while (originalClasses[offset][1] <= start) offset++;
          for (let j = offset; j < originalClasses.length && originalClasses[j][0] < end; j++) {
            const [a, b, , kind] = originalClasses[j]; append(result, [Math.max(a, start), Math.min(b, end), kind]);
          }
        }
        return {y, runs: result};
      });
    }
    if (supportedOwners.has(target.pixelIndex)) targets.push(coverage ? {...target, coverage_rows: coverage} : target);
  }
  need([...requestedOwners.keys()].every(owner => source.targets.some(target => target.pixelIndex === owner)),
    'Missing requested source owner');
  const accounting = {version: 1, diagnostic: diagnosticPin, original_patch: originalPin,
    ...(priorPin ? {prior_holds: priorPin} : {}), original_inputs: pins,
    original_cells: count(original), supported_cells: count(narrowed), held_cells: count(withheld),
    native_requested_cells: diagnostic.requested_cells, native_supported_cells: diagnostic.supported_cells,
    native_held_cells: diagnostic.held_cells, prior_held_cells: count(prior), prior_already_native_held_cells: priorNativeHeld,
    owners: [...owners.values()].sort((a, b) => a.owner - b.owner),
    limits: ['Preparation only. Exact emitted source and patch still require genuine native authority.',
      'Original source, physical and negative operands remain pinned; only positive coverage and wholly held owners are narrowed.']};
  return {'source-evidence.json': jsonBytes({...source, targets}), 'native-patch.json': jsonBytes({rows: narrowed}),
    'held-original.json': jsonBytes({rows: withheld}), 'original-scope-partition.json': jsonBytes(accounting)};
}

// Execute the existing modern constructor or its admitted read-only diagnostic,
// rather than authoring a country wrapper. Only qualification emits authority.
export async function nativeAuthority(config, reader, root, diagnostic = false) {
  need(typeof diagnostic === 'boolean' && same(Object.keys(config).filter(k=>k!=='preparation_allowance').sort(), ['native_patch', 'source_evidence', 'version'])
    && config.version === 1, 'Explicit native-authority inputs required');
  const flow = await import('./delivery-handoff-advance.mjs');
  const inputs = {source_evidence: config.source_evidence, native_patch: config.native_patch};
  const pins = diagnostic
    ? Object.fromEntries(Object.entries(inputs).map(([role, locator]) => [role, flow.locate(reader, locator)])) : null;
  if (!diagnostic) for (const locator of Object.values(inputs))
    reader.descriptor(locator?.commit, locator?.path);
  const authorityReader = flow.deliveryAuthorityReader(root, reader);
  const started = performance.now();
  let result, products, qualifiedCells;
  if (diagnostic) {
    const {diagnoseSourceTargetNativeAuthority} = await import('../coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs');
    const binding = {version: 1, kind: 'source-target-native-custody-v1', ...pins};
    const preimage = {...binding, kind: 'source-target-native-rule-v1'};
    result = diagnoseSourceTargetNativeAuthority(authorityReader, preimage, binding);
    products = {'native-diagnostic.json': jsonBytes(result)};
  } else {
    const owned=await flow.constructOriginalAuthorityStored(authorityReader,inputs,{directory:os.tmpdir()});
    let failed=false;try{result=owned.result;
    const {canonicalNativeJsonChunks}=await import('./native-patch-store.mjs');
    need(Array.isArray(result.ledger_rows) && result.ledger_rows.length > 0
      && same(result.component_ids, result.ledger_rows.map(row => row.component_id)), 'Complete modern constructor rows required');
    products = {...result.products, 'constructor-result.json': stageProduct(canonicalNativeJsonChunks({version: 1,
      kind: 'existing-source-target-native-constructor-result', inputs,
      component_ids: result.component_ids, rule_sha256: result.rule_sha256, ledger_rows: result.ledger_rows,
      limitations: result.limitations,
      ...(Object.hasOwn(result,'physical_context_hits') ? {physical_context_hits: result.physical_context_hits} : {}),
      ...(Object.hasOwn(result,'split_source_competitors') ? {split_source_competitors: result.split_source_competitors} : {}),
      ...(Object.hasOwn(result,'territorial_contacts') ? {territorial_contacts: result.territorial_contacts} : {})}))};
    qualifiedCells=result.ledger_rows.reduce((n,row)=>n+row.native_cells,0);
    }catch(error){failed=true;try{closeOwnedProducts(products);}catch{}throw error;}
    finally{try{owned.close();}catch(error){if(!failed){try{closeOwnedProducts(products);}catch{}throw error;}}}
  }
  return {products, observation: {elapsed_seconds: (performance.now() - started) / 1000,
    ...(diagnostic ? {requested_cells: result.requested_cells, supported_cells: result.supported_cells, held_cells: result.held_cells}
      : {qualified_cells: qualifiedCells}),
    limits: ['Original source/physical producers are not replayed.', diagnostic
      ? 'Diagnostic screening produces no authority, current-owner-zero or selected-output acceptance.'
      : 'Constructor qualification is not actual current-owner-zero or final selected-output acceptance.']}};
}

async function main(args) {
  const [phase, configFile, destination, ...flags] = args;
  if (phase === 'materialize') {
    need(configFile && destination && flags.every(f => f === '--resume') && flags.length <= 1,
      'Use materialize CONFIG DESTINATION [--resume]');
    need(!process.execArgv.length && !process.env.NODE_OPTIONS?.trim() && !process.env.NODE_PATH?.trim(), 'Plain Node launch required');
    const root = fs.realpathSync(process.cwd()), raw = ordinary(root, configFile), config = JSON.parse(raw);
    need(config.version === 1, 'Explicit materialization configuration required');
    const reader = pinReader(root); const flow = await import('./delivery-handoff-advance.mjs');
    const pin = flow.locate(reader, config.recipe_index), index = reader.json(pin), plan = index.acquisition_plan;
    need(index.version === 1 && plan?.products?.length, 'Completed recipe index with acquisition plan required');
    const products = {'materialized-inputs.json': jsonBytes({version: 1, kind: 'authenticated-delivery-inputs',
      recipe_index: pin, identities: [...new Set(plan.products.map(p => p.identity))], status: 'complete'})};
    const publishComplete = admitPublication(root, destination, products, {phase, config_sha256: digest(raw)}, flags.includes('--resume'));
    const started = performance.now();
    const result = await flow.acquireDeliveryInputs(plan, root, {token: '', execute: flow.deliveryAcquisitionExecute()});
    console.log(JSON.stringify({...publishComplete(), acquisition: result, acquisition_ms: performance.now() - started}));
    return;
  }
  need(['reference-metadata', 'source', 'physical', 'source-evidence', 'native-authority', 'native-diagnostic', 'supported-inputs', 'requests', 'native-requests', 'retain', 'rebind-operating', 'rebind-certificate', 'compose', 'package', 'finalize'].includes(phase) && configFile && destination && flags.every(f => f === '--resume') && flags.length <= 1,
    'Use prepare-delivery-handoff.mjs requests|native-requests|retain|rebind-operating|rebind-certificate|compose|package|finalize|source|physical|source-evidence|native-authority|native-diagnostic|supported-inputs|reference-metadata CONFIG DESTINATION [--resume]');
  need(!process.execArgv.length && !process.env.NODE_OPTIONS?.trim() && !process.env.NODE_PATH?.trim(), 'Plain Node launch required');
  const root = fs.realpathSync(process.cwd()); admitDestination(root, destination, flags.includes('--resume'));
  const raw = ordinary(root, configFile), config = JSON.parse(raw), reader = pinReader(root);
  need(config.version === 1, 'Versioned preparation config required');
  const binding = ['source','physical'].includes(phase) ? sourceBinding(raw,phase) : {phase, config_sha256: digest(raw)};
  if (['source','physical'].includes(phase) && flags.includes('--resume') && fs.existsSync(path.join(root, destination))) {
    console.log(JSON.stringify(resumeSource(root, destination, config, binding, reader))); return;
  }
  let outputs, observation;
  if (['source','physical'].includes(phase)) {
    const result = await sourceCohort(config, reader, root, destination, phase);
    console.log(JSON.stringify({...publishCompletedSource(root, destination, result, binding, flags.includes('--resume'), reader), observation: result.observation}));
    return;
  }
  if (['native-authority','native-diagnostic'].includes(phase)) { const result = await nativeAuthority(config, reader, root, phase === 'native-diagnostic'); outputs = result.products; observation = result.observation; }
  if (phase === 'reference-metadata') { const result = prepareReferenceMetadata(config, reader); outputs = result.products; binding.input_inventory = result.input_inventory; }
  if (phase === 'supported-inputs') outputs = supportedInputs(config, reader);
  if (phase === 'source-evidence') outputs = await sourceEvidence(config, reader);
  if (phase === 'requests') outputs = prepareRequests(config, reader);
  if (phase === 'native-requests') outputs = nativeRequests(config, reader);
  if (phase.startsWith('rebind-')) outputs = rebindCustody(config, reader, phase === 'rebind-certificate');
  if (phase === 'retain') outputs = retainProducts(config, root, reader);
  if (phase === 'compose') outputs = await composeAuthorities(config, reader);
  if (phase === 'package') outputs = packageProjection(config, reader);
  if (phase === 'finalize') {
    const token = config.accepted_checkpoint ? process.env.GH_TOKEN ?? execFileSync('gh', ['auth', 'token'],
      {encoding: 'utf8', timeout: 20000, maxBuffer: 16384}).trim() : undefined;
    const handle = await acquireFinalizationCheckpoint(config, reader, {token});
    try { outputs = finalizeDelivery(config, reader, {acceptedCheckpoint: handle}); }
    finally { if (handle) releaseAcceptedCheckpoint(handle); }
    const publication = publishFinalizedDelivery(root, destination, outputs, binding, reader, config.selector, flags.includes('--resume'));
    console.log(JSON.stringify(publication)); return;
  }
  console.log(JSON.stringify({...publishOwnedProducts(root, destination, outputs, binding, flags.includes('--resume')), ...(observation ? {observation} : {})}));
}
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) main(process.argv.slice(2)).catch(error => { console.error(error.message); process.exitCode = 1; });
