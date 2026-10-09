// A snapshot never establishes current authority. Every reuse requires a new
// authenticated conditional GET, and callers receive a freshly parsed value.
export function conditionalSnapshots({maxBytes = 64 * 1024 * 1024, maxEntries = 128} = {}) {
  if (!Number.isSafeInteger(maxBytes) || maxBytes < 0 || !Number.isSafeInteger(maxEntries) || maxEntries < 0)
    throw Error('Invalid HTTP snapshot bounds');
  const rows = new Map(); let bytes = 0;
  const tag = value => typeof value === 'string' && value.length <= 256 && /^(?:W\/)?"[\x21\x23-\x7e]*"$/.test(value);
  return {
    get(route) { return rows.get(route); },
    retain(route, etag, value) {
      const previous = rows.get(route);
      if (previous) { bytes -= previous.bytes; rows.delete(route); }
      if (!tag(etag)) return;
      const text = JSON.stringify(value), size = Buffer.byteLength(text);
      if (rows.size >= maxEntries || bytes + size > maxBytes) return;
      rows.set(route, Object.freeze({etag, text, bytes: size})); bytes += size;
    },
    revalidated(snapshot, etag) {
      if (!snapshot || (etag !== null && etag !== snapshot.etag)) throw Error('Unbound conditional GitHub response');
      return JSON.parse(snapshot.text);
    },
    invalidate(route) {
      const row = rows.get(route); if (row) { bytes -= row.bytes; rows.delete(route); }
    }
  };
}
