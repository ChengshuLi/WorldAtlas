import fs from 'node:fs';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';

process.chdir(fileURLToPath(new URL('..',import.meta.url)));
const phase=process.argv[2]??'contracts';
const contracts=['migration-hashes','attributes','temporal','unsettled-rank','unresolved-attributes','evidence-suppression','hosted-records','prepared-evidence','hosted-evidence-availability','geographic-releases','boundary-version-hash','reference-archive'];
const jobs={
 contracts:[[process.execPath,['--test',...contracts.map(name=>`test/${name}.test.mjs`)]]],
 scientific:[...fs.readdirSync('test').filter(name=>name.endsWith('.py')).sort().map(name=>[process.env.ATLAS_PYTHON??'python3',[`test/${name}`]]),[process.env.ATLAS_PYTHON??'python3',['scripts/prepare-ghsl-population.py','--self-test']]],
 publication:[[process.execPath,['--test','--test-concurrency=2',...fs.readdirSync('test').filter(name=>name.endsWith('.test.mjs')).sort().map(name=>`test/${name}`)]],[process.execPath,['--test','test/geographic-release-preparation.mjs']],[process.execPath,['scripts/validate-prepared.mjs']],[process.env.ATLAS_PYTHON??'python3',['scripts/validate-ownership-runtime.py','--source','data/ownership-history','--runtime','data/ownership-runtime']]],
 browser:[[process.execPath,['--test','test/browser.mjs']],[process.execPath,['test/static-rendering.mjs']]],
 'content-only':[[process.execPath,['--test','test/content-independence.mjs','test/import-records-ui.mjs']]],
};
if(phase==='--list'){console.log(JSON.stringify(jobs,null,2));process.exit(0);}
if(!jobs[phase])throw Error(`Unknown validation phase: ${phase}. Use ${Object.keys(jobs).join(', ')}.`);
const environment={...process.env,...(phase==='publication'?{ATLAS_REQUIRE_PREPARED:'1',ATLAS_REQUIRE_STATIC:'1'}:{})};
for(const [command,args]of jobs[phase]){
 console.log(`Checking: ${command} ${args.join(' ')}`);
 const result=spawnSync(command,args,{stdio:'inherit',env:environment});
 if(result.error)throw result.error;
 if(result.status!==0){console.error(`Validation failed (${result.signal??result.status}); remaining checks were not run.`);process.exit(result.status||1);}
}
console.log(`PASS: ${phase} validation commands completed.`);
