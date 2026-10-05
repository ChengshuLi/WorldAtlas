import http from 'node:http';
import fs from 'node:fs/promises';
import path from 'node:path';
import {build} from 'vite';
await build({base:'./',build:{outDir:'.cache/wheel-zoom/client'},define:{'import.meta.env.VITE_STATIC_ATLAS':JSON.stringify('true'),'import.meta.env.VITE_HOSTED_DATABASE':JSON.stringify('true')}});
const root=path.resolve('.cache/wheel-zoom/client');
const types={'.js':'text/javascript','.css':'text/css','.html':'text/html','.json':'application/json'};
http.createServer(async(req,res)=>{
 try{
  if(req.method!=='GET'){res.writeHead(405);res.end();return;}
  const url=new URL(req.url,'http://127.0.0.1:3886'),local=path.resolve(root,'.'+(url.pathname==='/'?'/index.html':url.pathname));
  if(!local.startsWith(root+'/'))throw Error('Invalid path');
  try{const bytes=await fs.readFile(local);res.setHeader('Content-Type',types[path.extname(local)]||'application/octet-stream');res.end(bytes);return;}catch{}
  const response=await fetch('https://worldatlas-explorer.chengshu-worldatlas.workers.dev'+url.pathname+url.search);
  res.writeHead(response.status,{'Content-Type':response.headers.get('Content-Type')||'application/octet-stream'});res.end(Buffer.from(await response.arrayBuffer()));
 }catch(e){res.writeHead(502);res.end(e.message);}
}).listen(3886,'127.0.0.1',()=>console.log('Read-only wheel preview ready on 3886'));
