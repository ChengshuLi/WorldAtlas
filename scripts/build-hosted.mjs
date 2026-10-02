import fs from 'node:fs/promises';
import {build} from 'esbuild';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import {compileHostedMigrations} from './compile-hosted-migrations.mjs';

const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(root);
// The fixed cartographic assets and prepared source caches are independent of
// new database records; importing history never runs this build.
process.env.ATLAS_HOSTED_BUILD='1';
await import('./build-static.mjs');
await fs.mkdir('dist/client',{recursive:true});
for(const name of await fs.readdir('dist'))if(name!=='client')await fs.rename(`dist/${name}`,`dist/client/${name}`);
await fs.mkdir('dist/server',{recursive:true});
await build({entryPoints:['hosted/worker.js'],outfile:'dist/server/index.js',bundle:true,format:'esm',platform:'browser',target:'es2022',minify:true});
// Sites' migration splitter needs the reviewed derivative transport; retain
// immutable original sources separately when building its deployment mirror.
const migrationSource=await fs.access('drizzle-source/meta/_journal.json').then(()=> 'drizzle-source').catch(()=> 'drizzle');
compileHostedMigrations({input:migrationSource,output:'dist/drizzle'});
await fs.cp('dist/drizzle','dist/server/drizzle',{recursive:true});
const config={name:'worldatlas-explorer',main:'index.js',compatibility_date:'2026-10-01',assets:{directory:'../client',binding:'ASSETS',run_worker_first:['/api/*']},d1_databases:[{binding:'DB',database_name:'worldatlas-db',migrations_dir:'./drizzle'}],r2_buckets:[{binding:'BUCKET',bucket_name:'worldatlas-media'}]};
await fs.writeFile('dist/server/wrangler.json',JSON.stringify(config,null,2)+'\n');
let totalBytes=0;
for(const file of await fs.readdir('dist',{recursive:true})){
 const stat=await fs.stat(`dist/${file}`);if(!stat.isFile())continue;
 totalBytes+=stat.size;
 if(stat.size>25*1024*1024)throw Error(`Deployment asset exceeds 25 MiB: ${file}`);
}
if(totalBytes>256*1024*1024)throw Error(`Deployment package exceeds 256 MiB: ${totalBytes} bytes`);
console.log('Hosted atlas ready: Worker API, persistent database declarations, media storage and fixed map assets.');
console.log(`Deployment files: ${totalBytes} bytes; catalog bootstrap and persistent media are separate.`);
