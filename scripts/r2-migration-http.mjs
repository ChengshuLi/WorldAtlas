// No credentials are written to receipts. Supply secrets through the caller's
// memory or stdin; endpoints refuse redirects rather than forward credentials.
export function httpBucket({url,token,headers = {}}, transport = fetch) {
  const base = new URL(url);
  if (base.protocol !== 'https:' || base.username || base.password || base.search || base.hash) throw Error('Expected credential-free HTTPS base URL');
  const request = (route, options={}) => transport(new URL('/api/_migration/r2/'+route,base), {
    ...options,redirect:'error',signal:AbortSignal.timeout(120000),
    headers:{...headers,Authorization:'Bearer '+token,...options.headers},
  });
  return {
    async list(cursor) {
      const response=await request('inventory'+(cursor?'?cursor='+encodeURIComponent(cursor):''));
      if(response.status!==200) throw Error('Inventory HTTP status '+response.status);
      let bytes=0;const chunks=[];
      for await(const chunk of response.body){bytes+=chunk.byteLength;if(bytes>8*1024**2)throw Error('Inventory response exceeds admitted page');chunks.push(Buffer.from(chunk));}
      return JSON.parse(Buffer.concat(chunks).toString('utf8'));
    },
    get(row) {return request('object?key='+encodeURIComponent(row.key),{headers:{'If-Match':row.httpEtag??'"'+row.etag+'"'}});},
    async createOnly(row,body,sha256) {
      const metadata=encodeURIComponent(JSON.stringify({httpMetadata:row.httpMetadata,customMetadata:row.customMetadata,storageClass:row.storageClass}));
      if(metadata.length>16384)throw Error('Object metadata exceeds destination header bound');
      const response=await request('object?key='+encodeURIComponent(row.key),{method:'PUT',body,
        headers:{'Content-Length':String(body.byteLength),'X-Migration-Sha256':sha256,'X-Migration-Metadata':metadata}});
      if(response.status!==201)throw Error('Create-only upload HTTP status '+response.status+'; verify destination before retry');
      await response.body?.cancel();
    },
  };
}
