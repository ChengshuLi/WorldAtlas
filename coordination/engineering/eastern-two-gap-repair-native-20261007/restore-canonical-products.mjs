// Exact accepted whole-byte restoration before the existing offline readers.
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {restoreWholeImage} from './whole-image.mjs';
import {applyBytePatch,verifyWholeBytes} from './byte-patch.mjs';
import {gzipSync,gunzipSync} from 'node:zlib';

const sha = raw => createHash('sha256').update(raw).digest('hex');
const CAP = 32 * 1024 * 1024;
const canonicalIndex = '1dad6b42f55a2291a6884f302b31308d9b4323daf4536fc93a41efc7dee1695d';
const priorIndex = 'ca1ab5fc3ef24470bcb79412f1d47a88281c6df0931461c5eb356079b75986fe';
const originalCanonicalTransport = '3a343812f25b02f4472dbe5338a72e9541e4de180b916e0cf8bbc9a00464f097';
const originalPriorTransport = '7c555e617c6843b070a0799088420ff535f210c2cf8d795b437230d79402c916';
const originalPriorIndex = 'e34743a84df2aaaa668b4e7b23c4f6870379edfe7eb88a427d6005b47333a393';
const namespace = 'coordination/engineering/eastern-two-gap-repair-native-20261007';
const safe = value => typeof value === 'string' && !path.isAbsolute(value) &&
  !value.includes('\\') && !value.includes('\0') && value.split('/').every(x => x && x !== '.' && x !== '..');

function ordinary(root, relative) {
  assert(safe(relative) && path.isAbsolute(root) && fs.realpathSync(root) === root);
  let current = root;
  for (const piece of relative.split('/')) {
    current = path.join(current, piece);
    let stat;
    try { stat = fs.lstatSync(current); } catch (error) { if (error.code !== 'ENOENT') throw error; }
    if (stat) assert(!stat.isSymbolicLink(), 'Nonordinary canonical ancestor');
  }
  return current;
}
function read(root, pin) {
  assert(Number.isSafeInteger(pin.bytes) && pin.bytes >= 0 && pin.bytes <= CAP);
  const file = ordinary(root, pin.path), stat = fs.lstatSync(file);
  assert(stat.isFile() && stat.size === pin.bytes);
  if(pin.mode!==undefined)assert.equal((stat.mode&0o111)?'100755':'100644',pin.mode,'Whole file mode differs');
  const fd = fs.openSync(file, 'r');
  try {
    assert.equal(fs.fstatSync(fd).size, pin.bytes);
    const raw = Buffer.alloc(pin.bytes + 1); let offset = 0;
    while (offset < raw.length) {
      const n = fs.readSync(fd, raw, offset, raw.length - offset, null);
      if (!n) break;
      offset += n;
    }
    assert.equal(offset, pin.bytes, 'Actual canonical EOF differs');
    assert.equal(fs.readSync(fd, Buffer.alloc(1), 0, 1, null), 0);
    const result = raw.subarray(0, offset);
    assert.equal(sha(result), pin.sha256);
    assert.equal((stat.mode & 0o111) ? '100755' : '100644', pin.mode);
    return result;
  } finally { fs.closeSync(fd); }
}
function copy(root, target, source, pin, original = null) {
  assert(safe(target) && ['100644', '100755'].includes(pin.mode));
  read(source, pin);
  const destination = ordinary(root, target);
  fs.mkdirSync(path.dirname(destination), {recursive: true});
  assert.equal(fs.realpathSync(path.dirname(destination)), path.dirname(destination));
  if (fs.existsSync(destination)) {
    assert(fs.lstatSync(destination).isFile());
    let accepted = false;
    for (const expected of [pin, original].filter(Boolean)) {
      try { read(root, {...expected, path: target}); accepted = true; break; } catch {}
    }
    assert(accepted, 'Existing canonical body is neither the exact original nor reviewed successor');
  }
  fs.copyFileSync(path.join(source, pin.path), destination, fs.constants.COPYFILE_FICLONE);
  read(root, {...pin, path: target});
}


function readIndexObject(root,name,expectedSha) {
  const file=ordinary(root,name),stat=fs.lstatSync(file);
  const raw=read(root,{path:name,bytes:stat.size,sha256:expectedSha,mode:'100644'});
  return JSON.parse(raw);
}
function writeExactObject(root,pin,body) {
  verifyWholeBytes(body,pin);
  const file=ordinary(root,pin.path);
  if(fs.existsSync(file)){read(root,pin);return;}
  fs.mkdirSync(path.dirname(file),{recursive:true});
  assert.equal(fs.realpathSync(path.dirname(file)),path.dirname(file));
  fs.writeFileSync(file,body,{flag:'wx',mode:pin.mode==='100755'?0o755:0o644});read(root,pin);
}
function restoreByteDerivedObjects(canonical,prior,map,old,images) {
  const imageRead=(root,name)=>{const pins=images.get(root).files.filter(p=>p.path===name);assert.equal(pins.length,1);return read(root,pins[0]);};
  const originalCanonical=readIndexObject(canonical,'original-canonical-transport-index.json',originalCanonicalTransport);
  const originalPrior=readIndexObject(prior,'original-prior-transport-index.json',originalPriorTransport);
  const originalV1=readIndexObject(prior,'original-v1-transport-index.json',originalPriorIndex);
  assert.deepEqual(old.original_index,originalV1,'Complete original v1 index fields differ');
  const priorPaths=new Map(old.logical_targets.map(p=>[p.path,p]));
  assert.equal(priorPaths.size,old.logical_targets.length);
  const sourceBodies=new Map();
  const relationRaw=imageRead(prior,'world-byte-relations.json');
  assert(relationRaw.length<=CAP);
  const relations=JSON.parse(relationRaw).all_original_world_files;
  const expectedWorld=old.logical_targets.filter(p=>p.path.startsWith('data/geography/part-'));
  assert.equal(relations.length,expectedWorld.length);
  assert.deepEqual(relations.map(p=>p.original_whole_binding.path).sort(),expectedWorld.map(p=>p.path).sort());
  for(const relation of relations) {
    const expected=priorPaths.get(relation.original_whole_binding.path);
    assert.deepEqual(relation.original_whole_binding,expected);
    assert.equal(relation.original_object,expected.object);
    const wire=read(prior,{path:relation.patch_path,bytes:relation.patch_encoded_bytes,sha256:relation.patch_encoded_sha256,mode:'100644'});
    assert(Number.isSafeInteger(relation.patch_decoded_bytes)&&relation.patch_decoded_bytes<=CAP);
    const decoded=gunzipSync(wire,{maxOutputLength:CAP});
    assert.equal(decoded.length,relation.patch_decoded_bytes);assert.equal(sha(decoded),relation.patch_decoded_sha256);
    const patch=JSON.parse(decoded);
    for(const key of ['path','bytes','sha256','mode'])assert.equal(patch[key],expected[key]);
    assert(Array.isArray(patch.sources));
    const sources=new Map(patch.sources.map(p=>[p.object,p]));assert.equal(sources.size,patch.sources.length);
    const source=name=>{
      const declaration=sources.get(name);assert(declaration);
      const original=priorPaths.get(declaration.path);assert(original);
      assert.equal(original.object,name);assert.equal(original.bytes,declaration.encoded_bytes);
      assert.equal(original.sha256,declaration.encoded_sha256);assert.equal(original.mode,declaration.mode);
      if(!sourceBodies.has(name)) {
        const encoded=read(prior,{...original,path:name});
        const body=gunzipSync(encoded,{maxOutputLength:CAP});
        assert.equal(body.length,declaration.decoded_bytes);assert.equal(sha(body),declaration.decoded_sha256);
        sourceBodies.set(name,body);
      }
      const body=sourceBodies.get(name);assert.equal(body.length,declaration.decoded_bytes);assert.equal(sha(body),declaration.decoded_sha256);
      return body;
    };
    const body=applyBytePatch(patch.commands,expected,source);
    writeExactObject(prior,{...expected,path:expected.object},body);
    // A later whole-file patch authenticates and reloads its own complete source
    // bodies. Retaining every decoded context across all34 files is unnecessary.
    sourceBodies.clear();
  }
  sourceBodies.clear();
  const planWire=imageRead(canonical,'current-context-byte-patch.json.gz');
  assert(planWire.length<=CAP);
  const plan=JSON.parse(gunzipSync(planWire,{maxOutputLength:CAP}));
  const original=priorPaths.get(plan.original_source.path);assert.deepEqual(plan.original_source,original);
  const beforeWire=read(prior,{...original,path:original.object});
  const before=gunzipSync(beforeWire,{maxOutputLength:CAP});
  assert.equal(before.length,plan.before_decoded_bytes);assert.equal(sha(before),plan.before_decoded_sha256);
  const commands=plan.commands.map(c=>Object.hasOwn(c,'copy')?{copy:['original',...c.copy]}:c);
  const after=applyBytePatch(commands,{bytes:plan.after_decoded_bytes,sha256:plan.after_decoded_sha256,mode:'100644'},name=>{assert.equal(name,'original');return before;});
  const changedWire=gzipSync(after,{level:9});
  verifyWholeBytes(changedWire,plan.current_member);
  const targets=new Map(map.logical_targets.map(p=>[p.target,p]));
  const contextPin=targets.get('data/canonical-grid/eastern-v8/context-transport/index.json');assert(contextPin);
  const contextIndex=JSON.parse(read(canonical,{...contextPin,path:contextPin.object}));
  assert.equal(contextIndex.files.length,34);assert.equal(new Set(contextIndex.files.map(p=>p.path)).size,34);
  assert(Number.isSafeInteger(contextIndex.whole_bytes)&&contextIndex.whole_bytes<=CAP);
  const originalByHash=new Map(old.logical_targets.map(p=>[p.sha256,p]));let offset=0,changes=0;
  const members=contextIndex.files.map(pin=>{
    assert.equal(pin.offset,offset);assert(pin.mode==='100644');let encoded;
    if(pin.sha256===plan.current_member.sha256){encoded=changedWire;changes++;}
    else {const source=originalByHash.get(pin.sha256);assert(source);assert.equal(source.mode,pin.mode);encoded=read(prior,{...source,path:source.object});}
    verifyWholeBytes(encoded,pin);offset+=encoded.length;assert(offset<=contextIndex.whole_bytes);return encoded;
  });
  assert.equal(changes,1);assert.equal(offset,contextIndex.whole_bytes);
  const whole=Buffer.concat(members,offset);assert.equal(sha(whole),contextIndex.whole_sha256);
  offset=0;
  for(const part of contextIndex.parts) {
    assert.equal(part.offset,offset);assert(Number.isSafeInteger(part.decoded_bytes)&&part.decoded_bytes>0&&part.decoded_bytes<=16*1024*1024);
    const decoded=whole.subarray(offset,offset+part.decoded_bytes);assert.equal(decoded.length,part.decoded_bytes);
    assert.equal(sha(decoded),part.decoded_sha256);offset+=decoded.length;
    const encoded=gzipSync(decoded,{level:9}),target=targets.get('data/canonical-grid/eastern-v8/context-transport/'+part.path);assert(target);
    assert.equal(encoded.length,part.bytes);assert.equal(sha(encoded),part.sha256);
    writeExactObject(canonical,{...target,path:target.object},encoded);
  }
  assert.equal(offset,whole.length);
  // Check every original physical image object after the inverse, including maps.
  for(const [root,index] of [[canonical,originalCanonical],[prior,originalPrior]])
    for(const pin of index.files)read(root,pin);
  return {original_world_files:expectedWorld.length,current_context_members:34,
    original_canonical_index_sha256:originalCanonicalTransport,original_prior_index_sha256:originalPriorTransport,
    all_original_image_whole_bodies_and_modes_verified:true,scientific_producers_invoked:false};
}

const restored = new Map();
export function restoreCanonicalProducts({root, temporaryRoot, mode = 'package'}) {
  assert(['package','checkout'].includes(mode),'Unknown canonical preparation boundary');
  if(mode==='package')assert.equal(root,process.env.WORLDATLAS_PACKAGE_STAGE,'Restoration requires the explicit normal package source image');
  else {
    assert.equal(root,process.cwd(),'Checkout preparation requires the actual explicit current checkout');
    assert.equal(process.env.WORLDATLAS_PACKAGE_STAGE,undefined,'Checkout preparation cannot spoof a package stage');
    const gitMarker=ordinary(root,'.git');
    assert(fs.existsSync(gitMarker)&&!fs.lstatSync(gitMarker).isSymbolicLink(),'Checkout preparation requires an actual Git checkout');
  }
  if (restored.has(root)) return getRestoredCanonicalProducts(root);
  assert(path.isAbsolute(root) && fs.realpathSync(root) === root);
  assert(path.isAbsolute(temporaryRoot) && fs.realpathSync(temporaryRoot) === temporaryRoot);
  const temporary = fs.mkdtempSync(path.join(temporaryRoot, '1295-canonical-'));
  const canonical = path.join(temporary, 'canonical-objects');
  const prior = path.join(temporary, 'prior-objects');
  const priorImage = path.join(temporary, 'original-v1-image');
  const canonicalImage=restoreWholeImage(path.join(root, namespace, 'canonical-products'), canonical, {expectedIndexSha: canonicalIndex});
  const priorImageIndex=restoreWholeImage(path.join(root, namespace, 'prior-v1'), prior, {expectedIndexSha: priorIndex});
  const imageMember=(image,name)=>{const pins=image.files.filter(p=>p.path===name);assert.equal(pins.length,1);return pins[0];};
  const map = JSON.parse(read(canonical,imageMember(canonicalImage,'canonical-path-map.json')));
  const old = JSON.parse(read(prior,imageMember(priorImageIndex,'prior-path-map.json')));
  assert.equal(map.issue, 1295); assert.equal(map.version, 1);
  assert.equal(map.kind, 'complete-accepted-canonical-product-byte-map');
  assert.equal(old.kind, 'complete-prior-v1-mode-whole-byte-bijection');
  assert.equal(old.original_index_sha256, originalPriorIndex);
  assert.equal(old.shared_canonical_index_sha256, originalCanonicalTransport);
  const byteInverse=restoreByteDerivedObjects(canonical,prior,map,old,new Map([[canonical,canonicalImage],[prior,priorImageIndex]]));
  assert.equal(map.logical_targets.length, 302); assert.equal(old.logical_targets.length, 122);
  assert.equal(new Set(map.logical_targets.map(p => p.target)).size, 302);
  fs.mkdirSync(priorImage);
  const canonicalObjects = new Map(map.distinct_objects.map(p => [p.path, p]));
  for (const pin of map.logical_targets) {
    const destination = ordinary(root,pin.target);
    if (fs.existsSync(destination)) {
      let accepted=false;
      for(const expected of [pin,pin.existing_original].filter(Boolean)) {
        try { read(root,{...expected,path:pin.target});accepted=true;break; } catch {}
      }
      assert(accepted,'All canonical before bodies must be authentic before activation');
    }
  }
  for (const pin of map.logical_targets) {
    assert(pin.target.startsWith('data/canonical-grid/eastern-v8/') ||
      pin.target.startsWith('data/ownership-history/') || pin.target.startsWith('data/ownership-runtime/') ||
      pin.target === 'data/pixel-audit.json' || pin.target === 'data/geography/part-29.json' || pin.target === 'data/granularity-audit.json' || pin.target === namespace + '/accepted-pixel-verification.json');
    const object = canonicalObjects.get(pin.object);
    assert(object && object.bytes === pin.bytes && object.sha256 === pin.sha256 && object.mode === pin.mode);
    copy(root, pin.target, canonical, object, pin.existing_original);
  }
  const original = new Map(old.original_index.files.map(p => [p.path, p]));
  for (const pin of old.logical_targets) {
    const expected = original.get(pin.path);
    assert(expected && expected.bytes === pin.bytes && expected.sha256 === pin.sha256 && expected.mode === pin.mode);
    const object = pin.shared_canonical_object ?? {...pin, path: pin.object};
    if (pin.shared_canonical_object) assert.deepEqual(canonicalObjects.get(object.path), object);
    copy(priorImage, pin.path, pin.shared_canonical_object ? canonical : prior, object);
  }
  const receipt = {version: 1, issue: 1295, canonical_paths: 302, prior_paths: 122,
    canonical_index_sha256: canonicalIndex, prior_index_sha256: priorIndex,
    original_prior_index_sha256: originalPriorIndex, byte_inverse:byteInverse, priorImage, temporary,
    scientific_producers_invoked: false, original_vintages_and_unknowns_preserved: true};
  restored.set(root, {receipt, map, old});
  // Stock readers use only the fully verified installed paths and priorImage.
  // Preserve those complete files; discard only this exclusive object's staging
  // copies after every current/prior whole body has been verified again.
  getRestoredCanonicalProducts(root);
  const released=[];
  for(const [directory,pins] of [
    [canonical,[...canonicalImage.files,...map.distinct_objects]],
    [prior,[...priorImageIndex.files,...old.logical_targets.filter(p=>!p.shared_canonical_object).map(p=>({...p,path:p.object}))]]
  ]) {
    released.push(releaseVerifiedStagingObjects(directory,pins));
  }
  receipt.reproducible_staging_objects_released=released;
  receipt.complete_installed_and_prior_bodies_retained=true;
  return receipt;
}

export function releaseVerifiedStagingObjects(directory,pins) {
  assert(path.isAbsolute(directory)&&fs.realpathSync(directory)===directory,'Ordinary staging root');
  const expected=new Map(),folders=new Set();
  for(const pin of pins) {
    assert(safe(pin.path),'Safe staging path');
    const previous=expected.get(pin.path);
    if(previous)for(const key of ['bytes','sha256','mode'])assert.equal(previous[key],pin[key],'Conflicting staging declaration');
    expected.set(pin.path,pin);
    const parts=pin.path.split('/');for(let i=1;i<parts.length;i++)folders.add(parts.slice(0,i).join('/'));
  }
  const actual=[];
  const visit=(relative='')=>{
    const base=relative?ordinary(directory,relative):directory;
    for(const name of fs.readdirSync(base).sort()) {
      const file=relative?relative+'/'+name:name,p=ordinary(directory,file),stat=fs.lstatSync(p);
      assert(!stat.isSymbolicLink(),'Foreign staging link');
      if(stat.isDirectory()){assert(folders.has(file),'Foreign staging directory');visit(file);}
      else {assert(stat.isFile()&&expected.has(file),'Foreign staging member');read(directory,expected.get(file));actual.push(file);}
    }
  };
  visit();assert.deepEqual(actual.sort(),[...expected.keys()].sort(),'Missing staging member');
  const result={directory,files:actual.length,bytes:actual.reduce((n,file)=>n+expected.get(file).bytes,0)};
  fs.rmSync(directory,{recursive:true});return result;
}

export function getRestoredCanonicalProducts(root) {
  const saved = restored.get(root);
  assert(saved, 'Canonical restoration must precede stock readers');
  for (const pin of saved.map.logical_targets) read(root, {...pin, path: pin.target});
  for (const pin of saved.old.logical_targets) read(saved.receipt.priorImage, pin);
  return saved.receipt;
}

function checkoutMetadata(root,relative) {
  const file=ordinary(root,relative),stat=fs.lstatSync(file);
  assert(stat.isFile()&&stat.size>0&&stat.size<=1024*1024,'Bounded checkout metadata required');
  const fd=fs.openSync(file,'r');
  try {
    assert.equal(fs.fstatSync(fd).size,stat.size);
    const raw=Buffer.alloc(stat.size+1);let offset=0;
    while(offset<raw.length){const n=fs.readSync(fd,raw,offset,raw.length-offset,null);if(!n)break;offset+=n;}
    assert.equal(offset,stat.size,'Checkout metadata EOF differs');
    assert.equal(fs.readSync(fd,Buffer.alloc(1),0,1,null),0);
    return JSON.parse(raw.subarray(0,offset));
  }finally{fs.closeSync(fd);}
}

// Explicit preparation for unchanged checkout consumers. The package boundary
// remains the default; no package environment is manufactured here.
export function prepareCanonicalCheckout() {
  const root=process.cwd();
  assert.equal(fs.realpathSync(root),root);
  assert.equal(process.env.WORLDATLAS_PACKAGE_STAGE,undefined);
  const selectionPath=ordinary(root,'data/ownership-selection.json');
  if(!fs.existsSync(selectionPath))return {applicable:false,reason:'No committed native selection'};
  const selection=checkoutMetadata(root,'data/ownership-selection.json');
  if(selection.manifest_path!=='data/canonical-grid/eastern-v8/manifest.json')
    return {applicable:false,reason:'The committed selection does not use this fixed continuation'};
  assert.equal(selection.version,1);
  assert.equal(selection.method,'native-linear-evenodd-first-owner-v1');
  assert.equal(selection.sha256,'a71edb65cbd7986e245f626e8a34b70e12c12d081ca24fc936bdd84e1bb07885','Selected v8 native body differs');
  assert.equal(selection.release_id,'geography:review:896bf79dd6e5661dfbbffba60da96fa987b9971af2b884cf52347189861ebe9e','Selected v8 release differs');
  const stage=checkoutMetadata(root,'data/native-context-migration/manifest.json');
  assert.equal(stage.canonical_restoration?.index_sha256,canonicalIndex,'Selected v8 requires its exact canonical restoration');
  assert.equal(stage.prior_image?.sha256,priorIndex,'Selected v8 requires its exact original prior image');
  const temporaryRoot=ordinary(root,'.cache');fs.mkdirSync(temporaryRoot,{recursive:true});
  const receipt=restoreCanonicalProducts({root,temporaryRoot,mode:'checkout'});
  return {applicable:true,mode:'explicit-checkout',receipt};
}
