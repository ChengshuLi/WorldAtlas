import fs from 'node:fs/promises';
import fsSync, {constants} from 'node:fs';
import path from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';
import {spawn, spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {loadPackageInputs, validatePackageInputs, containsPackagePath} from './package-inputs.mjs';
import {issueCurrentExecution,requireCurrentExecution,currentExecutionClosure} from '../coordination/engineering/eastern-two-gap-repair-native-20261007/current-execution.mjs';

// One explicit startup policy for package production and selected consumers.
// Site hooks, user/PYTHONPATH imports and ambient bytecode cannot run before
// the package's declared Python source and installed runtime have been admitted.
const helper=fileURLToPath(new URL('./package-python-runtime.py',import.meta.url));
export function packagePythonArgs(args){
  if(!Array.isArray(args)||!args.length||args.some(value=>typeof value!=='string'))throw Error('Explicit Python package arguments required');
  if(args[0]==='-c'){
    if(args.length<2)throw Error('Explicit Python source required');
    return ['-I','-S','-B',helper,'--run-code',...args.slice(1)];
  }
  if(args[0].startsWith('-'))throw Error('Package Python execution requires an explicit source script or -c');
  return ['-I','-S','-B',helper,'--run-script',...args];
}
export function packagePythonProbeArgs(rows){
  return ['-I','-S','-B',helper,'--probe-imports',JSON.stringify(rows)];
}

// Only this current execution wrapper controls the full build child's Python
// startup. Immutable critical callers retain their certified source bytes.
export function createPackagePythonExecution(stage,{python,sourceHelper,env=process.env}={}) {
  if(!path.isAbsolute(python??'')||/[\r\n]/.test(process.execPath)||/\s/.test(process.execPath))throw Error('Exact executable paths required for current Python launcher');
  const base=fsSync.realpathSync(stage),helperPath=path.join(base,'scripts/package-python-runtime.py');
  const identities=new Map(),identity=file=>{const resolved=fsSync.realpathSync(file),stat=fsSync.statSync(resolved);return {resolved,...Object.fromEntries(['dev','ino','size','mode','mtimeMs','ctimeMs'].map(key=>[key,stat[key]]))};};
  const pin=file=>{
    const actual=fsSync.realpathSync(file),stat=fsSync.statSync(actual);
    if(!stat.isFile())throw Error('Ordinary current execution tool required');
    const hash=createHash('sha256'),buffer=Buffer.alloc(1048576),fd=fsSync.openSync(actual,'r');let bytes=0,held;
    try{for(;;){const n=fsSync.readSync(fd,buffer,0,buffer.length,null);if(!n)break;bytes+=n;hash.update(buffer.subarray(0,n));}held=fsSync.fstatSync(fd);}finally{fsSync.closeSync(fd);}
    const after=fsSync.statSync(actual),fields=['dev','ino','size','mode','mtimeMs','ctimeMs'];
    if(bytes!==stat.size||fsSync.realpathSync(file)!==actual||fields.some(key=>stat[key]!==held[key]||stat[key]!==after[key]))throw Error('Current execution tool changed while reading');
    if(!identities.has(file))identities.set(file,{resolved:actual,...Object.fromEntries(fields.map(key=>[key,stat[key]]))});
    return {path:file,resolved:actual,mode:stat.mode&0o777,bytes,sha256:hash.digest('hex')};
  };
  if(fsSync.realpathSync(helperPath)!==helperPath)throw Error('Declared Python helper must be ordinary');
  const interpreter=pin(python),helperPin=pin(helperPath),node=pin(process.execPath);
  if(sourceHelper?.path!=='scripts/package-python-runtime.py'||sourceHelper.bytes!==helperPin.bytes||sourceHelper.sha256!==helperPin.sha256||sourceHelper.mode!==(helperPin.mode&0o111?'100755':'100644'))throw Error('Staged Python helper differs from independently authenticated source');
  const cache=path.join(base,'.cache');fsSync.mkdirSync(cache,{recursive:true});
  if(fsSync.realpathSync(cache)!==cache||!fsSync.lstatSync(cache).isDirectory())throw Error('Ordinary package cache required');
  const directory=fsSync.mkdtempSync(path.join(cache,'python-execution-')),launcher=path.join(directory,'python3');
  const raw=`#!${process.execPath}\nimport {spawnSync} from 'node:child_process';\nconst child=spawnSync(${JSON.stringify(python)},${JSON.stringify(['-I','-S','-B',helperPath,'--run-cli'])}.concat(process.argv.slice(2)),{stdio:'inherit'});\nif(child.error){process.stderr.write(String(child.error.message)+'\\n');process.exit(1);}\nif(child.signal){process.kill(process.pid,child.signal);}else process.exit(child.status??1);\n`;
  fsSync.writeFileSync(launcher,raw,{flag:'wx',mode:0o700});
  const launcherPin=pin(launcher);
  const record={kind:'current-package-isolated-python-execution-v1',source_role:'scripts/package-build.mjs',
    attribution:'Current application execution policy; not a historical scientific invocation',
    interpreter,helper:{...helperPin,source:sourceHelper},node,launcher:launcherPin,startup:['-I','-S','-B'],argv_mode:'--run-cli'};
  // Only four private same-process change detectors. Stat equality does not
  // establish content identity; creation and final verify still hash every tool.
  const check=()=>{for(const [file,expected]of identities)if(JSON.stringify(identity(file))!==JSON.stringify(expected))throw Error('Current Python execution tool changed');};
  const verify=()=>{
    check();
    for(const expected of [interpreter,helperPin,node,launcherPin])if(JSON.stringify(pin(expected.path))!==JSON.stringify(expected))throw Error('Current Python execution tool changed');
    if(fsSync.realpathSync(launcher)!==launcher||!fsSync.lstatSync(launcher).isFile())throw Error('Current Python launcher replaced');
  };
  check();
  return {env:{...env,PATH:directory+path.delimiter+(env.PATH??'')},record,check,verify};
}

export function packagePythonSourceDescriptor(root,head) {
  const name='scripts/package-python-runtime.py';
  if(!/^[a-f0-9]{40}$/.test(head??''))throw Error('Exact package source head required for Python helper');
  const file=path.join(fsSync.realpathSync(root),name),stat=fsSync.lstatSync(file);
  if(!stat.isFile()||fsSync.realpathSync(file)!==file)throw Error('Ordinary declared Python source required');
  const raw=fsSync.readFileSync(file),row=command('git',['--no-replace-objects','-C',root,'ls-tree','-z',head,'--',name],{env:gitEnv()});
  const oid=createHash('sha1').update(`blob ${raw.length}\0`).update(raw).digest('hex'),mode=stat.mode&0o111?'100755':'100644';
  if(row!==`${mode} blob ${oid}\t${name}\0`)throw Error('Declared Python helper differs from immutable source tree');
  return {path:name,source_head:head,git_blob_oid:oid,mode,bytes:raw.length,sha256:sha(raw)};
}

// Keep preparation in this already-admitted wrapper role. A new imported
// wrapper module would alter the immutable application-consumer role roster.
// The standalone preflight CLI below re-exports these same implementations.
const json = file => JSON.parse(fsSync.readFileSync(file, 'utf8'));
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
    try { stat = fsSync.lstatSync(file); } catch (error) { problem('materialized-input', relative, error.code); return; }
    if (stat.isSymbolicLink()) { problem('materialized-input', relative, 'symlink'); return; }
    if (stat.isDirectory()) {
      for (const name of fsSync.readdirSync(file).sort()) ordinary(path.join(file, name), `${relative.replace(/\/$/, '')}/${name}`);
    } else if (stat.isFile()) materialized.push({path: relative, bytes: stat.size});
    else problem('materialized-input', relative, 'not an ordinary file/directory');
  }
  for (const input of definition.inputs) {
    const file = path.join(root, input), optional = definition.optional_inputs.includes(input);
    try {
      let parent = root;
      for (const part of input.replace(/\/$/, '').split('/').slice(0, -1)) {
        parent = path.join(parent, part);
        const stat = fsSync.lstatSync(parent);
        if (!stat.isDirectory() || stat.isSymbolicLink()) throw Error('nonordinary parent');
      }
      const stat = fsSync.lstatSync(file);
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
    for (const row of committed) if (!present.has(row.path) && !definition.optional_inputs.some(input => containsPackagePath([input], row.path) && !fsSync.existsSync(path.join(root, input))))
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
  const errors = [];let files = [];
  try {
    files=currentExecutionClosure(root,`scripts/build-${kind}-inner.mjs`);
    for(const file of files)if(!containsPackagePath(definition.inputs,file))errors.push({kind:'execution-declaration',path:file,detail:'Actual project import is not a declared package input'});
  } catch(error){errors.push({kind:'execution-inputs',detail:error.message});}
  return {files,errors};
}

export function inspectPackageNodeRuntime(root) {
  const errors = [], result = {node: {version: process.version, executable: process.execPath}, python: null, npm_packages: 0, optional_npm_omissions: []};
  if(process.env.NODE_OPTIONS?.trim()||process.env.NODE_PATH?.trim())errors.push({kind:'node-execution',detail:'Actual package issuer requires NODE_OPTIONS and NODE_PATH unset'});
  const attempt = (kind, run) => { try { run(); } catch (error) { errors.push({kind, detail: error.message}); } };
  attempt('node-runtime', () => {
    const pkg = json(path.join(root, 'package.json'));
    if (pkg.engines?.node !== '>=24' || Number(process.versions.node.split('.')[0]) < 24) throw Error('Package requires its declared Node >=24 runtime');
  });
  attempt('npm-lock', () => {
    const raw = fsSync.readFileSync(path.join(root, 'package-lock.json')), lock = JSON.parse(raw);
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
  return {...result, errors};
}

export function inspectPackageRuntime(root, {python = 'python3'} = {}) {
  const {errors,...result}=inspectPackageNodeRuntime(root);
  const attempt = (kind, run) => { try { run(); } catch (error) { errors.push({kind, detail: error.message}); } };
  attempt('python-runtime', () => {
    const requirements = fsSync.readFileSync(path.join(root, 'requirements.txt'), 'utf8');
    const modules = ['numpy', 'shapely', 'pyproj'].map(name => {
      const version = requirements.match(new RegExp(`^${name}==([^\\s#]+)$`, 'm'))?.[1];
      if (!version) throw Error(`Missing exact build requirement ${name}`);
      return {name, version};
    });
    const args=packagePythonProbeArgs(modules);
    result.python = JSON.parse(command(python, args, {env: {...process.env, PYTHONDONTWRITEBYTECODE: '1', OPENBLAS_NUM_THREADS: '1'}}));
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
  root = fsSync.realpathSync(root);
  const definition = loadPackageInputs(root);
  const inputs = inspectPackageInputs(root, definition), ancestry = inspectPackageAncestry(root, definition, requiredAncestors);
  const execution = inspectPackageExecutionInputs(root, definition, kind);
  const runtime = inspectPackageRuntime(root, {python}), browserCapability = await inspectPackageBrowser(root, browser);
  const errors = [...inputs.errors, ...ancestry.errors, ...execution.errors, ...runtime.errors, ...browserCapability.errors];
  return {version: 1, kind: 'package-build-preflight', passed: errors.length === 0, input_definition_sha256: sha(fsSync.readFileSync(path.join(root, '.github/package-inputs.json'))),
    inputs, ancestry, execution, runtime, browser: browserCapability, errors, elapsed_seconds: (performance.now() - started) / 1000,
    limitation: 'Availability and runtime preflight only. Existing authenticated package/selected readers and applicable hosted tests remain authoritative; no scientific producer, fetch or installation invoked.'};
}

export function requirePackagePreflight(report) {
  if (!report.passed) throw Error(`Package preflight failed before image creation:\n${report.errors.map(error => JSON.stringify(error)).join('\n')}`);
  return report;
}


const entries = {static: 'scripts/build-static-inner.mjs', hosted: 'scripts/build-hosted-inner.mjs', cloudflare: 'scripts/build-cloudflare-inner.mjs'};
const repository = path.dirname(path.dirname(fileURLToPath(import.meta.url)));

async function copyOrdinary(source, destination, inventory, relative) {
  const stat = await fs.lstat(source);
  if (stat.isSymbolicLink()) throw Error(`Package source cannot be a symlink: ${relative}`);
  if (stat.isDirectory()) {
    await fs.mkdir(destination, {recursive: true});
    for (const name of (await fs.readdir(source)).sort()) {
      await copyOrdinary(path.join(source, name), path.join(destination, name), inventory, `${relative.replace(/\/$/, '')}/${name}`);
    }
  } else if (stat.isFile()) {
    await fs.mkdir(path.dirname(destination), {recursive: true});
    // APFS uses copy-on-write where available; other filesystems safely copy.
    await fs.copyFile(source, destination, constants.COPYFILE_FICLONE);
    inventory.push({path: relative, bytes: stat.size});
  } else throw Error(`Nonordinary package source: ${relative}`);
}

async function ordinaryParents(root, relative) {
  const parts = relative.replace(/\/$/, '').split('/');
  let current = root;
  for (const part of parts.slice(0, -1)) {
    current = path.join(current, part);
    const stat = await fs.lstat(current).catch(error => { if (error.code === 'ENOENT') return null; throw error; });
    if (!stat) break;
    if (!stat.isDirectory() || stat.isSymbolicLink()) throw Error(`Package path has nonordinary parent: ${relative}`);
  }
}

export async function materializePackageInputs({source, destination, definition = loadPackageInputs(source)}) {
  validatePackageInputs(definition);
  const inventory = [];
  for (const input of definition.inputs) {
    await ordinaryParents(source, input);
    const file = path.join(source, input), target = path.join(destination, input);
    const stat = await fs.lstat(file).catch(error => { if (error.code === 'ENOENT') return null; throw error; });
    if (!stat) {
      if (definition.optional_inputs.includes(input)) continue;
      throw Error(`Declared package input missing: ${input}`);
    }
    if (input.endsWith('/') !== stat.isDirectory()) throw Error(`Package input type changed: ${input}`);
    await copyOrdinary(file, target, inventory, input.replace(/\/$/, ''));
  }
  return inventory;
}

// Dependencies are installed by the caller/CI. Local package links must not expose
// undeclared repository inputs through a workspace/file dependency.
export async function verifyPackageDependencies(directory) {
  const root = await fs.realpath(directory);
  const visit = async current => {
    for (const row of await fs.readdir(current, {withFileTypes: true})) {
      const file = path.join(current, row.name);
      if (row.isSymbolicLink()) {
        const target = await fs.realpath(file);
        if (target !== root && !target.startsWith(root + path.sep)) throw Error(`Package dependency escapes its installation: ${file}`);
      } else if (row.isDirectory()) await visit(file);
    }
  };
  await visit(root);
  return root;
}

export function assertPackageStage(directory = repository) {
  const expected = process.env.WORLDATLAS_PACKAGE_STAGE;
  if (!expected || path.resolve(expected) !== path.resolve(directory)) throw Error('Private builder requires a declared input image; use build:static, build:hosted or build:cloudflare');
}

// The programmatic injection is for synthetic boundary tests only. Ordinary
// build entry points supply no override, and no environment flag disables it.
export async function runPackageBuild(kind, {root = repository, execute, preflight = preflightPackageBuild} = {}) {
  if (!Object.hasOwn(entries, kind)) throw Error('Unknown package build');
  root = await fs.realpath(root);
  const definition = loadPackageInputs(root);
  // Report all setup failures before copying the multi-gigabyte input image.
  const readiness = requirePackagePreflight(await preflight({root, kind}));
  const dependencies = await verifyPackageDependencies(path.join(root, 'node_modules'));
  const cache = path.join(root, '.cache');
  const cacheStat = await fs.lstat(cache).catch(error => { if (error.code === 'ENOENT') return null; throw error; });
  if (cacheStat && (!cacheStat.isDirectory() || cacheStat.isSymbolicLink())) throw Error('Package cache must be an ordinary directory');
  await fs.mkdir(cache, {recursive: true});
  await fs.rm(path.join(cache, 'package-input-build.json'), {force: true});
  const stage = await fs.mkdtemp(path.join(cache, 'package-input-image-'));
  const exports = [];
  try {
    const pythonSource=containsPackagePath(definition.inputs,'scripts/package-python-runtime.py')?packagePythonSourceDescriptor(root,readiness.inputs?.head):null;
    const inventory = await materializePackageInputs({source: root, destination: stage, definition});
    await fs.symlink(dependencies, path.join(stage, 'node_modules'), 'dir');
    let env = {...process.env, WORLDATLAS_PACKAGE_STAGE: stage};
    const pythonExecution=containsPackagePath(definition.inputs,'scripts/package-python-runtime.py')?createPackagePythonExecution(stage,{python:readiness.runtime?.python?.executable,sourceHelper:pythonSource,env}):null;
    if(pythonExecution)env=pythonExecution.env;
    delete env.WORLDATLAS_CURRENT_EXECUTION_PATH;
    delete env.WORLDATLAS_CURRENT_EXECUTION_SHA256;
    delete env.WORLDATLAS_PACKAGE_SOURCE_ROOT;
    // Current execution is independent of the historical producer/continuation.
    let currentExecution;
    if(containsPackagePath(definition.inputs,'data/ownership-selection.json')||containsPackagePath(definition.inputs,'data/native-context-migration/manifest.json')){
      currentExecution=issueCurrentExecution({source:root,stage,entry:entries[kind]});
      const raw=Buffer.from(JSON.stringify(currentExecution)+'\n');
      await fs.mkdir(path.join(stage,'.cache'),{recursive:true});
      await fs.writeFile(path.join(stage,'.cache/current-context-execution.json'),raw,{flag:'wx'});
      env.WORLDATLAS_PACKAGE_SOURCE_ROOT=root;
      env.WORLDATLAS_CURRENT_EXECUTION_PATH='.cache/current-context-execution.json';
      env.WORLDATLAS_CURRENT_EXECUTION_SHA256=createHash('sha256').update(raw).digest('hex');
    }
    const run = execute ?? ((entry, options) => new Promise((resolve, reject) => {
      const child = spawn(process.execPath, [entry], {...options, stdio: 'inherit'});
      child.on('error', reject);
      child.on('exit', (code, signal) => code === 0 ? resolve() : reject(Error(`Package ${kind} build failed (${signal ?? code}); prior outputs retained`)));
    }));
    pythonExecution?.check();
    try{await run(path.join(stage, entries[kind]), {cwd: stage, env});}
    catch(error){
      try{pythonExecution?.verify();}catch(changed){throw new AggregateError([error,changed],'Build failed and current Python execution changed');}
      throw error;
    }
    pythonExecution?.verify();
    if(currentExecution)requireCurrentExecution(currentExecution);
    // Only explicit generated outputs return to the caller. Source archives and
    // unpublished research never get copied back or altered by this wrapper.
    for (const output of definition.generated_outputs) {
      await ordinaryParents(stage, output);
      await ordinaryParents(root, output);
      const source = path.join(stage, output), target = path.join(root, output);
      const exists = await fs.lstat(source).catch(error => { if (error.code === 'ENOENT') return null; throw error; });
      if (!exists) continue;
      const temporary = target.replace(/\/$/, '') + `.package-output-${path.basename(stage)}`;
      exports.push({temporary, target});
      await copyOrdinary(source, temporary, [], output.replace(/\/$/, ''));
    }
    // Validate and prepare every output before replacing any caller output.
    for (const {temporary, target} of exports) {
      await fs.rm(target, {recursive: true, force: true});
      await fs.rename(temporary, target);
    }
    const receipt = {version: 1, kind, input_definition_sha256: createHash('sha256').update(await fs.readFile(path.join(stage, '.github/package-inputs.json'))).digest('hex'), source_files: inventory.length,
      source_bytes: inventory.reduce((sum, row) => sum + row.bytes, 0), input_paths: definition.inputs,
      boundary: 'Build source contains only declared inputs and the installed dependencies; unpublished inputs are absent. This is not an OS security sandbox.'};
    if(currentExecution)receipt.current_context_execution=currentExecution;
    if(pythonExecution)receipt.current_python_execution=pythonExecution.record;
    receipt.preflight = readiness;
    await fs.writeFile(path.join(cache, 'package-input-build.json'), JSON.stringify(receipt, null, 2) + '\n');
    return receipt;
  } finally {
    for (const {temporary} of exports) await fs.rm(temporary, {recursive: true, force: true});
    await fs.rm(stage, {recursive: true, force: true});
  }
}
