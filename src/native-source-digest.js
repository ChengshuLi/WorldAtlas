import {sha256} from '@noble/hashes/sha2.js';

// Hash exactly the retained JSON.stringify(sorted [id, geometry] pairs) bytes,
// incrementally. This changes neither the original digest nor source authority;
// it avoids a second complete-world JSON string and UTF-8 buffer in the worker.
export async function nativeSourceDigest(features, {signal, onProgress = () => {}} = {}) {
  const ordered = features.map(feature => [feature.id, feature.geometry])
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
