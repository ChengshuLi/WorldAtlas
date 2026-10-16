import fs from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
import {createServer} from 'vite';
import {pickOwnership} from '../../../../src/pixel-ownership.js';
const root=path.resolve('dist/client'),oldFetch=globalThis.fetch,reads=new Set();
const server=await createServer({configFile:false,server:{middlewareMode:true},define:{'import.meta.env.VITE_STATIC_ATLAS':'"true"','import.meta.env.VITE_HOSTED_DATABASE':'"false"'}});
try{
 globalThis.fetch=async name=>{assert.equal(typeof name,'string');const relative=name.replace(/^\.\//,'');const file=path.resolve(root,relative);assert.ok(file.startsWith(root+'/'));reads.add(relative);const bytes=await fs.readFile(file);return new Response(bytes,{headers:{'Content-Length':String(bytes.length)}});};
 const client=await server.ssrLoadModule('/src/data-client.js'),loaded=await client.loadGeography();
 const cathai=loaded.features.find(f=>f.id==='gb:VNM:ADM2:81297802B5756602808944');
 assert.equal(cathai.properties.parent_id,'framework:province:hai-phong:9b1802d93923');
 assert.equal(cathai.properties.metadata.reference_revision,'6778719a9c50889f317919fcf57eab07f3240892118ad135d1e8f9ae5df5b6b5');
 assert.ok(reads.has('reference-metadata/current.json'));
 assert.equal(pickOwnership(loaded.ownership,202763,122215),30271);
 assert.equal(pickOwnership(loaded.ownership,202763,122216),30271);
 const report={passed:true,entry:'src/data-client.js loadGeography via Vite SSR using actual emitted assets',feature_count:loaded.features.length,asset_reads:reads.size,metadata_read:reads.has('reference-metadata/current.json'),cathai_parent:cathai.properties.parent_id,application_reference_revision:cathai.properties.metadata.reference_revision,kyunsu_two_picks:2,limits:'Actual browser module and emitted assets in Node/Vite SSR; GPU/Canvas rendering and deployed HTTP delivery are not exercised.'};
 await fs.writeFile('.followups/runtime-revision-emitted-browser-entry.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));
}finally{globalThis.fetch=oldFetch;await server.close();}
