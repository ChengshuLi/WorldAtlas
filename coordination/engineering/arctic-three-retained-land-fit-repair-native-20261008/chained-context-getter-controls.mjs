import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {validateGeometryMigrations,requireValidatedGeometryMigrations} from '../../../scripts/prepare-geographic-release.mjs';
import {footprintHash} from '../../../scripts/check-prepared.mjs';
const source=fs.readFileSync(new URL('../eastern-two-gap-repair-native-20261007/chained-context.mjs',import.meta.url),'utf8');
const block=source.slice(source.indexOf('const successfulContexts=new WeakMap();'),source.indexOf('const executeFile='));
assert(block&&source.includes('return retainSuccessfulContext({receipt:')&&source.includes('}},after,afterIndex);'));
const sha=body=>createHash('sha256').update(body).digest('hex');
const feature=right=>({id:'fixture',properties:{id:'fixture',parent_id:'fixture-parent'},geometry:{type:'Polygon',coordinates:[[[0,0],[right,0],[right,1],[0,1],[0,0]]]}});
const before=[feature(1)],after=[feature(2)],oldHash=footprintHash(before),currentHash=footprintHash(after);
const directory=fs.mkdtempSync(path.resolve('.cache/getter-control-'));
try {
 const receipt={version:1,geometry_stage_validated:true,historical_claims_transferred:false,
  before_footprints_sha256:oldHash,after_footprints_sha256:currentHash,changed_ids:['fixture'],removed_ids:[],added_ids:[],reused_ids:[],
  archives:[{id:'fixture',feature:before[0]}],relationships:[{kind:'source-backed-shared-seam-reference',before_ids:['fixture'],after_ids:['fixture'],history_transfer:false}],
  source_evidence:[{url:'https://example.com/explicit-synthetic-getter-only',source_sha256:'1'.repeat(64)}]};
 const raw=Buffer.from(JSON.stringify(receipt));fs.writeFileSync(path.join(directory,'migration-receipt.json'),raw);
 fs.writeFileSync(path.join(directory,'index.json'),JSON.stringify({before_footprints_sha256:oldHash,after_footprints_sha256:currentHash,history_transfer:false,files:{'migration-receipt.json':{sha256:sha(raw)}}}));
 const brand=validateGeometryMigrations({features:after,baselineIds:['fixture'],baselineFootprints:oldHash,manifestFiles:[path.join(directory,'index.json')]});
 const realm=vm.createContext({assert,sha,AFTER:currentHash,requireValidatedGeometryMigrations});
 vm.runInContext(block.replace('export function','function')+';globalThis.keep=retainSuccessfulContext;globalThis.get=getSuccessfulChainedContext;',realm);
 const rows=Array.from({length:49625},(_,i)=>({id:'fixture-'+i,pixelIndex:i+1,geometry:after[0].geometry}));
 const index={locations:49625,footprints_sha256:currentHash,owner_sha256:'1'.repeat(64)};
 const result={receipt:{status:'verified',migration:{owner_sha256:index.owner_sha256}},geometryValidation:brand,coverageContinuation:{originalGeometryValidation:brand}};
 assert.throws(()=>realm.get(result));assert.throws(()=>realm.get({}));
 assert.throws(()=>realm.keep({...result,geometryValidation:structuredClone(brand)},rows,index));
 assert.throws(()=>realm.keep(result,rows.slice(1),index));
 assert.throws(()=>realm.keep(result,rows,{...index,footprints_sha256:oldHash}));
 assert.strictEqual(realm.keep(result,rows,index),result);
 const actual=realm.get(result);assert.strictEqual(actual.rows,rows);assert.strictEqual(actual.index,index);
 assert(Object.isFrozen(actual.rows)&&Object.isFrozen(actual.rows[0].geometry)&&Object.isFrozen(actual.index));
 assert.throws(()=>realm.get(structuredClone(result)));result.receipt.status='forged';assert.throws(()=>realm.get(result));result.receipt.status='verified';
 assert.strictEqual(realm.get(result).rows,rows);requireValidatedGeometryMigrations(brand);
 console.log(JSON.stringify({positive:2,negative:7,actual_geometry_brand:true,
  fixture:'exact-extracted-private-return-getter-boundary; synthetic rows, not full context replay'}));
} finally {fs.rmSync(directory,{recursive:true,force:true});}
