// Credential-free negative controls at the actual immutable verifier entry point.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {spawnSync,execFileSync} from 'node:child_process';
const commit=process.argv[2],owned='coordination/engineering/release-membership-admission-1150/';
assert.match(commit??'',/^[a-f0-9]{40}$/);
const raw=execFileSync('git',['show',commit+':'+owned+'verify-staging.mjs']);
const run=(code,output,reason)=>{
 const launch='await import('+JSON.stringify('data:text/javascript;base64,'+code.toString('base64'))+');';
 const result=spawnSync(process.execPath,['--input-type=module','-e',launch,commit,output],{encoding:'utf8',env:{PATH:'/usr/bin:/bin',GIT_NO_LAZY_FETCH:'1'}});
 assert.notEqual(result.status,0);assert.match(result.stderr,reason);
 console.log(JSON.stringify({execution_commit:commit,output,expected_error:String(reason),exit_code:result.status}));
};
const sentinel=owned+'verification-fourth.json',before=fs.readFileSync(sentinel);
run(raw,sentinel,/fresh filename/);assert.deepEqual(fs.readFileSync(sentinel),before);
run(raw,owned+'../escaped-output.json',/fresh owned JSON/);
const broken=owned+'owned-negative-dangling-link.json';
fs.symlinkSync('never-created-owned-target',broken);
try{run(raw,broken,/Output symlink refused/);assert.ok(fs.lstatSync(broken).isSymbolicLink());}
finally{fs.unlinkSync(broken);}
const mismatch=owned+'owned-negative-mismatch.json';
run(Buffer.concat([raw,Buffer.from('\n// altered consumed verifier code\n')]),mismatch,/Consumed verifier code differs/);
assert.equal(fs.existsSync(mismatch),false);
