import fs from 'node:fs';
import path from 'node:path';
import {randomUUID} from 'node:crypto';

// Local ownership of one receipt prevents concurrent CLI dispatches and preserves
// the last complete checkpoint across interruption. No provider operation lives here.
export function openLeaseCheckpoint(output) {
 if(!output)throw Error('Mutating claim actions require --out for a durable checkpoint');
 const target=path.join(fs.realpathSync(path.dirname(path.resolve(output))),path.basename(output));
 const lock=target+'.lock',owner=path.join(lock,'owner.json'),identity={pid:process.pid,id:randomUUID()};
 const readTarget=()=>{
  let stat;try{stat=fs.lstatSync(target);}catch(e){if(e.code==='ENOENT')return null;throw e;}
  if(!stat.isFile()||stat.isSymbolicLink()||stat.size>65536)throw Error('Checkpoint must be a bounded ordinary file');
  return fs.readFileSync(target,'utf8');
 };
 try{fs.mkdirSync(lock,{mode:0o700});}
 catch(error){
  if(error.code!=='EEXIST')throw error;
  const stat=fs.lstatSync(lock);if(!stat.isDirectory()||stat.isSymbolicLink())throw Error('Checkpoint lock is not ordinary');
  const os=fs.lstatSync(owner);if(!os.isFile()||os.isSymbolicLink()||os.size>2048)throw Error('Checkpoint lock owner is invalid');
  const old=JSON.parse(fs.readFileSync(owner,'utf8'));
  if(!Number.isSafeInteger(old.pid)||old.pid<1||typeof old.id!=='string')throw Error('Checkpoint lock owner is invalid');
  try{process.kill(old.pid,0);throw Error('Another process owns this checkpoint');}catch(e){if(e.code!=='ESRCH')throw e;}
  // A dead process cannot cross another dispatch boundary. Retain its receipt;
  // remove only its unchanged ordinary local lock, never an output directory.
  if(fs.readFileSync(owner,'utf8')!==JSON.stringify(old))throw Error('Checkpoint lock changed');
  fs.unlinkSync(owner);fs.rmdirSync(lock);fs.mkdirSync(lock,{mode:0o700});
 }
 fs.writeFileSync(owner,JSON.stringify(identity),{flag:'wx',mode:0o600});
 let last,closed=false;
 const close=()=>{if(closed)return;closed=true;if(fs.readFileSync(owner,'utf8')!==JSON.stringify(identity))throw Error('Checkpoint lock ownership changed');fs.unlinkSync(owner);fs.rmdirSync(lock);};
 try{
  last=readTarget();
  const stored=last===null?null:JSON.parse(last);
  if(last!==null&&(!stored||typeof stored!=='object'||Array.isArray(stored)||stored.status!=='pending'))throw Error('Existing completed or unrelated receipt must be preserved; use a fresh --out');
  return {stored,close,write(value){
   if(closed||readTarget()!==last)throw Error('Checkpoint changed outside this request');
   const raw=JSON.stringify(value,null,2)+'\n';if(Buffer.byteLength(raw)>65536)throw Error('Checkpoint exceeds local receipt budget');
   const temporary=target+'.'+identity.id+'.tmp';let fd;
   try{fd=fs.openSync(temporary,'wx',0o600);fs.writeFileSync(fd,raw);fs.fsyncSync(fd);fs.closeSync(fd);fd=undefined;
    if(readTarget()!==last)throw Error('Checkpoint changed before publication');
    fs.renameSync(temporary,target);last=raw;
    const directory=fs.openSync(path.dirname(target),'r');try{fs.fsyncSync(directory);}finally{fs.closeSync(directory);}
   }finally{if(fd!==undefined)fs.closeSync(fd);if(fs.existsSync(temporary))fs.unlinkSync(temporary);}
  }};
 }catch(error){close();throw error;}
}
