import {createHash} from 'node:crypto';

export const IMMUTABLE_CACHE_BYTES = 272 * 1024 * 1024;
export const IMMUTABLE_CACHE_ENTRIES = 512;

// Keep one execution's known immutable bytes. Mutable identities, trees,
// authority and checks always reach the underlying API again. This memory bound
// is independent of (and does not increase) any evidence-validator byte limit.
export function memoizeImmutableGitBlobs(api, {maxBytes = IMMUTABLE_CACHE_BYTES, maxEntries = IMMUTABLE_CACHE_ENTRIES} = {}) {
  if (!Number.isSafeInteger(maxBytes) || maxBytes < 0 || !Number.isSafeInteger(maxEntries) || maxEntries < 0) throw Error('Invalid immutable blob cache bounds');
  const cache = new Map(); let bytes = 0;
  return async (route, method = 'GET', body) => {
    const match = /^\/repos\/[\w.-]+\/[\w.-]+\/git\/blobs\/([a-f0-9]{40})$/.exec(route);
    if (!match || method !== 'GET' || body !== undefined) return api(route, method, body);
    if (cache.has(route)) return cache.get(route);
    const blob = await api(route, method, body);
    if (blob?.encoding !== 'base64' || blob.sha !== match[1] || !Number.isSafeInteger(blob.size) || blob.size < 0 ||
        blob.size > 32 * 1024 * 1024 || typeof blob.content !== 'string') throw Error('Incomplete or unsupported immutable Git blob');
    const encoded = blob.content.replace(/\s/g, '');
    if (encoded.length !== 4 * Math.ceil(blob.size / 3)) throw Error('Incomplete immutable Git blob encoding');
    const content = Buffer.from(encoded, 'base64');
    if (content.toString('base64') !== encoded) throw Error('Incomplete immutable Git blob encoding');
    const oid = createHash('sha1').update(`blob ${content.length}\0`).update(content).digest('hex');
    if (content.length !== blob.size || oid !== match[1]) throw Error('Immutable Git blob size/content does not match requested OID');
    const value = Object.freeze({sha: blob.sha, size: blob.size, encoding: 'base64', content: encoded});
    // Never evict the useful large first scan to admit a small tail and then
    // repeat it on each authority pass. Overflow stays uncached and verified.
    if (cache.size < maxEntries && bytes + content.length <= maxBytes) {
      cache.set(route, value); bytes += content.length;
    }
    return value;
  };
}
