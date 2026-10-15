// One-time rollout proof: compare a genuine full build and assembled output for
// the same selected state. Never substitutes for live consumers.
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import {fileURLToPath} from 'node:url';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {inventoryPackageOutput, committedPackageInputs, committedPackageProducer,
  admitPackageOutputTransition, inertSelectedPackageInput, validatePackageOutputManifest, streamedPackageFile} from './package-output-artifact.mjs';
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
    producer:committedPackageProducer(root,head),selection:JSON.parse(git('show',head+':data/ownership-selection.json'))}};
}
export function normalizeDeclarationReadAccounting(fullStage, assembledStage, currentDescriptor, originalDescriptor) {
  // The qualified consumer reads this unique issued code descriptor once via
  // its ordinary reader. Its bytes contribute to encoded reads, not decoded
  // scientific payload. Keep both original observations; normalize only a copy.
  for (const [stage, descriptor] of [[fullStage,currentDescriptor],[assembledStage,originalDescriptor]]) {
    assert.ok(Number.isSafeInteger(descriptor.bytes) && descriptor.bytes > 0);
    assert.ok(Number.isSafeInteger(stage.consumed_input_bytes?.encoded) &&
      stage.consumed_input_bytes.encoded >= descriptor.bytes, 'Invalid actual encoded input accounting');
  }
  const currentRemainder=fullStage.consumed_input_bytes.encoded-currentDescriptor.bytes;
  const originalRemainder=assembledStage.consumed_input_bytes.encoded-originalDescriptor.bytes;
  assert.equal(currentRemainder,originalRemainder,'Consumed bytes differ beyond the authenticated declaration read');
  const normalized=structuredClone(fullStage);
  normalized.consumed_input_bytes.encoded=assembledStage.consumed_input_bytes.encoded;
  return {normalized, accounting:{original_declaration_bytes:originalDescriptor.bytes,
    current_declaration_bytes:currentDescriptor.bytes, unchanged_other_encoded_bytes:originalRemainder}};
}

function bindDeclarationTransition({sourceRoot,originalManifest,assembled,originalHead,currentHead,fullContext,assembledContext,trustedBase}) {
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
  const extra=current.source.definition.inputs.slice(manifest.source.definition.inputs.length)
    .filter(name=>!inertSelectedPackageInput(name));
  let acceptedInputs;
  if(extra.length){
    // Observer authority is supplied by its authenticated frozen invocation,
    // never by a field asserted in the assembly receipt being inspected.
    assert.match(trustedBase??'',/^[a-f0-9]{40}$/,'Exact trusted comparison base required');
    acceptedInputs={commit:trustedBase,files:extra.map(name=>{
      assert.ok(safePackagePath(name)&&!name.endsWith('/'));
      const row=current.git('ls-tree','-l',trustedBase,'--',name).toString();
      const match=/^100644 blob ([a-f0-9]{40})\s+(\d+)\t([^\n]+)\n$/.exec(row);
      assert.ok(match&&match[3]===name,'Ordinary unchanged trusted comparison input required');
      return {path:name,mode:'100644',oid:match[1],bytes:Number(match[2])};
    })};
  }
  const transition=admitPackageOutputTransition(manifest,current.source,{acceptedInputs,typedInputs:assembly.current_selected_inputs});
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
  return {transition,originalDescriptor:original.descriptor,currentDescriptor:current.descriptor};
}
export function compareSelectedPackageOutput({full,assembled,originalHead,currentHead,sourceRoot,originalManifest,trustedBase}) {
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
  const binding=bindDeclarationTransition({sourceRoot,originalManifest,assembled,originalHead,currentHead,
    fullContext:a.nativeContextInputStage.current_execution,assembledContext:b.nativeContextInputStage.current_execution,trustedBase});
  // Only independently authenticated source head and declaration provenance may
  // differ. Only its exact encoded read delta is normalized; scientific bytes and all other fields match.
  const {normalized,accounting}=normalizeDeclarationReadAccounting(a.nativeContextInputStage,b.nativeContextInputStage,
    binding.currentDescriptor,binding.originalDescriptor);
  a.nativeContextInputStage=normalized;
  a.nativeContextInputStage.current_execution.source_head=originalHead;
  assert.deepEqual(a,b,'Atlas content differs beyond preserved original source provenance');
  return {version:1,kind:'actual-full-versus-assembled-output-comparison',original_head:originalHead,current_head:currentHead,
    files:before.files.length,exact_byte_files:exactFiles,exact_bytes:exactBytes,atlas_semantic_equal:true,
    transition:binding.transition,declaration_read_accounting:accounting,explicit_provenance_differences:['nativeContextInputStage.current_execution.source_head',
      'nativeContextInputStage.current_execution.full_code_closure[.github/package-inputs.json]',
      'nativeContextInputStage.consumed_input_bytes.encoded[authenticated declaration bytes]'],
    limitation:'Authenticated original source/declaration provenance is preserved; every other atlas field and output byte matches.'};
}
// The queue already records exhaustive actual output hashes. A genuine full
// reference need not be downloaded or rebuilt merely to compare its bytes.
// The caller must authenticate this existing readback through its run/job/log/
// artifact chain. This function cannot issue original-package reuse authority.
export function compareSelectedPackageReadback({assembled,readback,originalHead,currentHead,sourceRoot,originalManifest,trustedBase}) {
  assert.equal(readback.kind,'ordinary-cloudflare-built-output-readback');
  assert.equal(readback.head,currentHead,'Full readback must belong to actual current source');
  assert.match(originalHead,/^[a-f0-9]{40}$/);assert.match(currentHead,/^[a-f0-9]{40}$/);
  const current=inventoryPackageOutput(assembled),expected=[];
  for(const [prefix,rows] of [['client',readback.static_assets?.files],['cloudflare',readback.worker_bundle_files]]){
    assert.ok(Array.isArray(rows)&&rows.length>0,'Complete actual reference inventory required');
    for(const row of rows){
      assert.ok(safePackagePath(row.path)&&!row.path.endsWith('/'));
      assert.ok(Number.isSafeInteger(row.bytes)&&row.bytes>=0);assert.match(row.sha256,/^[a-f0-9]{64}$/);
      assert.deepEqual(Object.keys(row).sort(),['bytes','path','sha256']);
      expected.push({...row,path:'dist/'+prefix+'/'+row.path});
    }
  }
  assert.equal(new Set(expected.map(row=>row.path)).size,expected.length,'Duplicate reference output member');
  assert.equal(readback.static_assets.count,readback.static_assets.files.length);
  assert.equal(readback.static_assets.bytes,readback.static_assets.files.reduce((sum,row)=>sum+row.bytes,0));
  expected.sort((a,b)=>a.path.localeCompare(b.path,'en'));
  assert.deepEqual(current.files.map(row=>row.path),expected.map(row=>row.path),'Complete output member sets differ');
  const atlasPath='dist/client/atlas-geography.json',atlas=JSON.parse(fs.readFileSync(path.join(assembled,atlasPath)));
  assert.equal(atlas.nativeContextInputStage?.current_execution?.source_head,originalHead);
  assert.equal(readback.nativeContextInputStage?.current_execution?.source_head,currentHead);
  const originalCurrentStage=structuredClone(readback.nativeContextInputStage),normalizedStage=structuredClone(originalCurrentStage);
  const binding=bindDeclarationTransition({sourceRoot,originalManifest,assembled,originalHead,currentHead,
    fullContext:normalizedStage.current_execution,assembledContext:atlas.nativeContextInputStage.current_execution,trustedBase});
  const {normalized:accountedStage,accounting}=normalizeDeclarationReadAccounting(normalizedStage,atlas.nativeContextInputStage,
    binding.currentDescriptor,binding.originalDescriptor);
  accountedStage.current_execution.source_head=originalHead;
  assert.deepEqual(accountedStage,atlas.nativeContextInputStage,'Scientific context differs beyond authenticated provenance');
  // Preserve the builder's actual compact JSON ordering. A different field,
  // order, encoding or value fails the full reference's exact SHA-256 check.
  atlas.nativeContextInputStage=originalCurrentStage;
  const normalized=Buffer.from(JSON.stringify(atlas));let exactBytes=0;
  for(let index=0;index<current.files.length;index++){
    const actual=current.files[index],reference=expected[index];
    if(actual.path===atlasPath)assert.deepEqual({path:atlasPath,bytes:normalized.length,sha256:digest(normalized)},reference,
      'Complete atlas bytes differ beyond authenticated provenance');
    else{assert.deepEqual(actual,reference,'Output bytes differ: '+actual.path);exactBytes+=actual.bytes;}
  }
  return {version:1,kind:'actual-full-readback-versus-assembled-output-comparison',original_head:originalHead,current_head:currentHead,
    files:current.files.length,exact_byte_files:current.files.length-1,exact_bytes:exactBytes,
    atlas_exact_after_authenticated_provenance:true,transition:binding.transition,declaration_read_accounting:accounting,
    explicit_provenance_differences:['nativeContextInputStage.current_execution.source_head',
      'nativeContextInputStage.current_execution.full_code_closure[.github/package-inputs.json]',
      'nativeContextInputStage.consumed_input_bytes.encoded[authenticated declaration bytes]'],
    limitation:'Uses authenticated exhaustive full-build readback; no additional full build or inherited consumer claim is made.'};
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
  assert.equal(process.argv.length,8,'Usage: node scripts/compare-selected-package-output.mjs FULL_ROOT ASSEMBLED_ROOT ORIGINAL_HEAD CURRENT_HEAD SOURCE_REPO ORIGINAL_MANIFEST');
  console.log(JSON.stringify(compareSelectedPackageOutput({full:process.argv[2],assembled:process.argv[3],originalHead:process.argv[4],currentHead:process.argv[5],sourceRoot:process.argv[6],originalManifest:process.argv[7],trustedBase:process.env.SELECTED_PACKAGE_TRUSTED_BASE})));
}
