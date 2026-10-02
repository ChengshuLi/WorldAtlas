// Reproduce only the candidate, null-predecessor receipt and read-only cell screen.
import fs from 'node:fs';import path from 'node:path';import {execFileSync} from 'node:child_process';import {fileURLToPath,pathToFileURL} from 'node:url';
const here=path.dirname(fileURLToPath(import.meta.url));
export async function reproduceMarcus({root,output}){
 root=path.resolve(root);output=path.resolve(output);
 execFileSync('python3',[path.join(here,'prepare.py'),'--root='+root,'--output='+output],{maxBuffer:4*1024*1024});
 const {stageLandCreations}=await import(pathToFileURL(path.join(root,'scripts/stage-land-creations.mjs')));
 const migration=stageLandCreations({before:path.join(root,'data'),after:path.join(output,'after'),proofs:path.join(output,'proof-input/proofs.json'),output:path.join(output,'migration')});
 execFileSync(process.execPath,[path.join(here,'grid-check.mjs'),root,output],{maxBuffer:4*1024*1024});
 return {migration,grid:JSON.parse(fs.readFileSync(path.join(output,'grid-report.json'))),scope:'Candidate only; private preflight, combined publication and regional interior approval remain separate'};
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 const arg=key=>{const value=process.argv.find(a=>a.startsWith('--'+key+'='))?.slice(key.length+3);if(!value)throw Error('Required --'+key);return value;};console.log(JSON.stringify(await reproduceMarcus({root:arg('root'),output:arg('output')})));
}
