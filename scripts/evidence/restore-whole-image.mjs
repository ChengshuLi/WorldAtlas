// Operational exact-byte restoration; the original producer and its retained
// artifacts remain immutable. Authenticate the complete image before any write.
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
export {retainWholeImage} from '../../coordination/engineering/eastern-two-gap-repair-native-20261007/whole-image.mjs';

const CAP = 32 * 1024 * 1024;
const PART = 16 * 1024 * 1024;
const IMAGE = 256 * 1024 * 1024;
const sha = body => createHash('sha256').update(body).digest('hex');
const digest = value => typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);
const safe = value => typeof value === 'string' && !path.isAbsolute(value) &&
  !value.includes('\\') && !value.includes('\0') &&
  value.split('/').every(piece => piece && piece !== '.' && piece !== '..');
function bytes(root, relative) {
  assert(safe(relative) && path.isAbsolute(root) && fs.realpathSync(root) === root);
  const file = path.join(root, relative), stat = fs.lstatSync(file);
  assert(stat.isFile() && fs.realpathSync(file) === file && stat.size <= CAP);
  const fd = fs.openSync(file, 'r');
  try {
    const opened = fs.fstatSync(fd);
    assert(opened.isFile() && opened.size === stat.size && fs.realpathSync(file) === file);
    const raw = Buffer.alloc(stat.size + 1);
    let offset = 0;
    while (offset < raw.length) {
      const length = fs.readSync(fd, raw, offset, raw.length - offset, null);
      if (!length) break;
      offset += length;
    }
    assert.equal(offset, stat.size, 'Actual ordinary EOF length differs');
    assert.equal(fs.readSync(fd, Buffer.alloc(1), 0, 1, null), 0, 'Ordinary body grew');
    return raw.subarray(0, offset);
  } finally { fs.closeSync(fd); }
}
function boundedInteger(value, limit, name) {
  assert(Number.isSafeInteger(value) && value > 0 && value <= limit, name);
}
export function restoreWholeImage(source, out, {expectedIndexSha}) {
  assert(path.isAbsolute(source) && fs.realpathSync(source) === source);
  assert(path.isAbsolute(out) && !fs.existsSync(out));
  assert(fs.realpathSync(path.dirname(out)) === path.dirname(out));
  assert(digest(expectedIndexSha));
  const indexRaw = bytes(source, 'index.json');
  assert.equal(sha(indexRaw), expectedIndexSha, 'Whole image index binding differs');
  const index = JSON.parse(indexRaw);
  assert.equal(index.version, 1);
  assert.equal(index.issue, 1295);
  assert.equal(index.kind, 'ordered-exact-original-byte-fragments');
  assert(Array.isArray(index.parts) && Array.isArray(index.files));
  assert(Number.isSafeInteger(index.whole_bytes) && index.whole_bytes >= 0 && index.whole_bytes <= IMAGE, 'Bounded original fixed image required');
  assert(digest(index.whole_sha256));
  // Admit complete rosters and aggregate bounds before opening any part.
  let offset = 0;
  const names = new Set();
  for (const pin of index.parts) {
    assert(safe(pin.path) && !names.has(pin.path));
    names.add(pin.path);
    assert.equal(pin.offset, offset);
    boundedInteger(pin.bytes, CAP, 'Encoded part exceeds original cap');
    boundedInteger(pin.decoded_bytes, PART, 'Decoded part exceeds original cap');
    assert(digest(pin.sha256) && digest(pin.decoded_sha256));
    offset += pin.decoded_bytes;
    assert(Number.isSafeInteger(offset) && offset <= index.whole_bytes);
  }
  assert.equal(offset, index.whole_bytes, 'Incomplete whole-image part roster');
  offset = 0;
  const members = new Set();
  for (const pin of index.files) {
    assert(safe(pin.path) && !members.has(pin.path));
    members.add(pin.path);
    assert.equal(pin.offset, offset);
    boundedInteger(pin.bytes, CAP, 'Member exceeds original cap');
    assert(digest(pin.sha256) && ['100644', '100755'].includes(pin.mode));
    offset += pin.bytes;
    assert(Number.isSafeInteger(offset) && offset <= index.whole_bytes);
  }
  assert.equal(offset, index.whole_bytes, 'Original image roster omits bytes');
  for (const member of members) {
    const pieces = member.split('/');
    for (let i = 1; i < pieces.length; i++) {
      assert(!members.has(pieces.slice(0, i).join('/')), 'Member directory collision');
    }
  }
  // One complete private image replaces retained decoded chunks plus a second
  // concatenated image. Part frames end after copying into this authenticated body.
  const whole = Buffer.alloc(index.whole_bytes);
  function consumePart(pin) {
    const encoded = bytes(source, pin.path);
    assert.equal(encoded.length, pin.bytes);
    assert.equal(sha(encoded), pin.sha256);
    const raw = gunzipSync(encoded, {
      maxOutputLength: pin.decoded_bytes,
      chunkSize: Math.max(64, pin.decoded_bytes + 1)
    });
    assert.equal(raw.length, pin.decoded_bytes);
    assert.equal(sha(raw), pin.decoded_sha256);
    assert.equal(raw.copy(whole, pin.offset), pin.decoded_bytes);
  }
  for (const pin of index.parts) consumePart(pin);
  assert.equal(sha(whole), index.whole_sha256);
  for (const pin of index.files) {
    const body = whole.subarray(pin.offset, pin.offset + pin.bytes);
    assert.equal(body.length, pin.bytes);
    assert.equal(sha(body), pin.sha256);
  }
  fs.mkdirSync(out);
  for (const pin of index.files) {
    const file = path.join(out, pin.path);
    fs.mkdirSync(path.dirname(file), {recursive: true});
    assert.equal(fs.realpathSync(path.dirname(file)), path.dirname(file));
    fs.writeFileSync(file, whole.subarray(pin.offset, pin.offset + pin.bytes), {
      flag: 'wx', mode: pin.mode === '100755' ? 0o755 : 0o644
    });
  }
  return index;
}
