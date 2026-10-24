// Metadata preparation and explicit body acquisition. Existing
// operators, source authority and independent review remain authoritative.
import fs from 'node:fs';
import {scientificOperationSummary} from './native-ownership/scientific-operation-summary.mjs';
import os from 'node:os';
import {writeNativeByteChunks} from './native-patch-store.mjs';
import {performance} from 'node:perf_hooks';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {gunzipSync} from 'node:zlib';
import {locate, deliveryAcquisitionExecute} from './delivery-handoff-advance.mjs';
import {createAcquisition, githubTree} from './geography-prefetch.mjs';
import {admitCanonicalOutputs} from './delivery-checkpoint-finalization.mjs';
import {repairComponentKey, compareRepairComponents, nativeOnlyComponent} from '../src/native-grid.js';
import {finalBankSelection,scientificNativeSelection,originalNativeReference,validateReferenceMetadataHeader} from '../src/reference-metadata.js';
import {prepareReferenceMetadataProjection,validateReferenceMetadataProjection,referenceMetadataReader} from './selected-reference-metadata.mjs';
import {isReferenceAliasReceipt} from '../src/reference-metadata.js';
import {ImmutableReader,readSelectedGeometryBank} from './check-effective-geographic-regression.mjs';
import {validatePackageInputs, selectedCumulativePackageRoles, admitSelectedPackageDeclarations} from './package-inputs.mjs';
import {authorityRegistry, coordinateBounds, normaliseRetainedRepairLedger, compareVersionedRepairLedgers, verifyCompletedSourceTargetNativeAuthority, mergeCompletedNativePatches, verifyCurrentRebindExecution, CURRENT_REBIND_CODE} from '../coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';

const need = (ok, message) => { if (!ok) throw Error(message); };
const hex = (value, size) => typeof value === 'string' && new RegExp(`^[a-f0-9]{${size}}$`).test(value);
const canonical = value => Array.isArray(value) ? value.map(canonical) : value && typeof value === 'object'
  ? Object.fromEntries(Object.keys(value).sort().map(key => [key, canonical(value[key])])) : value;
export const jsonBytes = value => Buffer.from(JSON.stringify(canonical(value)) + '\n');
export const digest = raw => createHash('sha256').update(raw).digest('hex');
const orderedBytes = value => Buffer.from(JSON.stringify(value, null, 2) + '\n');
const same = (a, b) => jsonBytes(a).equals(jsonBytes(b));
const safe = name => typeof name === 'string' && /^[a-zA-Z0-9_./-]+$/.test(name) && !path.isAbsolute(name)
  && name.split('/').every(part => part && part !== '.' && part !== '..');
const unique = values => Array.isArray(values) && values.length > 0 && values.every(v => typeof v === 'string' && v) && new Set(values).size === values.length;
const environment = () => ({...process.env, GIT_NO_LAZY_FETCH: '1', GIT_NO_REPLACE_OBJECTS: '1', GIT_CONFIG_NOSYSTEM: '1', GIT_CONFIG_GLOBAL: '/dev/null', GIT_TERMINAL_PROMPT: '0'});

export function pinReader(root, {loadTree = githubTree,
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
    acquisition ??= createAcquisition({repo: root, execute, token: '', loadTree,
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
  need(config.version===2,'Current composition requires final-map version 2');
  return composeFinalAuthorities(config,reader);
}

function appendFinalPackageReadPaths(original, paths, plan) {
  validatePackageInputs(original);
  need(unique(paths)&&paths.every(safe),'Exact package read paths required');
  const prior=plan.priorDeclaration,retired=new Set();
  const old=prior?.selection.reference_projection;
  if(old&&!paths.includes(old.path)){
    const pin=plan.reader.pin(plan.selector.commit,old.path);
    need(pin.bytes===old.bytes&&pin.sha256===old.sha256,'Prior reference projection identity differs');
    if(original.inputs.includes(pin.path))retired.add(pin.path);
  }
  const inputs=original.inputs.filter(name=>!retired.has(name));
  inputs.push(...paths.filter(name=>!inputs.some(p=>p===name||p.endsWith('/')&&name.startsWith(p))).sort());
  return validatePackageInputs({...original,inputs,optional_inputs:original.optional_inputs.filter(name=>!retired.has(name))});
}

const finalizedAdoptions = new WeakMap();

// Final-profile preparation is deterministic current-bank editing, not a second
// qualifier. The ordinary accepted-code transition independently admits the new
// authority scope and compares every before/after word and context value.
function finalizeFinalBankDelivery(config, reader) {
  need(config.version===2 && Object.keys(config).every(key=>['version','selector','package_inputs','change_evidence','reference_projection','proposed_selector'].includes(key)),
    'Exact final-bank preparation config required');
  const selector=locate(reader,config.selector),packageInputs=locate(reader,config.package_inputs);
  need(selector.path==='data/ownership-selection.json'&&packageInputs.path==='.github/package-inputs.json', 'Canonical final-bank inputs required');
  const raw=reader.read(selector),selection=JSON.parse(raw),native=scientificNativeSelection(selection);
  need(native.method==='native-linear-evenodd-first-owner-v1', 'Explicit native selection required');
  need(selection.version===2, 'Final preparation requires an existing accepted final bank');
  if(config.proposed_selector){
    need(selection.version===2&&!config.change_evidence&&!config.reference_projection,
      'A proposed final bank already carries its complete change/reference selection');
    need(locate(reader,config.proposed_selector).path==='data/ownership-selection.json','Canonical proposed selector required');
  }
  const originalPackage=reader.read(packageInputs);validatePackageInputs(JSON.parse(originalPackage));
  const outputs={'ownership-selection.json':raw,'package-inputs.json':originalPackage};
  const adoption=new Map();
  const add=(name,bytes,previous,kind)=>{
    need(safe(name)&&Buffer.isBuffer(bytes)&&!adoption.has(name),'Distinct ordinary final-bank roles required');
    adoption.set(name,{path:name,bytes,expected:visitProduct(bytes),previous:previous?visitProduct(previous):undefined,kind});
  };
  for(const pin of [config.change_evidence,config.reference_projection].filter(Boolean)) {
    need(pin.commit&&pin.mode==='100644'&&hex(pin.git_blob_oid,40),'Complete issued final input pin required');
    add(pin.path,reader.read(pin),reader.hasPath(selector.commit,pin.path)?reader.read(reader.pin(selector.commit,pin.path)):undefined,'input');
  }
  add(packageInputs.path,originalPackage,originalPackage,'canonical');add(selector.path,raw,raw,'canonical');
  finalizedAdoptions.set(outputs,{reader,selector,package_inputs:packageInputs,adoption:[...adoption.values()],startupRequired:true,finalProfile:config,
    outputs:Object.fromEntries(Object.entries(outputs).map(([name,bytes])=>[name,visitProduct(bytes)]))});
  return outputs;
}
async function composeFinalAuthorities(config, reader) {
  const fields=['rule_preimage','source_authority','ledger','native_patch'];
  need(same(Object.keys(config).sort(),['authorities','selector','version'])&&config.version===2
    &&Array.isArray(config.authorities)&&config.authorities.length>0
    &&config.authorities.every(row=>same(Object.keys(row).sort(),[...fields].sort())), 'Complete new-only final authority groups required');
  await reader.acquire?.([config.selector,...config.authorities.flatMap(row=>fields.map(key=>row[key]))]);
  const selection=reader.json(config.selector),native=scientificNativeSelection(selection);
  need(selection.version===2,'New-only composition requires the accepted final profile');
  const manifestPin=reader.pin(config.selector.commit,native.manifest_path);
  need(manifestPin.sha256===native.sha256,'New-only composition changed the original native manifest');
  const entries=config.authorities.map(row=>{
    const rule=reader.pin(row.rule_preimage.commit,row.rule_preimage.path),binding=reader.json(row.source_authority);
    need(same(binding.native_patch,row.native_patch),'New-only native patch differs from its issued binding');
    const authority={policy_id:'retained-source-literal-additions',policy_version:1,rule_preimage:rule,rule_sha256:rule.sha256,
      source_authority:reader.pin(row.source_authority.commit,row.source_authority.path)};
    return {...authority,authority_sha256:digest(jsonBytes(authority)),completed_constructor:reader.pin(row.ledger.commit,row.ledger.path)};
  }).sort((a,b)=>a.authority_sha256.localeCompare(b.authority_sha256));
  const registry={version:1,kind:'retained-rule-authority-registry-v1',entries};authorityRegistry(registry);
  // This is only the exact new operand roster. Its original completion/science
  // is read by ordinary preparation and independently admitted by selected-joint.
  return {'authority-registry.json':jsonBytes(registry)};
}
async function proposedFinalNativeInputs(registryPin, reader, manifest) {
  const components=[],patches=[];
  if(!registryPin)return {components,patches};
  await reader.acquire?.([registryPin]);
  const registry=reader.json(registryPin),entries=[...authorityRegistry(registry).values()];
  const native=originalNativeReference(manifest),contract=Object.fromEntries(['size','coordinateBits','method','native_latitudes','hierarchy_sha256','original_assets'].map(key=>[key,manifest[key]]));
  for(const entry of entries){
    need(entry.completed_constructor,'Final-bank changes require completed native source-target custody');
    await reader.acquire?.([entry.rule_preimage,entry.source_authority,entry.completed_constructor]);
    const preimage=reader.json(entry.rule_preimage),binding=reader.json(entry.source_authority),constructed=reader.json(entry.completed_constructor);
    need(binding.kind==='source-target-native-custody-v1'&&entry.rule_sha256===digest(jsonBytes(preimage)), 'Final-bank original native rule/custody differs');
    await reader.acquire?.([binding.source_evidence,binding.native_patch]);
    const evidence=reader.json(binding.source_evidence),candidate=reader.json(binding.native_patch);
    const proof=verifyCompletedSourceTargetNativeAuthority({constructed,binding,preimage,evidence,candidate});
    need(same(evidence.base_reference,native)&&same(evidence.native_contract,contract)&&proof.original_ledger.parent_inventory===undefined,
      'Proposed final change differs from original native/source contract');
    for(const row of proof.original_ledger.rows)if(row.disposition==='assigned'){
      const component={...row,authority_sha256:entry.authority_sha256,rule_sha256:entry.rule_sha256};
      need(nativeOnlyComponent(component,value=>digest(jsonBytes(value))),'Final-bank positive changes require native cell components');components.push(component);
    }
    patches.push(candidate);
  }
  return {components,patches};
}
async function prepareProposedFinalBank({plan,selection,manifest,previous,originalIndex,originalBodies,readPin,destination}) {
  const reader=plan.reader,native=scientificNativeSelection(selection),config=plan.finalProfile;
  const {readPreparedFinalOwnership}=await import('./package-startup-ownership.mjs');
  const {prepareFinalBankStartupOwnership}=await import('./prepare-startup-ownership.mjs');
  const {finishEffectiveFootprint,extendFinishedNativeFootprint,mergeUnassignedNativeIntervals}=await import('../src/effective-footprint.js');
  let selected;
  const current=pointer=>{const pin=reader.pin(plan.selector.commit,pointer.path);need(pin.bytes===pointer.bytes&&pin.sha256===pointer.sha256,'Selected finalizer input whole identity differs');return reader.read(pin);};
  const projectionPointer=selection.reference_projection;
  let originalProjection,referenceMetadata;
  if(projectionPointer){
    const raw=current(projectionPointer);originalProjection=JSON.parse(raw);
    const references=validateReferenceMetadataHeader(originalProjection,{selection,manifest});
    referenceMetadata={version:1,asset:{path:'reference-metadata/current.json',bytes:raw.length,sha256:digest(raw)},native_reference:references.native,reference:references.reference};
  }
  plan.priorDeclaration={selection,priorEntry:name=>reader.descriptor(plan.selector.commit,name)};
  selected={selection,selectionBytes:reader.read(plan.selector),finalBank:selection.prepared_bank,
    reference_release:selection.reference,base:previous.preparedOwnership.base_reference,referenceMetadata};
  const before=await readPreparedFinalOwnership({indexRaw:originalIndex,manifest,manifestSha:native.sha256,selected,
    ownerCount:previous.preparedOwnership.owners,read:pin=>{need(originalBodies.has(pin.path),'Missing accepted final body');return originalBodies.get(pin.path);}});
  // Adopt an already prepared current-state proposal through the same writer.
  // The queue compares the complete before/after maps; preparation does not
  // grant scientific authority or reconstruct a correction from old repairs.
  if(config.proposed_selector){
    const pin=locate(reader,config.proposed_selector),raw=reader.read(pin),proposed=JSON.parse(raw);
    need(finalBankSelection(proposed)&&same(scientificNativeSelection(proposed),native)
      &&same(proposed.reference_projection,selection.reference_projection),
      'Proposed final bank changed the native/reference selection');
    const root=path.posix.dirname(proposed.prepared_bank.path);
    const read=async(pointer)=>{
      const request={...pointer,commit:pin.commit,mode:'100644'};
      await reader.acquire?.([request]);
      const physical=reader.pin(pin.commit,pointer.path);
      need(physical.bytes===pointer.bytes&&physical.sha256===pointer.sha256,'Proposed final body differs from its complete pin');
      return reader.read(physical);
    };
    const indexRaw=await read(proposed.prepared_bank),index=JSON.parse(indexRaw);
    need(same(index.compatibility_files,previous.compatibility_files),'Proposed final bank changed fixed compatibility');
    const proposedBank=await readPreparedFinalOwnership({indexRaw,manifest,manifestSha:native.sha256,
      selected:{finalBank:proposed.prepared_bank,base:before.index.preparedOwnership.base_reference,
        reference_release:proposed.reference,referenceMetadata},ownerCount:before.features.length,
      read:p=>read({...p,path:root+'/'+p.path})});
    const prepared=await prepareFinalBankStartupOwnership({manifest,manifestSha:native.sha256,previous,
      ownership:proposedBank.ownership,features:proposedBank.features,
      baseReference:before.index.preparedOwnership.base_reference,referenceMetadata,destination});
    const {prepared_bank,reference,...retained}=proposed;plan.proposedSelection=retained;
    return prepared;
  }
  let projection=originalProjection,reference=before.index.preparedOwnership.base_reference;
  if(config.reference_projection){
    const raw=readPin(config.reference_projection);projection=JSON.parse(raw);
    const references=validateReferenceMetadataHeader(projection,{selection:{...selection,reference_projection:{path:config.reference_projection.path,bytes:raw.length,sha256:digest(raw)}},manifest});
    reference=references.reference;referenceMetadata={version:1,asset:{path:'reference-metadata/current.json',bytes:raw.length,sha256:digest(raw)},native_reference:references.native,reference};
  }
  const changedHook=config.change_evidence&&!same(config.change_evidence,selection.change_evidence)?config.change_evidence:undefined;
  const added=await proposedFinalNativeInputs(changedHook,reader,manifest),byOwner=new Map();
  for(const component of added.components){const values=byOwner.get(component.target_id)??[];values.push(component);byOwner.set(component.target_id,values);}
  const properties=new Map((projection?.location_changes??[]).map(row=>[row.location_id,row.after_properties]));
  const features=before.features.map(feature=>{
    const components=byOwner.get(feature.id)??[];let source=feature;
    if(feature.geometry===null&&components.length){
      need(components.every(c=>c.base_geometry&&digest(jsonBytes(c.base_geometry))===c.base_geometry_sha256&&c.base_geometry_sha256===components[0].base_geometry_sha256),
        'Proposed lazy owner lacks one exact original base geometry');source={...feature,geometry:components[0].base_geometry};
    }
    source=finishEffectiveFootprint(source);byOwner.delete(feature.id);
    return extendFinishedNativeFootprint({...source,properties:properties.get(feature.id)??source.properties},components);
  });
  need(byOwner.size===0,'Proposed final authority names a foreign owner');
  const rows=mergeCompletedNativePatches(added.patches,manifest.size),owners=new Set(features.map(f=>f.pixelIndex));
  const words=mergeUnassignedNativeIntervals(before.ownership,rows,{owners,allowed:owners});
  const ownership={...before.ownership,...words,runWords:words.runs.length};
  const index=await prepareFinalBankStartupOwnership({manifest,manifestSha:native.sha256,previous,ownership,features,baseReference:reference,referenceMetadata,destination});
  plan.proposedSelection={version:2,kind:'selected-final-native-bank-v2',native_selection:native,
    ...(config.reference_projection?{reference_projection:{path:config.reference_projection.path,bytes:config.reference_projection.bytes,sha256:config.reference_projection.sha256}}:
      selection.reference_projection?{reference_projection:selection.reference_projection}:{}),
    ...(config.change_evidence?{change_evidence:config.change_evidence}:selection.change_evidence?{change_evidence:selection.change_evidence}:{})};
  return index;
}


export function finalizeDelivery(config, reader) {
  need(config.version===2,'Current finalization requires final-map version 2');
  return finalizeFinalBankDelivery(config,reader);
}

// The existing asynchronous finalization boundary prepares the finished map
// before the ordinary whole-set writer can adopt its selector. This private map
// is not a caller-provided write roster or a second publication mechanism.
export async function prepareFinalizedStartupOwnership(outputs) {
  const plan = finalizedAdoptions.get(outputs);
  need(plan, 'Authenticated finalization required for startup preparation');
  const reader = plan.reader, selection = JSON.parse(outputs['ownership-selection.json']),native=scientificNativeSelection(selection);
  const prefix = 'data/canonical-grid/current-startup/', indexPath = prefix + 'index.json';
  const definition = JSON.parse(outputs['package-inputs.json']);
  need(definition.inputs.includes(prefix), 'Final map bank must remain an ordinary package input');
  const originalIndex = reader.read(reader.pin(plan.selector.commit, indexPath)), previous = JSON.parse(originalIndex);
  need(previous.version===3 && previous.native_manifest_sha256 === native.sha256
    && Array.isArray(previous.files) && previous.files.length > 0
    && new Set(previous.files.map(pin => pin.path)).size === previous.files.length,
  'Complete original prepared bank required');
  const tree = new Map(reader.git('ls-tree', '-rz', plan.selector.commit, '--', prefix).toString().split('\0').filter(Boolean).map(line => {
    const match = /^100644 blob ([a-f0-9]{40})\t(.+)$/.exec(line);
    need(match && match[2].startsWith(prefix), 'Nonordinary prepared bank member');
    return [match[2].slice(prefix.length), match[1]];
  }));
  need(same([...tree.keys()].filter(name => name !== 'index.json').sort(), previous.files.map(pin => pin.path).sort()),
    'Original prepared bank inventory differs');
  const pins = previous.files.map(pin => {
    need(safe(pin.path) && Number.isSafeInteger(pin.bytes) && pin.bytes > 0 && hex(pin.sha256, 64), 'Invalid prepared bank pin');
    return {...pin, path: prefix + pin.path, commit: plan.selector.commit, mode: '100644', git_blob_oid: tree.get(pin.path)};
  });
  // Final-to-final preparation consumes current E and context, not the fixed
  // compatibility copies. Keep their complete accepted pins/tree identities; a
  // role also used by current E must still be acquired and fully authenticated.
  const retained = new Map();
  if (selection.version === 2) {
    const current = new Set([...previous.pixelMap.parts, ...previous.preparedOwnership.context_parts].map(pin => pin.path));
    need(Array.isArray(previous.compatibility_files), 'Complete compatibility roster required');
    for (const pin of previous.compatibility_files) {
      need(previous.files.some(old => same(old, pin)), 'Compatibility member differs from accepted index');
      if (!current.has(pin.path)) retained.set(pin.path, pin);
    }
  }
  const consumed = pins.filter(pin => !retained.has(pin.path.slice(prefix.length)));
  await reader.acquire(consumed);
  const originalBodies = new Map(consumed.map(pin => [pin.path.slice(prefix.length), reader.read(pin)]));
  const inputs = new Map(plan.adoption.map(row => [row.path, row.bytes]));
  const readPin = pin => {
    const body = inputs.get(pin.path);
    if (body !== undefined) {
      need(body.length === pin.bytes && digest(body) === pin.sha256, 'Final-map adopted input differs');
      return body;
    }
    return reader.read(pin);
  };
  const manifest = JSON.parse(reader.read(reader.pin(plan.selector.commit, native.manifest_path)));
  need(digest(reader.read(reader.pin(plan.selector.commit, native.manifest_path))) === native.sha256,
    'Final-map original manifest differs');
  const temporary = fs.mkdtempSync(path.join(os.tmpdir(), 'worldatlas-final-startup-'));
  try {
    const index=await prepareProposedFinalBank({plan,selection,manifest,previous,originalIndex,originalBodies,readPin,destination:temporary});
    const bodies = new Map(index.compatibility_files.filter(pin => !retained.has(pin.path)).map(pin => [pin.path, originalBodies.get(pin.path)]));
    const collect = (directory, relative = '') => {
      for (const entry of fs.readdirSync(directory, {withFileTypes: true})) {
        const name = relative + entry.name, full = path.join(directory, entry.name);
        if (entry.isDirectory()) collect(full, name + '/');
        else {
          need(entry.isFile() && safe(name), 'Nonordinary generated startup member');
          const bytes = fs.readFileSync(full), old = bodies.get(name);
          need(!old || old.equals(bytes), 'Immutable startup URL changed'); bodies.set(name, bytes);
        }
      }
    };
    collect(temporary);
    need([...retained.keys()].every(name => !bodies.has(name)), 'Generated output overlaps retained compatibility');
    index.files = [...retained.values(), ...[...bodies].map(([name, bytes]) => ({path: name, ...visitProduct(bytes)}))].sort((a, b) => a.path.localeCompare(b.path));
    const indexBytes = jsonBytes(index), adoption = new Map(plan.adoption.map(row => [row.path, row]));
    for (const [name, pin] of retained) {
      const expected = {bytes: pin.bytes, sha256: pin.sha256};
      need(!adoption.has(prefix + name), 'Conflicting retained compatibility role');
      adoption.set(prefix + name, {path: prefix + name, expected, previous: expected,
        git_blob_oid: tree.get(name), kind: 'input', retained: true});
    }
    for (const [name, bytes] of originalBodies) if (!bodies.has(name)) {
      need([2,3].includes(previous.version) && [...previous.pixelMap.parts, ...previous.preparedOwnership.context_parts].some(pin => pin.path === name),
        'Only inactive prior final-bank operands may retire');
      adoption.set(prefix + name, {path: prefix + name, bytes: null, expected: undefined, previous: visitProduct(bytes), git_blob_oid: tree.get(name), kind: 'retired'});
    }
    for (const [name, bytes] of [...bodies, ['index.json', indexBytes]]) {
      const target = prefix + name, expected = visitProduct(bytes), old = adoption.get(target);
      need(!old || same(old.expected, expected), 'Conflicting prepared finalization role');
      if (!old) adoption.set(target, {path: target, bytes, expected,
        previous: name === 'index.json' ? visitProduct(originalIndex) : originalBodies.has(name) ? expected : undefined,
        kind: name === 'index.json' ? 'canonical' : originalBodies.has(name) ? 'input' : 'generated'});
    }
    if(plan.finalProfile){
      const next={...plan.proposedSelection,prepared_bank:{path:indexPath,bytes:indexBytes.length,sha256:digest(indexBytes)},reference:index.preparedOwnership.effective_reference};
      const paths=[indexPath,...(next.reference_projection?[next.reference_projection.path]:[])];
      const packageInputs=appendFinalPackageReadPaths(JSON.parse(reader.read(plan.package_inputs)),paths,plan,next,manifest);
      for(const [key,target,bytes]of [['ownership-selection.json',plan.selector.path,jsonBytes(next)],['package-inputs.json',plan.package_inputs.path,orderedBytes(packageInputs)]]){
        outputs[key]=bytes;plan.outputs[key]=visitProduct(bytes);const previous=adoption.get(target);
        need(previous?.kind==='canonical','Missing original final-bank canonical role');adoption.set(target,{...previous,bytes,expected:visitProduct(bytes)});
      }
    }
    if(plan.finalProfile){const expectations=jsonBytes({version:2,kind:'selected-final-bank-consumer-v2',bank:JSON.parse(outputs['ownership-selection.json']).prepared_bank,reference:index.preparedOwnership.effective_reference});
      outputs['selected-delivery-expectations.json']=expectations;plan.outputs['selected-delivery-expectations.json']=visitProduct(expectations);}
    outputs['startup-ownership.json'] = indexBytes;
    plan.outputs['startup-ownership.json'] = visitProduct(indexBytes);
    const selector = adoption.get(plan.selector.path); adoption.delete(plan.selector.path); adoption.set(plan.selector.path, selector);
    plan.adoption = [...adoption.values()]; plan.startupPrepared = true;
  } finally { fs.rmSync(temporary, {recursive: true, force: true}); }
}

export function publishFinalizedDelivery(root, destination, outputs, binding, resume = false) {
  const plan = finalizedAdoptions.get(outputs);
  need(plan && same(Object.keys(outputs).sort(), Object.keys(plan.outputs).sort())
    && Object.entries(outputs).every(([name, bytes]) => same(visitProduct(bytes), plan.outputs[name])),
    'Authenticated complete finalization outputs required');
  need(!plan.startupRequired || plan.startupPrepared, 'Native finalization requires the finished startup bank before publication');
  const reader = plan.reader, head = reader.git('rev-parse', 'HEAD').toString().trim();
  const indexed = row => reader.git('ls-files', '--stage', '-v', '-z', '--', row.path).toString();
  const exactIndex = (row, entry, role) => {
    const identity = `100644 ${row.git_blob_oid} 0\t${row.path}\0`;
    need(entry === 'H ' + identity || entry === 'S ' + identity, `Indexed ${role} differs: ` + row.path);
    return entry === 'S ' + identity;
  };
  const retainedSparse = row => {
    const entry = indexed(row);
    return exactIndex(row, entry, 'retained compatibility');
  };
  const sparse = reader.git('config', '--type=bool', '--default=false', '--get', 'core.sparseCheckout').toString().trim() === 'true';
  const rows = plan.adoption.map(row => {
    if (row.retained) {
      // No cat-file sizing/read: an unchanged accepted ordinary tree entry is
      // and index entry preserve this unconsumed body. Only a real sparse
      // omission may remain absent; ordinary/staged deletions must not survive.
      need(reader.git('ls-tree', '-z', head, '--', row.path).toString()
        === `100644 blob ${row.git_blob_oid}\t${row.path}\0`, 'Committed retained compatibility differs: ' + row.path);
      return {...row, allowMissing: retainedSparse(row)};
    }
    const currentPin = reader.hasPath(head, row.path) ? reader.pin(head, row.path) : undefined;
    const current = currentPin ? visitProduct(reader.read(currentPin)) : undefined;
    need(row.kind === 'canonical' || row.kind === 'retired'
      ? same(current, row.previous) || same(current, row.expected)
      : current === undefined || same(current, row.expected),
    'Committed canonical baseline differs from finalization: ' + row.path);
    if (row.kind === 'retired') {
      const retirementIndex = indexed(row);
      // A genuine sparse omission is not an ordinary worktree deletion. Resume
      // may also observe our already staged retirement, but never a replacement.
      const removed = retirementIndex === '' && (current === undefined
        || resume && fs.existsSync(path.join(root, destination)));
      need(current !== undefined || retirementIndex === '', 'Indexed final-bank retirement differs: ' + row.path);
      const sparseRetirement = !removed && exactIndex(row, retirementIndex, 'final-bank retirement');
      return {...row, previous: current ?? row.previous, retirementIndex, sparseRetirement,
        allowMissing: current === undefined || sparseRetirement};
    }
    const writeIndex = indexed(row), identity = oid => `100644 ${oid} 0\t${row.path}\0`;
    let allowed = currentPin ? [identity(currentPin.git_blob_oid)] : [];
    if (resume) {
      const hash = createHash('sha1').update(`blob ${row.expected.bytes}\0`);
      visitProduct(row.bytes, chunk => hash.update(chunk));
      allowed.push(identity(hash.digest('hex')));
    }
    need(writeIndex === '' && !currentPin || allowed.some(value => writeIndex === 'H ' + value || writeIndex === 'S ' + value),
      'Indexed canonical output differs: ' + row.path);
    const sparsePreimage = sparse && writeIndex.startsWith('S ');
    return {...row, previous: current ?? row.previous, writeIndex, sparsePreimage,
      allowMissing: row.kind === 'input' || sparsePreimage};
  });
  need(rows.every(row => row.path !== destination && !row.path.startsWith(destination + '/')
    && !destination.startsWith(row.path + '/')),
    'Staging destination overlaps canonical finalization outputs');
  // Derive preparation from the actual authenticated write set, not a second
  // caller-maintained input list. This first pass still rejects every dirty or
  // nonordinary output before staging or changing sparse checkout selection.
  admitCanonicalOutputs(root, rows, resume);
  const writes = rows.filter(row => !row.retained && row.kind !== 'retired');
  if (sparse) need(reader.git('config', '--type=bool', '--default=false', '--get', 'core.sparseCheckoutCone').toString().trim() === 'false',
    'Finalization materialization requires the managed non-cone sparse checkout');
  const publication = publish(root, destination, outputs,
    {...binding, selector: plan.selector, package_inputs: plan.package_inputs}, resume);
  need(reader.git('rev-parse', 'HEAD').toString().trim() === head, 'Finalization HEAD changed before adoption');
  for (const row of rows.filter(row => row.retained)) need(retainedSparse(row) === row.allowMissing,
    'Retained compatibility index changed before adoption: ' + row.path);
  const retired = rows.filter(row => row.kind === 'retired');
  const recheckRetirements = () => {
    for (const row of retired) need(indexed(row) === row.retirementIndex,
      'Final-bank retirement index changed before adoption: ' + row.path);
  };
  recheckRetirements();
  for (const row of writes) need(indexed(row) === row.writeIndex, 'Canonical output index changed before materialization: ' + row.path);
  if (sparse) {
    reader.git('sparse-checkout', 'add', '--', ...writes.map(row => '/' + row.path));
    need(reader.git('rev-parse', 'HEAD').toString().trim() === head, 'Finalization HEAD changed during materialization');
    for (const row of writes) {
      const expected = row.writeIndex.replace(/^S /, 'H ');
      need(indexed(row) === expected, 'Canonical output index changed during materialization: ' + row.path);
    }
    recheckRetirements();
    for (const row of rows.filter(row => row.retained)) need(retainedSparse(row) === row.allowMissing,
      'Retained compatibility index changed during materialization: ' + row.path);
  }
  // Materialization supplies the exact existing preimages. The original writer
  // must now admit them normally, retaining its byte checks and selector-last order.
  const adopt = admitCanonicalOutputs(root, rows.map(row => row.sparsePreimage
    ? {...row, allowMissing: row.kind === 'input'} : row), resume);
  adopt();
  // Normal git add ignores excluded sparse paths even after clearing their
  // skip-worktree bit. Retire only these exact, now-absent indexed preimages.
  const sparseRetirements = retired.filter(row => row.sparseRetirement);
  if (sparseRetirements.length) {
    recheckRetirements();
    for (const row of sparseRetirements) need(!fs.lstatSync(path.join(root, row.path), {throwIfNoEntry: false}),
      'Retired sparse output reappeared before staging: ' + row.path);
    reader.git('update-index', '--force-remove', '--', ...sparseRetirements.map(row => row.path));
    for (const row of sparseRetirements) need(indexed(row) === '', 'Sparse retirement was not staged: ' + row.path);
  }
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
  // Project display bytes before publication. A formatting refusal cannot leave
  // a newly published receipt or discard the completed producer's staging.
  const summary = scientificOperationSummary({destination, binding, observation: result.observation},
    {products: result.products});
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
  return {...summary, resumed: publication.resumed};
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
  const selection=reader.json(selectorPin),base=scientificNativeSelection(selection);
  let assets,envelope;
  if(selection.version===2){
    const selectedManifest=reader.pin(selectorPin.commit,base.manifest_path),manifest=reader.json(selectedManifest);
    need(selectedManifest.sha256===base.sha256,'Original final-profile native manifest differs');
    const issued=manifest.original_assets?.bounds,owner=config.source_evidence.owner_roster;
    need(owner&&issued&&owner.commit===issued.commit&&owner.path===issued.path&&owner.sha256===issued.sha256,
      'Final-profile source preparation requires its genuine original owner pin');
    reader.read(owner);assets={base_manifest:selectedManifest,owner_roster:owner};
  }else{
  const hook = selection.additive_release;
  need(hook && same(Object.keys(hook).sort(), ['bytes', 'path', 'sha256']), 'Existing cumulative selection required');
  const sidecarPin = reader.pin(selectorPin.commit, hook.path);
  need(sidecarPin.bytes === hook.bytes && sidecarPin.sha256 === hook.sha256, 'Original selected sidecar differs');
  const sidecar = reader.json(sidecarPin);
  need(sidecar.version === 2 && sidecar.kind === 'retained-native-additive-selection-v2'
    && same(sidecar.base_selection, base), 'Original selected base differs');
  assets = sidecar.logical_asset_map;
  need(assets && same(Object.keys(assets).sort(), ['base_manifest', 'ledger', 'owner_roster', 'patch']),
    'Complete prior logical assets required');
  const wrapped = reader.json(sidecar.runtime_envelope); envelope = wrapped.additiveRelease ?? wrapped;
  need(envelope.version === 2 && envelope.kind === 'retained-native-base-plus-delta-v2', 'Existing v2 runtime envelope required');
  for (const [role, pin] of Object.entries(assets)) {
    const declared = envelope[role];
    need(declared?.bytes === pin.bytes && declared?.sha256 === pin.sha256
      && (declared.decoded_bytes ?? declared.bytes) === (pin.decoded_bytes ?? pin.bytes)
      && (declared.decoded_sha256 ?? declared.sha256) === (pin.decoded_sha256 ?? pin.sha256),
    'Prior envelope asset binding differs: ' + role);
  }
  }
  const manifest=reader.json(assets.base_manifest),selectedManifest=reader.pin(selectorPin.commit,base.manifest_path);
  need(selectedManifest.sha256===base.sha256&&assets.base_manifest.sha256===base.sha256
    &&selectedManifest.bytes===assets.base_manifest.bytes&&base.method===manifest.method,
    'Original selected native manifest/method differs');
  const contractKeys = ['size', 'coordinateBits', 'method', 'native_latitudes', 'hierarchy_sha256', 'original_assets'];
  need(contractKeys.every(key => Object.hasOwn(manifest, key)), 'Complete original native contract required');
  const native_contract = Object.fromEntries(contractKeys.map(key => [key, manifest[key]]));
  const references = qualifiedDeliveryReference(selection, manifest, reader, selectorPin.commit, assets.owner_roster);
  need((!envelope || (same(envelope.base_reference, references.native) || same(envelope.base_reference, references.reference))
    && (!references.projectionPin || envelope.effective_reference?.hierarchy_sha256 === envelope.base_reference.hierarchy_sha256))
    && manifest.geographic_release === base.release_id
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
  need(['reference-metadata', 'source', 'physical', 'source-evidence', 'native-authority', 'native-diagnostic', 'supported-inputs', 'requests', 'native-requests', 'retain', 'rebind-operating', 'rebind-certificate', 'compose', 'finalize'].includes(phase) && configFile && destination && flags.every(f => f === '--resume') && flags.length <= 1,
    'Use prepare-delivery-handoff.mjs requests|native-requests|retain|rebind-operating|rebind-certificate|compose|finalize|source|physical|source-evidence|native-authority|native-diagnostic|supported-inputs|reference-metadata CONFIG DESTINATION [--resume]');
  need(!process.execArgv.length && !process.env.NODE_OPTIONS?.trim() && !process.env.NODE_PATH?.trim(), 'Plain Node launch required');
  const root = fs.realpathSync(process.cwd()); admitDestination(root, destination, flags.includes('--resume'));
  const raw = ordinary(root, configFile), config = JSON.parse(raw), reader = pinReader(root);
  need(config.version===1||config.version===2&&['compose','finalize'].includes(phase),'Versioned preparation config required');
  const binding = ['source','physical'].includes(phase) ? sourceBinding(raw,phase) : {phase, config_sha256: digest(raw)};
  if (['source','physical'].includes(phase) && flags.includes('--resume') && fs.existsSync(path.join(root, destination))) {
    console.log(JSON.stringify(resumeSource(root, destination, config, binding, reader))); return;
  }
  let outputs, observation;
  if (['source','physical'].includes(phase)) {
    const result = await sourceCohort(config, reader, root, destination, phase);
    console.log(JSON.stringify(publishCompletedSource(root, destination, result, binding, flags.includes('--resume'), reader)));
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
  if (phase === 'finalize') {
    outputs=finalizeDelivery(config,reader);
    await prepareFinalizedStartupOwnership(outputs);
    const publication = publishFinalizedDelivery(root, destination, outputs, binding, flags.includes('--resume'));
    console.log(JSON.stringify(publication)); return;
  }
  console.log(JSON.stringify({...publishOwnedProducts(root, destination, outputs, binding, flags.includes('--resume')), ...(observation ? {observation} : {})}));
}
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) main(process.argv.slice(2)).catch(error => { console.error(error.message); process.exitCode = 1; });
