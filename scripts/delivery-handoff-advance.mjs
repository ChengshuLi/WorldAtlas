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
 acquisition.acquire(admitted); // Exact-OID import/resume; consumed bytes are authenticated below.
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
