// Temporary, separately authorized read-only migration capability. Never writes
// database/object storage; absent or expired credentials leave the route closed.
const PREFIX = '/api/_migration/r2';
const encoder = new TextEncoder();
const json = (body, status = 200) => new Response(JSON.stringify(body), {
  status, headers: {'Content-Type': 'application/json', 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'},
});
async function matches(candidate, expected) {
  if (!candidate || candidate.length > 256 || !expected || expected.length < 32 || expected.length > 256) return false;
  const [a, b] = await Promise.all([candidate, expected].map(value => crypto.subtle.digest('SHA-256', encoder.encode(value))));
  const left = new Uint8Array(a), right = new Uint8Array(b);
  let difference = 0;
  for (let i = 0; i < left.length; i++) difference |= left[i] ^ right[i];
  return difference === 0;
}
const metadata = object => ({key: object.key, version: object.version, size: object.size,
  etag: object.etag, httpEtag: object.httpEtag, uploaded: object.uploaded,
  storageClass: object.storageClass,
  httpMetadata: object.httpMetadata ?? {}, customMetadata: object.customMetadata ?? {},
  checksums: object.checksums?.toJSON?.() ?? object.checksums ?? {}});
export async function migrationAuthorized(request, env) {
  const expiry = Date.parse(env.ATLAS_R2_EXPORT_EXPIRES_AT ?? '');
  const supplied = request.headers.get('Authorization')?.match(/^Bearer (.+)$/)?.[1];
  return Number.isFinite(expiry) && Date.now() < expiry && await matches(supplied, env.ATLAS_R2_EXPORT_TOKEN);
}
export function readOnlyR2Export(inner) {
  return {async fetch(request, env, context) {
    const url = new URL(request.url);
    if (url.pathname !== PREFIX && !url.pathname.startsWith(PREFIX + '/')) return inner.fetch(request, env, context);
    if (!await migrationAuthorized(request, env)) return json({error: 'Not found'}, 404);
    if (request.method !== 'GET') return json({error: 'Read only'}, 405);
    if (!env.BUCKET) return json({error: 'Storage unavailable'}, 503);
    try {
    if (url.pathname === PREFIX + '/inventory') {
      const cursor = url.searchParams.get('cursor') || undefined;
      if (cursor && cursor.length > 4096) return json({error: 'Invalid cursor'}, 400);
      const page = await env.BUCKET.list({limit: 500, cursor, include: ['httpMetadata', 'customMetadata']});
      return json({objects: page.objects.map(metadata), truncated: page.truncated, cursor: page.truncated ? page.cursor : null});
    }
    if (url.pathname === PREFIX + '/object') {
      const key = url.searchParams.get('key');
      if (!key || encoder.encode(key).length > 1024) return json({error: 'Invalid key'}, 400);
      const expectedEtag = request.headers.get('If-Match');
      const object = await env.BUCKET.get(key, expectedEtag ? {onlyIf: {etagMatches: expectedEtag.replace(/^"|"$/g, '')}} : undefined);
      if (!object) return json({error: 'Object not found'}, 404);
      if (!('body' in object)) return json({error: 'Object changed'}, 412);
      const headers = new Headers({'Cache-Control': 'no-store', 'Content-Type': 'application/octet-stream', 'Content-Length': String(object.size), 'X-Content-Type-Options': 'nosniff'});
      if (object.httpEtag) headers.set('ETag', object.httpEtag);
      return new Response(object.body, {headers});
    }
    return json({error: 'Not found'}, 404);
    } catch {
      return json({error: 'Storage unavailable'}, 503);
    }
  }};
}
