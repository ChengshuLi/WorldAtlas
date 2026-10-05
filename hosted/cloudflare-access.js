import {createRemoteJWKSet, jwtVerify} from 'jose';

const keysets = new Map();
function remoteKeys(issuer) {
  if (!keysets.has(issuer)) keysets.set(issuer, createRemoteJWKSet(new URL(`${issuer}/cdn-cgi/access/certs`)));
  return keysets.get(issuer);
}

/** Private by default; explicit public mode permits reads only. */
export function protectedWorker(inner, {keys = remoteKeys} = {}) {
  return {
    async fetch(request, env, ctx) {
      if (env.ATLAS_PUBLIC_READ_ONLY === '1') {
        if (!['GET', 'HEAD', 'OPTIONS'].includes(request.method)) {
          return new Response('Historical storage is read-only', {status: 503, headers: {'Cache-Control': 'no-store'}});
        }
        return inner.fetch(request, {...env, ATLAS_READ_ONLY: '1'}, ctx);
      }
      const domain = env.ATLAS_ACCESS_TEAM_DOMAIN;
      const audience = env.ATLAS_ACCESS_AUD;
      const deny = status => new Response(status === 503 ? 'Private access is not configured' : 'Authentication required', {
        status, headers: {'Cache-Control': 'no-store', 'Content-Type': 'text/plain; charset=utf-8'},
      });
      if (typeof domain !== 'string' || !/^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.cloudflareaccess\.com$/.test(domain) ||
          typeof audience !== 'string' || !audience.trim()) return deny(503);
      const token = request.headers.get('Cf-Access-Jwt-Assertion');
      if (!token) return deny(403);
      const issuer = `https://${domain}`;
      try {
        await jwtVerify(token, keys(issuer), {
          issuer, audience, algorithms: ['RS256'], requiredClaims: ['exp', 'iat', 'sub'],
        });
      } catch {
        return deny(403);
      }
      // A new deployment stays read-only unless an explicit publisher cutover enables writes.
      if (env.ATLAS_READ_ONLY !== '0' && !['GET', 'HEAD', 'OPTIONS'].includes(request.method)) {
        return new Response('Historical storage is read-only during migration', {
          status: 503, headers: {'Cache-Control': 'no-store'},
        });
      }
      return inner.fetch(request, env, ctx);
    },
  };
}
