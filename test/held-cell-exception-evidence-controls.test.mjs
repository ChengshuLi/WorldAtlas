import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {nativePolygonIntervals, nativeRowLatitudes, witnessCellEffects} from '../coordination/engineering/original-held-cell-exceptions-20261018/native-grid-pinned.mjs';

const packet='coordination/engineering/original-held-cell-exceptions-20261018/';
const fixturePath='test/fixtures/held-cell-exceptions/current-packet-controls.json';
const readJson=name=>JSON.parse(fs.readFileSync(name,'utf8'));
const sha256=bytes=>createHash('sha256').update(bytes).digest('hex');
const gitBlobOid=bytes=>createHash('sha1').update(Buffer.from(`blob ${bytes.length}\0`)).update(bytes).digest('hex');

function packetProjection(partition,pins,reproduction){
  return {
    kind:'held-cell-exception-controls-fixture',
    status:'observations_only; no acceptance or repair credit',
    source_commits:[...new Set([pins.liberia.source_evidence,pins.liberia.physical_whole_target_support,
      pins.liberia.native_latitudes,...pins.liberia.original_negative_families.map(item=>item.part),
      pins.egypt.source_evidence,...Object.values(pins.egypt.whole_original_family_payloads).flatMap(item=>item.parts)
    ].map(pin=>pin.commit))].sort(),
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
  assert.equal(pins.exact_scanner.bytes,50250);
  const reproducer=fs.readFileSync(packet+'reproduce-native-centres.mjs');
  const reproducerPin=pins.reproduction_outputs['reproduce-native-centres.mjs'];
  assert.equal(reproducer.length,reproducerPin.bytes);
  assert.equal(sha256(reproducer),reproducerPin.sha256);
  const scanner=fs.readFileSync(packet+'native-grid-pinned.mjs');
  assert.equal(scanner.length,pins.exact_scanner.bytes);
  assert.equal(sha256(scanner),pins.exact_scanner.sha256);
  assert.equal(gitBlobOid(scanner),pins.exact_scanner.git_blob_oid);
}

function tempOutput(t){
  const dir=fs.mkdtempSync(path.join(os.tmpdir(),'held-cell-evidence-'));
  t.after(()=>fs.rmSync(dir,{recursive:true,force:true}));
  return path.join(dir,'reproduced.json');
}

function runNativeReproduction(output){
  return spawnSync(process.execPath,['-B',packet+'reproduce-native-centres.mjs',process.cwd(),output],{
    encoding:'utf8',timeout:120000,maxBuffer:8*1024*1024,
    env:{...process.env,GIT_NO_LAZY_FETCH:'1',GIT_TERMINAL_PROMPT:'0'}
  });
}

test('current held-cell packet and exact native-center reproduction match the small fixture',t=>{
  const fixture=readJson(fixturePath),partition=readJson(packet+'disposition-partition.json');
  const pins=readJson(packet+'input-pins.json'),retained=readJson(packet+'reproduced-native-centre-queries.json');
  const output=tempOutput(t),run=runNativeReproduction(output);
  assert.equal(run.error,undefined,run.error?.message);
  assert.equal(run.status,0,run.stderr);
  const actual=readJson(output);
  assert.deepEqual(actual.queries,retained.queries);
  const {commit,path:scannerPath,git_blob_oid,bytes,sha256:scannerSha}=pins.exact_scanner;
  assert.deepEqual(actual.scanner,{commit,path:scannerPath,git_blob_oid,bytes,sha256:scannerSha});
  assert.equal(actual.query_count,18);
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
    p=>p.liberia.source_evidence.commit='0'.repeat(40)
  ];
  for(let i=0;i<cases.length;i++){
    const p=structuredClone(partition),pin=structuredClone(pins),r=structuredClone(reproduction);
    if(i<5)cases[i](p); else if(i<7)cases[i](r); else if(i===7)cases[i](pin); else cases[i](pin);
    assert.throws(()=>verifyFixture(p,pin,r,fixture));
  }
});

test('the pinned numerical scanner catches an exact interior contact and rejects a bad owner',()=>{
  const size=16,latitudes=nativeRowLatitudes(size),y=8,x=8,lon=360*(x+.5)/size-180,lat=latitudes[y];
  const polygon={type:'Polygon',coordinates:[[[lon-1,lat-1],[lon+1,lat-1],[lon+1,lat+1],[lon-1,lat+1],[lon-1,lat-1]]]};
  const request={size,latitudes,requestedRows:[{y,runs:[[x,x+1,26987]]}],nativePolygonIntervals};
  const result=witnessCellEffects(polygon,request);
  assert.deepEqual(result.hits,[{y,x,kind:'interior'}]);
  assert.equal(result.counts.cells,1);
  assert.throws(()=>witnessCellEffects(polygon,{...request,requestedRows:[{y,runs:[[x,x+1,0]]}]}),/Unordered\/overlapping\/invalid requested run/);
});
