import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {deriveSourceTargetNativeDelta,nativeRowLatitudes} from '../src/native-grid.js';
import {ImmutableReader} from '../scripts/check-effective-geographic-regression.mjs';
import {constructOriginalAuthority} from '../scripts/delivery-handoff-advance.mjs';
import {valueSha} from '../coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';

const version='a'.repeat(40),foreign='b'.repeat(40);
const executingHead=execFileSync('git',['-c','protocol.allow=never','rev-parse','HEAD'],{encoding:'utf8'}).trim();
const prefix='coordination/engineering/dated-centre-fixture',family='gb:TST:ADM2',sourceId=family+':A',siblingId=family+':B';
const size=262166,y=size/2,x=(size/2-1)/2,longitude=-90;
const latitudes=nativeRowLatitudes(size),latitude=latitudes[y],latitudeBytes=Buffer.alloc(size*8);
for(let i=0;i<size;i++)latitudeBytes.writeDoubleLE(latitudes[i],i*8);
const digest=raw=>createHash('sha256').update(raw).digest('hex');
const blob=raw=>createHash('sha1').update('blob '+raw.length+'\0').update(raw).digest('hex');
const rectangle=(left,right,bottom=-.02,top=.02)=>({type:'Polygon',coordinates:[[[left,bottom],[right,bottom],[right,top],[left,top],[left,bottom]]]});
const empty=()=>({type:'Polygon',coordinates:[]});
const feature=(id,geometry)=>({type:'Feature',properties:{shapeID:id},geometry});
const clone=value=>structuredClone(value);
const key={owner:1,y,x},block=[0,0],scene='S2_FIXTURE_20200131_L2A';
const png=Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=','base64');

// Only Git transport is substituted. The production reader, constructor,
// source/member joins, physical witness operator and native scanner all run.
function fixture({legacy=false,displayPrefix='',change=()=>{},changeSupport=()=>{},forgeSupport}={}){
 const geometry=rectangle(-90.1,-89.9),other=rectangle(-89.8,-89.7);
 const original={owner:1,y,x,flags:[],territorial_holds:[]};
 const state={
  originals:[feature('A',geometry),feature('B',other)],
  roster:[{id:sourceId,index:1},{id:siblingId,index:2}],
  targets:[{id:sourceId,pixelIndex:1,source_family:family,base_geometry:geometry,coverage_classes:['mapped_land_support'],territorial_exclusions:[]}],
  physical:{results:[{target:sourceId,issues:[],support:{mapped_land_support:legacy?geometry:empty()}}]},
  measured:[{target:sourceId,consumed:{geometry},selected:{id:sourceId,geometry}}],
  proposed:{rows:[{y,runs:[[x,x+1,1]]}]},
  adoption:{records:[{original_key:key,centre_unchanged:{owner:1,y,x,longitude,latitude},
   original_record_unchanged:original,original_source_array_index:123,plan_index:17,
   adopted_bounded_answer:true,category:'dated-terrestrial-body-location',source_review_kind:'exposed-terrestrial-location',
   actual_answer:'Dated terrestrial body location at this original centre.',
   answer_dates:['2020-01-31T03:04:05.1234Z'],remaining_physical_question:null,
   review:{path:'review.json',record_index:275}}]},
  review:{records:[{index:275,original_key:key,original_source_array_index:123,interpretation:'exposed-terrestrial-location'}]},
  observation:{item:scene,acquisition_datetime:'2020-01-31T03:04:05.123400Z',
   points:[{index:17,original_key:key,longitude,latitude,physical_block:block,
    assets:Object.fromEntries(['red','green','blue','nir','scl'].map(name=>[name,{value:1,valid_mask:255}]))}],
   blocks:[{block,indices:[17],displays:[]}]}
 };
 change(state);
 const files=new Map(),byBlob=new Map();
 const put=(name,value,commit=version)=>{
  const raw=Buffer.isBuffer(value)?value:Buffer.from(JSON.stringify(value));
  const pin={commit,path:name,mode:'100644',git_blob_oid:blob(raw),bytes:raw.length,sha256:digest(raw)};
  files.set(commit+':'+name,{raw,pin});byBlob.set(pin.git_blob_oid,raw);return pin;
 };
 const frames=['rgb','nir-red-green'].map(channels=>{
  const name=displayPrefix+scene+'/block-0-0/'+channels+'-native.png';
  const pin=put(prefix+'/native/'+name,png);
  state.observation.blocks[0].displays.push({path:name,bytes:pin.bytes,sha256:pin.sha256});
  return {id:channels,role:'frame',pin,observation:'observation',display_base:prefix+'/native',block_pointer:'/blocks/0',
   display_pointer:'/blocks/0/displays/'+(channels==='rgb'?0:1),channels};
 });
 const source=put('original-source.json',{type:'FeatureCollection',features:state.originals});
 const roster=put('owners.json',state.roster),physical=put('physical.json',state.physical);
 const measured=put('measured.json',state.measured),nativeLatitudes=put('latitudes.f64le',latitudeBytes);
 const catalogue=put('coordination/engineering/original-geography-source-corpus-20261006/catalogue.json',{
  products:[{key:family,parts:[{path:source.path,bytes:source.bytes,sha256:source.sha256}],
   feature_count:state.originals.length,original_bytes:source.bytes,original_sha256:source.sha256}]});
 const nativeContract={size,native_latitudes:nativeLatitudes,original_assets:{bounds:{sha256:roster.sha256}}};
 const adoption=put(prefix+'/adoptions.json',state.adoption),review=put(prefix+'/review.json',state.review);
 const observation=put(prefix+'/native/'+scene+'/native-observations.json',state.observation);
 const support={version:1,kind:'adopted-dated-native-centre-land-support-v1',native_contract_sha256:valueSha(nativeContract),
  provenance:[{id:'adoption',role:'adoption',pin:adoption},{id:'review',role:'review',pin:review},
   {id:'observation',role:'observation',pin:observation},...frames],
  records:[{source_id:sourceId,pixelIndex:1,y,x,longitude,latitude,
   adoption:{id:'adoption',pointer:'/records/0'},review:{id:'review',pointer:'/records/0',interpretation_pointer:'/interpretation'},
   observations:[{id:'observation',pointer:'/points/0',frames:['rgb','nir-red-green']}]}]};
 changeSupport(support,state);
 const supportPath=prefix+'/dated-land-support.json';
 let dated=put(supportPath,support);
 // The executing module tree, not the caller's reader.version, is authoritative.
 put(supportPath,support,executingHead);
 if(forgeSupport){const forged=clone(support);forgeSupport(forged);dated=put(supportPath,forged,foreign);}
 const membership=state.membership?{
  index:put('data/world-index.json',{parts:['geography/part-0.json']}),
  lineage:put('data/semantic-report.json',state.membership.lineage),
  parts:[put('data/geography/part-0.json',state.membership.accepted)]}:undefined;
 const evidence=put('source-evidence.json',{version:legacy?1:2,kind:'source-target-native-evidence-v'+(legacy?1:2),
  catalogue,owner_roster:roster,physical_evidence:physical,physical_input:measured,
  physical_reproduction:put('physical.py',Buffer.from('# retained fixture')),
  native_latitudes:nativeLatitudes,native_contract:nativeContract,base_reference:{id:'fixture-base'},
  families:[{source_id:family,parts:[source]}],
  targets:state.targets.map(target=>({...target,source_receipt_sha256:physical.sha256})),
  ...(!legacy?{dated_land_support:dated}:{}),...(membership?{source_membership:membership}:{})});
 const patch=put('patch.json',state.proposed);
 class FixtureReader extends ImmutableReader{
  git(...args){
   if(args[0]==='ls-tree'){
    const entry=files.get(args[2]+':'+args.at(-1));assert.ok(entry,args[2]+':'+args.at(-1));
    return Buffer.from('100644 blob '+entry.pin.git_blob_oid+'\t'+args.at(-1)+'\0');
   }
   if(args[0]==='cat-file'&&args[1]==='-e')return Buffer.alloc(0);
   if(args[0]==='cat-file'&&args[1]==='-s')return Buffer.from(String(byBlob.get(args[2]).length));
   if(args[0]==='cat-file'&&args[1]==='blob')return byBlob.get(args[2]);
   throw Error('Unexpected fixture Git request: '+args.join(' '));
  }
 }
 const reader=()=>new FixtureReader('.',version,{runtimeBytes:0,metadataBytes:0,outputBytes:16*1024*1024,
  allowance:{phaseBytes:192*1024*1024,rssBytes:1024*1024*1024}});
 return {run:(inputReader=reader())=>constructOriginalAuthority(inputReader,{
  source_evidence:{commit:version,path:evidence.path},native_patch:{commit:version,path:patch.path}}),
  reader,files,byBlob,state,support,adoption,review,observation};
}

function positive(result){
 assert.equal(result.ledger_rows.length,1);
 const row=result.ledger_rows[0];
 assert.equal(row.target_id,sourceId);assert.equal(row.pixelIndex,1);assert.equal(row.native_cells,1);
 assert.deepEqual(row.native_rows,[{y,runs:[[x,x+1,1]]}]);
 return row;
}
test('actual constructor consumes dated-only land at exactly one native centre and retains v1 mapped support',()=>{
 const dated=fixture();const before=clone(dated.state);positive(dated.run());assert.deepEqual(dated.state,before);
 positive(fixture({change:s=>s.adoption.records[0].answer_dates=['2020-01-31']}).run());
 positive(fixture({displayPrefix:'remaining-december/'}).run());
 positive(fixture({legacy:true}).run());
 assert.throws(()=>fixture({change:s=>s.proposed.rows[0].runs[0][1]++}).run(),/coverage|support/i);
});

test('coherent caller replacement cannot turn reader.version or arbitrary pins into adopted authority',()=>{
 positive(fixture().run());
 for(const mutate of [
  s=>s.records[0].adoption.pointer='/records/1',
  s=>s.records[0].review.pointer='/records/1',
  s=>s.records[0].observations[0].pointer='/points/1',
  s=>s.provenance.find(p=>p.role==='frame').display_pointer='/blocks/0/displays/1',
  s=>s.records[0].x++,
  s=>s.records[0].pixelIndex=2,
  s=>s.records[0].source_id=siblingId
 ])assert.throws(()=>fixture({forgeSupport:mutate}).run(),/current|execut|descriptor|accepted|typed|support/i);
 const tampered=fixture(),entry=tampered.files.get(version+':'+tampered.observation.path);
 tampered.byBlob.set(entry.pin.git_blob_oid,Buffer.from('changed consumed observation'));
 assert.throws(()=>tampered.run(),/whole|identity|differ|body/i);
});

test('adoption, review, observation and native frame joins are substantive consumed records',()=>{
 for(const change of [
  s=>delete s.adoption.records[0].review,
  s=>s.adoption.records[0].review.path='different/review.json',
  s=>s.adoption.records[0].review.record_index=0,
  s=>s.review.records[0].original_key={owner:1,y,x:x+1},
  s=>s.review.records[0].original_source_array_index++,
  s=>s.review.records[0].interpretation='unresolved',
  s=>s.observation.points=[],
  s=>s.observation.points[0].index++,
  s=>s.observation.points[0].original_key={owner:1,y,x:x+1},
  s=>s.observation.points[0].longitude+=.001,
  s=>s.observation.points[0].physical_block=[0,1],
  s=>s.observation.item='different-scene',
  s=>s.observation.acquisition_datetime='2020-01-31T03:04:05.123401Z',
  s=>s.adoption.records[0].answer_dates=['2020-02-01'],
  s=>s.adoption.records[0].centre_unchanged.x++,
  s=>s.adoption.records[0].original_record_unchanged.owner=2,
  s=>s.observation.blocks[0].indices=[18]
 ])assert.throws(()=>fixture({change}).run(),/dated|adopt|review|observ|frame|centre|original|date|source/i);
 for(const changeSupport of [
  s=>delete s.records[0].adoption,
  s=>s.records[0].observations=[],
  s=>s.records[0].review.interpretation_pointer='/missing',
  s=>s.records[0].observations[0].frames=['rgb'],
  s=>s.provenance.find(p=>p.id==='nir-red-green').channels='rgb',
  s=>s.provenance.find(p=>p.id==='rgb').display_base=prefix+'/wrong-base',
  s=>delete s.provenance.find(p=>p.id==='rgb').display_base,
  s=>s.provenance.find(p=>p.id==='rgb').pin={...s.provenance.find(p=>p.id==='rgb').pin,sha256:'0'.repeat(64)},
  s=>s.native_contract_sha256='0'.repeat(64)
 ])assert.throws(()=>fixture({changeSupport}).run(),/dated|adopt|review|observ|frame|centre|native|contract|whole|input|body/i);
});

test('dated original member remains bound to complete accepted aggregate membership',()=>{
 const aggregateId=family+':AGG';
 const aggregate=s=>{
  const geometry={type:'MultiPolygon',coordinates:s.originals.map(f=>f.geometry.coordinates)};
  s.roster=[{id:aggregateId,index:1}];s.targets[0].target_id=aggregateId;s.targets[0].base_geometry=geometry;
  s.measured[0].selected={id:aggregateId,geometry};
  s.membership={lineage:{changes:[{id:aggregateId,replaces:[sourceId,siblingId]}]},
   accepted:{type:'FeatureCollection',features:[{type:'Feature',id:aggregateId,
    properties:{metadata:{source_member_ids:[sourceId,siblingId]}},geometry}]}};
 };
 const accepted=fixture({change:aggregate}).run();
 assert.equal(accepted.ledger_rows[0].target_id,aggregateId);
 assert.deepEqual(accepted.ledger_rows[0].native_rows,[{y,runs:[[x,x+1,1]]}]);
 assert.throws(()=>fixture({change:s=>{aggregate(s);s.membership.lineage.changes[0].replaces=[sourceId];}}).run(),/member|mapping/i);
 assert.throws(()=>fixture({change:aggregate,changeSupport:s=>s.records[0].source_id=siblingId}).run(),/exact requested source member/i);
 assert.throws(()=>fixture({change:aggregate,changeSupport:s=>s.records[0].pixelIndex=2}).run(),/source member|land class|centre/i);
});

test('water, special and unresolved records do not become dated land or inland-water permission',()=>{
 for(const mutate of [
  a=>a.category='dated-water-location',
  a=>a.category='managed-compartment',
  a=>a.adopted_bounded_answer=false,
  a=>a.remaining_physical_question='Unresolved ground state',
  a=>a.actual_answer=''
 ])assert.throws(()=>fixture({change:s=>mutate(s.adoption.records[0])}).run(),/adopt|land|terrestr|answer|unresolved|dated/i);
 assert.throws(()=>fixture({change:s=>s.targets[0].coverage_classes=['mapped_inland_water_support']}).run(),/land|water|coverage|support/i);
});

test('whole encoded frames retain their buffer charge and cap while legacy inputs retain sixfold scratch',()=>{
 const legacyPaths=['source-evidence.json','patch.json',
  'coordination/engineering/original-geography-source-corpus-20261006/catalogue.json',
  'physical.json','measured.json','physical.py','latitudes.f64le','owners.json','original-source.json'];
 const legacy=fixture({legacy:true}),legacyReader=legacy.reader();positive(legacy.run(legacyReader));
 const total=(f,paths)=>paths.reduce((n,p)=>n+f.files.get(version+':'+p).pin.bytes,0);
 assert.deepEqual([...legacyReader.charged.keys()].sort(),legacyPaths.map(p=>version+':'+p).sort());
 // Every old input still retains its admitted encoded bytes plus the same
 // sixfold scratch, including the native latitude table and source JSON.
 assert.equal(legacyReader.used,legacyReader.outputBytes+7*total(legacy,legacyPaths));

 const dated=fixture(),reader=dated.reader(),frame=dated.support.provenance.find(p=>p.id==='rgb').pin;
 let beforeFrame;
 const admit=reader.admit.bind(reader);
 reader.admit=(pin,decoded)=>{
  if(pin.path===frame.path&&!reader.charged.has(pin.commit+':'+pin.path))beforeFrame=reader.used-frame.bytes;
  return admit(pin,decoded);
 };
 positive(dated.run(reader));assert.ok(Number.isSafeInteger(beforeFrame));
 const framePaths=dated.support.provenance.filter(p=>p.role==='frame').map(p=>p.pin.path);
 const datedJson=[...legacyPaths,prefix+'/dated-land-support.json',dated.adoption.path,dated.review.path,dated.observation.path];
 assert.deepEqual([...reader.charged.keys()].sort(),[...datedJson,...framePaths].map(p=>version+':'+p).sort());
 assert.equal(reader.used,reader.outputBytes+7*total(dated,datedJson)+2*total(dated,framePaths));
 for(const path of framePaths)assert.equal(reader.inventory.get(version+':'+path).whole_body_consumed,true);

 // The actual complete PNG is one byte beyond the remaining temporary buffer
 // allowance. Fail before admitting/opening it; no image decoding is involved.
 const limited=dated.reader();limited.allowance.phaseBytes=beforeFrame+frame.bytes-1;
 assert.throws(()=>dated.run(limited),/Dated encoded frame buffer exceeds phase/);
 assert.equal(limited.used,beforeFrame);
 assert.equal(limited.charged.has(version+':'+frame.path),false);
 assert.equal(limited.inventory.get(version+':'+frame.path).whole_body_consumed,undefined);
 const missing=fixture(),missingFrame=missing.support.provenance.find(p=>p.id==='rgb').pin;
 missing.byBlob.set(missingFrame.git_blob_oid,Buffer.from('invalid PNG body'));
 assert.throws(()=>missing.run(),/whole|identity|body/i);
});

function physicalVeto(state,reason){
 const result=state.physical.results[0],geometry=rectangle(-90.02,-89.98);
 result.support={mapped_land_support:empty(),mapped_inland_water_support:empty(),outside_mapped_L1_context:empty(),
  missing_reconstruction:empty(),extra_reconstruction:empty(),contradictory_land_water_support:empty(),
  hierarchy_disagreements:Object.fromEntries(['L2-outside-L1','L3-outside-L2','L4-outside-L3'].map(k=>[k,empty()]))};
 if(reason==='outside_mapped_L1_context')result.support[reason]=geometry;
 else{
  if(reason.startsWith('L'))result.support.hierarchy_disagreements[reason]=geometry;
  else result.support[reason]=geometry;
  result.issues=[{reason,geometry}];
  result.source_id_queries=[7];result.query_relations=[{source_id:7,periodic_offset:0,status:'checked',
   source_covers_candidate:true,candidate_covers_source:false,intersects:true,disjoint:false,witness:'complete-candidate-reconstruction'}];
 }
}
test('complete original member retains competitor and territory vetoes outside selected base',()=>{
 // Keep the original source's reviewed component outside the selected base.
 // The complete member must still bring a competitor there into the scan.
 const secondComponent=s=>{
  const base=rectangle(-89.8,-89.7),reviewed=s.originals[0].geometry;
  const whole={type:'MultiPolygon',coordinates:[base.coordinates,reviewed.coordinates]};
  s.originals[0].geometry=whole;s.targets[0].base_geometry=base;
  s.measured[0]={target:sourceId,consumed:{geometry:whole},selected:{id:sourceId,geometry:base}};
 };
 positive(fixture({change:secondComponent}).run());
 assert.throws(()=>fixture({change:s=>{
  secondComponent(s);s.originals.push(feature('C',rectangle(-90.01,-89.99)));
  s.roster.push({id:family+':C',index:3});
 }}).run(),/unique source-target coverage/i);
 assert.throws(()=>fixture({change:s=>{
  secondComponent(s);s.targets[0].territorial_exclusions=[rectangle(-90.01,-89.99)];
 }}).run(),/unique source-target coverage/i);
});

test('new positive does not bypass physical, exterior, source-domain, competitor, territory or tie vetoes',()=>{
 for(const reason of ['missing_reconstruction','extra_reconstruction','contradictory_land_water_support','L2-outside-L1','outside_mapped_L1_context'])
  assert.throws(()=>fixture({change:s=>physicalVeto(s,reason)}).run(),/residual|conflict|witness/i,reason);
 for(const change of [
  s=>{const g=rectangle(-89.99,-89.9);s.originals[0].geometry=g;s.targets[0].base_geometry=g;s.measured[0]={target:sourceId,consumed:{geometry:g},selected:{id:sourceId,geometry:g}};},
  s=>s.originals[1].geometry=rectangle(-90.01,-89.99),
  s=>s.targets[0].territorial_exclusions=[rectangle(-90.02,-89.98)],
  s=>s.targets[0].territorial_exclusions=[rectangle(-90,-89.98)]
 ])assert.throws(()=>fixture({change}).run(),/coverage|source|support/i);
});

function smallInput(){
 const geometry=rectangle(-89,89,-40,40);
 return {targets:[{id:'city',pixelIndex:1}],sourceFeatures:[{id:'A',target_id:'city',pixelIndex:1,geometry}],
  coverageFeatures:[],coverageCentres:[{source_id:'A',pixelIndex:1,y:3,x:2}],
  size:8,latitudes:nativeRowLatitudes(8),rowStart:0,rowEnd:8,
  ownerRows:Array.from({length:8},(_,y)=>({y,complete_owner_intervals:[]})),
  diagnosticRows:[{y:3,runs:[[2,4,1]]}]};
}
test('native positive seam cannot spread, borrow a sibling or overwrite an existing owner',()=>{
 const input=smallInput(),result=deriveSourceTargetNativeDelta(input);
 assert.deepEqual(result.rows,[{y:3,runs:[[2,3,1]]}]);
 assert.deepEqual(result.diagnostic_rows,[{y:3,runs:[[2,3,1,'assigned_cells'],[3,4,1,'unsupported_coverage_cells']]}]);
 const owned=smallInput();owned.ownerRows[3].complete_owner_intervals=[[2,3,2]];
 assert.equal(deriveSourceTargetNativeDelta(owned).diagnostic_rows[0].runs[0][3],'already_owned_cells');
 const sibling=smallInput();sibling.sourceFeatures=[
  {id:'A',target_id:'city',pixelIndex:1,geometry:rectangle(-89,-1,-40,40)},
  {id:'B',target_id:'city',pixelIndex:1,geometry:rectangle(1,89,-40,40)}];
 sibling.coverageCentres[0].x=4;sibling.diagnosticRows=[{y:3,runs:[[4,5,1]]}];
 assert.equal(deriveSourceTargetNativeDelta(sibling).diagnostic_rows[0].runs[0][3],'unsupported_coverage_cells');
 const grouped=smallInput();grouped.coverageFeatureGroups=[[],[{id:'city',source_id:'A',pixelIndex:1,geometry:rectangle(0,1,-40,40)}]];
 grouped.coverageCentreGroups=[grouped.coverageCentres,[]];
 const classes=deriveSourceTargetNativeDelta(grouped).coverage_groups;
 assert.deepEqual(classes[0].rows,[{y:3,runs:[[2,3,1]]}]);assert.deepEqual(classes[1].rows,[]);
});
