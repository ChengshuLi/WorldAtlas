import {gunzipSync} from 'node:zlib';
import {ImmutableReader} from './check-effective-geographic-regression.mjs';
import {valueBytes, valueSha, readOriginalRuleAuthority, qualifyOriginalSourceAuthority, qualifyOriginalNativeAuthority, readRetainedRegistryAuthority, qualifySourceTargetNativeAuthority} from '../coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';
// Immutable delivery metadata, authority constructors and exact-body acquisition.
// Resolve actual committed outputs; never accept caller-written derived hashes.
import path from 'node:path';
import fs from 'node:fs';
import {execFileSync} from 'node:child_process';
import {createAcquisition} from './geography-prefetch.mjs';
import {createHash} from 'node:crypto';

const need = (value, message) => { if (!value) throw Error(message); };
const hash = raw => createHash('sha256').update(raw).digest('hex');
const safe = value => typeof value === 'string' && /^[a-zA-Z0-9_./-]+$/.test(value)
  && !path.isAbsolute(value) && value.split('/').every(x => x && x !== '.' && x !== '..');
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);

export function locate(reader, locator) {
  need(locator && same(Object.keys(locator).sort(), ['commit', 'path'])
    && /^[a-f0-9]{40}$/.test(locator.commit) && safe(locator.path),
  'Supply an exact commit/path locator, without handwritten derived descriptors');
  const pin = reader.pin(locator.commit, locator.path);
  reader.read(pin);
  return pin;
}

export function readPreparedStage(reader, locator, expectedPhase) {
  const pin = locate(reader, locator), receipt = reader.json(pin);
  need(path.posix.basename(pin.path) === 'preparation.json' && receipt.version === 1
    && receipt.binding?.phase === expectedPhase
    && /^[a-f0-9]{64}$/.test(receipt.binding.config_sha256)
    && receipt.outputs && Object.keys(receipt.outputs).length,
  'Missing completed preparation phase');
  need(!Object.hasOwn(receipt, 'input') || expectedPhase === 'package'
    && hash(bytes(receipt.input)) === receipt.binding.config_sha256, 'Committed package input binding differs');
  const prefix = path.posix.dirname(pin.path), outputs = {};
  for (const [name, declared] of Object.entries(receipt.outputs)) {
    need(safe(name) && !name.includes('/') && name !== 'preparation.json', 'Unsafe prepared output');
    const actual = reader.pin(pin.commit, prefix + '/' + name), raw = reader.read(actual);
    need(actual.bytes === declared.bytes && hash(raw) === declared.sha256, 'Committed prepared output differs: ' + name);
    outputs[name] = actual;
  }
  return {pin, receipt, outputs};
}

// Reuse authenticates both the original raw configuration and every committed
// output. The ordinary constructor below still establishes semantic applicability;
// a matching hash or caller-written completion flag cannot skip that check.
export function qualifiedPreparedReuse(reader, adoption, phase, products = null) {
  need(['recipe', 'requests', 'native-requests', 'retain', 'authority', 'registry', 'compose', 'rebind-operating', 'rebind-certificate', 'package', 'finalize'].includes(phase), 'Review and queue decisions cannot be adopted');
  need(adoption && equal(Object.keys(adoption).sort(), ['config', 'receipt']), 'Reuse requires original config and preparation receipt locators');
  const stage = readPreparedStage(reader, adoption.receipt, phase);
  const config = locate(reader, adoption.config);
  need(hash(reader.read(config)) === stage.receipt.binding.config_sha256, 'Reused receipt does not bind its original raw config');
  if (products) {
    need(equal(Object.keys(products).sort(), Object.keys(stage.outputs).sort()), 'Reused stage output inventory differs');
    for (const [name, raw] of Object.entries(products))
      need(Buffer.isBuffer(raw) && reader.read(stage.outputs[name]).equals(raw), 'Reused stage no longer matches qualified inputs: ' + name);
  }
  return {...stage, config};
}

// `templates` and `retained` are produced by the admitted recipe/stage index.
// They identify files, not component IDs, hashes, source acceptance or approvals.
export function nativeConfigFromStages(reader, {requests, retained, templates, compatibility}) {
  const issued = readPreparedStage(reader, requests, 'requests');
  need(issued.outputs['requests.json'], 'Missing issued request index');
  const index = reader.json(issued.outputs['requests.json']);
  need(index.version === 1 && Array.isArray(index.groups) && index.groups.length, 'Missing ordered issued groups');
  const ids = index.groups.map(row => row.id);
  need(new Set(ids).size === ids.length && same(Object.keys(retained).sort(), [...ids].sort())
    && same(Object.keys(templates).sort(), [...ids].sort()), 'Missing/extra/duplicate committed group binding');
  const groups = index.groups.map(row => {
    const request = issued.outputs[row.request];
    need(request && reader.json(request).source_rule
      && same(reader.json(request).source_rule.expected_ids, row.component_ids), 'Issued index/request scope differs');
    const stage = readPreparedStage(reader, retained[row.id], 'retain');
    for (const name of ['request.json', 'terminal.json', 'facts.json', 'inventory.jsonl.gz', 'publication.json'])
      need(stage.outputs[name], 'Incomplete retained SOURCE stage: ' + name);
    need(stage.outputs['request.json'].sha256 === request.sha256
      && stage.outputs['request.json'].bytes === request.bytes, 'Retained SOURCE belongs to another issued request');
    const facts = reader.json(stage.outputs['facts.json']);
    need(facts.request?.path === request.path && facts.request?.sha256 === request.sha256 && facts.request?.bytes === request.bytes,
    'Retained SOURCE does not name the actual original issued request');
    const original = locate(reader, {commit: facts.request.commit, path: facts.request.path});
    need(original.mode === facts.request.mode && original.git_blob_oid === (facts.request.git_blob_oid ?? facts.request.blob)
      && original.sha256 === request.sha256 && original.bytes === request.bytes,
    'Original issued request descriptor was substituted');
    const template = templates[row.id];
    need(safe(template.destination) && template.destination.startsWith('.cache/native-grid-candidates/'), 'Unsafe native destination');
    return {id: row.id, destination: template.destination, template: locate(reader, template.locator),
      source: {request: original, operating: stage.outputs['terminal.json'], publication: stage.outputs['publication.json'],
        facts: stage.outputs['facts.json'], inventory: stage.outputs['inventory.jsonl.gz']}};
  });
  // The existing nativeRequests constructor must still validate genuine terminal,
  // publication, whole handoff, complete inventory, runtime and native template.
  return {version: 1, ...(compatibility === undefined ? {} : {compatibility}), groups};
}

export function rebindConfigFromStage(reader, {retained, operating}) {
  const stage = readPreparedStage(reader, retained, 'retain');
  const names = {request: 'request.json', terminal: 'terminal.json', publication: 'publication.json',
    facts: 'facts.json', result: 'result.json'};
  const config = {version: 1};
  for (const [role, name] of Object.entries(names)) {
    need(stage.outputs[name], 'Incomplete retained rebind stage: ' + name);
    config[role] = stage.outputs[name];
  }
  config.execution_custody = {};
  for (const [role, name] of Object.entries({code_source: 'code-source.json', issued_plan: 'issued-plan.json',
    stderr: 'stderr.log', stdout: 'stdout.json', terminal: 'terminal.json'})) {
    need(stage.outputs[name], 'Incomplete retained execution custody: ' + name);
    config.execution_custody[role] = stage.outputs[name];
  }
  if (operating) {
    const proof = readPreparedStage(reader, operating, 'rebind-operating');
    need(proof.outputs['operating.json'], 'Missing committed operating body');
    config.operating = proof.outputs['operating.json'];
  }
  return config;
}

const canonical = value => Array.isArray(value) ? value.map(canonical) : value && typeof value === 'object'
  ? Object.fromEntries(Object.keys(value).sort().map(key => [key, canonical(value[key])])) : value;
const bytes = value => Buffer.from(JSON.stringify(canonical(value)) + '\n');
const equal = (a, b) => bytes(a).equals(bytes(b));

export function committedRetentionConfig(reader, observation) {
  const publication = locate(reader, observation.publication), document = reader.json(publication);
  need(path.posix.basename(publication.path) === 'publication.json', 'Actual publication filename required');
  const prefix = path.posix.dirname(publication.path), factsPath = document.outputs?.facts?.path ?? 'facts.json';
  need(safe(factsPath) && !factsPath.includes('/'), 'Unsafe published facts path');
  const facts = reader.json(reader.pin(publication.commit, prefix + '/' + factsPath));
  let request;
  if (facts.request) {
    request = locate(reader, {commit: facts.request.commit, path: facts.request.path});
    need(request.sha256 === facts.request.sha256 && request.bytes === facts.request.bytes
      && request.mode === facts.request.mode && request.git_blob_oid === (facts.request.blob ?? facts.request.git_blob_oid),
    'Published original request descriptor differs');
  } else {
    request = locate(reader, observation.request);
    need(facts.request_sha256 === request.sha256, 'Rebind facts/observed request differs');
  }
  const terminal = locate(reader, observation.terminal), readPins = new Map([[terminal.path, terminal]]);
  for (const row of document.outputs ? Object.values(document.outputs)
    : [{path: 'facts.json', ...document.facts}, {path: 'inventory.jsonl.gz', ...document.inventory}, ...(document.assets ?? [])]) {
    need(safe(row.path) && !row.path.includes('/'), 'Unsafe publication member');
    const pin = reader.pin(publication.commit, prefix + '/' + row.path);
    need(pin.bytes === row.bytes && pin.sha256 === row.sha256, 'Published whole member differs');
    need(!readPins.has(pin.path), 'Publication/terminal path collision'); readPins.set(pin.path, pin);
  }
  readPins.set(publication.path, publication);
  const custody = {};
  for (const [role, locator] of Object.entries(observation.custody ?? {})) {
    const pin = locate(reader, locator); need(!readPins.has(pin.path), 'Custody role path collision');
    readPins.set(pin.path, pin); custody[role] = pin.path;
  }
  return {config: {version: 1, request, terminal: terminal.path, output: prefix,
    ...(observation.custody ? {custody} : {})}, publication, terminal,
    readLocal: (_root, name) => { need(readPins.has(name), 'Undeclared committed publication read'); return reader.read(readPins.get(name)); }};
}

const locatorOf = pin => ({commit: pin.commit, path: pin.path});
function registryComposition(reader, registryPins) {
  const ledgerPins = new Map();
  for (const pin of registryPins) for (const entry of reader.json(pin).entries) {
    const binding = reader.json(entry.source_authority), ledger = binding.original_pins.ledger;
    reader.read(ledger); const key = ledger.commit + ':' + ledger.path;
    need(!ledgerPins.has(key) || equal(ledgerPins.get(key), ledger), 'Conflicting retained ledger descriptor');
    ledgerPins.set(key, ledger);
  }
  return {version: 1, registries: registryPins, ledgers: [...ledgerPins.values()]};
}

// Discovery from an existing selected release is only a metadata replay input.
// Each later phase still invokes its ordinary genuine terminal/custody checks.
export function observeCompletedDelivery(reader, {sidecar: sidecarLocator, composed_ledger, new_prefix}) {
  const sidecarPin = locate(reader, sidecarLocator), sidecar = reader.json(sidecarPin);
  const registry = reader.json(sidecar.authority_registry), selected = reader.json(sidecar.logical_asset_map.ledger);
  const certificate = reader.json(selected.current_rebind), operating = reader.json(certificate.operating);
  const sources = [], natives = [], authorities = [];
  for (const entry of registry.entries.filter(e => e.source_authority.path.startsWith(new_prefix))) {
    const binding = reader.json(entry.source_authority), native = reader.json(binding.original_pins.native_request).additive;
    const aliases = new Map((binding.source_output_aliases ?? []).map(a => [a.original.path, a.published]));
    const role = key => {
      const pins = native.inputs.filter(p => p.path === native[key]); need(pins.length === 1, 'Missing retained SOURCE role');
      return aliases.get(pins[0].path) ?? pins[0];
    };
    sources.push({publication: locatorOf(role('publication_path')), terminal: locatorOf(role('operating_path'))});
    natives.push({publication: locatorOf(binding.native_proof.publication), terminal: locatorOf(binding.native_proof.operating)});
    authorities.push({rule_preimage: locatorOf(entry.rule_preimage), source_authority: locatorOf(entry.source_authority)});
  }
  need(sources.length, 'Completed selection contains no owned authorities');
  return {sources, natives, authorities, registry: locatorOf(sidecar.authority_registry), composed_ledger,
    rebind: {request: locatorOf(certificate.request), publication: locatorOf(certificate.publication),
      terminal: locatorOf(operating.execution_custody.terminal), custody: Object.fromEntries(Object.entries(operating.execution_custody)
        .filter(([role]) => role !== 'terminal').map(([role, pin]) => [role, locatorOf(pin)]))},
    operating: locatorOf(certificate.operating), certificate: locatorOf(selected.current_rebind), sidecar: sidecarLocator};
}

// Qualify a completed standalone finalize receipt against its actual authority,
// composition, execution custody and final products.
export function qualifyFinalizedCheckpoint(recipe, adoption, reader, adapters) {
  need(recipe.mode === 'explicit-groups', 'Finalized checkpoint requires an explicit v2 subset recipe');
  const planned = materializeRecipe(recipe, reader);
  const stage = qualifiedPreparedReuse(reader, adoption, 'finalize');
  const final = reader.json(stage.config);
  need(final.new_prefix === recipe.new_prefix
    && equal(locatorOf(final.selector), recipe.selector)
    && equal(locatorOf(final.package_inputs), recipe.package_inputs), 'Finalized checkpoint original selection/package context differs');
  const registry = reader.json(final.registry), pairs = [], seen = new Set();
  const retained = (recipe.retained_registries ?? []).flatMap(p => reader.json(locate(reader, p)).entries);
  for (const entry of registry.entries) {
    if (retained.some(old => equal(old, entry))) continue;
    const binding = reader.json(entry.source_authority);
    const source = reader.json(binding.original_pins.source_request);
    const native = reader.json(binding.original_pins.native_request);
    const group = planned.groups.find(g => equal(g.component_ids, source.source_rule?.expected_ids));
    need(group && !seen.has(group.id), 'Finalized checkpoint has foreign/duplicate new component scope');
    need(equal(source, reader.json(locate(reader, group.source_locator)))
      && equal(native, reader.json(locate(reader, group.native_locator))), 'Finalized checkpoint original SOURCE/NATIVE identities differ from recipe');
    seen.add(group.id);
    pairs.push({rule_preimage: locatorOf(entry.rule_preimage), source_authority: locatorOf(entry.source_authority)});
  }
  need(seen.size === planned.groups.length && retained.every(old => registry.entries.some(e => equal(e, old))),
    'Finalized checkpoint omitted requested or retained authority');
  const qualified = JSON.parse(constructAuthorityRegistry(adapters.authorityReader(), pairs)['authority-registry.json']);
  need(qualified.entries.every(e => registry.entries.some(actual => equal(actual, e))), 'Finalized checkpoint authority descriptor differs');
  const composition = adapters.composeAuthorities(registryComposition(reader, [final.registry]), reader);
  for (const [name, pin] of [['authority-registry.json', final.registry], ['composed-original-ledger.json', final.ledger]])
    need(reader.read(pin).equals(composition[name]), 'Finalized checkpoint composition differs: ' + name);
  const certificate = reader.json(final.rebind), operating = reader.json(certificate.operating);
  const rebind = {version: 1, ...Object.fromEntries(['request', 'facts', 'publication', 'result', 'operating'].map(k => [k, certificate[k]])),
    terminal: operating.execution_custody.terminal, execution_custody: operating.execution_custody};
  need(reader.read(final.rebind).equals(adapters.rebindCustody(rebind, reader, true)['certificate.json']),
    'Finalized checkpoint certificate differs from genuine execution custody');
  qualifiedPreparedReuse(reader, adoption, 'finalize', adapters.finalizeDelivery(final, reader));
  return {receipt: stage.pin, config: stage.config, component_ids: planned.groups.flatMap(g => g.component_ids),
    limits: ['Immutable metadata and retained execution qualification only; no new science, delivery, CI or review acceptance.']};
}

// A historical completed SOURCE/NATIVE pair is not a new issuance template.
// Authenticate its whole original custody, including literal v1 scope.
export function qualifyCompletedCustody(recipe, reader, adapters) {
  const unique = values => Array.isArray(values) && values.length > 0
    && values.every(v => typeof v === 'string' && v.length > 0) && new Set(values).size === values.length;
  need(recipe?.version === 1 && recipe.mode === 'completed-original-custody' && typeof recipe.id === 'string' && /^[a-z0-9-]+$/.test(recipe.id)
    && equal(Object.keys(recipe).sort(), ['groups', 'id', 'mode', 'new_prefix', 'package_inputs', 'retained_registries', 'selector', 'version'])
    && Array.isArray(recipe.groups) && recipe.groups.length > 0,
    'Explicit completed-original custody recipe required');
  need(typeof recipe.new_prefix === 'string' && recipe.new_prefix.endsWith('/') && safe(recipe.new_prefix.slice(0, -1))
    && recipe.selector?.path === 'data/ownership-selection.json' && recipe.package_inputs?.path === '.github/package-inputs.json'
    && Array.isArray(recipe.retained_registries),
    'Completed-original selection/package/retained context required');
  locate(reader, recipe.selector); locate(reader, recipe.package_inputs);
  const retained = recipe.retained_registries.map(p => locate(reader, p));
  need(new Set(retained.map(p => p.commit + ':' + p.path)).size === retained.length, 'Duplicate retained registry context');
  const ids = new Set(), components = new Set(), groups = [];
  for (const group of recipe.groups) {
    need(equal(Object.keys(group).sort(), ['component_ids', 'id', 'native_operating', 'native_publication', 'source_publication', 'target_ids'])
      && typeof group.id === 'string' && /^[a-z0-9-]+$/.test(group.id) && !ids.has(group.id) && unique(group.component_ids) && unique(group.target_ids),
      'Explicit unique completed-original group scope required');
    ids.add(group.id);
    const input = {source_publication: group.source_publication, native_publication: group.native_publication,
      native_operating: group.native_operating};
    const qualified = constructOriginalAuthority(adapters.authorityReader(), input);
    const ledger = reader.json(qualified.ledger), targets = [...new Set(ledger.rows.map(row => row.target_id))].sort();
    need(equal(group.component_ids, qualified.component_ids) && equal(ledger.scope_ids, qualified.component_ids)
      && unique(targets) && equal([...group.target_ids].sort(), targets), 'Completed-original component/target scope differs');
    need(qualified.component_ids.every(id => !components.has(id)), 'Overlapping completed-original component scope');
    qualified.component_ids.forEach(id => components.add(id));
    groups.push({id: group.id, component_ids: [...qualified.component_ids], target_ids: targets,
      authority_input: input, qualified_products: qualified.products});
  }
  return {groups, component_ids: [...components], limits: ['Original completed custody only; current rebind, selection, independent review and queue remain required.']};
}

// Existing-contract constructor, scoped to avoid mixing scientific identities.
export const {materializeRecipe} = (() => {
// Metadata-only recipe postimage. No body acquisition, execution or publication.
const need=(v,m)=>{if(!v)throw Error(m);};
const canon=v=>Array.isArray(v)?v.map(canon):v&&typeof v==='object'?Object.fromEntries(Object.keys(v).sort().map(k=>[k,canon(v[k])])):v;
const bytes=v=>Buffer.from(JSON.stringify(canon(v))+'\n');
const sha=v=>createHash('sha256').update(v).digest('hex');
const equal=(a,b)=>bytes(a).equals(bytes(b));
const hash=(s,n=64)=>typeof s==='string'&&new RegExp(`^[a-f0-9]{${n}}$`).test(s);
const safe=s=>typeof s==='string'&&/^[A-Za-z0-9_.\/-]+$/.test(s)&&!s.startsWith('/')&&s.split('/').every(x=>x&&x!=='.'&&x!=='..');
const unique=a=>Array.isArray(a)&&a.length&&a.every(x=>typeof x==='string'&&x)&&new Set(a).size===a.length;
const integer=(n,name)=>{need(Number.isSafeInteger(n)&&n>=0,'Invalid '+name);return n;};
const add=values=>values.reduce((n,v)=>integer(n+v,'aggregate bytes'),0);
const operatorPin=p=>{const q={...p,blob:p.blob??p.git_blob_oid};delete q.git_blob_oid;return q;};
const identity=p=>({commit:p.commit,path:p.path,mode:p.mode,blob:p.blob??p.git_blob_oid,bytes:p.bytes,sha256:p.sha256});
function locate(reader,p){need(p&&equal(Object.keys(p).sort(),['commit','path'])&&hash(p.commit,40)&&safe(p.path),'Exact metadata commit/path locator required');const pin=reader.pin(p.commit,p.path);reader.read(pin);return pin;}
function read(reader,p){const pin=locate(reader,p);return {pin,body:reader.json(pin)};}
function uniquePins(pins){const map=new Map();for(const original of pins){const p=operatorPin(original);need(!map.has(p.path)||equal(map.get(p.path),p),'Conflicting input path: '+p.path);map.set(p.path,p);}return [...map.values()];}
function validateOperatorPin(p){
 need(safe(p?.path)&&['100644','100755'].includes(p.mode)&&hash(p.sha256),'Invalid operator input descriptor');
 if(p.kind==='original-report-product')need(p.mode==='100644'&&p.path.startsWith('.cache/additive-native-gap-repair/')&&hash(p.report_sha256)&&/^(components|sources)-\d{3}\.jsonl\.gz$/.test(p.original_product_path),'Invalid original report product');
 else if(p.kind==='completed-inventory-body')need(p.mode==='100644'&&/^\.cache\/native-grid-candidates\/[A-Za-z0-9_-]+\/(facts\.json|publication\.json|inventory\.jsonl\.gz)$/.test(p.path),'Invalid predecessor body');
 else need(hash(p.commit,40)&&hash(p.blob??p.git_blob_oid,40),'Missing immutable input identity');
 integer(p.bytes,'whole input');
 need((p.uncompressed_bytes===undefined)===(p.uncompressed_sha256===undefined),'Incomplete decoded identity');
 if(p.uncompressed_bytes!==undefined){need(hash(p.uncompressed_sha256),'Missing decoded identity');integer(p.uncompressed_bytes,'decoded input');}
}

function validateTemplateIdentity(request){
 const stage=request.source_rule??request.additive;
 need(stage&&Array.isArray(stage.inputs)&&Array.isArray(request.baseline?.pins),'Missing operator input inventory');
 need(request.operating_profile===undefined||request.operating_profile==='source-native-v2','Unsupported operator profile');
 const operating=request.operating_runtime;
 need(operating?.version===1&&operating.platform==='linux'&&operating.runtime?.map(p=>p.role).join(',')==='git,node,process-inspector,time','Complete bound runtime required');
 for(const p of operating.runtime)need(typeof p.path==='string'&&p.path.startsWith('/')&&p.mode===493&&hash(p.sha256)&&Number.isSafeInteger(p.bytes)&&p.bytes>0,'Invalid runtime binding');
 need(new Set(operating.runtime.map(p=>p.path)).size===4,'Duplicate runtime path');
 need(operating.supervisor?.path==='coordination/engineering/melanesia363-additive-delivery-20261010/supervise-source-native-linux.mjs'&&hash(operating.supervisor.sha256)&&Number.isSafeInteger(operating.supervisor.bytes)&&operating.supervisor.bytes>=0,'Invalid supervisor binding');
 if(request.operating_profile==='source-native-v2')need(operating.support_code?.map(p=>p.path).join(',')==='scripts/local-workspace.mjs,scripts/worker-identity.mjs'&&operating.support_code.every(p=>hash(p.sha256)&&Number.isSafeInteger(p.bytes)&&p.bytes>0),'Complete operating support bindings required');
 need(Array.isArray(request.executed_code)&&Array.isArray(request.installed_modules),'Complete executed code/module inventories required');
 for(const p of [...request.executed_code,...request.installed_modules]){
  need(typeof p.path==='string'&&safe(p.path.replaceAll('@',''))&&hash(p.sha256),'Invalid code/module descriptor');
  integer(p.bytes,'code/module bytes');
 }
 for(const pin of [request.report,...stage.inputs,...request.baseline.pins])validateOperatorPin(pin);
}

function accepted(reader,registry,selection){
 const entries=registry.body.entries.filter(e=>e.id===selection.handoff_id);need(entries.length===1,'Unknown/ambiguous accepted handoff');
 const entry=entries[0],pin={...entry.source,commit:entry.accepted_source_commit};
 const scope=reader.json(pin),rows=scope.candidate_source_native_bindings;
 need(unique(entry.cohort_ids)&&equal(scope.scopeIds,entry.cohort_ids)&&equal(rows?.map(r=>r.component_id),entry.cohort_ids),'Accepted handoff scope/order changed');
 need(equal([...new Set(rows.map(r=>r.retained_payload?.target_stable_location_id))].sort(),[...entry.target_ids].sort()),'Accepted target mapping changed');
 return {entry,pin:operatorPin(pin),scope,rows};
}
function directProduct(binding){return binding.physical_comparison?.original_report_product?.path;}
function locatorMap(reader,selection,handoff){
 if(!selection.physical_locator)return null;
 const {input,format}=selection.physical_locator,loaded=read(reader,input);
 const match=handoff.scope.consumed_inputs.filter(p=>p.path===loaded.pin.path&&equal(identity(p),identity(loaded.pin)));
 need(match.length===1,'Physical locator is not an exact consumed handoff input');
 if(format==='keyed-path')return new Map(Object.entries(loaded.body).map(([id,row])=>[id,row.path]));
 need(format==='components-comparison-product'&&Array.isArray(loaded.body.components),'Unsupported physical locator format');
 const rows=loaded.body.components;need(new Set(rows.map(r=>r.component_id)).size===rows.length,'Duplicate physical locator identity');
 return new Map(rows.map(r=>[r.component_id,r.comparison_product]));
}
function physicalProduct(handoff,name,report,acquisitions){
 const matches=handoff.scope.physical_restoration?.restorations?.filter(p=>p.path===name);
 need(matches?.length===1&&/^(components|sources)-\d{3}\.jsonl\.gz$/.test(name),'Missing/ambiguous restored physical product: '+name);
 const r=matches[0];
 const reused=handoff.scope.reused_whole_product_inputs===undefined?[]:handoff.scope.reused_whole_product_inputs;
 need(Array.isArray(reused)&&reused.every(p=>p?.whole_body_consumed===false),'Malformed reused whole physical product custody');
 // The unchanged handoff retains its honest prior-consumption annotations.
 // These ordinary pins request future acquisition of the actual whole bodies.
 const declared=[...handoff.scope.consumed_inputs,...reused];
 const paths=new Set(declared.filter(p=>p.bytes===r.whole_original_bytes&&p.sha256===r.whole_original_sha256).map(p=>p.path));
 const candidates=declared.filter(p=>paths.has(p.path));
 need(candidates.every(p=>p.blob===undefined||p.git_blob_oid===undefined||p.blob===p.git_blob_oid),
 'Conflicting physical product blob aliases: '+name);
 const sources=uniquePins(candidates.map(p=>({...identity(p),
  ...(p.uncompressed_bytes===undefined?{}:{uncompressed_bytes:p.uncompressed_bytes}),
  ...(p.uncompressed_sha256===undefined?{}:{uncompressed_sha256:p.uncompressed_sha256})})));
 need(sources.length>0,'No exact whole physical product pin: '+name);
 sources.forEach(validateOperatorPin);
 need(sources.every(p=>(p.uncompressed_bytes===undefined||p.uncompressed_bytes===r.decoded_bytes)
  &&(p.uncompressed_sha256===undefined||p.uncompressed_sha256===r.decoded_sha256)),
 'Conflicting decoded physical product identity: '+name);
 const source=operatorPin(sources[0]);validateOperatorPin(source);
 const destination='.cache/additive-native-gap-repair/delivery/'+source.sha256+'/'+name;
 acquisitions.push({source,destination,role:'physical-product'});
 return {kind:'original-report-product',path:destination,mode:'100644',bytes:r.whole_original_bytes,sha256:r.whole_original_sha256,
  uncompressed_bytes:r.decoded_bytes,uncompressed_sha256:r.decoded_sha256,report_sha256:report.sha256,original_product_path:name};
}
function adminProducts(handoff,pool){
 const records=handoff.scope.consumed_source_bindings;need(Array.isArray(records)&&records.length,'Missing consumed administrative source bindings');
 const result=[];
 for(const record of records){
  need(typeof record?.source_id==='string'&&record.source_id.length,'Missing administrative source identity');
  const custody=record.original_source_custody;
  need(custody===undefined||(custody&&typeof custody==='object'&&!Array.isArray(custody)
   &&custody.source_id===record.source_id&&custody.catalogue_record!==undefined),'Conflicting administrative source custody identity');
  const catalogues=[record.catalogue_record,custody?.catalogue_record].filter(value=>value!==undefined);
  need(catalogues.length&&catalogues.every(value=>value&&typeof value==='object'&&!Array.isArray(value)
   &&Array.isArray(value.parts)&&value.parts.length),'Incomplete administrative product parts');
  need(catalogues.every(value=>equal(value,catalogues[0])),'Conflicting administrative catalogue aliases');
  const catalogue=catalogues[0];
  need((catalogue.key===undefined||catalogue.key===record.source_id)
   &&(record.whole_bytes===undefined||record.whole_bytes===catalogue.original_bytes)
   &&(record.whole_sha256===undefined||record.whole_sha256===catalogue.original_sha256),
  'Conflicting administrative catalogue source identity');
  for(const part of catalogue.parts){const found=pool.filter(p=>p.path===part?.path&&['bytes','sha256','uncompressed_bytes','uncompressed_sha256'].every(k=>p[k]===part[k]));
   need(found.length&&found.every(p=>equal(p,found[0])),'Missing/ambiguous exact administrative input pin: '+part?.path);result.push(found[0]);}}
 return uniquePins(result);
}
const sourceKeys=['cases_path','outcomes_path','payloads_path','simplified_comparison_path','generalized_comparison_path','remainders_path'];
const nativeKeys=['source_request_path','operating_path','publication_path','facts_path','inventory_path'];
function nativeInvariant(request){const r=structuredClone(request);for(const k of ['destination','processing_allowance','output_reserve','operating_limits'])delete r[k];for(const k of [...nativeKeys,'scope_ids','source_execution_commit','source_runtime','inputs','owner_parts'])delete r.additive[k];return r;}
function sourceCommon(request){const r=request.source_rule,removed=new Set([...sourceKeys.map(k=>r[k]),r.registry_path,...r.original_products.map(p=>p.path),...r.administrative_products.map(p=>p.path),...r.target_banks]);return r.inputs.filter(p=>!removed.has(p.path));}

function materializeRecipe(recipe,reader){
 need(recipe?.version===1&&['greedy-model','retained-groups','explicit-groups'].includes(recipe.mode)&&/^[a-z0-9-]+$/.test(recipe.id),'Explicit admitted delivery recipe required');
 if(recipe.mode==='greedy-model')need(safe(recipe.destination_prefix)&&recipe.destination_prefix.startsWith('.cache/native-grid-candidates/'),'Fresh candidate destination prefix required');
 const registry=read(reader,recipe.registry);need(registry.body.version===1&&registry.body.kind==='accepted-administrative-handoffs-v1'&&Array.isArray(registry.body.entries),'Accepted registry required');
 const products={},groups=[],acquisitions=[],allIds=new Set();
 function emit(id,handoff,source,native,locators={}){
  validateTemplateIdentity(source);validateTemplateIdentity(native);
  const component_ids=source.source_rule.expected_ids;
  need(unique(component_ids)&&component_ids.every(x=>!allIds.has(x)),'Duplicate/empty recipe scope');component_ids.forEach(x=>allIds.add(x));
  need(equal(native.additive.scope_ids,component_ids),'SOURCE/NATIVE scope differs');
  const sourceName=id+'-source-template.json',nativeName=id+'-native-template.json';
  need(!products[sourceName],'Duplicate group label');products[sourceName]=bytes(source);products[nativeName]=bytes(native);
  const group={id,handoff_id:handoff.entry.id,component_ids,source_template:sourceName,native_template:nativeName,
   source_destination:recipe.mode!=='greedy-model'?source.destination:recipe.destination_prefix+'-'+id+'-source',native_destination:recipe.mode!=='greedy-model'?native.destination:recipe.destination_prefix+'-'+id+'-native',...locators};
  groups.push(group);
  for(const [stage,request] of [['source',source],['native',native]])for(const p of [request.report,...request.baseline.pins,...(request.source_rule??request.additive).inputs]){
   if(p.kind||(recipe.mode==='greedy-model'&&stage==='native'&&nativeKeys.some(k=>request.additive[k]===p.path)))continue;acquisitions.push({source:operatorPin(p),destination:p.path,role:stage+'-input'});}
 }
 if(recipe.mode!=='greedy-model'){
  const explicit=recipe.mode==='explicit-groups';
  need((explicit?recipe.compatibility===undefined:recipe.compatibility==='literal-historical-v1')&&Array.isArray(recipe.groups)&&recipe.groups.length,'Explicit admitted groups required');
  const cover=new Map();
  for(const g of recipe.groups){need(/^[a-z0-9-]+$/.test(g.id)&&(explicit?unique(g.component_ids):g.component_ids===undefined),'Explicit unique subset or original replay scope required');
   const h=accepted(reader,registry,g),source=read(reader,g.source_template).body,native=read(reader,g.native_template).body,r=source.source_rule;
   need(source.operation==='retained-land-source-premises-v1'&&native.operation==='unactivated-additive-native-batch-v1'&&r?.profile==='retained-consumed-administrative-source'&&equal(r.cohort_ids,h.entry.cohort_ids)&&r.registry_path===registry.pin.path&&r.cases_path===h.pin.path&&equal(r.inputs.find(p=>p.path===r.cases_path),h.pin),'Replay template differs from accepted whole handoff');
   need(unique(r.expected_ids)&&equal(r.expected_ids,h.entry.cohort_ids.filter(id=>r.expected_ids.includes(id)))&&equal(native.baseline,source.baseline),'Replay original ordered scope differs');
   if(explicit){
    need(source.operating_profile==='source-native-v2'&&native.operating_profile==='source-native-v2'&&equal(g.component_ids,r.expected_ids),'Explicit groups require genuine v2 templates with the exact ordered subset');
    need(equal(native.report,source.report)&&equal(native.parent,source.parent),'SOURCE/NATIVE report or parent identity differs');
    const targets=[...new Set(h.rows.filter(row=>g.component_ids.includes(row.component_id)).map(row=>row.retained_payload.target_stable_location_id))].sort();
    need(unique(g.target_ids)&&equal([...g.target_ids].sort(),targets),'Explicit subset target identities differ from accepted rows');
   }
   const prior=cover.get(h.entry.id)??[];cover.set(h.entry.id,[...prior,...r.expected_ids]);
   emit(g.id,h,source,native,{source_locator:g.source_template,native_locator:g.native_template});
  }
  if(!explicit)for(const [id,ids]of cover){const entry=registry.body.entries.find(e=>e.id===id);need(equal([...ids].sort(),[...entry.cohort_ids].sort()),'Replay omitted accepted handoff components');}
 }else{
  need(recipe.compatibility===undefined&&Array.isArray(recipe.handoffs)&&recipe.handoffs.length,'New admitted handoffs required');
  for(const selection of recipe.handoffs){
   need(selection.component_ids===undefined&&selection.groups===undefined,'Component/group lists are not new recipe inputs');
   const h=accepted(reader,registry,selection),sourceBase=structuredClone(read(reader,selection.source_template).body);
   for(const key of ['processing_allowance','output_reserve','operating_limits'])delete sourceBase[key];
   need(sourceBase.operating_profile==='source-native-v2'&&sourceBase.operation==='retained-land-source-premises-v1'&&sourceBase.source_rule?.profile==='retained-consumed-administrative-source'&&sourceBase.source_rule.geometry_scope==='full-component','Registered administrative full-component recipe required');
   need(Array.isArray(selection.targets)&&selection.targets.length&&new Set(selection.targets.map(t=>t.target_id)).size===selection.targets.length,'Explicit unique target mapping required');
   const targetMap=new Map(selection.targets.map(t=>{const n=structuredClone(read(reader,t.native_template).body);for(const key of ['processing_allowance','output_reserve','operating_limits'])delete n[key];need(n.operating_profile==='source-native-v2'&&n.operation==='unactivated-additive-native-batch-v1'&&n.additive?.source_profile===sourceBase.source_rule.profile&&equal(n.baseline,sourceBase.baseline)&&equal(n.report,sourceBase.report)&&equal(n.parent,sourceBase.parent),'Native recipe baseline/report/parent differs');return [t.target_id,{...t,native:n}];}));
   need(equal([...targetMap.keys()].sort(),[...h.entry.target_ids].sort()),'Target mapping must cover exactly the accepted handoff');
   const pool=uniquePins([...sourceBase.source_rule.inputs,...[...targetMap.values()].flatMap(t=>t.native.additive.inputs)]);
   const admin=adminProducts(h,pool),locators=locatorMap(reader,selection,h),physical=h.scope.original_physical_comparison_bindings;
   need(Array.isArray(physical)&&new Set(physical.map(p=>p.component_id)).size===physical.length,'Unique physical comparison bindings required');
   const sourceProducts=h.scope.physical_restoration.restorations.filter(p=>/^sources-\d{3}\.jsonl\.gz$/.test(p.path)).map(p=>p.path);need(sourceProducts.length,'Missing complete queried source metadata product');
   const rows=h.rows.map(row=>{const bindings=physical.filter(p=>p.component_id===row.component_id);need(bindings.length===1&&bindings[0].physical_comparison?.row?.component_id===row.component_id,'Missing exact component physical comparison');const direct=directProduct(bindings[0]),mapped=locators?.get(row.component_id);need(!direct||!mapped||direct===mapped,'Physical locator conflicts with handoff');const original=direct??mapped;need(original,'Missing per-case physical-product locator');const target=targetMap.get(row.retained_payload.target_stable_location_id);return {id:row.component_id,original,target};});
   let ordinal=0;
   function construct(members){
    const id=recipe.id+'-'+String(groups.length+1).padStart(3,'0'),nativeBase=members[0].target.native;
    need(members.every(r=>equal(nativeInvariant(r.target.native),nativeInvariant(nativeBase))),'Mixed native method/runtime recipe');
    const originals=[...new Set([...members.map(r=>r.original),...sourceProducts])].map(name=>physicalProduct(h,name,sourceBase.report,acquisitions));
    const banks=uniquePins(members.map(r=>{const found=r.target.native.additive.inputs.filter(p=>p.path===r.target.bank_path);need(found.length===1,'Target mapping bank lacks exact exemplar pin');return found[0];}));
    const rule={...structuredClone(sourceBase.source_rule),cohort_ids:h.entry.cohort_ids,expected_ids:members.map(r=>r.id),registry_path:registry.pin.path,
     ...Object.fromEntries(sourceKeys.map(k=>[k,h.pin.path])),administrative_products:admin,original_products:originals.map(p=>({original_product_path:p.original_product_path,path:p.path})),target_banks:banks.map(p=>p.path)};
    rule.inputs=uniquePins([...sourceCommon(sourceBase),h.pin,operatorPin(registry.pin),...originals,...admin,...banks]);
    const source={...sourceBase,destination:recipe.destination_prefix+'-'+id+'-source',source_rule:rule};
    const ownerParts=new Map(),nativeExtra=[];
    for(const member of members){const n=member.target.native,s=n.additive;for(const part of s.owner_parts??[]){const old=ownerParts.get(part.path);need(!old||equal(old,part),'Conflicting native owner operand');ownerParts.set(part.path,part);}
     const sourceNames=new Set([...sourceBase.source_rule.inputs.map(p=>p.path),...sourceKeys.map(k=>sourceBase.source_rule[k]),...nativeKeys.map(k=>s[k])]);
     // Keep only expressly admitted native owner/bounds/latitude/manifest operands.
     const needed=new Set([s.manifest_path,s.bounds_path,s.latitudes_path,...(s.owner_parts??[]).map(p=>p.path)]);
     nativeExtra.push(...s.inputs.filter(p=>needed.has(p.path)&&!sourceNames.has(p.path)));}
    const s=nativeBase.additive,slots=nativeKeys.map(k=>{const p=s.inputs.filter(p=>p.path===s[k]);need(p.length===1,'Native exemplar lacks five real predecessor slots');return p[0];});
    const native={...nativeBase,destination:recipe.destination_prefix+'-'+id+'-native',additive:{...s,scope_ids:rule.expected_ids,owner_parts:[...ownerParts.values()],inputs:uniquePins([...rule.inputs,...nativeExtra,...slots])}};
    return {id,source,native};
   }
   let pending=[];
   for(const row of rows){
    if(pending.length&&!equal(nativeInvariant(pending[0].target.native),nativeInvariant(row.target.native))){const built=construct(pending);emit(built.id,h,built.source,built.native);pending=[];}
    pending.push(row);ordinal++;
   }
   if(pending.length){const built=construct(pending);emit(built.id,h,built.source,built.native);}
   need(ordinal===h.entry.cohort_ids.length,'Incomplete recipe materialization');
  }
 }
 const transport=new Map();
 for(const item of acquisitions){const p=item.source;validateOperatorPin(p);const key=sha(bytes({mode:p.mode,bytes:p.bytes,sha256:p.sha256,uncompressed_bytes:p.uncompressed_bytes??null,uncompressed_sha256:p.uncompressed_sha256??null}));const prior=transport.get(key)??{identity:key,source:p,destinations:[],uses:[]};if(!prior.destinations.includes(item.destination))prior.destinations.push(item.destination);if(!prior.uses.includes(item.role))prior.uses.push(item.role);transport.set(key,prior);}
 const acquisition_plan={version:1,kind:'transport-only-deduplicated-input-plan',products:[...transport.values()],unique_encoded_bytes:add([...transport.values()].map(p=>p.source.bytes)),limits:['Acquisition reuse only. Every operator phase authenticates its complete issued input closure.']};
 const index={version:1,mode:recipe.mode,registry:registry.pin,...(recipe.compatibility?{compatibility:recipe.compatibility}:{}),groups,acquisition_plan,limits:['Metadata planning is not source approval, execution, or current-bank qualification.','Native templates retain real exemplar slots only until genuine SOURCE results replace them; templates must never execute directly.']};
 products['recipe-index.json']=bytes(index);return {products,groups,index,acquisition_plan};
}
return {materializeRecipe};
})();

// Existing-contract constructor, scoped to avoid mixing scientific identities.
export const {constructOriginalAuthority, constructAuthorityRegistry} = (() => {
// Scratch integration fragment. Replace only the two absolute import specifiers
// with their normal relative repository imports in delivery-handoff-advance.mjs.
// These constructors read committed evidence and never execute a science operator.

const need = (ok, message) => { if (!ok) throw Error(message); };
const sha = raw => createHash('sha256').update(raw).digest('hex');
const same = (a, b) => valueBytes(a).equals(valueBytes(b));
const safe = name => typeof name === 'string' && !name.startsWith('/') && !name.includes('\\') && !name.includes('\0')
  && name.split('/').every(part => part && part !== '.' && part !== '..');
const identity = p => ({commit: p.commit, path: p.path, mode: p.mode, git_blob_oid: p.git_blob_oid ?? p.blob, bytes: p.bytes, sha256: p.sha256});

function exactLocator(locator) {
  need(locator && Object.keys(locator).sort().join(',') === 'commit,path'
    && /^[a-f0-9]{40}$/.test(locator.commit) && safe(locator.path),
  'Supply exact commit/path locators only; derived hashes and IDs are not inputs');
  return locator;
}

// The declared decoded identity is read from a committed publication, never from
// caller-authored derived fields. The actual bytes must agree before it escapes.
function committedBody(reader, locator, declared = null, parse = false) {
  exactLocator(locator);
  const {commit, path: name} = locator, d = reader.descriptor(name, commit);
  const encoded = reader.read(name, {version: commit});
  const pin = {...identity({...d, sha256: sha(encoded)})};
  let raw = encoded;
  if (declared?.uncompressed_bytes !== undefined) {
    raw = gunzipSync(encoded);
    pin.uncompressed_bytes = raw.length; pin.uncompressed_sha256 = sha(raw);
  }
  if (declared) for (const key of ['bytes', 'sha256', 'uncompressed_bytes', 'uncompressed_sha256'])
    need(pin[key] === declared[key], 'Committed publication/member differs: ' + name + ' ' + key);
  return {pin, ...(parse ? {body: JSON.parse(raw)} : {})};
}

function publicationMembers(reader, locator) {
  need(path.posix.basename(exactLocator(locator).path) === 'publication.json', 'Locate the committed publication.json');
  const {pin, body} = committedBody(reader, locator, null, true);
  need(body.version === 1 && body.complete === true && body.facts && body.inventory, 'Missing complete committed publication');
  const member = name => ({commit: pin.commit, path: path.posix.join(path.posix.dirname(pin.path), name)});
  const facts = committedBody(reader, member('facts.json'), body.facts, true);
  const inventory = committedBody(reader, member('inventory.jsonl.gz'), body.inventory);
  return {pin, body, facts, inventory, member};
}

function deriveOriginalBinding(reader, inputs) {
  need(inputs && Object.keys(inputs).sort().join(',') === 'native_operating,native_publication,source_publication', 'Require SOURCE publication, NATIVE publication and NATIVE operating locators');
  for (const locator of Object.values(inputs)) exactLocator(locator);
  const source = publicationMembers(reader, inputs.source_publication);
  const native = publicationMembers(reader, inputs.native_publication);
  const issued = (facts, kind) => {
    const old = facts.body.request;
    need(old && old.commit && old.path, 'Missing original ' + kind + ' issued request locator');
    const result = committedBody(reader, {commit: old.commit, path: old.path}, null, true);
    need(same(result.pin, identity(old)), 'Original ' + kind + ' issued request descriptor differs');
    return result;
  };
  const sourceRequest = issued(source.facts, 'SOURCE'), nativeRequest = issued(native.facts, 'NATIVE');
  const spec = nativeRequest.body.additive;
  need(spec && Array.isArray(spec.inputs), 'Missing native SOURCE predecessor');
  const aliases = [];
  for (const [key, published] of [['facts_path', source.facts.pin], ['publication_path', source.pin], ['inventory_path', source.inventory.pin]]) {
    const matches = spec.inputs.filter(p => p.path === spec[key]);
    need(matches.length === 1, 'Missing/duplicate original SOURCE predecessor: ' + key);
    const original = matches[0];
    if (original.kind === 'completed-inventory-body') aliases.push({original, published});
    else need(same(identity(original), identity(published)), 'Native SOURCE predecessor points to another committed body: ' + key);
  }
  need(Array.isArray(native.body.assets) && native.body.assets.length > 0,
    'Missing native publication asset roster');
  const names = native.body.assets.map(p => p.path);
  need(new Set(names).size === names.length && names.every(n => safe(n) && !n.includes('/')), 'Duplicate/unsafe native publication asset');
  const assets = native.body.assets.map(p => committedBody(reader, native.member(p.path), p).pin);
  const manifest = assets.filter(p => path.posix.basename(p.path) === 'base-native-manifest.json');
  const envelopes = native.body.assets.filter(p => p.path === 'release-envelope.json');
  need(envelopes.length === 1, 'Native publication omits its release envelope');
  const envelope = committedBody(reader, native.member(envelopes[0].path), envelopes[0], true).body;
  const ledgerRole = envelope.additiveRelease?.ledger;
  need(ledgerRole && safe(ledgerRole.path) && ledgerRole.path.startsWith('additive-repairs/'), 'Missing published original ledger role');
  const ledger = assets.filter(p => path.posix.basename(p.path) === path.posix.basename(ledgerRole.path)
    && p.bytes === ledgerRole.bytes && p.sha256 === ledgerRole.sha256);
  need(manifest.length === 1 && ledger.length === 1, 'Native publication omits its unique base manifest or original ledger');
  const operating = committedBody(reader, inputs.native_operating).pin;
  return {version: 1, kind: 'original-issued-rule-source-custody-v1',
    original_pins: {source_request: sourceRequest.pin, source_facts: source.facts.pin, native_request: nativeRequest.pin,
      native_facts: native.facts.pin, native_manifest: manifest[0], ledger: ledger[0]},
    ...(aliases.length ? {source_output_aliases: aliases} : {}),
    native_proof: {publication: native.pin, inventory: native.inventory.pin, operating, assets}};
}

function constructOriginalAuthority(reader, inputs) {
  need(reader instanceof ImmutableReader, 'Require the existing ImmutableReader');
  if (inputs.source_evidence !== undefined) {
    need(Object.keys(inputs).sort().join(',') === 'native_patch,source_evidence', 'Source-target authority requires two immutable inputs');
    const source = committedBody(reader, inputs.source_evidence), patch = committedBody(reader, inputs.native_patch);
    const binding = {version:1,kind:'source-target-native-custody-v1',source_evidence:source.pin,native_patch:patch.pin};
    const preimage = {...binding,kind:'source-target-native-rule-v1'};
    const proof = qualifySourceTargetNativeAuthority(reader,preimage,binding);
    return {products:{'original-rule-preimage.json':valueBytes(preimage),'authority-binding.json':valueBytes(binding)},
      component_ids:proof.source_scope_ids,ledger_rows:proof.original_ledger.rows,rule_sha256:valueSha(preimage),limitations:proof.limitations,
      ...(Object.hasOwn(proof,'physical_context_hits') ? {physical_context_hits:proof.physical_context_hits} : {}),
      ...(Object.hasOwn(proof,'territorial_contacts') ? {territorial_contacts:proof.territorial_contacts} : {})};
  }
  const binding = deriveOriginalBinding(reader, inputs);
  const custody = readOriginalRuleAuthority(reader, binding.original_pins, binding.source_output_aliases ?? []);
  qualifyOriginalSourceAuthority(custody);
  const native = qualifyOriginalNativeAuthority(custody, binding.native_proof);
  return {products: {'original-rule-preimage.json': valueBytes(custody.rule_preimage), 'authority-binding.json': valueBytes(binding)},
    component_ids: [...custody.source_scope_ids], ledger: binding.original_pins.ledger, rule_sha256: custody.rule_sha256,
    limitations: native.limitations};
}

// Invoke only after the preceding bodies are committed. Policy is the existing
// selected-consumer policy; the complete original program is re-authenticated by
// readRetainedRegistryAuthority. A registry alone never approves selection.
function constructAuthorityRegistry(reader, authorities) {
  need(reader instanceof ImmutableReader && Array.isArray(authorities) && authorities.length > 0,
    'Require committed authority pairs and existing ImmutableReader');
  const entries = [], seen = new Set(), components = new Set();
  function committedEntry(locators) {
    need(locators && Object.keys(locators).sort().join(',') === 'rule_preimage,source_authority', 'Require committed preimage/binding locators only');
    for (const locator of Object.values(locators)) exactLocator(locator);
    const rule = committedBody(reader, locators.rule_preimage, null, true), binding = committedBody(reader, locators.source_authority);
    need(rule.pin.sha256 === valueSha(rule.body), 'Original rule preimage is not the canonical complete body');
    const body = {policy_id: 'retained-source-literal-additions', policy_version: 1, rule_sha256: rule.pin.sha256,
      rule_preimage: rule.pin, source_authority: binding.pin};
    const entry = {authority_sha256: valueSha(body), ...body};
    need(!seen.has(entry.authority_sha256), 'Duplicate committed original authority'); seen.add(entry.authority_sha256);
    const proof = readRetainedRegistryAuthority(reader, entry);
    return {entry, scope: [...proof.source_scope_ids]};
  }
  for (const locators of authorities) {
    const {entry, scope} = committedEntry(locators);
    for (const id of scope) { need(!components.has(id), 'Overlapping original authority component'); components.add(id); }
    entries.push(entry);
  }
  entries.sort((a, b) => a.authority_sha256.localeCompare(b.authority_sha256));
  return {'authority-registry.json': valueBytes({version: 1, kind: 'retained-rule-authority-registry-v1', entries})};
}
return {constructOriginalAuthority, constructAuthorityRegistry};
})();

export function deliveryAuthorityReader(root, pinReader) {
  const git = pinReader.git;
  class DeliveryReader extends ImmutableReader {
    git(...args) { return git(...args); }
  }
  return new DeliveryReader(root, git('rev-parse', 'HEAD').toString().trim());
}

// Reuse the already authenticated gh account only at an actual cold fetch.
// The token stays in this one subprocess environment; no credential is created
// or persisted, and warm verification never consults account credentials.
export function deliveryAcquisitionExecute({execute = execFileSync,
  readToken = () => execFileSync('gh', ['auth', 'token'], {encoding: 'utf8', maxBuffer: 16384, timeout: 20_000}).trim()} = {}) {
  let token;
  return (command, args, options) => {
    if (command === 'git' && args.includes('fetch')) {
      need(args.includes('https://github.com/ChengshuLi/WorldAtlas.git'), 'Unexpected acquisition repository');
      token ??= readToken(); need(typeof token === 'string' && token.trim(), 'Existing gh login required for cold acquisition');
      const env = {...options.env, GIT_CONFIG_COUNT: '3',
        GIT_CONFIG_KEY_2: 'http.https://github.com/.extraheader',
        GIT_CONFIG_VALUE_2: 'AUTHORIZATION: basic ' + Buffer.from('x-access-token:' + token).toString('base64')};
      return execute(command, args, {...options, env});
    }
    return execute(command, args, options);
  };
}

// Exact-body acquisition reuses the existing prefetch importer and ordinary writer.
export const {acquireDeliveryInputs} = (() => {
// Thin adapter for the existing exact Git object acquisition. It does not
// decode scientific records, restore logical products or execute operators.
const need=(v,m)=>{if(!v)throw Error(m);};
const sha=raw=>createHash('sha256').update(raw).digest('hex');
const oid=raw=>createHash('sha1').update('blob '+raw.length+'\0').update(raw).digest('hex');
const hex=(s,n)=>typeof s==='string'&&new RegExp(`^[a-f0-9]{${n}}$`).test(s);
const canonical=v=>Array.isArray(v)?v.map(canonical):v&&typeof v==='object'?Object.fromEntries(Object.keys(v).sort().map(k=>[k,canonical(v[k])])):v;
const bytes=v=>Buffer.from(JSON.stringify(canonical(v))+'\n');
const safe=s=>typeof s==='string'&&!path.isAbsolute(s)&&/^[A-Za-z0-9_.\/-]+$/.test(s)&&s.split('/').every(x=>x&&x!=='.'&&x!=='..');
const bodyIdentity=p=>({mode:p.mode,bytes:p.bytes,sha256:p.sha256,uncompressed_bytes:p.uncompressed_bytes??null,uncompressed_sha256:p.uncompressed_sha256??null});

// Narrow extraction of canonical-restoration.mjs ordinary/read/writeExactObject:
// an existing destination is reauthenticated, never overwritten. Interrupted
// incomplete members remain a refusal; completed members are safe to resume.
function ordinaryPath(root,relative){
 need(safe(relative)&&path.isAbsolute(root)&&fs.realpathSync(root)===root,'Ordinary acquisition root/path required');
 let current=root;for(const part of relative.split('/')){current=path.join(current,part);const stat=fs.lstatSync(current,{throwIfNoEntry:false});if(stat)need(!stat.isSymbolicLink()&&(current===path.join(root,relative)?stat.isFile():stat.isDirectory()),'Nonordinary acquisition destination');}return current;
}
function readExactFile(root,relative,pin){
 const name=ordinaryPath(root,relative),stat=fs.lstatSync(name,{throwIfNoEntry:false});if(!stat)return null;
 need(stat.isFile()&&stat.size===pin.bytes&&(stat.mode&0o777)===0o644,'Existing acquisition body size/mode differs');
 const fd=fs.openSync(name,fs.constants.O_RDONLY|fs.constants.O_NOFOLLOW);
 try{const opened=fs.fstatSync(fd);need(opened.isFile()&&opened.dev===stat.dev&&opened.ino===stat.ino&&opened.size===stat.size,'Acquisition file identity drift');const raw=Buffer.alloc(pin.bytes+1);let n=0;
  while(n<raw.length){const count=fs.readSync(fd,raw,n,raw.length-n,null);if(!count)break;n+=count;}
  const after=fs.fstatSync(fd),current=fs.lstatSync(name);need(n===pin.bytes&&after.size===stat.size&&after.mtimeMs===opened.mtimeMs&&after.ctimeMs===opened.ctimeMs&&current.dev===opened.dev&&current.ino===opened.ino&&!current.isSymbolicLink(),'Acquisition file changed during read');
  const body=raw.subarray(0,n);need(sha(body)===pin.sha256&&oid(body)===(pin.git_blob_oid??pin.blob),'Existing acquisition body hash differs');return body;
 }finally{fs.closeSync(fd);}
}
function writeExactFile(root,relative,pin,raw){
 need(raw.length===pin.bytes&&sha(raw)===pin.sha256&&oid(raw)===(pin.git_blob_oid??pin.blob),'Materialized source bytes differ');
 if(readExactFile(root,relative,pin))return false;
 const file=ordinaryPath(root,relative);fs.mkdirSync(path.dirname(file),{recursive:true});ordinaryPath(root,relative);
 fs.writeFileSync(file,raw,{flag:'wx',mode:0o644});readExactFile(root,relative,pin);return true;
}

async function acquireDeliveryInputs(plan,root,{execute=execFileSync,token,onMaterialized=()=>{}}={}){
 need(plan?.version===1&&plan.kind==='transport-only-deduplicated-input-plan'&&Array.isArray(plan.products)&&plan.products.length>0,'Complete delivery acquisition plan required');
 need(path.isAbsolute(root)&&fs.realpathSync(root)===root,'Actual ordinary acquisition root required');
 const rows=[],objects=new Map(),destinations=new Map(),descriptors=new Map();let declared=0;
 for(const item of plan.products){
  const p=item.source;need(p&&safe(p.path)&&hex(p.commit,40)&&p.mode==='100644'&&hex(p.git_blob_oid??p.blob,40)&&hex(p.sha256,64)&&Number.isSafeInteger(p.bytes)&&p.bytes>=0,'Complete immutable acquisition pin required');
  need(p.git_blob_oid===undefined||p.blob===undefined||p.git_blob_oid===p.blob,'Conflicting acquisition object aliases');
  need((p.uncompressed_bytes===undefined)===(p.uncompressed_sha256===undefined),'Incomplete decoded acquisition identity');
  if(p.uncompressed_bytes!==undefined)need(Number.isSafeInteger(p.uncompressed_bytes)&&p.uncompressed_bytes>=0&&hex(p.uncompressed_sha256,64),'Complete decoded acquisition identity required');
  need(item.identity===sha(bytes(bodyIdentity(p)))&&Array.isArray(item.destinations)&&item.destinations.length>0,'Acquisition identity/destination inventory differs');
  declared+=p.bytes;need(Number.isSafeInteger(declared),'Invalid acquisition aggregate');
  const key=p.git_blob_oid??p.blob,old=objects.get(key);
  need(!old||(old.pin.bytes===p.bytes&&old.pin.sha256===p.sha256&&old.pin.mode===p.mode),'Conflicting immutable acquisition body');
  const group=old??{pin:p,pins:[],destinations:new Set()};group.pins.push(p);objects.set(key,group);
  const descriptorKey=p.commit+':'+p.path,prior=descriptors.get(descriptorKey);
  need(!prior||(prior.git_blob_oid??prior.blob)===key,'Conflicting immutable acquisition path');descriptors.set(descriptorKey,p);
  for(const destination of item.destinations){
   need(safe(destination),'Unsafe acquisition destination');
   if(destination===p.path)continue; // Immutable consumers read this from Git.
   need(destination.startsWith('.cache/additive-native-gap-repair/delivery/'+p.sha256+'/'),'Only content-addressed physical aliases may be materialized');
   const before=destinations.get(destination);need(!before||before===key,'Conflicting materialization destination');
   destinations.set(destination,key);group.destinations.add(destination);
  }
  rows.push(p);
 }
 need(plan.unique_encoded_bytes===declared,'Declared acquisition aggregate differs');
 for(const [destination,key]of destinations)readExactFile(root,destination,objects.get(key).pin);
 const acquisition=createAcquisition({repo:root,token,execute,loadDescriptor:async(version,name)=>{const p=descriptors.get(version+':'+name);need(p,'Undeclared acquisition metadata');return {type:'blob',mode:p.mode,sha:p.git_blob_oid??p.blob,size:p.bytes};}});
 const admitted=[];
 for(const p of rows)admitted.push(await acquisition.descriptor(p.commit,p.path,{mode:p.mode,git_blob_oid:p.git_blob_oid??p.blob,bytes:p.bytes,sha256:p.sha256}));
 acquisition.acquire(admitted); // Existing import checks and missing-OID resume.
 const gitEnv=Object.fromEntries(Object.entries(process.env).filter(([key])=>!key.startsWith('GIT_')));
 Object.assign(gitEnv,{GIT_NO_LAZY_FETCH:'1',GIT_NO_REPLACE_OBJECTS:'1',GIT_CONFIG_NOSYSTEM:'1',GIT_CONFIG_GLOBAL:'/dev/null',GIT_TERMINAL_PROMPT:'0'});
 const outcomes=[];let bodyReads=0;
 for(const [key,group] of objects){
  const raw=execute('git',['-c','core.hooksPath=/dev/null','-C',root,'cat-file','blob',key],{env:gitEnv,maxBuffer:group.pin.bytes+1,timeout:60000,stdio:['ignore','pipe','pipe']});bodyReads++;
  need(Buffer.isBuffer(raw)&&raw.length===group.pin.bytes&&sha(raw)===group.pin.sha256&&oid(raw)===key,'Acquired body changed before materialization');
  const decodedPins=group.pins.filter(p=>p.uncompressed_bytes!==undefined);
  if(decodedPins.length){const decoded=gunzipSync(raw);for(const p of decodedPins)need(decoded.length===p.uncompressed_bytes&&sha(decoded)===p.uncompressed_sha256,'Acquired decoded identity differs');}
  for(const destination of group.destinations){const created=writeExactFile(root,destination,group.pin,raw);outcomes.push({path:destination,bytes:raw.length,sha256:group.pin.sha256,created});if(created)onMaterialized({path:destination,bytes:raw.length,sha256:group.pin.sha256});}
 }
 return {version:1,kind:'materialized-delivery-inputs-v1',plan_sha256:sha(bytes(plan)),status:'complete',...acquisition.stats,
  materialization_body_reads:bodyReads,materialized_files:outcomes.filter(p=>p.created).length,resumed_files:outcomes.filter(p=>!p.created).length,files:outcomes,
  limits:['Transport and exact-byte physical aliases only. Every scientific operator still authenticates its own complete inputs.','Completed objects/files resume by their actual identities; partial or corrupted destination files are refused and preserved.']};
}
return {acquireDeliveryInputs};
})();
