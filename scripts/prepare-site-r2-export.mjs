import fs from 'node:fs/promises';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {pathToFileURL} from 'node:url';

const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
export async function prepare({root, originalCommit, esbuildModule, receipt}) {
  if(!path.isAbsolute(root)||!path.isAbsolute(esbuildModule)||!path.isAbsolute(receipt)||!/^[a-f0-9]{40}$/.test(originalCommit))throw Error('Use absolute paths and exact original commit');
  // Fresh receipt reservation occurs before changing build output.
  const reserved=await fs.open(receipt,'wx',0o600);
  const git=(...args)=>execFileSync('git',['-C',root,...args],{maxBuffer:32*1024**2});
  try {
    const paths=git('ls-tree','-r','--name-only',originalCommit,'--','dist','drizzle','.openai/hosting.json').toString().trim().split('\n');
    if(paths.length>1000 || !paths.includes('dist/server/index.js') || !paths.includes('dist/client/index.html'))throw Error('Unsupported original package inventory');
    const unchanged=[];
    let total=0;
    for(const name of paths.filter(name=>name!=='dist/server/index.js')) {
      const original=git('show',originalCommit+':'+name);
      total+=original.length;if(total>512*1024**2)throw Error('Original package exceeds admitted build size');
      const filename=path.join(root,name);
      if(!(await fs.lstat(filename)).isFile())throw Error('Original package member is not a regular file');
      const current=await fs.readFile(filename);
      if(!current.equals(original))throw Error('Refusing changed original package member: '+name);
      unchanged.push({path:name,bytes:original.length,sha256:hash(original)});
    }
    const original=git('show',originalCommit+':dist/server/index.js');
    const wrapper=await fs.readFile(path.join(root,'hosted/site-r2-export.js'));
    const {build}=await import(pathToFileURL(esbuildModule).href);
    const result=await build({stdin:{contents:"import inner from 'worldatlas:original';import {readOnlyR2Export} from './hosted/site-r2-export.js';export default readOnlyR2Export(inner);",resolveDir:root,sourcefile:'migration-wrapper-entry.js'},
      bundle:true,write:false,format:'esm',platform:'browser',target:'es2022',minify:false,
      plugins:[{name:'pinned-original-site-worker',setup(build){build.onResolve({filter:/^worldatlas:original$/},()=>({path:'original',namespace:'pinned'}));build.onLoad({filter:/.*/,namespace:'pinned'},()=>({contents:original.toString('utf8'),loader:'js'}));}}]});
    if(result.outputFiles.length!==1)throw Error('Unexpected wrapper build outputs');
    const output=result.outputFiles[0].contents;
    await fs.writeFile(path.join(root,'dist/server/index.js'),output);
    for(const file of unchanged)if(hash(await fs.readFile(path.join(root,file.path)))!==file.sha256)throw Error('Preserved package member changed during build');
    const proof={version:1,original_commit:originalCommit,original_worker:{bytes:original.length,sha256:hash(original)},wrapper_sha256:hash(wrapper),
      output_worker:{bytes:output.length,sha256:hash(output)},unchanged_members:unchanged,
      deployment:false,database_writes:false,object_writes:false};
    await reserved.write(JSON.stringify(proof,null,2)+'\n');await reserved.sync();return proof;
  } catch(error) {
    await reserved.write(JSON.stringify({status:'failed',message:error.message})+'\n');throw error;
  } finally {await reserved.close();}
}
if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href){
  try{const [root,originalCommit,esbuildModule,receipt]=process.argv.slice(2);const result=await prepare({root,originalCommit,esbuildModule,receipt});console.log(JSON.stringify({preserved_members:result.unchanged_members.length,original_commit:result.original_commit}));}
  catch(error){console.error(error.message);process.exitCode=1;}
}
