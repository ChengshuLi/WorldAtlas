#!/usr/bin/env node

// Stream a pinned, redistributable original into bounded contiguous raw-byte
// parts. Never write an oversized whole-file temporary to disk.
import { createHash } from 'node:crypto';
import { mkdir, open, writeFile } from 'node:fs/promises';
import path from 'node:path';

const [urlArg, outputArg, lengthArg, shaArg] = process.argv.slice(2);
if (!urlArg || !outputArg || !lengthArg || !shaArg) {
  throw new Error('usage: partition-immutable-source.mjs HTTPS_URL OUTPUT_DIR EXPECTED_BYTES EXPECTED_SHA256');
}
const url = new URL(urlArg);
if (url.protocol !== 'https:') throw new Error('source URL must use HTTPS');
const expectedBytes = Number(lengthArg);
const expectedSha = shaArg.toLowerCase();
const partLimit = 32 * 1024 * 1024;
if (!Number.isSafeInteger(expectedBytes) || expectedBytes <= 0) throw new Error('invalid expected byte length');
if (!/^[0-9a-f]{64}$/.test(expectedSha)) throw new Error('invalid expected SHA-256');

const output = path.resolve(outputArg);
await mkdir(output, { recursive: false });
const response = await fetch(url, { headers: { 'accept-encoding': 'identity', 'user-agent': 'WorldAtlas-source-evidence/1' }, redirect: 'follow' });
if (!response.ok || !response.body) throw new Error(`source response was HTTP ${response.status}`);
const headerBytes = response.headers.get('content-length');
if (headerBytes !== null && Number(headerBytes) !== expectedBytes) throw new Error(`Content-Length ${headerBytes} did not match expected ${expectedBytes}`);
const whole = createHash('sha256');
const parts = [];
let total = 0;
let partIndex = -1;
let partBytes = 0;
let partHash;
let handle;

async function beginPart() {
  partIndex += 1;
  partBytes = 0;
  partHash = createHash('sha256');
  const filename = `part-${String(partIndex + 1).padStart(2, '3')}.bin`;
  handle = await open(path.join(output, filename), 'wx');
  parts.push({ filename, offset: total, bytes: 0 });
}
async function endPart() {
  await handle.close();
  parts.at(-1).bytes = partBytes;
  parts.at(-1).sha256 = partHash.digest('hex');
}

const reader = response.body.getReader();
try {
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    let offset = 0;
    while (offset < value.length) {
      if (total >= expectedBytes) throw new Error('response exceeded pinned original length');
      if (partIndex < 0 || partBytes === partLimit) {
        if (handle) await endPart();
        await beginPart();
      }
      const count = Math.min(value.length - offset, partLimit - partBytes, expectedBytes - total);
      const bytes = value.subarray(offset, offset + count);
      await handle.write(bytes);
      whole.update(bytes);
      partHash.update(bytes);
      total += count;
      partBytes += count;
      offset += count;
    }
  }
  if (handle) await endPart();
} catch (error) {
  await reader.cancel().catch(() => {});
  if (handle) await handle.close().catch(() => {});
  throw error;
}

const actualSha = whole.digest('hex');
if (total !== expectedBytes) throw new Error(`received ${total} bytes; expected ${expectedBytes}`);
if (actualSha !== expectedSha) throw new Error(`whole-original SHA-256 ${actualSha} did not match pinned ${expectedSha}`);
const receipt = {
  version: 1,
  source_url: url.href,
  final_response_url: response.url,
  retrieved_at: new Date().toISOString(),
  http_status: response.status,
  content_length_header: headerBytes,
  content_encoding_header: response.headers.get('content-encoding'),
  expected_bytes: expectedBytes,
  actual_bytes: total,
  expected_sha256: expectedSha,
  actual_sha256: actualSha,
  partitioning: 'contiguous raw source-byte stream, no decode or transformation',
  part_limit_bytes: partLimit,
  parts
};
await writeFile(path.join(output, 'partition-receipt.json'), `${JSON.stringify(receipt, null, 2)}\n`, { flag: 'wx' });
process.stdout.write(`${JSON.stringify(receipt, null, 2)}\n`);
