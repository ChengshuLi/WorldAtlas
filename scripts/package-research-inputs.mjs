import path from 'node:path';
import {createHash} from 'node:crypto';

// The opt-out is valid only for the reviewed build reader graph. A new/changed
// reader can introduce dependencies outside these manifests: fail full until
// its input behavior is reviewed and these immutable Git blob pins refreshed.
export const BUILD_MODULE_PINS = Object.freeze({
  "attribute-records.mjs": "4e2f50a9035223395975f2638e4b887f20ef38e4",
  "data/observation-registry-history/base-v1.json": "91c6e99190a1a90be820a5b3ca8dd5acd8e9fb00",
  "data/ownership-history/algorithms/exact/ellipsoidal_area.py": "518dcaada9e94907d7d886636dcbf928bd0788fa",
  "data/ownership-history/algorithms/exact/majority.py": "859b8e877f3a4199b848fbcf0949d9c3c10d8422",
  "data/ownership-history/algorithms/exact/prepare-ownership.py": "93d7a5fc759fe854521bdecc0b74188a78a9f2c2",
  "data/ownership-history/algorithms/incremental/e08d67bc39bde0e1-b33afcb77b20715f/prepare-ownership-incremental.py": "281a45a3f71c6fedf9e9f371a62345533fee8604",
  "data/ownership-history/algorithms/incremental/f44affea3bf822e7-b33afcb77b20715f/prepare-ownership-incremental.py": "281a45a3f71c6fedf9e9f371a62345533fee8604",
  "data/ownership-history/algorithms/incremental/prepare-ownership-incremental.py": "cc42970d339ea9a12e8f042c3e46509b8ec453cf",
  "data/ownership-history/algorithms/majority-refinement.py": "6d79206e9122fb3f2f0ffe961a4bc57c894d5b07",
  "data/ownership-history/algorithms/majority.py": "5d889e48489c17a709fd73d747d38dfac1d70d85",
  "data/ownership-history/algorithms/prepare-ownership.py": "3e164fd585b94844876acc8877cb5d23db511c0f",
  "data/ownership-history/algorithms/refine-ownership-threshold.py": "f6fdaf11c87c27ed2c87b054432bcb7eb2c9cfae",
  "database.mjs": "6a845801f610773d32ecd54aebd902c0ffc2ddd6",
  "derived.mjs": "ca020163448baf702d6ececcf49731b6478cc1a7",
  "geographic-archive.mjs": "314623f84b480a9d72cce1f3c602bb19fcadb2fc",
  "hierarchy.mjs": "7ee42a92ca78d0895eef93ed9b1dbe3d543e1b05",
  "hosted/cloudflare-access.js": "2dab92ce276915d394f81c0a70a2465285e49408",
  "hosted/cloudflare-worker.js": "b418d3e92768328efa2ad935002c18f4789a7db2",
  "hosted/content-backend.js": "895aac57446a1aad1bac3ffd048986f9ffd56b7d",
  "hosted/footprint-versions.js": "1c448a1ec037c79d958f7588f9b6b2dd97b87439",
  "hosted/geographic-releases.js": "dddb27a2463b4924092a390344fedec23862c8cd",
  "hosted/map-snapshot-postgres.js": "39fce10c4d1438aed8048dc2a1e42f7c4c1d0830",
  "hosted/map-snapshots.js": "5ba4733b5fb379822ff72ec53c78ea18547f68e2",
  "hosted/membership-storage-pins.js": "9cbce929388d4364d8e7c99dfa4a89f9d0cabeb8",
  "hosted/membership-storage-profile.js": "261d83a0f1635dba1d85c1377e41a194532b0ec0",
  "hosted/postgres-adapter.js": "f1a4207e9ba58410e9f3583ec60a44a940044771",
  "hosted/records-constraints.sql": "5155a63c45dd57fb22edadebe299af0234ac314d",
  "hosted/records.js": "015a8700651bf9f10be7e857411b08470f22f1da",
  "hosted/research-catalog.js": "4823938276b908825e11224182d8a299bddb384b",
  "hosted/retirement-constraints.sql": "edcb39436ff0dbfea9d3432152ef1acef8fbf08b",
  "hosted/storage-export-compat.js": "d7bc30c249cb5a0badd9d3e9e71a4431e5eed481",
  "hosted/storage-export-v2-contract.js": "77a4cfa6b0e0ea490cbc6980555783875367aed1",
  "hosted/storage-export-v2.js": "4180e33a2e7f6936e2cabb20268c374c0aae7098",
  "hosted/storage-export-v3-contract.js": "29bac7ab3c77427a1b86d30af0884c6b4c19a094",
  "hosted/storage-export-v3.js": "d7ed2cfda2df3a297b0d27a2e1ee5248516958d7",
  "hosted/storage-export-v4-contract.js": "185b09259c9c59b1b0c5d6a06c9b5f09b6d8c68f",
  "hosted/storage-export-v4.js": "69e190f0a9dca10ac1e71ed799f2f3eceb4dae5b",
  "hosted/storage-export.js": "250fa44906a44f4a2fdd6bc4b6ea8130c6218ad8",
  "hosted/temporal-geography.js": "99d477986a03701a1028dc2bea6a43e542b11068",
  "hosted/typed-observations.js": "6e62e301dec9cd8923f38066bdab9fc6c1131cb6",
  "hosted/typed-storage-compat.js": "613d14e40e72d068564ece4693523c5e133274ee",
  "hosted/worker.js": "ebb39634667a283db1449656017b1159fcaccc99",
  "index.html": "cedbda0a24f82993747397459fb953787016f89e",
  "package-lock.json": "cecbf0fde86f4b18a8f0f402a138bbdaf13ff2a5",
  "package.json": "921e4aab3a224c561800498c79f20d62b3769a89",
  "prepared-evidence.mjs": "67e6bcbd12f13bf131d1af9e28d5430ea5b1db50",
  "reference-archive.mjs": "2dac27d0f10eb4a3a25529d33f2dc0c29be7e2c0",
  "reference.mjs": "ef221489dea59894c8358b1376fe5830f3e2fc2a",
  "requirements.txt": "a51a1fe5d483cadf8c6bbfb8390f8c5bbad61f9c",
  "scripts/boundary-version-hash.py": "8dda3929ca08464172513ceba73a4e03885ba926",
  "scripts/build-hosted.mjs": "247fbd3a0161e3167848506e73f4555eefd79218",
  "scripts/build-static.mjs": "acafda278cec70f4adf200e811a23449a4341e83",
  "scripts/check-prepared.mjs": "238d7a7526a4fc6e2b2e55ff8a56916e57ea1938",
  "scripts/compile-hosted-migrations.mjs": "beabb64e646128a5d622d2226bc41ae124a6ef9b",
  "scripts/deployment-budget.mjs": "ebf89b2696126d50ee6f84e70a1d2dca96f9cd14",
  "scripts/package-ownership-history.mjs": "df472db64f0258c2d864cbd8e8b4eb943c905a15",
  "scripts/package-reference-bundle.mjs": "094dd21be93b679b13c2dda2913ce2666b42aaa2",
  "scripts/package-startup-ownership.mjs": "875f1c609a3e9b4546262f30949825e32e9d0b45",
  "scripts/prepare-evidence-bundle.mjs": "88a1fbf21581d6902c2e94f5fa558b84d66a318c",
  "scripts/read-geographic-release-manifest.mjs": "740284b35c0eef1d4b001d648fedbe138cd23de9",
  "src/attributes.js": "aa11e038189270aed132e1d1a206fcf84ef6bac2",
  "src/category-palette.js": "fb814163ba0aab841a0affd1a47f5539a964566b",
  "src/category-presentation.js": "c6878c27faa3fdf047d19bdf366a4c09e036e696",
  "src/color-perception.js": "467f5f8b2b8e5b3a3289a8221e68ad6f2ec2f7f2",
  "src/coverage-scope.js": "fbeb41fd03e8a33545d11fb27e58402cda29d1f9",
  "src/coverage.js": "f6803211b648ff1cf314e65844cc900ca0a6dccf",
  "src/data-client.js": "135f3190e2684192b214995ce0c7532651a8170e",
  "src/derived-records.js": "2d64349a3ad705d8498632afc9e3d02e4d3e8554",
  "src/environment-classifications.js": "1bc6cfa8165b144cacfc6de73d552990d7e64d80",
  "src/evidence-priority.js": "6ea549085e326f00fa1ccb89d32d568d0a2dabde",
  "src/geometry.js": "366c32ad43f9829b26463ff7b6ab838d2a210c64",
  "src/hierarchy.js": "3407175d6cc69b8f99e3da03b3aa75c88525e262",
  "src/hosted-temporal-client.js": "5e4e237ab673803c6f65a6571dfc885aa213924a",
  "src/hosted-temporal-geography.js": "e6306b0b3f711564c8d638e1f0ac476e4b74c513",
  "src/import-records.js": "02969206410bce43f2275d7fd2604932d1de1440",
  "src/json-contract.js": "6cb81b458242f33fa6915b77d7c8c29f2b41f085",
  "src/main.js": "61029d50d4b4e0d4eecf3f99f9d4770402c4d83c",
  "src/map-snapshot-format.js": "687e2327c37c43c2d32a82f51ceedf219c53c0e7",
  "src/model.js": "b742ff4778deb48200007150c77b1f533f8bec41",
  "src/observation-modules.js": "7b629c55e59f5bb9901677307ddaef1d0befd52a",
  "src/observation-registry.js": "424c23eadc4e38d4a2fde66e5f4099ba775d2c9b",
  "src/ownership-assets.js": "c47225977f102a7fa07ca5dc81e24868be821cda",
  "src/ownership-codec.js": "03eacc9bcb1bff03723a93c248ea6de5f2fed5e4",
  "src/pixel-canvas-layer.js": "088b635c2e43cd1828dd0a27e9196d130fd5469c",
  "src/pixel-gpu-worker.js": "bd3eb36d143330d2b4c44338813c5455512b2423",
  "src/pixel-gpu.js": "824e1e113f6758673e212d99f9e0eb101a554227",
  "src/pixel-grid.js": "5900a0f4f7aa3500c6836d8b6e7468b9cc42e6a0",
  "src/pixel-layer.js": "16a19a4d83ba315289d69b4a0f49c72a44412559",
  "src/pixel-metadata.js": "d7c94a791d4ea7f12e28960e506b1ccb4163ff98",
  "src/pixel-ownership.js": "de88d87bea5ddca72c5816b1356ab18b9795f985",
  "src/pixel-worker.js": "997db165b61cb8fa8388512272a540fc994ee5e1",
  "src/prepared-evidence.js": "30b219d288d09c2f6bb866477788119476fbb989",
  "src/reference-bundle.js": "6855bd8725b48e36fdec66c5d479b0956ed6900f",
  "src/reference-context.js": "d4a9ef87915a19114175c54b3456c11e8ecf5bc7",
  "src/reference-records.js": "2130e7a42ac5d3fc7754320ac6ff5792e0d13ba0",
  "src/regional-import-gate.js": "b6eabfb3da75ad8d0aa3ff6a5c7a0493773f0ead",
  "src/runtime-ownership.js": "e4dc53b6a509b2ac0a83d900e36aa5d8ea363b26",
  "src/source-policy-corrections.js": "37d8f0e82b50bfd5c6df03da0b4cf009f450df1b",
  "src/style.css": "b6b8ab9c6edbf5b3bd093f505c4dea6be0e89c9c",
  "src/temporal.js": "2fe09b9dca486de9e79b6a6f13e35359e56dc56d",
  "src/typed-client.js": "4547ef490ba2c37555f3ea95640a449e0fde7dbb",
  "src/typed-derivations.js": "979ddde9b36d4c382e31a624b64e4c055887a287",
  "src/typed-observations.js": "df6744823835e1a12e30021d44d197c0f641ec82",
  "src/typed-snapshot.js": "c903360938a1680a2483a9fc0a3fd85c6e221e0a",
  "temporal.mjs": "b25a3e69b3fb0c27935d86885daf46afddb2555c",
  "topology.mjs": "ca38f621899047c9b7422bd55f62f26c3b1046ec"
});

export function researchPath(file) {
  return typeof file === 'string' && !file.includes('\\') && !/[\x00-\x1f\x7f]/.test(file) &&
    !file.split('/').some(part => !part || part === '.' || part === '..') &&
    /^(?:data\/regional-review|research\/(?:geography|campaigns))\/[a-z0-9][a-z0-9-]{0,63}\/.+/.test(file);
}

// Cross-directory references used by the committed static/database builders.
// Ordinary producer parts stay under their producer directory. Scan their
// manifests too, so relative traversal cannot conceal a research dependency.
// New build consumers must update this inventory before opting research out.
const manifests = [
  ['data/granularity-audit.json', 'data'], ['data/world-index.json', 'data'],
  ['data/world-review.json', 'data'], ['data/hierarchy-report.json', 'data'],
  ['data/macro-foundation/world-review-projection.json', 'data'],
  ['data/source-quality-reviews/index.json', 'data'],
  ['data/geographic-repair-evidence/index.json', 'data/geographic-repair-evidence'],
  ['data/canonical-grid/manifest.json', 'data/canonical-grid'],
  ...['ownership-history', 'ownership-runtime', 'reference-attributes', 'cliopatria'].map(name => [`data/${name}/index.json`, `data/${name}`]),
  ...['dated-reference-names', 'demographic-evidence', 'population-ghsl'].flatMap(name =>
    ['index.json', 'proof.json', 'revalidation.json'].map(file => [`data/${name}/${file}`, `data/${name}`])),
];
const required = new Set(['data/granularity-audit.json', 'data/world-index.json', 'data/world-review.json', 'data/hierarchy-report.json', 'data/ownership-history/index.json', 'data/reference-attributes/index.json', 'data/ownership-runtime/index.json']);

/** Read only immutable base blobs; missing/capped/malformed evidence throws. */
export async function packageResearchInputs({route, base, api}) {
  const tree = await api(`${route}/git/trees/${base}?recursive=1`);
  if (tree?.truncated !== false || !Array.isArray(tree.tree)) throw Error('Incomplete package input tree');
  const entries = new Map();
  for (const entry of tree.tree) {
    if (typeof entry.path !== 'string' || entries.has(entry.path)) throw Error('Invalid package input tree');
    entries.set(entry.path, entry);
  }
  for (const entry of tree.tree) {
    if (entry.path.startsWith('data/') && (entry.type !== 'tree' && (entry.type !== 'blob' || !['100644', '100755'].includes(entry.mode)))) throw Error('Nonordinary data input tree entry');
    if (/^(?:vite\.config\.(?:js|mjs|cjs|ts|mts|cts)|postcss\.config\.[^/]+|\.postcssrc[^/]*|tsconfig[^/]*\.json)$/.test(entry.path) && !Object.hasOwn(BUILD_MODULE_PINS, entry.path)) throw Error('Unreviewed build configuration');
    if (entry.type !== 'tree' && (/^(?:src|hosted|public)\//.test(entry.path) || (/^data\/ownership-history\/.+\.py$/.test(entry.path) || entry.path.startsWith('data/ownership-history/algorithms/'))) && !Object.hasOwn(BUILD_MODULE_PINS, entry.path)) throw Error(`Unreviewed package source: ${entry.path}`);
  }
  for (const [file, sha] of Object.entries(BUILD_MODULE_PINS)) {
    const entry = entries.get(file);
    if (entry?.type !== 'blob' || entry.mode !== '100644' || entry.sha !== sha) throw Error(`Unreviewed package input reader: ${file}`);
  }
  for (const file of required) if (!entries.has(file)) throw Error(`Package input manifest unavailable: ${file}`);
  const inputs = new Set();
  const reads = new Map();
  async function read(file) {
    if (reads.has(file)) return reads.get(file);
    const operation = (async () => {
      const entry = entries.get(file);
      if (entry?.type !== 'blob' || entry.mode !== '100644' || !/^[a-f0-9]{40}$/.test(entry.sha ?? '') ||
          !Number.isSafeInteger(entry.size) || entry.size > 32 * 1024 * 1024) throw Error(`Invalid package input manifest: ${file}`);
      const blob = await api(`${route}/git/blobs/${entry.sha}`);
      if (blob?.sha !== entry.sha || blob.encoding !== 'base64' || typeof blob.content !== 'string' || blob.size !== entry.size) throw Error('Invalid package input blob');
      const raw = Buffer.from(blob.content, 'base64');
      const sha = createHash('sha1').update(`blob ${raw.length}\0`).update(raw).digest('hex');
      if (raw.length !== entry.size || sha !== entry.sha) throw Error('Package input blob hash mismatch');
      inputs.add(file);
      const value = JSON.parse(raw);
      if (!value || typeof value !== 'object' || Array.isArray(value)) throw Error('Invalid package input manifest object');
      if (file === 'data/world-index.json' && (!Array.isArray(value.parts) || value.parts.some(part => typeof part !== 'string'))) throw Error('Invalid world input inventory');
      if (file === 'data/granularity-audit.json' && (!value.input_sha256 || typeof value.input_sha256 !== 'object' || Array.isArray(value.input_sha256))) throw Error('Invalid geography audit input inventory');
      for (const key of ['location_parts', 'change_parts']) if (value[key] !== undefined && (!Array.isArray(value[key]) || value[key].some(part => typeof part !== 'string'))) throw Error('Invalid copied package input inventory');
      return value;
    })();
    reads.set(file, operation);
    return operation;
  }
  function collect(value, root) {
    if (typeof value === 'string') {
      // Inspect every string/key, rather than assuming only one schema's path
      // fields. URLs/prose cannot match the normalized research namespaces.
      if (/^file:/i.test(value.trim().replace(/[\t\r\n]/g, ''))) throw Error('External file URL in package input manifest');
      {
        const clean = value.trim().replace(/[\t\r\n]/g, '');
        const variants = [value, clean];
        // URL-based committed readers decode escaped file names. Inspect the
        // decoded form too; literal fs/path readers still use the first form.
        try { variants.push(decodeURIComponent(value), decodeURIComponent(clean)); } catch { /* prose may contain literal percent signs */ }
        for (const variant of variants) {
          const file = path.posix.normalize(path.posix.join(root, variant.replaceAll('\\', '/')));
          if (researchPath(file)) inputs.add(file);
        }
      }
    } else if (Array.isArray(value)) value.forEach(row => collect(row, root));
    else if (value && typeof value === 'object') for (const [key, row] of Object.entries(value)) {
      collect(key, root); collect(row, root);
    }
  }
  await Promise.all(manifests.filter(([file]) => entries.has(file)).map(async ([file, root]) => collect(await read(file), root)));
  const ownership = await read('data/ownership-history/index.json');
  for (const algorithms of [ownership.execution_algorithms, ownership.initial_execution?.algorithms]) {
    if (!Array.isArray(algorithms)) throw Error('Incomplete executed ownership reader inventory');
    for (const algorithm of algorithms) {
      if (typeof algorithm?.path !== 'string' || algorithm.path.includes('\\') || algorithm.path.split('/').some(part => !part || part === '.' || part === '..') ||
          !/^[a-f0-9]{64}$/.test(algorithm.sha256 ?? '') || !Object.hasOwn(BUILD_MODULE_PINS, `data/ownership-history/${algorithm.path}`)) throw Error('Unreviewed executed ownership reader');
    }
  }
  const indexFile = 'data/source-quality-reviews/index.json';
  if (entries.has(indexFile)) {
    const index = await read(indexFile);
    if (!Array.isArray(index.parts) || index.parts.length > 256) throw Error('Invalid source-review input inventory');
    await Promise.all(index.parts.map(async part => {
      if (typeof part.path !== 'string' || !/^[\w./-]+\.json$/.test(part.path) || part.path.split('/').some(p => !p || p === '.' || p === '..')) throw Error('Invalid source-review input path');
      const file = `data/${part.path}`;
      inputs.add(file);
      collect(await read(file), 'data');
    }));
  }
  return inputs;
}

export function researchPacket(file) {
  return researchPath(file) ? file.match(/^(?:data\/regional-review|research\/(?:geography|campaigns))\/[a-z0-9][a-z0-9-]{0,63}\//)[0] : null;
}
