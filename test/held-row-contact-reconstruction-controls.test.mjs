import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {execFileSync,spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import zlib from 'node:zlib';

const root=process.cwd();
const fixtureManifestPath='test/fixtures/held-row-contact/input-locators.json';
const manifestBytes=fs.readFileSync(path.join(root,fixtureManifestPath));
const manifest=JSON.parse(manifestBytes);
const packetDir=path.join(root,manifest.packet_directory);
const packetPath=path.join(packetDir,'held-row-exception-packet.json');
const resultsPath=path.join(packetDir,'centre-contact-results.json');
const adapterPath=path.join(packetDir,'held-row-diagnostic-repro.mjs');
const expectedPinsBlob='189dde6fbb4a0098e0f1d3ca0e40bd192f6e493a';
const expectedAdapterSha='57c0d3dcca56ef0614bb693543dcaa4e28f4a147bce1e8a9a5d9d1f18cb398cd';
const expectedPacketSha='b2bd104ecd27a599973c83815fc941a8a8182015b524d475fc1ccd8a35e1774d';
const expectedResultsSha='d4f3160ce42ed4ba5f1fb9ded4fd22d48bd19fc452b0753393b3d2411a99b2b0';
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
function git(args){
 return execFileSync('git',args,{cwd:root,encoding:null,maxBuffer:8*1024*1024,env:{...process.env,GIT_NO_LAZY_FETCH:'1',GIT_TERMINAL_PROMPT:'0'}});
}
function authenticate(pin){
 assert.equal(typeof pin.commit,'string');
 assert.equal(typeof pin.path,'string');
 const tree=git(['ls-tree','-z',pin.commit,'--',pin.path]).toString('utf8').split('\0').filter(Boolean);
 assert.equal(tree.length,1,'exactly one original tree entry: '+pin.path);
 const match=/^([0-7]{6}) blob ([a-f0-9]{40})\t(.+)$/.exec(tree[0]);
 assert(match,'regular Git blob required: '+pin.path);
 assert.equal(match[1],'100644','regular immutable source file: '+pin.path);
 assert.equal(match[2],pin.git_blob_oid,'tree blob differs: '+pin.path);
 assert.equal(match[3],pin.path,'tree path differs: '+pin.path);
 const bytes=git(['cat-file','blob',pin.git_blob_oid]);
 const objectOid=createHash('sha1').update(Buffer.concat([Buffer.from('blob '+bytes.length+'\0'),bytes])).digest('hex');
 assert.equal(objectOid,pin.git_blob_oid,'Git object identity differs: '+pin.path);
 assert.equal(bytes.length,pin.bytes,'byte length differs: '+pin.path);
 assert.equal(sha(bytes),pin.sha256,'SHA-256 differs: '+pin.path);
 let decoded=null;
 if(pin.decoded_bytes!==undefined){
  decoded=zlib.gunzipSync(bytes);
  assert.equal(decoded.length,pin.decoded_bytes,'decoded byte length differs: '+pin.path);
  assert.equal(sha(decoded),pin.decoded_sha256,'decoded SHA-256 differs: '+pin.path);
 }
 return {bytes,decoded};
}
function normalized(doc){
 const result={method:doc.method,size:doc.size,latitude_bytes:doc.latitude_bytes,results:[]};
 for(const row of doc.results){
  const value={};
  for(const key of ['country','owner','target','cell','positive','derived_base_geometry_contact','positive_geometry_sha256','derived_base_geometry_sha256','source_evidence_commit','diagnostic_rule_sha256'])value[key]=row[key];
  value.positive_source={};
  for(const key of ['source_id','name','feature_ordinal','decoded_bytes','decoded_sha256'])value.positive_source[key]=row.positive_source[key];
  value.exclusions=row.exclusions.map(item=>{
   const keys=item.source_id==='inline-archive-only'
    ?['source_index','source_id','geometry_sha256','relation']
    :['negative_ordinal','source_id','feature_ordinal','feature_id','decoded_bytes','decoded_sha256','geometry_sha256','relation'];
   return Object.fromEntries(keys.map(key=>[key,item[key]]));
  });
  result.results.push(value);
 }
 return result;
}
function runAdapter(packet,fixtures,helper,latitudes){
 const env={...process.env};delete env.NODE_OPTIONS;delete env.NODE_PATH;
 return spawnSync(process.execPath,[adapterPath,'--packet',packet,'--fixture-root',fixtures,'--helper',helper,'--latitudes',latitudes],
  {cwd:root,env,encoding:'utf8',maxBuffer:8*1024*1024});
}
test('authenticated held-row reconstruction matches its retained output and rejects altered evidence',()=>{
 const manifestTree=git(['ls-tree','-z','HEAD','--',fixtureManifestPath]).toString('utf8').split('\0').filter(Boolean);
 assert.equal(manifestTree.length,1);
 assert.equal(manifestTree[0].split(' ')[2]?.split('\t')[0],expectedPinsBlob,'review locator manifest changed');
 assert.equal(manifest.reviewed_head,'2a2745b995de5ffaae04376737a573b703e53db0');
 const packetBytes=fs.readFileSync(packetPath),resultsBytes=fs.readFileSync(resultsPath),adapterBytes=fs.readFileSync(adapterPath);
 assert.equal(sha(packetBytes),expectedPacketSha);
 assert.equal(sha(resultsBytes),expectedResultsSha);
 assert.equal(sha(adapterBytes),expectedAdapterSha);
 assert.equal(manifest.source_and_evidence_inputs.length,9);
 assert.equal(manifest.original_extraction_inputs.length,3);
 const pins=[...manifest.source_and_evidence_inputs,...manifest.original_extraction_inputs,manifest.helper,manifest.latitudes];
 assert.equal(pins.length,14);
 const commits=[...new Set(pins.map(pin=>pin.commit))];
 assert.deepEqual(commits,[
  '252f2aa1e6309b6990985dec73611d6df0e11c70',
  '601852e911478b90762edb7b9d80985786f95d43',
  '8c192828cf81a554176efdead967acb9b05ac79e',
  '6a6358d232df09ef4561073f8727b2892d5413ea',
  'e38e3488de52e6ef299157f7dc736398a1b9ca1f',
  '2d1fc6f430e756498908bf2c4e267356a13f5cc7'
 ]);
 const tmp=fs.mkdtempSync(path.join(os.tmpdir(),'held-row-ci-'));
 try{
  const fixtureRoot=path.join(tmp,'inputs');
  const extracted=new Map();
  for(const pin of pins){
   const {bytes,decoded}=authenticate(pin);
   const target=path.join(fixtureRoot,pin.fixture_path);
   fs.mkdirSync(path.dirname(target),{recursive:true});
   fs.writeFileSync(target,decoded??bytes);
   if(pin.decoded_sha256)extracted.set(pin.fixture_path,decoded);
  }
  const packet=JSON.parse(packetBytes.toString('utf8'));
  const originalBlocks=new Map(manifest.original_extraction_inputs.map(pin=>[pin.country+':'+pin.block,pin]));
  for(const row of packet.rows){
   const key=row.original_key,country=row.owner.source_id.split(':')[1];
   const pin=originalBlocks.get(country+':'+key.original_block);
   assert(pin,'original interval pin missing for row');
   const block=JSON.parse(extracted.get(pin.fixture_path).toString('utf8'));
   assert.equal(block.length,pin.intervals,'original interval count differs');
   const matches=block.filter(item=>item[0]===key.y&&item[1]<=key.x&&key.x<item[2]&&item[3].includes(key.owner_index));
   assert.equal(matches.length,1,'original row must be unique for '+country+' '+key.x+','+key.y);
   assert.equal(matches[0][5],key.class,'original class differs for '+country);
   assert.deepEqual(matches[0][4],[...row.original_source_contact_indices].sort((a,b)=>a-b),'complete original contacts differ for '+country);
  }
  const expected=JSON.parse(resultsBytes.toString('utf8'));
  const baseline=runAdapter(packetPath,fixtureRoot,path.join(fixtureRoot,manifest.helper.fixture_path),path.join(fixtureRoot,manifest.latitudes.fixture_path));
  assert.equal(baseline.status,0,baseline.stderr);
  const actual=JSON.parse(baseline.stdout);
  assert.deepEqual(normalized(actual),normalized(expected));
  assert.equal(actual.results.length,4);
  assert.equal(actual.results.reduce((sum,row)=>sum+row.exclusions.length,0),12);
  const refuse=(name,packetArg,fixtureArg,helperArg,latArg,needle)=>{
   const result=runAdapter(packetArg,fixtureArg,helperArg,latArg);
   assert.notEqual(result.status,0,name+' must refuse');
   assert.match(result.stderr,needle,name);
  };
  const badHelper=path.join(tmp,'altered-helper.mjs');
  fs.writeFileSync(badHelper,Buffer.concat([fs.readFileSync(path.join(fixtureRoot,manifest.helper.fixture_path)),Buffer.from('\n')]));
  refuse('altered helper',packetPath,fixtureRoot,badHelper,path.join(fixtureRoot,manifest.latitudes.fixture_path),/Native helper SHA-256/);
  const badLat=path.join(tmp,'altered-latitudes.f64le');
  const latitude=Buffer.from(fs.readFileSync(path.join(fixtureRoot,manifest.latitudes.fixture_path)));latitude[0]^=1;fs.writeFileSync(badLat,latitude);
  refuse('altered latitude',packetPath,fixtureRoot,path.join(fixtureRoot,manifest.helper.fixture_path),badLat,/Normative latitude vector size or SHA-256/);
  const changedPacket=path.join(tmp,'changed-owner-packet.json'),changed=JSON.parse(packetBytes.toString('utf8'));
  changed.rows[0].original_key.owner_index+=1;fs.writeFileSync(changedPacket,JSON.stringify(changed));
  refuse('changed original owner binding',changedPacket,fixtureRoot,path.join(fixtureRoot,manifest.helper.fixture_path),path.join(fixtureRoot,manifest.latitudes.fixture_path),/Target binding mismatch/);
  const alteredRoot=path.join(tmp,'altered-inputs');fs.cpSync(fixtureRoot,alteredRoot,{recursive:true});
  const positive=path.join(alteredRoot,'payloads','gb-HND-ADM2-000.bin.gz');
  fs.writeFileSync(positive,zlib.gzipSync(zlib.gunzipSync(fs.readFileSync(positive))));
  refuse('altered complete positive source body',packetPath,alteredRoot,path.join(fixtureRoot,manifest.helper.fixture_path),path.join(fixtureRoot,manifest.latitudes.fixture_path),/Whole source body mismatch/);
  for(const [name,mutate] of [
   ['changed contact relation',doc=>{doc.results[0].positive.relation='outside';}],
   ['changed geometry digest',doc=>{doc.results[0].derived_base_geometry_sha256='0'.repeat(64);}],
   ['omitted negative operand',doc=>{doc.results[0].exclusions.pop();}],
   ['changed negative source identity',doc=>{doc.results[1].exclusions[0].source_id='gb:HND:ADM1:wrong';}]
  ]){
   const altered=JSON.parse(JSON.stringify(actual));mutate(altered);
   assert.notDeepEqual(normalized(altered),normalized(expected),name+' must change the scientific projection');
  }
 }finally{
  fs.rmSync(tmp,{recursive:true,force:true});
 }
});
