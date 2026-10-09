// Executed only from a verified immutable baseline, with a read-only token.
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {githubAPI} from './issue-claim-contract.mjs';
import {collectGeographicApproval} from './geographic-adjudication-api.mjs';
import {gitBlobTransport} from './git-blob-transport.mjs';
import {copyAPIFeatures,requestAccounting,quotaDelay} from './github-quota.mjs';

export async function runGeographicApproval({repo,number,expectedHead,token,directory=process.cwd(),
 apiFactory=githubAPI,transportFactory=gitBlobTransport,collect=collectGeographicApproval}){
 const accounting=requestAccounting('geographic-adjudication'),downloads=[];
 const direct=apiFactory(token,{onRequest:accounting.observe});let transport;
 const api=copyAPIFeatures((...args)=>(transport?.api??direct)(...args),direct);
 // Ordinary source-only packets return not-requested without allocating a store.
 api.prefetchGitBlobs=async(targetRepo,rows)=>{
  if(!transport)transport=transportFactory(direct,{repo,token,directory,onFetch:row=>downloads.push(row)});
  return transport.api.prefetchGitBlobs(targetRepo,rows);
 };
 api.hasGitBlobs=(targetRepo,rows)=>transport?.api.hasGitBlobs(targetRepo,rows)??false;
 let result;
 try{result=await collect({api,repo,number,expectedHead});}
 catch(error){
  const delay=quotaDelay(error);
  result={status:'blocked',reason:error instanceof SyntaxError?'Malformed source dossier or review JSON':String(error.message).slice(0,1024),
   ...(error.github?{api_error:error.github}:{}),retryable:delay!==null,
   ...(delay!==null?{retry_at:new Date(Date.now()+delay).toISOString()}:{}),limits:['No successful source authority is published for an incomplete check.']};
 }
 finally{transport?.close();}
 return {...result,request_accounting:accounting.receipt(),immutable_transport:downloads};
}

if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 try{
  const values={},args=process.argv.slice(2);
  for(let index=0;index<args.length;index+=2){
   if(!['--pr','--head'].includes(args[index])||!args[index+1]||Object.hasOwn(values,args[index]))throw Error('Use exact --pr NUMBER --head COMMIT arguments');
   values[args[index]]=args[index+1];
  }
  if(!/^[1-9]\d*$/.test(values['--pr']??'')||!/^[a-f0-9]{40}$/.test(values['--head']??''))throw Error('Require exact PR number and reviewed commit');
  const result=await runGeographicApproval({repo:process.env.GITHUB_REPOSITORY??'ChengshuLi/WorldAtlas',number:Number(values['--pr']),expectedHead:values['--head'],token:process.env.GH_TOKEN});
  const raw=JSON.stringify(result)+'\n';if(Buffer.byteLength(raw)>48*1024*1024)throw Error('Approval transport exceeds bounded base64 budget');
  process.stdout.write(raw);if(result.status==='blocked')process.exitCode=1;
 }catch(error){process.stdout.write(JSON.stringify({status:'blocked',reason:error instanceof SyntaxError?'Malformed source dossier or review JSON':String(error.message).slice(0,1024)})+'\n');process.exitCode=1;}
}
