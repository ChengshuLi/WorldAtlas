import test from 'node:test';
import assert from 'node:assert/strict';
import {assertResearchImportsReady,assertResearchBundleApproved,readResearchImportGate} from '../scripts/research-import-gate.mjs';
import {transitionClaim} from '../scripts/issue-claim-contract.mjs';
const pins={release_id:'release:approved',hierarchy_sha256:'a'.repeat(64),footprints_sha256:'b'.repeat(64)},macroHash='c'.repeat(64);
const geography={id:pins.release_id,hierarchy_sha256:pins.hierarchy_sha256,footprints_sha256:pins.footprints_sha256};
const region=id=>({region_id:id,approval_issue:id==='region:a'?101:102,semantic_complete:true,approval_evidence:'Test-only certificate',macro_boundary_sha256:macroHash,approved_release:{...pins},approved_location_ids:[`${id}:location`],approved_subject_ids:[id,`${id}:province`,`${id}:location`]});
const gate=()=>({version:2,ready_for_location_attributes:true,macro_boundaries:{approved:true,approval_issue:100,approval_evidence:'Test-only macro certificate',boundary_sha256:macroHash},regions:[region('region:a'),region('region:b')]});
const opts=input=>({regionIds:['region:a'],input});
const record=(id='fact:a',location='region:a:location')=>({id,location_id:location,attribute:'population',value:10});

test('current manifest is closed and no region can claim invented approvals',()=>{
 assert.equal(readResearchImportGate().version,2);
 assert.throws(()=>assertResearchImportsReady(readResearchImportGate(),{regionIds:['region:a']}),/paused/);
});
test('v1 worldwide approval remains compatible',()=>{
 const legacy={version:1,ready_for_location_attributes:true,semantic_complete:true,approval_evidence:'test',approved_release:{...pins}};
 assert.deepEqual(assertResearchImportsReady(legacy),pins);
 assert.deepEqual(assertResearchBundleApproved(legacy,geography),pins);
});
test('regional content claims depend on macro and branch approval, not unfinished worldwide descendants',()=>{
 const spec={max_prs:1,depends_on:[],scope:'One sourced census batch',mode:'content',region_ids:['region:a'],geographic_release:pins.release_id,scope_manifest:'campaign/scope.json',territory_match_review:'Approved subject denominator'};
 const issue={number:200,state:'open',labels:['type:history-research','kind:work-item','status:ready'],body:`<!-- worldatlas-work:v1\n${JSON.stringify(spec)}\n-->`};
 const request={action:'claim',worker_id:'research-a',claim_id:'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',request_id:'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',branch:'research/census-a'};
 const dependencies=[{number:100,state:'closed'},{number:101,state:'closed'},{number:7,state:'open'}];
 assert.equal(transitionClaim({issue,comments:[],request,dependencies,geographyGate:gate()}).claim.mode,'content');
 for(const missing of [100,101])assert.throws(()=>transitionClaim({issue,comments:[],request,dependencies:dependencies.filter(d=>d.number!==missing),geographyGate:gate()}),/approval dependencies/);
 assert.throws(()=>transitionClaim({issue:{...issue,body:issue.body.replace('"region:a"','"region:b"')},comments:[],request,dependencies,geographyGate:gate()}),/approval dependencies/);
});
test('macro approval and explicit complete region certificates are required',()=>{
 assert.deepEqual(assertResearchImportsReady(gate(),{regionIds:['region:a']}),pins);
 assert.throws(()=>assertResearchImportsReady(gate()),/explicit bounded/);
 for(const change of [g=>g.macro_boundaries.approved=false,g=>g.macro_boundaries.boundary_sha256=null,g=>g.regions[0].semantic_complete=false,g=>g.regions[0].macro_boundary_sha256='d'.repeat(64),g=>g.regions[0].approval_evidence=null,g=>g.regions[0].approval_issue=null]){const candidate=gate();change(candidate);assert.throws(()=>assertResearchImportsReady(candidate,{regionIds:['region:a']}));}
 assert.throws(()=>assertResearchImportsReady(gate(),{regionIds:['missing']}),/not approved/);
});
test('pins and every location target are checked against explicitly selected regions',()=>{
 assertResearchBundleApproved(gate(),geography,opts({records:[record()]}));
 assert.throws(()=>assertResearchBundleApproved(gate(),{...geography,footprints_sha256:'d'.repeat(64)},opts({records:[record()]})),/does not match/);
 for(const location of ['region:b:location','unknown','region:a:province'])assert.throws(()=>assertResearchBundleApproved(gate(),geography,opts({records:[record('fact:a',location)]})),/outside/);
 assertResearchBundleApproved(gate(),geography,{regionIds:['region:a','region:b'],input:{records:[record(),record('fact:b','region:b:location')]}});
 const different=gate();different.regions[1].approved_release.release_id='other';assert.throws(()=>assertResearchBundleApproved(different,geography,{regionIds:['region:a','region:b'],input:{records:[record()]}}),/one exact/);
});
test('ambiguous territorial membership fails closed',()=>{
 const duplicate=gate();duplicate.regions[1].approved_subject_ids.push('region:a:location');assert.throws(()=>assertResearchImportsReady(duplicate,{regionIds:['region:a']}),/conflicting regional/);
});
test('all name, relationship and media targets are scoped; ancillary or geographic writes are refused',()=>{
 assertResearchBundleApproved(gate(),geography,opts({names:[{id:'name:a',entity_id:'region:a:location'}],relationships:[{id:'rel:a',source_entity_id:'region:a:location',target_entity_id:'region:a:province'}],media_links:[{id:'media:a',entity_id:'region:a:location'}]}));
 for(const input of [{names:[{entity_id:'region:b:location'}]},{relationships:[{source_entity_id:'region:a:location',target_entity_id:'region:b:location'}]},{media_links:[{entity_id:'unknown'}]},{entities:[{id:'person:new'}]},{entity_types:[{id:'person'}]},{categories:[{id:'owner:new'}]},{temporal_geography:{existence:[]}}])assert.throws(()=>assertResearchBundleApproved(gate(),geography,opts(input)));
});
test('verified raw batches are inspected rather than trusting caller target summaries',()=>{
 const options={regionIds:['region:a'],subjectIds:['region:a:location'],batches:[{raw:Buffer.from(JSON.stringify({records:[record('bad','region:b:location')]})),part:{}}]};
 assert.throws(()=>assertResearchBundleApproved(gate(),geography,options),/outside/);
 options.batches[0].raw=Buffer.from(JSON.stringify({records:[record()]}));assertResearchBundleApproved(gate(),geography,options);
 options.batches[0].part.endpoint='/api/geography/temporal/import';assert.throws(()=>assertResearchBundleApproved(gate(),geography,options),/memberships/);
 assert.throws(()=>assertResearchBundleApproved(gate(),geography,{regionIds:['region:a']}),/verified input/);
});
test('corrections require a territorial crosswalk and cannot transfer facts to another location',()=>{
 const correction={id:'withdraw:a',collection:'records',target_id:'old:a',replacement_id:'new:a'};
 assert.throws(()=>assertResearchBundleApproved(gate(),geography,opts({records:[record('new:a')],retirements:[correction]})),/lacks approved/);
 const approved=gate();approved.regions[0].approved_evidence_ids=[{collection:'records',id:'old:a',subject_ids:['region:a:location']},{collection:'records',id:'new:a',subject_ids:['region:a:location']}];
 assertResearchBundleApproved(approved,geography,opts({records:[record('new:a')],retirements:[correction]}));
 assert.throws(()=>assertResearchBundleApproved(approved,geography,{regionIds:['region:a','region:b'],input:{records:[record('new:a','region:b:location')],retirements:[correction]}}),/does not match its approved/);
 const transfer=gate();transfer.regions[0].approved_evidence_ids=[{collection:'records',id:'old:a',subject_ids:['region:a:location']}];transfer.regions[1].approved_evidence_ids=[{collection:'records',id:'new:a',subject_ids:['region:b:location']}];
 assert.throws(()=>assertResearchBundleApproved(transfer,geography,{regionIds:['region:a','region:b'],input:{records:[record('new:a','region:b:location')],retirements:[correction]}}),/cannot transfer/);
 assert.throws(()=>assertResearchBundleApproved(gate(),geography,opts({records:[record('old:a'),record('new:a')],retirements:[correction]})),/lacks approved/);
});
