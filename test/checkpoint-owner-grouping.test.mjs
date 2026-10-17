import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {valueSha} from '../coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';

// Exercise the actual private validator without exporting a new authority API.
const source=fs.readFileSync(new URL('../coordination/engineering/selected-geography-effective-prevention-20261009/selected-checkpoint.mjs',import.meta.url),'utf8');
const body=source.slice(source.indexOf('function coordinateCheck('),source.indexOf('\nfunction rebindProducts('));
const fields=['id','index','parent_id','parent_index','source','ordinal','whole_feature_sha256','geometry_sha256','effective_geometry_sha256','boxes'];
function validator(text,observe=()=>{}) {
 return vm.runInNewContext('('+text+')',{FIELDS:fields,Map,Set,
  demand:(ok,message)=>{if(!ok)throw Error(message);},supported:(ok,message)=>{if(!ok)throw Error(message);},
  hash:x=>typeof x==='string'&&/^[a-f0-9]{64}$/.test(x),same:(a,b)=>valueSha(a)===valueSha(b),
  valueSha:x=>{observe(x);return valueSha(x);}});
}
// The previous filtering expression is the independent ordered-array oracle.
const oracleBody=body.replace(/    \/\/ Build once,[\s\S]*?    const effective = additionsByTarget.get\(row\[0\]\) \?\? \[\];/,
 '    const effective = additions.filter(p => p.target_id === row[0]);');
assert.notEqual(oracleBody,body);
function fixture(additions=[]) {
 const base='a'.repeat(64),source={kind:'ordinary-immutable-git-source',bytes:1,sha256:base};
 const certificate={version:2,kind:'selected-coordinate-neighbor-certificate-v2',entry_fields:fields,binding:{},
  entries:['A','B','C'].map((id,i)=>[id,i+1,'parent',1,'source',i,base,base,
   valueSha({base_geometry_sha256:base,additions:additions.filter(p=>p.target_id===id)}),[[0,0,1,1]]]),
  inputs:[{path:'source',whole_body_sha256:base,bytes:1,source}]};
 return {certificate,facts:{binding:{},complete_owners:3,complete_sources:1},additions};
}
const outcome=(fn,f)=>{try{fn(f.certificate,f.facts,f.additions);return 'pass';}catch(e){return e.message;}};
test('owner grouping preserves filter order, duplicate references, missing owners and geometry identity',()=>{
 const geometry={type:'Polygon',coordinates:[[[0,0],[1,0],[0,0]]]};
 const row=(target,index,n)=>({target_id:target,pixelIndex:index,base_geometry_sha256:'a'.repeat(64),geometry,n});
 const a=row('A',1,1),c=row('C',3,2),b=row('A',1,3),foreign=row('absent',4,4);
 const f=fixture([c,a,foreign,b,a]),seen=[];
 assert.equal(outcome(validator(body,x=>{if(x.additions)seen.push(x.additions);}),f),'pass');
 assert.equal(outcome(validator(oracleBody),f),'pass');
 assert.deepEqual(seen.map(x=>Array.from(x)),[[a,b,a],[],[c]]);
 assert.strictEqual(seen[0][0],a);assert.strictEqual(seen[0][0].geometry,geometry);
 assert.deepEqual(f.additions,[c,a,foreign,b,a]);
});
test('owner grouping keeps original validation and refusal semantics',()=>{
 const mutations=[f=>f.certificate.entries[0][0]=null,f=>f.certificate.entries[1][0]='A',
  f=>f.certificate.entries[0][1]=2,f=>f.certificate.entries[0][7]='bad',
  f=>f.certificate.entries[0][8]='b'.repeat(64),f=>f.certificate.entries[0][9]=[],
  f=>f.certificate.inputs.push(f.certificate.inputs[0]),f=>f.certificate.inputs[0].bytes=2,
  f=>f.certificate.inputs[0].source.kind='unsupported',f=>f.additions.push(null),
  f=>{f.certificate.entries[0][0]=null;f.additions.push(null);},
  f=>{f.certificate.entries=[];f.facts.complete_owners=0;f.additions.push(null);}];
 for(const mutate of mutations){const f=fixture();mutate(f);assert.equal(outcome(validator(body),f),outcome(validator(oracleBody),f));}
});
test('owner grouping reads each original target once instead of once per owner',()=>{
 let reads=0;const row={pixelIndex:1,base_geometry_sha256:'a'.repeat(64)};
 Object.defineProperty(row,'target_id',{enumerable:true,get(){reads++;return 'A';}});
 const f=fixture([row]);reads=0;validator(body)(f.certificate,f.facts,f.additions);
 // One grouping read plus one canonical-hash read for the sole referenced row.
 assert.equal(reads,2);reads=0;validator(oracleBody)(f.certificate,f.facts,f.additions);assert.equal(reads,4);
});
