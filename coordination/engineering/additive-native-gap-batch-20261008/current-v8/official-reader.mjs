import fs from 'node:fs';
import zlib from 'node:zlib';
import assert from 'node:assert/strict';
import {unshuffleOwnershipBytes} from './ownership-codec.js';
import {ownershipRun} from './pixel-ownership.js';
const receipt=JSON.parse(fs.readFileSync(new URL('receipt.json',import.meta.url)));
const rows=JSON.parse(fs.readFileSync(new URL('complete-owner-rows.json',import.meta.url)));
const assets=receipt.whole_assets.map(a=>{const d=a.manifest_descriptor;return {d,words:unshuffleOwnershipBytes(zlib.gunzipSync(fs.readFileSync(new URL(d.path.split('/').at(-1),import.meta.url))),d.words)};});
const table=assets.find(a=>a.d.kind==='rows').words;
let count=0;
for(const row of rows){assert.equal(table[row.y*2],row.first_run);assert.equal(table[row.y*2+1],row.run_count);
 for(let j=0;j<row.run_count;j++){const word=(row.first_run+j)*2;const a=assets.find(a=>a.d.kind==='runs'&&a.d.offset<=word&&word+1<a.d.offset+a.d.words);assert(a);const v=ownershipRun({version:2,coordinateBits:19,runs:a.words},(word-a.d.offset)/2);assert.deepEqual([v.start,v.end,v.id],row.complete_owner_intervals[j]);count++;}}
for(const c of receipt.candidate_cells){const row=rows.find(r=>r.y===c.y);assert(!row.complete_owner_intervals.some(([s,e])=>s<=c.start&&c.start<e));}
fs.writeFileSync(new URL('official-reader-receipt.json',import.meta.url),JSON.stringify({complete_rows:rows.length,complete_runs:count,official_whole_module_readers_agree:true,candidate_windows:receipt.windows.length,no_candidate_assignments:true,scientific_recalculation:false})+'\n');
console.log(JSON.stringify({complete_rows:rows.length,complete_runs:count,official_readers_agree:true}));
