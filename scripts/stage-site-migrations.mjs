import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url))),sha=b=>createHash('sha256').update(b).digest('hex');
export function validateSiteMigrationInputs(source,compiled){
 const receipt=JSON.parse(fs.readFileSync(path.join(compiled,'transport-receipt.json')));
 const sqlFiles=fs.readdirSync(source).filter(file=>file.endsWith('.sql')).sort();
 const compiledFiles=fs.readdirSync(compiled).filter(file=>file.endsWith('.sql')).sort();
 const metadata=fs.readdirSync(path.join(source,'meta')).sort().map(file=>`meta/${file}`);
 const compiledMetadata=fs.readdirSync(path.join(compiled,'meta')).sort().map(file=>`meta/${file}`);
 if(JSON.stringify(receipt.migrations.map(row=>row.file))!==JSON.stringify(sqlFiles)||JSON.stringify(compiledFiles)!==JSON.stringify(sqlFiles)||JSON.stringify(receipt.meta.map(row=>row.file).sort())!==JSON.stringify(metadata)||JSON.stringify(compiledMetadata)!==JSON.stringify(metadata))throw Error('Full canonical migration inventory mismatch; rebuild before staging');
 for(const row of receipt.migrations){if(sha(fs.readFileSync(path.join(source,row.file)))!==row.source_sha256||sha(fs.readFileSync(path.join(compiled,row.file)))!==row.transport_sha256)throw Error('Migration source/build mismatch; rebuild before staging');}
 for(const row of receipt.meta)if(sha(fs.readFileSync(path.join(source,row.file)))!==row.sha256||sha(fs.readFileSync(path.join(compiled,row.file)))!==row.sha256)throw Error('Frozen migration metadata mismatch');
 const journal=JSON.parse(fs.readFileSync(path.join(source,'meta','_journal.json')));
 if(!Array.isArray(journal.entries)||journal.entries.length!==sqlFiles.length||journal.entries.some((row,index)=>row.idx!==index||row.tag+'.sql'!==sqlFiles[index]))throw Error('Canonical migration journal does not match all source SQL');
 const retainedSourceHash=sha(JSON.stringify({migrations:receipt.migrations.map(({file,source_sha256})=>({file,sha256:source_sha256})),meta:receipt.meta}));
 const fullReceiptHash=sha(fs.readFileSync(path.join(compiled,'transport-receipt.json')));
 return {receipt,journal,sqlFiles,retainedSourceHash,fullReceiptHash};
}
export function stageSiteMigrations(checkout,{legacyD1Only=false}={}){
 if(typeof legacyD1Only!=='boolean')throw Error('legacyD1Only must be an explicit boolean');
 const destination=path.resolve(checkout);
 if(!fs.existsSync(path.join(destination,'.openai','hosting.json'))||fs.realpathSync(destination)===fs.realpathSync(root))throw Error('Supply the separate Site checkout with its existing hosting manifest');
 for(const relative of ['dist','dist/server'])if(fs.existsSync(path.join(destination,relative))&&fs.lstatSync(path.join(destination,relative)).isSymbolicLink())throw Error('Site deployment parents must not be symlinks');
 const source=path.join(root,'drizzle'),compiled=path.join(root,'dist','drizzle');
 const {receipt,journal,sqlFiles,retainedSourceHash,fullReceiptHash}=validateSiteMigrationInputs(source,compiled);
 if(legacyD1Only&&(sqlFiles.length<8||sqlFiles.slice(0,8).some((file,index)=>!file.startsWith(String(index).padStart(4,'0')+'_'))))throw Error('Legacy D1 packaging requires the exact 0000–0007 prefix');
 // Original SQL stays available in the Site's source Git. The hosting service
 // reads the derivative root folder; rebuilds select the retained raw source.
 const sourceDestination=path.join(destination,'drizzle-source');
 fs.rmSync(sourceDestination,{recursive:true,force:true});fs.cpSync(source,sourceDestination,{recursive:true});
 const deploymentFiles=legacyD1Only?receipt.migrations.slice(0,8):receipt.migrations;
 for(const folder of [path.join(destination,'drizzle'),path.join(destination,'dist','server','drizzle')]){
  fs.rmSync(folder,{recursive:true,force:true});fs.cpSync(compiled,folder,{recursive:true});
  if(legacyD1Only){
   for(const row of receipt.migrations.slice(8))fs.unlinkSync(path.join(folder,row.file));
   for(const file of fs.readdirSync(path.join(folder,'meta')))if(file!=='_journal.json'&&!/^000[0-7]_snapshot\.json$/.test(file))fs.unlinkSync(path.join(folder,'meta',file));
   fs.writeFileSync(path.join(folder,'meta','_journal.json'),JSON.stringify({...journal,entries:journal.entries.slice(0,8)},null,2)+'\n');
   const meta=fs.readdirSync(path.join(folder,'meta')).sort().map(file=>({file:`meta/${file}`,sha256:sha(fs.readFileSync(path.join(folder,'meta',file)))}));
   const stagedReceipt={...receipt,legacy_d1_only:true,purpose:receipt.purpose+'; deployment derivative limited explicitly to legacy D1 0000–0007; PostgreSQL forward migrations are separate',retained_source_sha256:retainedSourceHash,full_transport_receipt_sha256:fullReceiptHash,migrations:deploymentFiles,meta,retained_source_migrations:receipt.migrations.map(({file,source_sha256})=>({file,sha256:source_sha256})),retained_source_meta:receipt.meta,omitted_deployment_migrations:receipt.migrations.slice(8).map(({file,source_sha256})=>({file,source_sha256}))};
   fs.writeFileSync(path.join(folder,'transport-receipt.json'),JSON.stringify(stagedReceipt,null,2)+'\n');
  }
  for(const row of deploymentFiles)if(sha(fs.readFileSync(path.join(folder,row.file)))!==row.transport_sha256)throw Error('Staged migration transport failed byte verification');
 }
 for(const row of receipt.migrations)if(sha(fs.readFileSync(path.join(sourceDestination,row.file)))!==row.source_sha256)throw Error('Staged original migration preservation failed');
 for(const row of receipt.meta)if(sha(fs.readFileSync(path.join(sourceDestination,row.file)))!==row.sha256)throw Error('Staged original metadata preservation failed');
 const result={source_preserved:true,transformed_guards:receipt.transformed_guards,transport_receipt_sha256:sha(fs.readFileSync(path.join(destination,'drizzle','transport-receipt.json')))};
 if(legacyD1Only)Object.assign(result,{legacy_d1_only:true,retained_source_sha256:retainedSourceHash,retained_source_migrations:receipt.migrations.length,deployment_migrations:deploymentFiles.length,full_transport_receipt_sha256:fullReceiptHash});
 return result;
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){const args=process.argv.slice(2),checkout=args.shift();if(!checkout)throw Error('Supply a separate Site checkout');if(args.some(arg=>arg!=='--legacy-d1-only')||new Set(args).size!==args.length)throw Error('Only the explicit --legacy-d1-only option is accepted');console.log(JSON.stringify(stageSiteMigrations(checkout,{legacyD1Only:args.includes('--legacy-d1-only')})));}
