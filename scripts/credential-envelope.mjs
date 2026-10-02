import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {constants,createHash,createPublicKey,createPrivateKey,generateKeyPairSync,randomBytes,publicEncrypt,privateDecrypt,createCipheriv,createDecipheriv} from 'node:crypto';

const suite='RSA-OAEP-256+A256GCM',purpose='worldatlas-runtime-database-url';
export const credentialEnvelopeLimits={credential_bytes:16384,envelope_bytes:65536,context_bytes:4096,key_bytes:32768,max_lifetime_ms:86400000,clock_skew_ms:300000};
const contextFields=['purpose','repository','workflow_path','commit_sha','run_id','run_attempt','project_id','branch_id','endpoint_host','database_name','role_name','source_manifest_sha256','schema_sha256','runtime_role_sql_sha256','issued_at_utc','expires_at_utc'];
const envelopeFields=['version','suite','recipient_sha256','context','wrapped_key','iv','ciphertext','tag'];
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const fail=()=>{throw Error('Credential envelope validation or private delivery failed');};
const exactKeys=(value,keys)=>value&&typeof value==='object'&&!Array.isArray(value)&&JSON.stringify(Object.keys(value).sort())===JSON.stringify([...keys].sort());
function boundedBytes(value,limit){if(typeof value!=='string'&&!Buffer.isBuffer(value))fail();const bytes=Buffer.from(value);if(!bytes.length||bytes.length>limit)fail();return bytes;}
function contextAt(context,now=Date.now()){
 if(!exactKeys(context,contextFields)||Buffer.byteLength(JSON.stringify(context))>credentialEnvelopeLimits.context_bytes||contextFields.some(field=>typeof context[field]!=='string'))fail();
 if(context.purpose!==purpose||!/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(context.repository)||!/^\.github\/workflows\/[A-Za-z0-9_.-]+\.ya?ml$/.test(context.workflow_path)||!/^[a-f0-9]{40}$/.test(context.commit_sha)||!/^\d{1,20}$/.test(context.run_id)||!/^\d{1,6}$/.test(context.run_attempt)||Number(context.run_id)<=0||Number(context.run_attempt)<=0||!/^[a-z][a-z0-9-]{2,199}$/.test(context.project_id)||!/^br-[a-z0-9-]{1,150}$/.test(context.branch_id)||!/^ep-[a-z0-9-]+(?:\.[a-z0-9-]+)+\.neon\.tech$/.test(context.endpoint_host)||context.database_name!=='neondb'||context.role_name!=='worldatlas_app')fail();
 if(['source_manifest_sha256','schema_sha256','runtime_role_sql_sha256'].some(field=>!/^[a-f0-9]{64}$/.test(context[field])))fail();
 const times=['issued_at_utc','expires_at_utc'].map(key=>{const time=Date.parse(context[key]);if(!Number.isFinite(time)||new Date(time).toISOString()!==context[key])fail();return time;});
 if(!Number.isFinite(now)||times[1]<=times[0]||times[1]-times[0]>credentialEnvelopeLimits.max_lifetime_ms||times[0]>now+credentialEnvelopeLimits.clock_skew_ms||times[1]<=now)fail();
 return Object.fromEntries(contextFields.map(field=>[field,context[field]]));
}
function rsaKey(value,{privateKey=false}={}){
 let key;try{boundedBytes(value,credentialEnvelopeLimits.key_bytes);key=privateKey?createPrivateKey(value):createPublicKey(value);}catch{fail();}
 const bits=key.asymmetricKeyDetails?.modulusLength;if(key.asymmetricKeyType!=='rsa'||![3072,4096].includes(bits))fail();return key;
}
function recipientId(key){return sha((key.type==='public'?key:createPublicKey(key)).export({type:'spki',format:'der'}));}
/** Validate a public recipient before any production operation; metadata only. */
export function credentialRecipientFingerprint(publicKey){return recipientId(rsaKey(publicKey));}
function authenticatedHeader(envelope){return Buffer.from(JSON.stringify({version:1,suite,recipient_sha256:envelope.recipient_sha256,context:envelope.context}));}
function validateCredential(bytes,context){
 if(bytes.length<1||bytes.length>credentialEnvelopeLimits.credential_bytes)fail();const credential=bytes.toString('utf8');if(!Buffer.from(credential).equals(bytes)||/[\s\u0000-\u001f\u007f]/.test(credential))fail();
 let url;try{url=new URL(credential);}catch{fail();}
 const pooler=context.endpoint_host.replace(/^([^.]+)\./,'$1-pooler.');
 if(!['postgres:','postgresql:'].includes(url.protocol)||![context.endpoint_host,pooler].includes(url.hostname)||url.port&&url.port!=='5432'||decodeURIComponent(url.username)!==context.role_name||decodeURIComponent(url.pathname)!=='/'+context.database_name||!url.password||url.hash||url.searchParams.getAll('sslmode').length!==1||url.searchParams.get('sslmode')!=='require')fail();
 return credential;
}
function decoded(value,min,max){if(typeof value!=='string'||!value||!/^[A-Za-z0-9_-]+$/.test(value)||value.length>Math.ceil(max*4/3)+2)fail();const result=Buffer.from(value,'base64url');if(result.toString('base64url')!==value||result.length<min||result.length>max)fail();return result;}

/** Confidentiality transport only. Authentication comes from the separately
 * verified authorized workflow artifact, not possession of a public key. */
export function encryptCredentialEnvelope({credential,publicKey,context,now=Date.now()}){
 const canonical=contextAt(context,now),key=rsaKey(publicKey),bytes=boundedBytes(credential,credentialEnvelopeLimits.credential_bytes);validateCredential(bytes,canonical);
 const contentKey=randomBytes(32),iv=randomBytes(12);try{
  const envelope={version:1,suite,recipient_sha256:recipientId(key),context:canonical};
  const cipher=createCipheriv('aes-256-gcm',contentKey,iv,{authTagLength:16});cipher.setAAD(authenticatedHeader(envelope));
  const ciphertext=Buffer.concat([cipher.update(bytes),cipher.final()]);
  const wrapped=publicEncrypt({key,padding:constants.RSA_PKCS1_OAEP_PADDING,oaepHash:'sha256'},contentKey);
  return {...envelope,wrapped_key:wrapped.toString('base64url'),iv:iv.toString('base64url'),ciphertext:ciphertext.toString('base64url'),tag:cipher.getAuthTag().toString('base64url')};
 }catch{fail();}finally{contentKey.fill(0);}
}
export function decryptCredentialEnvelope({envelope,privateKey,expectedContext,now=Date.now()}){
 let contentKey,plain;
 try{
  const expected=contextAt(expectedContext,now),bytes=boundedBytes(typeof envelope==='object'&&!Buffer.isBuffer(envelope)?JSON.stringify(envelope):envelope,credentialEnvelopeLimits.envelope_bytes),value=JSON.parse(bytes);
  if(!exactKeys(value,envelopeFields)||value.version!==1||value.suite!==suite||!/^[a-f0-9]{64}$/.test(value.recipient_sha256??''))fail();
  const actual=contextAt(value.context,now);if(JSON.stringify(actual)!==JSON.stringify(expected))fail();value.context=actual;
  const key=rsaKey(privateKey,{privateKey:true});if(recipientId(key)!==value.recipient_sha256)fail();
  const wrapped=decoded(value.wrapped_key,key.asymmetricKeyDetails.modulusLength/8,key.asymmetricKeyDetails.modulusLength/8),iv=decoded(value.iv,12,12),tag=decoded(value.tag,16,16),ciphertext=decoded(value.ciphertext,1,credentialEnvelopeLimits.credential_bytes);
  contentKey=privateDecrypt({key,padding:constants.RSA_PKCS1_OAEP_PADDING,oaepHash:'sha256'},wrapped);if(contentKey.length!==32)fail();
  const decipher=createDecipheriv('aes-256-gcm',contentKey,iv,{authTagLength:16});decipher.setAAD(authenticatedHeader(value));decipher.setAuthTag(tag);plain=Buffer.concat([decipher.update(ciphertext),decipher.final()]);validateCredential(plain,actual);
  return plain;
 }catch{plain?.fill(0);fail();}finally{contentKey?.fill(0);}
}
function outsideGit(filename){
 let cursor=path.dirname(path.resolve(filename));while(!fs.existsSync(cursor)){const parent=path.dirname(cursor);if(parent===cursor)fail();cursor=parent;}cursor=fs.realpathSync(cursor);
 for(;;){if(fs.existsSync(path.join(cursor,'.git')))fail();const parent=path.dirname(cursor);if(parent===cursor)break;cursor=parent;}
}
function readPrivateKey(filename){
 outsideGit(filename);const fd=fs.openSync(filename,fs.constants.O_RDONLY|fs.constants.O_NOFOLLOW);try{const stat=fs.fstatSync(fd);if(!stat.isFile()||stat.nlink!==1||(stat.mode&0o777)!==0o600||typeof process.getuid==='function'&&stat.uid!==process.getuid()||stat.size>credentialEnvelopeLimits.key_bytes)fail();return fs.readFileSync(fd);}finally{fs.closeSync(fd);}
}
function exclusiveFile(filename,bytes,{privateFile=false}={}){
 if(privateFile)outsideGit(filename);const parent=path.dirname(path.resolve(filename));if(!fs.statSync(parent).isDirectory())fail();const fd=fs.openSync(filename,fs.constants.O_CREAT|fs.constants.O_EXCL|fs.constants.O_WRONLY|fs.constants.O_NOFOLLOW,privateFile?0o600:0o644);
 try{fs.writeFileSync(fd,bytes);fs.fsyncSync(fd);}catch(error){try{fs.unlinkSync(filename);}catch{}throw error;}finally{fs.closeSync(fd);}
}
/** Root runs this only after authorizing an ephemeral recipient key. No key is
 * generated when importing this module. Private output must stay outside Git. */
export function generateRecipientFiles({privateKeyFile,publicKeyFile}){
 if(path.resolve(privateKeyFile)===path.resolve(publicKeyFile)||fs.existsSync(privateKeyFile)||fs.existsSync(publicKeyFile))fail();outsideGit(privateKeyFile);
 const pair=generateKeyPairSync('rsa',{modulusLength:3072,publicExponent:65537,publicKeyEncoding:{type:'spki',format:'pem'},privateKeyEncoding:{type:'pkcs8',format:'pem'}});
 exclusiveFile(privateKeyFile,pair.privateKey,{privateFile:true});try{exclusiveFile(publicKeyFile,pair.publicKey);}catch{try{fs.unlinkSync(privateKeyFile);}catch{}fail();}
 return {status:'recipient-created',recipient_sha256:recipientId(rsaKey(pair.publicKey)),private_key_logged:false,private_key_mode:'0600',algorithm:suite};
}
export function deliverCredentialFile({envelopeFile,privateKeyFile,expectedContext,envelopeSHA256,outputFile,now=Date.now()}){
 if(!/^[a-f0-9]{64}$/.test(envelopeSHA256??''))fail();const stat=fs.statSync(envelopeFile);if(!stat.isFile()||stat.size>credentialEnvelopeLimits.envelope_bytes)fail();const bytes=fs.readFileSync(envelopeFile);if(sha(bytes)!==envelopeSHA256)fail();
 const key=readPrivateKey(privateKeyFile);let secret;try{secret=decryptCredentialEnvelope({envelope:bytes,privateKey:key,expectedContext,now});exclusiveFile(outputFile,secret,{privateFile:true});return {status:'delivered',envelope_sha256:sha(bytes),recipient_sha256:JSON.parse(bytes).recipient_sha256,secret_file_mode:'0600',credential_logged:false};}finally{key.fill(0);secret?.fill(0);}
}
function readBounded(filename,limit){const stat=fs.statSync(filename);if(!stat.isFile()||stat.size<1||stat.size>limit)fail();return fs.readFileSync(filename);}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 try{
  const [command,...args]=process.argv.slice(2),options={};for(let at=0;at<args.length;at+=2){if(!/^--[a-z0-9-]+$/.test(args[at]??'')||!args[at+1]||Object.hasOwn(options,args[at]))fail();options[args[at]]=args[at+1];}
  let receipt;
  if(command==='generate'&&JSON.stringify(Object.keys(options).sort())===JSON.stringify(['--private-key','--public-key']))receipt=generateRecipientFiles({privateKeyFile:options['--private-key'],publicKeyFile:options['--public-key']});
  else if(command==='encrypt'&&JSON.stringify(Object.keys(options).sort())===JSON.stringify(['--context','--output','--public-key'])){
   const context=JSON.parse(readBounded(options['--context'],credentialEnvelopeLimits.context_bytes)),envelope=encryptCredentialEnvelope({credential:process.env.ATLAS_RUNTIME_DATABASE_URL,publicKey:readBounded(options['--public-key'],credentialEnvelopeLimits.key_bytes),context}),bytes=Buffer.from(JSON.stringify(envelope,null,2)+'\n');exclusiveFile(options['--output'],bytes);receipt={status:'encrypted',envelope_sha256:sha(bytes),recipient_sha256:envelope.recipient_sha256,credential_logged:false};
  }else if(command==='decrypt'&&JSON.stringify(Object.keys(options).sort())===JSON.stringify(['--context','--envelope','--expected-sha256','--output','--private-key']))receipt=deliverCredentialFile({envelopeFile:options['--envelope'],privateKeyFile:options['--private-key'],expectedContext:JSON.parse(readBounded(options['--context'],credentialEnvelopeLimits.context_bytes)),envelopeSHA256:options['--expected-sha256'],outputFile:options['--output']});
  else fail();console.log(JSON.stringify(receipt));
 }catch{console.error(JSON.stringify({status:'failed',error_code:'credential-envelope-delivery-rejected',credential_logged:false,private_key_logged:false}));process.exitCode=1;}
}
