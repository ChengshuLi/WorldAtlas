// Prepare pure, source-backed additions in a separate evidence directory.
// The supplied candidate must already contain reviewed adjacent-tier parents.
import fs from 'node:fs';import path from 'node:path';import {createHash} from 'node:crypto';import {execFileSync} from 'node:child_process';import {fileURLToPath} from 'node:url';
import {footprintHash} from './check-prepared.mjs';import {validateGeometryMigrations} from './prepare-geographic-release.mjs';
const sha=b=>createHash('sha256').update(b).digest('hex'),read=p=>JSON.parse(fs.readFileSync(p)),json=x=>JSON.stringify(x);
function dataset(directory){return read(path.join(directory,'world-index.json')).parts.flatMap(p=>{const file=path.resolve(directory,p);if(!file.startsWith(path.resolve(directory)+path.sep))throw Error('Unsafe geographic part');return read(file).features;});}
export function stageLandCreations({before,after,proofs,output}){
 before=path.resolve(before);after=path.resolve(after);output=path.resolve(output);
 if(fs.existsSync(output)||[before,after].some(p=>output===p||output.startsWith(p+path.sep)||p.startsWith(output+path.sep)))throw Error('Creation output must be a fresh, separate directory');
 const old=dataset(before),next=dataset(after),existing=new Map(old.map(f=>[f.id,f])),now=new Map(next.map(f=>[f.id,f]));
 if(existing.size!==old.length||now.size!==next.length||old.some(f=>!now.has(f.id)||json(now.get(f.id))!==json(f)))throw Error('Pure creation cannot rename, move or remove existing territory');
 const added=next.filter(f=>!existing.has(f.id));if(!added.length)throw Error('No genuinely new locations');
 if(added.some(f=>f.properties.reference_owner!=null||f.properties.metadata?.reference_owner_id!=null))throw Error('New attributes must remain unknown unless separately sourced');
 const input=read(proofs);if(!Array.isArray(input)||input.length!==added.length)throw Error('One creation proof per new territory required');
 const base=path.dirname(path.resolve(proofs)),units=read(path.join(after,'hierarchy.json'));
 const originalUnits=read(path.join(before,'hierarchy.json')),nextUnits=new Map(units.map(u=>[u.id,u]));
 if(originalUnits.some(u=>!nextUnits.has(u.id)||['name','level','parent_id'].some(key=>u[key]!==nextUnits.get(u.id)[key])))throw Error('Pure creation cannot rename, reparent or retire existing groups');
 execFileSync('python3',[fileURLToPath(new URL('./validate-land-creations.py',import.meta.url))],{input:json({before:old,after:next,units,proofs:input,base}),maxBuffer:16*1024*1024});
 fs.mkdirSync(path.dirname(output),{recursive:true});const temporary=fs.mkdtempSync(path.join(path.dirname(output),'.land-creations-'));
 try{
  const files={},put=(name,bytes)=>{fs.mkdirSync(path.dirname(path.join(temporary,name)),{recursive:true});fs.writeFileSync(path.join(temporary,name),bytes);files[name]={sha256:sha(bytes)};};
  const retainedProofs=input.map((proof,i)=>{const raw=fs.readFileSync(path.resolve(base,proof.source.path)),name=`sources/${i}.geojson`;put(name,raw);return {...proof,source:{...proof.source,path:name}};});
  put('after-hierarchy.json',fs.readFileSync(path.join(after,'hierarchy.json')));
  const receipt={version:1,geometry_stage_validated:true,historical_claims_transferred:false,before_hierarchy_sha256:sha(fs.readFileSync(path.join(before,'hierarchy.json'))),before_footprints_sha256:footprintHash(old),after_footprints_sha256:footprintHash(next),changed_ids:[],removed_ids:[],added_ids:added.map(f=>f.id).sort(),reused_ids:old.map(f=>f.id).sort(),archives:[],added_features:added,creation_proofs:retainedProofs,relationships:added.map(f=>({kind:'source-backed-create',proposal_id:f.id,before_ids:[],after_ids:[f.id],history_transfer:false})),source_evidence:retainedProofs.map(p=>({url:p.source.url,source_sha256:p.source.sha256,license:p.source.license,attribution:p.source.attribution,supported_from:p.source.supported_from,supported_to:p.source.supported_to})),source_repair_scope:'pure source-backed omitted-land additions; existing identity/name changes require a separate receipt'};
  put('migration-receipt.json',json(receipt));const manifest={version:1,history_transfer:false,before_footprints_sha256:receipt.before_footprints_sha256,after_footprints_sha256:receipt.after_footprints_sha256,files};
  fs.writeFileSync(path.join(temporary,'index.json'),json(manifest));
  validateGeometryMigrations({features:next,baselineIds:old.map(f=>f.id),baselineFootprints:receipt.before_footprints_sha256,manifestFiles:[path.join(temporary,'index.json')],units});
  fs.renameSync(temporary,output);return {output,added_ids:receipt.added_ids,before_footprints_sha256:receipt.before_footprints_sha256,after_footprints_sha256:receipt.after_footprints_sha256,manifest_sha256:sha(fs.readFileSync(path.join(output,'index.json')))};
 }catch(error){fs.rmSync(temporary,{recursive:true,force:true});throw error;}
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 const get=key=>{const value=process.argv.find(a=>a.startsWith('--'+key+'='))?.slice(key.length+3);if(!value)throw Error('Required --'+key+'=path');return value;};
 console.log(json(stageLandCreations(Object.fromEntries(['before','after','proofs','output'].map(key=>[key,get(key)])))));
}
