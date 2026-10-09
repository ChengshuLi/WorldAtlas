import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
const home=path.join(path.dirname(fileURLToPath(import.meta.url)),'original-execution-custody');
const hash=(kind,b)=>createHash(kind).update(b).digest('hex');
const need=(ok,msg)=>{if(!ok)throw Error(msg);};
const receipt=JSON.parse(fs.readFileSync(path.join(home,'receipt-v2.json')));
const objects=new Map();let total=0;
for(const pin of receipt.git_objects){
 need(pin.archive_path===`objects/${pin.oid}`&&!objects.has(pin.oid),'Foreign or duplicate Git object');
 const b=fs.readFileSync(path.join(home,pin.archive_path));total+=b.length;
 need(total<=256*1024*1024&&b.length<=32*1024*1024,'Whole custody admission exceeded');
 need(b.length===pin.bytes&&hash('sha256',b)===pin.sha256,'Whole object drift');
 need(hash('sha1',Buffer.concat([Buffer.from(`${pin.kind} ${b.length}\0`),b]))===pin.oid,'Git object identity drift');
 objects.set(pin.oid,{kind:pin.kind,body:b});
}
const object=(oid,kind)=>{const o=objects.get(oid);need(o?.kind===kind,'Missing or wrong Git object');return o.body;};
function entry(tree,name){const b=object(tree,'tree');let p=0;while(p<b.length){const space=b.indexOf(32,p),end=b.indexOf(0,space);need(space>p&&end>space&&end+21<=b.length,'Malformed tree');const mode=b.subarray(p,space).toString(),key=b.subarray(space+1,end).toString(),oid=b.subarray(end+1,end+21).toString('hex');if(key===name)return{mode,oid};p=end+21;}throw Error('Missing Merkle path');}
let pins=0;
for(const closure of receipt.closures)for(const pin of [closure.request,...closure.executed_code,...closure.original_code,closure.supervisor,closure.supervisor_helper].filter(Boolean)){
 const commit=object(pin.commit,'commit').toString();const match=/^tree ([0-9a-f]{40})\n/.exec(commit);need(match,'Malformed commit');let tree=match[1],found;const parts=pin.path.split('/');need(parts.every(p=>p&&p!=='.'&&p!=='..'),'Foreign path');
 for(let i=0;i<parts.length;i++){found=entry(tree,parts[i]);if(i<parts.length-1){need(found.mode==='40000','Wrong directory mode');tree=found.oid;}}
 need(found.oid===pin.blob&&found.mode===pin.mode,'Commit/path/mode binding drift');const b=object(pin.blob,'blob');need(b.length===pin.bytes&&hash('sha256',b)===pin.sha256,'Bound whole code/request drift');pins++;
}
for(const pin of receipt.installed_modules){need(pin.path.startsWith('node_modules/@noble/hashes/')&&!pin.path.includes('..'),'Foreign installed path');const b=fs.readFileSync(path.join(home,'installed',pin.path));need(b.length===pin.bytes&&hash('sha256',b)===pin.sha256,'Installed module drift');}
console.log(JSON.stringify({git_objects:objects.size,complete_bound_pins:pins,installed_modules:receipt.installed_modules.length,whole_object_bytes:total,scientific_execution:false}));
