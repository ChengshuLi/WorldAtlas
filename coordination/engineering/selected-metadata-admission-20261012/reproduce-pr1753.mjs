// Exact merged PR1753 replay. Requires these pinned commits and consumed Git
// blobs locally; never fetches, extracts a dataset or rewrites original inputs.
import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {selectedDataCandidate, selectedDataSelection} from '../../../scripts/integration-profile.mjs';
import {memoizeImmutableGitBlobs} from '../../../scripts/immutable-git-blobs.mjs';
const fixture=JSON.parse(fs.readFileSync(new URL('./pr1753.json',import.meta.url)));
const {base,head,branch}=fixture, output=process.argv[2];
if(!output||process.argv.length!==3)throw Error('Supply one fresh output JSON path');
const destination=path.resolve(output),relative=path.relative(process.cwd(),destination),parent=path.dirname(destination);
if(!relative||relative.startsWith('..')||path.isAbsolute(relative)||fs.realpathSync(parent)!==parent)throw Error('Use a fresh path inside this checkout without symlink parents');
try {fs.lstatSync(output);throw Error('Output already exists');} catch(error) {if(error.code!=='ENOENT')throw error;}
const git=(...args)=>execFileSync('git',args,{maxBuffer:32*1024**2,
  env:{...process.env,GIT_NO_LAZY_FETCH:'1',GIT_CONFIG_NOSYSTEM:'1',GIT_CONFIG_GLOBAL:'/dev/null',GIT_TERMINAL_PROMPT:'0'}});
const sizes=new Map(fixture.retained_tree_rows.map(row=>[row.sha,row.size])),trees=new Map(),reads=[];
function tree(commit){
  if(trees.has(commit))return trees.get(commit);
  const entries=git('ls-tree','-r','-z',commit).toString().split('\0').filter(Boolean).map(line=>{
    const at=line.indexOf('\t'),[mode,type,sha]=line.slice(0,at).split(' '),name=line.slice(at+1);
    return [name,{path:name,mode,type,sha,get size(){if(!sizes.has(sha))sizes.set(sha,Number(git('cat-file','-s',sha).toString()));return sizes.get(sha);}}];
  });
  const result={object:{sha:commit},entries:new Map(entries)};trees.set(commit,result);return result;
}
const files=git('diff','--name-status','--no-renames',base,head).toString().trim().split('\n').map(line=>{
  const [status,filename]=line.split('\t');return {filename,status:{A:'added',M:'modified',D:'removed'}[status]};
});
if(JSON.stringify(files)!==JSON.stringify(fixture.files))throw Error('Complete actual PR diff differs from retained fixture');
const api=async route=>{
  const part=route.split('/repos/ChengshuLi/WorldAtlas/')[1];
  if(part?.startsWith('git/blobs/')){const sha=part.slice(10),bytes=git('cat-file','blob',sha);reads.push({sha,bytes:bytes.length});return {sha,size:bytes.length,encoding:'base64',content:bytes.toString('base64')};}
  if(part?.startsWith('git/commits/')){const sha=part.slice(12);return {sha,tree:{sha:git('rev-parse',sha+'^{tree}').toString().trim()}};}
  if(part?.startsWith('git/trees/'))return {truncated:false,tree:[...tree(part.slice(10).split('?')[0]).entries.values()]};
  if(part?.startsWith('compare/')){const [old,current]=part.slice(8).split('...');git('merge-base','--is-ancestor',old,current);return {status:old===current?'identical':'ahead'};}
  throw Error('Unexpected immutable replay route');
};
const diagnostics={},start=performance.now(),result=await selectedDataSelection({api:memoizeImmutableGitBlobs(api),repo:'ChengshuLi/WorldAtlas',branch,files,
  baseline:tree(base),authored:tree(head),base,head,metadataDiagnostics:diagnostics});
const report={base,head,files:files.length,prefilter:selectedDataCandidate(branch,files),result,
  metadata_blob_reads:reads.length,metadata_bytes:reads.reduce((total,row)=>total+row.bytes,0),elapsed_ms:performance.now()-start,
  memoizer_sha256:createHash('sha256').update(fs.readFileSync(new URL('../../../scripts/immutable-git-blobs.mjs',import.meta.url))).digest('hex'),
  classifier_sha256:createHash('sha256').update(fs.readFileSync(new URL('../../../scripts/integration-profile.mjs',import.meta.url))).digest('hex'),diagnostics,reads};
fs.writeFileSync(output,JSON.stringify(report,null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify({...report,reads:undefined}));
if(result?.test_selection!=='selected-data')process.exitCode=1;
