import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url))),sha=b=>createHash('sha256').update(b).digest('hex');
export function stageSiteMigrations(checkout){
 const destination=path.resolve(checkout);
 if(destination===root||!fs.existsSync(path.join(destination,'.openai','hosting.json')))throw Error('Supply the separate Site checkout with its existing hosting manifest');
 const source=path.join(root,'drizzle'),compiled=path.join(root,'dist','drizzle');
 const receipt=JSON.parse(fs.readFileSync(path.join(compiled,'transport-receipt.json')));
 for(const row of receipt.migrations){if(sha(fs.readFileSync(path.join(source,row.file)))!==row.source_sha256||sha(fs.readFileSync(path.join(compiled,row.file)))!==row.transport_sha256)throw Error('Migration source/build mismatch; rebuild before staging');}
 for(const row of receipt.meta)if(sha(fs.readFileSync(path.join(source,row.file)))!==row.sha256||sha(fs.readFileSync(path.join(compiled,row.file)))!==row.sha256)throw Error('Frozen migration metadata mismatch');
 // Original SQL stays available in the Site's source Git. The hosting service
 // reads the derivative root folder; rebuilds select the retained raw source.
 fs.cpSync(source,path.join(destination,'drizzle-source'),{recursive:true});
 fs.cpSync(compiled,path.join(destination,'drizzle'),{recursive:true});
 for(const row of receipt.migrations)if(sha(fs.readFileSync(path.join(destination,'drizzle-source',row.file)))!==row.source_sha256||sha(fs.readFileSync(path.join(destination,'drizzle',row.file)))!==row.transport_sha256)throw Error('Staged migration transport failed byte verification');
 return {source_preserved:true,transformed_guards:receipt.transformed_guards,transport_receipt_sha256:sha(fs.readFileSync(path.join(compiled,'transport-receipt.json')))};
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){if(!process.argv[2])throw Error('Supply a separate Site checkout');console.log(JSON.stringify(stageSiteMigrations(process.argv[2])));}
