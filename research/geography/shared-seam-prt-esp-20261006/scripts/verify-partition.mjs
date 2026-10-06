#!/usr/bin/env node

// Verify retained contiguous source parts against both the baseline registry
// pin and the upstream Git LFS object pin without assembling a large file.
import { createHash } from 'node:crypto';
import { open, readdir, writeFile } from 'node:fs/promises';
import path from 'node:path';

const [directoryArg, byteArg, baselineShaArg, lfsShaArg] = process.argv.slice(2);
if (!directoryArg || !byteArg || !baselineShaArg || !lfsShaArg) {
  throw new Error('usage: verify-partition.mjs PARTS_DIR EXPECTED_BYTES BASELINE_SHA256 UPSTREAM_LFS_SHA256');
}
const directory = path.resolve(directoryArg);
const expectedBytes = Number(byteArg);
for (const sha of [baselineShaArg, lfsShaArg]) if (!/^[a-f0-9]{64}$/i.test(sha)) throw new Error('expected valid SHA-256 pins');
const partLimitBytes = 32 * 1024 * 1024;
const names = (await readdir(directory)).filter(name => /^part-\d+\.bin$/.test(name)).sort((a, b) => Number(a.match(/\d+/)[0]) - Number(b.match(/\d+/)[0]));
if (names.length !== Math.ceil(expectedBytes / partLimitBytes)) throw new Error('unexpected number of partition files');
const whole = createHash('sha256');
const parts = [];
let totalBytes = 0;
for (const name of names) {
  const file = await open(path.join(directory, name), 'r');
  const digest = createHash('sha256');
  const buffer = Buffer.allocUnsafe(1024 * 1024);
  let bytes = 0;
  try {
    while (true) {
      const { bytesRead } = await file.read(buffer, 0, buffer.length, null);
      if (!bytesRead) break;
      const chunk = buffer.subarray(0, bytesRead);
      whole.update(chunk);
      digest.update(chunk);
      bytes += bytesRead;
    }
  } finally { await file.close(); }
  if (bytes === 0 || bytes > partLimitBytes) throw new Error(`${name} violates the per-file byte limit`);
  parts.push({ filename: name, offset: totalBytes, bytes, sha256: digest.digest('hex') });
  totalBytes += bytes;
}
const actualSha256 = whole.digest('hex');
if (totalBytes !== expectedBytes) throw new Error(`partition total ${totalBytes} did not match ${expectedBytes}`);
for (let i = 0; i < parts.length - 1; i++) if (parts[i].bytes !== partLimitBytes) throw new Error(`${parts[i].filename} is not a full contiguous partition`);
const receipt = {
  version: 1,
  verification_method: 'stream SHA-256 over ordered unchanged source-byte partitions; no reconstructed full file written',
  expected_bytes: expectedBytes,
  actual_bytes: totalBytes,
  part_limit_bytes: partLimitBytes,
  baseline_registry_sha256: baselineShaArg.toLowerCase(),
  actual_sha256: actualSha256,
  baseline_registry_pin_status: actualSha256 === baselineShaArg.toLowerCase() ? 'verified' : 'mismatch',
  upstream_lfs_sha256: lfsShaArg.toLowerCase(),
  upstream_lfs_pin_status: actualSha256 === lfsShaArg.toLowerCase() ? 'verified' : 'mismatch',
  parts
};
const receiptPath = path.join(directory, 'verified-partition-receipt.json');
await writeFile(receiptPath, `${JSON.stringify(receipt, null, 2)}\n`, { flag: 'wx' });
process.stdout.write(`${JSON.stringify(receipt, null, 2)}\n`);
if (receipt.baseline_registry_pin_status !== 'verified' || receipt.upstream_lfs_pin_status !== 'verified') process.exitCode = 2;
