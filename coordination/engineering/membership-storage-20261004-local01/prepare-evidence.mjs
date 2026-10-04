import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {execFileSync} from 'node:child_process';

const root=process.cwd(),owned='coordination/engineering/membership-storage-20261004-local01';
const base='f72394a1194d0e0100cf08b7232da3d5be5a63bc',hash=bytes=>createHash('sha256').update(bytes).digest('hex');
const manifestPath=owned+'/evidence-quality.json';
const result=JSON.parse(fs.readFileSync(owned+'/result.json'));
const descriptor=(name,baseline=false)=>{
  const raw=baseline?execFileSync('git',['show',base+':'+name]):fs.readFileSync(name);
  const value={path:name,bytes:raw.length,sha256:hash(raw),hash_kind:'file-bytes'};
  if(name.endsWith('.gz')){const expanded=gunzipSync(raw);value.uncompressed_bytes=expanded.length;value.uncompressed_sha256=hash(expanded);}
  return value;
};
const input=JSON.parse(fs.readFileSync(owned+'/inputs.json'));
const baselineNames=['postgres/schema.sql','scripts/read-geographic-release-manifest.mjs','hosted/geographic-releases.js','package-lock.json',
  ...input.chain.map(x=>'data/geographic-releases/'+x.path),...input.predecessors.map(x=>'data/geographic-releases/'+x.path),
  ...input.source_pins.map(x=>'data/geographic-releases/'+x.path)];
const baselineFiles=[...new Set(baselineNames)].map(name=>({...descriptor(name,true),role:'original-source'}));
const walk=directory=>fs.readdirSync(directory).flatMap(name=>{const file=path.join(directory,name);return fs.statSync(file).isDirectory()?walk(file):[file];});
const outputs=walk(owned).filter(name=>name!==manifestPath).concat(['scripts/benchmark-membership-storage.mjs','test/membership-storage-benchmark.test.mjs']).map(name=>descriptor(name));
const metrics=[],bindings=[];
const collect=(value,parts,file,vintage='baseline',evaluation=base)=>{
  if(typeof value==='number'){
    const pointer='/'+parts.map(key=>String(key).replaceAll('~','~0').replaceAll('/','~1')).join('/');
    const id=file.slice(owned.length+1).replaceAll('.','-')+'-'+parts.join('-');
    const unit=pointer.includes('bytes')?'bytes':pointer.includes('_ms')?'milliseconds':pointer.includes('usd')?'USD':pointer.includes('cu_hours')?'CU-hours':'count';
    metrics.push({id,value,unit,vintage,evaluation_commit:evaluation,input_sha256:outputs.find(x=>x.path===file).sha256});
    bindings.push({metric_id:id,path:file,json_pointer:pointer});
  }else if(value&&typeof value==='object')for(const [key,item] of Object.entries(value))collect(item,[...parts,key],file,vintage,evaluation);
};
for(const name of ['result.json','alternatives.json','positive-control.json','negative-control.json'])
  collect(JSON.parse(fs.readFileSync(owned+'/'+name)),[],owned+'/'+name);
const production=JSON.parse(fs.readFileSync(owned+'/production-measurement.json'));
collect(production,[],owned+'/production-measurement.json','archived',production.source_commit);
const manifest={version:1,issue:754,lane:'engineering',worker_id:'engineering-membership-storage-20261004-local01',
  subject_ids:[],subject_ids_sha256:hash('[]'),baseline:{commit:base,files:baselineFiles,pins:{},pin_files:{}},
  sources:[{id:'prepared-membership-snapshots',url:'https://github.com/ChengshuLi/WorldAtlas/tree/'+base+'/data/geographic-releases',
    role:'Immutable prepared rows, canonical evidence, source IDs and extension manifests',vintage:base,retrieved_at:'2026-10-04',
    license:{status:'unknown',terms:'Original source-specific licenses remain in source catalogs; no new original source redistribution.'},
    retention:'restoration-only',verification:'verified',temporal_status:'reference',
    restoration:'Restore the exact Git commit and every whole-file-pinned batch in inputs.json; run the original manifest decoder and final benchmark.',
    limit:'Prepared snapshots include staged geography, are not a private production export/backup and do not independently certify scientific source archives or regional approval.'},
    {id:'provider-pricing',url:'https://neon.com/pricing',role:'Dated published rates and alternative-provider links retained in alternatives.json',
      vintage:'2026-10-04',retrieved_at:'2026-10-04',license:{status:'unknown',terms:'Published numerical prices and allowances; no full source article redistributed.'},
      retention:'restoration-only',verification:'verified',temporal_status:'reference',restoration:'Consult each direct official URL in alternatives.json; prices may change after inspection.',
      limit:'Public rates are not account-plan, measured consumption, billing or provider-activation proof; alternative SQL engines need separately verified migration/connection compatibility.'}],
  outputs,methods:[{id:'storage-measurement',kind:'measurement',description:'Independent disk-backed PostgreSQL/PGlite targets with original membership DDL versus compact keys and exact-byte evidence dictionary; all relation/index/TOAST overhead, release/raw-row hashes and bounded query probes.',
    software:'Node 24.19.0, locked PGlite '+result.environment.pglite_version+', PostgreSQL version/settings retained in result.json',units:'bytes, rows, milliseconds'}],
  metrics,metric_bindings:bindings,summaries:[],conclusions:[{text:'Lossless normalization materially reduces the measured local membership subsystem and justifies a separately reviewed compatible forward migration; production capacity/recovery and served acceptance remain unverified.',status:'supported',source_ids:['prepared-membership-snapshots']}],
  stages:{research:'complete',implementation:'implemented',geographic_approval:'not-requested'},
  validation:['positive-control','negative-control'].map(kind=>({method_id:'storage-measurement',kind,outcome:'passed',evidence_path:owned+'/'+kind+'.json'})),
  change_receipts:outputs.map(file=>({path:file.path,status:'added'})).concat([{path:manifestPath,status:'added'}]),
  commands:['node scripts/benchmark-membership-storage.mjs data/geographic-releases /absolute/new-output /absolute/new-isolated-target',
    'node --test test/membership-storage-benchmark.test.mjs test/postgres-contract.test.mjs test/postgres-adapter.test.mjs test/geographic-releases.test.mjs',
    'node '+owned+'/prepare-evidence.mjs','node scripts/evidence-quality.mjs '+manifestPath]};
fs.writeFileSync(manifestPath,JSON.stringify(manifest,null,2)+'\n');
console.log(JSON.stringify({files:outputs.length,metrics:metrics.length,baseline:baselineFiles.length,root}));
