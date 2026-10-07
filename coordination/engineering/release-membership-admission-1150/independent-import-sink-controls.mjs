import assert from 'node:assert/strict';import {spawnSync} from 'node:child_process';
const root=process.argv[2],catchEntry='let result;try{result=await db.batch(statements);}catch(e){';
const cases=[
 ['omitted-ingestion-intent','await db.batch(statements)','await db.batch(statements.slice(0,-1))',/Invalid field-admission write intent/],
 ['forged-intent-token','await db.batch(statements)','await db.batch(statements.map(()=>({})))',/Invalid field-admission write intent/],
 ['swallowed-refusal-success',catchEntry,catchEntry+'return {duplicate:true};',/unexpectedly returned without refusing a commit/],
 ['wrong-read-bind-shape',"db.prepare('SELECT * FROM atlas_ingestions WHERE id=?').bind(id)","db.prepare('SELECT * FROM atlas_ingestions WHERE id=?').bind(Number(id))",/Invalid field-admission read shape/],
 ['retryable-marker-status',catchEntry,catchEntry+'e.retryable=true;',/Import rejected: Field admission refuses commit/],
 ['unknown-commit-outcome',catchEntry,catchEntry+"e.commit_status='unknown';",/Import outcome is unknown/],
];
for(const[name,from,to,reason]of cases){
const script=`import{registerHooks}from'node:module';import assert from'node:assert/strict';import{createHash}from'node:crypto';const[from,to,pattern]=JSON.parse(process.argv[1]);let changed=false;registerHooks({load(url,context,next){const result=next(url,context);if(url.endsWith('/hosted/records.js')){const source=String(result.source);assert.ok(source.includes(from));changed=true;return{...result,source:source.replace(from,to)};}return result;}});const{admitGeographicReleaseBatches}=await import('./scripts/geographic-release-admission.mjs');const bytes=Buffer.from(JSON.stringify({sources:[{id:'fixture',name:'Fixture',license:'CC0',vintage:'2026',status:'reference',supported_from:2026,supported_to:2027}]}));await assert.rejects(admitGeographicReleaseBatches([{path:'sources.json',route:'/api/records/import',sha256:createHash('sha256').update(bytes).digest('hex')}],{readBatch:()=>bytes}),new RegExp(pattern));assert.equal(changed,true);`;
const r=spawnSync(process.execPath,['--input-type=module','-e',script,JSON.stringify([from,to,reason.source])],{cwd:root,env:{PATH:'/usr/bin:/bin',GIT_NO_LAZY_FETCH:'1'},encoding:'utf8'});assert.equal(r.status,0,r.stderr);console.log(JSON.stringify({name,rejected:true}));
}
