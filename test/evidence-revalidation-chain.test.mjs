import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {gzipSync} from 'node:zlib';
import {validateEvidenceRevalidationChain} from '../scripts/validate-evidence-revalidation-chain.mjs';
const sha=raw=>createHash('sha256').update(raw).digest('hex');
function fixture(){
 const files=new Map([['data/old-proof.json',Buffer.from('original proof')],['data/new-proof.json',Buffer.from('new proof')]]);
 const old={version:1,historical_membership_assigned:false,records:1,original_geography:{hierarchy_sha256:'original'},revalidated_geography:{hierarchy_sha256:'v5'},source_product_files:[{path:'rows.json',sha256:'immutable'}],entities:[{entity_id:'location',original_footprint_sha256:'unchanged',revalidated_footprint_sha256:'unchanged'}],migration_receipts:[{path:'data/old-proof.json',sha256:sha(files.get('data/old-proof.json'))}]};
 const raw=Buffer.from(JSON.stringify(old)+'\n'),packed=gzipSync(raw);
 files.set('data/previous.json.gz',packed);
 const current={...structuredClone(old),revalidated_geography:{hierarchy_sha256:'v6'},migration_receipts:[...old.migration_receipts,{path:'data/new-proof.json',sha256:sha(files.get('data/new-proof.json'))}],projection:{previous_revalidation_sha256:sha(raw)},prior_revalidation:{sha256:sha(raw),archive_path:'data/previous.json.gz',archive_sha256:sha(packed),compression:'gzip',revalidated_geography:old.revalidated_geography}};
 return {current,files,options:{root:'/tmp/unused',readFile:name=>{if(!files.has(name))throw Error('Missing fixture bytes');return files.get(name);}}};
}
test('exact predecessor bytes retain original claims and append migration chronology',()=>{
 const f=fixture(),before=structuredClone(f.current),result=validateEvidenceRevalidationChain(f.current,f.options);
 assert.equal(result.validated,true);assert.equal(result.archived_predecessors.length,1);assert.deepEqual(result.limits,[]);assert.deepEqual(f.current,before);
});
test('damaged archive, raw digest, current projection and previous geography reject',()=>{
 for(const mutate of [f=>f.files.set('data/previous.json.gz',gzipSync('changed')),f=>f.current.prior_revalidation.sha256='0'.repeat(64),f=>f.current.projection.previous_revalidation_sha256='0'.repeat(64),f=>f.current.prior_revalidation.revalidated_geography.hierarchy_sha256='wrong']){
  const f=fixture();mutate(f);assert.throws(()=>validateEvidenceRevalidationChain(f.current,f.options),/changed|exact archived predecessor|original claims/);
 }
});
test('replaced migration history and changed proof bytes reject',()=>{
 let f=fixture();f.current.migration_receipts.shift();assert.throws(()=>validateEvidenceRevalidationChain(f.current,f.options),/chronology/);
 f=fixture();f.files.set('data/old-proof.json',Buffer.from('changed'));assert.throws(()=>validateEvidenceRevalidationChain(f.current,f.options),/proof bytes/);
});
test('claim, source inventory, count and territorial transfer reject',()=>{
 for(const mutate of [x=>x.historical_membership_assigned=true,x=>x.original_geography.hierarchy_sha256='wrong',x=>x.source_product_files[0].sha256='wrong',x=>x.records=2,x=>x.entities[0].revalidated_footprint_sha256='wrong',x=>x.entities.push(x.entities[0])]){
  const f=fixture();mutate(f.current);assert.throws(()=>validateEvidenceRevalidationChain(f.current,f.options),/transfers history|original claims|duplicate subjects/);
 }
});
test('escaping, absolute paths and unknown archive compression reject',()=>{
 for(const value of ['../escape','/absolute']){const f=fixture();f.current.prior_revalidation.archive_path=value;assert.throws(()=>validateEvidenceRevalidationChain(f.current,f.options),/Unsafe/);}
 const f=fixture();f.current.prior_revalidation.compression='zip';assert.throws(()=>validateEvidenceRevalidationChain(f.current,f.options),/Unsafe/);
});
test('legacy detached terminal hash is recorded as a limit without inventing an archive',()=>{
 const f=fixture();delete f.current.prior_revalidation;const result=validateEvidenceRevalidationChain(f.current,f.options);
 assert.equal(result.archived_predecessors.length,0);assert.equal(result.limits.length,1);
});
