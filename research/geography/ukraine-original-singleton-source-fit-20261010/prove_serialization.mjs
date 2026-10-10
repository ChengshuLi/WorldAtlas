import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {isDeepStrictEqual} from 'node:util';

const here = path.dirname(fileURLToPath(import.meta.url));
const repo = path.resolve(here, '../../..');
const git = (...args) => execFileSync('git', ['-C', repo, ...args], {maxBuffer: 32 * 1024 ** 2});
const sha = raw => createHash('sha256').update(raw).digest('hex');
const canonical = value => Array.isArray(value) ? value.map(canonical) : value && typeof value === 'object' ? Object.fromEntries(Object.keys(value).sort().map(key => [key, canonical(value[key])])) : value;
const originalHash = 'acd61551d2dbc9b6925e6d8c2d17cb210a6dcf6f3d80bbbadb64951660e3b746';
const id = 'physical-component:6fd25496ae4a7635eef229d0cfd1eb8dc7d9c10c252d3255fe8d42d186e706d1';
const head = git('rev-parse', 'HEAD').toString().trim();
if (!fs.readFileSync(fileURLToPath(import.meta.url)).equals(git('show', head + ':' + path.relative(repo, fileURLToPath(import.meta.url))))) throw Error('Unfrozen code');
const originalPath = path.relative(repo, path.join(here, 'vintages/physical-restoration-001/original-component.json'));
const raw = git('show', head + ':' + originalPath);
function prove(bytes, proposedFeature) {
  if (sha(bytes) !== originalHash) throw Error('Wrong original whole byte hash');
  const original = JSON.parse(bytes);
  if (original.id !== id || !isDeepStrictEqual(original, proposedFeature)) throw Error('Parsed feature values, keys, types or identity differ');
  const serialized = Buffer.from(JSON.stringify(canonical(original)) + '\n');
  if (!isDeepStrictEqual(JSON.parse(serialized), original)) throw Error('Serialization loses values');
  return {original_raw_sha256: originalHash, derived_js_canonical_sha256: sha(serialized), original_path: originalPath, component_id: id, exact_parsed_value_roundtrip: true, bytes: raw.length, derived_js_bytes: serialized.length};
}
const original = JSON.parse(raw);
const positive = prove(raw, original);
const controls = [];
function refusal(name, bytes, value) {
  let error;
  try { prove(bytes, value); } catch (e) { error = e.message; }
  if (!error) throw Error('Adverse control unexpectedly accepted: ' + name);
  controls.push({name, observed_error: error, rejected: true});
}
const changedNumber = structuredClone(original);
changedNumber.properties.measured_fragment_area_sum_m2 += Number.EPSILON;
refusal('changed-numeric-value', raw, changedNumber);
const extra = structuredClone(original); extra.properties.unexpected = true;
refusal('unexpected-field', raw, extra);
const other = structuredClone(original); other.id = 'physical-component:unrelated';
refusal('unrelated-row', raw, other);
refusal('unrelated-byte-hash', Buffer.from(JSON.stringify(other) + '\n'), other);
const output = path.join(here, 'vintages/serialization-proof-001');
if (fs.existsSync(output)) throw Error('Existing output');
for (let p = path.dirname(output); p !== repo; p = path.dirname(p)) if (fs.existsSync(p) && fs.lstatSync(p).isSymbolicLink()) throw Error('Symlink output parent');
fs.mkdirSync(output);
fs.writeFileSync(path.join(output, 'result.json'), JSON.stringify({execution_commit: head, ...positive, controls, limits: ['This proves exact raw-byte custody and deterministic cross-serialization equivalence only.', 'No replacement of original hash and no common-source admission granted.']}) + '\n', {flag: 'wx'});
console.log(JSON.stringify({originalHash, derivedHash: positive.derived_js_canonical_sha256, controls}));
