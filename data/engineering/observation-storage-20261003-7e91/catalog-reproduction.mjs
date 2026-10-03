import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {DatabaseSync} from 'node:sqlite';
import {createLocalPostgres} from '../../../scripts/verify-postgres-schema.mjs';
import {storageCatalogV3} from '../../../hosted/storage-export-v3.js';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../../..');
const output=process.argv[2];
if(!output || process.argv.length!==3)throw Error('Provide one fresh output JSON path');
const hash=value=>createHash('sha256').update(JSON.stringify(value)).digest('hex');
const sqlite=new DatabaseSync(':memory:');
let pg;
try {
 for(const file of fs.readdirSync(path.join(root,'drizzle')).filter(file=>file.endsWith('.sql')).sort())sqlite.exec(fs.readFileSync(path.join(root,'drizzle',file),'utf8'));
 const db={prepare(sql){return {async all(){return {results:sqlite.prepare(sql).all()};}}}};
 pg=await createLocalPostgres();
 for(const file of fs.readdirSync(path.join(root,'postgres/migrations')).filter(file=>file.endsWith('.sql')).sort())await pg.engine.exec(fs.readFileSync(path.join(root,'postgres/migrations',file),'utf8'));
 const receipt={version:3,tables:26,scope:'Actual isolated SQLite and PostgreSQL full catalog byte hashes. No provider operation, historical/geographic approval or production certificate.',d1:hash(await storageCatalogV3(db,{verifyPins:false})),postgres:hash(await storageCatalogV3(pg.db,{verifyPins:false}))};
 fs.writeFileSync(output,JSON.stringify(receipt,null,2)+'\n',{flag:'wx'});
 console.log(JSON.stringify(receipt));
}finally{sqlite.close();await pg?.close();}
