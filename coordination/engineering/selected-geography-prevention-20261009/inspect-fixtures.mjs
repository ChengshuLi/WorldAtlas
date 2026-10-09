// Archive-only integrity reader; it executes no fixture or candidate program.
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
const cap=32*1024*1024,hash=(b,algorithm='sha256')=>createHash(algorithm).update(b).digest('hex');
const require=(value,message)=>{if(!value)throw Error(message);};
const files=process.argv.slice(2);require(files.length>0&&files.length<=512,'Name complete fixture archives');
let total=fs.statSync(process.execPath).size+8*1024*1024,objects=0,commits=0;
const entries=files.map(file=>{const stat=fs.lstatSync(file);require(stat.isFile()&&fs.realpathSync(file)===path.resolve(file)&&stat.size>=18&&stat.size<=cap,'Ordinary bounded archive required');total+=stat.size;return {file,stat};});
require(total<=256*1024*1024,'Complete encoded archive phase exceeds prospective cap');
for(const entry of entries){const fd=fs.openSync(entry.file,'r'),tail=Buffer.alloc(4);try{require(fs.readSync(fd,tail,0,4,entry.stat.size-4)===4,'Missing gzip size metadata');}finally{fs.closeSync(fd);}entry.decoded=tail.readUInt32LE();require(entry.decoded>0&&entry.decoded<=cap,'Whole fixture decoded cap');total+=entry.decoded*3;}
require(total<=256*1024*1024,'Complete archive/member/metadata phase exceeds prospective cap');
for(const {file,decoded} of entries){
 const encoded=fs.readFileSync(file),raw=gunzipSync(encoded,{maxOutputLength:decoded});require(raw.length===decoded,'Whole gzip decoded declaration differs');
 const archive=JSON.parse(raw),members=new Map();require(archive.kind==='complete-synthetic-immutable-entry-fixture'&&archive.source_approval===false&&Array.isArray(archive.objects),'Wrong fixture type');
 for(const member of archive.objects){require(['commit','tree','blob'].includes(member.type)&&!members.has(member.oid),'Foreign/duplicate fixture object');const body=Buffer.from(member.base64,'base64');require(body.length===member.bytes&&body.length<=cap&&hash(body)===member.sha256&&hash(Buffer.concat([Buffer.from(member.type+' '+body.length+'\0'),body]),'sha1')===member.oid,'Whole Git object inverse differs');members.set(member.oid,{type:member.type,body});}
 const visited=new Set();
 function visit(oid,expected){const member=members.get(oid);require(member?.type===expected,'Missing/wrong typed immutable fixture object');if(visited.has(oid))return;visited.add(oid);
  if(expected==='commit'){const headers=member.body.toString().split('\n\n')[0].split('\n'),tree=headers.filter(row=>row.startsWith('tree '));require(tree.length===1,'Incomplete commit tree');visit(tree[0].slice(5),'tree');for(const row of headers.filter(row=>row.startsWith('parent ')))visit(row.slice(7),'commit');}
  if(expected==='tree'){let at=0;const names=new Set();while(at<member.body.length){const nul=member.body.indexOf(0,at);require(nul>at&&nul+21<=member.body.length,'Truncated tree');const entry=member.body.subarray(at,nul).toString(),split=entry.indexOf(' '),mode=entry.slice(0,split),name=entry.slice(split+1);require(['40000','100644','100755'].includes(mode)&&name&&!name.includes('/')&&!['.','..'].includes(name)&&!names.has(name),'Foreign/duplicate tree member');names.add(name);visit(member.body.subarray(nul+1,nul+21).toString('hex'),mode==='40000'?'tree':'blob');at=nul+21;}}
 }
 require(Array.isArray(archive.commits)&&archive.commits.length>0,'Missing original executed fixture commits');for(const oid of archive.commits)visit(oid,'commit');require(visited.size===members.size,'Unrelated or omitted fixture custody');objects+=members.size;commits+=archive.commits.length;
}
console.log(JSON.stringify({files:files.length,objects,commits,complete_phase_bound:total,outcome:'whole-object-and-complete-Merkle-closure-verified',fixture_programs_executed:false,physical_authority_approved:false}));
