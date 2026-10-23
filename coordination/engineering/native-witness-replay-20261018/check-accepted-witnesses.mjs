// Read-only numerical parity check; this cannot qualify a selected transition.
import fs from 'node:fs';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {repairComponentKey,nativeOnlyComponent} from '../../../src/native-grid.js';
import {valueSha} from '../selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';
const root=fileURLToPath(new URL('../../../',import.meta.url));
const demand=(ok,message)=>{if(!ok)throw Error(message);};
const sha=body=>createHash('sha256').update(body).digest('hex');
const reportPath=process.argv[2];
demand(typeof reportPath==='string','Supply the exact PR2459 geography-check.json');
const stat=fs.lstatSync(reportPath);
demand(stat.isFile()&&!stat.isSymbolicLink()&&stat.size===510244,'Expected exact ordinary report');
const reportBody=fs.readFileSync(reportPath),reportSha='6a8f4953e761ac16b07804daea2c24f833f45f3d650ed18d0c48a5b9f70c3eaa';
demand(sha(reportBody)===reportSha,'Accepted report bytes differ');
const oid='6fbe85e13cb45ab45714bf8c4aa0c27583221f20';
const body=execFileSync('git',['-C',root,'cat-file','blob',oid],{maxBuffer:57989594,env:{...process.env,GIT_NO_LAZY_FETCH:'1'}});
demand(body.length===57989593&&sha(body)==='2b0431686879ef2382c0901ba387273d49b89c4ad3270b70469b05cd9457e0df','Accepted ledger bytes differ');
const report=JSON.parse(reportBody).selected_native_report,ledger=JSON.parse(body);
const keys=new Set(report.repair_visibility.witnesses.map(repairComponentKey));
const components=ledger.rows.filter(row=>keys.has(repairComponentKey(row)));
demand(keys.size===565&&components.length===565,'Incomplete/duplicate accepted component join');
const changed=new Set(report.native_row_scope.changed_rows);
const witnesses=components.map(item=>{
 demand(nativeOnlyComponent(item,valueSha),'Expected accepted native component');
 const row=item.native_rows[0],run=row.runs[0];
 demand(changed.has(row.y),'First native row omitted from accepted changed-row scope');
 return {component_id:item.component_id,authority_sha256:item.authority_sha256,
  native_rows_sha256:valueSha(item.native_rows),x:run[0],y:row.y,previous_owner:0,candidate_owner:run[2]};
});
demand(valueSha(witnesses)===valueSha(report.repair_visibility.witnesses),'First-cell witnesses differ from accepted actual comparison');
console.log(JSON.stringify({accepted_report_sha256:reportSha,ledger_git_blob_oid:oid,
 compared_components:components.length,witnesses_sha256:valueSha(witnesses),equal:true,
 limit:'Exact accepted output parity only; no current source/owner-zero/checkpoint qualification.'}));
