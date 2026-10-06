import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {rebindCoverageManifest} from '../scripts/rebind-coverage-manifest.mjs';
import {validateGeometryMigrations} from '../scripts/prepare-geographic-release.mjs';
import {footprintHash} from '../scripts/check-prepared.mjs';
const originalBytes = await fs.readFile('data/canonical-grid/manifest.json');
const selectedBytes = await fs.readFile('coordination/engineering/native-grid-candidate-1010-20261005-local16/candidate-v1/manifest.json');
const originalGrid = JSON.parse(originalBytes), selectedGrid = JSON.parse(selectedBytes);
const classification = JSON.parse(await fs.readFile('data/coverage-classification/manifest.json'));
const digest = bytes => createHash('sha256').update(bytes).digest('hex');
const context = {originalGrid, originalGridSha256: digest(originalBytes), selectedGrid,
  selectedGridSha256: digest(selectedBytes), release: {id: selectedGrid.geographic_release,
    footprints_sha256: selectedGrid.footprints_sha256, hierarchy_sha256: selectedGrid.hierarchy_sha256}};

test('native ownership binding retains all original physical bytes, sources, domain and uncertainties', () => {
  const before = JSON.stringify(classification), rebound = rebindCoverageManifest(classification, context);
  assert.equal(JSON.stringify(classification), before);
  assert.equal(rebound.canonical_grid_sha256, context.selectedGridSha256);
  const {ownership_binding, ...originalFields} = rebound;
  originalFields.canonical_grid_sha256 = classification.canonical_grid_sha256;
  assert.deepEqual(originalFields, classification);
  assert.equal(ownership_binding.original_canonical_grid_sha256, context.originalGridSha256);
  assert.equal(ownership_binding.selected_method, selectedGrid.method);
});

test('changed coordinate grid, sources, release or original ownership binding prohibit reuse', () => {
  for (const key of ['size', 'coordinateBits', 'footprints_sha256', 'hierarchy_sha256']) {
    const changed = {...selectedGrid, [key]: typeof selectedGrid[key] === 'number' ? selectedGrid[key] + 1 : '0'.repeat(64)};
    assert.throws(() => rebindCoverageManifest(classification, {...context, selectedGrid: changed}));
  }
  assert.throws(() => rebindCoverageManifest(classification, {...context, release: {...context.release, id: 'geography:other'}}));
  assert.throws(() => rebindCoverageManifest(classification, {...context, originalGridSha256: '0'.repeat(64)}));
  assert.throws(() => rebindCoverageManifest({...classification, sources: []}, context));
});

test('validated geometry-only successor preserves physical assets and records both associations', async () => {
  const feature = (id, left, right) => ({id,properties:{id,parent_id:'province'},
    geometry:{type:'Polygon',coordinates:[[[left,0],[right,0],[right,1],[left,1],[left,0]]]}});
  const before=[feature('a',0,1),feature('b',2,3)],after=[feature('a',0,1.25),before[1]];
  const oldHash=footprintHash(before),newHash=footprintHash(after);
  const predecessor={...context.release,footprints_sha256:oldHash};
  const successor={...predecessor,id:'geography:test-successor',footprints_sha256:newHash};
  const receipt={version:1,geometry_stage_validated:true,historical_claims_transferred:false,
    before_footprints_sha256:oldHash,after_footprints_sha256:newHash,
    changed_ids:['a'],removed_ids:[],added_ids:[],reused_ids:['b'],
    archives:[{id:'a',feature:before[0]}],
    relationships:[{kind:'source-backed-shared-seam-reference',before_ids:['a'],after_ids:['a'],history_transfer:false}],
    source_evidence:[{url:'https://example.com/synthetic-test-only',source_sha256:'1'.repeat(64)}]};
  await fs.mkdir('.cache',{recursive:true});
  const directory=await fs.mkdtemp('.cache/coverage-transition-test-');
  try {
    const raw=Buffer.from(JSON.stringify(receipt));
    successor.metadata={predecessor_release_id:predecessor.id,geometry_migration:{
      sha256:digest(raw),before_footprints_sha256:oldHash,after_footprints_sha256:newHash,history_transfer:false}};
    await fs.writeFile(directory+'/migration-receipt.json',raw);
    await fs.writeFile(directory+'/index.json',JSON.stringify({
      before_footprints_sha256:oldHash,after_footprints_sha256:newHash,history_transfer:false,
      files:{'migration-receipt.json':{sha256:digest(raw)}}}));
    const validate=()=>validateGeometryMigrations({features:after,baselineIds:['a','b'],
      baselineFootprints:oldHash,manifestFiles:[directory+'/index.json']});
    const migrationContext={...context,originalGrid:{...originalGrid,footprints_sha256:oldHash},
      selectedGrid:{...selectedGrid,footprints_sha256:newHash,geographic_release:successor.id},
      release:successor,predecessorRelease:predecessor,geometryValidation:validate()};
    const physical={...classification,footprints_sha256:oldHash};
    const rebound=rebindCoverageManifest(physical,migrationContext);
    const {ownership_binding,...restored}=rebound;
    restored.footprints_sha256=oldHash;restored.release_id=predecessor.id;
    restored.canonical_grid_sha256=physical.canonical_grid_sha256;
    assert.deepEqual(restored,physical); // Includes every asset digest, source and blocked tile.
    assert.equal(rebound.release_id,successor.id);
    assert.deepEqual(ownership_binding.geometry_migration.changed_ids,['a']);
    assert.equal(ownership_binding.geometry_migration.historical_claims_transferred,false);
    // A deserialized/self-authored receipt cannot stand in for reconstruction.
    assert.throws(()=>rebindCoverageManifest(physical,{...migrationContext,
      geometryValidation:structuredClone(migrationContext.geometryValidation)}),/complete geometry migration validation/);
    // Even a genuine result is unusable if its checked dispositions change later.
    const altered=validate();altered.changedIds.add('b');
    assert.throws(()=>rebindCoverageManifest(physical,{...migrationContext,geometryValidation:altered}),/unmodified/);
    assert.throws(()=>rebindCoverageManifest(physical,{...migrationContext,
      release:{...successor,metadata:{...successor.metadata,predecessor_release_id:'geography:wrong-predecessor'}}}),/retained-identity/);
    assert.throws(()=>rebindCoverageManifest(physical,{...migrationContext,
      selectedGrid:{...migrationContext.selectedGrid,size:selectedGrid.size+1}}));
    const corrupted=[after[0],feature('b',2,3.1)];
    assert.throws(()=>validateGeometryMigrations({features:corrupted,baselineIds:['a','b'],
      baselineFootprints:oldHash,manifestFiles:[directory+'/index.json']}),/unreceipted footprint mutation/);
  } finally { await fs.rm(directory,{recursive:true,force:true}); }
});
