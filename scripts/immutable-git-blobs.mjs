import {copyAPIFeatures} from './github-quota.mjs';
import {createHash} from 'node:crypto';
import {finiteBytes, immutableResponseBytes, LEGACY_FILE_BYTES} from './evidence-quality.mjs';

export const IMMUTABLE_CACHE_BYTES = 272 * 1024 * 1024;
export const IMMUTABLE_CACHE_ENTRIES = 512;

// Keep one execution's known immutable bytes. Mutable identities, trees,
// authority and checks always reach the underlying API again. This memory bound
// is independent of (and does not increase) any evidence-validator byte limit.
export function memoizeImmutableGitBlobs(api, {maxBytes = IMMUTABLE_CACHE_BYTES, maxEntries = IMMUTABLE_CACHE_ENTRIES} = {}) {
  if (!Number.isSafeInteger(maxBytes) || maxBytes < 0 || !Number.isSafeInteger(maxEntries) || maxEntries < 0) throw Error('Invalid immutable blob cache bounds');
  const cache = new Map(); let bytes = 0;
  const wrapped = async (route, method = 'GET', body, options) => {
    const match = /^\/repos\/[\w.-]+\/[\w.-]+\/git\/blobs\/([a-f0-9]{40})$/.exec(route);
    if (!match || method !== 'GET' || body !== undefined) return api(route, method, body, options);
    const expected = options?.expectedImmutableBytes;
    if (expected !== undefined) finiteBytes(expected, 'immutable blob size');
    if (cache.has(route)) {
      const value = cache.get(route);
      if (expected === undefined ? value.size > LEGACY_FILE_BYTES : value.size !== expected) throw Error('Immutable Git blob differs from exact tree size');
      return value;
    }
    const responseBound = immutableResponseBytes(expected ?? LEGACY_FILE_BYTES);
    const maxResponseBytes = options?.maxResponseBytes === undefined ? responseBound
      : Math.min(finiteBytes(options.maxResponseBytes, 'caller response budget'), responseBound);
    const blob = await api(route, method, body, {...options, maxResponseBytes});
    if (blob?.encoding !== 'base64' || blob.sha !== match[1] || !Number.isSafeInteger(blob.size) || blob.size < 0 ||
        (expected === undefined ? blob.size > LEGACY_FILE_BYTES : blob.size !== expected) || typeof blob.content !== 'string') throw Error('Incomplete or unsupported immutable Git blob');
    const encoded = blob.content.replace(/\s/g, '');
    if (encoded.length !== 4 * Math.ceil(blob.size / 3)) throw Error('Incomplete immutable Git blob encoding');
    const content = Buffer.from(encoded, 'base64');
    if (content.toString('base64') !== encoded) throw Error('Incomplete immutable Git blob encoding');
    const oid = createHash('sha1').update(`blob ${content.length}\0`).update(content).digest('hex');
    if (content.length !== blob.size || oid !== match[1]) throw Error('Immutable Git blob size/content does not match requested OID');
    const value = Object.freeze({sha: blob.sha, size: blob.size, encoding: 'base64', content: encoded});
    // Transient selector records still get complete authentication, but do not
    // enter any nested immutable cache. Previously cached required bytes remain
    // reusable; this hint changes neither authority nor HTTP accounting.
    // Never evict the useful large first scan to admit a small tail and then
    // repeat it on each authority pass. Overflow stays uncached and verified.
    if (options?.retainImmutableBlob !== false && cache.size < maxEntries && bytes + content.length <= maxBytes) {
      cache.set(route, value); bytes += content.length;
    }
    return value;
  };
  return copyAPIFeatures(wrapped,api);
}
