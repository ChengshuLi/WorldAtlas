// Availability checks before an expensive package image/build. No fetch, install,
// scientific producer, or replacement for the existing authenticated readers.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';
import {spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {loadPackageInputs, containsPackagePath} from './package-inputs.mjs';
import {currentExecutionClosure} from '../coordination/engineering/eastern-two-gap-repair-native-20261007/current-execution.mjs';

const json = file => JSON.parse(fs.readFileSync(file, 'utf8'));
const sha = raw => createHash('sha256').update(raw).digest('hex');
const gitEnv = () => ({...process.env, GIT_NO_LAZY_FETCH: '1', GIT_TERMINAL_PROMPT: '0', GIT_CONFIG_NOSYSTEM: '1', GIT_CONFIG_GLOBAL: '/dev/null'});
function command(executable, args, options = {}) {
  const child = spawnSync(executable, args, {encoding: 'utf8', timeout: 30000, maxBuffer: 16 * 1024 * 1024, ...options});
  if (child.error || child.status !== 0) throw Error(child.error?.message ?? child.stderr?.trim() ?? `${executable} exited ${child.status}`);
  return child.stdout;
}

export function inspectPackageInputs(root, definition) {
  const errors = [], materialized = [];
  const problem = (kind, file, detail) => errors.push({kind, path: file, detail});
  function ordinary(file, relative) {
    let stat;
    try { stat = fs.lstatSync(file); } catch (error) { problem('materialized-input', relative, error.code); return; }
    if (stat.isSymbolicLink()) { problem('materialized-input', relative, 'symlink'); return; }
    if (stat.isDirectory()) {
      for (const name of fs.readdirSync(file).sort()) ordinary(path.join(file, name), `${relative.replace(/\/$/, '')}/${name}`);
    } else if (stat.isFile()) materialized.push({path: relative, bytes: stat.size});
    else problem('materialized-input', relative, 'not an ordinary file/directory');
  }
  for (const input of definition.inputs) {
    const file = path.join(root, input), optional = definition.optional_inputs.includes(input);
    try {
      let parent = root;
      for (const part of input.replace(/\/$/, '').split('/').slice(0, -1)) {
        parent = path.join(parent, part);
        const stat = fs.lstatSync(parent);
        if (!stat.isDirectory() || stat.isSymbolicLink()) throw Error('nonordinary parent');
      }
      const stat = fs.lstatSync(file);
      if (stat.isSymbolicLink() || input.endsWith('/') !== stat.isDirectory()) throw Error('declared input type changed');
      ordinary(file, input.replace(/\/$/, ''));
    } catch (error) {
      if (!(optional && error.code === 'ENOENT')) problem('materialized-input', input, error.code ?? error.message);
    }
  }
  const git = args => command('git', ['-C', root, '-c', 'protocol.allow=never', ...args], {env: gitEnv()});
  let head = null, committed = [], missingObjects = [];
  try {
    head = git(['rev-parse', '--verify', 'HEAD^{commit}']).trim();
    const tree = git(['ls-tree', '-rz', '--full-tree', head]);
    committed = tree.split('\0').filter(Boolean).map(row => {
      const tab = row.indexOf('\t'), [mode, type, oid] = row.slice(0, tab).split(' ');
      return {path: row.slice(tab + 1), mode, type, oid};
    }).filter(row => containsPackagePath(definition.inputs, row.path));
    for (const input of definition.inputs) {
      if (!definition.optional_inputs.includes(input) && !committed.some(row => containsPackagePath([input], row.path)))
        problem('committed-input', input, 'absent from HEAD');
    }
    for (const row of committed) if (row.type !== 'blob' || !['100644', '100755'].includes(row.mode)) problem('committed-input', row.path, 'not an ordinary blob');
    const present = new Set(materialized.map(row => row.path));
    for (const row of committed) if (!present.has(row.path) && !definition.optional_inputs.some(input => containsPackagePath([input], row.path) && !fs.existsSync(path.join(root, input))))
      problem('materialized-input', row.path, 'Committed input not materialized as an ordinary file');
    const oids = [...new Set(committed.map(row => row.oid))];
    const raw = command('git', ['-C', root, '-c', 'protocol.allow=never', 'cat-file', '--batch-check=%(objectname) %(objecttype) %(objectsize)'], {env: gitEnv(), input: oids.join('\n') + '\n'});
    const lines = raw.trim().split('\n');
    if (lines.length !== oids.length) throw Error('Incomplete Git object inventory');
    for (let i = 0; i < oids.length; i++) {
      const [oid, type, bytes] = lines[i].split(' ');
      if (oid !== oids[i] || type !== 'blob' || !/^\d+$/.test(bytes ?? '')) missingObjects.push(oids[i]);
    }
    for (const oid of missingObjects) errors.push({kind: 'git-object', oid, paths: committed.filter(row => row.oid === oid).map(row => row.path)});
  } catch (error) { errors.push({kind: 'git-inventory', detail: error.message}); }
  return {head, committed_files: committed.length, materialized_files: materialized.length,
    materialized_bytes: materialized.reduce((n, row) => n + row.bytes, 0), missing_objects: missingObjects, errors};
}

export function inspectPackageAncestry(root, definition, requiredAncestors = []) {
  const errors = [], ancestors = [...requiredAncestors];
  // Only caller-required ancestry is checked. Historical qualified-source
  // custody does not require a full ancestor graph in an ordinary shallow CI
  // package checkout; its existing immutable reader authenticates those pins.
  for (const commit of new Set(ancestors)) {
    if (!/^[a-f0-9]{40}$/.test(commit ?? '')) { errors.push({kind: 'source-ancestry', detail: 'Invalid required ancestor'}); continue; }
    const result = spawnSync('git', ['-C', root, '-c', 'protocol.allow=never', 'merge-base', '--is-ancestor', commit, 'HEAD'], {env: gitEnv(), encoding: 'utf8', timeout: 30000});
    if (result.error || result.status !== 0) errors.push({kind: 'source-ancestry', commit, detail: result.error?.message ?? (result.status === 1 ? 'Not an ancestor of HEAD' : result.stderr.trim())});
  }
  return {required_ancestors: [...new Set(ancestors)], errors};
}

export function inspectPackageExecutionInputs(root, definition, kind = 'cloudflare') {
  if (!['static', 'hosted', 'cloudflare'].includes(kind)) throw Error('Unknown package build');
  const errors = [], contextPath = 'data/native-context-migration/manifest.json';
  let files = [];
  if (containsPackagePath(definition.inputs, contextPath)) {
    try {
      const context = json(path.join(root, contextPath));
      if (context.version === 2 && context.kind === 'retained-identity-context-continuation-v2' && context.issue === 1295) {
        files = currentExecutionClosure(root, `scripts/build-${kind}-inner.mjs`);
        for (const file of files) if (!containsPackagePath(definition.inputs, file)) errors.push({kind: 'execution-declaration', path: file, detail: 'Actual project import is not a declared package input'});
      }
    } catch (error) { errors.push({kind: 'execution-inputs', detail: error.message}); }
  }
  return {files, errors};
}

export function inspectPackageRuntime(root, {python = 'python3'} = {}) {
  const errors = [], result = {node: {version: process.version, executable: process.execPath}, python: null, npm_packages: 0, optional_npm_omissions: []};
  const attempt = (kind, run) => { try { run(); } catch (error) { errors.push({kind, detail: error.message}); } };
  attempt('node-runtime', () => {
    const pkg = json(path.join(root, 'package.json'));
    if (pkg.engines?.node !== '>=24' || Number(process.versions.node.split('.')[0]) < 24) throw Error('Package requires its declared Node >=24 runtime');
  });
  attempt('npm-lock', () => {
    const raw = fs.readFileSync(path.join(root, 'package-lock.json')), lock = JSON.parse(raw);
    const installed = json(path.join(root, 'node_modules/.package-lock.json'));
    result.package_lock_sha256 = sha(raw);
    if (lock.lockfileVersion !== installed.lockfileVersion || !lock.packages || !installed.packages) throw Error('Missing installed locked dependency inventory; use npm ci');
    for (const [name, pin] of Object.entries(lock.packages)) {
      if (!name) continue;
      // npm omits unsupported optional platform packages. Required packages never
      // become optional merely because their directory is absent.
      const actual = installed.packages[name];
      const incompatible = (list, value) => Array.isArray(list) && (list.includes('!' + value) || list.some(x => !x.startsWith('!')) && !list.includes(value));
      if (!actual && pin.optional && (incompatible(pin.os, process.platform) || incompatible(pin.cpu, process.arch) || !pin.os && !pin.cpu)) {
        result.optional_npm_omissions.push(name); continue;
      }
      if (!actual || actual.version !== pin.version || actual.integrity !== pin.integrity || actual.resolved !== pin.resolved) {
        errors.push({kind: 'npm-lock', path: name, detail: 'Installed package differs from lock'}); continue;
      }
      try {
        if (json(path.join(root, name, 'package.json')).version !== pin.version) throw Error('Installed package version differs');
        result.npm_packages++;
      } catch (error) { errors.push({kind: 'npm-package', path: name, detail: error.message}); }
    }
    for (const name of Object.keys(installed.packages)) if (!lock.packages[name]) errors.push({kind: 'npm-lock', path: name, detail: 'Unlisted installed package'});
  });
  attempt('python-runtime', () => {
    const requirements = fs.readFileSync(path.join(root, 'requirements.txt'), 'utf8');
    const modules = ['numpy', 'shapely', 'pyproj'].map(name => {
      const version = requirements.match(new RegExp(`^${name}==([^\\s#]+)$`, 'm'))?.[1];
      if (!version) throw Error(`Missing exact build requirement ${name}`);
      return {name, version};
    });
    const source = 'import importlib,json,sys\nrows=[]\nfor item in json.loads(sys.argv[1]):\n try:\n  module=importlib.import_module(item["name"]); rows.append({**item,"actual":module.__version__})\n except Exception as error: rows.append({**item,"error":str(error)})\nprint(json.dumps({"version":sys.version.split()[0],"executable":sys.executable,"imports":rows}))';
    result.python = JSON.parse(command(python, ['-c', source, JSON.stringify(modules)], {env: {...process.env, PYTHONDONTWRITEBYTECODE: '1', OPENBLAS_NUM_THREADS: '1'}}));
    for (const row of result.python.imports) if (row.error || row.actual !== row.version) errors.push({kind: 'python-import', module: row.name, expected: row.version, actual: row.actual ?? null, detail: row.error ?? 'Version differs'});
  });
  return {...result, errors};
}

export async function inspectPackageBrowser(root, mode = 'probe') {
  if (!['probe', 'required', 'off'].includes(mode)) throw Error('Browser mode must be probe, required or off');
  if (mode === 'off') return {mode, status: 'not-requested', limitation: 'No browser capability or GPU/Canvas check performed', errors: []};
  try {
    // Use the installed locked Playwright only. Never npx or download a browser.
    const module = path.join(root, 'node_modules/playwright/index.mjs');
    const source = `import {chromium} from ${JSON.stringify(pathToFileURL(module).href)};const browser=await chromium.launch({headless:true,timeout:5000});try{console.log(JSON.stringify({version:browser.version()}));}finally{await browser.close();}`;
    const observed = JSON.parse(command(process.execPath, ['--input-type=module', '-e', source], {cwd: root, timeout: 10000, maxBuffer: 64 * 1024}));
    return {mode, status: 'available', ...observed, limitation: 'Launch capability only; actual GPU/Canvas assertions remain separate', errors: []};
  } catch (error) {
    const detail = error.message.slice(0, 1600);
    return {mode, status: 'unavailable', detail, errors: mode === 'required' ? [{kind: 'browser-capability', detail}] : []};
  }
}

export async function preflightPackageBuild({root = process.cwd(), kind = 'cloudflare', browser = 'probe', python = 'python3', requiredAncestors = []} = {}) {
  const started = performance.now();
  root = fs.realpathSync(root);
  const definition = loadPackageInputs(root);
  const inputs = inspectPackageInputs(root, definition), ancestry = inspectPackageAncestry(root, definition, requiredAncestors);
  const execution = inspectPackageExecutionInputs(root, definition, kind);
  const runtime = inspectPackageRuntime(root, {python}), browserCapability = await inspectPackageBrowser(root, browser);
  const errors = [...inputs.errors, ...ancestry.errors, ...execution.errors, ...runtime.errors, ...browserCapability.errors];
  return {version: 1, kind: 'package-build-preflight', passed: errors.length === 0, input_definition_sha256: sha(fs.readFileSync(path.join(root, '.github/package-inputs.json'))),
    inputs, ancestry, execution, runtime, browser: browserCapability, errors, elapsed_seconds: (performance.now() - started) / 1000,
    limitation: 'Availability and runtime preflight only. Existing authenticated package/selected readers and applicable hosted tests remain authoritative; no scientific producer, fetch or installation invoked.'};
}

export function requirePackagePreflight(report) {
  if (!report.passed) throw Error(`Package preflight failed before image creation:\n${report.errors.map(error => JSON.stringify(error)).join('\n')}`);
  return report;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const options = {}, args = process.argv.slice(2);
  for (let i = 0; i < args.length; i += 2) {
    const key = args[i]?.replace(/^--/, ''), value = args[i + 1];
    if (!['root', 'kind', 'browser', 'python', 'out', 'ancestor'].includes(key) || !value) throw Error('Use --root DIR --kind static|hosted|cloudflare --browser probe|required|off --python EXE --ancestor COMMIT --out NEW_FILE');
    if (key === 'ancestor') (options.requiredAncestors ??= []).push(value); else if (Object.hasOwn(options, key)) throw Error('Duplicate option'); else options[key] = value;
  }
  if (options.out) {
    try { fs.lstatSync(options.out); throw Error('Preflight output already exists'); } catch (error) { if (error.code !== 'ENOENT') throw error; }
    for (let parent = path.dirname(path.resolve(options.out)); parent !== path.dirname(parent); parent = path.dirname(parent)) {
      const stat = fs.lstatSync(parent); if (!stat.isDirectory() || stat.isSymbolicLink()) throw Error('Preflight output has nonordinary parent');
    }
  }
  const report = await preflightPackageBuild(options);
  const raw = JSON.stringify(report, null, 2) + '\n';
  if (options.out) fs.writeFileSync(options.out, raw, {flag: 'wx'});
  console.log(raw); if (!report.passed) process.exitCode = 1;
}
