import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {ImmutableReader,NativeAssetImage} from './stock/scripts/check-effective-geographic-regression.mjs';
import {unshuffleOwnershipBytes} from './stock/src/ownership-codec.js';
import {applyNativeAdditiveRows} from './stock/scripts/selected-checkpoint-native.mjs';
const root='.cache/worker3-mmr3483-opportunity-001/current-owner28/';
const sha=b=>createHash('sha256').update(b).digest('hex');
const require=(v,m)=>{if(!v)throw Error(m);};
const selection=JSON.parse(fs.readFileSync(root+'../current-ownership-selection.json'));
const sideBytes=fs.readFileSync(root+'ownership-selection-v2.json');require(sha(sideBytes)===selection.additive_release.sha256&&sideBytes.length===selection.additive_release.bytes,'Current selected sidecar');
const side=JSON.parse(sideBytes),manifestBytes=fs.readFileSync(root+'manifest.json');require(sha(manifestBytes)===selection.sha256,'Current manifest pin');
const manifest=JSON.parse(manifestBytes),reader=new ImmutableReader('/Users/chengshuli/world-atlas-workspace/WorldAtlas','73852925a517d7c07c6475d6ce2281f9481ad705');
// Current manifest pins the complete exact byte bank; historical aliases must
// match those pins. This is a data lookup, not a manufactured checkpoint state.
const image=new NativeAssetImage(reader,manifest,selection.manifest_path);
const readPin=pin=>{const d=reader.descriptor(pin.path,pin.commit);require(d.mode===pin.mode&&d.bytes===pin.bytes&&d.git_blob_oid===pin.git_blob_oid,'Whole current selected role differs');const b=reader.read(pin.path,{version:pin.commit,expected:pin.sha256});if(pin.decoded_bytes!==undefined){const r=gunzipSync(b,{maxOutputLength:pin.decoded_bytes});require(r.length===pin.decoded_bytes&&sha(r)===pin.decoded_sha256,'Decoded selected role differs');return r;}return b;};
const patch=JSON.parse(readPin(side.logical_asset_map.patch));
const owners=JSON.parse(readPin(side.logical_asset_map.owner_roster));
require(owners.length===49625&&owners.every((o,i)=>o.index===i+1),'Complete original owner roster');
const asset=pin=>{const name=path.posix.join(path.posix.dirname(selection.manifest_path),pin.path);let body;
 if(reader.git('ls-tree','-z',reader.version,'--',name).length)body=reader.read(name,{expected:pin.sha256});else body=image.logical(name,pin);
 require(body.length===pin.bytes&&sha(body)===pin.sha256,'Native encoded member differs');const raw=gunzipSync(body,{maxOutputLength:pin.decoded_bytes});require(raw.length===pin.decoded_bytes,'Native decoded member length');const words=unshuffleOwnershipBytes(raw,pin.words),canonical=Buffer.alloc(words.length*4);for(let i=0;i<words.length;i++)canonical.writeUInt32LE(words[i],i*4);require(sha(canonical)===pin.decoded_sha256,'Native canonical words differ');return words;};
const tablePin=manifest.parts.filter(p=>p.kind==='rows');require(tablePin.length===1,'Whole row table');const table=asset(tablePin[0]);require(table.length===manifest.size*2,'Native row table size');let count=0;for(let y=0;y<manifest.size;y++){require(table[y*2]===count,'Complete native row partition');count+=table[y*2+1];}require(count*2===manifest.runWords,'Native complete run scope');
const scope=JSON.parse(fs.readFileSync(root+'../conflict28-source-choice-final.json'));const ys=[...new Set(scope.records.map(r=>r.y))].sort((a,b)=>a-b),bodies=new Map(),baseRows=[];
for(const y of ys){const start=table[y*2]*2,end=start+table[y*2+1]*2,runs=[];
 for(const pin of manifest.parts.filter(p=>p.kind==='runs'&&start<p.offset+p.words&&p.offset<end)){if(!bodies.has(pin.path))bodies.set(pin.path,asset(pin));const words=bodies.get(pin.path);for(let i=Math.max(start,pin.offset);i<Math.min(end,pin.offset+pin.words);i+=2){const a=words[i-pin.offset],b=words[i-pin.offset+1],bits=manifest.coordinateBits,mask=2**bits-1;runs.push([a&mask,(b&mask)+1,(a>>>bits)+(b>>>bits)*2**(32-bits)]);}}
 require(runs.length===table[y*2+1],'Complete containing row');baseRows.push({y,runs});}
const effective=applyNativeAdditiveRows(baseRows,patch,{size:manifest.size,owners});
const lookup=(rows,y,x)=>{const hit=rows.find(r=>r.y===y).runs.filter(r=>r[0]<=x&&x<r[1]);require(hit.length<=1,'Multiple effective owners');return hit[0]?.[2]??0;};
const records=scope.records.map(r=>{const base=lookup(baseRows,r.y,r.x),owner=lookup(effective,r.y,r.x);return {...r,actual_base_owner:base,actual_effective_owner:owner,actual_effective_location:owner?{index:owner,id:owners[owner-1].id,name:owners[owner-1].name}:null};});
const result={kind:'original-conflict28-current-selected-effective-owner-observation',current_accepted_commit:scope.current_accepted_commit,current_selection_sha256:sha(fs.readFileSync(root+'../current-ownership-selection.json')),current_sidecar_sha256:sha(sideBytes),current_manifest_sha256:sha(manifestBytes),patch:side.logical_asset_map.patch,owner_roster:side.logical_asset_map.owner_roster,base_transport_alias:reader.version,base_transport_index:manifest.native_asset_transport.index,base_logical_run_parts:[...bodies.keys()],whole_consumed_inputs:[...reader.inventory.values()].filter(r=>r.whole_body_consumed),base_rows:baseRows,effective_rows:effective,records,limits:['Existing complete native byte-bank transport/codec and additive-row consumer used. No geometry predicates or full-world raster replay.','This is an actual current selected-data owner lookup, not a qualified checkpoint capability or repair acceptance.','Any nonzero owner must be preserved. Source-choice answers do not themselves assign these cells.']};
fs.writeFileSync(root+'effective-owner28.json',JSON.stringify(result)+'\n',{flag:'wx'});
console.log(JSON.stringify({coordinates:records.length,complete_rows:ys.length,whole_run_parts:bodies.size,owner_zero:records.filter(r=>r.actual_effective_owner===0).length,owner_nonzero:records.filter(r=>r.actual_effective_owner!==0).length,observed_rss_bytes:process.memoryUsage().rss,output_sha256:sha(fs.readFileSync(root+'effective-owner28.json'))}));
