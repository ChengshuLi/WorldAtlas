import fs from 'node:fs';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
const root='data/engineering/storage-catalog-complete-20261004-a9c2/';
const raw=fs.readFileSync(root+'production-first-01.raw.json');
const original='9bef7434c14a36282e9e0965373c77f1c6ec633335b5b6105332098453b9829c';
const check=bytes=>{
 assert.equal(createHash('sha256').update(bytes).digest('hex'),original);
 const r=JSON.parse(bytes);assert.equal(r.status,'measured');assert.equal(r.source_commit,'6d6bfa8e97d53d702d1d3035c3cb5cd9c3eb369e');assert.equal(r.checks.transaction_read_only,true);assert.equal(r.checks.sql_endpoint_setting_present,true);assert.equal(r.credentials_logged,false);
 assert.equal(r.tables.reduce((n,t)=>n+t.total_bytes,0),r.application_relation_bytes);assert.equal(r.application_relation_bytes+r.other_database_bytes,r.database_bytes);
 assert.equal(r.tables.length,23);assert.equal(r.indexes.length,54);assert.equal(r.provider.billing_usage.status,'unavailable');assert.ok(!/postgres(?:ql)?:\/\//i.test(bytes.toString()));
 return r;
};
check(raw);const damaged=Buffer.from(raw);damaged[damaged.indexOf('1011466240')]=50;assert.throws(()=>check(damaged));
for(const kind of ['positive-control','negative-control'])fs.writeFileSync(root+'retained-'+kind+'-01.json',JSON.stringify({method_id:'retained-capacity-observation',kind,outcome:'passed',checked_at_utc:new Date().toISOString(),source_sha256:original,scope:kind==='positive-control'?'Original full sanitized stdout byte pin and complete target/read-only/accounting metadata conformance; not a new live read or independent raw API response verification.':'Deliberate corruption of physical-byte value rejected by original-byte pin; no mutation/network or source rewriting.'},null,2)+'\n');
