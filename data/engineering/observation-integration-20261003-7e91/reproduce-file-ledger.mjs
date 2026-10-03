import fs from 'node:fs';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';

const [base,output]=process.argv.slice(2);
if(!/^[a-f0-9]{40}$/.test(base??'')||!output||fs.existsSync(output))throw Error('Supply an exact base SHA and a new output path');
const git=args=>execFileSync('git',args,{encoding:'utf8'}).trim().split('\n').filter(Boolean);
const own='data/engineering/observation-integration-20261003-7e91/';
const paths=[...new Set([...git(['diff','--name-only',base]),...git(['ls-files','--others','--exclude-standard']).filter(path=>path.startsWith(own))])].filter(path=>path!==output&&path!==own+'file-ledger.json').sort();
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const files=paths.map(path=>{const stat=fs.lstatSync(path);if(!stat.isFile()||stat.isSymbolicLink())throw Error('Ordinary evidence files only');const bytes=fs.readFileSync(path);return {path,bytes:bytes.length,sha256:sha(bytes)};});
const frozenPaths=git(['ls-tree','-r','--name-only',base]).filter(path=>path.startsWith('drizzle/')||path.startsWith('postgres/')||['data/hosted-type-catalog.json','src/typed-observations.js','src/observation-registry.js','hosted/storage-export.js','hosted/storage-export-v2.js','hosted/storage-export-v2-contract.js','hosted/storage-export-v3-contract.js','scripts/restore-postgres-storage.mjs','scripts/restore-postgres-storage-v2.mjs'].includes(path));
const preserved=frozenPaths.map(path=>{const original=execFileSync('git',['show',base+':'+path],{maxBuffer:16*1024*1024}),current=fs.readFileSync(path);if(!current.equals(original))throw Error('Retained original changed: '+path);return {path,bytes:original.length,sha256:sha(original)};});
fs.writeFileSync(output,JSON.stringify({version:1,base_main_commit:base,source_commit:execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim(),purpose:'Optional report-only whole-file evidence ledger; not an adopted contract or self-certification',ledger_self_excluded:true,files,preserved_originals:preserved},null,2)+'\n',{flag:'wx'});
