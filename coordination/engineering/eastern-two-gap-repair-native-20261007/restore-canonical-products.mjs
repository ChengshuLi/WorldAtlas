// Exact accepted whole-byte restoration before the existing offline readers.
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {restoreWholeImage} from './whole-image.mjs';

const sha = raw => createHash('sha256').update(raw).digest('hex');
const CAP = 32 * 1024 * 1024;
const canonicalIndex = '6b990b9322be838415f35371e17919723b0bc4b226766cff589ccc2f6d9d83d4';
const priorIndex = '60444198fb8966d5e80c327b99c4bcaf5b8c879326abd7b1b8f9039f72971006';
const originalPriorIndex = 'e34743a84df2aaaa668b4e7b23c4f6870379edfe7eb88a427d6005b47333a393';
const namespace = 'coordination/engineering/eastern-two-gap-repair-native-20261007';
const safe = value => typeof value === 'string' && !path.isAbsolute(value) &&
  !value.includes('\\') && !value.includes('\0') && value.split('/').every(x => x && x !== '.' && x !== '..');

function ordinary(root, relative) {
  assert(safe(relative) && path.isAbsolute(root) && fs.realpathSync(root) === root);
  let current = root;
  for (const piece of relative.split('/')) {
    current = path.join(current, piece);
    let stat;
    try { stat = fs.lstatSync(current); } catch (error) { if (error.code !== 'ENOENT') throw error; }
    if (stat) assert(!stat.isSymbolicLink(), 'Nonordinary canonical ancestor');
  }
  return current;
}
function read(root, pin) {
  assert(Number.isSafeInteger(pin.bytes) && pin.bytes >= 0 && pin.bytes <= CAP);
  const file = ordinary(root, pin.path), stat = fs.lstatSync(file);
  assert(stat.isFile() && stat.size === pin.bytes);
  const fd = fs.openSync(file, 'r');
  try {
    assert.equal(fs.fstatSync(fd).size, pin.bytes);
    const raw = Buffer.alloc(pin.bytes + 1); let offset = 0;
    while (offset < raw.length) {
      const n = fs.readSync(fd, raw, offset, raw.length - offset, null);
      if (!n) break;
      offset += n;
    }
    assert.equal(offset, pin.bytes, 'Actual canonical EOF differs');
    assert.equal(fs.readSync(fd, Buffer.alloc(1), 0, 1, null), 0);
    const result = raw.subarray(0, offset);
    assert.equal(sha(result), pin.sha256);
    assert.equal((stat.mode & 0o111) ? '100755' : '100644', pin.mode);
    return result;
  } finally { fs.closeSync(fd); }
}
function copy(root, target, source, pin) {
  assert(safe(target) && ['100644', '100755'].includes(pin.mode));
  read(source, pin);
  const destination = ordinary(root, target);
  fs.mkdirSync(path.dirname(destination), {recursive: true});
  assert.equal(fs.realpathSync(path.dirname(destination)), path.dirname(destination));
  if (fs.existsSync(destination)) assert(fs.lstatSync(destination).isFile());
  fs.copyFileSync(path.join(source, pin.path), destination, fs.constants.COPYFILE_FICLONE);
  read(root, {...pin, path: target});
}

export function restoreCanonicalProducts({root, temporaryRoot}) {
  assert(path.isAbsolute(root) && fs.realpathSync(root) === root);
  assert(path.isAbsolute(temporaryRoot) && fs.realpathSync(temporaryRoot) === temporaryRoot);
  const temporary = fs.mkdtempSync(path.join(temporaryRoot, '1295-canonical-'));
  const canonical = path.join(temporary, 'canonical-objects');
  const prior = path.join(temporary, 'prior-objects');
  const priorImage = path.join(temporary, 'original-v1-image');
  restoreWholeImage(path.join(root, namespace, 'canonical-products'), canonical, {expectedIndexSha: canonicalIndex});
  restoreWholeImage(path.join(root, namespace, 'prior-source-objects'), prior, {expectedIndexSha: priorIndex});
  const map = JSON.parse(fs.readFileSync(path.join(canonical, 'canonical-path-map.json')));
  const old = JSON.parse(fs.readFileSync(path.join(prior, 'prior-path-map.json')));
  assert.equal(map.issue, 1295); assert.equal(map.version, 1);
  assert.equal(map.kind, 'complete-accepted-canonical-product-byte-map');
  assert.equal(old.kind, 'complete-prior-v1-mode-whole-byte-bijection');
  assert.equal(old.original_index_sha256, originalPriorIndex);
  assert.equal(old.shared_canonical_index_sha256, canonicalIndex);
  assert.equal(map.logical_targets.length, 300); assert.equal(old.logical_targets.length, 122);
  assert.equal(new Set(map.logical_targets.map(p => p.target)).size, 300);
  fs.mkdirSync(priorImage);
  const canonicalObjects = new Map(map.distinct_objects.map(p => [p.path, p]));
  for (const pin of map.logical_targets) {
    assert(pin.target.startsWith('data/canonical-grid/eastern-v8/') ||
      pin.target.startsWith('data/ownership-history/') || pin.target.startsWith('data/ownership-runtime/') ||
      pin.target === 'data/pixel-audit.json' || pin.target === namespace + '/accepted-pixel-verification.json');
    const object = canonicalObjects.get(pin.object);
    assert(object && object.bytes === pin.bytes && object.sha256 === pin.sha256 && object.mode === pin.mode);
    copy(root, pin.target, canonical, object);
  }
  const original = new Map(old.original_index.files.map(p => [p.path, p]));
  for (const pin of old.logical_targets) {
    const expected = original.get(pin.path);
    assert(expected && expected.bytes === pin.bytes && expected.sha256 === pin.sha256 && expected.mode === pin.mode);
    const object = pin.shared_canonical_object ?? {...pin, path: pin.object};
    if (pin.shared_canonical_object) assert.deepEqual(canonicalObjects.get(object.path), object);
    copy(priorImage, pin.path, pin.shared_canonical_object ? canonical : prior, object);
  }
  return {version: 1, issue: 1295, canonical_paths: 300, prior_paths: 122,
    canonical_index_sha256: canonicalIndex, prior_index_sha256: priorIndex,
    original_prior_index_sha256: originalPriorIndex, priorImage, temporary,
    scientific_producers_invoked: false, original_vintages_and_unknowns_preserved: true};
}
