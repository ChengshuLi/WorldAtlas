// One-time rollout proof: compare a genuine full build and assembled output for
// the same selected state. Never substitutes for live consumers.
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import {fileURLToPath} from 'node:url';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {inventoryPackageOutput, committedPackageInputs, committedPackageProgramme,
  admitPackageOutputTransition, validatePackageOutputManifest, streamedPackageFile} from './package-output-artifact.mjs';
import {safePackagePath} from './package-inputs.mjs';
const digest = raw => createHash('sha256').update(raw).digest('hex');

// This is an observational comparison, not a new authority issuer. The existing
// authenticated original manifest and genuine assembly receipt remain required.
// Authenticate the exact consumed selected members as well as source metadata.
// Whole member checks stream through one temporary file, never a package buffer.
function sourceSnapshot(root, head) {
  const env={...process.env,GIT_NO_REPLACE_OBJECTS:'1',GIT_NO_LAZY_FETCH:'1',GIT_TERMINAL_PROMPT:'0'};
  const git = (...args) => execFileSync('git', ['-C', root, ...args], {maxBuffer:32*1048576,env});
  const verifyBody = pin => {
    assert.equal(Number(git('cat-file','-s',pin.git_blob_oid)),pin.bytes,'Consumed delta byte count differs');
    if(pin.sha256===undefined){assert.notEqual(pin.whole_body_consumed,true);return;}
    assert.match(pin.sha256,/^[a-f0-9]{64}$/);assert.equal(pin.whole_body_consumed,true);
    const temporary=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-comparison-'));
    try{
      const disk=fs.statfsSync(temporary);assert.ok(disk.bavail*disk.bsize>=pin.bytes,'Insufficient disk for actual comparison member');
      const fd=fs.openSync(path.join(temporary,'member'),'wx',0o600);
      try{execFileSync('git',['-C',root,'cat-file','blob',pin.git_blob_oid],{env,stdio:['ignore',fd,'pipe']});}
      finally{fs.closeSync(fd);}
      assert.deepEqual(streamedPackageFile(temporary,'member'),{path:'member',bytes:pin.bytes,sha256:pin.sha256},
        'Consumed delta whole body differs');
    }finally{fs.rmSync(temporary,{recursive:true,force:true});}
  };
  const raw=git('show',head+':.github/package-inputs.json'), definition=JSON.parse(raw);
  const descriptor={path:'.github/package-inputs.json',mode:'100644',bytes:raw.length,sha256:digest(raw),
    git_blob:createHash('sha1').update(`blob ${raw.length}\0`).update(raw).digest('hex')};
  assert.equal(git('ls-tree',head,'--',descriptor.path).toString(),
    `100644 blob ${descriptor.git_blob}\t${descriptor.path}\n`,'Declaration must match ordinary immutable source');
  return {git,verifyBody,descriptor,source:{head,tree:git('rev-parse',head+'^{tree}').toString().trim(),definition,
    input_definition_sha256:digest(raw),files:committedPackageInputs(root,definition,head),
    programme:committedPackageProgramme(root,head),selection:JSON.parse(git('show',head+':data/ownership-selection.json'))}};
}
function bindDeclarationTransition({sourceRoot,originalManifest,assembled,originalHead,currentHead,fullContext,assembledContext}) {
  assert.ok(sourceRoot&&originalManifest,'Actual Git source and authenticated original manifest required');
  const raw=fs.readFileSync(originalManifest),manifest=validatePackageOutputManifest(JSON.parse(raw));
  const original=sourceSnapshot(sourceRoot,originalHead),current=sourceSnapshot(sourceRoot,currentHead);
  for(const key of Object.keys(original.source))assert.deepEqual(manifest.source[key],original.source[key],
    'Original manifest source differs from immutable Git: '+key);
  const receipt=JSON.parse(fs.readFileSync(path.join(assembled,'.cache/package-input-build.json'))),assembly=receipt.assembly;
  assert.equal(receipt.kind,'cloudflare');assert.equal(receipt.preflight?.passed,true);
  assert.deepEqual(receipt.preflight.errors,[]);assert.equal(receipt.preflight.inputs?.head,currentHead);
  assert.equal(receipt.input_definition_sha256,current.descriptor.sha256);
  assert.equal(assembly?.kind,'retained-original-output-plus-current-additive');
  assert.equal(assembly.original_manifest_sha256,digest(raw),'Assembly original manifest binding differs');
  assert.equal(assembly.origin?.head,originalHead);
  assert.equal(assembly.current_execution?.source_commit,currentHead);
  assert.equal(assembly.current_execution?.source_tree,current.source.tree);
  assert.equal(assembly.original_base_context_retained,true);
  assert.equal(assembly.base_restoration_invoked,false);assert.equal(assembly.invariant_build_invoked,false);
  assert.ok(Array.isArray(assembly.current_selected_inputs)&&assembly.current_selected_inputs.length>0);
  const pins=new Map();
  for(const pin of assembly.current_selected_inputs){
    assert.match(pin.commit,/^[a-f0-9]{40}$/);assert.ok(safePackagePath(pin.path));
    assert.ok(Number.isSafeInteger(pin.bytes)&&pin.bytes>0);
    assert.equal(current.git('ls-tree',pin.commit,'--',pin.path).toString(),
      `${pin.mode} blob ${pin.git_blob_oid}\t${pin.path}\n`,'Consumed delta differs from immutable source');
    const key=pin.commit+':'+pin.path;if(pins.has(key))assert.deepEqual(pin,pins.get(key),'Conflicting consumed delta descriptor');
    if(!pins.has(key))current.verifyBody(pin);
    pins.set(key,pin);
  }
  const authorized=assembly.current_selected_inputs.filter(pin=>current.source.files.some(row=>
    row.path===pin.path&&row.mode===pin.mode&&row.oid===pin.git_blob_oid)).map(pin=>pin.path);
  const transition=admitPackageOutputTransition(manifest,current.source,authorized);
  assert.deepEqual(assembly.transition,transition,'Assembly delta transition differs');
  for(const [context,snapshot] of [[fullContext,current],[assembledContext,original]]){
    assert.ok(Array.isArray(context.full_code_closure),'Full code closure required');
    assert.equal(new Set(context.full_code_closure.map(row=>row.path)).size,context.full_code_closure.length,
      'Duplicate closure descriptor');
    const matches=context.full_code_closure.filter(row=>row.path==='.github/package-inputs.json');
    assert.equal(matches.length,1,'Exactly one package declaration closure descriptor required');
    assert.deepEqual(matches[0],snapshot.descriptor,'Package declaration descriptor differs from actual source bytes');
  }
  fullContext.full_code_closure=fullContext.full_code_closure.map(row=>row.path==='.github/package-inputs.json'?original.descriptor:row);
  return transition;
}
export function compareSelectedPackageOutput({full,assembled,originalHead,currentHead,sourceRoot,originalManifest}) {
  assert.match(originalHead,/^[a-f0-9]{40}$/);assert.match(currentHead,/^[a-f0-9]{40}$/);
  const before=inventoryPackageOutput(full),after=inventoryPackageOutput(assembled);
  assert.deepEqual(before.files.map(row=>row.path),after.files.map(row=>row.path),'Complete output member sets differ');
  const atlas='dist/client/atlas-geography.json';let exactFiles=0,exactBytes=0;
  for(let index=0;index<before.files.length;index++){
    const a=before.files[index],b=after.files[index];
    if(a.path!==atlas){assert.deepEqual(a,b,'Output bytes differ: '+a.path);exactFiles++;exactBytes+=a.bytes;}
  }
  const read=root=>JSON.parse(fs.readFileSync(path.join(root,atlas)));
  const a=read(full),b=read(assembled);
  assert.equal(a.nativeContextInputStage?.current_execution?.source_head,currentHead,'Full output must record actual current build head');
  assert.equal(b.nativeContextInputStage?.current_execution?.source_head,originalHead,'Assembly must preserve original context head');
  const transition=bindDeclarationTransition({sourceRoot,originalManifest,assembled,originalHead,currentHead,
    fullContext:a.nativeContextInputStage.current_execution,assembledContext:b.nativeContextInputStage.current_execution});
  // Only independently authenticated source head and declaration provenance may
  // differ. All other code, runtime, scientific counters and atlas fields match.
  a.nativeContextInputStage.current_execution.source_head=originalHead;
  assert.deepEqual(a,b,'Atlas content differs beyond preserved original source provenance');
  return {version:1,kind:'actual-full-versus-assembled-output-comparison',original_head:originalHead,current_head:currentHead,
    files:before.files.length,exact_byte_files:exactFiles,exact_bytes:exactBytes,atlas_semantic_equal:true,
    transition,explicit_provenance_differences:['nativeContextInputStage.current_execution.source_head',
      'nativeContextInputStage.current_execution.full_code_closure[.github/package-inputs.json]'],
    limitation:'Authenticated original source/declaration provenance is preserved; every other atlas field and output byte matches.'};
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
  assert.equal(process.argv.length,8,'Usage: node scripts/compare-selected-package-output.mjs FULL_ROOT ASSEMBLED_ROOT ORIGINAL_HEAD CURRENT_HEAD SOURCE_REPO ORIGINAL_MANIFEST');
  console.log(JSON.stringify(compareSelectedPackageOutput({full:process.argv[2],assembled:process.argv[3],originalHead:process.argv[4],currentHead:process.argv[5],sourceRoot:process.argv[6],originalManifest:process.argv[7]})));
}
