import {effectiveFootprintValue,additiveReleaseFootprintDigest} from './effective-footprint.js';
import {sha256} from '@noble/hashes/sha2.js';

// Hash exactly the retained JSON.stringify(sorted [id, geometry] pairs) bytes,
// incrementally. This changes neither the original digest nor source authority;
// it avoids a second complete-world JSON string and UTF-8 buffer in the worker.
export async function nativeSourceDigest(features, {signal, onProgress = () => {}, additiveBaseReference} = {}) {
  if(additiveBaseReference&&features.some(feature=>Object.hasOwn(feature,'additiveFootprint'))){
    const base=await nativeSourceDigest(features.map(feature=>({id:feature.id,geometry:feature.geometry})),{signal,onProgress});
    if(base.sha256!==additiveBaseReference.footprints_sha256)throw Error('Complete loaded original base footprint differs from selected additive bank');
    return {...base,sha256:additiveReleaseFootprintDigest(additiveBaseReference,features),base_sha256:base.sha256,
      domain:features.some(feature=>feature?.additiveFootprint?.version===2)?'worldatlas-effective-native-footprints:v2':'worldatlas-effective-native-footprints:v1'};
  }
  const ordered = features.map(feature => [feature.id, Object.hasOwn(feature,'additiveFootprint') ? effectiveFootprintValue(feature) : feature.geometry])
    .sort((a, b) => a[0].localeCompare(b[0]));
  const hash = sha256.create(), encoder = new TextEncoder();
  let bytes = 2, largestFeatureBytes = 0;
  try {
    signal?.throwIfAborted(); hash.update(encoder.encode('['));
    for (let i = 0; i < ordered.length; i++) {
      signal?.throwIfAborted();
      if (i) {hash.update(encoder.encode(',')); bytes++;}
      const chunk = encoder.encode(JSON.stringify(ordered[i]));
      hash.update(chunk); bytes += chunk.length;
      largestFeatureBytes = Math.max(largestFeatureBytes, chunk.length);
      if (i % 256 === 255) {
        onProgress({phase: 'reference-digest', features: i + 1});
        await new Promise(resolve => setTimeout(resolve, 0));
      }
    }
    hash.update(encoder.encode(']')); signal?.throwIfAborted();
    const value = Array.from(hash.digest(), byte => byte.toString(16).padStart(2, '0')).join('');
    return {sha256: value, bytes, largestFeatureBytes};
  } finally {hash.destroy();}
}
