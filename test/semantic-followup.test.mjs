import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { syncBuiltinESMExports } from 'node:module';
import { mkdtemp, mkdir, writeFile, readFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join, dirname } from 'node:path';
import { gzipSync } from 'node:zlib';
import { CONTINENTS, LEDGERS, hash, canonicalRawJson, rawEntries, validateFollowupSnapshot, validateSemanticFollowup } from '../scripts/validate-semantic-followup.mjs';

function fixture() {
  const hierarchy = [], locations = [], reports = [], frozen = {}, policies = {}, territories = [], policy_crosswalk = {};
  for (const [index, continent] of CONTINENTS.entries()) {
    const owner = `Owner ${continent}`, iso = `P${index}X`, id = `location:${index}`, members = [id];
    const tiers = ['continent', 'subcontinent', 'region', 'area', 'province'];
    const chain = tiers.map(level => `${continent}:${level}`);
    for (const [i, level] of tiers.entries()) hierarchy.push({ id: chain[i], name: i === 0 ? continent : `${continent} ${level}`, level, parent_id: i === 0 ? null : chain[i - 1] });
    const footprint = hash(canonicalRawJson('{"type":"Polygon","coordinates":[[[1.0,0.0],[2.0,0.0],[1.0,1.0],[1.0,0.0]]]}'));
    locations.push({ id, name: id, parent_id: chain.at(-1), owner, footprint_sha256: footprint });
    policies[iso] = { level: 'ADM2', role: 'District', reason: `Reviewed ${continent} reference scope` };
    territories.push({ owner }); policy_crosswalk[iso] = [owner];
    const groupRows = tiers.map((level, i) => ({ id: chain[i], name: i === 0 ? continent : `${continent} ${level}`, level, parent_id: i === 0 ? null : chain[i - 1], child_ids: [i === tiers.length - 1 ? id : chain[i + 1]], member_location_ids: members, members: 1, footprint_sha256: hash(JSON.stringify([[id, footprint]])), status: 'open' }));
    const row = { id, name: id, parent_id: chain.at(-1), chain, reference_owner: owner, footprint_sha256: footprint, status: 'open' };
    const report = { continent, semantic_complete: false, counts: { locations: 1, groups: 5 }, groups: groupRows, locations: [row], countries: [{ iso, reference_owner: owner, source_policy: policies[iso], location_ids: members, count: 1 }] };
    if (continent === 'Africa') {
      delete report.countries;
      report.source_policy_assessments = [{ iso, policy: policies[iso], location_ids: members }];
      report.reference_owner_crosswalk = [{ owner, location_ids: members }];
      row.parent_chain = [...chain].reverse(); delete row.chain;
      row.owner_reference = owner; delete row.reference_owner;
      row.geometry_sha256 = footprint; delete row.footprint_sha256;
      row.semantic_status = 'open'; delete row.status;
      for (const g of groupRows) { g.children = g.child_ids; delete g.child_ids; g.membership_sha256 = hash(JSON.stringify(members)); g.branch_semantic_status = 'open'; delete g.status; }
    } else if (['Asia', 'Oceania'].includes(continent)) {
      delete report.countries; report.territory_matrix = [{ reference_owner: owner, location_count: 1, policy_profiles: { [iso]: policies[iso] } }];
      row.province_id = row.parent_id; delete row.parent_id; delete row.chain;
    }
    reports.push(report); frozen[continent] = { inventory: { location_ids: [...members], group_ids: [...chain] } };
  }
  return { hierarchy, locations, reports, worldReview: { territories, policy_crosswalk }, policies, frozen, migrations: { retiredLocations: new Set(), createdLocations: new Set(), retiredGroups: new Set(), createdGroups: new Set() }, closure: { locations: new Map(locations.map(r => [r.id, { status: 'open', footprint_sha256: r.footprint_sha256 }])), groups: new Map(hierarchy.map(r => [r.id, { status: 'open' }])), policy_crosswalk }, expectedCounts: { locations: 6, groups: 30, reference_owner_groups: 6, policy_profiles: 6 } };
}

async function fixtureRepository(t,{twoParts=false}={}) {
  const root = await mkdtemp(join(tmpdir(), 'worldatlas-semantic-followup-')); t.after(() => rm(root, { recursive: true, force: true }));
  const data = fixture();
  const put = async (path, value) => { const p = join(root, path); await mkdir(dirname(p), { recursive: true }); const raw = typeof value === 'string' ? value : JSON.stringify(value); await writeFile(p, path.endsWith('.gz') ? gzipSync(raw, { mtime: 0 }) : raw); };
  const geometryRaw = '{"type":"Polygon","coordinates":[[[1.0,0.0],[2.0,0.0],[1.0,1.0],[1.0,0.0]]]}';
  const features = data.locations.map(r => `{"id":${JSON.stringify(r.id)},"properties":${JSON.stringify({ id: r.id, name: r.name, parent_id: r.parent_id, reference_owner: r.owner, metadata: {} })},"geometry":${geometryRaw}}`);
  const partNames=twoParts?['geography/part-0.json','geography/part-1.json']:['geography/part-0.json'];
  for(const [i,name]of partNames.entries())await put('data/'+name, `{"type":"FeatureCollection","features":[${(twoParts?features.slice(i*3,i*3+3):features).join(',')}]}`);
  await put('data/hierarchy.json', data.hierarchy); await put('data/world-index.json', { parts: partNames });
  await put('data/world-review.json', data.worldReview); await put('data/location-policy.json', { countries: data.policies }); await put('data/administrative-sources.json', {});
  const input_sha256 = Object.fromEntries(await Promise.all(['data/hierarchy.json', 'data/world-index.json', ...partNames.map(name=>'data/'+name)].map(async path => [path, hash(await readFile(join(root, path)))])));
  const groupHashes = new Map(data.reports.flatMap(r => r.groups.map(g => [g.id, g.footprint_sha256])));
  await put('data/global-semantic-closure.json.gz', { input_sha256: Object.fromEntries(Object.entries(input_sha256).map(([path, digest]) => [path.slice(5), digest])), locations: data.locations.map(r => ({ id: r.id, status: 'open', footprint_sha256: r.footprint_sha256 })), groups: data.hierarchy.map(r => ({ id: r.id, status: 'open', footprint_sha256: groupHashes.get(r.id) })), policy_crosswalk: data.worldReview.policy_crosswalk });
  for (const report of data.reports) { await put(LEDGERS[report.continent], { ...report, input_sha256 }); await put(`data/geographic-decisions/${report.continent.toLowerCase().replaceAll(' ', '-')}.json`, data.frozen[report.continent]); }
  await put('data/geographic-decision-migration.json.gz', { retired_units: [], group_changes: [] });
  await put('data/macro-boundary-migration.json.gz', { retired_units: [], group_changes: [], location_chain_crosswalk: [] });
  await put('data/geographic-repair-evidence/migration-receipt.json.gz', { removed_ids: [], added_ids: [], retired_units: [], archives: [] });
  return { root, expectedCounts: data.expectedCounts };
}

test('six schema variants partition all IDs and preserve explicit semantic openness', () => {
  const result = validateFollowupSnapshot(fixture());
  assert.deepEqual(result.counts, { locations: 6, groups: 30, reference_owner_groups: 6, policy_profiles: 6 });
  assert.equal(result.semantic_complete, false); assert.equal(result.approvals_created, 0); assert.equal(result.corrections_installed, 0);
  assert.equal(result.continents.length, 6);
});

test('raw hashing preserves float lexemes, signed zero, exponent precision and Unicode policy', () => {
  const raw = ' { "z": [1.0, -0.0, 1e+20], "a": "\\u5317\\u4eac" } ';
  assert.equal(canonicalRawJson(raw), '{"a":"北京","z":[1.0,-0.0,1e+20]}');
  assert.equal(canonicalRawJson(raw, { ascii: true }), '{"a":"\\u5317\\u4eac","z":[1.0,-0.0,1e+20]}');
  assert.notEqual(hash(canonicalRawJson(raw)), hash(JSON.stringify(JSON.parse(raw))));
  assert.throws(() => canonicalRawJson('{"x":1,"x":2}'), /Duplicate/);
  assert.deepEqual(rawEntries('[{"geometry":{"type":"Polygon","coordinates":[1.0]}},null]').map(([, r]) => r), ['{"geometry":{"type":"Polygon","coordinates":[1.0]}}', 'null']);
});

test('duplicate reports, stale polygons and incomplete parent chains fail', () => {
  let data = fixture(); data.reports[1].continent = 'Africa'; assert.throws(() => validateFollowupSnapshot(data), /duplicate IDs/i);
  data = fixture(); data.reports[0].locations[0].geometry_sha256 = '0'.repeat(64); assert.throws(() => validateFollowupSnapshot(data), /footprint/);
  data = fixture(); data.locations[0].parent_id = 'Africa:area'; assert.throws(() => validateFollowupSnapshot(data), /Incomplete/);
});

test('parent membership cannot overlap, omit a child or claim unsupported approval', () => {
  let data = fixture(); data.reports[0].groups[0].children = []; assert.throws(() => validateFollowupSnapshot(data), /Direct children/);
  data = fixture(); data.reports[1].groups[0].member_location_ids.push('location:0'); assert.throws(() => validateFollowupSnapshot(data), /Member locations/);
  data = fixture(); data.reports[0].locations[0].semantic_status = 'supported'; assert.throws(() => validateFollowupSnapshot(data), /Unsubstantiated/);
  data = fixture(); data.reports[0].semantic_complete = true; assert.throws(() => validateFollowupSnapshot(data), /unfinished semantic/);
});

test('owner labels and source policy identities are exhaustively crosswalked', () => {
  let data = fixture(); data.reports[0].reference_owner_crosswalk[0].owner = 'Another owner'; assert.throws(() => validateFollowupSnapshot(data), /owner crosswalk/);
  data = fixture(); data.reports[0].source_policy_assessments[0].policy = { role: 'Village' }; assert.throws(() => validateFollowupSnapshot(data), /Stale or unexpected policy/);
  data = fixture(); data.worldReview.policy_crosswalk.P0X = []; assert.throws(() => validateFollowupSnapshot(data), /Invalid canonical/);
});

test('removed/new IDs require archival receipts and migration is never inferred', () => {
  let data = fixture(); data.frozen.Africa.inventory.location_ids.push('retired:old'); assert.throws(() => validateFollowupSnapshot(data), /retirement receipt/);
  data.migrations.retiredLocations.add('retired:old'); assert.equal(validateFollowupSnapshot(data).prior_current_identity_accounting.retired_location_ids[0], 'retired:old');
  data = fixture(); data.frozen.Africa.inventory.group_ids.push('retired:province'); assert.throws(() => validateFollowupSnapshot(data), /retirement archive/);
  data = fixture(); data.frozen.Africa.inventory.group_ids.pop(); assert.throws(() => validateFollowupSnapshot(data), /creation receipt/);
});

test('fresh-clone reader verifies every file pin without Python or cache access', async t => {
  const { root, expectedCounts } = await fixtureRepository(t); const result = await validateSemanticFollowup(root, { expectedCounts });
  assert.equal(result.counts.locations, 6); assert.equal(result.source_verification.external_response_bytes_refetched, 0);
  assert.equal(result.full_ledgers_are_deployment_assets, false); assert.equal(Object.keys(result.report_sha256).length, 6);
});

test('changed source bytes or missing continent ledger reject the read-only snapshot', async t => {
  const { root, expectedCounts } = await fixtureRepository(t);
  await writeFile(join(root, 'data/hierarchy.json'), `${await readFile(join(root, 'data/hierarchy.json'), 'utf8')}\n`);
  await assert.rejects(validateSemanticFollowup(root, { expectedCounts }), /Stale source hash/);
  const second = await fixtureRepository(t); await rm(join(second.root, LEDGERS['South America']));
  await assert.rejects(validateSemanticFollowup(second.root, { expectedCounts: second.expectedCounts }), /Missing continent follow-up/);
});

test('a renamed complete ledger cannot leak into website deployment assets', async t => {
  const { root, expectedCounts } = await fixtureRepository(t);
  await mkdir(join(root, 'dist/client'), { recursive: true });
  await writeFile(join(root, 'dist/client/renamed-evidence.bin'), await readFile(join(root, LEDGERS.Africa)));
  await assert.rejects(validateSemanticFollowup(root, { expectedCounts }), /Full semantic follow-up ledger is a deployment asset/);
});

test('source-parent measurements require current footprint context and actual members', async t => {
  const { root, expectedCounts } = await fixtureRepository(t), path = join(root, LEDGERS.Africa);
  const { gunzipSync } = await import('node:zlib');
  const report = JSON.parse(gunzipSync(await readFile(path)));
  report.source_evidence = { original_parent_geometry_diagnostics: { 'Africa:continent': { current_group_footprint_sha256: report.groups[0].footprint_sha256, original_parent_candidates: [{ member_matches: [{ id: 'location:0' }] }] } } };
  await writeFile(path, gzipSync(JSON.stringify(report), { mtime: 0 }));
  assert.equal((await validateSemanticFollowup(root, { expectedCounts })).source_verification.diagnostic_current_footprint_contexts_verified, 1);
  report.source_evidence.original_parent_geometry_diagnostics['Africa:continent'].current_group_footprint_sha256 = '0'.repeat(64);
  await writeFile(path, gzipSync(JSON.stringify(report), { mtime: 0 }));
  await assert.rejects(validateSemanticFollowup(root, { expectedCounts }), /Stale original-parent diagnostic context/);
  report.source_evidence.original_parent_geometry_diagnostics['Africa:continent'].current_group_footprint_sha256 = report.groups[0].footprint_sha256;
  report.source_evidence.original_parent_geometry_diagnostics['Africa:continent'].original_parent_candidates[0].member_matches[0].id = 'location:1';
  await writeFile(path, gzipSync(JSON.stringify(report), { mtime: 0 }));
  await assert.rejects(validateSemanticFollowup(root, { expectedCounts }), /references a nonmember/);
});

test('actual semantic validation checks complete current member fields and literal compact shards',async t=>{
 const {projectCurrentMemberEdges}=await import('../scripts/prepare-macro-review-projection.mjs');
 const {footprintHash}=await import('../scripts/check-prepared.mjs');
 const {root,expectedCounts}=await fixtureRepository(t,{twoParts:true}),indexRaw=await readFile(join(root,'data/world-index.json'));
 const parts=await Promise.all(JSON.parse(indexRaw).parts.map(async name=>({path:'data/'+name,mode:'100644',raw:await readFile(join(root,'data/'+name))}))),features=parts.flatMap(part=>JSON.parse(part.raw).features);
 // This fixture's existing feature shape intentionally omits the optional
 // GeoJSON Feature tag. The projection must preserve that accepted input.
 const extracted=projectCurrentMemberEdges({indexRaw,parts}),hierarchyRaw=await readFile(join(root,'data/hierarchy.json')),hierarchy=JSON.parse(hierarchyRaw),groups=new Map(hierarchy.map(r=>[r.id,r]));
 const currentPins={hierarchy_sha256:hash(hierarchyRaw),location_index_sha256:hash(indexRaw),footprints_sha256:footprintHash(features)};
 const locations=features.map(feature=>{const p=feature.properties,chain=[];for(let id=p.parent_id;id!==null;id=groups.get(id).parent_id)chain.push(id);return{id:feature.id,name:p.name,parent_id:p.parent_id,owner:p.reference_owner,parent_chain:chain,status:'open',semantic_status:'open'};});
 const projection={version:1,kind:'current-membership-projection',semantic_complete:false,regional_interiors_approved:false,historical_claims_transferred:false,geometry_changes:0,current_pins:currentPins,counts:{locations:6,groups:30,...Object.fromEntries(['continent','subcontinent','region','area','province'].map(tier=>[tier,6]))},locations,groups:hierarchy.map(row=>({...row,member_location_ids:locations.filter(l=>l.parent_chain.includes(row.id)).map(l=>l.id),branch_semantic_status:'open'})),archived_predecessors:[],crosswalks:[],member_edges:extracted.member_edges};
 const dashboard={member_edges:extracted.member_edges,current_pins:currentPins,locations:6,location_parts:['macro-foundation/world-review-locations-0.json.gz']};
 const directory=join(root,'data/macro-foundation');await mkdir(directory,{recursive:true});
 const save=async()=>{await writeFile(join(directory,'current-membership-projection.json.gz'),gzipSync(JSON.stringify(projection)));await writeFile(join(directory,'world-review-projection.json'),JSON.stringify(dashboard));await writeFile(join(directory,'world-review-locations-0.json.gz'),gzipSync(JSON.stringify(projection.locations)));};
 await save();const parse=JSON.parse,counts=new Map(parts.map(part=>[part.raw.toString(),0]));let result;
 const reads=[],paths=new Map(parts.map(part=>[join(root,part.path),part.path]));
 const bodyPaths=new Map(parts.map(part=>[part.raw.toString(),part.path]));
 const asyncRead=fs.promises.readFile,syncRead=fs.readFileSync;
 const observe=file=>{if(paths.has(String(file)))reads.push(['read',paths.get(String(file))]);};
 fs.promises.readFile=async function(file,...args){observe(file);return asyncRead.call(this,file,...args);};
 fs.readFileSync=function(file,...args){observe(file);return syncRead.call(this,file,...args);};
 syncBuiltinESMExports();
 JSON.parse=function(raw,...args){if(Buffer.isBuffer(raw)&&counts.has(raw.toString())){
  counts.set(raw.toString(),counts.get(raw.toString())+1);reads.push(['parse',bodyPaths.get(raw.toString())]);
 }return parse(raw,...args);};
 try{result=await validateSemanticFollowup(root,{expectedCounts});}finally{
  JSON.parse=parse;fs.promises.readFile=asyncRead;fs.readFileSync=syncRead;syncBuiltinESMExports();
 }
 assert.deepEqual([...counts.values()],[1,1],'each indexed current part decoded once; existing retained-baseline text parsing is separate');
 const firstParse=reads.findIndex(([operation])=>operation==='parse');
 assert.deepEqual(reads.slice(firstParse-1,firstParse+3),parts.flatMap(part=>[['read',part.path],['parse',part.path]]),
  'current canonical raw bodies are read and consumed one at a time, not accumulated before decoding');
 assert.equal(result.current_member_edges.validated,true);assert.equal(result.current_member_edges.native_absence_admission,false);assert.equal(Object.hasOwn(result.current_member_edges,'features'),false);
 projection.locations[0].source_member_ids=['forged'];await save();await assert.rejects(validateSemanticFollowup(root,{expectedCounts}),/member property/);
 delete projection.locations[0].source_member_ids;await save();const compact=structuredClone(projection.locations);compact[0].source_member_ids=null;await writeFile(join(directory,'world-review-locations-0.json.gz'),gzipSync(JSON.stringify(compact)));await assert.rejects(validateSemanticFollowup(root,{expectedCounts}),/member property/);
});
