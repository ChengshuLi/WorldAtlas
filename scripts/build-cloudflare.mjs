import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {isDeepStrictEqual} from 'node:util';
import {runPackageBuild} from './package-build.mjs';
import {snapshotPackageOutputSource,inventoryPackageOutput,packageBuildConfiguration,streamedPackageFile} from './package-output-artifact.mjs';
import {readGeographicReleaseManifest} from './read-geographic-release-manifest.mjs';
import {readCurrentSelectedAdditive} from './package-current-additive.mjs';
import {verifyLegacyPublicMap,verifyPublicRelease} from './publication-cloudflare.mjs';
import {scientificNativeSelection} from '../src/reference-metadata.js';
import {additiveBaseReference} from '../src/effective-footprint.js';
import {cloudflareConfig,bundleCloudflareWorker} from './build-cloudflare-inner.mjs';
export {cloudflareConfig};
const need=(ok,message)=>{if(!ok)throw Error(message);};
const hash=raw=>createHash('sha256').update(raw).digest('hex');
export const PUBLIC_PACKAGE_RECEIPT='.cache/cloudflare-publication.json';
// This is the existing public builder, not another deployment or ingestion API.
// The owner job synchronizes first; this boundary refuses before an expensive
// build if its exact source-selected content pair is unavailable or different.
export async function preparePublicCloudflarePackage({root=process.cwd(),receiptFile='data/validation/neon-forward-migrations/receipt.json',fetchImpl=fetch,env=process.env,build=()=>runPackageBuild('cloudflare',{root})}={}){
 root=fs.realpathSync(root);const read=file=>fs.readFileSync(path.join(root,file)),json=file=>JSON.parse(read(file));
 const sourceHead=execFileSync('git',['-C',root,'rev-parse','HEAD'],{encoding:'utf8'}).trim();
 const receipt=json(receiptFile),operation=read('.github/operations/neon-geographic-production.json');
 need(receipt.status==='verified'&&receipt.mode==='geography-production'&&receipt.github?.head_sha===sourceHead&&receipt.operation_sha256===hash(operation)&&receipt.geography?.status==='published','Exact successful source-bound geographic operation required before public build');
 const release=readGeographicReleaseManifest(path.join(root,'data/geographic-releases')).releases.at(-1);
 need(isDeepStrictEqual(receipt.geography.target,release),'Geographic operation and current build select different content');
 const selection=json('data/ownership-selection.json'),native=scientificNativeSelection(selection),raw=read(native.manifest_path);
 need(hash(raw)===native.sha256,'Selected native manifest changed before public build');
 const selected=await readCurrentSelectedAdditive({root,selectedGrid:{manifest:JSON.parse(raw),sha256:hash(raw)},geographicRelease:release});
 need(selected,'An exact source-selected map/content pair is required');
 await verifyLegacyPublicMap({prior:receipt.geography.prior,fetchImpl});await verifyPublicRelease({release,fetchImpl});
 const configuration=packageBuildConfiguration(env);need(configuration.ATLAS_PUBLIC_READ_ONLY==='1','Public package must retain read-only access');
 const {producer,...source}=snapshotPackageOutputSource(root);
 const retained=path.join(root,PUBLIC_PACKAGE_RECEIPT);
 if(fs.existsSync(retained)){
  const prior=json(PUBLIC_PACKAGE_RECEIPT);
  need(prior.version===1&&prior.kind==='coordinated-public-cloudflare-package'&&isDeepStrictEqual(prior.source,source)&&prior.operation_sha256===receipt.operation_sha256&&isDeepStrictEqual(prior.release,release)&&isDeepStrictEqual(prior.configuration,configuration),'Retained public package belongs to a different source/release/configuration');
  need(isDeepStrictEqual(prior.output,inventoryPackageOutput(root)),'Retained public package output changed');
  need(isDeepStrictEqual(prior.build_receipt,streamedPackageFile(root,'.cache/package-input-build.json')),'Retained public package build receipt changed');
  return {reused:true,receipt:prior};
 }
 await build();
 const completed=json('.cache/package-input-build.json');
 need(completed.version===1&&completed.kind==='cloudflare'&&completed.preflight?.passed===true&&completed.preflight.errors.length===0&&completed.preflight.inputs.head===sourceHead&&!completed.assembly&&completed.input_definition_sha256===source.input_definition_sha256,'Actual successful fresh full build required');
 const atlas=json('dist/client/atlas-geography.json'),config=json('dist/cloudflare/wrangler.json');
 need(isDeepStrictEqual(additiveBaseReference(atlas),Object.fromEntries(['id','hierarchy_sha256','footprints_sha256'].map(key=>[key,release[key]]))),'Emitted map and verified content pair differ');
 need(config.name==='worldatlas-explorer'&&config.vars?.ATLAS_PUBLIC_READ_ONLY==='1'&&config.vars.ATLAS_READ_ONLY==='1'&&config.vars.ATLAS_CONTENT_BACKEND==='postgres','Emitted public configuration differs');
 const value={version:1,kind:'coordinated-public-cloudflare-package',source,release,operation_sha256:receipt.operation_sha256,configuration,
  execution:{repository:env.GITHUB_REPOSITORY??null,workflow_ref:env.GITHUB_WORKFLOW_REF??null,run_id:env.GITHUB_RUN_ID??null,run_attempt:env.GITHUB_RUN_ATTEMPT??null},
  output:inventoryPackageOutput(root),build_receipt:streamedPackageFile(root,'.cache/package-input-build.json'),
  semantics:'Actual public full build after exact geographic synchronization. Retained output reuse is not another build or a stock integration artifact.'};
 fs.mkdirSync(path.dirname(retained),{recursive:true});fs.writeFileSync(retained,JSON.stringify(value,null,2)+'\n',{flag:'wx'});
 return {reused:false,receipt:value};
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 if(process.argv.includes('--legacy-worker')){const root=process.cwd(),output=path.join(root,'.cache/cloudflare-legacy');await bundleCloudflareWorker(root,output);fs.writeFileSync(path.join(output,'wrangler.json'),JSON.stringify(cloudflareConfig({preserveAssets:true}),null,2)+'\n');}
 else if(process.argv.includes('--publication'))console.log(JSON.stringify(await preparePublicCloudflarePackage()));
 else await runPackageBuild('cloudflare');
}
