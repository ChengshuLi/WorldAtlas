// Explicit, fully enumerated overlay of our preserved package source image.
// This calls the unchanged materializer once, then the unchanged hosted builder.
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {execFileSync, spawn} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {materializePackageInputs, verifyPackageDependencies} from '../../../scripts/package-build.mjs';
import {validatePackageInputs, containsPackagePath} from '../../../scripts/package-inputs.mjs';

const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..');
const ownedExternalImages = '/Users/chengshuli/world-atlas-workspace/.cache/1295-normal-consumer-materialization-20261008';
const git = (...args) => execFileSync('git', ['-C', repo, ...args], {maxBuffer: 34 * 1024 * 1024});
const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const blob = bytes => createHash('sha1').update(`blob ${bytes.length}\0`).update(bytes).digest('hex');
function ordinary(file, directory = false) {
  for (let p = file; p !== path.dirname(p); p = path.dirname(p)) {
    const s = fs.lstatSync(p);
    if (s.isSymbolicLink() || (p !== file && !s.isDirectory())) throw Error('Nonordinary package path');
  }
  const s = fs.lstatSync(file);
  if (directory ? !s.isDirectory() : !s.isFile()) throw Error('Package path type changed');
  return s;
}
function fingerprint(file) {
  const s = ordinary(file), h = createHash('sha256'), o = createHash('sha1').update(`blob ${s.size}\0`);
  const fd = fs.openSync(file, 'r'), buffer = Buffer.alloc(1024 * 1024); let length = 0;
  try { for (;;) { const n = fs.readSync(fd, buffer, 0, buffer.length, null); if (!n) break; length += n; h.update(buffer.subarray(0, n)); o.update(buffer.subarray(0, n)); } }
  finally { fs.closeSync(fd); }
  if (length !== s.size) throw Error('Package body changed during read');
  return {bytes: length, sha256: h.digest('hex'), git_blob: o.digest('hex'), mode: s.mode & 0o111 ? '100755' : '100644'};
}
function files(root, relative = '') {
  ordinary(path.join(root, relative), true); const result = [];
  for (const name of fs.readdirSync(path.join(root, relative)).sort()) {
    const rel = path.posix.join(relative, name), p = path.join(root, rel), s = fs.lstatSync(p);
    if (s.isSymbolicLink()) throw Error('Unlisted source link');
    if (s.isDirectory()) result.push(...files(root, rel));
    else if (s.isFile()) result.push(rel); else throw Error('Unlisted nonordinary source');
  }
  return result;
}
export function plan(commit) {
  if (!/^[a-f0-9]{40}$/.test(commit)) throw Error('Immutable commit required before Git');
  const definitionRaw = git('show', `${commit}:.github/package-inputs.json`);
  const definition = validatePackageInputs(JSON.parse(definitionRaw));
  const rows = git('ls-tree', '-r', '-l', '-z', commit).toString().split('\0').filter(Boolean).map(line => {
    const [meta, file] = line.split('\t'), [mode, type, oid, bytes] = meta.trim().split(/\s+/);
    return {path: file, mode, type, git_blob: oid, bytes: Number(bytes)};
  }).filter(row => containsPackagePath(definition.inputs, row.path));
  if (rows.some(row => row.type !== 'blob' || !['100644', '100755'].includes(row.mode) || !Number.isSafeInteger(row.bytes) || row.bytes > 32 * 1024 * 1024)) throw Error('Package source body bounds/type');
  for (const input of definition.inputs) if (!definition.optional_inputs.includes(input) && !rows.some(row => input.endsWith('/') ? row.path.startsWith(input) : row.path === input)) throw Error('Required frozen package input absent');
  return {commit, definition, definition_sha256: sha(definitionRaw), source_files: rows, source_bytes: rows.reduce((n, row) => n + row.bytes, 0)};
}
export function originalMaterializationView(original, source, candidate) {
  validatePackageInputs(original);
  const missing = original.inputs.filter(input => !fs.existsSync(path.join(source, input)));
  const required = missing.filter(input => !original.optional_inputs.includes(input));
  const allowed = 'coordination/engineering/eastern-two-gap-repair-native-20261007/native-proposal.json';
  for (const input of required) {
    if (input !== allowed || !candidate.source_files.some(row => row.path === input && row.type === 'blob' && ['100644', '100755'].includes(row.mode) && row.bytes > 0 && row.bytes <= 32 * 1024 * 1024 && /^[a-f0-9]{40}$/.test(row.git_blob))) throw Error('Unbound missing original package input');
  }
  const definition = validatePackageInputs({...original, inputs: original.inputs.filter(input => !required.includes(input))});
  return {definition, original_inputs_missing: missing, required_candidate_restorations: required};
}
export async function run({commit, source, destination, receipt, execute = true}) {
  const started = new Date().toISOString(), p = plan(commit);
  if (process.env.WORLDATLAS_PACKAGE_STAGE) throw Error('Caller cannot spoof package stage');
  if (git('rev-parse', 'HEAD').toString().trim() !== commit) throw Error('Author execution commit changed');
  for (const file of ['scripts/package-build.mjs', 'scripts/package-inputs.mjs', path.relative(repo, fileURLToPath(import.meta.url))]) {
    const actual = fingerprint(path.join(repo, file)); if (actual.git_blob !== blob(git('show', `${commit}:${file}`))) throw Error('Executed materializer/code differs from freeze');
  }
  source = path.resolve(source); destination = path.resolve(destination); ordinary(source, true);
  if ((!destination.startsWith(path.join(repo, '.cache') + path.sep) && path.dirname(destination) !== ownedExternalImages) || fs.existsSync(destination)) throw Error('Exclusive owned destination required');
  ordinary(path.dirname(destination), true);
  const oldDefinitionRaw = fs.readFileSync(path.join(source, '.github/package-inputs.json'));
  const oldDefinition = JSON.parse(oldDefinitionRaw);
  const originalView = originalMaterializationView(oldDefinition, source, p);
  const preservationFile = `${source}-whole-preservation.json`;
  const preservationStat = ordinary(preservationFile);
  if (preservationStat.size > 4 * 1024 * 1024) throw Error('Original package preservation metadata bound');
  const preservationRaw = fs.readFileSync(preservationFile);
  if (preservationRaw.length !== preservationStat.size || sha(preservationRaw) !== '33144c8f62aaf92085a599cf1912d064beb8cb47a5fd5b1df80e6cfc21223ff1') throw Error('Original package preservation authority changed');
  const preservation = JSON.parse(preservationRaw);
  if (preservation.status !== 'PASS' || preservation.preserved_absolute_path !== source) throw Error('Wrong preserved original source');
  const expected = new Map(preservation.whole_entry_inventory.map(row => [row.path, row]));
  const seen = new Set();
  function authenticateOld(relative = '') {
    for (const name of fs.readdirSync(path.join(source, relative)).sort()) {
      const rel = path.posix.join(relative, name), file = path.join(source, rel), s = fs.lstatSync(file), row = expected.get(rel);
      if (!row || (s.mode & 0o777) !== row.mode) throw Error('Foreign/changed original package member');
      seen.add(rel);
      if (s.isSymbolicLink()) { if (row.kind !== 'symlink' || fs.readlinkSync(file) !== row.target) throw Error('Original package dependency link changed'); }
      else if (s.isDirectory()) { if (row.kind !== 'directory') throw Error('Original source directory changed'); authenticateOld(rel); }
      else if (s.isFile()) { const f = fingerprint(file); if (row.kind !== 'file' || f.bytes !== row.bytes || f.sha256 !== row.sha256) throw Error('Original source whole body changed'); }
      else throw Error('Original source contains nonordinary member');
    }
  }
  authenticateOld();
  if (seen.size !== expected.size) throw Error('Original package source member omitted');
  const dependencies = await verifyPackageDependencies(path.join(source, 'node_modules'));
  const missingRestorationPins = originalView.required_candidate_restorations.map(input => {
    const row = p.source_files.find(row => row.path === input), raw = git('cat-file', 'blob', row.git_blob);
    if (raw.length !== row.bytes || blob(raw) !== row.git_blob) throw Error('Missing original input candidate body differs');
    return {...row, sha256: sha(raw), origin: 'explicit current immutable candidate; absent in original preserved source'};
  });
  fs.mkdirSync(destination);
  const materialized = await materializePackageInputs({source, destination, definition: originalView.definition});
  const required = new Set(p.source_files.map(row => row.path));
  const removed = [];
  for (const file of files(destination)) if (!required.has(file)) { fs.unlinkSync(path.join(destination, file)); removed.push(file); }
  const actual = [];
  for (const row of p.source_files) {
    const target = path.join(destination, row.path); let before = null;
    if (fs.existsSync(target)) before = fingerprint(target);
    const reused = before?.git_blob === row.git_blob && before.mode === row.mode && before.bytes === row.bytes;
    if (!reused) {
      const raw = git('cat-file', 'blob', row.git_blob);
      if (raw.length !== row.bytes || blob(raw) !== row.git_blob) throw Error('Immutable overlay body changed');
      fs.mkdirSync(path.dirname(target), {recursive: true});
      // Remove the cloned leaf before writing, preserving the old image even if
      // a filesystem implements the materializer with a shared copy mechanism.
      if (fs.existsSync(target)) fs.unlinkSync(target);
      fs.writeFileSync(target, raw, {flag: 'wx', mode: row.mode === '100755' ? 0o755 : 0o644});
    }
    const after = fingerprint(target);
    if (after.git_blob !== row.git_blob || after.mode !== row.mode || after.bytes !== row.bytes) throw Error('Candidate source image changed');
    actual.push({...row, ...after, reused_preserved_source: reused});
  }
  if (files(destination).length !== required.size) throw Error('Foreign/omitted candidate source file');
  const inputProof = {status: 'PASS', started_at: started, materialization_finished_at: new Date().toISOString(), commit,
    method: 'unchanged FICLONE materializer once, explicit complete immutable candidate overlay, unchanged hosted inner builder',
    definition_sha256: p.definition_sha256, source, destination, original_materialized_count: materialized.length, removed,
    original_source_preservation_sha256: sha(preservationRaw), original_source_members_checked: seen.size,
    original_definition_sha256: sha(oldDefinitionRaw), missing_original_input_whole_candidate_pins: missingRestorationPins,
    original_materialization_definition_sha256: sha(Buffer.from(JSON.stringify(originalView.definition))),
    original_inputs_missing: originalView.original_inputs_missing, required_candidate_restorations: originalView.required_candidate_restorations,
    source_files: actual, source_bytes: p.source_bytes, node: {version: process.version, executable: process.execPath, ...fingerprint(process.execPath)}, executed: false};
  fs.writeFileSync(receipt, JSON.stringify(inputProof, null, 2) + '\n', {flag: 'wx'});
  fs.symlinkSync(dependencies, path.join(destination, 'node_modules'), 'dir');
  if (!execute) return inputProof;
  const code = await new Promise((resolve, reject) => {
    const child = spawn(process.execPath, [path.join(destination, 'scripts/build-hosted-inner.mjs')], {cwd: destination, env: {...process.env, WORLDATLAS_PACKAGE_STAGE: destination}, stdio: 'inherit'});
    child.on('error', reject); child.on('exit', (code, signal) => resolve({code, signal}));
  });
  const result = {...inputProof, executed: true, finished_at: new Date().toISOString(), exit: code, status: code.code === 0 && !code.signal ? 'PASS' : 'FAILED_NORMAL_CONSUMER'};
  fs.writeFileSync(receipt, JSON.stringify(result, null, 2) + '\n');
  if (result.status !== 'PASS') throw Error(`Normal consumer failed: ${JSON.stringify(code)}`);
  return result;
}
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const [commit, source, destination, receipt, option] = process.argv.slice(2);
  if (option === '--plan') console.log(JSON.stringify(plan(commit), null, 2));
  else await run({commit, source, destination, receipt, execute: option !== '--prepare-only'});
}
