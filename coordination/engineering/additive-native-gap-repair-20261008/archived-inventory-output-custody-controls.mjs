import fs from 'node:fs';import path from 'node:path';import {createHash} from 'node:crypto';import {gunzipSync,gzipSync} from 'node:zlib';
import {verifyCustody} from '../../coordination/engineering/additive-native-gap-repair-20261008/restore-qualified-inventory-outputs.mjs';
const sha=b=>createHash('sha256').update(b).digest('hex');const P='coordination/engineering/additive-native-gap-repair-20261008',src=P+'/qualified-inventory-output-custody/index.json';const raw=fs.readFileSync(src),index=JSON.parse(raw),dir='.cache/additive-native-gap-repair/output-custody-controls-v1';fs.mkdirSync(dir);const rejected=[];
for(const [name,mutate] of [
 ['omitted_member',x=>x.archives[0].members.pop()],
 ['duplicate_member',x=>x.archives[0].members[1]=x.archives[0].members[0]],
 ['foreign_original_path',x=>x.archives[0].members[0].path='.cache/foreign/publication.json'],
 ['changed_execution_commit',x=>x.archives[0].members[0].execution_commit='0'.repeat(40)],
 ['whole_phase_over_cap',x=>x.archives[0].admission.complete_phase_bytes=268435457],
 ['changed_original_decoded_charge',x=>x.archives[0].admission.original_decoded_bytes--],
 ['changed_archive_encoded_hash',x=>x.archives[0].sha256='0'.repeat(64)]
]){const x=structuredClone(index);mutate(x);const b=Buffer.from(JSON.stringify(x)),f=dir+'/'+name+'.json';fs.writeFileSync(f,b);try{verifyCustody(f,sha(b));throw Error('CONTROL ACCEPTED '+name);}catch(e){if(e.message.startsWith('CONTROL ACCEPTED'))throw e;rejected.push({name,error:e.message});}}
// A coherent envelope with changed raw payload reaches the whole inverse byte guard.
const x=structuredClone(index),a=x.archives[0],rows=gunzipSync(fs.readFileSync(a.path)).toString().trimEnd().split('\n');const row=JSON.parse(rows[0]);const body=Buffer.from(row.body_base64,'base64');body[0]^=1;row.body_base64=body.toString('base64');rows[0]=JSON.stringify(row);const decoded=Buffer.from(rows.join('\n')+'\n'),encoded=gzipSync(decoded);a.path=dir+'/coherent-changed-body.jsonl.gz';fs.writeFileSync(a.path,encoded);Object.assign(a,{bytes:encoded.length,sha256:sha(encoded),uncompressed_bytes:decoded.length,uncompressed_sha256:sha(decoded)});const b=Buffer.from(JSON.stringify(x)),f=dir+'/coherent-changed-body-index.json';fs.writeFileSync(f,b);try{verifyCustody(f,sha(b));throw Error('CONTROL ACCEPTED changed_body');}catch(e){if(e.message!=='Whole inverse bytes')throw e;rejected.push({name:'coherent_changed_body',error:e.message});}
const result={version:1,index_sha256:sha(raw),reader_sha256:sha(fs.readFileSync(P+'/restore-qualified-inventory-outputs.mjs')),positive:verifyCustody(src,sha(raw),{compareOriginal:true}),rejected,limits:'Byte custody controls only; no new scientific execution or physical authority approval.'};fs.writeFileSync(P+'/qualified-inventory-output-custody/actual-inverse-controls.json',JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify({positive:result.positive,negative_controls:rejected.length}));
