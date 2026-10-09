// Finished metadata issuer: consumes qualified whole predecessors, no geometry kernel.
import assert from 'node:assert/strict';
import fs from 'node:fs';import path from 'node:path';import {createHash} from 'node:crypto';
import {admitPhase,authenticateAdmittedBody,readAdmittedBody} from './phase-admission.mjs';
import {continueNativeManifest} from './native-v9-manifest.mjs';
import {continuePixelAudit} from './pixel-audit-continuation.mjs';
import {composeNativeSelectionReceipt} from './native-selection-continuation.mjs';
const sha=raw=>createHash('sha256').update(raw).digest('hex');
export function issueV9Bindings(plan,destination){
 assert.equal(plan.kind,'qualified-native-v9-and-full-pixel-continuation');
 assert(path.isAbsolute(destination)&&!destination.split(path.sep).includes('..')&&destination.startsWith(plan.root+'/.cache/'));
 let absent=false;try{fs.lstatSync(destination)}catch(error){if(error.code!=='ENOENT')throw error;absent=true}assert(absent);
 for(let current=path.dirname(destination);;current=path.dirname(current)){assert(!fs.lstatSync(current).isSymbolicLink());if(current===path.dirname(current))break}
 const named=['oldNative','oldPixel','assetIndex','assetJoinReceipt','assetJoinTerminal','accounting','accountingTerminal','sourceAreas','sourceAreasTerminal','selectedProof','selectedTerminal','footprints','footprintsTerminal','releaseHeader','migrationReceipt','oldComparison','contextIndex','changedRows'];
 assert.equal(plan.sourcePairs.length,4);assert.deepEqual(plan.sourcePairs.map(pair=>pair.kind).sort(),['context','footprints','native_repack','selected_rows']);
 const expectedPairs={selected_rows:[1,2,'29b67f33c35b806e0ba4a3510dfcfc9e1c4a106a'],footprints:[1,2,'2295dcc279d963beb265b05a7909388bc10b2926'],context:[2,2,'b081aafb47a95ea931384d70d4353f024073de41'],native_repack:[4,4,'c7799a18f11df4b418bc801708c058d0db1b95ff']};
 for(const pair of plan.sourcePairs){assert.equal(pair.files.length,expectedPairs[pair.kind][0]);assert.equal(pair.terminals.length,expectedPairs[pair.kind][1]);}
 for(const [kind,pin]of [['selected_rows',plan.selectedProof],['footprints',plan.footprints],['context',plan.contextIndex]]){const pair=plan.sourcePairs.find(pair=>pair.kind===kind);assert(pair.files.some(file=>file.one.sha256===pin.sha256&&file.one.bytes===pin.bytes));}
 const distinct=new Map();for(const pin of [...named.map(name=>plan[name]),...plan.code,...plan.sourcePairs.flatMap(pair=>pair.files.flatMap(file=>[file.one,file.two]).concat(pair.terminals))]){const old=distinct.get(pin.path);if(old)assert.deepEqual(old,pin);else distinct.set(pin.path,pin);}const inputs=[...distinct.values()];
 const admission=admitPhase({inputs,runtime:plan.runtime,outputReserve:20*1024*1024,metadataBytes:1048576});
 for(const pin of [...inputs,plan.runtime])authenticateAdmittedBody(admission,pin.path);
 const read=name=>JSON.parse(readAdmittedBody(admission,plan[name].path));
 const sourcePairBindings={};for(const pair of plan.sourcePairs){for(const terminalPin of pair.terminals){const terminal=JSON.parse(readAdmittedBody(admission,terminalPin.path));assert.equal(terminal.head,expectedPairs[pair.kind][2]);assert.equal(terminal.qualified,true);assert.equal(terminal.exit_code,0);assert.equal(terminal.guard_reason,null);assert.deepEqual(terminal.owned_group_survivors,[]);}for(const file of pair.files){assert.equal(file.one.bytes,file.two.bytes);assert.equal(file.one.sha256,file.two.sha256);assert(readAdmittedBody(admission,file.one.path).equals(readAdmittedBody(admission,file.two.path)));}sourcePairBindings[pair.kind]={qualified_runs:2,whole_equal:true,proof_sha256:sha(Buffer.from(JSON.stringify(pair)))};}
 for(const name of ['assetJoinTerminal','accountingTerminal','sourceAreasTerminal','selectedTerminal','footprintsTerminal']){const terminal=read(name);assert.equal(terminal.qualified,true);assert.equal(terminal.exit_code,0);assert.equal(terminal.guard_reason,null);assert.deepEqual(terminal.owned_group_survivors,[])}
 const oldNative=read('oldNative'),oldPixel=read('oldPixel'),index=read('assetIndex'),joined=read('assetJoinReceipt'),header=read('releaseHeader'),migration=read('migrationReceipt');
 assert.equal(index.version,1);assert.equal(index.issue,1295);assert.equal(index.kind,'ordered-exact-original-byte-fragments');assert.equal(index.files.length,56);assert.equal(index.whole_bytes,47604645);
 assert.equal(joined.index_sha256,plan.assetIndex.sha256);assert.equal(joined.whole_sha256,index.whole_sha256);assert.equal(joined.all_original_compressed_file_inverses,true);
 assert.equal(header.release.id,plan.releaseId);assert.equal(migration.issue,1520);assert.deepEqual(migration.changed_ids,['atlas:physical:CAN-15:NWT','atlas:physical:CAN-25:NUN']);assert.equal(migration.reused_ids.length,49623);assert.deepEqual(migration.removed_ids,[]);assert.deepEqual(migration.added_ids,[]);assert.equal(migration.history_transfer,'none');
 assert.equal(header.migration_receipt_sha256,plan.migrationReceipt.sha256);assert.deepEqual(header.release.metadata.geometry_migration,{commit:'9b212c585583dc218a961b4c7ee1056a64b54726',path:'coordination/engineering/arctic-three-retained-land-fit-repair-native-20261008/migration-receipt.json',sha256:plan.migrationReceipt.sha256,before_footprints_sha256:migration.before_footprints_sha256,after_footprints_sha256:migration.after_footprints_sha256,history_transfer:'none'});
 let native=continueNativeManifest(oldNative,{originalSha:plan.oldNative.sha256,replacements:plan.replacements,selectedProof:read('selectedProof'),footprints:read('footprints'),releaseId:plan.releaseId});
 assert.equal(plan.nativeManifestPath,'coordination/engineering/arctic-three-retained-land-fit-repair-native-20261008/native-v9/manifest.json');
 assert.equal(plan.assetIndexPublicationPath,'coordination/engineering/arctic-three-retained-land-fit-repair-native-20261008/native-v9/assets-bank/index.json');
 const files=new Map(index.files.map(file=>[file.path,file]));assert.equal(files.size,56);
 for(const part of native.parts){const file=files.get(part.path);assert(file);assert.equal(file.mode,'100644');assert.equal(file.bytes,part.bytes);assert.equal(file.sha256,part.sha256)}
 native={...native,native_asset_transport:{version:1,kind:index.kind,index:{path:plan.assetIndexPublicationPath,bytes:plan.assetIndex.bytes,sha256:plan.assetIndex.sha256},logical_assets:56,original_compressed_bytes:index.whole_bytes}};
 const nativeRaw=Buffer.from(JSON.stringify(native)+'\n');
 const pixel=continuePixelAudit(oldPixel,read('accounting'),read('sourceAreas'),{nativeManifest:{path:plan.nativeManifestPath,sha256:sha(nativeRaw)},releaseId:plan.releaseId,originalAuditSha:plan.oldPixel.sha256});
 const pixelRaw=Buffer.from(JSON.stringify(pixel)+'\n');
 const contextIndexRaw=readAdmittedBody(admission,plan.contextIndex.path);const selection=composeNativeSelectionReceipt({original:read('oldComparison'),originalComparisonPin:plan.oldComparison,manifestRaw:nativeRaw,manifest:native,contextIndexRaw,contextIndex:JSON.parse(contextIndexRaw),selectedPin:plan.selectedProof,changedRowsPin:plan.changedRows,footprintsPin:plan.footprints,assetIndex:index,sourcePairBindings});const selectionRaw=Buffer.from(JSON.stringify(selection)+'\n');
 const reportRaw=Buffer.from(JSON.stringify({issue:1520,kind:plan.kind,source_head:plan.head,complete_phase_bytes:admission.bytes,descriptors:admission.descriptors,native_manifest_sha256:sha(nativeRaw),pixel_audit_sha256:sha(pixelRaw),native_selection_receipt_sha256:sha(selectionRaw),asset_index_sha256:plan.assetIndex.sha256,locations:49625,unchanged_complete_records:49623,added_native_cells:141,old_urls_preserved_in_source:true,normal_fresh_output_old_url_availability_verified:false,normal_caller_qualified:false,activated:false})+'\n');
 assert(nativeRaw.length+pixelRaw.length+selectionRaw.length+reportRaw.length<=admission.outputReserve);
 for(const pin of [...inputs,plan.runtime])authenticateAdmittedBody(admission,pin.path);
 fs.mkdirSync(destination);for(const [name,raw]of [['manifest.json',nativeRaw],['pixel-audit.json',pixelRaw],['native-selection-receipt.json',selectionRaw],['v9-bindings.json',reportRaw]])fs.writeFileSync(path.join(destination,name),raw,{flag:'wx',mode:0o644});
 return JSON.parse(reportRaw);
}
