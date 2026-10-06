import {nativeDisplayContext} from './native-location-context.js';
import {NATIVE_METHOD} from './ownership-method.js';
let revision = 0;

// The old displayed date remains coherent until its replacement grid is ready.
// Canceling a selection terminates its isolated worker, including native math.
export function prepareNativeLocationContext(input, {signal, onProgress = () => {},
  workerFactory = () => new Worker(new URL('./native-context-worker.js', import.meta.url), {type: 'module'})} = {}) {
  signal?.throwIfAborted();
  const context = nativeDisplayContext(input.referenceFeatures, input.features);
  const worker = workerFactory(), request = ++revision;
  return new Promise((resolve, reject) => {
    let settled = false;
    const finish = (error, value) => {
      if (settled) return;
      settled = true; signal?.removeEventListener('abort', abort); worker.terminate();
      if (error) reject(error); else resolve(value);
    };
    const abort = () => finish(signal.reason ?? new DOMException('Selection canceled', 'AbortError'));
    worker.onerror = event => finish(Error(event.message || 'Native context worker failed'));
    worker.onmessage = ({data}) => {
      if (data?.revision !== request || settled) return;
      if (data.progress) {try {onProgress(data.progress);} catch (error) {finish(error);} return;}
      if (data.error) {const error = Error(data.error); error.name = data.errorName || 'Error'; finish(error); return;}
      if (data.grid?.method !== NATIVE_METHOD || data.grid.version !== 2 || data.grid.size !== 262166 ||
        data.grid.coordinateBits !== 19 || !(data.grid.rows instanceof Uint32Array) ||
        data.grid.rows.length !== 524332 || !(data.grid.runs instanceof Uint32Array) || data.grid.runs.length % 2 ||
        !Array.isArray(data.owners) || data.owners.length !== context.owners.length ||
        data.owners.some((owner, i) => owner.id !== context.owners[i].id || owner.index !== context.owners[i].index ||
          owner.referenceIndex !== context.owners[i].referenceIndex)) {
        finish(Error('Native worker display identity mapping differs from selected context')); return;
      }
      finish(null, {...data, context});
    };
    signal?.addEventListener('abort', abort, {once: true});
    if (signal?.aborted) {abort(); return;}
    try {worker.postMessage({type: 'compile-native-context', revision: request, input});}
    catch (error) {finish(error);}
  });
}
