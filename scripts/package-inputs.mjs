import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';

export const PACKAGE_INPUT_FILE = '.github/package-inputs.json';
const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
export const safePackagePath = value => typeof value === 'string' && /^[A-Za-z0-9_.\/-]+$/.test(value)
  && !value.startsWith('/') && value.replace(/\/$/, '').split('/').every(part => part && part !== '.' && part !== '..');
export const containsPackagePath = (paths, file) => paths.some(input => input.endsWith('/') ? file.startsWith(input) : file === input);

export function validatePackageInputs(value) {
  if (value?.version !== 1) throw Error('Unsupported package input definition');
  for (const name of ['inputs', 'optional_inputs', 'verification_paths', 'generated_outputs']) {
    const rows = value[name];
    if (!Array.isArray(rows) || rows.length > 1024 || rows.some(row => !safePackagePath(row)) || new Set(rows).size !== rows.length) throw Error(`Invalid package ${name}`);
  }
  if (!value.inputs.length || !value.inputs.includes(PACKAGE_INPUT_FILE) || value.optional_inputs.some(row => !value.inputs.includes(row))) throw Error('Incomplete package input definition');
  if (value.inputs.some(row => value.inputs.some(parent => parent !== row && parent.endsWith('/') && row.startsWith(parent)))) throw Error('Overlapping package inputs');
  // Ambient databases, secrets and existing build/cache output cannot become source inputs.
  if (value.inputs.some(row => /^(?:\.git(?:\/|$)|node_modules(?:\/|$)|\.cache(?:\/|$)|dist(?:\/|$)|data\/atlas\.sqlite)/.test(row))) throw Error('Ambient/generated package source input');
  const outputs = ['dist/', '.cache/deployment-budget.json', 'data/prepared-evidence/', 'data/atlas.sqlite'];
  if (value.generated_outputs.some(row => !outputs.includes(row))) throw Error('Unsupported generated package output');
  return value;
}

export function loadPackageInputs(directory = root) {
  return validatePackageInputs(JSON.parse(fs.readFileSync(path.join(directory, PACKAGE_INPUT_FILE), 'utf8')));
}

export async function readPackageInputs({route, base, api}) {
  const blob = await api(`${route}/contents/${PACKAGE_INPUT_FILE}?ref=${base}`);
  if (blob?.type !== 'file' || blob.encoding !== 'base64' || blob.path !== PACKAGE_INPUT_FILE ||
      !/^[a-f0-9]{40}$/.test(blob.sha ?? '') || !Number.isSafeInteger(blob.size) || blob.size > 128 * 1024 || typeof blob.content !== 'string') throw Error('Package input definition unavailable');
  const raw = Buffer.from(blob.content, 'base64');
  if (raw.length !== blob.size || createHash('sha1').update(`blob ${raw.length}\0`).update(raw).digest('hex') !== blob.sha) throw Error('Package input definition bytes changed');
  return validatePackageInputs(JSON.parse(raw));
}

export function packagePathRequired(file, definition) {
  return containsPackagePath(definition.inputs, file) || containsPackagePath(definition.verification_paths, file);
}
