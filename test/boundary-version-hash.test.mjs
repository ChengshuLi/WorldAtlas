import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import {execFileSync} from 'node:child_process';
import {DatabaseSync} from 'node:sqlite';
import {createHash} from 'node:crypto';
const root=path.resolve(import.meta.dirname,'..'),helper=path.join(root,'scripts/boundary-version-hash.py');
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const polygon=size=>JSON.stringify({type:'Polygon',coordinates:[[[0,0],[size,0],[size,size],[0,size],[0,0]]]});

test('dated non-example footprint fingerprints change with geometry/date and ignore examples',()=>{
 const temporary=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-footprint-version-'));
 try{
  const file=path.join(temporary,'boundaries.sqlite'),db=new DatabaseSync(file);db.exec('CREATE TABLE boundaries(location_id TEXT,valid_from INTEGER,valid_to INTEGER,geometry TEXT,is_example INTEGER)');
  const digest=()=>execFileSync('python3',[helper,'--database',file],{encoding:'utf8'}).trim();
  const empty=digest();assert.equal(empty,sha('[]'));
  db.prepare('INSERT INTO boundaries VALUES(?,?,?,?,?)').run('fictional',1000,1100,'not a real geometry',1);assert.equal(digest(),empty,'example geometry cannot invalidate factual ownership');
  db.prepare('INSERT INTO boundaries VALUES(?,?,?,?,?)').run('real',1000,1100,polygon(1),0);const real=digest();assert.notEqual(real,empty);
  const rows=db.prepare('SELECT location_id,valid_from,valid_to,geometry FROM boundaries WHERE is_example=0').all().map(r=>[r.location_id,r.valid_from,r.valid_to,r.geometry]);
  assert.equal(execFileSync('python3',[helper,'--stdin'],{input:JSON.stringify(rows),encoding:'utf8'}).trim(),real,'API and preparation use the same fingerprint');
  db.exec("UPDATE boundaries SET valid_to=1101 WHERE location_id='real'");const dated=digest();assert.notEqual(dated,real,'changing only a supported interval invalidates ownership');
  db.prepare("UPDATE boundaries SET geometry=? WHERE location_id='real'").run(polygon(2));assert.notEqual(digest(),dated,'changing only geometry invalidates ownership');
  const before=sha(fs.readFileSync(file));digest();assert.equal(sha(fs.readFileSync(file)),before,'fingerprint computation never mutates the database');db.close();
 }finally{fs.rmSync(temporary,{recursive:true,force:true});}
});

test('boundary fingerprints verify the archived executed canonical algorithm',()=>{
 const temporary=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-footprint-algorithm-'));
 try{
  const index=JSON.parse(fs.readFileSync(path.join(root,'data/ownership-history/index.json')));for(const entry of index.execution_algorithms){const target=path.join(temporary,entry.path);fs.mkdirSync(path.dirname(target),{recursive:true});fs.copyFileSync(path.join(root,'data/ownership-history',entry.path),target);}
  const indexFile=path.join(temporary,'index.json');fs.writeFileSync(indexFile,JSON.stringify(index));const input=JSON.stringify([['real',1000,1100,polygon(1)]]);
  assert.match(execFileSync('python3',[helper,'--index',indexFile,'--stdin'],{input,encoding:'utf8'}).trim(),/^[a-f0-9]{64}$/);
  fs.appendFileSync(path.join(temporary,index.execution_algorithms[0].path),'\n# changed');assert.throws(()=>execFileSync('python3',[helper,'--index',indexFile,'--stdin'],{input,encoding:'utf8',stdio:['pipe','pipe','pipe']}),/Executed ownership algorithm hash mismatch/);
 }finally{fs.rmSync(temporary,{recursive:true,force:true});}
});

test('changed footprints invalidate cached values while direct evidence can still resolve the location',async()=>{
 const {preparedBoundariesMatch,invalidatePreparedFootprints}=await import('../derived.mjs');
 const {resolveAttributes}=await import('../src/attributes.js');
 const rows=[['affected',1000,1100,polygon(1)]];
 assert.equal(preparedBoundariesMatch([]),true);
 assert.equal(preparedBoundariesMatch(rows),false);
 const cached=[{id:'old-owner',location_id:'affected',attribute:'owner',value:'Old polity',category_id:'owner:old',method:'majority-area',status:'derived',valid_from:1000,valid_to:1100,source:'Prepared source'}, {id:'other-owner',location_id:'other',attribute:'owner',value:'Other polity',category_id:'owner:other',method:'majority-area',valid_from:1000,valid_to:1100,source:'Prepared source'}];
 const invalidated=invalidatePreparedFootprints(cached,rows,false);
 assert.equal(invalidated[0].value,null);assert.equal(invalidated[0].category_id,null);assert.equal(invalidated[0].metadata.invalidated_footprint,true);assert.deepEqual(invalidated[1],cached[1]);
 const features=[{id:'affected',properties:{}}];
 const direct={id:'direct',location_id:'affected',attribute:'owner',value:'Direct polity',category_id:'owner:direct',method:'direct',valid_from:1000,valid_to:1100,source:'Direct evidence'};
 assert.equal(resolveAttributes(features,1000,{records:invalidated,states:[]}).get('affected').owner,null);
 assert.equal(resolveAttributes(features,1000,{records:[...invalidated,direct],states:[]}).get('affected').owner,'Direct polity');
});
