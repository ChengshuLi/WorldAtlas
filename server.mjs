import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {isDeepStrictEqual} from 'node:util';
import {resolveTypedSnapshot} from './src/typed-snapshot.js';
import {finalBankSelection,scientificNativeSelection} from './src/reference-metadata.js';
import {loadPackageInputs} from './scripts/package-inputs.mjs';
import {streamedPackageFile} from './scripts/package-output-artifact.mjs';

const repository=path.dirname(fileURLToPath(import.meta.url));
const json=file=>JSON.parse(fs.readFileSync(file));
const need=(ok,message)=>{if(!ok)throw Error(message);};
const sha=raw=>createHash('sha256').update(raw).digest('hex');
const git=(root,args)=>execFileSync('git',['--no-replace-objects','-C',root,...args],{encoding:'utf8',maxBuffer:Infinity,
  env:{...process.env,GIT_NO_LAZY_FETCH:'1',GIT_NO_REPLACE_OBJECTS:'1',GIT_TERMINAL_PROMPT:'0'}});

// Preview copies no map and constructs no alternate ownership. Reuse the actual
// ordinary package, with its current E header and whole file identities checked.
export function inspectPreviewPackage(root=repository) {
  root=fs.realpathSync(root);
  const output=fs.existsSync(path.join(root,'dist/client/atlas-geography.json'))?'dist/client':'dist';
  const atlas=json(path.join(root,output,'atlas-geography.json'));
  const selection=json(path.join(root,'data/ownership-selection.json')),bank=finalBankSelection(selection);
  const indexRaw=fs.readFileSync(path.join(root,bank?.path??'data/canonical-grid/current-startup/index.json')),index=JSON.parse(indexRaw);
  if(bank)need(indexRaw.length===bank.bytes&&sha(indexRaw)===bank.sha256,'Preview selected final-bank index differs');
  need(index.native_manifest_sha256===scientificNativeSelection(selection).sha256,
    'Preview native selection differs');
  need(isDeepStrictEqual(atlas.preparedOwnership,index.preparedOwnership),'Preview prepared ownership differs');
  const {reference_owner_sha256,...pixelMap}=atlas.pixelMap??{};
  need(isDeepStrictEqual(pixelMap,index.pixelMap),'Preview complete ownership header differs');
  if(bank)need(isDeepStrictEqual(atlas.reference_release,selection.reference),'Preview final release differs');
  const {application_reference_revision,...referenceMetadata}=atlas.referenceMetadata??{};
  need(isDeepStrictEqual(index.referenceMetadata,atlas.referenceMetadata?referenceMetadata:undefined),'Preview reference projection differs');
  need(Array.isArray(index.files)&&index.files.length>0,'Preview complete package files missing');
  for(const pin of index.files){
    const actual=streamedPackageFile(root,output+'/'+pin.path);
    need(actual.bytes===pin.bytes&&actual.sha256===pin.sha256,'Preview package member differs: '+pin.path);
  }
  for(const name of ['index.html','atlas-history.json.gz','typed-evidence.json','typed-evidence-manifest.json','environment-classifications.json'])
    streamedPackageFile(root,output+'/'+name);
  return {root,output,atlas};
}

function reusablePreviewSource(root) {
  const receipt=json(path.join(root,'.cache/package-input-build.json'));
  need(receipt.preflight?.passed===true&&['static','cloudflare'].includes(receipt.kind),'Successful canonical package build required');
  const head=receipt.preflight.inputs?.head;
  need(/^[a-f0-9]{40}$/.test(head??''),'Package input source identity missing');
  const definition=loadPackageInputs(root);
  need(receipt.input_definition_sha256===sha(fs.readFileSync(path.join(root,'.github/package-inputs.json'))),'Package input declaration changed');
  // Existing declared inputs cover data and code. A dirty source is not erased or
  // rejected: the normal builder handles it. Only unchanged input bytes are reused.
  const flags=git(root,['ls-files','-v','-z','--',...definition.inputs]).split('\0').filter(Boolean);
  need(!flags.some(row=>/[a-z]/.test(row[0])||row[0]==='S'&&fs.existsSync(path.join(root,row.slice(2)))),
    'Package input trust flags cannot establish unchanged preview bytes');
  need(git(root,['diff','--no-ext-diff','--no-textconv','--name-only',head,'--',...definition.inputs]).trim()===''&&
    git(root,['ls-files','--others','--',...definition.inputs]).trim()==='',
    'Package inputs changed since the canonical build');
}

export async function preparePreviewPackage(root=repository,{build}={}) {
  let reason;
  try{reusablePreviewSource(root);return inspectPreviewPackage(root);}catch(error){reason=error.message;}
  console.log('Preparing canonical standalone atlas for preview: '+reason);
  // One existing constructor, including its normal declared-input preparation,
  // prior-output preservation and failure behavior. No hidden second map master.
  const run=build??(await import('./scripts/package-build.mjs')).runPackageBuild;
  await run('static',{root});
  return inspectPreviewPackage(root);
}

export async function startPreview({root=repository,production=false,port=Number(process.env.PORT||3000),host='0.0.0.0',build}={}) {
  const prepared=await preparePreviewPackage(root,{build}),assets=path.join(prepared.root,prepared.output);
  const typedBytes=fs.readFileSync(path.join(assets,'typed-evidence.json')),typed=json(path.join(assets,'typed-evidence-manifest.json'));
  need(typed.bytes===typedBytes.length&&typed.sha256===sha(typedBytes),'Preview typed evidence identity differs');
  const typedPrepared=JSON.parse(typedBytes);
  const vite=production?null:await (await import('vite')).createServer({root:prepared.root,publicDir:false,
    define:{'import.meta.env.VITE_STATIC_ATLAS':JSON.stringify('true'),'import.meta.env.VITE_HOSTED_DATABASE':JSON.stringify('false')},
    server:{middlewareMode:true,host,hmr:process.env.ATLAS_TEST_MODE==='1'?false:undefined}});
  const mime={'.html':'text/html','.js':'text/javascript','.css':'text/css','.svg':'image/svg+xml','.png':'image/png','.json':'application/json','.gz':'application/gzip'};
  const server=http.createServer(async(req,res)=>{
    const url=new URL(req.url,'http://localhost');
    if(url.pathname.startsWith('/api/')){
      res.setHeader('Content-Type','application/json');res.setHeader('Cache-Control','no-store');
      if(req.method!=='GET'){res.writeHead(405);return res.end(JSON.stringify({error:'Method not allowed'}));}
      try{
        if(url.pathname==='/api/typed/v1/prepared-snapshot')return res.end(JSON.stringify(await resolveTypedSnapshot(typedPrepared,Number(url.searchParams.get('year')),{examples:url.searchParams.get('examples')==='1'})));
        if(url.pathname==='/api/classifications')return fs.createReadStream(path.join(assets,'environment-classifications.json')).pipe(res);
        // A local preview is not a connected Neon backend. Compiled hosted assets
        // retain their existing unavailable-content behavior rather than fake data.
        res.writeHead(404);return res.end(JSON.stringify({error:'No hosted content API in local package preview'}));
      }catch(error){res.writeHead(400);return res.end(JSON.stringify({error:error.message}));}
    }
    if(req.method!=='GET'&&req.method!=='HEAD'){res.writeHead(405);return res.end('Method not allowed');}
    let pathname;
    try{pathname=decodeURIComponent(url.pathname);}catch{res.writeHead(400);return res.end('Invalid path');}
    const file=path.resolve(assets,'.'+(pathname==='/'?'/index.html':pathname));
    if(!file.startsWith(assets+path.sep)){res.writeHead(404);return res.end('Not found');}
    // Source UI/HMR stays with Vite; all canonical data comes from the one package.
    if((production||pathname!=='/'&&!/\.(?:js|css|html)$/.test(pathname))&&fs.existsSync(file)&&fs.statSync(file).isFile()){
      if(!fs.realpathSync(file).startsWith(fs.realpathSync(assets)+path.sep)){res.writeHead(404);return res.end('Not found');}
      res.setHeader('Content-Type',mime[path.extname(file)]||'application/octet-stream');
      if(req.method==='HEAD')return res.end();return fs.createReadStream(file).pipe(res);
    }
    if(vite)return vite.middlewares(req,res);
    res.writeHead(404);res.end('Not found');
  });
  await new Promise((resolve,reject)=>{server.once('error',reject);server.listen(port,host,resolve);});
  return {server,vite,prepared,async close(){await vite?.close();await new Promise(resolve=>server.close(resolve));}};
}

if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
  const preview=await startPreview({production:process.argv.includes('--production')});
  console.log(`WorldAtlas listening on http://localhost:${preview.server.address().port}`);
  if(preview.prepared.output==='dist/client')console.log('Local package preview has no connected hosted content API');
  for(const signal of ['SIGTERM','SIGINT'])process.on(signal,async()=>{await preview.close();process.exit(0);});
}
