import fs from 'node:fs';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {performance} from 'node:perf_hooks';
import {gitBlobTransport} from '../../../scripts/git-blob-transport.mjs';
const repo='ChengshuLi/WorldAtlas',commit='8b6835dfa645cf763137374c3730401d5ac2f732';
const manifestPath='coordination/engineering/worldwide-native-batches-1184-20261006/evidence-quality.json';
const git=(...args)=>execFileSync('git',args,{maxBuffer:64*1024*1024});
const manifest=JSON.parse(git('show',commit+':'+manifestPath));
const bindings=[...manifest.baseline.files.map(row=>[manifest.baseline.commit,row.path]),
 ...manifest.outputs.map(row=>[commit,row.path]),...manifest.sources.flatMap(source=>(source.files??[]).map(row=>[commit,row.path]))];
const rows=bindings.map(([version,path])=>{
 const fields=git('ls-tree','-l',version,'--',path).toString().trim().split(/\s+/);
 if(fields[1]!=='blob'||!['100644','100755'].includes(fields[0]))throw Error('Invalid pinned descriptor');
 return {sha:fields[2],size:Number(fields[3])};
});
const batches=[],directory=fs.mkdtempSync('.quota-real-transport-');let rest=0;
const transport=gitBlobTransport(async()=>{rest++;throw Error('Unexpected REST read');},{repo,token:execFileSync('gh',['auth','token'],{encoding:'utf8'}).trim(),directory:fs.realpathSync(directory),onFetch:row=>batches.push(row)});
const started=performance.now();
try {
 await transport.api.prefetchGitBlobs(repo,[...new Map(rows.map(row=>[row.sha,row])).values()]);
 for(const [i,row] of rows.entries()){
  const value=await transport.api(`/repos/${repo}/git/blobs/${row.sha}`);
  const actual=Buffer.from(value.content,'base64'),expected=git('show',bindings[i].join(':'));
  if(!actual.equals(expected))throw Error('Hosted bytes differ from actual pinned Git evidence');
 }
 const result={commit,manifestPath,baseline:manifest.baseline.commit,descriptor_loads:rows.length,unique_oids:new Set(rows.map(x=>x.sha)).size,
   actual_git_fetches:batches.length,actual_blob_rest_requests:rest,decoded_bytes:batches.reduce((a,b)=>a+b.decoded_bytes,0),all_whole_file_bytes_match:true,
   duration_ms:Math.round(performance.now()-started),manifest_sha256:createHash('sha256').update(git('show',commit+':'+manifestPath)).digest('hex'),
   limit:'Actual GitHub exact-blob transfer and pinned local-byte comparison; not a hosted Actions authority/merge validation measurement. Prior 306 blob calls were an inventory bound, not instrumented HTTP counts.'};
 fs.writeFileSync('coordination/engineering/actions-quota-1249-20261006/transport-probe.json',JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result));
}finally{transport.close();fs.rmdirSync(directory);}
