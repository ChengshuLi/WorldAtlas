import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {spawn} from 'node:child_process';
import {resolveTypedSnapshot} from '../../../src/typed-snapshot.js';
import {loadPreparedTypedEvidence} from '../../../src/typed-client.js';

const output=process.argv[2];
if(!output||fs.existsSync(output))throw Error('Supply a new receipt path');
const source=fs.readFileSync('data/typed-prepared-v1.json');
const artifact=fs.readFileSync('dist/client/typed-evidence.json');
assert.deepEqual(artifact,source);
const manifest=JSON.parse(fs.readFileSync('dist/client/typed-evidence-manifest.json'));
assert.equal(manifest.sha256,createHash('sha256').update(source).digest('hex'));
assert.equal(manifest.bytes,source.length);
const child=spawn(process.execPath,['server.mjs','--production'],{env:{...process.env,PORT:'0',ATLAS_TEST_MODE:'1'},stdio:['ignore','pipe','pipe']});
let logs='';child.stderr.on('data',bytes=>{logs+=bytes;});
try{
 const origin=await new Promise((resolve,reject)=>{
  const timer=setTimeout(()=>reject(Error('Prepared server startup timeout')),45000);
  child.stdout.on('data',bytes=>{logs+=bytes;const match=logs.match(/WorldAtlas listening on http:\/\/localhost:(\d+)/);if(match){clearTimeout(timer);resolve('http://127.0.0.1:'+match[1]);}});
  child.once('exit',code=>{clearTimeout(timer);reject(Error('Prepared server exited '+code));});
 });
 const serverManifest=await (await fetch(origin+'/typed-evidence-manifest.json')).json();assert.deepEqual(serverManifest,manifest);
 assert.deepEqual(Buffer.from(await (await fetch(origin+'/typed-evidence.json')).arrayBuffer()),source);
 const controls=[];
 for(const year of [-100,-1,1,2026]){
  const expected=JSON.parse(JSON.stringify(await resolveTypedSnapshot(JSON.parse(source),year,{examples:true})));
  const response=await fetch(origin+'/api/typed/v1/prepared-snapshot?year='+year+'&examples=1');assert.equal(response.status,200);assert.deepEqual(await response.json(),expected);
  const staticResult=await loadPreparedTypedEvidence({url:'https://example.org/typed-evidence.json',sha256:manifest.sha256,year,examples:true,fetcher:async()=>new Response(artifact)});assert.deepEqual(JSON.parse(JSON.stringify(staticResult)),expected);
  controls.push({year,node_http_static_prepared_equal:true,observations:expected.observations.length,links:expected.feature_links.length});
 }
 assert.equal((await fetch(origin+'/api/typed/v1/prepared-snapshot?year=0')).status,400);
 assert.equal((await fetch(origin+'/api/typed/v1/prepared-snapshot?year=2026',{method:'POST'})).status,405);
 fs.writeFileSync(output,JSON.stringify({version:1,scope:'actual local Node HTTP server and exact-byte built static/prepared empty structural archive',source_sha256:manifest.sha256,bytes:source.length,controls,year_zero_rejected:true,write_rejected:true,limits:'No provider, factual import, geographic approval, production publication or device certificate'},null,2)+'\n',{flag:'wx'});
}finally{
 child.kill('SIGTERM');
 await new Promise(resolve=>{if(child.exitCode!==null)resolve();else child.once('exit',resolve);});
}
