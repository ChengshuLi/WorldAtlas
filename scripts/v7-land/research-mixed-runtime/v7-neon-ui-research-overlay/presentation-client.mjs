// Browser-side integrity checks for a trusted, same-origin presentation service.
// The expected manifest hash and release ID must come from independently trusted
// release configuration, not from this response. No database credentials belong here.
const encoder = new TextEncoder();
const decoder = new TextDecoder('utf-8', {fatal: true});
const HEX = /^[0-9a-f]{64}$/;
const MAX_BYTES = 2 * 1024 * 1024;

function canonical(value) {
  if (value === null || typeof value === 'boolean' || typeof value === 'string') return JSON.stringify(value);
  if (typeof value === 'number') {
    if (!Number.isSafeInteger(value)) throw Error('Unsafe presentation number');
    return JSON.stringify(value);
  }
  if (Array.isArray(value)) return '[' + value.map(canonical).join(',') + ']';
  if (typeof value === 'object' && Object.getPrototypeOf(value) === Object.prototype) {
    const keys=Object.keys(value).sort();
    if (keys.some(k=>!/^[\x20-\x7e]*$/.test(k))) throw Error('Non-ASCII presentation object key');
    return '{' + keys.map(k=>JSON.stringify(k)+':'+canonical(value[k])).join(',') + '}';
  }
  throw Error('Unsupported presentation value');
}
async function sha256(bytes) {
  const digest=await crypto.subtle.digest('SHA-256',bytes);
  return [...new Uint8Array(digest)].map(x=>x.toString(16).padStart(2,'0')).join('');
}
function bytesOf(value) { return encoder.encode(canonical(value)+'\n'); }
async function readLimited(response,limit) {
  const length=response.headers.get('content-length');
  if (length!==null && (!/^\d+$/.test(length)||Number(length)>limit)) {
    try { if (response.body) response.body.cancel().catch(()=>{}); } catch {}
    throw Error('Presentation response too large');
  }
  if (!response.body) throw Error('Presentation response has no body');
  const reader=response.body.getReader(), chunks=[]; let total=0;
  try {
    for (;;) {
      const {done,value}=await reader.read(); if (done) break;
      total+=value.length; if (total>limit) throw Error('Presentation response too large');
      chunks.push(value);
    }
  } catch(e) { try { reader.cancel().catch(()=>{}); } catch {} throw e; }
  const raw=new Uint8Array(total); let offset=0;
  for (const chunk of chunks) {raw.set(chunk,offset);offset+=chunk.length;}
  return raw;
}

export async function loadPresentationEnvelope({endpoint, expectedManifestSha256, expectedReleaseId}) {
  if (!HEX.test(expectedManifestSha256||'') || typeof expectedReleaseId!=='string' || !expectedReleaseId) throw Error('Missing trusted presentation configuration');
  const url=new URL(endpoint,location.href);
  if (url.origin!==location.origin || !/^https?:$/.test(url.protocol)) throw Error('Presentation endpoint must be same-origin');
  const response=await fetch(url,{credentials:'same-origin',cache:'no-store',redirect:'error'});
  if (!response.ok) throw Error('Presentation service is unavailable');
  const raw=await readLimited(response,MAX_BYTES);
  const body=decoder.decode(raw), envelope=JSON.parse(body);
  // Requiring canonical transport rejects duplicate keys and alternate JSON encodings.
  if (body!==canonical(envelope)+'\n' || !envelope || Object.keys(envelope).sort().join(',')!=='manifest,records,schema' || envelope.schema!=='worldatlas-presentation-transport-v1') throw Error('Invalid presentation transport');
  const m=envelope.manifest;
  if (!m || m.schema!=='worldatlas-presentation-parity-manifest-v2' || m.release_id!==expectedReleaseId || await sha256(bytesOf(m))!==expectedManifestSha256) throw Error('Presentation manifest mismatch');
  const assets=m.assets;
  if (!assets || !['proposal','water_presentation','references','records'].every(k=>HEX.test(assets[k]||''))) throw Error('Invalid presentation asset pins');
  if (await sha256(bytesOf(envelope.records))!==assets.records) throw Error('Presentation records mismatch');
  return envelope;
}

export async function verifyPresentationSource(envelope,name,bytes) {
  if (!['proposal','water_presentation','references'].includes(name) || !(bytes instanceof ArrayBuffer) || await sha256(bytes)!==envelope?.manifest?.assets?.[name]) throw Error('Presentation source mismatch: '+name);
}

export async function readPinnedJSON(envelope,name,response) {
  if (!response.ok) throw Error('Presentation source unavailable: '+name);
  const raw=await readLimited(response,8*1024*1024);
  await verifyPresentationSource(envelope,name,raw.buffer);
  return JSON.parse(decoder.decode(raw));
}
