// Add only the two accepted unchanged whole JSON bodies to the same byte map.
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {retainWholeImage} from './whole-image.mjs';
const sha = raw => createHash('sha256').update(raw).digest('hex');
const CAP = 32 * 1024 * 1024;
const REPORT_SHA = '6d5dee8d80d2927bdf7e2c9a1745ebf5187bb657a03f4fef7396092a50b7d2a6';
export function augmentAcceptedIntegration({originalObjects, acceptedRun, output, transport}) {
  for (const root of [originalObjects, acceptedRun]) assert(path.isAbsolute(root) && fs.realpathSync(root) === root);
  for (const target of [output, transport]) assert(path.isAbsolute(target) && !fs.existsSync(target) && fs.realpathSync(path.dirname(target)) === path.dirname(target));
  const reportRaw = fs.readFileSync(path.join(acceptedRun, 'report.json'));
  assert.equal(sha(reportRaw), REPORT_SHA, 'Genuine complete accepted integration report differs');
  const report = JSON.parse(reportRaw);
  assert.equal(report.status, 'PASS');
  assert.equal(report.execution_commit, '23e492515bdd2de5701c4b87e9661768e52fce4b');
  const map = JSON.parse(fs.readFileSync(path.join(originalObjects, 'canonical-path-map.json')));
  assert.equal(map.logical_targets.length, 300);
  fs.mkdirSync(output); fs.mkdirSync(path.join(output, 'objects'));
  for (const pin of map.distinct_objects) {
    const source = path.join(originalObjects, pin.path), stat = fs.lstatSync(source);
    assert(stat.isFile() && fs.realpathSync(source) === source && stat.size === pin.bytes && pin.bytes <= CAP);
    const raw = fs.readFileSync(source); assert.equal(sha(raw), pin.sha256);
    assert.equal((stat.mode & 0o111) ? '100755' : '100644', pin.mode);
    fs.copyFileSync(source, path.join(output, pin.path), fs.constants.COPYFILE_FICLONE);
  }
  for (const target of ['data/geography/part-29.json', 'data/granularity-audit.json']) {
    const original = report.outputs.find(pin => pin.path === target);
    assert(original && original.bytes > 0 && original.bytes <= CAP);
    const source = path.join(acceptedRun, 'delivery', target), stat = fs.lstatSync(source);
    assert(stat.isFile() && fs.realpathSync(source) === source && stat.size === original.bytes);
    const fd = fs.openSync(source, 'r'); let raw;
    try {
      const buffer = Buffer.alloc(original.bytes + 1); let n = 0;
      while (n < buffer.length) { const got = fs.readSync(fd, buffer, n, buffer.length - n, null); if (!got) break; n += got; }
      assert.equal(n, original.bytes); assert.equal(fs.readSync(fd, Buffer.alloc(1), 0, 1, null), 0);
      raw = buffer.subarray(0, n);
    } finally { fs.closeSync(fd); }
    assert.equal(sha(raw), original.sha256);
    const mode = (stat.mode & 0o111) ? '100755' : '100644', object = 'objects/' + mode + '-' + sha(raw);
    assert.equal(mode, '100644');
    if (!map.distinct_objects.some(pin => pin.path === object)) {
      fs.copyFileSync(source, path.join(output, object), fs.constants.COPYFILE_FICLONE);
      map.distinct_objects.push({path: object, mode, bytes: raw.length, sha256: sha(raw)});
    }
    map.logical_targets.push({target, object, mode, bytes: raw.length, sha256: sha(raw),
      origin: {kind: 'accepted-complete-integration-unchanged-body', execution_commit: report.execution_commit,
        original_report_sha256: REPORT_SHA, original_output: original,
        original_scientific_vintage_preserved: true, current_science_rerun_claimed: false}});
  }
  assert.equal(map.logical_targets.length, 302); assert.equal(new Set(map.logical_targets.map(pin => pin.target)).size, 302);
  map.accepted_integration_report_sha256 = REPORT_SHA;
  fs.writeFileSync(path.join(output, 'canonical-path-map.json'), JSON.stringify(map) + '\n', {flag: 'wx'});
  const index = retainWholeImage(output, transport, {roles: Object.fromEntries(map.distinct_objects.map(pin =>
    [pin.path, {kind: 'exact-mode-whole-byte-object', logical_targets: map.logical_targets.filter(row => row.object === pin.path)}]))});
  return {status: 'PASS', logical_targets: 302, whole_bytes: index.whole_bytes, objects: map.distinct_objects.length,
    parts: index.parts.length, encoded_bytes: index.parts.reduce((n, pin) => n + pin.bytes, 0),
    index_bytes: fs.statSync(path.join(transport, 'index.json')).size, index_sha256: sha(fs.readFileSync(path.join(transport, 'index.json'))),
    scientific_producers_invoked: false};
}
