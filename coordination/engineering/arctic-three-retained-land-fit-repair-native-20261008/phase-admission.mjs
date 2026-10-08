import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
const MAX_FILE = 32 * 1024 * 1024, MAX_PHASE = 256 * 1024 * 1024;

function ordinary(file) {
  assert(path.isAbsolute(file) && !file.split(path.sep).includes('..'), 'Absolute ordinary input required');
  for (let current = file; ; current = path.dirname(current)) {
    const stat = fs.lstatSync(current);
    assert(!stat.isSymbolicLink(), 'Symlink input or ancestor rejected');
    if (current === path.dirname(current)) break;
  }
  const stat = fs.lstatSync(file);
  assert(stat.isFile(), 'Ordinary input body required');
  return stat;
}

// All declared bodies, decoded products, code and whole installed runtime are
// reserved before any body hash/read. No per-shard reset within a process.
export function admitPhase({inputs, runtime, outputReserve, metadataBytes = 0}) {
  assert(Array.isArray(inputs) && inputs.length <= 512);
  assert(Number.isSafeInteger(outputReserve) && outputReserve >= 0);
  assert(Number.isSafeInteger(metadataBytes) && metadataBytes >= 0);
  const seen = new Set();
  let bytes = outputReserve + metadataBytes;
  const records = [...inputs.map(pin => ({...pin, installed_runtime: false})),
    {...runtime, installed_runtime: true}];
  assert(records.length <= 512, 'Complete unique descriptor cap');
  const snapshots = records.map(pin => {
    assert(!seen.has(pin.path), 'Duplicate physical input requires explicit prior whole-byte alias proof');
    seen.add(pin.path);
    assert(Number.isSafeInteger(pin.bytes) && pin.bytes >= 0 && /^[a-f0-9]{64}$/.test(pin.sha256));
    assert(pin.installed_runtime || pin.bytes <= MAX_FILE, 'Ordinary whole-body cap');
    assert(Number.isSafeInteger(pin.decoded_bytes ?? 0) && (pin.decoded_bytes ?? 0) >= 0 &&
      (pin.decoded_bytes ?? 0) <= MAX_FILE, 'Whole decoded member cap');
    const stat = ordinary(pin.path);
    assert.equal(stat.size, pin.bytes); assert.equal(stat.mode & 0o777, pin.mode);
    bytes += pin.bytes + (pin.decoded_bytes ?? 0);
    assert(Number.isSafeInteger(bytes) && bytes <= MAX_PHASE, 'Complete phase byte cap');
    return {pin, identity: {dev: stat.dev, ino: stat.ino, size: stat.size, mode: stat.mode,
      mtimeMs: stat.mtimeMs, ctimeMs: stat.ctimeMs}};
  });
  return {bytes, descriptors: records.length, outputReserve, metadataBytes, snapshots};
}

export function readAdmittedBody(admission, file) {
  const snapshot = admission.snapshots.find(row => row.pin.path === file);
  assert(snapshot, 'Unadmitted body read');
  const before = ordinary(file), identity = snapshot.identity;
  for (const field of Object.keys(identity)) assert.equal(before[field], identity[field], 'Body identity changed');
  const fd = fs.openSync(file, fs.constants.O_RDONLY | fs.constants.O_NOFOLLOW);
  try {
    const body = Buffer.alloc(snapshot.pin.bytes); let offset = 0;
    while (offset < body.length) {
      const count = fs.readSync(fd, body, offset, body.length - offset, null);
      assert(count > 0, 'Truncated admitted body'); offset += count;
    }
    assert.equal(fs.readSync(fd, Buffer.alloc(1), 0, 1, null), 0, 'Growing admitted body');
    assert.equal(createHash('sha256').update(body).digest('hex'), snapshot.pin.sha256);
    const after = fs.fstatSync(fd);
    for (const field of Object.keys(identity)) assert.equal(after[field], identity[field], 'Body changed while read');
    return body;
  } finally { fs.closeSync(fd); }
}
