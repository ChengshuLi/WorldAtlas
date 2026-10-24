import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {supportedInputs, jsonBytes, digest} from '../scripts/prepare-delivery-handoff.mjs';

function fixture() {
  const files = new Map(), commit = 'a'.repeat(40), puts = [];
  const put = (path, value) => {
    const raw = jsonBytes(value), pin = {commit, path, mode: '100644', git_blob_oid: 'b'.repeat(40), bytes: raw.length, sha256: digest(raw)};
    files.set(path, {raw, pin}); puts.push(pin); return pin;
  };
  const read = pin => { const file = files.get(pin.path); assert.deepEqual(pin, file.pin); return file.raw; };
  const reader = {pin: (c, p) => {assert.equal(c, commit); return files.get(p).pin;}, read, json: p => JSON.parse(read(p))};
  const native_contract = {size: 262166};
  const cover = [{y: 10, runs: [[1, 2, 'mapped_land_support'], [2, 4, 'mapped_inland_water_support']]}];
  const target = (id, pixelIndex) => ({id, pixelIndex, base_geometry: {whole: id}, source_members: ['a', 'b'],
    territorial_exclusions: [{whole_negative: 1}, {source_id: 'foreign', feature_ordinal: 3, geometry_sha256: 'f'.repeat(64)}],
    coverage_rows: pixelIndex === 1 ? cover : [{y: 10, runs: [[6, 8, 'mapped_land_support']]}]});
  const source = {version: 1, kind: 'source-target-native-evidence-v1', native_contract, targets: [target('a', 1), target('b', 1), target('c', 2)],
    families: [{whole: 'original'}], physical_input: {whole: 'all physical members'}, negative_sources: [{whole: 'complete foreign family'}]};
  const pins = {source_evidence: put('source.json', source), native_patch: put('patch.json', {rows: [{y: 10, runs: [[1, 4, 1], [6, 8, 2]]}]})};
  const diagnostic = {version: 1, kind: 'source-target-native-diagnostic-v1', native_contract, original_pins: pins,
    rule_sha256: digest(jsonBytes({version: 1, kind: 'source-target-native-rule-v1', ...pins})),
    requested_rows: [{y: 10, runs: [[1, 4, 1], [6, 8, 2]]}], supported_rows: [{y: 10, runs: [[1, 3, 1]]}],
    held_rows: [{y: 10, runs: [[3, 4, 1], [6, 8, 2]]}],
    decision_rows: [{y: 10, runs: [[1, 3, 1, 'assigned_cells'], [3, 4, 1, 'boundary_cells'], [6, 8, 2, 'territorial_exclusion_cells']]}],
    requested_cells: 5, supported_cells: 2, held_cells: 3};
  put('diagnostic.json', diagnostic);
  const original = {rows: [{y: 10, runs: [[1, 4, 1], [6, 8, 2], [10, 12, 3]]}]}; put('original.json', original);
  const prior = {rows: [{y: 10, runs: [[2, 4, 1, 'prior-fitness'], [10, 12, 3, 'prior-identity']]}],
    assessments: [{original: 'whole retained prior assessment', unresolved: true}]}; put('prior.json', prior);
  const config = {version: 1, diagnostic: {commit, path: 'diagnostic.json'}, original_patch: {commit, path: 'original.json'},
    prior_holds: {commit, path: 'prior.json'}};
  const run = () => Object.fromEntries(Object.entries(supportedInputs(config, reader)).map(([p, raw]) => [p, JSON.parse(raw)]));
  return {put, files, reader, source, pins, diagnostic, original, prior, config, run};
}

test('supported-inputs joins full original, native and prior holds without changing whole operands', () => {
  const f = fixture(), before = structuredClone(f.source), result = f.run();
  assert.deepEqual(result['native-patch.json'], {rows: [{y: 10, runs: [[1, 2, 1]]}]});
  assert.deepEqual(result['held-original.json'], {rows: [{y: 10, runs: [[2, 3, 1, 'prior-fitness'], [3, 4, 1, 'boundary_cells'],
    [6, 8, 2, 'territorial_exclusion_cells'], [10, 12, 3, 'prior-identity']]}]});
  const expected = {...before, targets: before.targets.slice(0, 2).map(t => ({...t, coverage_rows: [{y: 10, runs: [[1, 2, 'mapped_land_support']]}]}))};
  assert.deepEqual(result['source-evidence.json'], expected);
  assert.deepEqual(f.source, before);
  const counts = result['original-scope-partition.json'];
  assert.equal(counts.original_cells, 7); assert.equal(counts.supported_cells, 1); assert.equal(counts.held_cells, 6);
  assert.equal(counts.prior_held_cells, 4); assert.equal(counts.prior_already_native_held_cells, 1);
  assert.deepEqual(counts.owners, [{owner: 1, original_cells: 3, supported_cells: 1, held_cells: 2},
    {owner: 2, original_cells: 2, supported_cells: 0, held_cells: 2}, {owner: 3, original_cells: 2, supported_cells: 0, held_cells: 2}]);
  assert.deepEqual(f.reader.json(counts.prior_holds), f.prior, 'complete prior assessments remain pinned');
  assert.deepEqual(counts.original_inputs, f.pins);
  assert(!Object.keys(result).some(name => /authority|proof|ledger/.test(name)));
});

test('supported-inputs defaults to complete diagnostic scope and preserves class boundaries', () => {
  const f = fixture(); delete f.config.original_patch; delete f.config.prior_holds;
  const result = f.run();
  assert.deepEqual(result['native-patch.json'].rows, f.diagnostic.supported_rows);
  assert.deepEqual(result['source-evidence.json'].targets[0].coverage_rows,
    [{y: 10, runs: [[1, 2, 'mapped_land_support'], [2, 3, 'mapped_inland_water_support']]}]);
  assert.equal(result['source-evidence.json'].targets.length, 2, 'both original member atoms survive');
});

test('supported-inputs preserves absent masks and accounts for an entirely held scope', () => {
  const f = fixture(); delete f.config.original_patch;
  for (const t of f.source.targets) delete t.coverage_rows;
  f.pins.source_evidence = f.put('source.json', f.source);
  f.diagnostic.rule_sha256 = digest(jsonBytes({version: 1, kind: 'source-target-native-rule-v1', ...f.pins}));
  f.put('diagnostic.json', f.diagnostic);
  f.put('prior.json', {rows: [{y: 10, runs: [[1, 4, 1, 'prior'], [6, 8, 2, 'prior']]}]});
  const result = f.run(); assert.deepEqual(result['native-patch.json'].rows, []);
  assert.deepEqual(result['source-evidence.json'].targets, []);
  assert.equal(result['original-scope-partition.json'].held_cells, 5);
  delete f.config.prior_holds;
  assert(f.run()['source-evidence.json'].targets.every(t => !('coverage_rows' in t)));
});

const changes = {
  'missing diagnostic row': f => f.diagnostic.decision_rows = [],
  'duplicate diagnostic row': f => f.diagnostic.decision_rows.push(f.diagnostic.decision_rows[0]),
  'overlapping diagnostic spans': f => f.diagnostic.decision_rows[0].runs[1][0] = 2,
  'altered native reason': f => f.diagnostic.decision_rows[0].runs[0][3] = 'foreign',
  'wrong original owner': f => f.original.rows[0].runs[0][2] = 9,
  'omitted original owner': f => f.original.rows[0].runs.pop(),
  'extra unaccounted original key': f => f.original.rows[0].runs.push([15, 16, 4]),
  'prior key outside original': f => f.prior.rows[0].runs.push([15, 16, 4, 'foreign']),
  'prior assignment claim': f => f.prior.rows[0].runs[0][3] = 'assigned_cells',
  'duplicate prior key': f => f.prior.rows[0].runs[1] = f.prior.rows[0].runs[0],
  'false diagnostic count': f => f.diagnostic.supported_cells++,
  'wrong rule binding': f => f.diagnostic.rule_sha256 = '0'.repeat(64),
  'wrong native extent': f => f.diagnostic.native_contract = {size: 262165},
  'wrong requested patch': f => f.diagnostic.requested_rows[0].runs[0][1] = 3,
  'out of grid': f => f.original.rows[0].runs.push([262166, 262167, 1]),
  'negative row': f => f.original.rows[0].y = -1,
};
for (const [name, change] of Object.entries(changes)) test('supported-inputs refuses ' + name, () => {
  const f = fixture(); change(f); f.put('diagnostic.json', f.diagnostic); f.put('original.json', f.original); f.put('prior.json', f.prior);
  assert.throws(f.run);
});

for (const [name, change] of Object.entries({
  'missing member owner': s => s.targets = s.targets.slice(0, 2),
  'duplicate member id': s => s.targets[1].id = s.targets[0].id,
  'conflicting sibling classes': s => s.targets[1].coverage_rows = [{y: 10, runs: [[1, 4, 'mapped_land_support']]}],
  'missing class coverage': s => s.targets[0].coverage_rows[0].runs.pop(),
  'invented class': s => s.targets[0].coverage_rows[0].runs[0][2] = 'invented',
  'extra class cell': s => s.targets[0].coverage_rows[0].runs[0][0] = 0,
})) test('supported-inputs refuses ' + name + ' with refreshed source binding', () => {
  const f = fixture(); change(f.source); f.pins.source_evidence = f.put('source.json', f.source);
  f.diagnostic.rule_sha256 = digest(jsonBytes({version: 1, kind: 'source-target-native-rule-v1', ...f.pins}));
  f.put('diagnostic.json', f.diagnostic); assert.throws(f.run);
});

test('supported-inputs authenticates original source bytes rather than accepting a supplied replacement', () => {
  const f = fixture(); f.put('source.json', {...f.source, families: []}); assert.throws(f.run);
  const other = fixture(); other.config.source_evidence = other.config.diagnostic; assert.throws(other.run);
});

test('supported-inputs operates on full-width intervals without expanding native cells', () => {
  const f=fixture();delete f.config.original_patch;delete f.config.prior_holds;
  const requested=[{y:262165,runs:[[0,262166,1]]}],supported=[{y:262165,runs:[[0,262165,1]]}],held=[{y:262165,runs:[[262165,262166,1]]}];
  f.source.targets=f.source.targets.slice(0,2).map(t=>({...t,coverage_rows:[{y:262165,runs:[[0,262166,'mapped_land_support']]}]}));
  f.pins.source_evidence=f.put('source.json',f.source);f.pins.native_patch=f.put('patch.json',{rows:requested});
  Object.assign(f.diagnostic,{requested_rows:requested,supported_rows:supported,held_rows:held,
    decision_rows:[{y:262165,runs:[[0,262165,1,'assigned_cells'],[262165,262166,1,'boundary_cells']]}],
    requested_cells:262166,supported_cells:262165,held_cells:1,
    rule_sha256:digest(jsonBytes({version:1,kind:'source-target-native-rule-v1',...f.pins}))});
  f.put('diagnostic.json',f.diagnostic);
  const result=f.run();assert.deepEqual(result['native-patch.json'],{rows:supported});
  assert.equal(result['original-scope-partition.json'].original_cells,262166);
  assert.deepEqual(result['source-evidence.json'].targets[1].coverage_rows,[{y:262165,runs:[[0,262165,'mapped_land_support']]}]);
});

// Real immutable Git readers and the existing canonical final-bank loader own
// acceptance input authentication; no caller-supplied ownership map is trusted.
async function acceptedFixture(t) {
  const {trustedFixture} = await import('./fixtures/selected-checkpoint.mjs');
  const {initialFinalBank} = await import('./fixtures/final-bank.mjs');
  const {pinReader} = await import('../scripts/prepare-delivery-handoff.mjs');
  const f = await trustedFixture(t, {nativeAppend:true, finalBank:true});
  await initialFinalBank(f);
  const selectorCommit = f.git('rev-parse','HEAD').toString().trim();
  const contract = Object.fromEntries(['size','coordinateBits','method','native_latitudes','hierarchy_sha256','original_assets'].map(k=>[k,f.manifest[k]]));
  async function run({supported=[[2,4,1]], held=[[4,5,1]], mutateSource=()=>{}, mutateDiagnostic=()=>{}, mutateSelector=()=>{}, mutateReader=()=>{}, priorHoldRuns, accepted=true}={}) {
    f.git('reset','--hard',selectorCommit);
    const requested=[...supported,...held].sort((a,b)=>a[0]-b[0]);
    const source={version:1,kind:'source-target-native-evidence-v1',native_contract:contract,base_reference:f.envelope.base_reference,
      families:[{original:'complete retained source'}],negative_sources:[{original:'complete foreign family'}],
      targets:[{id:'member-a',target_id:'A',pixelIndex:1,source_members:['a','b'],
        coverage_rows:[{y:1,runs:requested.map(([a,b])=>[a,b,'mapped_land_support'])}]}]};
    mutateSource(source);
    f.save('incremental/source.json',source);f.save('incremental/patch.json',{rows:[{y:1,runs:requested}]});
    const inputsAt=f.commit(),pins={source_evidence:f.pin('incremental/source.json',inputsAt),native_patch:f.pin('incremental/patch.json',inputsAt)};
    const count=r=>r.reduce((n,[a,b])=>n+b-a,0);
    const diagnostic={version:1,kind:'source-target-native-diagnostic-v1',native_contract:contract,original_pins:pins,
      rule_sha256:digest(jsonBytes({version:1,kind:'source-target-native-rule-v1',...pins})),
      requested_rows:[{y:1,runs:requested}],supported_rows:supported.length?[{y:1,runs:supported}]:[],held_rows:held.length?[{y:1,runs:held}]:[],
      decision_rows:[{y:1,runs:[...supported.map(r=>[...r,'assigned_cells']),...held.map(r=>[...r,'territorial_exclusion_cells'])].sort((a,b)=>a[0]-b[0])}],
      requested_cells:count(requested),supported_cells:count(supported),held_cells:count(held)};
    mutateDiagnostic(diagnostic);f.save('incremental/diagnostic.json',diagnostic);const at=f.commit();
    const config={version:1,diagnostic:{commit:at,path:'incremental/diagnostic.json'},
      ...(accepted?{accepted_selector:{commit:selectorCommit,path:'data/ownership-selection.json'}}:{})};
    if(priorHoldRuns){f.save('incremental/prior-holds.json',{rows:[{y:1,runs:priorHoldRuns}]});config.prior_holds={commit:f.commit(),path:'incremental/prior-holds.json'};}
    mutateSelector(config,f);
    const reader=pinReader(f.root);mutateReader(reader);
    const output=await supportedInputs(config,reader);
    return {output:Object.fromEntries(Object.entries(output).map(([name,raw])=>[name,JSON.parse(raw)])),source,diagnostic,pins,config};
  }
  return {...f,run,selectorCommit};
}

test('accepted final map partitions full support into exact novel/already-present/held keys',async t=>{
 const f=await acceptedFixture(t);
 for(const [name,supported,held,novel,present] of [
  ['mixed',[[2,4,1]],[[4,5,1]],[[3,4,1]],[[2,3,1]]],
  ['all novel',[[10,12,1]],[[12,13,1]],[[10,12,1]],[]],
  ['zero novel',[[2,3,1]],[[4,5,1]],[],[[2,3,1]]],
  ['entirely held',[],[[2,3,1]],[],[]],
  ['full-width intervals',[[2,262166,1]],[],[[3,262166,1]],[[2,3,1]]]
 ])await t.test(name,async()=>{
  const {output:o,source,diagnostic,pins}=await f.run({supported,held});
  assert.deepEqual(o['native-patch.json'].rows,novel.length?[{y:1,runs:novel}]:[]);
  assert.deepEqual(o['already-present-original.json'].rows,present.length?[{y:1,runs:present}]:[]);
  assert.deepEqual(o['held-original.json'].rows,held.length?[{y:1,runs:held.map(r=>[...r,'territorial_exclusion_cells'])}]:[]);
  assert.deepEqual(o['source-evidence.json'],{...source,targets:novel.length?source.targets.map(target=>({...target,coverage_rows:[{y:1,runs:novel.map(([a,b])=>[a,b,'mapped_land_support'])}]})):[]});
  const a=o['original-scope-partition.json'];assert.equal(a.original_cells,a.supported_cells+a.already_present_cells+a.held_cells);
  assert.equal(a.native_supported_cells,diagnostic.supported_cells);assert.deepEqual(a.original_inputs,pins);
  assert(a.accepted_input_inventory.some(p=>p.path.endsWith('/index.json')));
  for(const owner of a.owners)assert.equal(owner.original_cells,owner.supported_cells+owner.already_present_cells+owner.held_cells);
 });
 await t.test('prior holds cannot become already-present or novel authority',async()=>{
  const {output:o}=await f.run({priorHoldRuns:[[2,4,1,'prior-unresolved']]});
  assert.deepEqual(o['native-patch.json'].rows,[]);assert.deepEqual(o['already-present-original.json'].rows,[]);
  assert.deepEqual(o['held-original.json'].rows,[{y:1,runs:[[2,4,1,'prior-unresolved'],[4,5,1,'territorial_exclusion_cells']]}]);
  const a=o['original-scope-partition.json'];assert.equal(a.original_cells,3);assert.equal(a.held_cells,3);assert.equal(a.already_present_cells,0);
 });
 await t.test('omitting selector retains complete original supported route',async()=>{
  const {output:o}=await f.run({accepted:false});assert.deepEqual(o['native-patch.json'].rows,[{y:1,runs:[[2,4,1]]}]);
  assert(!Object.hasOwn(o,'already-present-original.json'));assert(!Object.hasOwn(o['original-scope-partition.json'],'accepted_selector'));
 });
});

test('incremental support refuses conflicts, identity substitutions and incomplete accepted state',async t=>{
 const f=await acceptedFixture(t);
 const cases=[
  ['unexpected replacement operand',{mutateSelector:c=>c.source_evidence={}},/Explicit incremental supported-input locators/],
  ['different occupied owner',{supported:[[0,1,1]],held:[]},/conflicts with accepted owner/],
  ['foreign target identity',{mutateSource:s=>s.targets[0].target_id='B'},/owner identity differs/],
  ['missing target identity',{mutateSource:s=>delete s.targets[0].target_id},/owner identity differs/],
  ['native contract substitution',{mutateSource:s=>s.base_reference={...s.base_reference,id:'geography:foreign'}},/original native contract/],
  ['noncanonical selector path',{mutateSelector:c=>c.accepted_selector.path='incremental/source.json'},/Canonical accepted selector/],
  ['missing immutable selector',{mutateSelector:c=>c.accepted_selector.commit='0'.repeat(40)},/Missing ordinary|not a tree|bad object|Not a valid object/],
  ['stale committed selection',{mutateSelector:(_c,f)=>{const s=JSON.parse(f.git('show','HEAD:data/ownership-selection.json'));s.reference.id='geography:stale';f.save('data/ownership-selection.json',s);f.commit();}},/differs from current committed selection/],
  ['mismatched accepted native manifest',{mutateSelector:(c,f)=>{const s=JSON.parse(f.git('show','HEAD:data/ownership-selection.json'));s.native_selection.sha256='0'.repeat(64);f.save('data/ownership-selection.json',s);c.accepted_selector.commit=f.commit();}},/Accepted native manifest differs/],
  ['incomplete original owner coverage',{mutateSource:s=>s.targets[0].coverage_rows[0].runs.shift()},/coverage rows differ/],
  ['missing accepted body',{mutateReader:r=>{const read=r.read;r.read=p=>{if((p.path.startsWith('data/canonical-grid/current-startup/')&&!p.path.endsWith('/index.json')))throw Error('Fixture required accepted body unavailable');return read(p);};}},/required accepted body unavailable/],
  ['altered accepted body',{mutateReader:r=>{const read=r.read;r.read=p=>{const raw=read(p);return (p.path.startsWith('data/canonical-grid/current-startup/')&&!p.path.endsWith('/index.json'))?Buffer.from(raw).fill(0):raw;};}},/whole identity differs/]
 ];
 for(const [name,options,pattern]of cases)await t.test(name,async()=>{await assert.rejects(f.run(options),pattern);});
});

test('stock supported-inputs CLI awaits accepted-map preparation and preserves exact resume',async t=>{
  const f=await acceptedFixture(t),{config,output}=await f.run();
  f.save('incremental/config.json',config);f.commit();
  const env={...process.env};delete env.NODE_PATH;delete env.NODE_OPTIONS;
  const args=[path.resolve('scripts/prepare-delivery-handoff.mjs'),'supported-inputs','incremental/config.json','coordination/engineering/incremental-test/output'];
  for(const flags of [[],['--resume']]){
   const run=spawnSync(process.execPath,[...args,...flags],{cwd:f.root,env,encoding:'utf8'});
   assert.equal(run.status,0,run.stderr);
   for(const [name,value]of Object.entries(output))assert.deepEqual(JSON.parse(fs.readFileSync(path.join(f.root,'coordination/engineering/incremental-test/output',name))),value);
  }
 });
