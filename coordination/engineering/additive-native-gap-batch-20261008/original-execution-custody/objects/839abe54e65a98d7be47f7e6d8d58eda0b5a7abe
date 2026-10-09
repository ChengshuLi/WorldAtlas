// Versioned location ownership metadata. Legacy vintages retain their original
// method; a selected native reference requires matching source/release pins.
export const NATIVE_METHOD = 'native-linear-evenodd-first-owner-v1';
export const LATITUDE_DIGEST = '66db3d02ede56a75e9c58426ad1388552be3bf7e5e4477476f198983b7436d23';
const hash = value => /^[a-f0-9]{64}$/.test(value ?? '');
export function ownershipMetadata(manifest, {requireNative = false, expectedReference} = {}) {
  if (!manifest || (manifest.version !== 1 && manifest.version !== 2)) throw Error('Unknown ownership packing version');
  if (manifest.method !== undefined && manifest.method !== NATIVE_METHOD) throw Error('Unknown ownership coordinate method');
  const native = manifest.method === NATIVE_METHOD;
  if (expectedReference && !native) throw Error('Selected native reference cannot use legacy ownership');
  if (requireNative && !expectedReference) throw Error('Current location grid requires an independently selected reference release');
  if (requireNative && !native) throw Error('Current location grid requires prepared native ownership');
  const output = Object.fromEntries(['version','coordinateBits','size','runWords'].map(key => [key, manifest[key]]));
  if (native) {
    const latitude = manifest.native_latitudes;
    if (manifest.version !== 2 || manifest.size !== 262166 || manifest.coordinateBits !== 19 ||
        !latitude || latitude.root !== 'repository' || latitude.role !== 'immutable-normative-rule-input' ||
        latitude.path !== 'coordination/engineering/native-grid-fidelity-1010-20261005-local15/results-v1/native-row-latitudes.f64le.gz' ||
        !/^[a-f0-9]{40}$/.test(latitude.commit ?? '') || !hash(latitude.sha256) ||
        latitude.decoded_sha256 !== LATITUDE_DIGEST || latitude.decoded_bytes !== manifest.size * 8 ||
        !Number.isSafeInteger(latitude.bytes) || latitude.bytes < 1 || latitude.bytes > 32 * 1024 * 1024)
      throw Error('Native ownership rule input is missing or incompatible');
    if (!hash(manifest.footprints_sha256) || !hash(manifest.hierarchy_sha256) ||
        typeof manifest.geographic_release !== 'string' || !manifest.geographic_release.startsWith('geography:'))
      throw Error('Native ownership source/release pins are missing');
    if (expectedReference && (manifest.footprints_sha256 !== expectedReference.footprints_sha256 ||
        manifest.hierarchy_sha256 !== expectedReference.hierarchy_sha256 ||
        manifest.geographic_release !== expectedReference.id))
      throw Error('Native ownership differs from the selected reference release');
    output.footprints_sha256 = manifest.footprints_sha256;
    output.hierarchy_sha256 = manifest.hierarchy_sha256;
    output.geographic_release = manifest.geographic_release;
    if (manifest.reference_owner_sha256 !== undefined) {
      if (!hash(manifest.reference_owner_sha256)) throw Error('Invalid native reference owner mapping');
      output.reference_owner_sha256 = manifest.reference_owner_sha256;
    }
    output.method = NATIVE_METHOD;
    output.native_latitudes = {...latitude};
  }
  return output;
}
