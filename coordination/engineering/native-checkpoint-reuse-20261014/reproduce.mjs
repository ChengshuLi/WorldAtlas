import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {ImmutableReader} from '../../../scripts/check-effective-geographic-regression.mjs';
import {acquireAcceptedCheckpoint,releaseAcceptedCheckpoint} from '../../../scripts/accepted-selected-checkpoint.mjs';
import {qualifyAcceptedCheckpoint,qualifyTransition,releaseCheckpoint} from '../../../coordination/engineering/selected-geography-effective-prevention-20261009/selected-checkpoint.mjs';
import {compareSelectedCheckpointNative} from '../../../scripts/selected-checkpoint-native.mjs';
const root=fileURLToPath(new URL('../../../',import.meta.url));
if(process.argv.length!==3)throw Error('Supply one fresh output JSON path');
const output=path.resolve(process.argv[2]);
if(fs.realpathSync(path.dirname(output))!==path.dirname(output)||fs.lstatSync(output,{throwIfNoEntry:false}))
 throw Error('Output must have ordinary existing parents and must not already exist');
const git=(...args)=>execFileSync('git',['-C',root,...args],{maxBuffer:64*1024**2});
const baseline='3eaa41fcd21ca07c00d7b13bf3674ce14fae6efe',candidate='73d26bff6cf5ae195f80bdf3f63927483b6e10bd';
const locator=JSON.parse(git('show',candidate+':data/selected-checkpoint.json'));
const token=execFileSync('gh',['auth','token'],{encoding:'utf8',stdio:['ignore','pipe','pipe']}).trim();
const allowance={phaseBytes:1024**3,rssBytes:1024**3};
let transport=0,handle,state;
const start=Date.now();
try{
 const acquired=await acquireAcceptedCheckpoint({repo:'ChengshuLi/WorldAtlas',locator:locator.acceptance,token,
  admit:bytes=>{if(bytes>256*1024**2)throw Error('Transport exceeds current reserve');transport=Math.max(transport,bytes);},
  retainedArchive:()=>git('show',candidate+':'+locator.retained_artifact.path)});
 if(!acquired.available)throw Error(acquired.reason);handle=acquired.handle;
 console.log(JSON.stringify({phase:'authenticated-original-acceptance',seconds:(Date.now()-start)/1000,transport}));
 const before=new ImmutableReader(root,baseline,{allowance});
 const after=new ImmutableReader(root,candidate,{allowance,budget:before.budget});
 const budget={shared:before.budget,carriedBytes:transport+7*4*1024**2};
 const qualified=await qualifyAcceptedCheckpoint({reader:before,acceptedHandle:handle,budget});
 if(!qualified.available)throw Error(qualified.reason);state=qualified.state;
 console.log(JSON.stringify({phase:'qualified-accepted-baseline',seconds:(Date.now()-start)/1000,additions:state.additions.length}));
 const transition=qualifyTransition({state,reader:after,budget});
 if(!transition.available)throw Error(transition.reason);
 const native=await compareSelectedCheckpointNative({transition,budget});
 if(native.status!=='no-new-native-loss')throw Error('Native regression');
 const nativeRows=transition.candidate.additions.filter(row=>row.representation==='native-cells');
 const nativeCells=nativeRows.reduce((n,row)=>n+row.native_cells,0);
 if(nativeCells!==13963)throw Error('Wrong native-only repair scope');
 const warm=qualifyTransition({state:transition.candidate,reader:after,budget});
 if(!warm.available)throw Error(warm.reason);
 const warmNative=await compareSelectedCheckpointNative({transition:warm,budget});
 if(warmNative.status!=='no-new-native-loss'||warm.changedIds.length||warm.changedNativeRows.length)throw Error('Warm reuse changed');
 const report={executing_commit:git('rev-parse','HEAD').toString().trim(),baseline,candidate,
  accepted_execution:state.accepted_execution,source_target_cells:nativeCells,source_target_components:nativeRows.length,
  cumulative_cells:transition.candidate.patch.rows.reduce((n,row)=>n+row.runs.reduce((m,r)=>m+r[1]-r[0],0),0),
  native,warm_native:warmNative,elapsed_seconds:(Date.now()-start)/1000,max_rss_bytes:process.resourceUsage().maxRSS*1024};
 fs.writeFileSync(output,JSON.stringify(report,null,2)+'\n',{flag:'wx'});
 console.log(JSON.stringify({phase:'complete',source_target_cells:nativeCells,affected_rows:native.affected_rows,witnesses:native.repair_visibility.witnesses.length,elapsed_seconds:report.elapsed_seconds,max_rss_bytes:report.max_rss_bytes}));
}finally{if(state)releaseCheckpoint(state);if(handle)releaseAcceptedCheckpoint(handle);}
