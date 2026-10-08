import {createHash} from 'node:crypto';

// Explicit operational limits, independent of the premerge evidence limits.
// Bodies are streamed for verification; only a missing object is buffered.
export const limits = Object.freeze({objects: 20000, pages: 200, totalBytes: 1024 ** 3, objectBytes: 32 * 1024 ** 2, metadataBytes:32*1024**2});
export const canonical = value => JSON.stringify(normalize(value));
function normalize(value) {
  if (Array.isArray(value)) return value.map(normalize);
  if (value && typeof value === 'object') return Object.fromEntries(Object.keys(value).sort().map(key => [key, normalize(value[key])]));
  return value;
}
export async function inventory(list, bounds = limits) {
  const objects = [], keys = new Set(), cursors = new Set();
  let cursor, bytes = 0, metadataBytes=0;
  for (let pageNumber = 0; pageNumber < bounds.pages; pageNumber++) {
    const page = await list(cursor);
    if (!Array.isArray(page.objects) || typeof page.truncated !== 'boolean') throw Error('Invalid inventory page');
    for (const row of page.objects) {
      if (typeof row.key !== 'string' || !row.key || Buffer.byteLength(row.key) > 1024 || keys.has(row.key)) throw Error('Invalid or duplicate object key');
      if (!Number.isSafeInteger(row.size) || row.size < 0 || row.size > bounds.objectBytes) throw Error('Object size outside admitted bounds');
      if (!row.httpMetadata || !row.customMetadata || typeof row.httpMetadata!=='object' || typeof row.customMetadata!=='object' || Array.isArray(row.httpMetadata) || Array.isArray(row.customMetadata) || typeof row.etag !== 'string' || !['Standard','InfrequentAccess'].includes(row.storageClass??'Standard')) throw Error('Missing or unsupported inventory metadata');
      metadataBytes+=Buffer.byteLength(JSON.stringify(row));
      if(metadataBytes>(bounds.metadataBytes??limits.metadataBytes))throw Error('Inventory metadata exceeds admitted bounds');
      keys.add(row.key); bytes += row.size; objects.push(row);
      if (objects.length > bounds.objects || bytes > bounds.totalBytes) throw Error('Inventory exceeds admitted bounds');
    }
    if (!page.truncated) {
      if (page.cursor != null) throw Error('Unexpected final cursor');
      return {objects: objects.sort((a,b)=>a.key < b.key ? -1 : a.key > b.key ? 1 : 0), bytes};
    }
    if (typeof page.cursor !== 'string' || !page.cursor || cursors.has(page.cursor)) throw Error('Missing or repeated inventory cursor');
    cursors.add(page.cursor); cursor = page.cursor;
  }
  throw Error('Inventory page bound exceeded');
}
export async function readObject(response, row, retain = false) {
  if (response.status !== 200 || !response.body) throw Error('Object read failed: ' + response.status);
  const hash = createHash('sha256'), chunks = [];
  let bytes = 0;
  const reader = response.body.getReader();
  try {
    while (true) {
      const {done,value} = await reader.read();
      if (done) break;
      bytes += value.byteLength;
      if (bytes > row.size || bytes > limits.objectBytes) throw Error('Object body exceeds admitted size');
      hash.update(value);
      if (retain) chunks.push(Buffer.from(value));
    }
  } finally { await reader.cancel().catch(()=>{}); reader.releaseLock(); }
  if (bytes !== row.size) throw Error('Object body is incomplete');
  return {bytes, sha256: hash.digest('hex'), ...(retain ? {body: Buffer.concat(chunks, bytes)} : {})};
}
export function assertStable(before, after) {
  if (canonical(before) !== canonical(after)) throw Error('Storage inventory changed during reconciliation');
}
function metadataPreserved(original, target) {
  return (original.storageClass??'Standard')===(target.storageClass??'Standard') && ['httpMetadata','customMetadata'].every(kind=>Object.entries(original[kind]).every(([key,value])=>canonical(value)===canonical(target[kind][key])));
}
// Adapters must pin reads to listed ETags and implement an atomic create-only
// put. No delete or overwrite callback exists in this interface.
export async function reconcile({source, destination, copy = false, requiredSourceKeys = [], onVerified = async()=>{}}) {
  const initialSource = await inventory(source.list), initialDestination = await inventory(destination.list);
  if (!initialSource.objects.length) throw Error('Empty original inventory cannot establish migration');
  const sourceKeys=new Set(initialSource.objects.map(row=>row.key));
  if (requiredSourceKeys.some(key=>!sourceKeys.has(key))) throw Error('Required independent original object missing from inventory');
  assertStable(initialSource, await inventory(source.list));
  const targets = new Map(initialDestination.objects.map(row => [row.key,row]));
  const proofs = [], missing = [];
  // Validate every existing collision before the first possible write.
  for (const row of initialSource.objects) {
    const target = targets.get(row.key);
    const original = await readObject(await source.get(row), row);
    if (/^media\/[a-f0-9]{64}$/.test(row.key) && row.key.slice(6) !== original.sha256) throw Error('Source content-addressed key disagrees with bytes');
    if (target) {
      const restored = await readObject(await destination.get(target), target);
      if (original.bytes !== restored.bytes || original.sha256 !== restored.sha256) throw Error('Conflicting destination bytes: ' + row.key);
      if (!metadataPreserved(row,target)) throw Error('Conflicting destination metadata: ' + row.key);
      proofs.push({key: row.key, disposition: 'existing', bytes: original.bytes, sha256: original.sha256,
        source_metadata: row, destination_metadata: target, metadata_preserved:true,
        metadata_equal: canonical(row.httpMetadata) === canonical(target.httpMetadata) && canonical(row.customMetadata) === canonical(target.customMetadata)});
      await onVerified(proofs.at(-1));
    } else {
      // Keep only descriptors in this first phase; reread missing bodies after
      // complete collision verification and a fresh stable source inventory.
      missing.push({row, sha256: original.sha256});
    }
  }
  assertStable(initialSource, await inventory(source.list));
  assertStable(initialDestination, await inventory(destination.list));
  if (copy) for (const {row,sha256} of missing) {
    const original = await readObject(await source.get(row), row, true);
    if (original.sha256 !== sha256) throw Error('Missing source object changed');
    await destination.createOnly(row, original.body, sha256);
    const after = await inventory(destination.list), target = after.objects.find(value=>value.key===row.key);
    if (!target) throw Error('New object absent from readback inventory');
    const restored = await readObject(await destination.get(target), target);
    if (restored.bytes !== original.bytes || restored.sha256 !== sha256) throw Error('Transferred bytes failed verification');
    if (!metadataPreserved(row,target) || canonical(row.httpMetadata) !== canonical(target.httpMetadata) || canonical(row.customMetadata) !== canonical(target.customMetadata)) throw Error('Transferred metadata failed verification');
    proofs.push({key: row.key, disposition: 'transferred', bytes: original.bytes, sha256,
      source_metadata: row, destination_metadata: target, metadata_equal: true, metadata_preserved:true});
    await onVerified(proofs.at(-1));
  }
  assertStable(initialSource, await inventory(source.list));
  const finalDestination = await inventory(destination.list);
  for (const row of initialDestination.objects) {
    const final = finalDestination.objects.find(value=>value.key===row.key);
    if (canonical(row) !== canonical(final)) throw Error('Existing destination object changed');
  }
  if (copy && (proofs.length !== initialSource.objects.length || new Set(proofs.map(row=>row.key)).size !== sourceKeys.size || proofs.some(row=>!sourceKeys.has(row.key)))) throw Error('Incomplete source/proof coverage');
  for (const proof of proofs) {
    const final=finalDestination.objects.find(row=>row.key===proof.key);
    if (!final || canonical(final)!==canonical(proof.destination_metadata)) throw Error('Verified destination object changed or disappeared');
    if (proof.disposition==='transferred') {
      const finalBytes=await readObject(await destination.get(final),final);
      if(finalBytes.sha256!==proof.sha256)throw Error('Final transferred object failed byte verification');
    }
  }
  return {version:1, mode:copy?'copy':'verify', source:initialSource, destination_before:initialDestination,
    destination_after:finalDestination, missing:copy?[]:missing.map(value=>({key:value.row.key,sha256:value.sha256})),
    proofs:proofs.sort((a,b)=>a.key < b.key ? -1 : a.key > b.key ? 1 : 0),
    original_preserved:true, destination_existing_preserved:true, database_access:false};
}
