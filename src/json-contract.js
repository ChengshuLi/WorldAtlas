/** Inspect descriptors before serialization: never execute hooks/getters or lose data. */
export function assertJSONData(value, {maxBytes = 16384, objectRequired = false} = {}) {
  if (objectRequired && (!value || typeof value !== 'object' || Array.isArray(value))) throw Error('Expected a JSON object');
  const inspect = (entry, ancestors = new Set(), depth = 0) => {
    if (entry === null || typeof entry === 'string' || typeof entry === 'boolean') return;
    if (typeof entry === 'number' && Number.isFinite(entry)) return;
    if (!entry || typeof entry !== 'object') throw Error('Only JSON data is supported');
    if (depth > 64 || ancestors.has(entry)) throw Error('Cyclic or excessive-depth JSON data');
    const array = Array.isArray(entry), prototype = Object.getPrototypeOf(entry);
    if (!array && prototype !== Object.prototype && prototype !== null
      || array && prototype !== Array.prototype) throw Error('Custom JSON prototypes are unsupported');
    const descriptors = Object.getOwnPropertyDescriptors(entry);
    const keys = Reflect.ownKeys(descriptors);
    if (keys.some(key => typeof key !== 'string')) throw Error('Symbol properties are not JSON data');
    if (array && keys.length !== entry.length + 1) throw Error('Sparse or decorated arrays are not JSON data');
    const next = new Set(ancestors); next.add(entry);
    for (const key of keys) {
      if (array && key === 'length') continue;
      const descriptor = descriptors[key];
      if (!Object.hasOwn(descriptor, 'value') || !descriptor.enumerable) throw Error('Accessors and hidden properties are not JSON data');
      if (array && (!/^(0|[1-9]\d*)$/.test(key) || Number(key) >= entry.length)) throw Error('Custom array properties are not JSON data');
      inspect(descriptor.value, next, depth + 1);
    }
  };
  inspect(value);
  if (new TextEncoder().encode(JSON.stringify(value)).length > maxBytes) throw Error(`JSON data exceeds ${maxBytes} bytes`);
  return value;
}
