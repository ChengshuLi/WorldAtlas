// Execute complete immutable row partitions sequentially, with bounded memory.
import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
const options={};
for(let n=2;n<process.argv.length;n+=2){
  const key=process.argv[n];
  if(!['--repo','--commit','--out'].includes(key)||!process.argv[n+1]||options[key])
    throw Error('Require explicit repository, immutable baseline and fresh output directory');
  options[key]=process.argv[n+1];
}
if(!options['--repo']||!/^[a-f0-9]{40}$/.test(options['--commit']??'')||!options['--out'])
  throw Error('Require explicit repository, immutable baseline and fresh output directory');
const repo=path.resolve(options['--repo']),root=path.resolve(options['--out']),baseline=options['--commit'];
if(fs.existsSync(root))throw Error('Refuse existing output directory');
const git=args=>execFileSync('git',['-C',repo,...args],{encoding:'utf8',maxBuffer:32*1024*1024});
const size=JSON.parse(git(['show',baseline+':data/canonical-grid/manifest.json'])).size;
if(!Number.isSafeInteger(size)||size<2||!Number.isSafeInteger(size**2))throw Error('Unsupported complete grid domain');
const head=git(['rev-parse','HEAD']).trim(),sha=raw=>createHash('sha256').update(raw).digest('hex');
fs.mkdirSync(root,{recursive:false});
const state={version:1,phase:'running',pid:process.pid,evaluation_commit:head,baseline_commit:baseline,size,completed:[],counts:{}};
const save=()=>fs.writeFileSync(path.join(root,'progress.json'),JSON.stringify(state,null,2)+'\n');
save();
try{
  for(let start=0;start<size;start+=4096){
    const end=Math.min(size,start+4096),name=`rows-${start}-${end}.json.gz`,out=path.join(root,name);
    const receipt=execFileSync(process.execPath,[path.join(repo,'scripts/audit-canonical-rows.mjs'),
      '--commit',baseline,'--row-start',String(start),'--row-end',String(end),'--out',out],
      {cwd:repo,encoding:'utf8',maxBuffer:2*1024*1024});
    const measured=JSON.parse(receipt),raw=fs.readFileSync(out),decoded=gunzipSync(raw,{maxOutputLength:32*1024*1024});
    const report=JSON.parse(decoded);
    if(report.evaluation_commit!==head||report.baseline_commit!==baseline||report.domain.row_start!==start||
       report.domain.row_end!==end||report.domain.checked_cells!==(end-start)*size)throw Error('Partition scope differs');
    state.completed.push({path:name,bytes:raw.length,decoded_bytes:decoded.length,sha256:sha(raw),row_start:start,row_end:end,
      checked_cells:report.domain.checked_cells,findings:report.findings.length,boundary_ties:report.boundary_ties.length,
      elapsed_seconds:measured.elapsed_seconds,node_resource_usage_maxRSS:measured.node_resource_usage_maxRSS});
    for(const [key,value] of Object.entries(report.counts))state.counts[key]=(state.counts[key]??0)+value;
    save();console.log(JSON.stringify({completed:state.completed.length,row_end:end,checked_cells:state.counts.checked_cells}));
  }
  if(state.counts.checked_cells!==size**2)throw Error('Incomplete world accounting');
  state.phase='complete';state.unchecked_rows=0;state.unchecked_cells=0;save();
}catch(error){
  state.phase='failed';state.error=String(error);save();throw error;
}
