// Invocation-local native interval storage. This parses data, never authority.
// Keep original JSON wire products; only their large interval arrays live on disk.
import fs from 'node:fs';
import {nativeSequence,isNativeSequence} from '../src/native-grid.js';
import path from 'node:path';
import {createHash} from 'node:crypto';

const demand=(ok,message)=>{if(!ok)throw Error(message);};
const whitespace=b=>b===32||b===9||b===10||b===13;
const canonical=value=>{
 if(Array.isArray(value))return value.map(canonical);
 if(value&&typeof value==='object'){
  const out=Object.create(null);for(const key of Object.keys(value).sort())out[key]=canonical(value[key]);return out;
 }
 demand((value===null||['string','number','boolean'].includes(typeof value))
  &&(typeof value!=='number'||Number.isFinite(value)),'Nonfinite/missing/non-JSON canonical value');return value;
};
const freeze=value=>{if(value&&typeof value==='object'){Object.values(value).forEach(freeze);Object.freeze(value);}return value;};

// Frame complete scalar/metadata values, delegating their syntax and Unicode /
// number semantics to JSON.parse. Domain arrays below frame each triple, never
// a complete dense row. Metadata and an individual scalar remain explicit terms.
class Input {
 constructor(chunks,expected){
  demand(Number.isSafeInteger(expected?.bytes)&&expected.bytes>=0&&/^[a-f0-9]{64}$/.test(expected.sha256),
   'Complete JSON stream identity required');
  this.iterator=chunks[Symbol.asyncIterator]?.()??chunks[Symbol.iterator]?.();
  demand(this.iterator,'Complete JSON stream iterator required');
  this.scalarBuffer=Buffer.allocUnsafe(256);this.expected=expected;this.buffer=Buffer.alloc(0);this.at=0;this.bytes=0;this.hash=createHash('sha256');this.done=false;
 }
 async available(){
  while(this.at===this.buffer.length&&!this.done){
   const next=await this.iterator.next();
   if(next.done){this.done=true;break;}
   demand(Buffer.isBuffer(next.value)||next.value instanceof Uint8Array,'JSON stream requires byte chunks');
   // Snapshot the yielded chunk before any await can let its owner mutate it.
   this.buffer=Buffer.from(next.value);this.at=0;this.bytes+=this.buffer.length;
   demand(this.bytes<=this.expected.bytes,'JSON stream exceeds exact byte identity');this.hash.update(this.buffer);
  }
  return this.at<this.buffer.length;
 }
 async peek(){return await this.available()?this.buffer[this.at]:undefined;}
 async space(){while(await this.available()){while(this.at<this.buffer.length&&whitespace(this.buffer[this.at]))this.at++;if(this.at<this.buffer.length)return;}}
 async char(byte){await this.space();demand(await this.peek()===byte,'Malformed native JSON delimiter');this.at++;}
 async value({key=false}={}){
  await this.space();let quoted=false,escaped=false,pendingSpace=false;const stack=[],parts=[];
  let buffer=this.scalarBuffer,used=0;
  const append=byte=>{if(used===buffer.length){parts.push(buffer);buffer=Buffer.allocUnsafe(8192);used=0;}buffer[used++]=byte;};
  outer:while(await this.available()){
   while(this.at<this.buffer.length){
    const byte=this.buffer[this.at];
    if(!quoted&&!stack.length&&(byte===44||byte===93||byte===125||key&&byte===58))break outer;
    this.at++;
    if(!quoted&&whitespace(byte)){pendingSpace=true;continue;}
    if(pendingSpace){append(32);pendingSpace=false;}append(byte);
    if(quoted){if(escaped)escaped=false;else if(byte===92)escaped=true;else if(byte===34)quoted=false;}
    else if(byte===34)quoted=true;
    else if(byte===91||byte===123)stack.push(byte);
    else if(byte===93||byte===125)demand(stack.pop()===(byte===93?91:123),'Malformed nested native JSON');
   }
  }
  if(!parts.length)return JSON.parse(buffer.subarray(0,used));
  parts.push(buffer.subarray(0,used));return JSON.parse(Buffer.concat(parts));
 }
 async end(){
  await this.space();demand(!await this.available(),'Unexpected data after complete native JSON');
  demand(this.bytes===this.expected.bytes&&this.hash.digest('hex')===this.expected.sha256,'Complete native JSON identity differs');
 }
 async close(){await this.iterator.return?.();}
}
class Writer {
 constructor(fd){this.fd=fd;this.buffer=Buffer.allocUnsafe(64*1024);this.used=0;this.bytes=0;}
 flush(){let at=0;while(at<this.used){const n=fs.writeSync(this.fd,this.buffer,at,this.used-at,this.bytes+at);demand(n>0,'Incomplete native interval write');at+=n;}this.bytes+=this.used;this.used=0;}
 append(record){let at=0;while(at<record.length){if(this.used===this.buffer.length)this.flush();
  const count=Math.min(this.buffer.length-this.used,record.length-at);record.copy(this.buffer,this.used,at,at+count);this.used+=count;at+=count;}}
 get position(){return this.bytes+this.used;}
 reset(position=0){this.flush();fs.ftruncateSync(this.fd,position);this.bytes=position;}
}
function ordinaryDirectory(directory){
 demand(typeof directory==='string'&&path.isAbsolute(directory),'Absolute native scratch directory required');
 for(let p=directory;;p=path.dirname(p)){
  const stat=fs.lstatSync(p);demand(stat.isDirectory()&&!stat.isSymbolicLink(),'Nonordinary native scratch directory');
  if(p===path.dirname(p))break;
 }
}
function readExact(fd,buffer,length,position){
 let at=0;while(at<length){const n=fs.readSync(fd,buffer,at,length-at,position+at);demand(n>0,'Incomplete native interval store');at+=n;}
}

async function array(input,visit){
 await input.char(91);await input.space();if(await input.peek()===93){input.at++;return;}
 while(true){await visit();await input.space();const next=await input.peek();
  if(next===93){input.at++;return;}await input.char(44);
 }
}
async function object(input,visit){
 await input.char(123);await input.space();if(await input.peek()===125){input.at++;return;}
 while(true){const key=await input.value({key:true});demand(typeof key==='string','Native JSON object key must be a string');await input.char(58);
  await visit(key);await input.space();const next=await input.peek();if(next===125){input.at++;return;}await input.char(44);
 }
}

// One parser for both cumulative patch rows and component native_rows. Errors in
// domain fields are deferred until their final containing duplicate field wins.
async function parseRows(input,runs,index,size,ownerCount){
 const start=index.position/16,tripleRecord=Buffer.allocUnsafe(12),indexRecord=Buffer.allocUnsafe(16);let rowCount=0,runCount=0,error=null,previous=-1;
 await input.space();
 if(await input.peek()!==91){await input.value();return {start,rowCount,runCount,error:'Missing complete native rows'};}
 await array(input,async()=>{
  const offset=runs.position;let y,fields=new Set(),result={error:'Missing complete native runs',count:0};
  await input.space();
  if(await input.peek()!==123){await input.value();error??='Missing complete native row';return;}
  await object(input,async key=>{
   fields.add(key);
   if(key!=='runs'){const value=await input.value();if(key==='y')y=value;return;}
   runs.reset(offset);result={error:null,count:0};let end=0;
   await input.space();
   if(await input.peek()!==91){await input.value();result.error='Missing complete native intervals';return;}
   await array(input,async()=>{
    const run=await input.value();
    if(!(Array.isArray(run)&&run.length===3&&run.every(Number.isSafeInteger)&&run[0]>=end
     &&run[1]>run[0]&&run[1]<=size&&run[2]>0&&run[2]<=ownerCount)){
     result.error??='Invalid complete native interval/owner';return;
    }
    end=run[1];run.forEach((value,i)=>tripleRecord.writeUInt32LE(value,i*4));
    runs.append(tripleRecord);result.count++;
   });
  });
  const rowError=fields.size!==2||!fields.has('y')||!fields.has('runs')?'Unknown native row shape':
   !Number.isSafeInteger(y)||y<=previous||y>=size?'Duplicate, unordered or foreign native row':result.error;
  if(rowError){error??=rowError;return;}
  demand(Number.isSafeInteger(offset)&&result.count<=0xffffffff,'Native interval offset/count exceeds exact format');
  indexRecord.writeUInt32LE(y,0);indexRecord.writeBigUInt64LE(BigInt(offset),4);indexRecord.writeUInt32LE(result.count,12);
  index.append(indexRecord);rowCount++;runCount+=result.count;previous=y;
 });
 return {start,rowCount,runCount,error};
}
function* canonicalChunks(value){
 if(isNativeSequence(value)){
  yield '[';let first=true;for(const item of value){if(!first)yield ',';first=false;yield* canonicalChunks(item);}yield ']';return;
 }
 if(value&&typeof value==='object'){
  const ordered=Object.create(null);for(const key of Object.keys(value).sort())ordered[key]=null;
  yield '{';let first=true;for(const key of Object.keys(ordered)){if(!first)yield ',';first=false;yield JSON.stringify(key)+':';yield* canonicalChunks(value[key]);}yield '}';return;
 }
 yield JSON.stringify(canonical(value));
}
function* canonicalObject(metadata,rowField,rowChunks,overrides={}){
 demand(overrides&&typeof overrides==='object'&&!Array.isArray(overrides)&&(!rowField||!Object.hasOwn(overrides,rowField)),
  'Canonical overrides cannot replace stored native rows');
 const fields=Object.assign(Object.create(null),metadata,overrides),ordered=Object.create(null);
 for(const key of [...Object.keys(fields),...(rowField?[rowField]:[])].sort())ordered[key]=null;
 yield '{';let first=true;
 for(const key of Object.keys(ordered)){
  if(!first)yield ',';first=false;yield JSON.stringify(key)+':';
  if(key===rowField)yield* rowChunks();else yield* canonicalChunks(fields[key]);
 }
 yield '}';
}
function hashChunks(chunks){
 const hash=createHash('sha256');let pending='';
 for(const chunk of chunks){pending+=chunk;if(pending.length>=16384){hash.update(pending);pending='';}}
 if(pending)hash.update(pending);return hash.digest('hex');
}

/** Parse original wire JSON into invocation-owned storage, never authority.
 * The caller authenticates roles/modes/OIDs and passes the original byte stream.
 * Full syntax, exact bytes/hash and final row domains precede returned cursors.
 */
async function admitStore({chunks,expected,directory,size,ownerCount,rowField='rows',envelopePaths},ledger){
 demand(Number.isSafeInteger(size)&&size>0&&size<=0xffffffff&&Number.isSafeInteger(ownerCount)
  &&ownerCount>0&&ownerCount<=0xffffffff&&['rows','native_rows'].includes(rowField),'Invalid native interval store domain');
 ordinaryDirectory(directory);
 let input,root,complete=false,closed=false;const fds=[];
 try {
  root=fs.mkdtempSync(path.join(directory,'native-intervals-'));input=new Input(chunks,expected);
  const open=name=>{const fd=fs.openSync(path.join(root,name),'wx+',0o600);fds.push(fd);return fd;};
  const vectorFd=open('vectors.bin'),vectorIndexFd=open('vectors-index.bin'),vectors=new Writer(vectorFd),vectorIndex=new Writer(vectorIndexFd);
  const runsFd=open('runs.bin'),indexFd=open('rows.bin'),runs=new Writer(runsFd),index=new Writer(indexFd);
  const componentFd=ledger?open('components.bin'):null,metadataFd=ledger?open('metadata.bin'):null;
  const components=ledger?new Writer(componentFd):null,meta=ledger?new Writer(metadataFd):null;
  const metadata=Object.create(null),admittedRows=new WeakSet(),admittedComponents=new WeakMap();
  let rowsSeen=false,rowsError=null,range={start:0,rowCount:0,runCount:0},componentCount=0;
  const active=()=>demand(!closed,'Native interval store is closed');
  async function metadataValue(){
   await input.space();if(await input.peek()!==91)return input.value();
   const start=vectorIndex.position,countRecord=Buffer.alloc(16);let count=0,valueError;
   await array(input,async()=>{
    const value=await input.value();let body;
    try{body=Buffer.from(JSON.stringify(canonical(value)));}catch(error){valueError??=error;body=Buffer.from('null');}
    countRecord.writeBigUInt64LE(BigInt(vectors.position),0);countRecord.writeBigUInt64LE(BigInt(body.length),8);
    vectorIndex.append(countRecord);vectors.append(body);count++;
   });
   vectors.flush();vectorIndex.flush();
   const entryAt=ordinal=>{
    active();if(valueError)throw valueError;const record=Buffer.allocUnsafe(16);readExact(vectorIndexFd,record,16,start+ordinal*16);
    const length=Number(record.readBigUInt64LE(8)),body=Buffer.allocUnsafe(length);
    readExact(vectorFd,body,length,Number(record.readBigUInt64LE(0)));return freeze(JSON.parse(body));
   };
   return nativeSequence(count,function*(){for(let i=0;i<count;i++)yield entryAt(i);},{entryAt});
  }
  const rowRecord=buffer=>{
   const row=Object.freeze({y:buffer.readUInt32LE(0),offset:Number(buffer.readBigUInt64LE(4)),count:buffer.readUInt32LE(12)});
   admittedRows.add(row);return row;
  };
  function* rowEntries(selected=range,{windowRecords=4096}={}){
   active();demand(Number.isSafeInteger(windowRecords)&&windowRecords>0,'Invalid native cursor window');const buffer=Buffer.allocUnsafe(16*Math.min(windowRecords,selected.rowCount));
   for(let at=0;at<selected.rowCount;){const count=Math.min(windowRecords,selected.rowCount-at);active();readExact(indexFd,buffer,count*16,(selected.start+at)*16);
    for(let i=0;i<count;i++){active();yield rowRecord(buffer.subarray(i*16,i*16+16));}at+=count;
   }
  }
  function* intervals(row,{windowRecords=4096}={}){
   active();demand(Number.isSafeInteger(windowRecords)&&windowRecords>0,'Invalid native cursor window');demand(admittedRows.has(row),'Foreign native interval row');const buffer=Buffer.allocUnsafe(12*Math.min(windowRecords,row.count));
   for(let at=0;at<row.count;){const count=Math.min(windowRecords,row.count-at);active();readExact(runsFd,buffer,count*12,row.offset+at*12);
    for(let i=0;i<count;i++){active();yield [buffer.readUInt32LE(i*12),buffer.readUInt32LE(i*12+4),buffer.readUInt32LE(i*12+8)];}at+=count;
   }
  }
  function rowAt(y,selected=range){
   active();demand(Number.isSafeInteger(y)&&y>=0&&y<size,'Invalid native row lookup');const buffer=Buffer.allocUnsafe(16);let lo=0,hi=selected.rowCount;
   while(lo<hi){const mid=Math.floor((lo+hi)/2);readExact(indexFd,buffer,16,(selected.start+mid)*16);if(buffer.readUInt32LE(0)<y)lo=mid+1;else hi=mid;}
   if(lo===selected.rowCount)return null;readExact(indexFd,buffer,16,(selected.start+lo)*16);return buffer.readUInt32LE(0)===y?rowRecord(buffer):null;
  }
  function* rowChunks(selected){
   yield '[';let first=true;
   for(const row of rowEntries(selected)){
    if(!first)yield ',';first=false;yield '{"runs":[';let firstRun=true;
    for(const run of intervals(row)){if(!firstRun)yield ',';firstRun=false;yield JSON.stringify(run);}
    yield '],"y":'+row.y+'}';
   }
   yield ']';
  }
  const componentRecord=(buffer,ordinal)=>{
   const descriptor={metaOffset:Number(buffer.readBigUInt64LE(0)),metaBytes:Number(buffer.readBigUInt64LE(8)),
    start:Number(buffer.readBigUInt64LE(16)),rowCount:Number(buffer.readBigUInt64LE(24)),runCount:Number(buffer.readBigUInt64LE(32)),
    hasNativeRows:buffer.readUInt32LE(40)===1};
   const handle=Object.freeze({ordinal,canonical_sha256:buffer.subarray(48,80).toString('hex'),
    rowCount:descriptor.rowCount,runCount:descriptor.runCount,hasNativeRows:descriptor.hasNativeRows});
   admittedComponents.set(handle,descriptor);return handle;
  };
  function* componentEntries({windowRecords=512}={}){
   active();demand(Number.isSafeInteger(windowRecords)&&windowRecords>0,'Invalid native cursor window');const buffer=Buffer.allocUnsafe(80*Math.min(windowRecords,componentCount));
   for(let at=0;at<componentCount;){const count=Math.min(windowRecords,componentCount-at);active();readExact(componentFd,buffer,count*80,at*80);
    for(let i=0;i<count;i++){active();yield componentRecord(buffer.subarray(i*80,i*80+80),at+i);}at+=count;
   }
  }
  function componentAt(ordinal){
   active();demand(Number.isSafeInteger(ordinal),'Invalid native component ordinal');
   if(ordinal<0||ordinal>=componentCount)return undefined;
   const buffer=Buffer.allocUnsafe(80);readExact(componentFd,buffer,80,ordinal*80);return componentRecord(buffer,ordinal);
  }
  const componentDescriptor=handle=>{active();const descriptor=admittedComponents.get(handle);demand(descriptor,'Foreign native component');return descriptor;};
  function componentMetadata(handle){
   const {metaBytes,metaOffset}=componentDescriptor(handle),buffer=Buffer.allocUnsafe(metaBytes);readExact(metadataFd,buffer,metaBytes,metaOffset);
   return freeze(JSON.parse(buffer));
  }
  function componentRows(handle,options){return rowEntries(componentDescriptor(handle),options);}
  function* componentCanonicalChunks(handle,{overrides={},newline=true}={}){
   const selected=componentDescriptor(handle),fields=componentMetadata(handle);
   demand(!Object.hasOwn(overrides,'native_rows'),'Canonical overrides cannot replace stored native rows');
   yield* canonicalObject(fields,selected.hasNativeRows?'native_rows':null,()=>rowChunks(selected),overrides);
   if(newline)yield '\n';
  }
  const parseComponent=async()=>{
   const fields=Object.create(null),runStart=runs.position,indexStart=index.position;
   let selected={start:indexStart/16,rowCount:0,runCount:0,error:null},hasNativeRows=false;
   await input.space();
   if(await input.peek()!==123){await input.value();rowsError??='Missing complete ledger component';return;}
   await object(input,async key=>{
    if(key!=='native_rows'){fields[key]=await input.value();return;}
    hasNativeRows=true;runs.reset(runStart);index.reset(indexStart);selected=await parseRows(input,runs,index,size,ownerCount);
   });
   if(selected.error){rowsError??=selected.error;return;}
   // Canonicalization can reject a domain value that a later duplicate root rows
   // replaces. Keep parsing full syntax, but defer this error as for native rows.
   let body;
   try{body=Buffer.from(JSON.stringify(canonical(fields)));}
   catch(error){rowsError??=error.message;return;}
   runs.flush();index.flush();
   const canonical_sha256=hashChunks((function*(){yield* canonicalObject(fields,hasNativeRows?'native_rows':null,()=>rowChunks(selected));yield '\n';})());
   const record=Buffer.alloc(80),offset=meta.position;
   for(const [i,value] of [offset,body.length,selected.start,selected.rowCount,selected.runCount].entries()){
    demand(Number.isSafeInteger(value),'Native component offset/count exceeds exact format');record.writeBigUInt64LE(BigInt(value),i*8);
   }
   record.writeUInt32LE(hasNativeRows?1:0,40);Buffer.from(canonical_sha256,'hex').copy(record,48);
   meta.append(body);components.append(record);componentCount++;range.rowCount+=selected.rowCount;range.runCount+=selected.runCount;
  };
  async function envelopeObject(prefix=[]){
   const fields=Object.create(null);
   await object(input,async key=>{
    const here=[...prefix,key],matches=envelopePaths.filter(p=>here.every((part,i)=>p[i]===part));
    if(matches.some(p=>p.length===here.length)){
     const selected=await parseRows(input,runs,index,size,ownerCount);runs.flush();index.flush();
     const wrap=row=>Object.freeze({y:row.y,runs:nativeSequence(row.count,()=>intervals(row))});
     const check=()=>{active();demand(!selected.error,selected.error);};
     fields[key]=nativeSequence(selected.rowCount,function*(){check();for(const row of rowEntries(selected))yield wrap(row);},
      {rowAt:y=>{check();const row=rowAt(y,selected);return row?wrap(row):undefined;}});
    }else if(matches.length){
     await input.space();fields[key]=await input.peek()===123?await envelopeObject(here):await metadataValue();
    }else fields[key]=await metadataValue();
   });return fields;
  }
  if(envelopePaths)Object.assign(metadata,await envelopeObject());else
  await object(input,async key=>{
   if(key!==rowField){metadata[key]=await metadataValue();return;}
   rowsSeen=true;rowsError=null;componentCount=0;range={start:0,rowCount:0,runCount:0};runs.reset();index.reset();
   if(!ledger){range=await parseRows(input,runs,index,size,ownerCount);rowsError=range.error;return;}
   components.reset();meta.reset();await input.space();
   if(await input.peek()!==91){await input.value();rowsError='Missing complete ledger rows';return;}
   await array(input,parseComponent);
  });
  await input.end();if(!envelopePaths)demand(rowsSeen&&!rowsError,rowsError??'Missing complete native rows');runs.flush();index.flush();components?.flush();meta?.flush();
  const canonical_sha256=hashChunks((function*(){
   if(envelopePaths){yield* canonicalChunks(metadata);yield '\n';return;}
   yield* canonicalObject(metadata,rowField,function*(){
    if(!ledger){yield* rowChunks(range);return;}
    yield '[';let first=true;for(const component of componentEntries()){
     if(!first)yield ',';first=false;yield* componentCanonicalChunks(component,{newline:false});
    }yield ']';
   });yield '\n';
  })());
  const close=()=>{if(closed)return;closed=true;let error;
   for(const fd of fds)try{fs.closeSync(fd);}catch(e){error??=e;}
   try{fs.rmSync(root,{recursive:true});}catch(e){error??=e;}if(error)throw error;
  };
  const common={metadata:freeze(metadata),canonical_sha256,runCount:range.runCount,
   storedBytes:runs.position+index.position+vectors.position+vectorIndex.position+(components?.position??0)+(meta?.position??0),intervals,close,[Symbol.dispose]:close};
  complete=true;return Object.freeze(ledger?
   {...common,componentCount,nativeRowCount:range.rowCount,componentEntries,componentAt,componentMetadata,componentRows,componentCanonicalChunks}:
   {...common,rowCount:range.rowCount,rowEntries:options=>rowEntries(range,options),rowAt});
 } finally {
  try {await input?.close();} catch(error){complete=false;throw error;}
  finally {if(!complete){let error;for(const fd of fds)try{fs.closeSync(fd);}catch(e){error??=e;}
   try{if(root)fs.rmSync(root,{recursive:true});}catch(e){error??=e;}if(error)throw error;}}
 }
}
export const admitNativePatchStore=options=>admitStore(options,false);
export const admitNativeLedgerStore=options=>admitStore({...options,rowField:'rows'},true);

export const admitNativeEnvelopeStore=options=>admitStore({...options,envelopePaths:options.envelopePaths??[['current_rows'],['acquisition','predecessor_rows'],['native','rows']]},false);
