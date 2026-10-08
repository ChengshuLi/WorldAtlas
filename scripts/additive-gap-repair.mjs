import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {gunzipSync, gzipSync} from 'node:zlib';
import {canonicalValue, footprintValueSha256} from '../src/effective-footprint.js';
import {candidateBudget, committedPreparationFiles, createNativeCandidateOutput, requirePlainExecution} from './native-ownership/native-preparation-guards.mjs';

export const INVENTORY_VERSION = 'complete-source-relative-gap-inventory-v1';
export const DISPOSITIONS = ['eligible', 'assigned', 'zero-cell', 'rejected', 'awaiting-evidence'];
const categories = new Set(['mapped-land-support', 'mapped-inland-water-support', 'mixed-source-support', 'outside-mapped-L1-context', 'unknown']);
const sha = raw => createHash('sha256').update(raw).digest('hex');
const canonical = value => Buffer.from(JSON.stringify(canonicalValue(value)) + '\n');
const hex = value => /^[a-f0-9]{64}$/.test(value ?? '');
function demand(value, message) { if (!value) throw Error(message); }
function safe(name) { return typeof name === 'string' && /^[a-zA-Z0-9_.\/-]+$/.test(name) && name.split('/').every(p => p && p !== '.' && p !== '..'); }

// A classification is never an authority to alter ownership. This first stage
// is immediately usable on the retained complete #1261 inventory, including
// every unknown. Repair admission consumes a separate whole source-rule proof.
export function candidateDisposition(row) {
  demand(typeof row?.component_id === 'string' && row.component_id && hex(row.candidate_feature_sha256)
    && hex(row.candidate_geometry_sha256) && categories.has(row.status), 'Incomplete original candidate record');
  demand(typeof row.physical_authority === 'string' && typeof row.physical_status === 'string'
    && Array.isArray(row.physical_limits), 'Missing original physical limits');
  return row.status === 'mapped-inland-water-support'
    ? {disposition: 'rejected', reason: 'source-relative-water; retained, not reassigned'}
    : {disposition: 'awaiting-evidence', reason: 'classification does not establish source fitness or target eligibility'};
}

export function inventoryRows(rows, {source, parent, expectedIds, expectedRosterSha256, originalRecordBytes}) {
  demand(parent?.version === 1 && Number.isSafeInteger(parent.components) && parent.components > 0
    && hex(parent.roster_sha256) && hex(parent.report_sha256), 'Missing independent complete parent denominator');
  demand(Array.isArray(expectedIds) && expectedIds.length && new Set(expectedIds).size === expectedIds.length
    && expectedIds.every(id => typeof id === 'string' && id), 'Missing exact independently selected IDs');
  const expected = new Set(expectedIds), seen = new Set(), counts = Object.fromEntries(DISPOSITIONS.map(key => [key, 0]));
  const sourceCounts = {}, identities = [], output = [];
  demand(Array.isArray(originalRecordBytes) && originalRecordBytes.length === rows.length
    && originalRecordBytes.every(raw=>Buffer.isBuffer(raw)), 'Complete original record byte boundaries required');
  rows.forEach((row, ordinal) => {
    demand(JSON.stringify(canonicalValue(JSON.parse(originalRecordBytes[ordinal]))) === JSON.stringify(canonicalValue(row)),
      'Original record bytes/value disagree');
    const decision = candidateDisposition(row), id = row.component_id;
    demand(expected.has(id) && !seen.has(id), 'Foreign or duplicate candidate identity');
    seen.add(id); counts[decision.disposition]++;
    sourceCounts[row.status] = (sourceCounts[row.status] ?? 0) + 1;
    identities.push({id, feature_sha256: row.candidate_feature_sha256});
    output.push({component_id: id, ...decision, source_relative_category: row.status,
      physical_authority: row.physical_authority, physical_status: row.physical_status,
      physical_limits: row.physical_limits, candidate_feature_sha256: row.candidate_feature_sha256,
      candidate_geometry_sha256: row.candidate_geometry_sha256,
      original: {source, ordinal, whole_record_sha256: sha(originalRecordBytes[ordinal])}});
  });
  demand(seen.size === expected.size, 'Missing candidate identity');
  const roster = footprintValueSha256(identities);
  demand(roster === expectedRosterSha256, 'Original ordered candidate roster changed');
  demand(output.length <= parent.components && Object.values(counts).reduce((a,b) => a+b,0) === output.length,
    'Disposition inventory is incomplete');
  return {rows: output, facts: {version: 1, operation: INVENTORY_VERSION, parent,
    components: output.length, complete_ordered_roster_sha256: roster, counts, source_relative_counts: sourceCounts,
    limits: ['Source-relative categories retained exactly; no physical approval, ownership or geometry change.',
      'Every original whole source body remains required for row restoration; aliases are not replacement geometry.']}};
}

export function joinInventoryFacts(children, parent) {
  demand(Array.isArray(children) && children.length, 'Missing inventory children');
  const ids = new Set(), ordered = [], counts = Object.fromEntries(DISPOSITIONS.map(key => [key,0])), sourceCounts = {};
  for (const child of children) {
    demand(JSON.stringify(canonicalValue(child.facts.parent)) === JSON.stringify(canonicalValue(parent))
      && child.facts.operation === INVENTORY_VERSION && child.rows.length === child.facts.components, 'Foreign inventory parent');
    const actualCounts = Object.fromEntries(DISPOSITIONS.map(key => [key,0]));
    for (const row of child.rows) {
      demand(!ids.has(row.component_id) && DISPOSITIONS.includes(row.disposition), 'Duplicate or invalid disposition');
      ids.add(row.component_id); actualCounts[row.disposition]++; counts[row.disposition]++;
      ordered.push({id: row.component_id, feature_sha256: row.candidate_feature_sha256});
      sourceCounts[row.source_relative_category] = (sourceCounts[row.source_relative_category] ?? 0)+1;
    }
    demand(JSON.stringify(actualCounts) === JSON.stringify(child.facts.counts), 'Child disposition totals changed');
    demand(footprintValueSha256(child.rows.map(row => ({id: row.component_id, feature_sha256: row.candidate_feature_sha256})))
      === child.facts.complete_ordered_roster_sha256, 'Child ordered inventory changed');
  }
  demand(ids.size === parent.components && footprintValueSha256(ordered) === parent.roster_sha256,
    'Incomplete or reordered complete parent inventory');
  return {version: 1, operation: 'complete-gap-inventory-join-v1', parent, components: ids.size, counts,
    source_relative_counts: sourceCounts, repair_authority: 'none; source-rule and selected-release stages remain required'};
}

function pinCost(pin) {
  demand(/^[a-f0-9]{40}$/.test(pin?.commit ?? '') && safe(pin.path) && ['100644','100755'].includes(pin.mode)
    && /^[a-f0-9]{40}$/.test(pin.blob ?? '') && hex(pin.sha256), 'Missing whole immutable input descriptor');
  demand(Number.isSafeInteger(pin.bytes) && pin.bytes >= 0 && pin.bytes <= 32*1024*1024, 'Ordinary input exceeds cap');
  if (pin.uncompressed_bytes !== undefined) demand(Number.isSafeInteger(pin.uncompressed_bytes)
    && pin.uncompressed_bytes >= 0 && pin.uncompressed_bytes <= 32*1024*1024 && hex(pin.uncompressed_sha256), 'Decoded whole input exceeds cap');
  return [{bytes: pin.bytes}, ...(pin.uncompressed_bytes === undefined ? [] : [{bytes:pin.uncompressed_bytes}])];
}
function readPin(repo, pin) {
  pinCost(pin);
  const tree = execFileSync('git',['-C',repo,'ls-tree','-z',pin.commit,'--',pin.path],{encoding:'utf8'});
  demand(tree === `${pin.mode} blob ${pin.blob}\t${pin.path}\0`, 'Immutable input mode/blob differs');
  const bytes = Number(execFileSync('git',['-C',repo,'cat-file','-s',pin.blob],{encoding:'utf8'}));
  demand(bytes === pin.bytes, 'Immutable input length differs');
  const raw = execFileSync('git',['-C',repo,'cat-file','blob',pin.blob],{maxBuffer:32*1024*1024});
  demand(sha(raw) === pin.sha256, 'Whole encoded input changed');
  if (pin.uncompressed_bytes === undefined) return raw;
  const decoded = gunzipSync(raw,{maxOutputLength:pin.uncompressed_bytes+1});
  demand(decoded.length === pin.uncompressed_bytes && sha(decoded) === pin.uncompressed_sha256, 'Whole decoded input changed');
  return decoded;
}
export function restoreInventoryRow(alias, originalRows, originalSource, originalRecordBytes) {
  demand(JSON.stringify(canonicalValue(alias.original?.source)) === JSON.stringify(canonicalValue(originalSource))
    && Number.isSafeInteger(alias.original.ordinal), 'Wrong original row source');
  const original = originalRows[alias.original.ordinal];
  demand(original?.component_id === alias.component_id && Buffer.isBuffer(originalRecordBytes?.[alias.original.ordinal])
    && sha(originalRecordBytes[alias.original.ordinal]) === alias.original.whole_record_sha256
    && JSON.stringify(canonicalValue(JSON.parse(originalRecordBytes[alias.original.ordinal]))) === JSON.stringify(canonicalValue(original)),
    'Original whole record inverse failed');
  return original;
}

export function admitInventoryDestination(repo, destination) {
  const sourceRoot = fs.realpathSync(repo);
  demand(/^\.cache\/native-grid-candidates\/[A-Za-z0-9_-]+$/.test(destination), 'Fresh offline destination required');
  let current = sourceRoot;
  for (const part of destination.split('/')) {
    current = path.join(current,part); const entry = fs.lstatSync(current,{throwIfNoEntry:false});
    if(entry) demand(current !== path.join(sourceRoot,destination) && entry.isDirectory() && !entry.isSymbolicLink()
      && fs.realpathSync(current) === current, 'Output collision or symlink parent');
  }
  return sourceRoot;
}

// One genuine detached whole-shard acquisition per invocation. The parent
// report supplies the complete denominator; an independently frozen scope
// supplies exact selected IDs/ordered feature hashes. No all-world JSON lives
// in this process. Parent joining is a subsequent bounded custody operation.
export function inventoryCommand({repo, commit, requestPin, destination}) {
  requirePlainExecution();
  const sourceRoot = admitInventoryDestination(repo,destination);
  demand(execFileSync('git',['-C',sourceRoot,'rev-parse','HEAD'],{encoding:'utf8'}).trim() === commit,
    'Executing immutable head differs');
  const runtimeStat = fs.lstatSync(process.execPath);
  demand(runtimeStat.isFile() && !runtimeStat.isSymbolicLink(), 'Installed runtime must be an ordinary whole executable');
  const codeNames = ['package.json','scripts/additive-gap-repair.mjs','src/effective-footprint.js',
    'scripts/native-ownership/native-preparation-guards.mjs','src/native-runtime.js',
    'scripts/native-ownership/compile-native-ownership.mjs','src/native-grid.js','scripts/audit-grid-intervals.mjs','node_modules/@noble/hashes/package.json'];
  const projectNames = codeNames.filter(name=>!name.startsWith('node_modules/')).concat('package-lock.json');
  const projectSizes = projectNames.map(name=>({bytes:fs.lstatSync(path.join(sourceRoot,name)).size}));
  candidateBudget([...projectSizes,...pinCost(requestPin)],{reserveBytes:runtimeStat.size+131072});
  const project = committedPreparationFiles(sourceRoot,commit,projectNames);
  const requestBudget = candidateBudget([...project, ...pinCost(requestPin)],{reserveBytes:runtimeStat.size+131072});
  const runtimeSha = sha(fs.readFileSync(process.execPath));
  const request = JSON.parse(readPin(sourceRoot,requestPin));
  demand(request.version === 1 && request.operation === INVENTORY_VERSION
    && JSON.stringify(canonicalValue(request.executed_code)) === JSON.stringify(canonicalValue(project)),
    'Foreign request operation/head');
  demand(typeof destination === 'string' && destination === request.destination && Array.isArray(request.expected_ids), 'Foreign output/scope');
  const outputReserve = request.output_reserve;
  demand(Number.isSafeInteger(outputReserve) && outputReserve >= 131072 && outputReserve <= 32*1024*1024, 'Explicit output reserve required');
  const dependencyNames = ['package.json','sha2.js','_md.js','_u64.js','utils.js'].map(name=>'node_modules/@noble/hashes/'+name);
  demand(Array.isArray(request.installed_modules) && request.installed_modules.length === dependencyNames.length
    && request.installed_modules.every((pin,i)=>pin.path === dependencyNames[i] && hex(pin.sha256)
      && Number.isSafeInteger(pin.bytes) && pin.bytes <= 32*1024*1024), 'Complete actual installed import closure required');
  const verifyModules = () => request.installed_modules.forEach(pin=>{
    const file = path.join(sourceRoot,pin.path), stat = fs.lstatSync(file);
    demand(stat.isFile() && !stat.isSymbolicLink() && fs.realpathSync(file) === file && stat.size === pin.bytes && sha(fs.readFileSync(file)) === pin.sha256,
      'Actual installed module drift');
  });
  const inputs = [...project,...request.installed_modules,...pinCost(requestPin),...pinCost(request.report),...pinCost(request.source)];
  const budget = candidateBudget(inputs,{reserveBytes:runtimeStat.size+outputReserve+131072});
  verifyModules();
  const report = JSON.parse(readPin(sourceRoot,request.report));
  demand(request.parent.report_sha256 === request.report.sha256 && request.parent.components === report.component_count
    && request.parent.roster_sha256 === report.complete_roster_sha256, 'Wrong complete original report');
  demand(/^components-[0-9]{3}\.jsonl\.gz$/.test(request.original_product_path), 'Only complete original component shards accepted');
  const product = report.products.find(pin=>pin.path === request.original_product_path);
  demand(product && ['bytes','sha256','uncompressed_bytes','uncompressed_sha256'].every(key=>product[key] === request.source[key]),
    'Containing shard omitted from original report');
  const decoded = readPin(sourceRoot,request.source), lines = decoded.toString('utf8').split('\n');
  demand(lines.at(-1) === '', 'Truncated original JSONL source'); lines.pop();
  const sourceRows = lines.map(line=>JSON.parse(line));
  const result = inventoryRows(sourceRows,{source:request.source,parent:request.parent,expectedIds:request.expected_ids,
    expectedRosterSha256:request.expected_roster_sha256,originalRecordBytes:lines.map(line=>Buffer.from(line+'\n'))});
  const body = Buffer.concat(result.rows.map(canonical)), encoded = gzipSync(body,{mtime:0});
  const facts = canonical({...result.facts,execution_commit:commit,executed_code:project,request:requestPin,
    input_descriptors:[request.report,request.source],runtime:{bytes:runtimeStat.size,sha256:runtimeSha},
    installed_modules:request.installed_modules, admission:budget.snapshot(), request_admission:requestBudget.snapshot()});
  demand(body.length <= 32*1024*1024 && encoded.length <= 32*1024*1024 && body.length+encoded.length+facts.length <= outputReserve,
    'Complete outputs exceed prospective reserve');
  demand(sha(fs.readFileSync(process.execPath)) === runtimeSha, 'Installed runtime drift');
  verifyModules();
  committedPreparationFiles(sourceRoot,commit,project.map(pin=>pin.path));
  const output = createNativeCandidateOutput(sourceRoot,destination);
  fs.writeFileSync(path.join(output,'inventory.jsonl.gz'),encoded,{flag:'wx'});
  fs.writeFileSync(path.join(output,'facts.json'),facts,{flag:'wx'});
  const publication = {version:1,complete:true,facts:{bytes:facts.length,sha256:sha(facts)},
    inventory:{bytes:encoded.length,sha256:sha(encoded),uncompressed_bytes:body.length,uncompressed_sha256:sha(body)}};
  fs.writeFileSync(path.join(output,'publication.json'),canonical(publication),{flag:'wx'});
  return publication;
}
if(process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const [repo,commit,requestName,requestSha,destination] = process.argv.slice(2);
  demand(repo && /^[a-f0-9]{40}$/.test(commit ?? '') && safe(requestName) && hex(requestSha),
    'Usage: additive-gap-repair.mjs REPO EXECUTION_COMMIT REQUEST_GIT_PATH REQUEST_SHA256 DESTINATION');
  const tree = execFileSync('git',['-C',repo,'ls-tree','-z',commit,'--',requestName],{encoding:'utf8'});
  const match = /^([0-9]{6}) blob ([a-f0-9]{40})\t/.exec(tree);
  demand(match && tree.endsWith(requestName+'\0'), 'Missing immutable request');
  const bytes = Number(execFileSync('git',['-C',repo,'cat-file','-s',match[2]],{encoding:'utf8'}));
  const publication = inventoryCommand({repo,commit,destination,requestPin:{commit,path:requestName,mode:match[1],blob:match[2],bytes,sha256:requestSha}});
  process.stdout.write(JSON.stringify(publication)+'\n');
}
