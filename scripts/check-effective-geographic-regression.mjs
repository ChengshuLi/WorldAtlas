// Trusted immutable data reader. Proposed project code is never imported.
import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {fileURLToPath} from 'node:url';
import {unshuffleOwnershipBytes} from '../src/ownership-codec.js';
import {readSelectedAdditive,selectedAdditiveRows,compareVersionedRepairLedgers} from '../coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';

const FILE=32*1024*1024, PHASE=256*1024*1024, OUTPUT=4*1024*1024;
const sha=b=>createHash('sha256').update(b).digest('hex');
const demand=(v,m)=>{if(!v)throw Error(m);};
const hash=v=>typeof v==='string'&&/^[a-f0-9]{64}$/.test(v);
const commit=v=>typeof v==='string'&&/^[a-f0-9]{40}$/.test(v);
const safe=v=>typeof v==='string'&&v&&!v.includes('\\')&&!v.includes('\0')&&!path.isAbsolute(v)&&v.split('/').every(p=>p&&p!=='.'&&p!=='..');
const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
const freezeJson=value=>{if(value&&typeof value==='object'){Object.values(value).forEach(freezeJson);Object.freeze(value);}return value;};
const installedRuntimes=new Map();
const selectedSnapshots=new WeakMap();
function runtimeIdentity(executable=process.execPath) {
  const executablePath=fs.realpathSync(executable);
  if(installedRuntimes.has(executablePath))return installedRuntimes.get(executablePath);
  const stat=fs.statSync(executablePath);demand(stat.isFile()&&stat.size<PHASE,'Installed execution runtime exceeds phase');
  const fd=fs.openSync(executablePath,'r'),hasher=createHash('sha256'),buffer=Buffer.alloc(1024*1024);let bytes=0;
  try{for(let n;(n=fs.readSync(fd,buffer,0,buffer.length,null));){hasher.update(buffer.subarray(0,n));bytes+=n;}const end=fs.fstatSync(fd);demand(end.size===stat.size&&end.ino===stat.ino&&bytes===stat.size,'Installed runtime changed during complete read');}finally{fs.closeSync(fd);}
  const runtime={path:executablePath,bytes,mode:stat.mode&0o777,sha256:hasher.digest('hex'),version:executable===process.execPath?process.version:null};installedRuntimes.set(executablePath,runtime);return runtime;
}
const NS='coordination/engineering/eastern-two-gap-repair-native-20261007/canonical-products';
const STOCK_INDEX='b82b195d94530d9b1f48153f7e47616f8b841cb1438ddf59994ba4869a1d7876';

export class ImmutableReader {
  constructor(repo,version,{runtimeBytes=fs.statSync(process.execPath).size,metadataBytes=8*1024*1024,executionBytes=0,outputBytes=OUTPUT,gitExecutable='git',budget}={}) {
    demand(commit(version),'Require immutable input commit');
    this.repo=repo;this.version=version;this.runtimeBytes=runtimeBytes;this.metadataBytes=metadataBytes;
    this.executionBytes=executionBytes;this.outputBytes=outputBytes;this.gitExecutable=gitExecutable;this.inventory=new Map();this.budget=budget??{};if(!budget)this.phase();
  }
  get used(){return this.budget.used;} set used(value){this.budget.used=value;}
  get charged(){return this.budget.charged;} set charged(value){this.budget.charged=value;}
  git(...args){return execFileSync(this.gitExecutable,['-c','core.hooksPath=/dev/null','-C',this.repo,...args],{maxBuffer:FILE+1,stdio:['ignore','pipe','pipe']});}
  descriptor(name,version=this.version) {
    demand(safe(name)&&commit(version),'Unsafe immutable path/commit');
    const row=this.git('ls-tree','-z',version,'--',name).toString();
    demand(/^100(644|755) blob [a-f0-9]{40}\t/.test(row)&&row.slice(row.indexOf('\t')+1)===name+'\0','Require whole ordinary Git input: '+name);
    const [mode,,blob]=row.slice(0,row.indexOf('\t')).split(' '),bytes=Number(this.git('cat-file','-s',blob));
    demand(Number.isSafeInteger(bytes)&&bytes>0&&bytes<=FILE,'Whole ordinary file exceeds cap: '+name);
    const key=version+':'+name,previous=this.inventory.get(key);
    const pin={commit:version,path:name,mode,git_blob_oid:blob,bytes};
    if(previous){demand(previous.git_blob_oid===blob&&previous.bytes===bytes&&previous.mode===mode,'Immutable descriptor drift');return previous;}
    this.inventory.set(key,pin);return pin;
  }
  phase(){this.used=this.runtimeBytes+this.executionBytes+this.metadataBytes+this.outputBytes;this.charged=new Map();demand(this.used<PHASE,'Installed runtime/metadata exceeds complete phase');}
  admit(pin,decoded=0) {
    demand(Number.isSafeInteger(decoded)&&decoded>=0&&decoded<=FILE,'Whole decoded member exceeds ordinary cap');
    const key=pin.commit+':'+pin.path,prior=this.charged.get(key);
    demand(!prior||prior===pin.bytes+decoded,'Ambiguous phase input accounting');
    if(!prior){demand(this.charged.size<512&&this.used+pin.bytes+decoded<=PHASE,'Complete phase exceeds prospective cap');this.charged.set(key,pin.bytes+decoded);this.used+=pin.bytes+decoded;}
  }
  read(name,{version=this.version,expected,decoded=0}={}) {
    const pin=this.descriptor(name,version);this.admit(pin,decoded);
    const body=this.git('cat-file','blob',pin.git_blob_oid);
    demand(body.length===pin.bytes&&(!expected||sha(body)===expected),'Whole immutable input differs: '+name);
    pin.sha256=sha(body);pin.whole_body_consumed=true;
    return body;
  }
  json(name,options){return JSON.parse(this.read(name,options));}
}

// Whole containing fragments, not sampled byte ranges, authenticate each member.
class StockImage {
  constructor(reader) {
    this.reader=reader;
    this.index=reader.json(NS+'/index.json',{expected:STOCK_INDEX});
    demand(this.index.version===1&&this.index.kind==='ordered-exact-original-byte-fragments','Unsupported selected bank transport');
    for(const list of [this.index.files,this.index.parts]) {
      demand(Array.isArray(list)&&list.length>0&&list.length<=512,'Incomplete selected transport roster');
      let at=0;const seen=new Set();for(const p of list){demand(safe(p.path)&&!seen.has(p.path)&&p.offset===at&&p.bytes>0&&p.bytes<=FILE&&hash(p.sha256),'Bad complete transport partition');seen.add(p.path);at+=p.decoded_bytes??p.bytes;}
      demand(at===this.index.whole_bytes,'Selected transport partition incomplete');
    }
    const mapPin=this.index.files.find(p=>p.path==='canonical-path-map.json');
    this.map=JSON.parse(this.member(mapPin));
    demand(this.map.version===1&&this.map.kind==='complete-accepted-canonical-product-byte-map'&&this.map.logical_targets.length===302,'Wrong complete selected logical map');
    demand(new Set(this.map.logical_targets.map(p=>p.target)).size===302,'Duplicate selected logical target');
  }
  member(pin) {
    demand(pin&&['100644','100755'].includes(pin.mode),'Missing whole bank member');
    const containing=this.index.parts.filter(p=>p.offset<pin.offset+pin.bytes&&pin.offset<p.offset+p.decoded_bytes);
    const descriptors=containing.map(p=>({p,d:this.reader.descriptor(NS+'/'+p.path)}));
    for(const {p,d}of descriptors)this.reader.admit(d,p.decoded_bytes);
    demand(pin.bytes<=FILE&&this.reader.used+pin.bytes<=PHASE,'Complete member reconstruction phase exceeds cap');
    // Reconstructed logical member is a real decoded consumer, charged separately.
    this.reader.used+=pin.bytes;
    const chunks=[];let bytes=0;
    for(const {p}of descriptors){const encoded=this.reader.read(NS+'/'+p.path,{expected:p.sha256,decoded:p.decoded_bytes});demand(encoded.length===p.bytes,'Transport encoded length differs');const raw=gunzipSync(encoded,{maxOutputLength:p.decoded_bytes});demand(raw.length===p.decoded_bytes&&sha(raw)===p.decoded_sha256,'Whole transport decoded body differs');const start=Math.max(pin.offset,p.offset),end=Math.min(pin.offset+pin.bytes,p.offset+raw.length);chunks.push(raw.subarray(start-p.offset,end-p.offset));bytes+=end-start;}
    demand(bytes===pin.bytes,'Incomplete whole bank member inverse');const raw=Buffer.concat(chunks,bytes);demand(sha(raw)===pin.sha256,'Whole bank member differs');return raw;
  }
  logical(name,pin) {
    const target=this.map.logical_targets.find(p=>p.target===name);
    demand(target&&target.bytes===pin.bytes&&target.sha256===pin.sha256,'Selected asset differs from authenticated bank map');
    const member=this.index.files.find(p=>p.path===target.object);
    demand(member&&member.bytes===target.bytes&&member.sha256===target.sha256&&member.mode===target.mode,'Logical/physical whole member differs');
    return this.member(member);
  }
}

// Explicit selected manifest-bound native asset transport. This consumes only
// immutable data; candidate whole-image/restoration code is never executed.
export class NativeAssetImage {
  constructor(reader,manifest,manifestPath) {
    demand(safe(manifestPath),'Missing selected native manifest path');this.nativeRoot=path.posix.dirname(manifestPath);
    this.reader=reader;const t=manifest.native_asset_transport;
    demand(t&&same(Object.keys(t).sort(),['index','kind','logical_assets','original_compressed_bytes','version'])&&t.version===1&&t.kind==='ordered-exact-original-byte-fragments','Unsupported selected native asset transport');
    demand(t.index&&same(Object.keys(t.index).sort(),['bytes','path','sha256'])&&safe(t.index.path)&&hash(t.index.sha256)&&Number.isSafeInteger(t.index.bytes)&&t.index.bytes>0&&t.index.bytes<=FILE,'Unbound selected native transport index');
    this.directory=path.posix.dirname(t.index.path);
    const descriptor=reader.descriptor(t.index.path);demand(descriptor.bytes===t.index.bytes,'Selected native index whole size differs');
    this.index=reader.json(t.index.path,{expected:t.index.sha256});
    demand(this.index.version===1&&this.index.kind===t.kind&&hash(this.index.whole_sha256)&&Number.isSafeInteger(this.index.whole_bytes)&&this.index.whole_bytes>0&&this.index.whole_bytes===t.original_compressed_bytes,'Unknown/incomplete native byte bank');
    demand(Number.isSafeInteger(t.logical_assets)&&t.logical_assets===manifest.parts.length&&Array.isArray(this.index.files)&&this.index.files.length===t.logical_assets&&Array.isArray(this.index.parts)&&this.index.parts.length>0&&this.index.parts.length<=512,'Incomplete native asset transport roster');
    for(const list of [this.index.files,this.index.parts]) {
      let offset=0;const names=new Set();for(const p of list){const length=list===this.index.parts?p.decoded_bytes:p.bytes;
        demand(safe(p.path)&&!names.has(p.path)&&Number.isSafeInteger(p.offset)&&p.offset===offset&&Number.isSafeInteger(p.bytes)&&p.bytes>0&&p.bytes<=FILE&&Number.isSafeInteger(length)&&length>0&&length<=FILE&&hash(p.sha256),'Invalid complete native byte partition');
        if(list===this.index.files)demand(p.mode==='100644'&&manifest.parts.some(a=>a.path===p.path&&a.bytes===p.bytes&&a.sha256===p.sha256),'Foreign/rebound whole native member');
        else{demand(hash(p.decoded_sha256),'Missing full native fragment decoded hash');const d=reader.descriptor(path.posix.join(this.directory,p.path));demand(d.bytes===p.bytes,'Whole native fragment size differs');}
        names.add(p.path);offset+=length;
      }demand(offset===this.index.whole_bytes,'Native transport omitted complete bytes');
    }
  }
  logical(name,pin) {
    demand(name===path.posix.join(this.nativeRoot,pin.path),'Foreign selected native logical path');
    const member=this.index.files.find(p=>p.path===pin.path);
    demand(member&&member.bytes===pin.bytes&&member.sha256===pin.sha256,'Selected native asset differs from manifest-bound whole member');
    const containing=this.index.parts.filter(p=>p.offset<member.offset+member.bytes&&member.offset<p.offset+p.decoded_bytes);
    const descriptors=containing.map(p=>({p,d:this.reader.descriptor(path.posix.join(this.directory,p.path))}));
    for(const {p,d}of descriptors)this.reader.admit(d,p.decoded_bytes);
    demand(member.bytes<=FILE&&this.reader.used+member.bytes<=PHASE,'Native complete member reconstruction exceeds phase');this.reader.used+=member.bytes;
    const chunks=[];let bytes=0;for(const {p}of descriptors){const encoded=this.reader.read(path.posix.join(this.directory,p.path),{expected:p.sha256,decoded:p.decoded_bytes});demand(encoded.length===p.bytes&&encoded.readUInt32LE(encoded.length-4)===p.decoded_bytes,'Native fragment declared decoded size differs before inflate');
      const raw=gunzipSync(encoded,{maxOutputLength:p.decoded_bytes});demand(raw.length===p.decoded_bytes&&sha(raw)===p.decoded_sha256,'Whole native fragment decoded body differs');
      const start=Math.max(member.offset,p.offset),end=Math.min(member.offset+member.bytes,p.offset+raw.length);chunks.push(raw.subarray(start-p.offset,end-p.offset));bytes+=end-start;
    }demand(bytes===member.bytes,'Incomplete whole native member inverse');const body=Buffer.concat(chunks,bytes);demand(sha(body)===member.sha256,'Whole native member changed');return body;
  }
}

// Resolve the selected continuous source independently of raw Git target bytes.
// The accepted v8 bank replaces part29 while the same raw Git path remains the
// historical original. Logical inverse provenance stays distinct from Git pins.
export class SelectedGeometrySources {
  constructor(snapshot) {
    demand(selectedSnapshots.has(snapshot)&&snapshot?.reader instanceof ImmutableReader,'Require authenticated selected snapshot');
    this.reader=snapshot.reader;this.snapshot=snapshot;
    const accepted=selectedSnapshots.get(snapshot);demand(accepted.selection===JSON.stringify(snapshot.selection)&&accepted.manifest===JSON.stringify(snapshot.manifest),'Selected snapshot metadata drift');
    const declared=snapshot.selection.selected_geography;
    if(declared){
      demand(declared.version===1&&declared.kind==='complete-world-index-with-exact-encoded-overrides'&&same(Object.keys(declared).sort(),['bytes','kind','path','sha256','version'])&&safe(declared.path)&&hash(declared.sha256)&&Number.isSafeInteger(declared.bytes)&&declared.bytes>0&&declared.bytes<=FILE,'Unsupported explicit selected geometry bank');
      const pin=this.reader.descriptor(declared.path);demand(pin.bytes===declared.bytes,'Selected source map size differs');
      this.bank=this.reader.json(declared.path,{expected:declared.sha256});
      demand(this.bank.version===1&&this.bank.kind===declared.kind&&this.bank.release_id===snapshot.selection.release_id&&this.bank.native_manifest_sha256===snapshot.selection.sha256&&hash(this.bank.footprints_sha256),'Selected source/native/release binding differs');
    }else{
      demand(snapshot.selection.manifest_path==='data/canonical-grid/eastern-v8/manifest.json','Selected continuous source transport unsupported; explicit release binding required');
      this.image=snapshot.image instanceof StockImage?snapshot.image:new StockImage(this.reader);
    }
    // Native preflight has discarded its whole containing buffers. Retain all
    // live snapshot metadata and any acquisition-frame bounds buffers explicitly
    // before the distinct release/source metadata acquisition phase.
    const external=Math.max(0,this.reader.metadataBytes-8*1024*1024);
    const ownImageBytes=this.image&&this.image!==snapshot.image?Buffer.byteLength(JSON.stringify({index:this.image.index,map:this.image.map})):0;
    this.reader.metadataBytes=8*1024*1024+external+2*(snapshot.metadataBytes+ownImageBytes)+snapshot.acquisition_buffer_bytes;
    this.reader.phase();
    const pointer=this.reader.json('data/geographic-releases/current-manifest.json');
    demand(safe(pointer.path)&&hash(pointer.sha256),'Unbound selected geographic release');
    const releasePath=path.posix.join('data/geographic-releases',pointer.path);
    // This ordinary gzip is charged at its maximum ordinary decoded bound BEFORE
    // reading. A smaller trusted decoded pin can be introduced by a typed release
    // descriptor, never by inspecting uncharged compressed bytes.
    const encoded=this.reader.read(releasePath,{expected:pointer.sha256,decoded:FILE});
    const release=JSON.parse(gunzipSync(encoded,{maxOutputLength:FILE}));
    const entries=release.releases;
    demand(Array.isArray(entries)&&entries.length>0&&new Set(entries.map(r=>r.id)).size===entries.length,'Incomplete selected release roster');
    this.release=entries.find(r=>r.id===snapshot.selection.release_id);
    demand(this.release&&this.release===entries.at(-1)&&hash(this.release.footprints_sha256),'Native source differs from current selected geographic release');
    const index=this.reader.json('data/world-index.json');
    demand(Array.isArray(index.parts)&&index.parts.length>0&&index.parts.length<=512&&new Set(index.parts).size===index.parts.length,'Incomplete whole source containing roster');
    this.paths=index.parts.map(p=>{demand(safe(p),'Unsafe world source part');return 'data/'+p;});
    const pathSet=new Set(this.paths);
    if(this.bank){
      demand(this.bank.footprints_sha256===this.release.footprints_sha256&&this.bank.locations===snapshot.owners.length,'Selected source full scope/digest differs');
      const original=this.readPinned(this.bank.world_index);demand(original.equals(this.reader.read('data/world-index.json')),'Source bank original index differs from current complete index');
      demand(Array.isArray(this.bank.unchanged_files)&&Array.isArray(this.bank.overrides),'Incomplete selected source map');
      const roster=new Map();
      for(const p of this.bank.unchanged_files){demand(pathSet.has(p.path)&&!roster.has(p.path),'Foreign/duplicate selected original containing source');this.checkPin(p);const actual=this.reader.descriptor(p.path);demand(actual.mode===p.mode&&actual.git_blob_oid===p.git_blob_oid&&actual.bytes===p.bytes,'Current original containing body differs from selected source map');roster.set(p.path,{...p,kind:'ordinary-immutable-git-source'});}
      for(const p of this.bank.overrides){demand(pathSet.has(p.logical_path)&&!roster.has(p.logical_path)&&p.encoding==='gzip','Foreign/duplicate/unsupported selected source override');this.checkPin(p);demand(Number.isSafeInteger(p.decoded_bytes)&&p.decoded_bytes>0&&p.decoded_bytes<=FILE&&hash(p.decoded_sha256),'Unbounded whole source override');roster.set(p.logical_path,{...p,kind:'selected-exact-encoded-override'});}
      demand(roster.size===this.paths.length&&this.paths.every(p=>roster.has(p)),'Incomplete selected source containing inventory');
      this.sources=this.paths.map(p=>roster.get(p));this.replacements=new Map(this.bank.overrides.map(p=>[p.logical_path,p]));
    }else{
      const replacements=this.image.map.logical_targets.filter(p=>p.target.startsWith('data/geography/'));
      demand(replacements.every(p=>pathSet.has(p.target)),'Selected bank contains unrostered source replacement');
      this.replacements=new Map(replacements.map(p=>[p.target,p]));
      this.sources=this.paths.map(name=>{
        const replacement=this.replacements.get(name);
        if(replacement){demand(replacement.mode==='100644'&&hash(replacement.sha256)&&Number.isSafeInteger(replacement.bytes)&&replacement.bytes>0&&replacement.bytes<=FILE,'Invalid whole selected geometry member');return {path:name,kind:'selected-whole-bank-member',bytes:replacement.bytes,sha256:replacement.sha256,mode:replacement.mode,transport_index_sha256:STOCK_INDEX,physical_member:replacement.object,origin:replacement.origin,existing_original:replacement.existing_original};}
        return {...this.reader.descriptor(name),kind:'ordinary-immutable-git-source'};
      });
    }
    freezeJson(this.paths);freezeJson(this.sources);freezeJson(this.bank);freezeJson(this.release);Object.freeze(this);

  }
  checkPin(p) {
    demand(p&&commit(p.commit)&&safe(p.path)&&p.mode==='100644'&&/^[a-f0-9]{40}$/.test(p.git_blob_oid)&&Number.isSafeInteger(p.bytes)&&p.bytes>0&&p.bytes<=FILE&&hash(p.sha256),'Incomplete whole selected source pin');
  }
  readPinned(p) {
    this.checkPin(p);let version=p.commit;
    // Squash retention is allowed ONLY for the exact same original ordinary
    // path/mode/Git blob/full SHA. Actual consumed provenance remains explicit.
    try{this.reader.git('cat-file','-e',version+'^{commit}');}catch{version=this.reader.version;}
    const actual=this.reader.descriptor(p.path,version);
    demand(actual.mode===p.mode&&actual.git_blob_oid===p.git_blob_oid&&actual.bytes===p.bytes,'Selected source original mode/OID/body differs');
    const raw=this.reader.read(p.path,{version,expected:p.sha256,decoded:p.decoded_bytes??0});
    return raw;
  }

  read(name) {
    demand(this.paths.includes(name),'Foreign source outside complete selected roster');
    const replacement=this.replacements.get(name);
    const source=this.sources[this.paths.indexOf(name)];let raw;
    if(this.bank){
      const encoded=this.readPinned(source);
      if(replacement){demand(encoded.length>=18&&encoded[0]===31&&encoded[1]===139&&encoded.readUInt32LE(encoded.length-4)===source.decoded_bytes,'Source override gzip size differs before decode');raw=gunzipSync(encoded,{maxOutputLength:source.decoded_bytes});demand(raw.length===source.decoded_bytes&&sha(raw)===source.decoded_sha256,'Whole selected source override differs');}
      else raw=encoded;
    }else if(replacement&&name==='data/geography/part-29.json'&&replacement.sha256==='c34114912dc620dce0821e251877470b5a83385ab3bf1284408f077b78bbdec8'&&replacement.bytes===12932407){
      // The accepted v8 logical member has a separately retained whole ordinary
      // gzip inverse. It is a fixed byte-exact alias, never a proposal scan.
      const alias='coordination/engineering/eastern-two-gap-repair-20261007/run-two/proposed-part-29.json.gz';
      demand(this.reader.descriptor(alias).mode==='100644','Accepted whole v8 alias mode differs');
      const encoded=this.reader.read(alias,{expected:'fa286f44f47494cacab793e4109eb18db3e6016dc7103d930b9dff2dbf3573fb',decoded:replacement.bytes});
      demand(encoded.length===3400273&&encoded.length>=18&&encoded.readUInt32LE(encoded.length-4)===replacement.bytes,'Accepted whole v8 alias size differs');
      raw=gunzipSync(encoded,{maxOutputLength:replacement.bytes});demand(raw.length===replacement.bytes&&sha(raw)===replacement.sha256,'Accepted whole v8 alias inverse differs');
      return this.collection(raw,{...source,whole_encoded_alias:{...this.reader.inventory.get(this.reader.version+':'+alias)}});
    }else raw=replacement?this.image.logical(name,replacement):this.reader.read(name);

    return this.collection(raw,source);
  }
  collection(raw,source) {
    const collection=JSON.parse(raw);
    demand(collection?.type==='FeatureCollection'&&Array.isArray(collection.features)&&collection.features.length>0,'Incomplete whole selected source collection');
    return {body:raw,collection,source,whole_sha256:sha(raw)};
  }
}

function validateParts(manifest) {
  demand(manifest.version===2&&manifest.method==='native-linear-evenodd-first-owner-v1'&&Number.isSafeInteger(manifest.size)&&manifest.size>1&&manifest.coordinateBits===Math.ceil(Math.log2(manifest.size)),'Unsupported selected ownership domain');
  demand(Array.isArray(manifest.parts)&&manifest.parts.length>0&&manifest.parts.length<=512,'Missing native whole parts');
  const names=new Set();
  for(const kind of ['rows','runs']){let offset=0;const parts=manifest.parts.filter(p=>p.kind===kind);demand(parts.length>0,'Missing native '+kind);for(const p of parts){demand(safe(p.path)&&!names.has(p.path)&&p.offset===offset&&Number.isSafeInteger(p.words)&&p.words>0&&p.words%2===0&&p.encoding==='byte-shuffle'&&p.decoded_bytes===p.words*4&&p.decoded_bytes<=FILE&&p.bytes>0&&p.bytes<=FILE&&hash(p.sha256)&&hash(p.decoded_sha256),'Invalid complete native partition');names.add(p.path);offset+=p.words;}demand(offset===(kind==='rows'?manifest.size*2:manifest.runWords),'Native partition omitted words');}
}

// Independently accepted immutable scientific artifacts are consumed as data.
// This exact registered authority preserves original scientific qualification;
// it never imports the proposed consumer or fabricates a scientific brand.
const REGISTERED_ARTIFACT_REVIEW_GETS=Object.freeze({
  // Retained original acceptance. New independent decisions append their whole
  // GET hash here after ordinary trusted-code review; candidate data cannot mint
  // a reviewer identity or approval boolean as an authority.
  '79024f6fd9335b0ad9da0ed936f5eabc600188f6176d9f953ceb006946626dbd':Object.freeze({review_id:6078458358,github_user_id:6732996,issue:1520,retired:true}),
  '5d6758debd9c2e141b83c40594486939f6fa2fd819816070957bbc4b0f1075c2':Object.freeze({review_id:6078884054,github_user_id:6732996,issue:1520,releaseCatalogue:true}),
  '7bd742247d4f2c2435fcb8c9bbc3134d3edc6193f312171bdb9a3b2ffd769c72':Object.freeze({review_id:6079096820,github_user_id:6732996,issue:1520,releaseCatalogue:true}),
  '5ff3e90bed0618f66c290eac5a0d813821b6ae513378a003ae2452e6e131350b':Object.freeze({review_id:6080211722,github_user_id:6732996,issue:1520,releaseCatalogue:true,entryProfiles:true}),
  'd75f436320deff42c9ecac8dfff46da252ebbdfeef69cec0ce633620a87184f3':Object.freeze({review_id:6087324521,github_user_id:6732996,issue:1520,releaseCatalogue:true,entryProfiles:true,cloudflareProfile:true}),
  '7158e9be36852eb4c2997309cf3d3818bcf46f67034f625dc9f57b67afb53d62':Object.freeze({review_id:6081097955,github_user_id:6732996,issue:1520,releaseCatalogue:true,entryProfiles:true,cloudflareProfile:true}),
  'ca283dcb0814cfbbd4430d8646eb5af3ad6e89af2669343a478c86fecf736519':Object.freeze({review_id:6090495174,github_user_id:6732996,issue:1520,releaseCatalogue:true,entryProfiles:true,cloudflareProfile:true}),
  '87ab56e1354dd8a8fda532bfa008436abd35c6c506f0e0685eaa2f2f07f59a8a':Object.freeze({review_id:6090739618,github_user_id:6732996,issue:1520,releaseCatalogue:true,entryProfiles:true,cloudflareProfile:true})
});
// Validate the complete ordered installer catalogue as immutable provenance.
// Reading these descriptors does not claim this gate installs their payloads.
export function validateReleaseCatalogue(certificate,catalogue,registry) {
  const pin=certificate.release_product_catalogue,inline=certificate.application_inputs;
  demand(catalogue?.version===1&&catalogue.kind==='qualified-arctic-release-product-roster-v1'&&catalogue.issue===1520&&same(Object.keys(catalogue).sort(),['issue','kind','products','version'])&&Array.isArray(catalogue.products)&&catalogue.products.length===343,'Incomplete qualified release product catalogue');
  demand(Array.isArray(inline)&&inline.length>0&&same(inline.find(p=>(p.space??'root')==='root'&&p.path===pin.path),{space:'root',...pin}),'Release catalogue is not the exact inline application input');
  const seen=new Set();
  function descriptor(p,space) {
    demand(['root','prior','image'].includes(space)&&safe(p.path)&&p.mode==='100644'&&Number.isSafeInteger(p.bytes)&&p.bytes>0&&p.bytes<=FILE&&hash(p.sha256),'Invalid complete application role');
    if(p.decoded_bytes!==undefined)demand(Number.isSafeInteger(p.decoded_bytes)&&p.decoded_bytes>0&&p.decoded_bytes<=FILE&&hash(p.decoded_sha256),'Invalid full application decoded role');
    const key=space+':'+p.path;demand(!seen.has(key),'Duplicate/overlapping complete application role');seen.add(key);
  }
  for(const p of inline)descriptor(p,p.space??'root');
  const directory=path.posix.dirname(certificate.selected_artifact_bindings.registry.path);
  demand(Array.isArray(registry?.batches)&&registry.batches.length>=343,'Missing complete release registry product roster');
  const rows=registry.batches.slice(-343);
  for(let i=0;i<catalogue.products.length;i++) {
    const p=catalogue.products[i],row=rows[i];
    demand(same(Object.keys(p).sort(),['bytes','decoded_bytes','decoded_sha256','mode','path','sha256']),'Incomplete whole release product descriptor');descriptor(p,'root');
    demand(safe(row.path)&&p.path===path.posix.join(directory,row.path)&&row.encoding==='gzip'&&row.sha256===p.sha256&&row.payload_sha256===p.decoded_sha256,'Release catalogue ordered path/encoded/payload join differs');
  }
  demand(seen.size===inline.length+catalogue.products.length,'Incomplete expanded application closure');
  return {inline_roles:inline.length,release_products:catalogue.products.length,complete_roles:seen.size};
}
function readArtifactGzip(reader,pin) {
  demand(pin&&safe(pin.path)&&pin.mode==='100644'&&Number.isSafeInteger(pin.bytes)&&pin.bytes>0&&pin.bytes<=FILE&&hash(pin.sha256)&&Number.isSafeInteger(pin.decoded_bytes)&&pin.decoded_bytes>0&&pin.decoded_bytes<=FILE&&hash(pin.decoded_sha256),'Unbounded artifact gzip pin');
  const actual=reader.descriptor(pin.path);demand(actual.bytes===pin.bytes&&actual.mode===pin.mode,'Artifact gzip whole mode/size differs');reader.admit(actual,pin.decoded_bytes);
  const encoded=reader.read(pin.path,{expected:pin.sha256,decoded:pin.decoded_bytes});demand(encoded.readUInt32LE(encoded.length-4)===pin.decoded_bytes,'Artifact decoded size differs before inflate');
  const body=gunzipSync(encoded,{maxOutputLength:pin.decoded_bytes});demand(body.length===pin.decoded_bytes&&sha(body)===pin.decoded_sha256,'Artifact whole decoded body differs');return JSON.parse(body);
}
// Code inventories are source custody. This trusted reader executes none of
// these candidate bodies; actual application entries authenticate their own
// current execution closure separately from shared and other-entry critical code.
export function validateArtifactSourceMetadata(certificate,code,qualification,{entryProfiles=false,cloudflareProfile=false}={}) {
  const pins=new Map(certificate.application_inputs.map(p=>[(p.space??'root')+':'+p.path,p]));
  const whole=p=>p&&safe(p.path)&&p.mode==='100644'&&Number.isSafeInteger(p.bytes)&&p.bytes>0&&p.bytes<=FILE&&hash(p.sha256);
  demand(code?.version===1&&code.kind==='qualified-artifact-application-code-closure-v1'&&Array.isArray(code.critical_files)&&code.critical_files.length>0&&typeof code.semantics==='string','Incomplete application code source custody');
  const shared=new Map();
  function critical(p,map){
    demand(whole(p)&&/^[a-f0-9]{40}$/.test(p.git_blob)&&!map.has(p.path),'Invalid/duplicate critical source role');map.set(p.path,p);
    if(entryProfiles){const input=pins.get('root:'+p.path);demand(input&&['mode','bytes','sha256'].every(k=>input[k]===p[k]),'Critical source role omitted/rebound in complete application inputs');}
  }
  for(const p of code.critical_files)critical(p,shared);
  demand(!cloudflareProfile||entryProfiles,'Cloudflare requires explicit entry-specific source custody');
  const allowed=['scripts/build-static-inner.mjs','scripts/build-hosted-inner.mjs',...(entryProfiles?['scripts/run-integration-tests.mjs']:[]),...(cloudflareProfile?['scripts/build-cloudflare-inner.mjs']:[])];
  demand(same(Object.keys(code.entry_roles??{}).sort(),allowed.toSorted()),'Missing/foreign actual entry profile');
  if(entryProfiles)demand(same(Object.keys(code.entry_critical_files??{}).sort(),allowed.toSorted()),'Missing/foreign entry-specific source custody');
  else demand(code.entry_critical_files===undefined,'Unsupported historical entry-specific profile');
  const complete=new Map(shared),profiles={};
  for(const entry of allowed){
    const role=code.entry_roles[entry],groups=entryProfiles?[role?.actual_current_execution_wrappers]:Object.values(role??{});
    demand(groups.length>0&&groups.every(a=>Array.isArray(a)&&a.length>0),'Missing original entry role groups');
    const wrappers=groups.flat();
    demand(Array.isArray(wrappers)&&wrappers.length>0&&wrappers.every(safe)&&new Set(wrappers).size===wrappers.length,'Incomplete/duplicate actual wrapper profile');
    const local=new Map();
    if(entryProfiles){demand(Array.isArray(code.entry_critical_files[entry])&&code.entry_critical_files[entry].length>0,'Missing entry-specific critical source role');for(const p of code.entry_critical_files[entry]){critical(p,local);demand(!shared.has(p.path),'Shared/entry critical role overlap');const previous=complete.get(p.path);demand(!previous||same(previous,p),'Cross-entry critical source drift');complete.set(p.path,p);}}
    profiles[entry]={shared_critical_roles:shared.size,entry_critical_roles:local.size,declared_current_role_groups:structuredClone(role)};
  }
  demand(qualification?.kind==='complete-qualified-scientific-artifact-inventory-v1'&&qualification.version===1&&qualification.issue===1520&&sha(Buffer.from(JSON.stringify(qualification.source_policy)))===certificate.source_policy.sha256,'Original qualification/source policy differs');
  const phases=qualification.complete_phase_inventory;
  demand(Array.isArray(phases)&&phases.length>0&&new Set(phases.map(p=>p.phase)).size===phases.length,'Incomplete/duplicate original qualification phases');
  for(const phase of phases){demand(typeof phase.phase==='string'&&Number.isSafeInteger(phase.complete_actual_runs)&&phase.complete_actual_runs>0&&Array.isArray(phase.runs)&&phase.runs.length===phase.complete_actual_runs,'Missing original qualification runs');for(const run of phase.runs){const t=run.actual_terminal;demand(t?.qualified===true&&t.exit_code===0&&t.guard_reason===null&&same(t.owned_group_survivors,[]),'Unqualified original operating evidence');}}
  demand(Array.isArray(qualification.original_source_and_qualification_publications)&&qualification.original_source_and_qualification_publications.length>0&&Array.isArray(qualification.complete_operating_custody)&&qualification.complete_operating_custody.length>0,'Missing complete original source/operating custody');
  return {source_critical_roles:complete.size,entry_profiles:profiles,original_phases:phases.length,candidate_code_executed:false};
}
export function readArtifactConsumption(reader,selection,manifest) {
  const hook=selection.artifact_consumption;if(hook===undefined)return null;
  demand(hook&&same(Object.keys(hook).sort(),['certificate','review']),'Unsupported artifact-consumption selector');
  const registration=REGISTERED_ARTIFACT_REVIEW_GETS[hook.review?.sha256];
  demand(registration,'Missing independently registered artifact authority');
  demand(!registration.retired,'Historical artifact authority cannot select the superseded application closure');
  for(const pin of [hook.certificate,hook.review]){
    demand(pin&&same(Object.keys(pin).sort(),['bytes','mode','path','sha256'])&&pin.mode==='100644'&&safe(pin.path)&&hash(pin.sha256)&&Number.isSafeInteger(pin.bytes)&&pin.bytes>0&&pin.bytes<=FILE,'Unsupported whole artifact authority pin');
    const actual=reader.descriptor(pin.path);demand(actual.mode===pin.mode&&actual.bytes===pin.bytes,'Artifact authority whole mode/size differs');reader.admit(actual);
  }
  const certificate=reader.json(hook.certificate.path,{expected:hook.certificate.sha256}),review=reader.json(hook.review.path,{expected:hook.review.sha256});
  demand(review.id===registration.review_id&&review.user?.id===registration.github_user_id&&typeof review.body==='string','Artifact authority is not the independently retained review GET');
  const block=review.body.match(/<!-- worldatlas-qualified-artifact-consumption:v1\s*([\s\S]*?)\s*-->/);demand(block,'Missing typed artifact review');const accepted=JSON.parse(block[1]);
  demand(accepted.version===1&&accepted.issue===registration.issue&&accepted.decision==='accept-qualified-artifact-consumption'&&accepted.certificate_sha256===hook.certificate.sha256&&accepted.certificate_bytes===hook.certificate.bytes&&accepted.native_manifest_sha256===selection.sha256,'Typed independent artifact authority differs');
  demand(certificate.version===1&&certificate.kind==='qualified-arctic-immutable-product-certificate-v1'&&certificate.issue===registration.issue&&certificate.native_manifest_sha256===accepted.native_manifest_sha256&&selection.sha256===accepted.native_manifest_sha256&&certificate.complete_locations===49625,'Unsupported qualified artifact domain');
  const bindings=certificate.selected_artifact_bindings,last=certificate.steps?.at(-1),declared=bindings?.native_manifest,actual=reader.descriptor(selection.manifest_path);
  demand(declared?.path===selection.manifest_path&&declared.bytes===actual.bytes&&declared.sha256===selection.sha256&&last?.successor_release_id===selection.release_id&&last.selected_grid.path===declared.path&&last.selected_grid.sha256===declared.sha256&&last.selected_grid.bytes===declared.bytes,'Selected native/release is not the qualified artifact');
  demand(same(bindings.selected_geography,selection.selected_geography)&&certificate.source_policy.sha256===accepted.source_policy_sha256&&certificate.application_consumer_code.sha256===accepted.application_consumer_code_sha256&&certificate.qualification_inventory.sha256===accepted.qualification_inventory_sha256,'Selected source/policy/qualification binding differs');
  demand(Array.isArray(certificate.application_inputs)&&certificate.application_inputs.length>0&&certificate.steps.length===3&&certificate.limits.science_reexecuted_for_application===false&&manifest.geographic_release===selection.release_id,'Incomplete original artifact-consumption closure');
  let releaseCatalogue=null;
  if(registration.releaseCatalogue){
    const cataloguePin=certificate.release_product_catalogue,registryPin={mode:'100644',...bindings.registry};
    // Admit BOTH complete gzip bodies before reading either one.
    for(const pin of [cataloguePin,registryPin]){demand(pin&&Number.isSafeInteger(pin.decoded_bytes)&&pin.decoded_bytes>0&&pin.decoded_bytes<=FILE,'Missing bounded complete release catalogue');const d=reader.descriptor(pin.path);demand(d.bytes===pin.bytes&&d.mode===pin.mode,'Complete release catalogue pin differs');reader.admit(d,pin.decoded_bytes);}
    releaseCatalogue=validateReleaseCatalogue(certificate,readArtifactGzip(reader,cataloguePin),readArtifactGzip(reader,registryPin));
  }
  const codePin=certificate.application_consumer_code,qualificationPin=certificate.qualification_inventory;
  // Both complete metadata bodies and the decoded qualification are charged
  // before either body opens. Descriptor references never masquerade as reads.
  for(const p of [codePin,qualificationPin]){demand(p&&safe(p.path)&&p.mode==='100644'&&hash(p.sha256)&&Number.isSafeInteger(p.bytes)&&p.bytes>0&&p.bytes<=FILE,'Incomplete source custody metadata pin');const d=reader.descriptor(p.path);demand(d.mode===p.mode&&d.bytes===p.bytes,'Source custody metadata mode/size differs');reader.admit(d,p.decoded_bytes??0);}
  const code=reader.json(codePin.path,{expected:codePin.sha256}),qualification=readArtifactGzip(reader,qualificationPin);
  const sourceCustody=validateArtifactSourceMetadata(certificate,code,qualification,{entryProfiles:registration.entryProfiles===true,cloudflareProfile:registration.cloudflareProfile===true});
  return freezeJson({releaseCatalogue,sourceCustody,certificate_pin:hook.certificate,review_pin:hook.review,certificate,review_id:review.id,limits:accepted.limits,
    scope:'Once-qualified immutable artifact provenance only. This gate independently consumes actual selected native/source products; no source authority, activation or production approval.'});
}

function loadBaseSelection(reader) {
  const has=reader.git('ls-tree','-z',reader.version,'--','data/ownership-selection.json').length;
  if(!has)return null;
  const selection=reader.json('data/ownership-selection.json');
  const selectionKeys=['manifest_path','method','release_id','sha256','version',...(selection.selected_geography?['selected_geography']:[]),...(Object.hasOwn(selection,'additive_release')?['additive_release']:[]),...(Object.hasOwn(selection,'artifact_consumption')?['artifact_consumption']:[])].sort();
  demand(same(Object.keys(selection).sort(),selectionKeys),'Unsupported committed additive/ownership selection; no proposal scanning');
  demand(selection.version===1&&selection.method==='native-linear-evenodd-first-owner-v1'&&safe(selection.manifest_path)&&hash(selection.sha256),'Unsupported ownership selection');
  const manifest=reader.json(selection.manifest_path,{expected:selection.sha256});validateParts(manifest);
  const artifactConsumption=readArtifactConsumption(reader,selection,manifest);
  demand(selection.release_id===manifest.geographic_release,'Selected reference differs from native bank');
  const bounds=manifest.original_assets?.bounds;
  demand(bounds?.role==='original-identity-parent-camera-context'&&commit(bounds.commit)&&bounds.path==='data/canonical-grid/bounds.json.gz'&&bounds.sha256===manifest.bounds?.sha256,'Missing independent original native owner roster');
  const rawBounds=reader.read(bounds.path,{version:bounds.commit,expected:bounds.sha256,decoded:manifest.bounds.decoded_bytes??FILE});
  const decoded=gunzipSync(rawBounds,{maxOutputLength:FILE});
  const owners=JSON.parse(decoded),ids=new Set();
  demand(Array.isArray(owners)&&owners.length>0&&owners.every((p,i)=>p.index===i+1&&typeof p.id==='string'&&p.id.length>0&&!ids.has(p.id)&&ids.add(p.id)),'Incomplete/duplicate stable native owner roster');
  const registry=reader.json('scripts/native-ownership/verified-candidates.json');
  const proof=registry.candidates?.[selection.sha256];
  demand(registry.version===1&&proof?.role==='reviewed-exhaustive-native-rule-comparison'&&proof.installation_approval===false&&commit(proof.commit)&&safe(proof.path)&&hash(proof.sha256),'Missing registered complete native comparison');
  let proofVersion=proof.commit;
  // Squash merges may omit the original producer commit from a clean clone.
  // Its independently registered WHOLE byte hash still binds the exact retained
  // same-path copy; consumed provenance never pretends to be the original commit.
  try{reader.git('cat-file','-e',proof.commit+'^{commit}');}catch{proofVersion=reader.version;}
  const receipt=reader.json(proof.path,{version:proofVersion,expected:proof.sha256});
  const receiptProvenance={registered_origin:{commit:proof.commit,path:proof.path,sha256:proof.sha256},consumed:{...reader.inventory.get(proofVersion+':'+proof.path)},whole_body_alias:proofVersion!==proof.commit};
  demand(receipt.method===manifest.method&&receipt.baseline_commit===manifest.provenance?.baseline_commit&&receipt.preparation_commit===manifest.provenance?.evaluation_commit&&receipt.owned_cells===manifest.accounting?.owned_cells&&receipt.owners===manifest.accounting?.owners&&receipt.checked_rows===manifest.size&&receipt.checked_cells===manifest.size**2&&receipt.unchecked_cells===0&&receipt.checked_runs*2===manifest.runWords&&receipt.installation_ready===false,'Native registered comparison differs');
  const products=receipt.products;
  demand(Array.isArray(products)&&products.length>0&&products.length<=512&&products.every(p=>safe(p.path)&&hash(p.sha256)&&Number.isSafeInteger(p.bytes)&&p.bytes>=0&&p.bytes<=FILE)&&new Set(products.map(p=>p.path)).size===products.length&&receipt.two_run_products===products.length&&receipt.run_one_sha256===sha(Buffer.from(JSON.stringify(products)))&&receipt.run_two_sha256===receipt.run_one_sha256&&products.find(p=>p.path==='manifest.json')?.sha256===selection.sha256,'Incomplete two-run native comparison');
  demand(products.filter(p=>p.path.startsWith('native-v1/ownership/')).length===manifest.parts.length,'Comparison contains foreign/missing native assets');
  for(const part of manifest.parts)demand(products.some(p=>p.path===part.path&&p.sha256===part.sha256&&p.bytes===part.bytes),'Comparison omitted selected native asset');
  let image=manifest.native_asset_transport?new NativeAssetImage(reader,manifest,selection.manifest_path):undefined;
  for(const part of manifest.parts){const name=path.posix.join(path.posix.dirname(selection.manifest_path),part.path);
    if(reader.git('ls-tree','-z',reader.version,'--',name).length)reader.descriptor(name);
    else{if(image instanceof NativeAssetImage){demand(image.index.files.some(p=>p.path===part.path&&p.bytes===part.bytes&&p.sha256===part.sha256),'Missing selected native transport asset');}else{demand(selection.manifest_path==='data/canonical-grid/eastern-v8/manifest.json','Missing selected ordinary bank asset');image??=new StockImage(reader);const target=image.map.logical_targets.find(p=>p.target===name);demand(target&&target.bytes===part.bytes&&target.sha256===part.sha256,'Selected native asset absent from complete bank');}}}
  if(image instanceof StockImage)for(const part of image.index.parts){const actual=reader.descriptor(NS+'/'+part.path);demand(actual.bytes===part.bytes,'Whole selected container length differs');}
  const snapshot={selection,manifest,owners,image,receiptProvenance,artifactConsumption,metadataBytes:decoded.length+Buffer.byteLength(JSON.stringify(manifest))+(image instanceof StockImage?Buffer.byteLength(JSON.stringify(image.map))+Buffer.byteLength(JSON.stringify(image.index)):image?Buffer.byteLength(JSON.stringify(image.index)):0),acquisition_buffer_bytes:rawBounds.length+decoded.length,reader};
  if(artifactConsumption)snapshot.metadataBytes+=Buffer.byteLength(JSON.stringify(artifactConsumption));
  selectedSnapshots.set(snapshot,{selection:JSON.stringify(selection),manifest:JSON.stringify(manifest)});
  if(selection.selected_geography){snapshot.geometrySources=new SelectedGeometrySources(snapshot);snapshot.metadataBytes+=Buffer.byteLength(JSON.stringify(snapshot.geometrySources.bank))+Buffer.byteLength(JSON.stringify(snapshot.geometrySources.sources))+Buffer.byteLength(JSON.stringify(snapshot.geometrySources.release));}
  return snapshot;
}

export function loadSelection(reader) {
  // This completed helper frame relinquishes raw base containers and decoded
  // owner-body buffers before a genuinely separate additive acquisition stage.
  // The full authenticated owners/map/index and all descriptor custody survive.
  const snapshot=loadBaseSelection(reader);if(!snapshot)return null;
  // The returned owner objects remain, but the helper's encoded/decoded byte
  // buffers do not. Their full consumption remains in the completed phase below.
  snapshot.acquisition_buffer_bytes=0;
  const basePhase={kind:'complete-selected-base-acquisition-v1',complete_phase_bytes:reader.used,inputs:structuredClone([...reader.inventory.values()])};
  snapshot.acquisitionPhases=[basePhase];
  if(snapshot.selection.additive_release!==undefined){
    reader.metadataBytes+=snapshot.metadataBytes+Buffer.byteLength(JSON.stringify(basePhase));
    reader.phase();
    snapshot.additive=readSelectedAdditive(snapshot);
    snapshot.acquisitionPhases.push({kind:'complete-selected-additive-acquisition-v1',complete_phase_bytes:reader.used,inputs:structuredClone([...reader.inventory.values()])});
    snapshot.metadataBytes+=snapshot.additive.metadata_bytes;
  }else snapshot.additive=null;
  snapshot.metadataBytes+=Buffer.byteLength(JSON.stringify(snapshot.acquisitionPhases));
  freezeJson(snapshot.acquisitionPhases);freezeJson(snapshot.selection);freezeJson(snapshot.manifest);freezeJson(snapshot.owners);return Object.freeze(snapshot);
}

function asset(snapshot,pin) {
  const {reader,selection}=snapshot,name=path.posix.join(path.posix.dirname(selection.manifest_path),pin.path);
  const exists=reader.git('ls-tree','-z',reader.version,'--',name).length;
  const decodedReserve=pin.decoded_bytes*(exists?2:3);
  demand(reader.used+decodedReserve<=PHASE,'Complete shuffled/canonical native representations exceed cap');reader.used+=decodedReserve;
  let raw;
  if(exists)raw=reader.read(name,{expected:pin.sha256,decoded:pin.decoded_bytes});
  else {
    demand(snapshot.image instanceof NativeAssetImage||selection.manifest_path==='data/canonical-grid/eastern-v8/manifest.json','Missing selected ordinary bank asset');
    const image=snapshot.image??new StockImage(reader);raw=image.logical(name,pin);
  }
  demand(raw.length===pin.bytes&&sha(raw)===pin.sha256,'Whole selected native encoded body differs');
  const shuffled=gunzipSync(raw,{maxOutputLength:pin.decoded_bytes});demand(shuffled.length===pin.decoded_bytes,'Native whole decoded length differs');
  const words=unshuffleOwnershipBytes(shuffled,pin.words);
  const canonical=Buffer.alloc(words.length*4);for(let i=0;i<words.length;i++)canonical.writeUInt32LE(words[i],i*4);
  demand(sha(canonical)===pin.decoded_sha256,'Native canonical unshuffled words differ');return words;
}

// Complete row projections are private products of authenticated whole-part
// acquisition. They retain every interval, never whole transport/word buffers.
const nativeTables=new WeakMap(), nativeProjections=new WeakMap();
const projectionSha=p=>{const h=createHash('sha256');for(const words of [p.rows,p.offsets,p.words])h.update(Buffer.from(words.buffer,words.byteOffset,words.byteLength));return h.digest('hex');};
function nativeParts(snapshot,table,y) {
  const start=table[y*2]*2,end=start+table[y*2+1]*2;
  return snapshot.manifest.parts.filter(p=>p.kind==='runs'&&start<p.offset+p.words&&p.offset<end);
}
export function loadNativeRowTable(snapshot) {
  demand(selectedSnapshots.has(snapshot),'Require authenticated selected snapshot');
  const pins=snapshot.manifest.parts.filter(p=>p.kind==='rows');demand(pins.length===1,'Unsupported split native row table');
  const table=asset(snapshot,pins[0]);nativeTables.set(table,{snapshot,sha256:sha(Buffer.from(table.buffer,table.byteOffset,table.byteLength))});return table;
}
function sidePlan(snapshot,table,rows) {
  const tableProof=nativeTables.get(table);demand(selectedSnapshots.has(snapshot)&&tableProof?.snapshot===snapshot&&sha(Buffer.from(table.buffer,table.byteOffset,table.byteLength))===tableProof.sha256,'Require authenticated unchanged selected row table');
  demand(rows.length>0&&rows.every((y,i)=>Number.isSafeInteger(y)&&y>=0&&y<snapshot.manifest.size&&(!i||rows[i-1]<y)),'Missing/duplicate/foreign planned native row');
  const pins=[...new Map(rows.flatMap(y=>nativeParts(snapshot,table,y)).map(p=>[p.path,p])).values()];
  const inputs=new Map(),members=[];
  for(const pin of pins){
    const memberInputs=new Map();let buffers=0;
    demand(Number.isSafeInteger(pin.decoded_bytes)&&pin.decoded_bytes>0&&pin.decoded_bytes<=FILE,'Whole decoded native member exceeds cap');
    const name=path.posix.join(path.posix.dirname(snapshot.selection.manifest_path),pin.path),reader=snapshot.reader;
    if(reader.git('ls-tree','-z',reader.version,'--',name).length){
      const d=reader.descriptor(name);demand(d.bytes===pin.bytes,'Whole immutable input differs (native size)');inputs.set(d.commit+':'+d.path,{pin:d,decoded:pin.decoded_bytes});memberInputs.set(d.commit+':'+d.path,{pin:d,decoded:pin.decoded_bytes});buffers+=2*pin.decoded_bytes;
    }else{
      const image=snapshot.image;demand(image instanceof NativeAssetImage||image instanceof StockImage,'Missing selected whole native byte bank');
      const member=image instanceof NativeAssetImage?image.index.files.find(p=>p.path===pin.path):image.index.files.find(p=>p.path===image.map.logical_targets.find(t=>t.target===name)?.object);
      demand(member&&member.bytes===pin.bytes&&member.sha256===pin.sha256&&member.bytes<=FILE,'Missing/rebound complete native member');
      for(const part of image.index.parts.filter(p=>p.offset<member.offset+member.bytes&&member.offset<p.offset+p.decoded_bytes)){
        const d=reader.descriptor((image instanceof NativeAssetImage?image.directory:NS)+'/'+part.path),key=d.commit+':'+d.path;
        demand(d.bytes===part.bytes&&part.decoded_bytes<=FILE,'Whole native fragment size differs');
        const old=inputs.get(key);demand(!old||old.decoded===part.decoded_bytes,'Conflicting native containing fragment');inputs.set(key,{pin:d,decoded:part.decoded_bytes});memberInputs.set(key,{pin:d,decoded:part.decoded_bytes});
      }
      buffers+=3*pin.decoded_bytes+member.bytes;
    }
    members.push({pin,inputs:[...memberInputs.values()],buffers});
  }
  const intervals=rows.reduce((n,y)=>n+table[y*2+1],0);
  demand(Number.isSafeInteger(intervals)&&intervals>=0,'Invalid complete projected interval count');
  const completeInputs=list=>list.map(p=>({...p.pin,sha256:'0'.repeat(64),whole_body_consumed:true}));
  const custodyBytes=2*Buffer.byteLength(JSON.stringify({selection:snapshot.selection.sha256,rows,whole_parts:pins,whole_inputs:completeInputs([...inputs.values()]),member_phases:members.map(m=>({part:m.pin.path,whole_inputs:completeInputs(m.inputs),phase_bytes:PHASE})),phase_bytes:PHASE,planned_phase_bytes:PHASE}));
  const projectionBytes=intervals*12+rows.length*12+4+custodyBytes+512;
  return {rows,pins,inputs:[...inputs.values()],members,intervals,projectionBytes,custodyBytes};
}
function sideAdmission(snapshot,plan,carriedBytes) {
  const reader=snapshot.reader;
  demand(Number.isSafeInteger(carriedBytes)&&carriedBytes>=0,'Missing complete native carried-state admission');
  const bytes=reader.runtimeBytes+reader.executionBytes+reader.metadataBytes+reader.outputBytes+carriedBytes+plan.projectionBytes+Math.max(0,...plan.members.map(m=>m.buffers+m.inputs.reduce((n,p)=>n+p.pin.bytes+p.decoded,0))); 
  demand(plan.inputs.length<=512&&bytes<=PHASE,'Complete native side/carry phase exceeds prospective cap');return bytes;
}
export function acquireNativeRows(snapshot,table,rows,options={}) {
  demand(Object.keys(options).every(k=>k==='carry'),'Undeclared native carried state');
  const carry=options.carry;let carriedBytes=0;
  if(carry){const proof=nativeProjections.get(carry);demand(proof,'Missing authenticated native carry');validateNativeRowCarry(carry,proof.snapshot,rows);carriedBytes=proof.bytes;}
  const plan=sidePlan(snapshot,table,rows),plannedBytes=sideAdmission(snapshot,plan,carriedBytes),reader=snapshot.reader;
  // Allocate the complete projection before body reads; every member phase
  // reserves it in full, including portions not yet populated. A member helper
  // never returns native/transport buffers into the next genuine phase.
  const words=new Uint32Array(plan.intervals*3),indices=Uint32Array.from(rows),offsets=new Uint32Array(rows.length+1),counts=new Uint32Array(rows.length);
  let at=0;for(let k=0;k<rows.length;k++){offsets[k]=at;at+=table[rows[k]*2+1]*3;}offsets[rows.length]=at;
  const memberPhases=[];
  const extract=member=>{
    reader.phase();reader.used+=carriedBytes+plan.projectionBytes;
    for(const item of member.inputs)reader.admit(item.pin,item.decoded);
    const pin=member.pin,body=asset(snapshot,pin);
    for(let k=0;k<rows.length;k++){
      const y=rows[k],start=table[y*2]*2,end=start+table[y*2+1]*2;
      for(let i=Math.max(start,pin.offset);i<Math.min(end,pin.offset+pin.words);i+=2){
        const x=body[i-pin.offset],z=body[i-pin.offset+1],bits=snapshot.manifest.coordinateBits,mask=2**bits-1,target=offsets[k]+(i-start)/2*3;
        demand(Number.isSafeInteger(target)&&target>=offsets[k]&&target+2<offsets[k+1],'Foreign native projected ordinal');
        words[target]=x&mask;words[target+1]=(z&mask)+1;words[target+2]=(x>>>bits)+(z>>>bits)*2**(32-bits);
        demand(words[target]<words[target+1]&&words[target+1]<=snapshot.manifest.size,'Native interval exceeds original grid domain');counts[k]++;
      }
    }
    return {part:pin.path,whole_inputs:member.inputs.map(p=>p.pin),phase_bytes:reader.used};
  };
  if(plan.members.length===0){reader.phase();reader.used+=carriedBytes+plan.projectionBytes;}
  for(const member of plan.members)memberPhases.push(extract(member));
  for(let k=0;k<rows.length;k++)demand(counts[k]===table[rows[k]*2+1],'Incomplete projected native row');
  demand(at===words.length,'Incomplete native row projection');
  const digest=projectionSha({rows:indices,offsets,words});
  const product={rows:indices,offsets,words,bytes:plan.projectionBytes,custody:{selection:snapshot.selection.sha256,rows:plan.rows,whole_parts:plan.pins,whole_inputs:plan.inputs.map(p=>p.pin),member_phases:memberPhases,phase_bytes:Math.max(reader.used,...memberPhases.map(p=>p.phase_bytes)),planned_phase_bytes:plannedBytes}};
  nativeProjections.set(product,{snapshot,digest,bytes:plan.projectionBytes,custody:JSON.stringify(product.custody)});return product;
}
export function validateNativeRowCarry(product,snapshot,rows) {
  const proof=nativeProjections.get(product);
  demand(proof&&proof.snapshot===snapshot&&product.bytes===proof.bytes&&JSON.stringify(product.custody)===proof.custody&&same([...product.rows],rows)&&projectionSha(product)===proof.digest,'Missing/altered/incomplete native row carry');
}
function projectedRow(product,k) {
  const out=[];for(let i=product.offsets[k];i<product.offsets[k+1];i+=3)out.push([product.words[i],product.words[i+1],product.words[i+2]]);return out;
}

// Also used by the eventual explicit additive selection hook. Full geometry rows
// are retained, including zero-cell additions: cell conservation alone is weaker.
export function compareRepairLedgers(before,after) {
  const selected=ledger=>{demand(ledger?.kind==='native-additive-repair-ledger-v1'&&ledger.version===1&&hash(ledger.rule_sha256)&&Array.isArray(ledger.scope_ids)&&Array.isArray(ledger.rows)&&ledger.scope_ids.length===ledger.rows.length,'Incomplete selected repair ledger');const seen=new Set();return ledger.rows.filter((r,i)=>{demand(r.component_id===ledger.scope_ids[i]&&!seen.has(r.component_id),'Foreign/duplicate ledger row');seen.add(r.component_id);return ['assigned','zero-cell'].includes(r.disposition);});};
  const old=selected(before),next=new Map(selected(after).map(r=>[r.component_id,r]));
  const keys=['target_id','pixelIndex','base_geometry_sha256','geometry_sha256','geometry','source_receipt_sha256'];
  for(const row of old){const other=next.get(row.component_id);demand(other&&before.rule_sha256===after.rule_sha256&&keys.every(k=>same(row[k],other[k])),'Previously selected full repair primitive lost/rebound: '+row.component_id);}
  return old.length;
}

export function compareIntervals(before,after,{row,ownersBefore,ownersAfter}) {
  const validate=(runs,owners)=>{let end=0;for(const r of runs){demand(Array.isArray(r)&&r.length===3&&r.every(Number.isSafeInteger)&&r[0]>=end&&r[1]>r[0]&&r[2]>0&&owners[r[2]-1],'Invalid complete owner interval');end=r[1];}};
  validate(before,ownersBefore);validate(after,ownersAfter);
  const losses=[];let j=0;
  for(const [start,end,owner]of before){let at=start;while(j<after.length&&after[j][1]<=at)j++;let k=j;while(at<end){const next=after[k];const stop=Math.min(end,next?(next[0]>at?next[0]:next[1]):end);demand(stop>at,'Nonadvancing owner interval');const actual=next&&next[0]<=at?ownersAfter[next[2]-1].id:null,expected=ownersBefore[owner-1].id;if(actual!==expected)losses.push({row,start:at,end:stop,previous_owner:expected,candidate_owner:actual});at=stop;if(next&&at>=next[1])k++;}}
  return losses;
}

export function selectedBootstrap(repo,baseline,candidate,{parentRuntimePath}={}) {
  const runtimePaths=[fs.realpathSync(process.execPath),...(parentRuntimePath?[fs.realpathSync(parentRuntimePath)]:[])];
  const codeRoot=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
  const codePaths=['scripts/run-geographic-check.py','scripts/check-geographic-regression.py','scripts/check-effective-geographic-regression.mjs','src/ownership-codec.js','scripts/evidence/immutable.py','scripts/evidence/geometry.py','scripts/ellipsoidal_area.py','requirements.txt','coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs','coordination/engineering/selected-geography-effective-prevention-20261009/selected-continuous-entry.mjs'];
  const codeStats=codePaths.map(name=>{const file=path.join(codeRoot,name),stat=fs.statSync(file);demand(stat.isFile()&&stat.size<=FILE,'Nonordinary/oversized trusted execution code');return {name,file,stat};});
  const executionBytes=codeStats.reduce((n,p)=>n+p.stat.size,0);
  const launchGit=(process.env.PATH??'').split(path.delimiter).map(p=>path.join(p,'git')).find(p=>{try{return fs.statSync(p).isFile();}catch{return false;}});
  demand(launchGit,'Missing installed Git');runtimePaths.push(fs.realpathSync(launchGit));
  const admittedRuntime=()=>[...new Set(runtimePaths)].reduce((n,p)=>{const stat=fs.statSync(p);demand(stat.isFile()&&stat.size>0,'Nonordinary installed execution runtime');return n+stat.size;},0);
  demand(admittedRuntime()+executionBytes+8*1024*1024+OUTPUT<PHASE,'Complete bootstrap exceeds prospective phase before runtime/code opens');
  // Resolve the full Git implementation (including macOS command-line shim)
  // only after admitting the launcher and its bounded metadata reply.
  const execPath=execFileSync(runtimePaths.at(-1),['--exec-path'],{maxBuffer:4096}).toString().trim();
  const gitExecutable=fs.realpathSync(path.resolve(execPath,'../../bin/git'));runtimePaths.push(gitExecutable);
  const runtimeBytes=admittedRuntime();
  const beforeReader=new ImmutableReader(repo,baseline,{runtimeBytes,executionBytes,gitExecutable}),afterReader=new ImmutableReader(repo,candidate,{runtimeBytes,executionBytes,gitExecutable,budget:beforeReader.budget});
  const identities=[...new Set(runtimePaths)].map(p=>runtimeIdentity(p));
  const runtime=identities.find(p=>p.path===fs.realpathSync(process.execPath)),callerRuntime=parentRuntimePath?identities.find(p=>p.path===fs.realpathSync(parentRuntimePath)):null;
  const executionCode=codeStats.map(({name,file,stat})=>{const body=fs.readFileSync(file);demand(body.length===stat.size,'Trusted execution code changed during whole read');return {path:name,bytes:body.length,mode:stat.mode&0o777,sha256:sha(body)};});
  return {beforeReader,afterReader,runtime,callerRuntime,identities,executionCode};
}

export function inspectSelected(repo,baseline,candidate,{parentRuntimePath}={}) {
  const {beforeReader,afterReader,runtime,callerRuntime,identities,executionCode}=selectedBootstrap(repo,baseline,candidate,{parentRuntimePath});
  const before=loadSelection(beforeReader);
  // loadSelection's raw acquisition buffers are no longer live. Its complete
  // decoded metadata remains retained and is charged during the candidate
  // acquisition; this is a lifecycle boundary, not two simultaneous free phases.
  if(before){afterReader.metadataBytes=8*1024*1024+2*before.metadataBytes;afterReader.phase();}
  const after=loadSelection(afterReader);
  if(!before&&!after)return {version:1,status:'legacy-selection',limits:['Legacy raw polygon gate remains applicable.']};
  demand(before&&after,'Selected native ownership removed or introduced without comparable migration');
  const a=before.manifest,b=after.manifest;
  const metadataBytes=before.metadataBytes+after.metadataBytes+8*1024*1024;
  beforeReader.metadataBytes=afterReader.metadataBytes=metadataBytes;
  // A changed transport body with an unchanged declared selected member must
  // still authenticate against its independently pinned whole container hash.
  for(const snapshot of [before,after])if(snapshot.image)for(const part of snapshot.image.index.parts){const name=(snapshot.image instanceof NativeAssetImage?snapshot.image.directory:NS)+'/'+part.path,own=snapshot.reader.inventory.get(snapshot.reader.version+':'+name),other=(snapshot===before?afterReader:beforeReader).inventory.get((snapshot===before?candidate:baseline)+':'+name);if(!other||own.git_blob_oid!==other.git_blob_oid){snapshot.reader.phase();const encoded=snapshot.reader.read(name,{expected:part.sha256,decoded:part.decoded_bytes});const body=gunzipSync(encoded,{maxOutputLength:part.decoded_bytes});demand(body.length===part.decoded_bytes&&sha(body)===part.decoded_sha256,'Changed selected whole transport body differs');}}
  demand(a.size===b.size&&a.version===b.version&&a.method===b.method&&a.coordinateBits===b.coordinateBits&&same(a.native_latitudes,b.native_latitudes),'Changed native grid/domain requires independent migration');
  demand(same(before.owners.map(p=>[p.index,p.id,p.province_id,p.province_index]),after.owners.map(p=>[p.index,p.id,p.province_id,p.province_index])),'Original stable owner/parent indices rebound');
  beforeReader.phase();
  const rows=loadNativeRowTable;
  const oldRows=rows(before),newRows=rows(after);
  let largestRow=0;for(let y=0;y<a.size;y++)largestRow=Math.max(largestRow,oldRows[y*2+1]+newRows[y*2+1]);
  // Both complete row tables and both complete reconstructed interval rows stay
  // live while containing run cohorts are consumed; they are not free aliases.
  beforeReader.metadataBytes=afterReader.metadataBytes=metadataBytes+oldRows.byteLength+newRows.byteLength+largestRow*24;
  demand(beforeReader.runtimeBytes+beforeReader.executionBytes+beforeReader.metadataBytes+beforeReader.outputBytes<PHASE,'Retained metadata/whole interval rows exceed phase cap');
  const runs=snapshot=>snapshot.manifest.parts.filter(p=>p.kind==='runs');
  const oldParts=runs(before),newParts=runs(after);
  let offset=0;for(let y=0;y<a.size;y++){demand(oldRows[y*2]===offset,'Baseline row partition incomplete');offset+=oldRows[y*2+1];}demand(offset*2===a.runWords,'Baseline rows omitted runs');
  offset=0;for(let y=0;y<b.size;y++){demand(newRows[y*2]===offset,'Candidate row partition incomplete');offset+=newRows[y*2+1];}demand(offset*2===b.runWords,'Candidate rows omitted runs');
  const bodyChanged=(p,snapshot,other)=>{const ownPath=path.posix.join(path.posix.dirname(snapshot.selection.manifest_path),p.path),otherPath=path.posix.join(path.posix.dirname(other.selection.manifest_path),p.path),own=snapshot.reader.inventory.get(snapshot.reader.version+':'+ownPath),prior=other.reader.inventory.get(other.reader.version+':'+otherPath);return !!own!==!!prior||!!own&&(own.mode!==prior.mode||own.git_blob_oid!==prior.git_blob_oid);};
  const changed=oldParts.filter(p=>!newParts.some(q=>same(p,q))||bodyChanged(p,before,after)).concat(newParts.filter(p=>!oldParts.some(q=>same(p,q))||bodyChanged(p,after,before)));
  const additiveRows=new Set([...(before.additive?.patch.rows??[]),...(after.additive?.patch.rows??[])].map(r=>r.y));
  let additiveConservation=null;if(before.additive){demand(after.additive,'Previously selected additive repair ledger removed');additiveConservation=compareVersionedRepairLedgers(before.additive.ledger,after.additive.ledger,{beforeRegistry:before.additive.registry,afterRegistry:after.additive.registry});}
  const affected=[];for(let y=0;y<a.size;y++){const spans=[[oldRows[y*2]*2,(oldRows[y*2]+oldRows[y*2+1])*2],[newRows[y*2]*2,(newRows[y*2]+newRows[y*2+1])*2]];if(additiveRows.has(y)||oldRows[y*2]!==newRows[y*2]||oldRows[y*2+1]!==newRows[y*2+1]||spans.some(([s,e])=>changed.some(p=>s<p.offset+p.words&&p.offset<e)))affected.push(y);}
  // Plan consecutive identical containing rosters, splitting by the actual
  // complete carry/output cost when necessary. Every affected row appears once.
  const phases=[];let lostCells=0;const losses=[];
  const groups=[],wholeGroups=[];let pending=[],pendingKey='';
  const rosterKey=y=>JSON.stringify([nativeParts(before,oldRows,y).map(p=>p.path),nativeParts(after,newRows,y).map(p=>p.path)]);
  const carriedMetadata=()=>2*Buffer.byteLength(JSON.stringify({before:[...beforeReader.inventory.values()],after:[...afterReader.inventory.values()],phases}))+affected.length*32;
  const baseMetadata=beforeReader.metadataBytes;
  const fits=rows=>{
    beforeReader.metadataBytes=afterReader.metadataBytes=baseMetadata+carriedMetadata();
    const previous=sidePlan(before,oldRows,rows),next=sidePlan(after,newRows,rows);
    sideAdmission(before,previous,0);sideAdmission(after,next,previous.projectionBytes);
  };
  for(const y of affected){const key=rosterKey(y);if(pending.length&&key!==pendingKey){wholeGroups.push(pending);pending=[];}pending.push(y);pendingKey=key;}
  if(pending.length)wholeGroups.push(pending);
  const split=rows=>{
    try{fits(rows);groups.push(rows);}catch(error){
      if(rows.length===1||!error.message.includes('phase exceeds prospective cap'))throw error;
      const middle=Math.floor(rows.length/2);split(rows.slice(0,middle));split(rows.slice(middle));
    }
  };
  for(const rows of wholeGroups)split(rows);
  let checkedRows=0;
  for(const group of groups){
    fits(group);
    // This frame returns compact complete intervals and custody only. All whole
    // baseline native/transport buffers are out of scope before candidate opens.
    const previous=acquireNativeRows(before,oldRows,group);validateNativeRowCarry(previous,before,group);
    const next=acquireNativeRows(after,newRows,group,{carry:previous});
    validateNativeRowCarry(previous,before,group);validateNativeRowCarry(next,after,group);
    for(let k=0;k<group.length;k++){
      const y=group[k],oldBase=projectedRow(previous,k),newBase=projectedRow(next,k),old=before.additive?selectedAdditiveRows(before.additive,y,oldBase):oldBase,current=after.additive?selectedAdditiveRows(after.additive,y,newBase):newBase;
      for(const loss of compareIntervals(old,current,{row:y,ownersBefore:before.owners,ownersAfter:after.owners})){
        lostCells+=loss.end-loss.start;demand(losses.length<65536,'Exact native finding output exceeds bounded receipt; refuse acceptance');losses.push(loss);
      }checkedRows++;
    }
    phases.push({first_row:group[0],last_row:group.at(-1),rows:group.length,baseline:previous.custody,candidate:next.custody,baseline_carried_bytes:previous.bytes});
    demand(Buffer.byteLength(JSON.stringify(phases))+Buffer.byteLength(JSON.stringify(losses))<=OUTPUT,'Native phase/finding receipt exceeds admitted output reserve');
  }
  demand(checkedRows===affected.length&&groups.flat().every((y,i)=>y===affected[i]),'Incomplete affected native row comparison');
  return {version:1,method:'selected-native-owner-conservation-v1',status:losses.length?'native-regressions-found':'no-new-native-loss',baseline_selection:before.selection,candidate_selection:after.selection,baseline_receipt_provenance:before.receiptProvenance,candidate_receipt_provenance:after.receiptProvenance,additive_conservation:additiveConservation,affected_rows:affected.length,lost_or_reassigned_cells:lostCells,intervals:losses,phases,runtime,caller_runtime:callerRuntime,execution_runtimes:identities,execution_code_inventory:executionCode,output_reserve_bytes:OUTPUT,input_inventory:[...beforeReader.inventory.values(),...afterReader.inventory.values()],candidate_code_executed:false,limits:['Native owner conservation is not sub-cell polygon coverage or source authority approval.','Only explicit authenticated committed additive hooks are consumed; proposal files never select a release. Continuous primitive-set coverage is enforced separately.']};
}

if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)) {
  const [repo,baseline,candidate,parentRuntimePath]=process.argv.slice(2);const result=inspectSelected(repo,baseline,candidate,{parentRuntimePath});const body=JSON.stringify(result)+'\n';demand(Buffer.byteLength(body)<=OUTPUT,'Generated selected-native receipt exceeds admitted output reserve');process.stdout.write(body);
}
