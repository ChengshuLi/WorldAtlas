// Existing full-geography evidence consumers, with explicit owned product copies.
import fs from 'node:fs';import path from 'node:path';import assert from 'node:assert/strict';import {gunzipSync} from 'node:zlib';import {createHash} from 'node:crypto';
import {immutableReader,BEFORE,AFTER} from './native-producer.mjs';
import {revalidatePreparedEvidence} from '../../../scripts/revalidate-prepared-evidence.mjs';
import {prepareEvidenceBundle} from '../../../scripts/prepare-evidence-bundle.mjs';
import {validateEvidenceRevalidationChain} from '../../../scripts/validate-evidence-revalidation-chain.mjs';
import{execFileSync}from'node:child_process';
import{fileURLToPath}from'node:url';
import{requirePlainExecution}from'../../../scripts/native-ownership/native-preparation-guards.mjs';
import {footprintHash} from '../../../scripts/check-prepared.mjs';
const sha=b=>createHash('sha256').update(b).digest('hex');const json=x=>Buffer.from(JSON.stringify(x)+'\n');
export function continueContent(repo,baseline,runRoot,plan,{storage}={}){
 assert(path.isAbsolute(runRoot)&&fs.realpathSync(runRoot)===runRoot);assert.equal(plan.read_commit,baseline);
 const reader=immutableReader(repo,baseline,storage),review=immutableReader(repo,'b4b7db357ba92d19df513f188bbd046fe66a35e4',storage);
 function put(name,raw){assert(!path.isAbsolute(name)&&name.split('/').every(p=>p&&p!=='.'&&p!=='..'));assert(raw.length<=32*1024*1024);const target=path.join(runRoot,name);fs.mkdirSync(path.dirname(target),{recursive:true});assert(fs.realpathSync(path.dirname(target))===path.dirname(target));fs.writeFileSync(target,raw,{flag:'wx'});}
 const index=reader.object('data/world-index.json'),before=[];
 for(const name of ['world-index.json','hierarchy.json',...index.parts]){
  const raw=reader.read('data/'+name);put('before/'+name,raw);put('data/'+name,name==='geography/part-29.json'?gunzipSync(review.read('coordination/engineering/eastern-two-gap-repair-20261007/run-one/proposed-part-29.json.gz'),{maxOutputLength:32*1024*1024}):raw);
  if(name.startsWith('geography/'))before.push(...JSON.parse(raw).features);
 }
 assert.equal(before.length,49625);assert.equal(footprintHash(before),BEFORE);
 const after=index.parts.flatMap(p=>JSON.parse(fs.readFileSync(path.join(runRoot,'data',p))).features);assert.equal(footprintHash(after),AFTER);
 const prefix='data/reference-migrations/eastern-two-gap-repair-20261006/';
 const products=plan.products.map(product=>{
  for(const pin of product.files){const raw=reader.read(pin.path);assert.equal(raw.length,pin.bytes);assert.equal(sha(raw),pin.sha256,'Original reviewed product changed');put(pin.path,raw);put(prefix+'products/'+product.id+'/'+pin.relative_product_path,raw);}
  return {id:product.id,kind:product.kind,directory:prefix+'products/'+product.id};
 });
 for(const pin of plan.prior_chain){const raw=reader.read(pin.path);assert.equal(raw.length,pin.bytes);assert.equal(sha(raw),pin.sha256,'Original reviewed content chain changed');if(!fs.existsSync(path.join(runRoot,pin.path)))put(pin.path,raw);}
 const receiptName=prefix+'migration-receipt.json.gz';put(receiptName,reader.read(receiptName));
 const initial=process.cwd();process.chdir(runRoot);
 try{
  // Default old producer directories must still reject their stale v7 receipts.
  assert.throws(()=>prepareEvidenceBundle({data:'data',output:'default-must-not-exist',products:plan.products.map(p=>({id:p.id,kind:p.kind}))}),/Stale producer revalidation geography/);
  assert(!fs.existsSync('default-must-not-exist'));
  const summaries=revalidatePreparedEvidence({before:'before',after:'data',products,migrationReceipts:[receiptName],archiveDirectory:prefix+'prior-content',write:true});
  const chains=[];
  for(const product of products){const name=product.directory+'/revalidation.json',receipt=JSON.parse(fs.readFileSync(name));
   // Bind this actual new full revalidation to its exact archived predecessor;
   // retain the old projection unchanged inside that complete immutable archive.
   assert(receipt.prior_revalidation);receipt.projection={method:'Complete unchanged-footprint source/entity revalidation by existing revalidatePreparedEvidence',previous_revalidation_sha256:receipt.prior_revalidation.sha256,
    revalidation_algorithm_sha256:receipt.revalidation_algorithm_sha256,issue:1295};
   fs.writeFileSync(name,json(receipt));chains.push({product:product.id,...validateEvidenceRevalidationChain(receipt,{root:runRoot})});
  }
  const prepared=prepareEvidenceBundle({data:'data',output:'data/prepared-evidence',products:[...products,{id:'population-ghsl',kind:'records'}]});
  assert.equal(prepared.records,396);assert.equal(prepared.names,3588);assert.equal(prepared.footprints_sha256,AFTER);
  assert.deepEqual(prepared.products.map(p=>p.directory).sort(),products.map(p=>p.directory.slice(5)).sort());
  assert(prepared.pending_products.some(p=>p.id==='population-ghsl'));
  const entityBindings=summaries.reduce((n,p)=>n+p.entities,0),claimRows=summaries.reduce((n,p)=>n+p.records,0);assert.equal(entityBindings,3984);assert.equal(claimRows,3984);
  return {version:1,status:'PASS',before_footprints_sha256:BEFORE,after_footprints_sha256:AFTER,product_qualified_entity_bindings:entityBindings,claim_rows:claimRows,changed_source_claims:0,summaries,chains,
   prepared_index_sha256:sha(fs.readFileSync('data/prepared-evidence/index.json')),pending_products:prepared.pending_products,source_pins:[...reader.pins(),...review.pins()],
   limits:['Unchanged dated claim/interval/source bytes only, no historical affiliation transfer','Pending GHSL and macro/regional certificate approvals are not promoted']};
 }finally{process.chdir(initial);}
}

// The unchanged full consumer runs alone, without a second retained world in its parent heap.
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 requirePlainExecution();assert.equal(process.argv.length,3);const invocation=JSON.parse(fs.readFileSync(process.argv[2]));
 assert(path.isAbsolute(invocation.repo)&&fs.realpathSync(invocation.repo)===invocation.repo);assert.equal(invocation.baseline,'913db0624b8aa79b188ff17a7f5c4ae0c0f63965');
 assert.match(invocation.execution_commit,/^[a-f0-9]{40}$/);
 for(const pin of invocation.executed_modules){assert(pin.path.split('/').every(p=>p&&p!=='.'&&p!=='..'));const raw=fs.readFileSync(path.join(invocation.repo,pin.path));assert.equal(raw.length,pin.bytes);assert.equal(sha(raw),pin.sha256);const committed=execFileSync('git',['-C',invocation.repo,'cat-file','blob',invocation.execution_commit+':'+pin.path],{maxBuffer:32*1024*1024});assert(raw.equals(committed));}
 const result=continueContent(invocation.repo,invocation.baseline,invocation.runRoot,invocation.plan,{storage:new Map(invocation.storage)});
 result.actual_execution={commit:invocation.execution_commit,node:process.version,executable:process.execPath,executed_module_pins:invocation.executed_modules};
 process.stdout.write(JSON.stringify(result)+'\n');
}
