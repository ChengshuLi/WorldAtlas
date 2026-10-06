import {compileNativeLocationContext} from './native-location-context.js';
let current;
self.onmessage = async ({data}) => {
  if (data?.type !== 'compile-native-context' || !Number.isSafeInteger(data.revision) || data.revision < 1) {
    self.postMessage({revision: data?.revision, error: 'Invalid native context request'});
    return;
  }
  current?.abort();
  const controller = new AbortController(); current = controller;
  const started=performance.now();
  try {
    const result = await compileNativeLocationContext({...data.input, signal: controller.signal,
      onProgress: progress => self.postMessage({revision: data.revision, progress})});
    controller.signal.throwIfAborted();
    self.postMessage({revision: data.revision, compileMs: performance.now()-started, grid: result.grid, owners: result.context.owners,
      accounting: {...result.accounting, ownerMapping: undefined}}, [result.grid.rows.buffer, result.grid.runs.buffer]);
  } catch (error) {
    self.postMessage({revision: data.revision, error: error.message, errorName: error.name});
  } finally {if (current === controller) current = null;}
};
