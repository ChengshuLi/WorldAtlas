// Scientific data preparation only; qualification remains the stock entry point.
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL, fileURLToPath} from 'node:url';
import {gunzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
const [root, inputCommit, output] = process.argv.slice(2);
const base = '21984e9ec4ec7370bc807e2da23cea2228747698';
const prefix = 'coordination/engineering/sierra-leone-original-repair-20261018/';
const need = (value, message) => { if (!value) throw Error(message); };
const sha = body => createHash('sha256').update(body).digest('hex');
need(/^[a-f0-9]{40}$/.test(inputCommit) && !fs.existsSync(output), 'Exact input commit and fresh output required');
const {pinReader} = await import(pathToFileURL(path.join(root, 'scripts/prepare-delivery-handoff.mjs')));
const reader = pinReader(root);
const pins = new Map();
function pin(name, commit = base) {
  const value = reader.pin(commit, name);
  pins.set(commit + ':' + name, value);
  return value;
}
function json(name, commit = base) {
  const value = pin(name, commit), raw = reader.read(value);
  if (!name.endsWith('.gz')) return JSON.parse(raw);
  const decoded = gunzipSync(raw);
  value.decoded_bytes = decoded.length;
  value.decoded_sha256 = sha(decoded);
  return JSON.parse(decoded);
}
need(reader.read(pin(prefix + 'method/prepare-native-config.mjs', inputCommit))
  .equals(fs.readFileSync(fileURLToPath(import.meta.url))), 'Preparation method drift');
const stages = json(prefix + 'source-stage-001/original-stage-inputs.json', inputCommit);
const members = json(prefix + 'source-stage-001/source-target-membership.json', inputCommit);
const foreign = json(prefix + 'source-review/foreign-bounds-001/complete-foreign-bounds.json', inputCommit);
const periodic = json(prefix + 'source-review/periodic-negatives-001/retained-periodic-negative-reconciliation.json', inputCommit);
const original = [30].flatMap(block =>
  json(prefix + 'original-intervals/block-' + String(block).padStart(3, '0') + '.json.gz', inputCommit));
need(stages.length === 11 && members.length === 11 && original.length === 1335
  && foreign.complete_foreign_features === 73549 && foreign.complete_foreign_families === 366
  && periodic.unresolved_foreign_bound_features === 0, 'Complete original scientific scope required');
const byOwner = new Map(), patchRows = new Map();
let cells = 0;
for (const [y, start, end, owners, sources, kind] of original) {
  need(owners.length === 1 && ['land','inland-water'].includes(kind), 'Original owner and class required');
  const owner = owners[0], rows = byOwner.get(owner) ?? new Map();
  const runs = rows.get(y) ?? [];
  runs.push([start, end, kind === 'land' ? 'mapped_land_support' : 'mapped_inland_water_support']);
  rows.set(y, runs); byOwner.set(owner, rows);
  const patch = patchRows.get(y) ?? []; patch.push([start, end, owner]); patchRows.set(y, patch);
  cells += end - start;
}
const merge = rows => {
  const result = [];
  for (const row of rows.toSorted((a,b) => a[0]-b[0] || a[1]-b[1])) {
    const prior = result.at(-1);
    need(!prior || prior[1] <= row[0], 'Overlapping original intervals');
    if (prior && prior[1] === row[0] && prior[2] === row[2]) prior[1] = row[1];
    else result.push([...row]);
  }
  return result;
};
need(cells === 3878 && byOwner.size === 11, 'Original denominator changed');
const patch = {rows: [...patchRows].sort(([a],[b]) => a-b).map(([y,runs]) => ({y,runs:merge(runs)}))};
const classRows = new Map([...byOwner].map(([owner, rows]) => [owner,
  [...rows].sort(([a],[b]) => a-b).map(([y,runs]) => ({y,runs:merge(runs)}))]));
const cataloguePath = 'coordination/engineering/original-geography-source-corpus-20261006/catalogue.json';
const catalogue = json(cataloguePath);
const family = catalogue.products.find(product => product.key === 'gb:SLE:ADM2');
need(family.feature_count === 14, 'Whole domestic original competitor family required');
const parts = family.parts.map(part => ({...pin(part.path),
  decoded_bytes:part.uncompressed_bytes, decoded_sha256:part.uncompressed_sha256}));
const physicalPath = prefix + 'physical-001/whole-target-support.json';
const physical = json(physicalPath, inputCommit);
const physicalPin = pins.get(inputCommit + ':' + physicalPath);
const physicalBySource = new Map(physical.results.map(result => [result.target,result]));
need(physicalBySource.size === 11, 'Complete whole-member physical output required');
const memberById = new Map(members.map(member => [member.source_id,member]));
const targets = stages.map(stage => {
  const member = memberById.get(stage.target), support = physicalBySource.get(stage.target)?.support;
  need(member && member.target_id === stage.selected.id && classRows.has(member.pixelIndex)
    && support, 'Complete original source/owner/physical record join required');
  // Keep each member's actual positive class operands, as in the retained
  // complete-member adapter. Empty water is not a positive polygon. The original
  // owner classRows, with all original source classes, remain unchanged.
  const classes = ['mapped_land_support'];
  if (support.mapped_inland_water_support?.coordinates?.length) classes.push('mapped_inland_water_support');
  return {id:stage.target, target_id:member.target_id, pixelIndex:member.pixelIndex,
    base_geometry:stage.selected.geometry, source_family:'gb:SLE:ADM2',
    source_receipt_sha256:physicalPin.sha256, coverage_classes:classes,
    coverage_rows:classRows.get(member.pixelIndex), territorial_exclusions:[]};
});
const world = pin('data/world-index.json');
const projectionPath = 'data/macro-foundation/world-review-projection.json';
const projection = json(projectionPath);
need(projection.current_pins.location_index_sha256 === world.sha256, 'Current canonical projection differs');
const cohortParts = [], cohortRows = [];
for (const name of projection.location_parts) {
  cohortRows.push(...json('data/' + name));
  cohortParts.push(pins.get(base + ':data/' + name));
}
need(cohortRows.length === 49625 && new Set(cohortRows.map(row => row.id)).size === 49625,
  'Complete world owner association inventory required');
const canonicalPaths = ['data/geography/part-22.json'];
const canonical = canonicalPaths.flatMap(name => json(name).features)
  .filter(feature => feature.properties.reference_owner === 'Sierra Leone');
const country = cohortRows.filter(row => row.owner === 'Sierra Leone');
need(canonical.length === 14 && country.length === canonical.length
  && canonical.every(feature => country.some(row => row.id === feature.id)), 'Complete Sierra_Leone country context required');
const config = {version:1, selector:{commit:base,path:'data/ownership-selection.json'},
  ...(foreign.whole_bounds_candidate_families.length ? {compact_territorial_exclusions:true,
    territorial_exclusion_families:foreign.whole_bounds_candidate_families} : {}),
  source_evidence:{version:1,kind:'source-target-native-evidence-v1',
    catalogue:pins.get(base + ':' + cataloguePath), families:[{source_id:'gb:SLE:ADM2',parts}],
    physical_evidence:physicalPin,
    physical_input:pin(prefix + 'source-stage-001/original-stage-inputs.json',inputCommit),
    physical_reproduction:pin('scripts/qualify-source-cohort.py'),
    source_membership:{index:world,lineage:pin('data/semantic-report.json'),
      parts:canonicalPaths.map(name => pins.get(base + ':' + name)),
      cohort_inventory:{index:pins.get(base + ':' + projectionPath),parts:cohortParts}},targets}};
fs.mkdirSync(output);
for (const [name,value] of Object.entries({'source-evidence-config.json':config,'native-requested-patch.json':patch}))
  fs.writeFileSync(path.join(output,name),JSON.stringify(value)+'\n',{flag:'wx'});
console.log(JSON.stringify({original_cells:cells,owners:byOwner.size,whole_members:targets.length,
  complete_domestic_features:14,foreign_negative_families:foreign.whole_bounds_candidate_families,
  complete_canonical_Sierra_Leone_owners:canonical.length,qualified_cells:0}));
