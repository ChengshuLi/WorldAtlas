// Metadata serialization only. Preserve exact original JS canonical row bytes.
import fs from 'node:fs';
import crypto from 'node:crypto';
const Q='coordination/engineering/global-gap-candidate-refresh-20261009/inputs/';
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const canonical=v=>Array.isArray(v)?v.map(canonical):v&&typeof v==='object'?Object.fromEntries(Object.keys(v).sort().map(k=>[k,canonical(v[k])])):v;
const pins=JSON.parse(fs.readFileSync(Q+'pins.json'));
const files=[...new Set(pins.filter(p=>p.original_bindings?.some(v=>v.path.endsWith('source-fit-seven-cases.json')||v.path.endsWith('/measurement.json'))).map(p=>p.path))];
const bytes=fs.statSync(process.execPath).size+fs.statSync(new URL(import.meta.url)).size+fs.statSync(Q+'pins.json').size+files.reduce((n,p)=>n+fs.statSync(p).size,0)+8*1024*1024;
if(bytes>268435456||files.some(p=>fs.statSync(p).size>33554432))throw Error('Complete canonical custody preparation cap');
const out=[];
for(const path of files){const pin=pins.find(p=>p.path===path),raw=fs.readFileSync(path);if(sha(raw)!==pin.sha256)throw Error('Whole source custody drift');const source=JSON.parse(raw),rows=source.results??source.cases;
 for(let ordinal=0;ordinal<rows.length;ordinal++){const body=Buffer.from(JSON.stringify(canonical(rows[ordinal]))+'\n');const digest=sha(body),destination=Q+'case-'+digest+'.json';if(fs.existsSync(destination)){if(!fs.readFileSync(destination).equals(body))throw Error('Custody collision');}else fs.writeFileSync(destination,body,{flag:'wx'});out.push({path:destination,bytes:body.length,sha256:digest,case_source_sha256:pin.sha256,ordinal});}}
fs.writeFileSync(Q+'canonical-case-pins.json',JSON.stringify(out,null,2)+'\n');
console.log(JSON.stringify({metadata_only:true,complete_prospective_bytes:bytes,whole_case_count:out.length,source_file_count:files.length}));
