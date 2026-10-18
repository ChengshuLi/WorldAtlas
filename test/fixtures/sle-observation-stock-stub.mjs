import fs from 'node:fs';
import path from 'node:path';
import {gunzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';

const base='75861b9784f75b7894bfc51fa0419f40f966157d';
const prefix='coordination/engineering/sierra-leone-physical-review-20261018-worker4/';
const sha=body=>createHash('sha256').update(body).digest('hex');
let intervalRows;
function retainedIntervals(){
  if(!intervalRows)intervalRows=JSON.parse(gunzipSync(fs.readFileSync(path.join(process.cwd(),prefix,'intervals/block-030.json.gz'))));
  return intervalRows;
}

export function selectedBootstrap(cwd,baseCommit,effectiveCommit){
  if(cwd!==process.cwd()||baseCommit!==base||effectiveCommit!==base)throw Error('Unexpected fixture reader identity');
  const intervals=retainedIntervals(),[y,start,end,owners]=intervals[0];
  const patchBytes=Buffer.from(JSON.stringify({rows:[{y,runs:[[start,start+1,88001]]}]}));
  const patch={
    path:'synthetic/accepted-patch.json',commit:base,mode:'100644',git_blob_oid:'a'.repeat(40),
    bytes:patchBytes.length,sha256:sha(patchBytes)
  };
  const sidecarBytes=Buffer.from(JSON.stringify({
    version:2,kind:'retained-native-additive-selection-v2',
    logical_asset_map:{patch}
  }));
  const hook={path:'synthetic/accepted-sidecar.json',bytes:sidecarBytes.length,sha256:sha(sidecarBytes)};
  const code=Buffer.from('stock');
  const codePin={path:'scripts/synthetic-stock-entry.mjs',bytes:code.length,sha256:sha(code)};
  const selectedTargets=Array.from({length:14},(_,i)=>({properties:{id:'gb:SLE:ADM2:fixture-'+i}}));
  const source={source:{kind:'fixture-source'},whole_sha256:'b'.repeat(64),
    collection:{features:selectedTargets}};
  const inventory=new Map([[base+':'+hook.path,{path:hook.path,commit:base,bytes:hook.bytes,sha256:hook.sha256}]]);
  const reader={
    inventory,
    read(file,{expected}={}){
      let body;
      if(file===codePin.path)body=code;
      else if(file===hook.path)body=sidecarBytes;
      else if(file===patch.path)body=patchBytes;
      else throw Error('Unexpected fixture read: '+file);
      if(expected&&sha(body)!==expected)throw Error('Fixture pin mismatch: '+file);
      return body;
    },
    descriptor(file,commit){
      if(file!==patch.path||commit!==patch.commit)throw Error('Unexpected fixture patch descriptor');
      return {mode:patch.mode,git_blob_oid:patch.git_blob_oid,bytes:patch.bytes};
    }
  };
  return {beforeReader:reader,executionCode:[codePin],runtime:{kind:'synthetic-existing-reader'},
    identities:{kind:'bounded-control-fixture'},fixture:{intervals,owners:owners[0],first:[y,start,end]}};
}

export function loadBaseSelection(reader){
  const selection={additive_release:{path:'synthetic/accepted-sidecar.json',
    bytes:reader.inventory.get(base+':synthetic/accepted-sidecar.json').bytes,
    sha256:reader.inventory.get(base+':synthetic/accepted-sidecar.json').sha256}};
  return {selection,geometrySources:{read(pathname){
    if(pathname!=='data/geography/part-22.json')throw Error('Unexpected source fixture read');
    return {source:{kind:'fixture-source'},whole_sha256:'b'.repeat(64),collection:{features:
      Array.from({length:14},(_,i)=>({properties:{id:'gb:SLE:ADM2:fixture-'+i}}))}};
  }}};
}

export function loadNativeRowTable(){return {kind:'synthetic-row-table'};}

export function acquireNativeRows(snapshot,table,rows){
  if(!snapshot||table.kind!=='synthetic-row-table')throw Error('Unexpected native-row fixture input');
  const grouped=new Map(rows.map(y=>[y,[]]));
  for(const [y,start,end,owners] of retainedIntervals()){
    if(grouped.has(y))grouped.get(y).push([start,end,owners[0]]);
  }
  const offsets=[0],words=[];
  for(const y of rows){
    for(const [start,end,owner] of grouped.get(y))words.push(start,end,owner);
    offsets.push(words.length);
  }
  return {offsets:Uint32Array.from(offsets),words:Uint32Array.from(words),custody:{kind:'synthetic-native-custody'}};
}
