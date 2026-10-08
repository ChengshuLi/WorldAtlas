import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {reconcile} from './r2-reconcile.mjs';
import {httpBucket} from './r2-migration-http.mjs';

export async function run(config, transport=fetch) {
  if (!path.isAbsolute(config.output) || typeof config.copy!=='boolean') throw Error('Absolute fresh output path and explicit copy boolean required');
  // Refuse symlink parents and a pre-existing run. No old receipt is replaced.
  let parent=path.dirname(config.output);
  while(true){if((await fs.lstat(parent)).isSymbolicLink())throw Error('Symlink output parent refused');const next=path.dirname(parent);if(next===parent)break;parent=next;}
  await fs.mkdir(config.output,{recursive:false});
  const proofs=await fs.open(path.join(config.output,'object-verification.jsonl'),'wx',0o600);
  try {
    const result=await reconcile({source:httpBucket(config.source,transport),destination:httpBucket(config.destination,transport),copy:config.copy,
      onVerified:async row=>{await proofs.write(JSON.stringify(row)+'\n');await proofs.sync();}});
    await fs.writeFile(path.join(config.output,'reconciliation.json'),JSON.stringify(result,null,2)+'\n',{flag:'wx',mode:0o600});
    return {output:config.output,source_objects:result.source.objects.length,verified_objects:result.proofs.length,
      remaining_objects:result.missing.length,metadata_discrepancies:result.proofs.filter(row=>!row.metadata_equal).length};
  } catch(error) {
    await fs.writeFile(path.join(config.output,'failure.json'),JSON.stringify({status:'failed',message:error.message,at:new Date().toISOString(),partial_proof:'object-verification.jsonl'})+'\n',{flag:'wx',mode:0o600});
    throw error;
  } finally {await proofs.close();}
}
if(process.argv[1] && import.meta.url===pathToFileURL(process.argv[1]).href) {
  try {
    let input='';for await(const chunk of process.stdin){input+=chunk;if(Buffer.byteLength(input)>65536)throw Error('Configuration too large');}
    console.log(JSON.stringify(await run(JSON.parse(input))));
  } catch(error) {console.error(error.message);process.exitCode=1;}
}
