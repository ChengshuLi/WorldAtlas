import fs from 'node:fs';
import {execFileSync} from 'node:child_process';
import {validatePremergeManifest} from '../../../scripts/premerge-evidence.mjs';
import {workSpec} from '../../../scripts/issue-claim-contract.mjs';
const root='data/engineering/startup-scheduling-20261004-a9c2/',manifestPath='coordination/engineering/startup-scheduling-20261004-a9c2/evidence-quality.json';
const manifest=JSON.parse(fs.readFileSync(manifestPath)),issue=JSON.parse(fs.readFileSync(root+'issue-metadata-current.json'));
const diff=execFileSync('git',['diff','--name-status','--no-renames',manifest.baseline.commit],{encoding:'utf8'}).trim().split('\n').filter(Boolean);
const files=diff.map(line=>{const [status,filename]=line.split('\t');return {filename,status:({A:'added',M:'modified',D:'removed'})[status]};});
for(const filename of execFileSync('git',['ls-files','--others','--exclude-standard'],{encoding:'utf8'}).trim().split('\n').filter(Boolean))if(!files.some(f=>f.filename===filename))files.push({filename,status:'added'});
const cache=new Map();
const result=validatePremergeManifest(manifest,{manifestPath,issue,spec:workSpec(issue.body),files,
 reservation:JSON.parse(fs.readFileSync(root+'reservation-current.json')),branch:'engineering/startup-scheduling-20261004-a9c2',pr:{base:{sha:execFileSync('git',['rev-parse','origin/main'],{encoding:'utf8'}).trim()}},
 readFile:(name,vintage)=>{const key=vintage+':'+name;if(!cache.has(key))cache.set(key,vintage==='candidate'?fs.readFileSync(name):execFileSync('git',['show',(vintage==='base'?execFileSync('git',['rev-parse','origin/main'],{encoding:'utf8'}).trim():vintage)+':'+name],{maxBuffer:32*1024*1024}));return cache.get(key);}});
console.log(JSON.stringify(result,null,2));
