import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {constants,createHash,createPublicKey,createPrivateKey,randomBytes,publicEncrypt,privateDecrypt,createCipheriv,createDecipheriv} from 'node:crypto';

const suite='RSA-OAEP-256+A256GCM',maxBytes=256*1024*1024;
const sha=value=>createHash('sha256').update(value).digest('hex');
const need=(condition)=>{if(!condition)throw Error('Private backup envelope validation failed');};
const contextFields=['purpose','repository','primary_main_commit','run_id','run_attempt','window_comment_id','source_fingerprint','project_id','branch_id'];
function checkedContext(context){
 need(context&&JSON.stringify(Object.keys(context).sort())===JSON.stringify([...contextFields].sort())&&contextFields.every(k=>typeof context[k]==='string')&&Buffer.byteLength(JSON.stringify(context))<=4096);
 need(context.purpose==='worldatlas-private-sql-backup'&&context.repository==='ChengshuLi/WorldAtlas'&&/^[a-f0-9]{40}$/.test(context.primary_main_commit)&&/^[a-f0-9]{64}$/.test(context.source_fingerprint)&&['run_id','run_attempt','window_comment_id'].every(k=>/^[1-9]\d*$/.test(context[k]))&&context.project_id==='weathered-lab-37571695'&&context.branch_id==='br-summer-butterfly-ar8qikk5');return context;
}
function checkedKey(value,privateKey=false){
 need((typeof value==='string'||Buffer.isBuffer(value))&&Buffer.byteLength(value)<=32768);
 const key=privateKey?createPrivateKey(value):createPublicKey(value);
 need(key.asymmetricKeyType==='rsa'&&key.asymmetricKeyDetails?.modulusLength>=3072&&key.asymmetricKeyDetails.modulusLength<=8192);return key;
}
export function backupRecipientFingerprint(publicKey){return sha(checkedKey(publicKey).export({type:'spki',format:'der'}));}
const header=value=>Buffer.from(JSON.stringify({version:value.version,suite:value.suite,recipient_sha256:value.recipient_sha256,context:value.context,plaintext_bytes:value.plaintext_bytes,plaintext_sha256:value.plaintext_sha256}));
export function sealRecoveryBackup({bytes,publicKey,context}){
 need(Buffer.isBuffer(bytes)&&bytes.length>=5&&bytes.length<=maxBytes&&bytes.subarray(0,5).toString()==='PGDMP');
 const recipient=checkedKey(publicKey),key=randomBytes(32),iv=randomBytes(12);
 try{
  const envelope={version:1,suite,recipient_sha256:backupRecipientFingerprint(publicKey),context:checkedContext(context),plaintext_bytes:bytes.length,plaintext_sha256:sha(bytes)};
  const cipher=createCipheriv('aes-256-gcm',key,iv);cipher.setAAD(header(envelope));const ciphertext=Buffer.concat([cipher.update(bytes),cipher.final()]);
  Object.assign(envelope,{ciphertext_bytes:ciphertext.length,ciphertext_sha256:sha(ciphertext),wrapped_key:publicEncrypt({key:recipient,padding:constants.RSA_PKCS1_OAEP_PADDING,oaepHash:'sha256'},key).toString('base64'),iv:iv.toString('base64'),tag:cipher.getAuthTag().toString('base64')});
  const verify=createDecipheriv('aes-256-gcm',key,iv);verify.setAAD(header(envelope));verify.setAuthTag(Buffer.from(envelope.tag,'base64'));const readback=Buffer.concat([verify.update(ciphertext),verify.final()]);
  try{need(readback.length===bytes.length&&sha(readback)===envelope.plaintext_sha256);}finally{readback.fill(0);}
  return {envelope,ciphertext};
 }finally{key.fill(0);}
}
function decoded(value,bytes){need(typeof value==='string'&&value.length<=2048);const result=Buffer.from(value,'base64');need(result.length===bytes&&result.toString('base64')===value);return result;}
export function openRecoveryBackup({envelope,ciphertext,privateKey,expectedContext}){
 let key,plaintext;
 try{
  const fields=['version','suite','recipient_sha256','context','plaintext_bytes','plaintext_sha256','ciphertext_bytes','ciphertext_sha256','wrapped_key','iv','tag'];
  need(envelope&&JSON.stringify(Object.keys(envelope).sort())===JSON.stringify(fields.sort())&&envelope.version===1&&envelope.suite===suite&&Number.isSafeInteger(envelope.plaintext_bytes)&&envelope.plaintext_bytes>=5&&envelope.plaintext_bytes<=maxBytes&&envelope.ciphertext_bytes===envelope.plaintext_bytes&&/^[a-f0-9]{64}$/.test(envelope.plaintext_sha256)&&/^[a-f0-9]{64}$/.test(envelope.ciphertext_sha256));
  checkedContext(envelope.context);need(JSON.stringify(envelope.context)===JSON.stringify(checkedContext(expectedContext))&&Buffer.isBuffer(ciphertext)&&ciphertext.length===envelope.ciphertext_bytes&&sha(ciphertext)===envelope.ciphertext_sha256);
  const recipient=checkedKey(privateKey,true),publicKey=createPublicKey(recipient);need(sha(publicKey.export({type:'spki',format:'der'}))===envelope.recipient_sha256);
  key=privateDecrypt({key:recipient,padding:constants.RSA_PKCS1_OAEP_PADDING,oaepHash:'sha256'},decoded(envelope.wrapped_key,recipient.asymmetricKeyDetails.modulusLength/8));need(key.length===32);
  const decipher=createDecipheriv('aes-256-gcm',key,decoded(envelope.iv,12));decipher.setAAD(header(envelope));decipher.setAuthTag(decoded(envelope.tag,16));plaintext=Buffer.concat([decipher.update(ciphertext),decipher.final()]);
  need(plaintext.length===envelope.plaintext_bytes&&sha(plaintext)===envelope.plaintext_sha256&&plaintext.subarray(0,5).toString()==='PGDMP');return plaintext;
 }catch{plaintext?.fill(0);throw Error('Private backup envelope validation failed');}finally{key?.fill(0);}
}
function outsideGit(file){let cursor=fs.realpathSync(path.dirname(path.resolve(file)));for(;;){need(!fs.existsSync(path.join(cursor,'.git')));const parent=path.dirname(cursor);if(parent===cursor)break;cursor=parent;}}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 let plaintext,key;
 try{
  const [command,manifestFile,ciphertextFile,privateKeyFile,contextFile,outputFile,...extra]=process.argv.slice(2);need(command==='decrypt'&&!extra.length&&[manifestFile,ciphertextFile,privateKeyFile,contextFile,outputFile].every(Boolean));outsideGit(privateKeyFile);outsideGit(outputFile);
  const fd=fs.openSync(privateKeyFile,fs.constants.O_RDONLY|fs.constants.O_NOFOLLOW);try{const stat=fs.fstatSync(fd);need(stat.isFile()&&stat.nlink===1&&(stat.mode&0o777)===0o600&&stat.size<=32768&&(typeof process.getuid!=='function'||stat.uid===process.getuid()));key=fs.readFileSync(fd);}finally{fs.closeSync(fd);}
  need(fs.statSync(manifestFile).size<=65536&&fs.statSync(contextFile).size<=4096&&fs.statSync(ciphertextFile).size<=maxBytes);
  plaintext=openRecoveryBackup({envelope:JSON.parse(fs.readFileSync(manifestFile)),ciphertext:fs.readFileSync(ciphertextFile),privateKey:key,expectedContext:JSON.parse(fs.readFileSync(contextFile))});
  const out=fs.openSync(outputFile,fs.constants.O_CREAT|fs.constants.O_EXCL|fs.constants.O_WRONLY|fs.constants.O_NOFOLLOW,0o600);try{fs.writeFileSync(out,plaintext);fs.fsyncSync(out);}finally{fs.closeSync(out);}
  console.log(JSON.stringify({status:'decrypted-and-hash-verified',bytes:plaintext.length,sha256:sha(plaintext),credentials_logged:false}));
 }catch{console.error('Private backup delivery failed; preserve ciphertext and use the authorized private key outside Git');process.exitCode=1;}
 finally{key?.fill(0);plaintext?.fill(0);}
}
