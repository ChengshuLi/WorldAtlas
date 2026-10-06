import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';

const here=path.dirname(new URL(import.meta.url).pathname);
const repo=path.resolve(here,'../../..');
const parent=path.join(repo,'data/regional-review/regional-review-1aa97b490604ea4e');
const snapshotFile=path.join(here,'github-issue-snapshots.json');
const outDir=path.resolve(process.argv[2]??path.join(here,'output'));
const sha=b=>createHash('sha256').update(b).digest('hex');
const readJson=f=>JSON.parse(fs.readFileSync(f,'utf8'));
const fail=(condition,message)=>{if(!condition)throw Error(message)};
const sorted=a=>[...a].sort();
const equal=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
const unique=a=>Array.isArray(a)&&new Set(a).size===a.length;
const expectedIssueIds=[910,911,912,913];
const expectedChildTitles={
  910:'Resolve Fiji province source vintage and Lau/Rotuma evidence',
  911:'Restore valid official New Caledonia province boundary evidence',
  912:'Reconcile Vanuatu province boundary evidence and island coverage',
  913:'Verify Temotu province and Santa Cruz Islands parent scope'
};
const idsByChild=id=>id.startsWith('gb:FJI:')?910:id.startsWith('NCL-')?911:
  id.startsWith('gb:VUT:')?912:id.startsWith('gb:SLB:')?913:null;
function exactScopeFromBody(issue){
  const heading='Machine-readable exact workload scope';
  const start=issue.body.indexOf(heading);
  fail(start>=0,`#${issue.number} has no exact workload heading`);
  const match=issue.body.slice(start).match(/```json\s*\n([\s\S]*?)\n```/);
  fail(Boolean(match),`#${issue.number} has no workload JSON`);
  return JSON.parse(match[1]);
}
function machineContract(issue){
  const match=issue.body.match(/<!-- worldatlas-work:v1\s*\n([\s\S]*?)\n-->/);
  fail(Boolean(match),`#${issue.number} has no machine contract`);
  return JSON.parse(match[1]);
}
function expectedRoster(scope){
  const ids=scope.member_location_ids;
  fail(Array.isArray(ids)&&ids.length===25&&unique(ids), 'Parent scope must contain exactly 25 unique IDs');
  fail(scope.location_count===25, 'Parent declared count must equal 25');
  fail(sha(Buffer.from(ids.join('\n')))===scope.member_location_ids_sha256,'Parent ID digest mismatch');
  return ids;
}
function validateParentScope(scope,baselineScope,liveIssue){
  const expected=expectedRoster(baselineScope), live=exactScopeFromBody(liveIssue);
  const liveIds=expectedRoster(live);
  fail(equal(sorted(scope.member_location_ids??[]),sorted(expected))&&scope.member_location_ids.length===25,
    'Candidate subject roster is not the exact immutable ancestor roster');
  fail(equal(sorted(liveIds),sorted(expected)),'Live #454 issue contract differs from immutable ancestor roster');
  fail(scope.location_count===25,'Candidate declared count differs from exact roster');
  fail(scope.member_location_ids_sha256===baselineScope.member_location_ids_sha256,
    'Candidate declared digest differs from exact roster digest');
  return {expected,live};
}
function validateChildren(saved,archivedContracts,liveIssues,roster){
  const numbers=saved.followups.map(x=>x.number);
  fail(equal(sorted(numbers),sorted(expectedIssueIds))&&numbers.length===4&&unique(numbers),
    'Saved child inventory must contain exactly four distinct expected issue numbers');
  const archived=archivedContracts.followups.map(x=>x.issue);
  fail(equal(sorted(archived),sorted(expectedIssueIds))&&archived.length===4&&unique(archived),
    'Archived child contracts must contain exactly #910–#913 once each');
  fail(liveIssues.length===4&&unique(liveIssues.map(x=>x.number))&&
    equal(sorted(liveIssues.map(x=>x.number)),sorted(expectedIssueIds)),
    'Live child snapshots must contain exactly #910–#913 once each');
  const parentSet=new Set(roster),all=[],rows=[];
  for(const number of expectedIssueIds){
    const issue=liveIssues.find(x=>x.number===number),savedIssue=saved.followups.find(x=>x.number===number);
    const old=archivedContracts.followups.find(x=>x.issue===number);
    fail(issue.title===expectedChildTitles[number]&&savedIssue.title===issue.title&&old.title===issue.title,
      `Child #${number} identity/title mismatch`);
    const ids=machineContract(issue).evidence_quality?.subject_ids;
    fail(Array.isArray(ids)&&ids.length>0&&unique(ids),`#${number} contract needs unique exact subjects`);
    const savedIds=machineContract(savedIssue).evidence_quality?.subject_ids;
    fail(Array.isArray(savedIds)&&unique(savedIds)&&equal(sorted(ids),sorted(savedIds)),
      `Saved #${number} issue snapshot subject roster differs from live contract`);
    fail(old.subject_count===ids.length&&old.status==='blocked on parent',
      `Archived #${number} contract does not preserve its original count/status`);
    for(const id of ids){
      fail(parentSet.has(id),`#${number} contains out-of-parent subject ${id}`);
      fail(idsByChild(id)===number,`#${number} contains a subject assigned to another child: ${id}`);
      all.push(id);
    }
    rows.push({issue:number,title:issue.title,archived_status:old.status,
      current_state:issue.state,current_status_labels:issue.labels.filter(x=>x.startsWith('status:')),
      subject_count:ids.length,subject_ids:ids});
  }
  fail(unique(all)&&all.length===roster.length&&equal(sorted(all),sorted(roster)),
    'Child subject sets must form a complete disjoint union of the 25 parent subjects');
  return rows;
}
function validateBaselineFeatureIdentity(roster,baselineCommit){
  const blob=rel=>execFileSync('git',['-C',repo,'show',`${baselineCommit}:${rel}`],{maxBuffer:40*1024*1024});
  const index=JSON.parse(blob('data/world-index.json'));
  const wanted=new Set(roster),found=new Map();
  for(const rel of index.parts){
    const file=`data/${rel}`,doc=JSON.parse(blob(file));
    for(const feature of doc.features??[]){
      const id=feature.id??feature.properties?.id;
      if(wanted.has(id)){
        fail(!found.has(id),`Subject has multiple containing features: ${id}`);
        found.set(id,{id,path:file,name:feature.properties?.name??null,parent_id:feature.properties?.parent_id??null});
      }
    }
  }
  fail(found.size===roster.length&&equal(sorted([...found.keys()]),sorted(roster)),
    'Baseline location features do not cover the exact unique subject roster');
  return {index,found};
}
function runControls(scope,baselineScope,saved,archived,liveIssues,roster){
  const controls=[];
  const expectReject=(name,fn)=>{
    let message='';try{fn();}catch(error){message=error.message;}
    fail(message.length>0,`Negative control unexpectedly passed: ${name}`);
    controls.push({id:name,passed:true,rejection:message});
  };
  const dup={...scope,member_location_ids:[...roster.slice(0,-1),roster[0]]};
  dup.member_location_ids_sha256=sha(Buffer.from(dup.member_location_ids.join('\n')));
  expectReject('duplicate_subject_even_with_recomputed_digest',()=>validateParentScope(dup,baselineScope,liveIssues.find(x=>x.number===454)));
  const missing={...scope,member_location_ids:roster.slice(1)};
  expectReject('missing_subject',()=>validateParentScope(missing,baselineScope,liveIssues.find(x=>x.number===454)));
  const fabricated={...scope,member_location_ids:[...roster.slice(0,-1),'gb:FJI:ADM2:NOT-A-REAL-ID']};
  fabricated.member_location_ids_sha256=sha(Buffer.from(fabricated.member_location_ids.join('\n')));
  expectReject('fabricated_subject',()=>validateParentScope(fabricated,baselineScope,liveIssues.find(x=>x.number===454)));
  expectReject('changed_declared_count',()=>validateParentScope({...scope,location_count:24},baselineScope,liveIssues.find(x=>x.number===454)));
  expectReject('changed_declared_digest',()=>validateParentScope({...scope,member_location_ids_sha256:'0'.repeat(64)},baselineScope,liveIssues.find(x=>x.number===454)));
  const repeatedSaved={...saved,followups:[...saved.followups]};
  repeatedSaved.followups[0]={...repeatedSaved.followups[0],number:911};
  expectReject('duplicate_child_missing_910',()=>validateChildren(repeatedSaved,archived,liveIssues,roster));
  expectReject('missing_child_913',()=>validateChildren({...saved,followups:saved.followups.filter(x=>x.number!==913)},archived,liveIssues,roster));
  expectReject('unexpected_child_914',()=>validateChildren({...saved,followups:[...saved.followups,{...saved.followups[0],number:914}]},archived,liveIssues,roster));
  const liveDuplicate=liveIssues.map(x=>x.number===910?{...x,body:x.body.replace(roster[0],roster[1])}:x);
  expectReject('incorrect_fiji_child_subset',()=>validateChildren(saved,archived,liveDuplicate,roster));
  const overlap=liveIssues.map(x=>x.number===912?{...x,body:x.body.replace('gb:VUT:ADM1:32282491B17169683382430',roster[3])}:x);
  expectReject('overlapping_child_subjects',()=>validateChildren(saved,archived,overlap,roster));
  const missingMember=liveIssues.map(x=>x.number===913?{...x,body:x.body.replace(roster.at(-1),'gb:SLB:ADM1:NOT-A-REAL-ID')}:x);
  expectReject('incomplete_child_union',()=>validateChildren(saved,archived,missingMember,roster));
  return controls;
}

const snapshots=readJson(snapshotFile),liveIssues=snapshots.issues;
fail(snapshots.repository==='ChengshuLi/WorldAtlas'&&snapshots.retrieved_via.includes('GitHub REST API'),
  'Issue snapshots must document repository and API retrieval');
const workItem=snapshots.work_item,workSpec=machineContract(workItem);
fail(workItem.number===1107&&workItem.state==='open'&&
  ['kind:work-item','status:ready','type:geography'].every(label=>workItem.labels.includes(label)),
  'Current #1107 must remain an open, ready geography work item');
fail(workSpec.mode==='geography'&&workSpec.max_prs===1&&equal(workSpec.depends_on,[454])&&
  equal(workSpec.owned_paths,['data/regional-review/melanesia-subject-validation-20261006/']),
  'Current #1107 work contract scope, dependency, or ownership differs');
fail(unique(workSpec.evidence_quality?.subject_ids??[])&&workSpec.evidence_quality.subject_ids.length===25,
  'Current #1107 must declare exactly 25 unique evidence subjects');
fail(liveIssues.length===5&&unique(liveIssues.map(x=>x.number)),'Snapshot must contain #454 and #910–#913 exactly once');
const issue454=liveIssues.find(x=>x.number===454),children=liveIssues.filter(x=>x.number!==454);
fail(issue454.state==='closed','Parent #454 must be closed before this corrective packet runs');
const scope=readJson(path.join(parent,'scope.json'));
const pinned=readJson(path.join(parent,'baseline-files.json'));
const baselineScope=pinned.scope;
const {expected,live}=validateParentScope(scope,baselineScope,issue454);
fail(equal(sorted(workSpec.evidence_quality.subject_ids),sorted(expected)),
  'Current #1107 declared subject roster differs from exact parent contract');
const oldIssue=readJson(path.join(parent,'issue-scope-pinned.json'));
fail(oldIssue.number===454,'Original archived issue identity mismatch');
const originalRoster=expectedRoster(JSON.parse(oldIssue.body.match(/```json\s*\n([\s\S]*?)\n```/)[1]));
fail(equal(sorted(originalRoster),sorted(expected)),'Original archived issue scope differs from immutable baseline roster');
const saved=readJson(path.join(parent,'follow-up-issues.json'));
const archivedContracts=readJson(path.join(parent,'follow-up-contract-check.json'));
const childRows=validateChildren(saved,archivedContracts,children,expected);
const featureAudit=validateBaselineFeatureIdentity(expected,pinned.commit);
const reproduction=readJson(path.join(parent,'reproduction.json'));
fail(Array.isArray(reproduction.subjects)&&unique(reproduction.subjects.map(x=>x.location_id))&&
  equal(sorted(reproduction.subjects.map(x=>x.location_id)),sorted(expected)),
  'Original reproduced rows must cover every exact subject once');
for(const row of reproduction.subjects)
  fail(featureAudit.found.get(row.location_id)?.path===row.baseline_containing_file&&
    featureAudit.found.get(row.location_id)?.name===row.name&&
    featureAudit.found.get(row.location_id)?.parent_id===(row.parent_id??null),
    `Original row identity/parent/containing-file differs from immutable feature: ${row.location_id}`);
const controls=runControls(scope,baselineScope,saved,archivedContracts,liveIssues,expected);
const sourceInventory=readJson(path.join(parent,'sources.json'));
for(const row of sourceInventory.files){
  const bytes=fs.readFileSync(path.join(parent,row.path));
  fail(bytes.length===row.bytes&&sha(bytes)===row.sha256,`Original source bytes differ from retained inventory: ${row.path}`);
}
const nativeSources={
  FJI:JSON.parse(fs.readFileSync(path.join(parent,'sources/fiji-2007-census-province.geojson'),'utf8')),
  SLB:JSON.parse(fs.readFileSync(path.join(parent,'sources/solomon-islands-natural-earth-adm1.geojson'),'utf8')),
  VUT:JSON.parse(fs.readFileSync(path.join(parent,'sources/vanuatu-2017-adm1.geojson'),'utf8'))
};
const nativeMaps={};
for(const [code,collection] of Object.entries(nativeSources)){
  nativeMaps[code]=new Map();
  for(const feature of collection.features??[]){
    const id=feature.properties?.shapeID;
    fail(typeof id==='string'&&!nativeMaps[code].has(id),`Duplicate/missing ${code} native source ID`);
    nativeMaps[code].set(id,feature);
  }
}
const nclFiles=fs.readdirSync(path.join(parent,'sources/new-caledonia-province-parts')).sort();
const nclFeatures=nclFiles.map(file=>JSON.parse(fs.readFileSync(path.join(parent,'sources/new-caledonia-province-parts',file),'utf8')).features[0]);
const nclNames={'NCL-559':'PROVINCE_NORD','NCL-1258':'PROVINCE_DES_ILES','NCL-1259':'PROVINCE_SUD'};
for(const row of reproduction.subjects){
  const code=row.location_id.startsWith('gb:')?row.location_id.split(':')[1]:'NCL';
  if(code==='NCL'){
    const feature=nclFeatures.find(f=>f.properties?.nom_fichier===nclNames[row.location_id]);
    fail(Boolean(feature)&&row.source_name===nclNames[row.location_id],`New Caledonia source feature mapping differs: ${row.location_id}`);
  }else{
    const nativeId=row.location_id.split(':').at(-1),feature=nativeMaps[code]?.get(nativeId);
    fail(Boolean(feature)&&feature.properties?.shapeName===row.name&&row.source_name===row.name,
      `Native source ID/name crosswalk differs: ${row.location_id}`);
  }
}
const subjectRows=reproduction.subjects.map(row=>({...row,
  parent_id:featureAudit.found.get(row.location_id).parent_id,
  baseline_containing_file:featureAudit.found.get(row.location_id).path}));
const result={version:1,issue:1107,parent_issue:454,scope_validation:{
  source:'current #454 GitHub issue body, original pinned workload, and ancestor scope at the original packet baseline',
  retrieved_at:snapshots.retrieved_at,exact_subject_count:expected.length,
  subject_ids_sha256:scope.member_location_ids_sha256,unique_subject_count:new Set(scope.member_location_ids).size,
  unique_baseline_feature_count:featureAudit.found.size,original_row_count:reproduction.subjects.length,
  original_row_unique_count:new Set(reproduction.subjects.map(x=>x.location_id)).size,
  source_identity_matches:reproduction.subjects.length,
  original_findings:{correction_needed:subjectRows.filter(x=>x.finding==='correction-needed').length,
    insufficient_evidence:subjectRows.filter(x=>x.finding==='insufficient-evidence').length,
    by_country:{FJI:subjectRows.filter(x=>x.location_id.startsWith('gb:FJI:')).length,
      NCL:subjectRows.filter(x=>x.location_id.startsWith('NCL-')).length,
      VUT:subjectRows.filter(x=>x.location_id.startsWith('gb:VUT:')).length,
      SLB:subjectRows.filter(x=>x.location_id.startsWith('gb:SLB:')).length}},
  rows:subjectRows},followup_validation:{expected_issue_numbers:expectedIssueIds,child_issue_count:childRows.length,
    unique_child_issue_count:new Set(childRows.map(x=>x.issue)).size,
    archived_contracts_status:'blocked on parent (as recorded 2026-10-05)',
    current_parent_state:issue454.state,children:childRows,complete_disjoint_union:true,
    union_subject_count:expected.length},controls,limits:[
  'This corrective packet verifies scope, source-byte accounting, and child-contract coverage; it does not re-adjudicate any territorial boundary.',
  'The original parent packet retains source roles, vintages, licenses, and geographic uncertainties; see its findings.md and source-acquisition.json. Original source-byte hashes were rechecked, not upstream products or reuse terms.',
  'Archived child status and current GitHub readiness are distinct snapshots; no status is inferred from the other.',
  'Counts, source identity, and source geometries do not establish legal boundary correctness, completeness, parent meaning, or regional approval.'
]};
const positive={method_id:'melanesia-contract-validation',kind:'positive-control',outcome:'passed',
  parent_subjects:expected.length,unique_baseline_features:featureAudit.found.size,
  child_issues:childRows.length,disjoint_child_union:expected.length};
const negative={version:1,issue:1107,method_id:'melanesia-contract-validation',kind:'negative-control',
  outcome:'passed',all_passed:controls.length===11,control_count:controls.length,controls};
fail(negative.all_passed,'Expected all eleven substantive negative controls to pass');
const output=path.join(outDir,'reproduction.json'),controlsPath=path.join(outDir,'negative-controls.json');
fs.mkdirSync(outDir,{recursive:true});
fs.writeFileSync(output,JSON.stringify(result,null,2)+'\n');
fs.writeFileSync(controlsPath,JSON.stringify(negative,null,2)+'\n');
fs.writeFileSync(path.join(outDir,'positive-control.json'),JSON.stringify(positive,null,2)+'\n');
console.log(JSON.stringify({issue:1107,subjects:expected.length,children:childRows.length,
  controls:controls.length,output_sha256:sha(fs.readFileSync(output)),
  controls_sha256:sha(fs.readFileSync(controlsPath))},null,2));
