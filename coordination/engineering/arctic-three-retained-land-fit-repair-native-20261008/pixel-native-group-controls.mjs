// Actual complete-word group boundary on synthetic bounded files; no world claim.
import assert from 'node:assert/strict';
import fs from 'node:fs';import os from 'node:os';import path from 'node:path';
import {createHash} from 'node:crypto';import {gzipSync} from 'node:zlib';
import {shuffleOwnershipBytes} from '../../../src/ownership-codec.js';
import {admitPhase} from './phase-admission.mjs';import {pixelNativeGroup} from './pixel-native-group.mjs';
import {producePixelNativeGroup} from './pixel-native-group-producer.mjs';
const root=fs.mkdtempSync(path.join(fs.realpathSync(os.tmpdir()),'worldatlas-pixel-group-control-')),sha=b=>createHash('sha256').update(b).digest('hex');
try {
 const inputs=[];function words(name,value,extra={}){const canonical=Buffer.alloc(value.length*4);value.forEach((n,i)=>canonical.writeUInt32LE(n,i*4));
  const body=gzipSync(shuffleOwnershipBytes(value));const file=path.join(root,name);fs.writeFileSync(file,body);
  const pin={path:file,bytes:body.length,sha256:sha(body),mode:0o644,words:value.length,decoded_bytes:canonical.length,decoded_sha256:sha(canonical),encoding:'byte-shuffle',...extra};inputs.push(pin);return pin;}
 const rows=new Uint32Array(262166*2);rows[1]=8;for(let y=1;y<262166;y++)rows[y*2]=8;rows[rows.length-1]=28808887-8;
 const rowPin=words('rows.gz',rows,{kind:'rows'}),parts=[],pairs=[];
 for(let i=0;i<55;i++){const offset=i<4?i*4:16+(i-4)*2;const count=i<4?4:i===54?57617774-offset:2;
  const pin=i<4?words(`part${i}.gz`,new Uint32Array([6666*524288,1,6757*524288+3,3]),{kind:'runs',offset,original_path:`part${i}`}):{kind:'runs',path:`part${i}`,offset,words:count};
  parts.push({...pin,path:`part${i}`});if(i<4)pairs.push({before:pin,after:pin});}
 const manifest={size:262166,coordinateBits:19,runWords:57617774,parts};const raw=Buffer.from(JSON.stringify(manifest)),file=path.join(root,'manifest.json');fs.writeFileSync(file,raw);
 const manifestPin={path:file,bytes:raw.length,sha256:sha(raw),mode:0o644};inputs.push(manifestPin);
 const runtime={path:process.execPath,bytes:fs.statSync(process.execPath).size,sha256:sha(fs.readFileSync(process.execPath)),mode:0o755};
 const admission=admitPhase({inputs,runtime,outputReserve:65536,reservedInputBytes:inputs.reduce((n,p)=>n+(p.decoded_bytes??0),0)});
 const plan={kind:'complete-native-target-run-accounting-group',ordinal:0,rows:rowPin,parts:pairs,manifest:manifestPin};
 const out=pixelNativeGroup(admission,plan);assert.equal(out.parts.length,4);assert.equal(out.parts[0].before[6666][0][2],2);assert.deepEqual(out.parts[0].before,out.parts[0].after);
 let negative=0;const reject=fn=>{assert.throws(fn);negative++;};
 reject(()=>pixelNativeGroup(admission,{...plan,ordinal:14}));reject(()=>pixelNativeGroup(admission,{...plan,parts:pairs.slice(0,3)}));
 reject(()=>pixelNativeGroup(admission,{...plan,parts:[{...pairs[0],before:{...pairs[0].before,offset:2}},...pairs.slice(1)]}));
 reject(()=>pixelNativeGroup(admission,{...plan,parts:[{...pairs[0],before:{...pairs[0].before,original_path:'foreign'}},...pairs.slice(1)]}));
 reject(()=>pixelNativeGroup(admission,{...plan,parts:[{...pairs[0],after:{...pairs[0].after,sha256:'0'.repeat(64)}},...pairs.slice(1)]}));
 reject(()=>pixelNativeGroup(admission,{...plan,parts:[{...pairs[0],after:{...pairs[0].after,path:path.join(root,'foreign-current')}},...pairs.slice(1)]}));
 const originalOpen=fs.openSync;let opens=0;fs.openSync=(...args)=>{opens++;return originalOpen(...args);};
 try{reject(()=>producePixelNativeGroup({},path.join(process.cwd(),'.cache','..','..','escaped')));reject(()=>producePixelNativeGroup({},root));assert.equal(opens,0);}finally{fs.openSync=originalOpen;}
 console.log(JSON.stringify({positive:1,negative,actual_full_group_boundary:true,destination_zero_body_opens:true,synthetic_fixture_not_world:true}));
}finally{fs.rmSync(root,{recursive:true});}
