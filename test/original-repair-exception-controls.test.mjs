import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';

const packet='coordination/engineering/sweden-el-salvador-original-exceptions-20261018/';
const fixture='test/fixtures/original-repair-exceptions/';
const read=name=>JSON.parse(fs.readFileSync(fixture+name,'utf8'));
const hash=b=>createHash('sha256').update(b).digest('hex');
const originalPatch='32d819ddc9333ff025584665665c963822dfcead:coordination/engineering/americas-following-original-evaluations-20261018/source-packets/SLV/original-native-requested-patch.json';
function workspace(t){const d=fs.mkdtempSync(path.join(os.tmpdir(),'repair-exceptions-'));t.after(()=>fs.rmSync(d,{recursive:true,force:true}));return d;}
function run(directory,env=process.env){return spawnSync(process.env.PYTHON??'python3',['-I','-B',path.resolve(packet+'verify-original-partitions.py'),process.cwd(),path.join(directory,'output')],{encoding:'utf8',maxBuffer:8*1024*1024,env});}

test('actual original exception verifier preserves all original keys, source contacts, holds and zero credit',t=>{
 const d=workspace(t),pins=read('historical-input-pins.json').inputs;
 for(const pin of pins){
  const result=spawnSync('git',['--no-lazy-fetch','show',pin.commit+':'+pin.path],{maxBuffer:40*1024*1024});
  assert.equal(result.status,0,String(result.stderr));const b=result.stdout;
  assert.equal(b.length,pin.bytes);assert.equal(hash(b),pin.sha256);
  assert.equal(createHash('sha1').update(Buffer.from(`blob ${b.length}\0`)).update(b).digest('hex'),pin.git_blob_oid);
 }
 const result=run(d);assert.equal(result.error,undefined);assert.equal(result.status,0,result.stderr);
 for(const country of ['swe','slv']){
  const name=country+'-original-partition.json',expected=read(name),actual=JSON.parse(fs.readFileSync(path.join(d,'output',name)));
  assert.deepEqual(actual,expected);
  assert.equal(actual.new_native_repairs,0);assert.equal(actual.accepted_disposition_credit,0);
  assert.equal(actual.original_cells,actual.accepted_original_owner_cells+actual.proposed_documented_exceptions);
  const validate=r=>{assert.deepEqual(r,expected);assert.equal(new Set(r.exception_records.map(x=>`${x.y}:${x.x}:${x.owner}`)).size,r.proposed_documented_exceptions);};
  const changes=[
   r=>r.exception_records.pop(),r=>r.exception_records.push(structuredClone(r.exception_records[0])),
   r=>r.exception_records[0].owner=1,r=>r.exception_records[0].x=0,
   r=>r.exception_records[0].original_source_contacts.pop(),r=>r.exception_records[0].physical_class='inland_water',
   r=>r.exception_records[0].positive_original_target_id='invented',r=>r.new_native_repairs=1,
   r=>r.exception_records[0].scientific_territorial_hold_retained=false,r=>r.accepted_original_owner_cells++,
   r=>r.proposed_exception_key_sha256='0'.repeat(64),r=>r.accepted_disposition_credit=1
  ];
  for(const change of changes){const altered=structuredClone(actual);change(altered);assert.throws(()=>validate(altered));}
 }
 assert.deepEqual(JSON.parse(fs.readFileSync(path.join(d,'output','input-custody.json'))),read('input-custody.json'));
});

// A bounded transport fault injection. The actual current Python program still
// reads every other original Git body; no source/native producer is executed.
function brokenGit(directory,ref,change){
 const real=spawnSync('which',['git'],{encoding:'utf8'}).stdout.trim();assert(real);
 const bin=path.join(directory,'bin');fs.mkdirSync(bin);
 const body=`#!${process.execPath}\nconst {spawnSync}=require('node:child_process');const args=process.argv.slice(2);const p=spawnSync(${JSON.stringify(real)},args,{maxBuffer:40*1024*1024});if(p.status!==0){process.stderr.write(p.stderr);process.exit(p.status??1);}let b=p.stdout;if(args.at(-1)===${JSON.stringify(ref)}){let x=JSON.parse(b);${change};b=Buffer.from(JSON.stringify(x));}process.stdout.write(b);`;
 fs.writeFileSync(path.join(bin,'git'),body,{mode:0o755});return {...process.env,PATH:bin+path.delimiter+process.env.PATH};
}
test('actual verifier refuses a changed original requested owner rather than manufacturing an exception',t=>{
 const d=workspace(t),env=brokenGit(d,originalPatch,'x.rows[0].runs[0][2]=1');const result=run(d,env);
 assert.notEqual(result.status,0);assert.match(result.stderr,/requested_cells==set\(cells\)|AssertionError/);
 assert.equal(fs.existsSync(path.join(d,'output','slv-original-partition.json')),false);
});
test('actual verifier refuses tampered accepted patch custody before recording any disposition',t=>{
 const d=workspace(t),pins=read('historical-input-pins.json').inputs;
 const pin=pins.find(p=>p.path.endsWith('composition-six-001/patch.json'));assert(pin);
 const result=run(d,brokenGit(d,pin.git_ref,'x.rows[0].runs[0][2]=1'));
 assert.notEqual(result.status,0);assert.match(result.stderr,/AssertionError/);
 assert.equal(fs.existsSync(path.join(d,'output','swe-original-partition.json')),false);
});
