import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {validateEvidence, subjectsHash, sha256} from '../../../scripts/evidence-quality.mjs';

const folder=path.dirname(fileURLToPath(import.meta.url));
const baseline='24629e5918a144a1979db80ba7012baea42036e7';
const original='data/regional-review/bc-administrative-remainders-followup-2026/cd-assessments.json';
const registryPath=path.relative(process.cwd(),path.join(folder,'registry-from-pr678.geojson'));
const record=execFileSync('git',['show',`${baseline}:${original}`],{maxBuffer:32*1024*1024});
const registry=fs.readFileSync(registryPath);
const desc=(name,raw)=>({path:name,bytes:raw.length,sha256:sha256(raw),hash_kind:'file-bytes'});
const subjects=['5901','5933','5939','5941','5949','5951','5953','5955','5957','5959'].map(id=>'StatisticsCanada:2021:CD:'+id);
const manifest={version:1,issue:667,lane:'geography',worker_id:'compatibility-probe-not-a-worker-review',
  subject_ids:subjects,subject_ids_sha256:subjectsHash(subjects),
  baseline:{commit:baseline,files:[desc(original,record)],pins:{},subject_inventory:{version:1,basis:'prior-evidence',
    path:original,json_pointer:'/exact_subjects',id_prefix:'StatisticsCanada:2021:CD:',source_property:'CDUID',
    source_id:'statcan',registry_path:registryPath}},
  sources:[{id:'statcan',url:'https://www12.statcan.gc.ca/census-recensement/2021/geo/index-eng.cfm',
    role:'Census source named by prior audit; original source bytes not inspected in this identity probe',vintage:'2021',retrieved_at:'2026-10-03',
    license:{status:'unknown',terms:'This probe does not independently assess source reuse'},retention:'restoration-only',verification:'unverified',
    temporal_status:'reference',restoration:'Use original packet source acquisition receipts',limit:'Original source membership/geometry not independently checked in this probe'}],
  outputs:[desc(registryPath,registry)],methods:[{id:'compatibility',kind:'code',description:'Exact real prior roster versus new identity registry',software:'Node 24',units:'identities'}],
  metrics:[],summaries:[],conclusions:[],stages:{research:'partial',implementation:'not-proposed',geographic_approval:'unapproved'},
  commands:['node coordination/engineering/source-subject-extracts-713-20261003/verify-compatibility.mjs']};
const readFile=(name,vintage)=>{
  if(name===original&&vintage===baseline)return record;
  if(name===registryPath&&vintage==='candidate')return registry;
  throw Error('Unexpected source/candidate read');
};
const result=validateEvidence(manifest,{readFile,expectedSubjects:subjects});
assert.equal(result.status,'limited');
const mutations=[m=>m.baseline.subject_inventory.path=registryPath,m=>m.baseline.subject_inventory.id_prefix='invented:',
  m=>m.baseline.subject_inventory.basis='original-source',m=>m.baseline.subject_inventory.json_pointer='/unknown'];
for(const mutate of mutations){const m=structuredClone(manifest);mutate(m);assert.throws(()=>validateEvidence(m,{readFile}));}
console.log(JSON.stringify({version:1,method_id:'compatibility',kind:'positive-control',outcome:'passed',
  actual_subject_count:subjects.length,original:desc(original,record),baseline_commit:baseline,
  registry:desc(registryPath,registry),registry_origin:{pr:678,head:'baded97d71982436656b17de34d87172e2642cd7',path:'research/geography/bc-remainders-reproduction-followup/source-subject-registry.geojson'},
  negative_controls_rejected:mutations.length,result,
  limits:['Identity-only compatibility probe; not a full validation of PR678, original source extraction, geography, review or publication']},null,2));
