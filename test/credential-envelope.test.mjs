import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {createHash,generateKeyPairSync} from 'node:crypto';
import {spawnSync} from 'node:child_process';
import {encryptCredentialEnvelope,decryptCredentialEnvelope,deliverCredentialFile,credentialEnvelopeLimits,credentialRecipientFingerprint} from '../scripts/credential-envelope.mjs';

// Synthetic keys exist only for isolated tests. No production recipient key or
// real Neon password is generated, fetched or persisted by this suite.
const pair=()=>generateKeyPairSync('rsa',{modulusLength:3072,publicKeyEncoding:{type:'spki',format:'pem'},privateKeyEncoding:{type:'pkcs8',format:'pem'}}),recipient=pair(),other=pair();
const now=Date.parse('2026-10-02T12:00:00.000Z');
const context={purpose:'worldatlas-runtime-database-url',repository:'ChengshuLi/WorldAtlas',workflow_path:'.github/workflows/neon-production-cutover.yml',commit_sha:'a'.repeat(40),run_id:'123456789',run_attempt:'1',project_id:'weathered-lab-37571695',branch_id:'br-test-only-branch',endpoint_host:'ep-test-only.us-east-1.aws.neon.tech',database_name:'neondb',role_name:'worldatlas_app',source_manifest_sha256:'1'.repeat(64),schema_sha256:'2'.repeat(64),runtime_role_sql_sha256:'3'.repeat(64),issued_at_utc:new Date(now).toISOString(),expires_at_utc:new Date(now+3600000).toISOString()};
const credential='postgresql://worldatlas_app:synthetic-test-password-not-a-real-account@ep-test-only-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require';
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const encrypt=(extra={})=>encryptCredentialEnvelope({credential,publicKey:recipient.publicKey,context,now,...extra});
const decrypt=(envelope,extra={})=>decryptCredentialEnvelope({envelope,privateKey:recipient.privateKey,expectedContext:context,now,...extra});
function altered(value){const bytes=Buffer.from(value,'base64url');bytes[0]^=1;return bytes.toString('base64url');}

test('standard envelope roundtrip uses fresh randomness, authenticated context and no plaintext fields',()=>{
 const first=encrypt(),second=encrypt();assert.equal(first.recipient_sha256,credentialRecipientFingerprint(recipient.publicKey));assert.notEqual(first.recipient_sha256,credentialRecipientFingerprint(other.publicKey));assert.equal(first.suite,'RSA-OAEP-256+A256GCM');assert.notEqual(first.iv,second.iv);assert.notEqual(first.wrapped_key,second.wrapped_key);assert.notEqual(first.ciphertext,second.ciphertext);assert.ok(!JSON.stringify(first).includes(credential));assert.ok(!JSON.stringify(first).includes('synthetic-test-password'));assert.deepEqual(decrypt(first),Buffer.from(credential));assert.deepEqual(decrypt(JSON.stringify(first)),Buffer.from(credential));
});
test('tampered ciphertext, authentication tag, IV, wrapped key and recipient are rejected',()=>{
 const encrypted=encrypt();for(const field of ['ciphertext','tag','iv','wrapped_key'])assert.throws(()=>decrypt({...encrypted,[field]:altered(encrypted[field])}),/validation|delivery/);assert.throws(()=>decrypt({...encrypted,recipient_sha256:'b'.repeat(64)}));assert.throws(()=>decrypt(encrypted,{privateKey:other.privateKey}));assert.throws(()=>decrypt({...encrypted,context:{...context,project_id:'forged-project'}}));assert.throws(()=>decrypt(encrypted,{expectedContext:{...context,commit_sha:'c'.repeat(40)}}));assert.throws(()=>decrypt(encrypted,{expectedContext:{...context,run_attempt:'2'}}));assert.throws(()=>decrypt(encrypted,{expectedContext:{...context,source_manifest_sha256:'4'.repeat(64)}}));
});
test('malformed or oversized envelopes, unapproved algorithms and invalid intervals fail closed',()=>{
 const encrypted=encrypt();for(const value of ['{','[]','null','x'.repeat(credentialEnvelopeLimits.envelope_bytes+1),{...encrypted,version:2},{...encrypted,suite:'legacy'},{...encrypted,tag:encrypted.tag+'='},{...encrypted,iv:'AA'},{...encrypted,ciphertext:''},{...encrypted,unexpected:'field'}])assert.throws(()=>decrypt(value));assert.throws(()=>decrypt(encrypted,{now:now+3600000}));assert.throws(()=>encrypt({context:{...context,expires_at_utc:new Date(now+credentialEnvelopeLimits.max_lifetime_ms+1).toISOString()}}));assert.throws(()=>encrypt({context:{...context,issued_at_utc:new Date(now+credentialEnvelopeLimits.clock_skew_ms+1).toISOString()}}));assert.throws(()=>encrypt({context:{...context,role_name:'neondb_owner'}}));assert.throws(()=>encrypt({credential:'x'.repeat(credentialEnvelopeLimits.credential_bytes+1)}));
});
test('owner credentials, other endpoints, missing TLS and non-RSA keys cannot be transported',()=>{
 for(const value of [credential.replace('worldatlas_app:','neondb_owner:'),credential.replace('ep-test-only-pooler','ep-unapproved'),credential.replace('sslmode=require','sslmode=disable'),credential+'#fragment','NEON_API_KEY=not-transported'])assert.throws(()=>encrypt({credential:value}));const ec=generateKeyPairSync('ec',{namedCurve:'prime256v1',publicKeyEncoding:{type:'spki',format:'pem'}});assert.throws(()=>encrypt({publicKey:ec.publicKey}));
});
test('private delivery writes owner-only outside-Git file and refuses wrong digest, unsafe permissions, symlinks and overwrite',()=>{
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-envelope-test-'));try{
  const keyFile=path.join(root,'synthetic-private.pem'),envelopeFile=path.join(root,'envelope.json'),outputFile=path.join(root,'runtime-secret'),bytes=Buffer.from(JSON.stringify(encrypt())+'\n');fs.writeFileSync(keyFile,recipient.privateKey,{mode:0o600});fs.writeFileSync(envelopeFile,bytes);const args={envelopeFile,privateKeyFile:keyFile,expectedContext:context,envelopeSHA256:sha(bytes),outputFile,now};
  assert.throws(()=>deliverCredentialFile({...args,envelopeSHA256:'f'.repeat(64)}));assert.equal(fs.existsSync(outputFile),false);fs.chmodSync(keyFile,0o644);assert.throws(()=>deliverCredentialFile(args));fs.chmodSync(keyFile,0o600);const link=path.join(root,'private-link');fs.symlinkSync(keyFile,link);assert.throws(()=>deliverCredentialFile({...args,privateKeyFile:link}));
  const repo=path.join(root,'repository');fs.mkdirSync(repo);fs.mkdirSync(path.join(repo,'.git'));assert.throws(()=>deliverCredentialFile({...args,outputFile:path.join(repo,'runtime-secret')}));assert.equal(fs.existsSync(path.join(repo,'runtime-secret')),false);
  const receipt=deliverCredentialFile(args);assert.equal(receipt.credential_logged,false);assert.equal(fs.statSync(outputFile).mode&0o777,0o600);assert.equal(fs.readFileSync(outputFile,'utf8'),credential);assert.ok(!JSON.stringify(receipt).includes(credential));assert.throws(()=>deliverCredentialFile(args));assert.equal(fs.readFileSync(outputFile,'utf8'),credential);
 }finally{fs.rmSync(root,{recursive:true,force:true});}
});
test('CLI encryption/decryption returns metadata only and failures never print plaintext or key material',()=>{
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-envelope-cli-test-'));try{
  const publicFile=path.join(root,'synthetic-public.pem'),privateFile=path.join(root,'synthetic-private.pem'),contextFile=path.join(root,'context.json'),envelopeFile=path.join(root,'envelope.json'),outputFile=path.join(root,'runtime-secret');fs.writeFileSync(publicFile,recipient.publicKey);fs.writeFileSync(privateFile,recipient.privateKey,{mode:0o600});const current=Date.now(),liveContext={...context,issued_at_utc:new Date(current).toISOString(),expires_at_utc:new Date(current+3600000).toISOString()};fs.writeFileSync(contextFile,JSON.stringify(liveContext));const script=new URL('../scripts/credential-envelope.mjs',import.meta.url).pathname;
  const encrypted=spawnSync(process.execPath,[script,'encrypt','--public-key',publicFile,'--context',contextFile,'--output',envelopeFile],{env:{...process.env,ATLAS_RUNTIME_DATABASE_URL:credential},encoding:'utf8'});assert.equal(encrypted.status,0,encrypted.stderr);assert.equal(JSON.parse(encrypted.stdout).status,'encrypted');const digest=JSON.parse(encrypted.stdout).envelope_sha256;
  const decrypted=spawnSync(process.execPath,[script,'decrypt','--private-key',privateFile,'--context',contextFile,'--envelope',envelopeFile,'--expected-sha256',digest,'--output',outputFile],{encoding:'utf8'});assert.equal(decrypted.status,0,decrypted.stderr);assert.equal(JSON.parse(decrypted.stdout).status,'delivered');assert.equal(fs.readFileSync(outputFile,'utf8'),credential);const denied=spawnSync(process.execPath,[script,'decrypt','--private-key',privateFile,'--context',contextFile,'--envelope',envelopeFile,'--expected-sha256','f'.repeat(64),'--output',path.join(root,'must-not-exist')],{encoding:'utf8'});assert.equal(denied.status,1);
  for(const text of [encrypted.stdout,encrypted.stderr,decrypted.stdout,decrypted.stderr,denied.stdout,denied.stderr]){assert.ok(!text.includes(credential));assert.ok(!text.includes('synthetic-test-password'));assert.ok(!text.includes('PRIVATE KEY'));}assert.equal(fs.existsSync(path.join(root,'must-not-exist')),false);
 }finally{fs.rmSync(root,{recursive:true,force:true});}
});
