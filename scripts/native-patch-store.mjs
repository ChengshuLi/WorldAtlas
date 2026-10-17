// Invocation-local native interval storage. This parses data, never authority.
// Keep original JSON wire products; only their large interval arrays live on disk.
import fs from 'node:fs';
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
  this.expected=expected;this.buffer=Buffer.alloc(0);this.at=0;this.bytes=0;this.hash=createHash('sha256');this.done=false;
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
  let buffer=Buffer.allocUnsafe(256),used=0;
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
 append(record){if(this.used+record.length>this.buffer.length)this.flush();record.copy(this.buffer,this.used);this.used+=record.length;}
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

/** The caller authenticates source roles/modes/OIDs and supplies their byte stream.
 * No qualified state escapes before complete JSON syntax, exact bytes/hash and
 * all final row fields pass. Duplicate object keys retain JSON.parse last-wins.
 * rowField also supports an isolated ledger component's native_rows field.
 */
export async function admitNativePatchStore({chunks,expected,directory,size,ownerCount,rowField='rows'}) {
 demand(Number.isSafeInteger(size)&&size>0&&size<=0xffffffff&&Number.isSafeInteger(ownerCount)
  &&ownerCount>0&&ownerCount<=0xffffffff&&['rows','native_rows'].includes(rowField),'Invalid native interval store domain');
 ordinaryDirectory(directory);
 let input,root,runsFd,indexFd,complete=false;
 try {
  root=fs.mkdtempSync(path.join(directory,'native-intervals-'));input=new Input(chunks,expected);
  runsFd=fs.openSync(path.join(root,'runs.bin'),'wx+',0o600);indexFd=fs.openSync(path.join(root,'rows.bin'),'wx+',0o600);
  const runs=new Writer(runsFd),index=new Writer(indexFd),metadata=Object.create(null);
  let rowCount=0,runCount=0,rowsSeen=false,rowsError=null;
  const array=async visit=>{
   await input.char(91);await input.space();if(await input.peek()===93){input.at++;return;}
   while(true){await visit();await input.space();const next=await input.peek();
    if(next===93){input.at++;return;}await input.char(44);
   }
  };
  const parseRuns=async()=>{
   let error=null,count=0,end=0;
   await input.space();
   if(await input.peek()!==91){await input.value();return {error:'Missing complete native intervals',count};}
   await array(async()=>{
    const run=await input.value();
    if(!(Array.isArray(run)&&run.length===3&&run.every(Number.isSafeInteger)&&run[0]>=end
     &&run[1]>run[0]&&run[1]<=size&&run[2]>0&&run[2]<=ownerCount)){
     error??='Invalid complete native interval/owner';return;
    }
    end=run[1];const record=Buffer.allocUnsafe(12);run.forEach((value,i)=>record.writeUInt32LE(value,i*4));
    runs.append(record);count++;
   });
   return {error,count};
  };
  const parseRow=async previous=>{
   const start=runs.position;let y,fields=new Set(),result={error:'Missing complete native runs',count:0};
   await input.space();
   if(await input.peek()!==123){await input.value();return {error:'Missing complete native row',y:previous};}
   await object(async key=>{
    fields.add(key);
    if(key==='runs'){runs.reset(start);result=await parseRuns();}
    else {const value=await input.value();if(key==='y')y=value;}
   });
   const error=fields.size!==2||!fields.has('y')||!fields.has('runs')?'Unknown native row shape':
    !Number.isSafeInteger(y)||y<=previous||y>=size?'Duplicate, unordered or foreign native row':result.error;
   if(error)return {error,y:previous};
   demand(Number.isSafeInteger(start)&&result.count<=0xffffffff,'Native interval offset/count exceeds exact format');
   const record=Buffer.allocUnsafe(16);record.writeUInt32LE(y,0);record.writeBigUInt64LE(BigInt(start),4);record.writeUInt32LE(result.count,12);
   index.append(record);rowCount++;runCount+=result.count;return {y};
  };
  const object=async visit=>{
   await input.char(123);await input.space();if(await input.peek()===125){input.at++;return;}
   while(true){const key=await input.value({key:true});demand(typeof key==='string','Native JSON object key must be a string');await input.char(58);
    await visit(key);await input.space();const next=await input.peek();if(next===125){input.at++;return;}await input.char(44);
   }
  };
  await object(async key=>{
   if(key!==rowField){metadata[key]=await input.value();return;}
   rowsSeen=true;rowsError=null;rowCount=0;runCount=0;runs.reset();index.reset();let previous=-1;
   await input.space();if(await input.peek()!==91){await input.value();rowsError='Missing complete native rows';return;}
   await array(async()=>{const row=await parseRow(previous);rowsError??=row.error??null;previous=row.y;});
  });
  await input.end();demand(rowsSeen&&!rowsError,rowsError??'Missing complete native rows');runs.flush();index.flush();
  let closed=false;const admittedRows=new WeakSet();
  const active=()=>demand(!closed,'Native interval store is closed');
  const rowRecord=buffer=>{
   const row=Object.freeze({y:buffer.readUInt32LE(0),offset:Number(buffer.readBigUInt64LE(4)),count:buffer.readUInt32LE(12)});
   admittedRows.add(row);return row;
  };
  function* rowEntries(){
   active();const buffer=Buffer.allocUnsafe(16*Math.min(4096,rowCount));
   for(let at=0;at<rowCount;){const count=Math.min(4096,rowCount-at);active();readExact(indexFd,buffer,count*16,at*16);
    for(let i=0;i<count;i++){active();yield rowRecord(buffer.subarray(i*16,i*16+16));}at+=count;
   }
  }
  function* intervals(row){
   active();demand(admittedRows.has(row),'Foreign native interval row');const buffer=Buffer.allocUnsafe(12*Math.min(4096,row.count));
   for(let at=0;at<row.count;){const count=Math.min(4096,row.count-at);active();readExact(runsFd,buffer,count*12,row.offset+at*12);
    for(let i=0;i<count;i++){active();yield [buffer.readUInt32LE(i*12),buffer.readUInt32LE(i*12+4),buffer.readUInt32LE(i*12+8)];}at+=count;
   }
  }
  function rowAt(y){
   active();demand(Number.isSafeInteger(y)&&y>=0&&y<size,'Invalid native row lookup');const buffer=Buffer.allocUnsafe(16);let lo=0,hi=rowCount;
   while(lo<hi){const mid=Math.floor((lo+hi)/2);readExact(indexFd,buffer,16,mid*16);if(buffer.readUInt32LE(0)<y)lo=mid+1;else hi=mid;}
   if(lo===rowCount)return null;readExact(indexFd,buffer,16,lo*16);return buffer.readUInt32LE(0)===y?rowRecord(buffer):null;
  }
  const hash=createHash('sha256');let pending='',length=0;
  const write=text=>{pending+=text;length+=text.length;if(length>=16384){hash.update(pending);pending='';length=0;}};
  const ordered=Object.create(null);
  for(const key of [...Object.keys(metadata),rowField].sort())ordered[key]=null;
  const keys=Object.keys(ordered);write('{');
  for(let i=0;i<keys.length;i++){
   const key=keys[i];if(i)write(',');write(JSON.stringify(key)+':');
   if(key!==rowField){write(JSON.stringify(canonical(metadata[key])));continue;}
   write('[');let first=true;
   for(const row of rowEntries()){
    if(!first)write(',');first=false;write('{"runs":[');let firstRun=true;
    for(const run of intervals(row)){if(!firstRun)write(',');firstRun=false;write(JSON.stringify(run));}
    write('],"y":'+row.y+'}');
   }
   write(']');
  }
  write('}\n');if(length)hash.update(pending);
  const canonical_sha256=hash.digest('hex');
  const close=()=>{if(closed)return;closed=true;try{fs.closeSync(runsFd);}finally{try{fs.closeSync(indexFd);}finally{fs.rmSync(root,{recursive:true});}}};
  complete=true;return Object.freeze({metadata:freeze(metadata),canonical_sha256,rowCount,runCount,
   storedBytes:runs.position+index.position,rowEntries,intervals,rowAt,close,[Symbol.dispose]:close});
 } finally {
  try {await input?.close();} catch(error){complete=false;throw error;}
  finally {if(!complete){try{if(runsFd!==undefined)fs.closeSync(runsFd);}
   finally{try{if(indexFd!==undefined)fs.closeSync(indexFd);}finally{if(root)fs.rmSync(root,{recursive:true});}}}}
 }
}
