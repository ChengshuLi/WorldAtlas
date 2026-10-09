// Trusted immutable data reader. Proposed project code is never imported.
import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {fileURLToPath} from 'node:url';
import {unshuffleOwnershipBytes} from '../src/ownership-codec.js';

const FILE=32*1024*1024, PHASE=256*1024*1024, OUTPUT=4*1024*1024;
const sha=b=>createHash('sha256').update(b).digest('hex');
const demand=(v,m)=>{if(!v)throw Error(m);};
const hash=v=>typeof v==='string'&&/^[a-f0-9]{64}$/.test(v);
const commit=v=>typeof v==='string'&&/^[a-f0-9]{40}$/.test(v);
const safe=v=>typeof v==='string'&&v&&!v.includes('\\')&&!v.includes('\0')&&!path.isAbsolute(v)&&v.split('/').every(p=>p&&p!=='.'&&p!=='..');
const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
const installedRuntimes=new Map();
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

function validateParts(manifest) {
  demand(manifest.version===2&&manifest.method==='native-linear-evenodd-first-owner-v1'&&Number.isSafeInteger(manifest.size)&&manifest.size>1&&manifest.coordinateBits===Math.ceil(Math.log2(manifest.size)),'Unsupported selected ownership domain');
  demand(Array.isArray(manifest.parts)&&manifest.parts.length>0&&manifest.parts.length<=512,'Missing native whole parts');
  const names=new Set();
  for(const kind of ['rows','runs']){let offset=0;const parts=manifest.parts.filter(p=>p.kind===kind);demand(parts.length>0,'Missing native '+kind);for(const p of parts){demand(safe(p.path)&&!names.has(p.path)&&p.offset===offset&&Number.isSafeInteger(p.words)&&p.words>0&&p.words%2===0&&p.encoding==='byte-shuffle'&&p.decoded_bytes===p.words*4&&p.decoded_bytes<=FILE&&p.bytes>0&&p.bytes<=FILE&&hash(p.sha256)&&hash(p.decoded_sha256),'Invalid complete native partition');names.add(p.path);offset+=p.words;}demand(offset===(kind==='rows'?manifest.size*2:manifest.runWords),'Native partition omitted words');}
}

export function loadSelection(reader) {
  const has=reader.git('ls-tree','-z',reader.version,'--','data/ownership-selection.json').length;
  if(!has)return null;
  const selection=reader.json('data/ownership-selection.json');
  demand(same(Object.keys(selection).sort(),['manifest_path','method','release_id','sha256','version']),'Unsupported committed additive/ownership selection; no proposal scanning');
  demand(selection.version===1&&selection.method==='native-linear-evenodd-first-owner-v1'&&safe(selection.manifest_path)&&hash(selection.sha256),'Unsupported ownership selection');
  const manifest=reader.json(selection.manifest_path,{expected:selection.sha256});validateParts(manifest);
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
  let image;
  for(const part of manifest.parts){const name=path.posix.join(path.posix.dirname(selection.manifest_path),part.path);
    if(reader.git('ls-tree','-z',reader.version,'--',name).length)reader.descriptor(name);
    else{demand(selection.manifest_path==='data/canonical-grid/eastern-v8/manifest.json','Missing selected ordinary bank asset');image??=new StockImage(reader);const target=image.map.logical_targets.find(p=>p.target===name);demand(target&&target.bytes===part.bytes&&target.sha256===part.sha256,'Selected native asset absent from complete bank');}}
  if(image)for(const part of image.index.parts){const actual=reader.descriptor(NS+'/'+part.path);demand(actual.bytes===part.bytes,'Whole selected container length differs');}
  return {selection,manifest,owners,image,receiptProvenance,metadataBytes:decoded.length+JSON.stringify(manifest).length+(image?JSON.stringify(image.map).length:0),reader};
}

function asset(snapshot,pin) {
  const {reader,selection}=snapshot,name=path.posix.join(path.posix.dirname(selection.manifest_path),pin.path);
  const exists=reader.git('ls-tree','-z',reader.version,'--',name).length;
  const decodedReserve=pin.decoded_bytes*(exists?2:3);
  demand(reader.used+decodedReserve<=PHASE,'Complete shuffled/canonical native representations exceed cap');reader.used+=decodedReserve;
  let raw;
  if(exists)raw=reader.read(name,{expected:pin.sha256,decoded:pin.decoded_bytes});
  else {
    demand(selection.manifest_path==='data/canonical-grid/eastern-v8/manifest.json','Missing selected ordinary bank asset');
    const image=snapshot.image??new StockImage(reader);raw=image.logical(name,pin);
  }
  demand(raw.length===pin.bytes&&sha(raw)===pin.sha256,'Whole selected native encoded body differs');
  const shuffled=gunzipSync(raw,{maxOutputLength:pin.decoded_bytes});demand(shuffled.length===pin.decoded_bytes,'Native whole decoded length differs');
  const words=unshuffleOwnershipBytes(shuffled,pin.words);
  const canonical=Buffer.alloc(words.length*4);for(let i=0;i<words.length;i++)canonical.writeUInt32LE(words[i],i*4);
  demand(sha(canonical)===pin.decoded_sha256,'Native canonical unshuffled words differ');return words;
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

export function inspectSelected(repo,baseline,candidate,{parentRuntimePath}={}) {
  const runtimePaths=[fs.realpathSync(process.execPath),...(parentRuntimePath?[fs.realpathSync(parentRuntimePath)]:[])];
  const codeRoot=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
  const codePaths=['scripts/run-geographic-check.py','scripts/check-geographic-regression.py','scripts/check-effective-geographic-regression.mjs','src/ownership-codec.js','scripts/evidence/immutable.py','scripts/evidence/geometry.py','scripts/ellipsoidal_area.py','requirements.txt'];
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
  const before=loadSelection(beforeReader),after=loadSelection(afterReader);
  if(!before&&!after)return {version:1,status:'legacy-selection',limits:['Legacy raw polygon gate remains applicable.']};
  demand(before&&after,'Selected native ownership removed or introduced without comparable migration');
  const a=before.manifest,b=after.manifest;
  // A changed transport body with an unchanged declared selected member must
  // still authenticate against its independently pinned whole container hash.
  for(const snapshot of [before,after])if(snapshot.image)for(const part of snapshot.image.index.parts){const name=NS+'/'+part.path,own=snapshot.reader.inventory.get(snapshot.reader.version+':'+name),other=(snapshot===before?afterReader:beforeReader).inventory.get((snapshot===before?candidate:baseline)+':'+name);if(!other||own.git_blob_oid!==other.git_blob_oid){snapshot.reader.phase();const encoded=snapshot.reader.read(name,{expected:part.sha256,decoded:part.decoded_bytes});const body=gunzipSync(encoded,{maxOutputLength:part.decoded_bytes});demand(body.length===part.decoded_bytes&&sha(body)===part.decoded_sha256,'Changed selected whole transport body differs');}}
  demand(a.size===b.size&&a.version===b.version&&a.method===b.method&&a.coordinateBits===b.coordinateBits&&same(a.native_latitudes,b.native_latitudes),'Changed native grid/domain requires independent migration');
  demand(same(before.owners.map(p=>[p.index,p.id,p.province_id,p.province_index]),after.owners.map(p=>[p.index,p.id,p.province_id,p.province_index])),'Original stable owner/parent indices rebound');
  const metadataBytes=before.metadataBytes+after.metadataBytes+8*1024*1024;
  beforeReader.metadataBytes=metadataBytes;afterReader.metadataBytes=metadataBytes;
  beforeReader.phase();
  const rows=snapshot=>{const pins=snapshot.manifest.parts.filter(p=>p.kind==='rows');demand(pins.length===1,'Unsupported split native row table');return asset(snapshot,pins[0]);};
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
  const affected=[];for(let y=0;y<a.size;y++){const spans=[[oldRows[y*2]*2,(oldRows[y*2]+oldRows[y*2+1])*2],[newRows[y*2]*2,(newRows[y*2]+newRows[y*2+1])*2]];if(oldRows[y*2]!==newRows[y*2]||oldRows[y*2+1]!==newRows[y*2+1]||spans.some(([s,e])=>changed.some(p=>s<p.offset+p.words&&p.offset<e)))affected.push(y);}
  // A genuine detached cohort owns both sides' whole containing parts. Its
  // decoded words are discarded before resetting admission for another cohort.
  let cache=new Map(),cacheKey='';const phases=[];
  const needed=(snapshot,table,y)=>{const start=table[y*2]*2,end=start+table[y*2+1]*2;return runs(snapshot).filter(p=>start<p.offset+p.words&&p.offset<end);};
  const row=(snapshot,table,y)=>{const start=table[y*2]*2,end=start+table[y*2+1]*2,out=[];for(const p of needed(snapshot,table,y)){const words=cache.get(snapshot.reader.version+':'+p.path);for(let i=Math.max(start,p.offset);i<Math.min(end,p.offset+p.words);i+=2){const x=words[i-p.offset],z=words[i-p.offset+1],bits=snapshot.manifest.coordinateBits,mask=2**bits-1;out.push([x&mask,(z&mask)+1,(x>>>bits)+(z>>>bits)*2**(32-bits)]);}}demand(out.length===table[y*2+1]&&out.every(r=>r[1]<=a.size),'Complete row extraction differs');return out;};
  const losses=[];let lostCells=0;
  for(const y of affected){const roster=[...needed(before,oldRows,y).map(p=>({snapshot:before,p})),...needed(after,newRows,y).map(p=>({snapshot:after,p}))];const key=JSON.stringify(roster.map(({snapshot,p})=>[snapshot.reader.version,p.path]));if(key!==cacheKey){cache.clear();beforeReader.phase();cacheKey=key;for(const {snapshot,p}of roster)cache.set(snapshot.reader.version+':'+p.path,asset(snapshot,p));phases.push({first_row:y,input_bytes:beforeReader.used,descriptors:beforeReader.charged.size});}const previous=row(before,oldRows,y),next=row(after,newRows,y);const found=compareIntervals(previous,next,{row:y,ownersBefore:before.owners,ownersAfter:after.owners});for(const loss of found){lostCells+=loss.end-loss.start;demand(losses.length<65536,'Exact native finding output exceeds bounded receipt; refuse acceptance');losses.push(loss);}}
  cache.clear();
  return {version:1,method:'selected-native-owner-conservation-v1',status:losses.length?'native-regressions-found':'no-new-native-loss',baseline_selection:before.selection,candidate_selection:after.selection,baseline_receipt_provenance:before.receiptProvenance,candidate_receipt_provenance:after.receiptProvenance,affected_rows:affected.length,lost_or_reassigned_cells:lostCells,intervals:losses,phases,runtime,caller_runtime:callerRuntime,execution_runtimes:identities,execution_code_inventory:executionCode,output_reserve_bytes:OUTPUT,input_inventory:[...beforeReader.inventory.values(),...afterReader.inventory.values()],candidate_code_executed:false,limits:['Native owner conservation is not sub-cell polygon coverage or source authority approval.','Explicit additive selection is unsupported until its normal activation contract is integrated; proposal files never select a release.']};
}

if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)) {
  const [repo,baseline,candidate,parentRuntimePath]=process.argv.slice(2);const result=inspectSelected(repo,baseline,candidate,{parentRuntimePath});const body=JSON.stringify(result)+'\n';demand(Buffer.byteLength(body)<=OUTPUT,'Generated selected-native receipt exceeds admitted output reserve');process.stdout.write(body);
}
