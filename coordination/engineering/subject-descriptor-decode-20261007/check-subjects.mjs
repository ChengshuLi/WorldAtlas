import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {validateEvidence,sha256,subjectsHash} from '../../../scripts/evidence-quality.mjs';
const dir=path.dirname(fileURLToPath(import.meta.url)),repo=path.resolve(dir,'../../..');
const [codeCommit,outputName]=process.argv.slice(2);
if(!/^[a-f0-9]{40}$/.test(codeCommit??'')||!/^run-(one|two)$/.test(outputName??''))throw Error('Use exact immutable commit and run-one/run-two');
const git=(commit,name)=>execFileSync('/usr/bin/git',['-C',repo,'show',`${commit}:${name}`],{maxBuffer:33554433});
const executed=['scripts/evidence-quality.mjs','coordination/engineering/subject-descriptor-decode-20261007/check-subjects.mjs','coordination/engineering/subject-descriptor-decode-20261007/source-plan.json'];
for(const name of executed)if(!git(codeCommit,name).equals(fs.readFileSync(path.join(repo,name))))throw Error('Executed input/code differs from immutable commit');
const plan=JSON.parse(git(codeCommit,executed[2]));
const m={version:1,issue:1393,lane:'geography',worker_id:'01a10fea-fe9b-7722-a974-0269a733a330',subject_ids:plan.subject_ids,subject_ids_sha256:subjectsHash(plan.subject_ids),
 baseline:{commit:plan.source_commit,files:plan.files,pins:{},subject_files:plan.subject_files},sources:[],outputs:[],metrics:[],summaries:[],conclusions:[],
 methods:[{id:'subject-decode',description:'Whole baseline membership only',software:process.version,units:'subjects'}],
 stages:{research:'complete',implementation:'not-proposed',geographic_approval:'not-requested'},commands:['check-subjects.mjs exact-commit run-one|run-two']};
const sourceReads=new Map();
const result=validateEvidence(m,{expectedSubjects:plan.subject_ids,readFile:(name,vintage)=>{
 if(vintage!==plan.source_commit||!plan.files.some(f=>f.path===name))throw Error('Undeclared source/vintage');
 const row=execFileSync('/usr/bin/git',['-C',repo,'ls-tree',vintage,'--',name],{encoding:'utf8'}).trim().split(/\s+/);
 if(row[0]!=='100644'||row[1]!=='blob'||row[3]!==name)throw Error('Nonordinary source');
 const raw=git(vintage,name);sourceReads.set(name,{path:name,commit:vintage,mode:row[0],blob_oid:row[2],bytes:raw.length,sha256:sha256(raw)});return raw;
}});
const scientific={status:'passed',method_id:'subject-decode',kind:'positive',outcome:'passed',subject_count:plan.subject_ids.length,physical_components:plan.scope.physical_components,current_contacts:plan.scope.current_contacts,numeric_siblings_preserved:plan.scope.numeric_siblings_preserved,subject_ids_sha256:m.subject_ids_sha256,source_commit:plan.source_commit,source_reads:[...sourceReads.values()],checked:result.checked,limits:plan.limits};
// Exclusive ordinary destination, with no caller-provided path or symlink ancestors.
const cache=path.join(dir,'.cache');if(fs.existsSync(cache)&&(!fs.lstatSync(cache).isDirectory()||fs.lstatSync(cache).isSymbolicLink()))throw Error('Unsafe cache');
fs.mkdirSync(cache,{recursive:true});const out=path.join(cache,outputName);fs.mkdirSync(out);fs.writeFileSync(path.join(out,'subjects.json'),JSON.stringify(scientific,null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify({status:'passed',output:outputName,scientific_sha256:sha256(fs.readFileSync(path.join(out,'subjects.json'))),subjects:plan.subject_ids.length,source_files:sourceReads.size,node:process.version,code_commit:codeCommit}));
