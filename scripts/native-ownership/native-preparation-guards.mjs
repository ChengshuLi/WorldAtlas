import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';

const digest = raw => createHash('sha256').update(raw).digest('hex');
const safe = name => typeof name === 'string' && /^[a-zA-Z0-9_./-]+$/.test(name) &&
  name.split('/').every(part => part && part !== '.' && part !== '..');

export function requirePlainExecution({boundedHeap=false}={}) {
  const bounded=boundedHeap===true&&process.execArgv.length===2
    &&process.execArgv[0]==='--max-old-space-size=128'
    &&process.execArgv[1]==='--max-semi-space-size=16';
  if ((process.execArgv.length&&!bounded) || process.env.NODE_OPTIONS?.trim() || process.env.NODE_PATH?.trim())
    throw Error('Native preparation requires the reviewed plain Node launch without loaders/preloads');
}

export function candidateBudget(inputs, {reserveBytes = 131072, reserveDescriptors = 16} = {}) {
  const limitBytes = 256 * 1024 * 1024, limitDescriptors = 512;
  if (!Number.isSafeInteger(reserveBytes) || reserveBytes < 0 || !Number.isInteger(reserveDescriptors) || reserveDescriptors < 0)
    throw Error('Invalid preparation budget reservation');
  let bytes = 0, descriptors = 0;
  function add(item) {
    if (!Number.isSafeInteger(item?.bytes) || item.bytes < 0 || item.bytes > 32 * 1024 * 1024)
      throw Error('Invalid whole-file admission');
    if (bytes + item.bytes + reserveBytes > limitBytes || descriptors + 1 + reserveDescriptors > limitDescriptors)
      throw Error('Aggregate evidence preparation budget exceeded');
    bytes += item.bytes; descriptors++;
  }
  for (const input of inputs) add(input);
  return {add, snapshot: () => ({accounted_bytes: bytes, accounted_descriptors: descriptors,
    reserved_review_bytes: reserveBytes, reserved_review_descriptors: reserveDescriptors, limit_bytes: limitBytes,
    limit_descriptors: limitDescriptors, limits_include_reserve: true})};
}

export function originalCandidateAssets(repo, manifest) {
  if (manifest.asset_root !== 'data/canonical-grid') throw Error('Unknown candidate installation namespace');
  const output = {};
  for (const [key, filename] of [['bounds', 'bounds.json.gz'], ['province_membership', 'province-membership.bin.gz']]) {
    const reference = manifest.original_assets?.[key], descriptor = manifest[key];
    if (!/^[a-f0-9]{40}$/.test(reference?.commit ?? '') || reference.path !== 'data/canonical-grid/' + filename ||
      descriptor?.path !== filename || reference.sha256 !== descriptor.sha256 || !/^[a-f0-9]{64}$/.test(reference.sha256))
      throw Error('Invalid explicit original asset reference');
    const tree = execFileSync('git', ['-C', repo, 'ls-tree', '-z', reference.commit, '--', reference.path], {encoding: 'utf8'});
    if (!/^100644 blob /.test(tree) || tree.slice(tree.indexOf('\t') + 1) !== reference.path + '\0')
      throw Error('Original identity asset must be an ordinary blob');
    const blob = tree.split(' ')[2].split('\t')[0];
    const bytes = Number(execFileSync('git', ['-C', repo, 'cat-file', '-s', blob], {encoding: 'utf8'}));
    if (!Number.isSafeInteger(bytes) || bytes < 0 || bytes > 32 * 1024 * 1024) throw Error('Original identity byte budget exceeded');
    const raw = execFileSync('git', ['-C', repo, 'cat-file', 'blob', blob], {maxBuffer: 32 * 1024 * 1024});
    if (raw.length !== bytes || digest(raw) !== reference.sha256) throw Error('Original identity asset hash differs');
    output[key] = raw;
  }
  return output;
}

export function committedPreparationFiles(repo, commit, names) {
  if (!/^[a-f0-9]{40}$/.test(commit ?? '') || !Array.isArray(names) || !names.length ||
    new Set(names).size !== names.length) throw Error('Explicit immutable code inventory required');
  const root = fs.realpathSync(repo);
  for (const name of names) {
    if (!safe(name)) throw Error('Unsafe executed code path');
    for (let directory = path.dirname(path.join(root, name));; directory = path.dirname(directory)) {
      const configuration = path.join(directory, 'package.json');
      if (fs.existsSync(configuration) && !names.includes(path.relative(root, configuration)))
        throw Error('Undeclared module package configuration');
      if (directory === root) break;
    }
  }
  return names.map(name => {
    if (!safe(name)) throw Error('Unsafe executed code path');
    const tree = execFileSync('git', ['-C', root, 'ls-tree', '-z', commit, '--', name], {encoding: 'utf8'});
    if (!/^100(?:644|755) blob /.test(tree) || tree.slice(tree.indexOf('\t') + 1) !== name + '\0')
      throw Error('Commit exact ordinary executed files before generation');
    const blob = tree.split(' ')[2].split('\t')[0];
    const count = Number(execFileSync('git', ['-C', root, 'cat-file', '-s', blob], {encoding: 'utf8'}));
    if (!Number.isSafeInteger(count) || count < 0 || count > 32 * 1024 * 1024)
      throw Error('Executed code exceeds existing whole-file budget');
    const file = path.join(root, name);
    const actualStat = fs.lstatSync(file);
    if (!actualStat.isFile() || fs.realpathSync(file) !== file)
      throw Error('Executed code must be ordinary and inside the repository');
    if (actualStat.size !== count) throw Error('Executed code differs from immutable bootstrap');
    const original = execFileSync('git', ['-C', root, 'cat-file', 'blob', blob], {maxBuffer: 32 * 1024 * 1024});
    const actual = fs.readFileSync(file);
    if (actual.length !== count || !actual.equals(original)) throw Error('Executed code differs from immutable bootstrap');
    return {path: name, bytes: actual.length, sha256: digest(actual)};
  });
}

// Only new offline scratch vintages are generated; staging is a separate action.
export function createNativeCandidateOutput(repo, relative) {
  if (!safe(relative) || !/^\.cache\/native-grid-candidates\/[a-zA-Z0-9_-]+$/.test(relative))
    throw Error('Require a new offline native candidate vintage');
  const root = fs.realpathSync(repo), destination = path.join(root, relative);
  let current = root;
  for (const part of relative.split('/')) {
    current = path.join(current, part);
    if (fs.existsSync(current) || fs.lstatSync(current, {throwIfNoEntry: false})) {
      if (current === destination || !fs.lstatSync(current).isDirectory() || fs.realpathSync(current) !== current)
        throw Error('Preserve existing output; symlink ancestors are prohibited');
    }
  }
  fs.mkdirSync(path.dirname(destination), {recursive: true});
  fs.mkdirSync(destination); // Exclusive final creation, including concurrent reuse.
  return destination;
}
