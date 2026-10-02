import fs from 'node:fs';
import {fileURLToPath} from 'node:url';
export function assertResearchImportsReady(gate){
 if(gate?.version!==1||gate.ready_for_location_attributes!==true||gate.semantic_complete!==true||!gate.approved_release?.release_id||!gate.approved_release?.hierarchy_sha256||!gate.approved_release?.footprints_sha256||!gate.approval_evidence)throw Error('Research imports are paused pending complete worldwide hierarchy approval (GitHub issue #7). Continue source-only research/staging; dry-run is available.');
 return gate.approved_release;
}
export function readResearchImportGate(){return JSON.parse(fs.readFileSync(fileURLToPath(new URL('../data/research-geography-gate.json',import.meta.url)),'utf8'));}
export function assertResearchBundleApproved(gate,geography){
 const approved=assertResearchImportsReady(gate);
 if((geography?.id??geography?.release_id)!==approved.release_id||geography.hierarchy_sha256!==approved.hierarchy_sha256||geography.footprints_sha256!==approved.footprints_sha256)throw Error('Research bundle does not match the worldwide-approved geographic release; preserve it and request engineering revalidation');
 return approved;
}
