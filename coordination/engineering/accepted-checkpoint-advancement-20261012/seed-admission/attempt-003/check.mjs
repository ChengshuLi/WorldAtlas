import fs from 'node:fs';
import {execFileSync} from 'node:child_process';
import assert from 'node:assert/strict';
import {ImmutableReader,NativeAssetImage,selectedBootstrap,processingAllowance} from '../../scripts/check-effective-geographic-regression.mjs';
import {qualifyCheckpoint,releaseCheckpoint} from '../../coordination/engineering/selected-geography-effective-prevention-20261009/selected-checkpoint.mjs';
import {JOINT_CODE} from '../../coordination/engineering/selected-geography-effective-prevention-20261009/selected-joint-entry.mjs';
import {valueBytes} from '../../coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';
const repo=process.cwd(), baseline='04cfa575c98915fa50cc9ef17e1d00ca1579b3d5';
const trusted=execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim();
const output=new URL('./result.json',import.meta.url);
const catalogue=JSON.parse(fs.readFileSync('coordination/engineering/selected-checkpoint-reuse-20261012/accepted-checkpoints.json'));
const root=catalogue.checkpoints.find(x=>x.id==='accepted-1790-clean004-current-aus');
const allowed=new Set([...JSON.parse(fs.readFileSync('.checkpoint-integration-001/smoke-metadata-import.json')).inputs.map(x=>x.path),...catalogue.qualifier_code.map(x=>x.path),...Object.values(root).filter(x=>x?.path).map(x=>x.path),'coordination/engineering/selected-checkpoint-reuse-20261012/accepted-checkpoints.json']);
allowed.add('coordination/engineering/arctic-three-retained-land-fit-repair-native-20261008/native-v9/manifest.json');
const original=ImmutableReader.prototype.read, opened=[];
ImmutableReader.prototype.read=function(name,options){
 assert(allowed.has(name),'Unplanned body open: '+name);
 assert(!name.startsWith('data/geography/')&&!/assets-bank\/.*\.bin\.gz$/.test(name)&&!name.endsWith('.bin'),'Scientific body-open trap: '+name);
 opened.push({commit:options?.version??this.version,path:name});return original.call(this,name,options);
};
for(const method of ['logical','member'])if(typeof NativeAssetImage.prototype[method]==='function')NativeAssetImage.prototype[method]=()=>{throw Error('Native image body-open trap');};
const startup=selectedBootstrap(repo,baseline,baseline,{parentRuntimePath:process.env.PYTHON});
const code=JOINT_CODE.map(path=>({path,bytes:fs.statSync(path).size}));
const allowance=processingAllowance({phaseBytes:1024**3,rssBytes:1024**3});
const reader=new ImmutableReader(repo,baseline,{runtimeBytes:startup.beforeReader.runtimeBytes,executionBytes:code.reduce((n,x)=>n+x.bytes,0),gitExecutable:startup.beforeReader.gitExecutable,allowance});
const budget={shared:reader.budget,carriedBytes:7*valueBytes({code,identities:startup.identities}).length+7*4*1024**2};
let state;const started=performance.now();
try{
 const result=qualifyCheckpoint({reader,budget});
 assert.equal(result.available,true,result.reason);state=result.state;
 assert.equal(state.accepted_execution.kind,'trusted-main-derived-selected-checkpoint-v1');
 fs.writeFileSync(output,JSON.stringify({version:1,complete:true,trusted,baseline,seconds:(performance.now()-started)/1000,accepted_execution:state.accepted_execution,selection:state.selection,certificate_entries:state.certificate.entries.length,source_native_body_opens:0,opened,inventory:[...reader.inventory.values()]},null,2)+'\n',{flag:'wx'});
 console.log(JSON.stringify({available:true,accepted_execution:state.accepted_execution,certificate_entries:state.certificate.entries.length,body_reads:opened.length,seconds:(performance.now()-started)/1000}));
}finally{if(state)releaseCheckpoint(state);}
