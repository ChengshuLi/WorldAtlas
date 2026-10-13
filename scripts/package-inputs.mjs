import os from 'node:os';
import {getHeapStatistics} from 'node:v8';
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';

export const PACKAGE_INPUT_FILE = '.github/package-inputs.json';
const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
export const safePackagePath = value => typeof value === 'string' && /^[A-Za-z0-9_.\/-]+$/.test(value)
  && !value.startsWith('/') && value.replace(/\/$/, '').split('/').every(part => part && part !== '.' && part !== '..');
export const containsPackagePath = (paths, file) => paths.some(input => input.endsWith('/') ? file.startsWith(input) : file === input);

export function packageInputByteBudget() {
  const heap=getHeapStatistics();
  // Eightfold reservation, shared with native readback: encoded metadata,
  // decoded strings, parsed object graphs and comparison copies coexist.
  return Math.floor(Math.min(process.availableMemory?.() ?? os.freemem(), heap.heap_size_limit-heap.used_heap_size)/8);
}

export function validatePackageInputs(value, {maximumBytes=packageInputByteBudget()} = {}) {
  if(!Number.isSafeInteger(maximumBytes)||maximumBytes<=0||Buffer.byteLength(JSON.stringify(value)??'')>maximumBytes)
    throw Error('Package input metadata exceeds available-memory admission');
  if (value?.version !== 1) throw Error('Unsupported package input definition');
  for (const name of ['inputs', 'optional_inputs', 'verification_paths', 'generated_outputs']) {
    const rows = value[name];
    if (!Array.isArray(rows) || rows.some(row => !safePackagePath(row)) || new Set(rows).size !== rows.length) throw Error(`Invalid package ${name}`);
  }
  const inputSet=new Set(value.inputs);
  if (!value.inputs.length || !inputSet.has(PACKAGE_INPUT_FILE) || value.optional_inputs.some(row => !inputSet.has(row))) throw Error('Incomplete package input definition');
  for(const row of value.inputs) for(let slash=row.indexOf('/');slash>=0;slash=row.indexOf('/',slash+1)){
    const parent=row.slice(0,slash+1);
    if(parent!==row&&inputSet.has(parent))throw Error('Overlapping package inputs');
  }
  // Ambient databases, secrets and existing build/cache output cannot become source inputs.
  if (value.inputs.some(row => /^(?:\.git(?:\/|$)|node_modules(?:\/|$)|\.cache(?:\/|$)|dist(?:\/|$)|data\/atlas\.sqlite)/.test(row))) throw Error('Ambient/generated package source input');
  const outputs = ['dist/', '.cache/deployment-budget.json', 'data/prepared-evidence/', 'data/atlas.sqlite'];
  if (value.generated_outputs.some(row => !outputs.includes(row))) throw Error('Unsupported generated package output');
  return value;
}

export function loadPackageInputs(directory = root) {
  const file=path.join(directory,PACKAGE_INPUT_FILE),maximumBytes=packageInputByteBudget();
  if(fs.statSync(file).size>maximumBytes)throw Error('Package input metadata exceeds available-memory admission');
  return validatePackageInputs(JSON.parse(fs.readFileSync(file,'utf8')),{maximumBytes});
}

export async function readPackageInputs({route, base, api, maximumBytes=packageInputByteBudget()}) {
  if(!Number.isSafeInteger(maximumBytes)||maximumBytes<=0)throw Error('Invalid package metadata memory admission');
  const blob = await api(`${route}/contents/${PACKAGE_INPUT_FILE}?ref=${base}`);
  if (blob?.type !== 'file' || blob.encoding !== 'base64' || blob.path !== PACKAGE_INPUT_FILE ||
      !/^[a-f0-9]{40}$/.test(blob.sha ?? '') || !Number.isSafeInteger(blob.size) || blob.size > maximumBytes || typeof blob.content !== 'string') throw Error('Package input definition unavailable');
  // Base64 expansion plus ordinary line wrapping fits two encoded characters
  // per admitted decoded byte. Check before allocating the decoded buffer.
  if(blob.content.length>2*maximumBytes+4)throw Error('Encoded package metadata exceeds available-memory admission');
  const raw = Buffer.from(blob.content, 'base64');
  if (raw.length !== blob.size || createHash('sha1').update(`blob ${raw.length}\0`).update(raw).digest('hex') !== blob.sha) throw Error('Package input definition bytes changed');
  return validatePackageInputs(JSON.parse(raw),{maximumBytes});
}

export function packagePathRequired(file, definition) {
  return containsPackagePath(definition.inputs, file) || containsPackagePath(definition.verification_paths, file);
}
