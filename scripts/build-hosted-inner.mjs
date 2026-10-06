import {assertPackageStage} from './package-build.mjs';
import fs from 'node:fs/promises';
import {build} from 'esbuild';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import {compileHostedMigrations} from './compile-hosted-migrations.mjs';
import {auditDeployment,formatDeploymentBudget} from './deployment-budget.mjs';

assertPackageStage();
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(root);
// The fixed cartographic assets and prepared source caches are independent of
// new database records; importing history never runs this build.
process.env.ATLAS_HOSTED_BUILD='1';
await import('./build-static-inner.mjs');
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
// Audit the fresh compiled transport. The publisher audits its staged Site
// separately after any explicit legacy-D1 cutoff.
const budget=await auditDeployment({root,layout:'build'});
await fs.mkdir('.cache',{recursive:true});
await fs.writeFile('.cache/deployment-budget.json',JSON.stringify(budget,null,2)+'\n');
console.log(formatDeploymentBudget(budget));
if(budget.violations.length)throw Error('Deployment reserve gate failed; see .cache/deployment-budget.json and the category/file breakdown above');
console.log('Hosted atlas ready: Worker API, persistent database declarations, media storage and fixed map assets.');
