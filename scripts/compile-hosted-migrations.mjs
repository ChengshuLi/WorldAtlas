import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
const target='0002_geographic_reference_releases.sql';
const originalTargetHash='fc03e50b1c7053d9ffe89534395bcbb644e3192231122eca51a424fd14753c53';
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
/** One pinned semantic-equivalent transport adaptation; never edit raw SQL. */
export function compileGeographicReleaseSql(raw){
 if(sha(raw)!==originalTargetHash)throw Error('Geographic migration source hash changed; review a new transport rule rather than rewriting frozen SQL');
 const lines=[];
 const sql=raw.replace(/^([ \t]*)SELECT CASE WHEN (.+) THEN (RAISE\(ABORT,'(?:''|[^'])*'\)) END;$/gm,(whole,indent,condition,raise,offset)=>{
  lines.push({line:raw.slice(0,offset).split('\n').length,condition_sha256:sha(condition),raise_sha256:sha(raise)});
  // CASE returns NULL when false; SELECT WHERE returns no row. In a trigger
  // either result is discarded. Both raise the identical error only if true.
  return `${indent}SELECT ${raise} WHERE ${condition};`;
 });
 if(lines.length!==21||/SELECT CASE WHEN/.test(sql))throw Error('Pinned transport adaptation must cover exactly the 21 reviewed trigger guards');
 return {sql,transformations:lines};
}
export function compileHostedMigrations({input='drizzle',output}={}){
 if(!output||path.resolve(output)===path.resolve(input))throw Error('Choose a separate derivative migration output directory');
 const files=fs.readdirSync(input).filter(f=>f.endsWith('.sql')).sort();
 if(!files.includes(target))throw Error('Pinned geographic-release source migration is missing');
 const prepared=files.map(file=>{const raw=fs.readFileSync(path.join(input,file)),result=file===target?compileGeographicReleaseSql(raw.toString('utf8')):{sql:raw.toString('utf8'),transformations:[]};return {file,raw,compiled:file===target?Buffer.from(result.sql):raw,transformations:result.transformations};});
 fs.mkdirSync(output,{recursive:true});fs.cpSync(input,output,{recursive:true});
 const migrations=prepared.map(row=>{fs.writeFileSync(path.join(output,row.file),row.compiled);return {file:row.file,source_sha256:sha(row.raw),transport_sha256:sha(row.compiled),transformed_guards:row.transformations.length,transformations:row.transformations};});
 const meta=fs.readdirSync(path.join(input,'meta')).sort().map(file=>({file:`meta/${file}`,sha256:sha(fs.readFileSync(path.join(input,'meta',file)))}));
 const receipt={version:1,purpose:'Derivative deployment transport only; immutable source SQL and metadata remain retained unchanged',rule:'0002 trigger SELECT CASE WHEN condition THEN RAISE(ABORT,message) END becomes SELECT RAISE(ABORT,message) WHERE condition',source_sql_rewritten:false,claims_rewritten:false,source_migration_hash:originalTargetHash,transformed_guards:21,migrations,meta};
 fs.writeFileSync(path.join(output,'transport-receipt.json'),JSON.stringify(receipt,null,2)+'\n');
 return receipt;
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 const options={};for(let at=2;at<process.argv.length;at+=2){const key=process.argv[at],value=process.argv[at+1];if(!value)throw Error(`Missing value for ${key}`);if(key==='--input')options.input=value;else if(key==='--output')options.output=value;else throw Error(`Unknown option ${key}`);}const receipt=compileHostedMigrations(options);console.log(JSON.stringify({transformed_guards:receipt.transformed_guards,migrations:receipt.migrations.map(({file,source_sha256,transport_sha256})=>({file,source_sha256,transport_sha256}))}));
}
