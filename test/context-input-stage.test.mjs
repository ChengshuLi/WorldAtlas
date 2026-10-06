import test from 'node:test';
import assert from 'node:assert/strict';
import {validateContextInputStage,CONTEXT_STAGE_PATH} from '../scripts/native-ownership/validate-context-input-stage.mjs';
import {repositoryReader,sha256} from '../scripts/evidence-quality.mjs';
const read=repositoryReader(process.cwd());
test('complete native context stage verifies original bytes, compact derivative and both immutable inventories',{timeout:90000},async()=>{
 const result=await validateContextInputStage();
 assert.equal(result.locations,49625);assert.equal(result.source_files,43);assert.equal(result.vertices,3968397);
 assert.equal(result.scientific_approval,false);assert.equal(result.status,'verified');
});
test('mandatory context stage rejects missing, tampered, stale and over-budget inputs',{timeout:90000},async()=>{
 await assert.rejects(validateContextInputStage({readFile:(name,v)=>{if(name===CONTEXT_STAGE_PATH)throw Error('Missing stage');return read(name,v);}}),/Missing stage/);
 const mutate=change=>(name,v)=>{const raw=read(name,v);if(name!==CONTEXT_STAGE_PATH)return raw;const m=JSON.parse(raw);change(m);return Buffer.from(JSON.stringify(m));};
 await assert.rejects(validateContextInputStage({readFile:mutate(m=>m.outputs.find(f=>f.path.endsWith('part-0.json.gz')).sha256='0'.repeat(64))}),/bytes mismatch/);
 await assert.rejects(validateContextInputStage({readFile:mutate(m=>m.baseline.files[0].sha256='0'.repeat(64))}),/bytes mismatch|actual file binding/);
 await assert.rejects(validateContextInputStage({readFile:mutate(m=>m.outputs[0].bytes=33*1024*1024)}),/exceeds budget/);
 await assert.rejects(validateContextInputStage({readFile:mutate(m=>m.transform.kind='unchecked-stage')}),/Unsupported/);
 await assert.rejects(validateContextInputStage({readFile:mutate(m=>m.baseline.files=m.baseline.files.filter(f=>f.path!=='data/geography/part-0.json'))}),/Incomplete original/);
 const originalInputs=JSON.parse(read(CONTEXT_STAGE_PATH.replace('evidence-quality.json','inputs.json'),'candidate'));
 await assert.rejects(validateContextInputStage({expectedReference:{id:'stale-release',footprints_sha256:originalInputs.footprints_sha256,hierarchy_sha256:'568301690ef231a85856666b57876a5efe8d8c7c6e671a56d81307b2dc28b80b'}}),/Expected values/);
 for(const omit of [true,false]){
  const name=CONTEXT_STAGE_PATH.replace('evidence-quality.json','inputs.json');
  const changed=structuredClone(originalInputs);
  changed.executed_sources=omit?changed.executed_sources.slice(1):[...changed.executed_sources,changed.executed_sources[0]];
  const raw=Buffer.from(JSON.stringify(changed));
  const manifest=JSON.parse(read(CONTEXT_STAGE_PATH,'candidate'));
  Object.assign(manifest.outputs.find(f=>f.path===name),{bytes:raw.length,sha256:sha256(raw)});
  await assert.rejects(validateContextInputStage({readFile:(n,v)=>n===name?raw:n===CONTEXT_STAGE_PATH?Buffer.from(JSON.stringify(manifest)):read(n,v)}),/Incomplete or duplicate/);
 }
 await assert.rejects(validateContextInputStage({expectedReference:{footprints_sha256:'0'.repeat(64),hierarchy_sha256:'0'.repeat(64)}}),/Expected values/);
});
