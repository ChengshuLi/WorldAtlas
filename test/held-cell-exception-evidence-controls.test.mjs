import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {execFileSync, spawnSync} from 'node:child_process';
import {gunzipSync, gzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import {nativePolygonIntervals, nativeRowLatitudes, witnessCellEffects} from '../coordination/engineering/original-held-cell-exceptions-20261018/native-grid-pinned.mjs';
import {prepareNativeRegressionInputs} from '../scripts/run-integration-tests.mjs';

const packet='coordination/engineering/original-held-cell-exceptions-20261018/';
const packetFixture='test/fixtures/held-cell-exceptions/packet/';
const fixturePath='test/fixtures/held-cell-exceptions/current-packet-controls.json';
const historicalPinsPath='test/fixtures/held-cell-exceptions/historical-input-pins.json';
const readJson=name=>JSON.parse(fs.readFileSync(name.startsWith(packet)?packetFixture+name.slice(packet.length):name,'utf8'));
const sha256=bytes=>createHash('sha256').update(bytes).digest('hex');
const gitBlobOid=bytes=>createHash('sha1').update(Buffer.from(`blob ${bytes.length}\0`)).update(bytes).digest('hex');

function usedSourcePins(pins){
  return [pins.liberia.source_evidence,pins.liberia.physical_whole_target_support,pins.liberia.native_latitudes,
    ...pins.liberia.original_negative_families.map(item=>item.part),pins.egypt.source_evidence,
    ...Object.values(pins.egypt.whole_original_family_payloads).flatMap(item=>item.parts)];
}

function reproduceSourcePins(pins){
  return [
    {name:'Liberia source evidence',...pins.liberia.source_evidence},
    {name:'Liberia whole-target physical support',...pins.liberia.physical_whole_target_support},
    {name:'Normative native latitude table',...pins.egypt.native_latitudes},
    ...pins.liberia.original_negative_families.map(item=>({name:'Original negative family '+item.source_id,...item.part})),
    {name:'Egypt full source evidence',...pins.egypt.source_evidence},
    ...Object.entries(pins.egypt.whole_original_family_payloads).map(([family,item])=>({name:'Original family '+family,...item.parts[0]}))
  ].map(({name,commit,path,bytes,git_blob_oid,sha256,decoded_bytes,decoded_sha256})=>({
    name,commit,path,mode:'100644',bytes,git_blob_oid,sha256,...(decoded_bytes===undefined?{}:{decoded_bytes}),
    ...(decoded_sha256===undefined?{}:{decoded_sha256})
  }));
}

function authenticateHistoricalInputs(pins){
  const seen=new Set();
  for(const pin of pins){
    const key=pin.commit+':'+pin.path;assert(!seen.has(key),`duplicate historical input ${key}`);seen.add(key);
    const tree=execFileSync('git',['ls-tree','-z',pin.commit,'--',pin.path],{
      encoding:'buffer',env:{...process.env,GIT_NO_LAZY_FETCH:'1',GIT_TERMINAL_PROMPT:'0'}
    }).toString('utf8');
    assert.equal(tree,`${pin.mode} blob ${pin.git_blob_oid}\t${pin.path}\0`,`${key} tree identity`);
    const body=execFileSync('git',['show',key],{
      encoding:'buffer',maxBuffer:64*1024*1024,
      env:{...process.env,GIT_NO_LAZY_FETCH:'1',GIT_TERMINAL_PROMPT:'0'}
    });
    assert.equal(body.length,pin.bytes,`${key} encoded bytes`);
    assert.equal(gitBlobOid(body),pin.git_blob_oid,`${key} Git blob OID`);
    assert.equal(sha256(body),pin.sha256,`${key} encoded SHA-256`);
    if(pin.decoded_bytes!==undefined||pin.decoded_sha256!==undefined){
      assert(Number.isSafeInteger(pin.decoded_bytes)&&pin.decoded_bytes>0,`${key} decoded size pin`);
      assert.match(pin.decoded_sha256,/^[0-9a-f]{64}$/);
      const decoded=gunzipSync(body);
      assert.equal(decoded.length,pin.decoded_bytes,`${key} decoded bytes`);
      assert.equal(sha256(decoded),pin.decoded_sha256,`${key} decoded SHA-256`);
    }
  }
  return seen;
}

function compareStableReproduction(actual,retained,historicalPins){
  const omitCheckoutTelemetry=({input_resolution,...result})=>result;
  // The retained report adds this exact review annotation; it is not raw output.
  const annotation='The Buu-Yao query is against target.base_geometry, the selected base footprint, not the raw positive source operand; its no-hit does not establish original source absence or no-repair eligibility.';
  assert.deepEqual(retained.limits,[actual.limits[0],annotation,...actual.limits.slice(1)]);
  assert.deepEqual(omitCheckoutTelemetry(actual),omitCheckoutTelemetry({...retained,limits:actual.limits}));
  assert.deepEqual(Object.keys(actual.input_resolution).sort(),['git_show_with_verified_worktree_fallbacks']);
  const allowed=new Set(historicalPins.map(pin=>pin.commit+':'+pin.path));
  for(const result of [actual,retained])for(const spec of result.input_resolution.git_show_with_verified_worktree_fallbacks)
    assert(allowed.has(spec),`unrecognized checkout fallback ${spec}`);
}

function packetProjection(partition,pins,reproduction){
  return {
    kind:'held-cell-exception-controls-fixture',
    status:'observations_only; no acceptance or repair credit',
    source_commits:[...new Set(usedSourcePins(pins).map(pin=>pin.commit))].sort(),
    contract_artifacts:[
      [pins.liberia.original_package_contract.reproduction.original_extractor_output.relative_output_name,
        pins.liberia.original_package_contract.reproduction.original_extractor_output.bytes,
        pins.liberia.original_package_contract.reproduction.original_extractor_output.sha256],
      [pins.liberia.original_package_contract.reproduction.published_derived_artifact.path,
        pins.liberia.original_package_contract.reproduction.published_derived_artifact.bytes,
        pins.liberia.original_package_contract.reproduction.published_derived_artifact.sha256]
    ],
    scope:{
      original_keys:partition.scope.original_keys,
      accepted:partition.scope.counts.accepted,
      pending_independent_review:partition.scope.counts.pending_independent_review,
      otherwise_resolved:partition.scope.counts.otherwise_resolved
    },
    cases:partition.all_cases.map(({country,key})=>[
      country,key.y,key.x,key.owner,key.source_id,key.original_physical_class,
      key.source_evidence_coverage_class,key.diagnostic_hold_reason
    ]),
    package_partitions:partition.scope.package_partitions.map(p=>[
      p.country,p.original_scope_cells,p.accepted_original_owner_cells,p.pending_held_original_cells,
      p.original_physical_class_counts,p.accepted_original_owner_class_counts,p.pending_held_original_class_counts
    ]),
    reproduction:{
      query_count:reproduction.query_count,
      all_retained_hit_lists_reproduced:reproduction.status==='all_retained_hit_lists_reproduced; observations_only' &&
        reproduction.matching_queries===reproduction.query_count && reproduction.queries.every(q=>q.exact_hit_list_matches_retained),
      first_query:[reproduction.queries[0].label,reproduction.queries[0].query.y,
        reproduction.queries[0].query.x_start,reproduction.queries[0].query.x_end_exclusive,
        reproduction.queries[0].query.owner,reproduction.queries[0].hits]
    }
  };
}

function verifyFixture(partition,pins,reproduction,fixture){
  assert.deepEqual(packetProjection(partition,pins,reproduction),fixture);
  for(const pin of usedSourcePins(pins)){
    assert.match(pin.commit,/^[0-9a-f]{40}$/);
    assert.match(pin.path,/^[A-Za-z0-9._/-]+$/);
    if(pin.bytes!==undefined)assert(Number.isSafeInteger(pin.bytes)&&pin.bytes>0);
    if(pin.git_blob_oid!==undefined)assert.match(pin.git_blob_oid,/^[0-9a-f]{40}$/);
    const hashes=[pin.sha256,pin.encoded_sha256,pin.decoded_sha256].filter(value=>value!==undefined);
    assert(hashes.length>0&&hashes.every(value=>/^[0-9a-f]{64}$/.test(value)));
  }
  assert.equal(pins.exact_scanner.bytes,50250);
  const reproducer=fs.readFileSync(packet+'reproduce-native-centres.mjs');
  const reproducerPin=pins.reproduction_outputs['reproduce-native-centres.mjs'];
  assert.equal(reproducer.length,reproducerPin.bytes);
  assert.equal(sha256(reproducer),reproducerPin.sha256);
  const original=pins.liberia.original_package_contract.reproduction.original_extractor_output;
  const derived=pins.liberia.original_package_contract.reproduction.published_derived_artifact;
  const derivedBytes=fs.readFileSync(packetFixture+derived.path);
  assert.equal(derivedBytes.length,derived.bytes);
  assert.equal(sha256(derivedBytes),derived.sha256);
  assert.notEqual(original.bytes,derived.bytes);
  assert.notEqual(original.sha256,derived.sha256);
  const scanner=fs.readFileSync(packet+'native-grid-pinned.mjs');
  assert.equal(scanner.length,pins.exact_scanner.bytes);
  assert.equal(sha256(scanner),pins.exact_scanner.sha256);
  assert.equal(gitBlobOid(scanner),pins.exact_scanner.git_blob_oid);
}

function tempDir(t){
  const directory=fs.mkdtempSync(path.join(os.tmpdir(),'held-cell-evidence-'));
  t.after(()=>fs.rmSync(directory,{recursive:true,force:true}));
  return directory;
}

function runNativeReproduction(script,output,env=process.env,repository=process.cwd()){
  return spawnSync(process.execPath,[script,repository,output],{
    encoding:'utf8',timeout:120000,maxBuffer:8*1024*1024,
    env:{...env,GIT_NO_LAZY_FETCH:'1',GIT_TERMINAL_PROMPT:'0'}
  });
}

test('current held-cell packet and actual 18-query native-center reproduction match the small fixture',t=>{
  const fixture=readJson(fixturePath),partition=readJson(packet+'disposition-partition.json');
  const pins=readJson(packet+'input-pins.json'),reproduction=readJson(packet+'reproduced-native-centre-queries.json');
  const historical=readJson(historicalPinsPath).inputs;
  assert.equal(historical.length,13);
  assert.deepEqual(historical,reproduceSourcePins(pins));
  const uniqueCommits=new Set(historical.map(pin=>pin.commit));
  assert.equal(uniqueCommits.size,7);
  const lbrLatitude=pins.liberia.native_latitudes;
  const pinnedLatitude=historical.find(pin=>pin.name==='Normative native latitude table');
  assert.equal(lbrLatitude.commit,pinnedLatitude.commit);
  assert.equal(lbrLatitude.path,pinnedLatitude.path);
  assert.equal(lbrLatitude.encoded_sha256,pinnedLatitude.sha256);
  assert.equal(lbrLatitude.decoded_sha256,pinnedLatitude.decoded_sha256);
  authenticateHistoricalInputs(historical);
  const outputPin=pins.reproduction_outputs['reproduced-native-centre-queries.json'];
  const outputBytes=fs.readFileSync(packetFixture+'reproduced-native-centre-queries.json');
  assert.equal(outputBytes.length,outputPin.bytes);
  assert.equal(sha256(outputBytes),outputPin.sha256);
  assert.equal(reproduction.status,'all_retained_hit_lists_reproduced; observations_only');
  assert.equal(reproduction.query_count,18);
  assert.equal(reproduction.matching_queries,18);
  assert(reproduction.queries.every(query=>query.exact_hit_list_matches_retained));
  const directory=tempDir(t),actualPath=path.join(directory,'actual-reproduction.json');
  const currentPacket=copyReproducerPacket(directory);
  execFileSync(process.execPath,[path.join(currentPacket,'reproduce-native-centres.mjs'),process.cwd(),actualPath],{
    encoding:'utf8',timeout:120000,maxBuffer:8*1024*1024,
    env:{...process.env,GIT_NO_LAZY_FETCH:'1',GIT_TERMINAL_PROMPT:'0'}
  });
  const actual=readJson(actualPath);
  compareStableReproduction(actual,reproduction,historical);
  const {commit,path:scannerPath,git_blob_oid,bytes,sha256:scannerSha}=pins.exact_scanner;
  assert.deepEqual(actual.scanner,{commit,path:scannerPath,git_blob_oid,bytes,sha256:scannerSha});
  const packetScanner=fs.readFileSync(packet+'native-grid-pinned.mjs');
  assert.equal(packetScanner.length,bytes);
  assert.equal(sha256(packetScanner),scannerSha);
  assert.equal(gitBlobOid(packetScanner),git_blob_oid);
  verifyFixture(partition,pins,actual,fixture);
});

test('packet controls reject altered owners, class/hold labels, partitions, contacts, labels, and source pins',()=>{
  const fixture=readJson(fixturePath),partition=readJson(packet+'disposition-partition.json');
  const pins=readJson(packet+'input-pins.json'),reproduction=readJson(packet+'reproduced-native-centre-queries.json');
  const cases=[
    p=>p.all_cases[0].key.owner++,
    p=>p.all_cases[0].key.original_physical_class='territorial_exclusion_cells',
    p=>p.all_cases[0].key.diagnostic_hold_reason='land',
    p=>p.scope.package_partitions[0].accepted_original_owner_cells++,
    p=>p.scope.package_partitions[1].original_physical_class_counts.land--,
    r=>r.queries[0].hits.push({y:126219,x:124938,kind:'interior'}),
    r=>r.queries[0].label='LBR original positive Buu-Yao target',
    p=>p.exact_scanner.sha256='0'.repeat(64),
    p=>p.liberia.source_evidence.commit='0'.repeat(40),
    p=>p.liberia.original_package_contract.reproduction.original_extractor_output.bytes=4802
  ];
  for(let i=0;i<cases.length;i++){
    const p=structuredClone(partition),pin=structuredClone(pins),r=structuredClone(reproduction);
    if(i<5)cases[i](p); else if(i<7)cases[i](r); else if(i>=7)cases[i](pin);
    assert.throws(()=>verifyFixture(p,pin,r,fixture));
  }
});

function copyReproducerPacket(directory){
  const copy=path.join(directory,'packet');fs.mkdirSync(copy);
  for(const name of ['reproduce-native-centres.mjs','native-grid-pinned.mjs','input-pins.json',
    'native-center-observations.json','liberia-causal-result.json'])
    fs.copyFileSync((name.endsWith('.mjs')?packet:packetFixture)+name,path.join(copy,name));
  return copy;
}

function gitBody(commit,path){
  return execFileSync('git',['show',`${commit}:${path}`],{
    encoding:'buffer',maxBuffer:64*1024*1024,
    env:{...process.env,GIT_NO_LAZY_FETCH:'1',GIT_TERMINAL_PROMPT:'0'}
  });
}

function putAt(root,relative,body){
  const destination=path.join(root,relative);fs.mkdirSync(path.dirname(destination),{recursive:true});
  fs.writeFileSync(destination,body);return destination;
}

function emptyRepo(directory){
  const root=path.join(directory,'empty-repo');fs.mkdirSync(root);
  execFileSync('git',['init','--quiet',root],{encoding:'utf8'});return root;
}

function mockScopedGitRun(pins){
  const objects=new Map(),calls=[],fetches=[];
  for(const pin of pins)objects.set(pin.git_blob_oid,pin.bytes);
  let commitsAvailable=false;
  return {calls,fetches,run(file,args,options={}){
    calls.push(args);
    if(args[0]==='cat-file'&&args[1]==='-e')return {status:commitsAvailable?0:1,stdout:'',stderr:''};
    if(args[0]==='fetch'){
      if(args.includes('--stdin'))throw Error('unexpected missing-body fetch');
      fetches.push(args.slice(args.indexOf('origin')+1));commitsAvailable=true;
      return {status:0,stdout:'',stderr:''};
    }
    if(args[0]==='ls-tree'){
      const commit=args[2],pathIndex=args.indexOf('--')+1,relative=args[pathIndex];
      const pin=pins.find(item=>item.commit===commit&&item.path===relative);
      return {status:0,stdout:`100644 blob ${pin.git_blob_oid}\t${relative}\0`,stderr:''};
    }
    if(args[0]==='cat-file'&&args[1]==='--batch-check=%(objectname) %(objecttype) %(objectsize)'){
      const rows=String(options.input).trimEnd().split('\n').map(oid=>`${oid} blob ${objects.get(oid)}`).join('\n')+'\n';
      return {status:0,stdout:rows,stderr:''};
    }
    throw Error('unexpected Git invocation: '+args.join(' '));
  }};
}

test('the actual reproducer refuses an altered expected contact before writing output',t=>{
  const directory=tempDir(t),copy=copyReproducerPacket(directory),observations=readJson(path.join(copy,'native-center-observations.json'));
  observations.liberia.physical_report_mapped_land_support.effect.hits.pop();
  fs.writeFileSync(path.join(copy,'native-center-observations.json'),JSON.stringify(observations,null,2)+'\n');
  const output=path.join(directory,'must-not-exist.json');
  const run=runNativeReproduction(path.join(copy,'reproduce-native-centres.mjs'),output);
  assert.equal(run.error,undefined,run.error?.message);
  assert.notEqual(run.status,0);
  assert.match(run.stderr,/recheck differs from retained expected hits/);
  assert.equal(fs.existsSync(output),false);
});

test('an empty repo uses the authenticated latitude fallback then rejects corrupted LBR evidence',t=>{
  const directory=tempDir(t),copy=copyReproducerPacket(directory),pins=readJson(path.join(copy,'input-pins.json'));
  const historical=readJson(historicalPinsPath).inputs;
  const latitude=historical.find(pin=>pin.name==='Normative native latitude table');
  const latitudeBody=gitBody(latitude.commit,latitude.path);
  assert.equal(latitudeBody.length,latitude.bytes);assert.equal(gitBlobOid(latitudeBody),latitude.git_blob_oid);
  assert.equal(sha256(latitudeBody),latitude.sha256);
  assert.equal(sha256(gunzipSync(latitudeBody)),latitude.decoded_sha256);
  const source=pins.liberia.source_evidence,sourceBody=gitBody(source.commit,source.path);
  assert.equal(sourceBody.length,source.bytes);assert.equal(gitBlobOid(sourceBody),source.git_blob_oid);assert.equal(sha256(sourceBody),source.sha256);
  const repo=emptyRepo(directory);putAt(repo,latitude.path,latitudeBody);
  const altered=Buffer.from(sourceBody);altered[0]^=1;putAt(repo,source.path,altered);
  const output=path.join(directory,'must-not-exist.json');
  const run=runNativeReproduction(path.join(copy,'reproduce-native-centres.mjs'),output,process.env,repo);
  assert.equal(run.error,undefined,run.error?.message);assert.notEqual(run.status,0);
  assert(run.stderr.includes(`${source.commit}:${source.path}: Git blob OID mismatch`),run.stderr);
  assert.equal(fs.existsSync(output),false);
});

test('an empty repo refuses corrupted normative latitude bytes after the working-tree fallback',t=>{
  const directory=tempDir(t),copy=copyReproducerPacket(directory),historical=readJson(historicalPinsPath).inputs;
  const latitude=historical.find(pin=>pin.name==='Normative native latitude table');
  const body=gitBody(latitude.commit,latitude.path);assert.equal(gitBlobOid(body),latitude.git_blob_oid);assert.equal(sha256(body),latitude.sha256);
  const decoded=gunzipSync(body);assert.equal(sha256(decoded),latitude.decoded_sha256);
  decoded[0]^=1;const corrupted=gzipSync(decoded);
  const repo=emptyRepo(directory);putAt(repo,latitude.path,corrupted);
  const output=path.join(directory,'must-not-exist.json');
  const run=runNativeReproduction(path.join(copy,'reproduce-native-centres.mjs'),output,process.env,repo);
  assert.equal(run.error,undefined,run.error?.message);assert.notEqual(run.status,0);
  assert.match(run.stderr,/Decoded native latitude table mismatch/);
  assert.equal(fs.existsSync(output),false);
});

test('the actual reproducer refuses to replace an existing output file',t=>{
  const directory=tempDir(t),output=path.join(directory,'existing-reproduction.json');
  const sentinel='preserve-existing-output\n';fs.writeFileSync(output,sentinel,{flag:'wx'});
  const currentPacket=copyReproducerPacket(directory);
  let error;
  try{
    execFileSync(process.execPath,[path.join(currentPacket,'reproduce-native-centres.mjs'),process.cwd(),output],{
      encoding:'utf8',timeout:120000,maxBuffer:8*1024*1024,
      env:{...process.env,GIT_NO_LAZY_FETCH:'1',GIT_TERMINAL_PROMPT:'0'}
    });
  }catch(caught){error=caught;}
  assert(error,'expected the exclusive output create to refuse replacement');
  assert.match(`${error.message}\n${error.stderr??''}`,/EEXIST|already exists/);
  assert.equal(fs.readFileSync(output,'utf8'),sentinel);
});

test('named held-cell consumer acquires only its thirteen pinned bodies and seven commits',()=>{
  const historical=readJson(historicalPinsPath).inputs,expected=new Set(historical.map(pin=>pin.commit));
  const mock=mockScopedGitRun(historical);
  const result=prepareNativeRegressionInputs('evidence',{
    files:['test/held-cell-exception-evidence-controls.test.mjs'],exists:()=>true,run:mock.run
  });
  assert.equal(result.applicable,true);
  assert.deepEqual(new Set(result.fetched),expected);
  assert.equal(mock.fetches.length,1);
  assert.deepEqual(new Set(mock.fetches[0]),expected);
  assert.equal(mock.calls.some(args=>args[0]==='fetch'&&args.includes('--stdin')),false);
});

test('unrelated named test roster performs zero native historical fetches',()=>{
  const calls=[];
  const result=prepareNativeRegressionInputs('evidence',{
    exists:()=>true,
    files:['test/compact-ownership.test.mjs'],run:(file,args)=>{calls.push(args);throw Error('unexpected Git call');}
  });
  assert.deepEqual(result,{applicable:false,fetched:[]});
  assert.deepEqual(calls,[]);
});

test('the pinned numerical scanner catches an exact interior contact and rejects a bad owner',()=>{
  const size=16,latitudes=nativeRowLatitudes(size),y=8,x=8,lon=360*(x+.5)/size-180,lat=latitudes[y];
  const polygon={type:'Polygon',coordinates:[[[lon-1,lat-1],[lon+1,lat-1],[lon+1,lat+1],[lon-1,lat+1],[lon-1,lat-1]]]};
  const request={size,latitudes,requestedRows:[{y,runs:[[x,x+1,26987]]}],nativePolygonIntervals};
  const result=witnessCellEffects(polygon,request);
  assert.deepEqual(result.hits,[{y,x,kind:'interior'}]);
  assert.equal(result.counts.cells,1);
  const outside={type:'Polygon',coordinates:[[[lon+10,lat-1],[lon+12,lat-1],[lon+12,lat+1],[lon+10,lat+1],[lon+10,lat-1]]]};
  assert.deepEqual(witnessCellEffects(outside,request).hits,[]);
  assert.throws(()=>witnessCellEffects(polygon,{...request,requestedRows:[{y,runs:[[x,x+1,0]]}]}),/Unordered\/overlapping\/invalid requested run/);
});


test('compact packet fixtures are exact current-tree operands with original custody',()=>{
  const provenance=readJson(packetFixture+'provenance.json');
  assert.equal(provenance.source_commit,'41db58b993f1b855c9ff3146520fb4e4c7e082a1');
  assert.equal(provenance.inputs.length,6);
  for(const pin of provenance.inputs){
    const body=fs.readFileSync(packetFixture+pin.fixture);
    assert.equal(body.length,pin.bytes);assert.equal(sha256(body),pin.sha256);assert.equal(gitBlobOid(body),pin.git_blob_oid);
    const row=execFileSync('git',['ls-tree','-z','HEAD','--',pin.path],{encoding:'utf8',env:{...process.env,GIT_NO_LAZY_FETCH:'1',GIT_TERMINAL_PROMPT:'0'}});
    assert.equal(row,`100644 blob ${pin.git_blob_oid}\t${pin.path}\0`);
  }
});


test('retained output annotation allowance rejects every unexpected annotation',()=>{
  const retained=readJson(packet+'reproduced-native-centre-queries.json'),historical=readJson(historicalPinsPath).inputs;
  const actual=structuredClone(retained);actual.limits.splice(1,1);
  compareStableReproduction(actual,retained,historical);
  for(const change of [r=>r.limits[1]+=' unexpected',r=>r.limits.push('extra annotation'),r=>r.limits.reverse()]){
    const altered=structuredClone(retained);change(altered);
    assert.throws(()=>compareStableReproduction(actual,altered,historical));
  }
});
