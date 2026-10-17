/* Measure complete prior Argentina pointsets against every original native key.
 * Usage: node measure-prior-family-keys.mjs REPO EXACT_METHOD_COMMIT FRESH_OUTPUT
 * This produces applicability witnesses, not geography or source-fitness approval.
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { gunzipSync } from 'node:zlib';
const [repoArg, C, outputArg] = process.argv.slice(2);
const R = path.resolve(repoArg ?? ''), O = path.resolve(outputArg ?? '');
const H = 'd4968ddc37aa3aa6105e9610c9e6fadbb368ba14';
const F = '29500dfbc67532a3ef9e9f23ca76ebafed2670b2';
const P = 'coordination/engineering/argentina-repair-delivery-20261017';
const assert = (b, m) => { if (!b) throw Error(m); };
assert(process.argv.length === 5 && /^[a-f0-9]{40}$/.test(C), 'Exact arguments required');
function ordinaryAncestors(p) {
  for (let q = p; ; q = path.dirname(q)) {
    const s = fs.lstatSync(q, { throwIfNoEntry: false });
    assert(!s?.isSymbolicLink(), `Symlink refused: ${q}`);
    if (q === path.dirname(q)) break;
  }
}
ordinaryAncestors(R); ordinaryAncestors(O);
assert(fs.statSync(R).isDirectory() && fs.statSync(path.dirname(O)).isDirectory(), 'Ordinary existing roots required');
assert(!fs.lstatSync(O, { throwIfNoEntry: false }), 'Fresh output required');
const start = performance.now(), pins = new Map();
let inputBytes = 0;
const sha = b => createHash('sha256').update(b).digest('hex');
const git = (...args) => execFileSync('git', ['-c', 'protocol.allow=never', '-C', R, ...args], {
  maxBuffer: 64 * 1024 * 1024, timeout: 30000,
  env: { ...process.env, GIT_NO_LAZY_FETCH: '1', GIT_NO_REPLACE_OBJECTS: '1', GIT_TERMINAL_PROMPT: '0' },
});
function read(c, p, decompress = false) {
  assert(/^[a-f0-9]{40}$/.test(c) && !p.startsWith('/') && !p.split('/').some(x => ['', '.', '..'].includes(x)), 'Exact ordinary pin required');
  const row = git('ls-tree', '-z', c, '--', p).toString();
  const m = /^100644 blob ([a-f0-9]{40})\t([^\0]+)\0$/.exec(row);
  assert(m && m[2] === p, 'Ordinary complete blob required');
  const n = Number(git('cat-file', '-s', m[1]).toString());
  assert(n > 0 && n <= 64 * 1024 * 1024, 'Input resource bound');
  const b = git('cat-file', 'blob', m[1]);
  assert(b.length === n && createHash('sha1').update(Buffer.from(`blob ${n}\0`)).update(b).digest('hex') === m[1], 'Blob integrity');
  const pin = { commit: c, path: p, mode: '100644', git_blob_oid: m[1], bytes: n, sha256: sha(b) };
  const d = decompress ? gunzipSync(b, { maxOutputLength: 64 * 1024 * 1024 }) : b;
  if (decompress) Object.assign(pin, { decoded_bytes: d.length, decoded_sha256: sha(d) });
  if (!pins.has(`${c}:${p}`)) inputBytes += n + (decompress ? d.length : 0);
  pins.set(`${c}:${p}`, pin);
  assert(inputBytes <= 256 * 1024 * 1024 && performance.now() - start < 120000, 'Bounded whole-input read');
  return d;
}
assert(read(C, `${P}/probes/measure-prior-family-keys.mjs`).equals(fs.readFileSync(fileURLToPath(import.meta.url))), 'Executed method drift');
const code = read(H, 'src/native-grid.js');
assert(!/^import\s/m.test(code.toString()), 'Unexpected stock code import');
const { nativePolygonIntervals, witnessCellEffects } = await import('data:text/javascript;base64,' + code.toString('base64'));
const line = JSON.parse(read(H, 'coordination/engineering/global-current-cell-work-queue-20261014/lineage-summary.json'));
const lp = line.latitudes, latbuf = read(lp.commit, lp.path, true), actual = pins.get(`${lp.commit}:${lp.path}`);
assert(actual.bytes === lp.bytes && actual.sha256 === lp.sha256 && latbuf.length === lp.decoded_bytes && sha(latbuf) === lp.decoded_sha256, 'Latitude exact custody');
assert(latbuf.length % 8 === 0, 'Binary64 latitude body');
const size = latbuf.length / 8, latitudes = Float64Array.from({ length: size }, (_, i) => latbuf.readDoubleLE(i * 8));
const original = JSON.parse(read(F, `${P}/original-scope/original-intervals.json.gz`, true));
const byY = new Map(), keyInfo = new Map(), owners = new Set();
for (const [y, a, z, oo, ss, k] of original) {
  assert(oo.length === 1 && ['land', 'water'].includes(k) && z > a, 'Original row shape');
  const rr = byY.get(y) ?? []; rr.push([a, z, oo[0]]); byY.set(y, rr); owners.add(oo[0]);
  for (let x = a; x < z; x++) {
    const key = `${y}:${x}`; assert(!keyInfo.has(key), 'Duplicate original key');
    keyInfo.set(key, { y, x, pixelIndex: oo[0], physical_class: k });
  }
}
assert(original.length === 10702 && keyInfo.size === 28846 && owners.size === 115, 'Complete original denominator');
const requestedRows = [...byY].sort(([a], [b]) => a - b).map(([y, runs]) => ({ y, runs: runs.sort(([a], [b]) => a - b) }));
const features = JSON.parse(read(F, `${P}/source-review/prior-family-001/candidate-components.geojson`)).features;
const extraction = JSON.parse(read(F, `${P}/source-review/prior-family-001/extraction.json`));
assert(features.length === 7 && JSON.stringify(features.map(f => f.id)) === JSON.stringify(extraction.complete_component_ids), 'Complete seven-component family');
const preliminary = JSON.parse(read(F, `${P}/original-scope/preliminary-source-holds.json`));
const foreign = new Set(preliminary.foreign_keys.map(k => `${k.y}:${k.x}`));
const caba = new Set(preliminary.CABA_keys.map(k => `${k.y}:${k.x}`));
assert(foreign.size === 1025 && caba.size === 32 && ![...caba].some(k => foreign.has(k)), 'Preliminary exact reconciliation');
const results = [], prior = new Map();
for (const f of features) {
  const observation = witnessCellEffects(f.geometry, { size, latitudes, requestedRows, nativePolygonIntervals });
  const keys = [...new Set(observation.hits.map(k => `${k.y}:${k.x}`))];
  for (const key of keys) {
    assert(keyInfo.has(key), 'Witness outside original scope');
    const r = prior.get(key) ?? { ...keyInfo.get(key), component_ids: [] }; r.component_ids.push(f.id); prior.set(key, r);
  }
  results.push({ component_id: f.id, distinct_original_keys: keys.length, ...observation });
  assert(performance.now() - start < 120000, 'Bounded witness deadline');
}
const held = new Map();
function add(key, reason) { assert(keyInfo.has(key), 'Held key outside original'); const r = held.get(key) ?? { ...keyInfo.get(key), reasons: [] }; r.reasons.push(reason); held.set(key, r); }
for (const key of foreign) add(key, 'foreign-whole-original-contact');
for (const key of caba) add(key, 'unresolved-CABA-membership');
for (const key of prior.keys()) add(key, 'unresolved-seven-component-source-fitness');
const sorted = m => [...m.values()].sort((a, b) => a.y - b.y || a.x - b.x);
const classes = rows => rows.reduce((a, k) => ({ ...a, [k.physical_class]: (a[k.physical_class] ?? 0) + 1 }), {});
const result = {
  kind: 'exact-original-key-Argentina-seven-component-applicability', baseline: H, component_checkpoint: F,
  method: 'Authenticated stock witnessCellEffects/nativePolygonIntervals; exact rational native longitudes and pinned binary64 row latitudes; every complete original component against every original package key.',
  original_cells: keyInfo.size, original_intervals: original.length, original_subjects: owners.size, original_classes: classes([...keyInfo.values()]),
  complete_components: features.length, prior_family_original_cells: prior.size, prior_family_classes: classes([...prior.values()]),
  preliminary_foreign_cells: foreign.size, preliminary_CABA_cells: caba.size,
  prior_foreign_overlap: [...prior.keys()].filter(k => foreign.has(k)).length,
  prior_CABA_overlap: [...prior.keys()].filter(k => caba.has(k)).length,
  held_union_cells: held.size, held_union_classes: classes([...held.values()]), remaining_after_these_predicates: keyInfo.size - held.size,
  components: results, prior_family_keys: sorted(prior), held_union_keys: sorted(held),
  inputs: [...pins.values()], input_encoded_decoded_bytes: inputBytes,
  elapsed_seconds: (performance.now() - start) / 1000, max_rss_bytes_linux: process.resourceUsage().maxRSS * 1024,
  limits: ['This measures exact applicability of retained unresolved pointsets, not source fitness, physical/legal truth or native qualification.', 'Foreign contacts here remain the authenticated original complete-corpus census, not a fresh independent polygon screen.', 'Other historical identity, topology, source and physical obligations remain under review; this is not final qualified accounting.'],
};
const body = Buffer.from(JSON.stringify(result, null, 2) + '\n');
assert(body.length < 16 * 1024 * 1024, 'Measured output resource bound');
ordinaryAncestors(O); assert(!fs.lstatSync(O, { throwIfNoEntry: false }), 'Fresh output changed');
fs.mkdirSync(O); fs.writeFileSync(path.join(O, 'exact-prior-family-keys.json'), body, { flag: 'wx' });
console.log(JSON.stringify({ original_cells: result.original_cells, prior_family_cells: prior.size, prior_foreign_overlap: result.prior_foreign_overlap, prior_CABA_overlap: result.prior_CABA_overlap, held_union_cells: held.size, remaining: result.remaining_after_these_predicates, elapsed_seconds: result.elapsed_seconds, output_bytes: body.length, output_sha256: sha(body) }));
