import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {nativePolygonIntervals, nativeRowLatitudes, witnessCellEffects} from '../coordination/engineering/original-held-cell-exceptions-20261018/native-grid-pinned.mjs';

const packet='coordination/engineering/original-held-cell-exceptions-20261018/';
const fixturePath='test/fixtures/held-cell-exceptions/current-packet-controls.json';
const readJson=name=>JSON.parse(fs.readFileSync(name,'utf8'));
const sha256=bytes=>createHash('sha256').update(bytes).digest('hex');
const gitBlobOid=bytes=>createHash('sha1').update(Buffer.from(`blob ${bytes.length}\0`)).update(bytes).digest('hex');

function usedSourcePins(pins){
  return [pins.liberia.source_evidence,pins.liberia.physical_whole_target_support,pins.liberia.native_latitudes,
    ...pins.liberia.original_negative_families.map(item=>item.part),pins.egypt.source_evidence,
    ...Object.values(pins.egypt.whole_original_family_payloads).flatMap(item=>item.parts)];
}

function packetProjection(partition,pins,reproduction){
  return {
    kind:'held-cell-exception-controls-fixture',
    status:'observations_only; no acceptance or repair credit',
    source_commits:[...new Set(usedSourcePins(pins).map(pin=>pin.commit))].sort(),
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
  const scanner=fs.readFileSync(packet+'native-grid-pinned.mjs');
  assert.equal(scanner.length,pins.exact_scanner.bytes);
  assert.equal(sha256(scanner),pins.exact_scanner.sha256);
  assert.equal(gitBlobOid(scanner),pins.exact_scanner.git_blob_oid);
}

test('current held-cell packet and retained native-center reproduction match the small fixture',()=>{
  const fixture=readJson(fixturePath),partition=readJson(packet+'disposition-partition.json');
  const pins=readJson(packet+'input-pins.json'),reproduction=readJson(packet+'reproduced-native-centre-queries.json');
  const outputPin=pins.reproduction_outputs['reproduced-native-centre-queries.json'];
  const outputBytes=fs.readFileSync(packet+'reproduced-native-centre-queries.json');
  assert.equal(outputBytes.length,outputPin.bytes);
  assert.equal(sha256(outputBytes),outputPin.sha256);
  assert.equal(reproduction.status,'all_retained_hit_lists_reproduced; observations_only');
  assert.equal(reproduction.query_count,18);
  assert.equal(reproduction.matching_queries,18);
  assert(reproduction.queries.every(query=>query.exact_hit_list_matches_retained));
  verifyFixture(partition,pins,reproduction,fixture);
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
  const outside={type:'Polygon',coordinates:[[[lon+10,lat-1],[lon+12,lat-1],[lon+12,lat+1],[lon+10,lat+1],[lon+10,lat-1]]]};
  assert.deepEqual(witnessCellEffects(outside,request).hits,[]);
  assert.throws(()=>witnessCellEffects(polygon,{...request,requestedRows:[{y,runs:[[x,x+1,0]]}]}),/Unordered\/overlapping\/invalid requested run/);
});
