import test from 'node:test';
import assert from 'node:assert/strict';
import {generateKeyPairSync,createHash} from 'node:crypto';
import {backupRecipientFingerprint,sealRecoveryBackup,openRecoveryBackup} from '../scripts/recovery-backup-envelope.mjs';
const keys=generateKeyPairSync('rsa',{modulusLength:3072,publicKeyEncoding:{type:'spki',format:'pem'},privateKeyEncoding:{type:'pkcs8',format:'pem'}});
const context={purpose:'worldatlas-private-sql-backup',repository:'ChengshuLi/WorldAtlas',primary_main_commit:'a'.repeat(40),run_id:'1',run_attempt:'1',window_comment_id:'2',source_fingerprint:'b'.repeat(64),project_id:'weathered-lab-37571695',branch_id:'br-summer-butterfly-ar8qikk5'};
const bytes=Buffer.from('PGDMP synthetic fixture: private raw historical strings');
const sealed=()=>sealRecoveryBackup({bytes,publicKey:keys.publicKey,context});
const open=(value,expectedContext=context)=>openRecoveryBackup({...value,privateKey:keys.privateKey,expectedContext});
test('private backup round trips exact bytes with pinned recipient and no plaintext envelope',()=>{
 const value=sealed();assert.deepEqual(open(value),bytes);assert.equal(value.envelope.recipient_sha256,backupRecipientFingerprint(keys.publicKey));assert.equal(JSON.stringify(value.envelope).includes('private raw'),false);assert.equal(value.ciphertext.includes(bytes),false);
});
test('fresh randomness prevents identical backup ciphertext',()=>assert.notDeepEqual(sealed().ciphertext,sealed().ciphertext));
for(const field of ['primary_main_commit','run_id','window_comment_id','source_fingerprint'])test(`rejects replay under a different ${field}`,()=>assert.throws(()=>open(sealed(),{...context,[field]:field.includes('commit')?'c'.repeat(40):field.includes('fingerprint')?'c'.repeat(64):'99'})));
for(const field of ['tag','iv','wrapped_key'])test(`rejects corrupted ${field}`,()=>{
 const value=sealed(),raw=Buffer.from(value.envelope[field],'base64');raw[0]^=1;value.envelope[field]=raw.toString('base64');assert.throws(()=>open(value));
});
test('ciphertext integrity survives attacker replacing the unauthenticated ciphertext digest',()=>{
 const value=sealed();value.ciphertext[0]^=1;value.envelope.ciphertext_sha256=createHash('sha256').update(value.ciphertext).digest('hex');assert.throws(()=>open(value));
});
test('rejects truncated ciphertext',()=>{const value=sealed();value.ciphertext=value.ciphertext.subarray(1);assert.throws(()=>open(value));});
test('rejects unauthenticated original byte hash',()=>{const value=sealed();value.envelope.plaintext_sha256='c'.repeat(64);assert.throws(()=>open(value));});
test('rejects envelope fields outside the reviewed contract',()=>{const value=sealed();value.envelope.extra=true;assert.throws(()=>open(value));});
test('rejects weak recipient before encrypting private data',()=>{const weak=generateKeyPairSync('rsa',{modulusLength:2048,publicKeyEncoding:{type:'spki',format:'pem'}});assert.throws(()=>sealRecoveryBackup({bytes,publicKey:weak.publicKey,context}));});
test('rejects non-native dump bytes',()=>assert.throws(()=>sealRecoveryBackup({bytes:Buffer.from('plain JSON'),publicKey:keys.publicKey,context})));
test('rejects a different recipient key',()=>{const other=generateKeyPairSync('rsa',{modulusLength:3072,privateKeyEncoding:{type:'pkcs8',format:'pem'}});assert.throws(()=>openRecoveryBackup({...sealed(),privateKey:other.privateKey,expectedContext:context}));});

test('refuses private PEM in the public recipient field',()=>assert.throws(()=>backupRecipientFingerprint(keys.privateKey)));
