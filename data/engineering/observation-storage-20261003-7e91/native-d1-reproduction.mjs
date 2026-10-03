import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {Miniflare,convertV4MiniflareOptions} from 'miniflare';
import {storageCatalogV3,exportStorageMarkerV3} from '../../../hosted/storage-export-v3.js';
const root=path.resolve(import.meta.dirname,'../../..'),output=process.argv[2];
if(!output||process.argv.length!==3||fs.existsSync(output))throw Error('Provide one fresh output JSON path');
// Explicit statements avoid D1 exec transport splitting SQL trigger bodies.
function split(sql){const re=/'(?:''|[^'])*'|"(?:""|[^"])*"|`[^`]*`|--[^\n]*|\/\*[\s\S]*?\*\/|\bBEGIN\b|\bEND\b|;/gi;let depth=0,start=0;const parts=[];for(const match of sql.matchAll(re)){const token=match[0].toUpperCase();if(token==='BEGIN')depth++;if(token==='END')depth=Math.max(0,depth-1);if(token===';'&&depth===0){parts.push(sql.slice(start,match.index+1));start=match.index+1;}}if(sql.slice(start).trim())parts.push(sql.slice(start));return parts.filter(v=>v.replace(/--[^\n]*/g,'').trim());}
const mf=new Miniflare(convertV4MiniflareOptions({name:'typed-storage-isolated-proof',modules:true,script:'export default {fetch(){return new Response("synthetic verification")}}',compatibilityDate:'2026-10-01',d1Databases:{DB:'00000000-0000-0000-0000-000000000529'}}));
try {
 const db=await mf.getD1Database('DB');
 const migrations=fs.readdirSync(path.join(root,'drizzle')).filter(file=>file.endsWith('.sql')).sort();
 for(const file of migrations){const sql=fs.readFileSync(path.join(root,'drizzle',file),'utf8');const statements=sql.includes('--> statement-breakpoint')?sql.split('--> statement-breakpoint').map(v=>v.trim()).filter(v=>v.replace(/--[^\n]*/g,'').trim()):split(sql);console.log(JSON.stringify({migration:file,statements:statements.length}));for(const statement of statements)await db.prepare(statement).run();}
 const catalog=await storageCatalogV3(db),marker=await exportStorageMarkerV3(db);
 assert.equal(Object.keys(marker.counts).length,26);
 await db.prepare("DROP TRIGGER atlas_typed_retirements_collision").run();
 await assert.rejects(exportStorageMarkerV3(db),/schema|guards/);
 const receipt={version:1,scope:'Actual local workerd D1 applying every raw source migration through explicit statement transport; no deployed database/provider operation or geographic approval.',migrations:migrations.length,tables:26,catalog_sha256:createHash('sha256').update(JSON.stringify(catalog)).digest('hex'),empty_marker_verified:true,missing_guard_rejected:true,source_sql_rewritten:false};
 fs.writeFileSync(output,JSON.stringify(receipt,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify(receipt));
}finally{await mf.dispose();}
