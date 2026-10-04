import {loadPinnedTransport} from './reference-bundle.js';

export async function loadTemporalBundle(proof, release, fetcher = fetch) {
  if (!Number.isSafeInteger(proof?.entities) || proof.entities < 0 ||
      !Number.isSafeInteger(proof.history) || proof.history < 0) throw Error('Invalid temporal bundle roster');
  const bundle = await loadPinnedTransport(proof, release?.footprints_sha256,
    'geography/startup-temporal.json.gz', fetcher, release?.hierarchy_sha256 ?? null);
  if (bundle.version !== 1 || bundle.footprints_sha256 !== release.footprints_sha256 ||
      bundle.hierarchy_sha256 !== release.hierarchy_sha256 ||
      !Array.isArray(bundle.entities) || bundle.entities.length !== proof.entities ||
      !Array.isArray(bundle.history) || bundle.history.length !== proof.history) throw Error('Temporal bundle roster mismatch');
  return {entities: bundle.entities, history: bundle.history};
}
