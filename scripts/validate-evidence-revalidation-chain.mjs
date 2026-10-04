// Validate retained byte links; this does not approve factual claims or publication.
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {isDeepStrictEqual} from 'node:util';
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const equal=isDeepStrictEqual;
export function validateEvidenceRevalidationChain(receipt,{root,readFile}={}){
 root=path.resolve(root);
 const load=readFile??(name=>{
  const file=path.resolve(root,name);
  if(!file.startsWith(root+path.sep)||!fs.lstatSync(file).isFile())throw Error('Unsafe evidence archive path');
  return fs.readFileSync(file);
 });
 const checked=[],limits=[],seen=new Set();let current=receipt,depth=0;
 while(true){
  if(current.version!==1||current.historical_membership_assigned!==false)throw Error('Evidence chain transfers history or has unknown version');
  if(!Array.isArray(current.source_product_files)||!Array.isArray(current.entities)||new Set(current.entities.map(row=>row.entity_id)).size!==current.entities.length)throw Error('Evidence chain has incomplete or duplicate subjects');
  for(const file of current.migration_receipts??[]){
   if(path.isAbsolute(file.path)||file.path.split('/').includes('..')||sha(load(file.path))!==file.sha256)throw Error('Evidence migration proof bytes changed');
  }
  const link=current.prior_revalidation;
  if(!link){
   if(current.projection?.previous_revalidation_sha256)limits.push('Legacy terminal receipt has a detached earlier projection hash; original entity/source proofs are retained, but no additional archive link is asserted.');
   break;
  }
  if(depth>=32||link.compression!=='gzip'||path.isAbsolute(link.archive_path)||link.archive_path.split('/').includes('..')||seen.has(link.sha256))throw Error('Unsafe or cyclic evidence predecessor');
  const packed=load(link.archive_path);
  if(sha(packed)!==link.archive_sha256)throw Error('Evidence predecessor archive changed');
  const raw=gunzipSync(packed,{maxOutputLength:32*1024*1024});
  if(sha(raw)!==link.sha256)throw Error('Evidence predecessor raw bytes changed');
  const prior=JSON.parse(raw);
  if(!equal(prior.revalidated_geography,link.revalidated_geography)||!equal(current.original_geography,prior.original_geography)||!equal(current.source_product_files,prior.source_product_files)||current.records!==prior.records||!equal(current.entities,prior.entities))throw Error('Evidence predecessor changes original claims or territory proofs');
  const previousHash=current.projection?.previous_revalidation_sha256;
  if(previousHash&&previousHash!==link.sha256){
   if(depth===0)throw Error('Current projection is not bound to the exact archived predecessor');
   limits.push('Archived predecessor projection hash differs from its explicit archive link; immutable prior_revalidation bytes govern this legacy link.');
  }
  const priorMigrations=prior.migration_receipts??[];
  if(!equal((current.migration_receipts??[]).slice(0,priorMigrations.length),priorMigrations))throw Error('Evidence migration chronology was replaced');
  checked.push({archive_path:link.archive_path,archive_sha256:link.archive_sha256,raw_sha256:link.sha256});
  seen.add(link.sha256);current=prior;depth++;
 }
 return {validated:true,archived_predecessors:checked,limits,historical_claims_transferred:false};
}
