// Verify these two source corrections using the production migration gate.
import fs from 'node:fs';import path from 'node:path';import {gunzipSync} from 'node:zlib';
import {fileURLToPath} from 'node:url';
import {footprintHash} from '../../../../scripts/check-prepared.mjs';
import {validateGeometryMigrations} from '../../../../scripts/prepare-geographic-release.mjs';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../../../..');
const stage=path.resolve(process.argv[2]);
const read=file=>JSON.parse(file.endsWith('.gz')?gunzipSync(fs.readFileSync(file)):fs.readFileSync(file));
const baseline=read(path.join(root,'data/world-index.json')).parts.flatMap(p=>read(path.join(root,'data',p)).features);
const patch=read(path.join(stage,'candidate-patch.json.gz'));
const replacements=new Map(patch.existing_location_updates.map(f=>[f.id,f]));
const next=baseline.map(f=>replacements.get(f.id)??f);
const verified=validateGeometryMigrations({features:next,baselineIds:baseline.map(f=>f.id),
 baselineFootprints:footprintHash(baseline),manifestFiles:[path.join(stage,'index.json')],
 units:read(path.join(root,'data/hierarchy.json'))});
if(verified.changedIds.size!==2||verified.retiredIds.size||verified.addedIds.size)
 throw Error('Unexpected identity changes');
console.log(JSON.stringify({production_migration_gate_passed:true,changed_ids:[...verified.changedIds],
 baseline_locations:verified.baselineFeatures.length,history_transfer:false}));
