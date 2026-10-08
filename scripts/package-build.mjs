import fs from 'node:fs/promises';
import {constants} from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawn} from 'node:child_process';
import {createHash} from 'node:crypto';
import {loadPackageInputs, validatePackageInputs} from './package-inputs.mjs';
import {issueCurrentExecution,authenticateCurrentExecution,requireCurrentExecution} from '../coordination/engineering/eastern-two-gap-repair-native-20261007/current-execution.mjs';

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

export async function runPackageBuild(kind, {root = repository, execute} = {}) {
  if (!Object.hasOwn(entries, kind)) throw Error('Unknown package build');
  root = await fs.realpath(root);
  const definition = loadPackageInputs(root);
  const dependencies = await verifyPackageDependencies(path.join(root, 'node_modules'));
  const cache = path.join(root, '.cache');
  const cacheStat = await fs.lstat(cache).catch(error => { if (error.code === 'ENOENT') return null; throw error; });
  if (cacheStat && (!cacheStat.isDirectory() || cacheStat.isSymbolicLink())) throw Error('Package cache must be an ordinary directory');
  await fs.mkdir(cache, {recursive: true});
  await fs.rm(path.join(cache, 'package-input-build.json'), {force: true});
  const stage = await fs.mkdtemp(path.join(cache, 'package-input-image-'));
  const exports = [];
  try {
    const inventory = await materializePackageInputs({source: root, destination: stage, definition});
    await fs.symlink(dependencies, path.join(stage, 'node_modules'), 'dir');
    const env = {...process.env, WORLDATLAS_PACKAGE_STAGE: stage};
    delete env.WORLDATLAS_CURRENT_EXECUTION_PATH;
    delete env.WORLDATLAS_CURRENT_EXECUTION_SHA256;
    delete env.WORLDATLAS_PACKAGE_SOURCE_ROOT;
    // Bind current checkout execution separately from immutable authored lineage.
    const contextPath=path.join(stage,'data/native-context-migration/manifest.json');
    const context=await fs.readFile(contextPath,'utf8').then(JSON.parse,error=>{if(error.code==='ENOENT')return null;throw error;});
    let currentExecution;
    if(context?.version===2&&context.kind==='retained-identity-context-continuation-v2'&&context.issue===1295){
      currentExecution=issueCurrentExecution({source:root,stage,entry:entries[kind]});
      authenticateCurrentExecution(currentExecution,{root:stage,executingRoot:root,sourceRoot:root});
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
    await run(path.join(stage, entries[kind]), {cwd: stage, env});
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
    await fs.writeFile(path.join(cache, 'package-input-build.json'), JSON.stringify(receipt, null, 2) + '\n');
    return receipt;
  } finally {
    for (const {temporary} of exports) await fs.rm(temporary, {recursive: true, force: true});
    await fs.rm(stage, {recursive: true, force: true});
  }
}
