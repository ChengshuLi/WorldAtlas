// Bounded owner-authorized fixed-origin GETs; secret never reaches files or browser.
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
const directory=process.argv[2],origin='https://worldatlas-explorer.chengshu-li-2013.chatgpt.site';
if(!directory||!process.stdin.isTTY)throw Error('Use an owned directory and hidden credential stdin');
process.stdin.setRawMode(true);console.log('Ready for private verification credential on hidden stdin.');
const token=await new Promise((resolve,reject)=>{let input='';process.stdin.on('data',chunk=>{input+=chunk;if(!/[\r\n]/.test(input))return;process.stdin.pause();process.stdin.setRawMode(false);try{const d=JSON.parse(input.trim());if(typeof d.token!=='string'||!d.token||/[\r\n]/.test(d.token))throw Error();resolve(d.token);}catch{reject(Error('Invalid hidden input'));}});});
fs.mkdirSync(directory,{recursive:true});const files=[],receipt={version:1,read_only:true,origin,started_at_utc:new Date().toISOString(),files,completed:false};
const save=()=>fs.writeFileSync(path.join(directory,'capture-receipt.json'),JSON.stringify(receipt,null,2)+'\n');
let total=0;
async function get(relative,maximum){
 const response=await fetch(origin+'/'+relative,{headers:{'OAI-Sites-Authorization':'Bearer '+token},redirect:'error',signal:AbortSignal.timeout(30000)});
 if(!response.ok)throw Error('Input GET failed with HTTP'+response.status);
 const bytes=Buffer.from(await response.arrayBuffer());total+=bytes.length;
 if(bytes.length>maximum||total>32*1024*1024)throw Error('Input byte budget exceeded');
 const target=path.join(directory,relative);fs.mkdirSync(path.dirname(target),{recursive:true});fs.writeFileSync(target,bytes);
 files.push({path:relative,bytes:bytes.length,sha256:createHash('sha256').update(bytes).digest('hex'),status:response.status});save();
 return JSON.parse(bytes[0]===31&&bytes[1]===139?gunzipSync(bytes,{maxOutputLength:32*1024*1024}):bytes);
}
try{
 const geography=await get('atlas-geography.json',16*1024*1024);
 receipt.reference_release=geography.reference_release;
 const index=await get('reference-attributes/index.json',4*1024*1024);
 if(!Array.isArray(index.parts)||index.parts.length>256||new Set(index.parts).size!==index.parts.length||index.parts.some(p=>!/^[a-zA-Z0-9_-]+\.json(?:\.gz)?$/.test(p)))throw Error('Invalid part roster');
 let next=0;await Promise.all(Array.from({length:4},async()=>{while(next<index.parts.length)await get('reference-attributes/'+index.parts[next++],4*1024*1024);}));
 receipt.completed=true;receipt.completed_at_utc=new Date().toISOString();save();console.log(JSON.stringify({completed:true,files:files.length,bytes:total}));
}catch{save();console.error('Input capture failed; retained partial receipt');process.exitCode=1;}
