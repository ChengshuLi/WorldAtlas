import test from 'node:test';
import assert from 'node:assert/strict';
import {createObservationRegistry, observationRegistry} from '../src/observation-registry.js';
import {normalizeTypedObservation, normalizeTypedRelationship, resolveTypedObservations, typedObservationAt, supportedInterval} from '../src/typed-observations.js';
import {resolveAttributes, locationAttributes} from '../src/attributes.js';
import {evidencePriority} from '../src/evidence-priority.js';
import fs from 'node:fs';

// Synthetic controls only: these identities are never application factual data.
const source = {id: 'fixture:source', status: 'historical', supported_from: -3000, supported_to: 2027,
  metadata: {sha256: 'a'.repeat(64), original_text: 'Retained synthetic source bytes reference'}};
const context = {sources: [source,
  {...source, id: 'fixture:reference', status: 'reference', supported_from: 2026},
  {...source, id: 'fixture:estimate', status: 'estimate'}, {...source, id: 'fixture:example', status: 'example'}],
entities: [
  {id: 'fixture:location', kind: 'location'}, {id: 'fixture:polity', kind: 'polity'},
  {id: 'fixture:class', kind: 'government-class'}, {id: 'fixture:language', kind: 'language'},
  {id: 'fixture:port', kind: 'port'}, {id: 'fixture:function', kind: 'port-function'},
  {id: 'fixture:outbreak', kind: 'outbreak'}, {id: 'fixture:disease', kind: 'disease'},
  {id: 'fixture:lake', kind: 'lake'}, {id: 'fixture:shore', kind: 'marine-shoreline'},
]};
const contact = (extra = {}) => ({version: 1, id: 'fixture:claim', subject_id: 'fixture:location', subject_kind: 'location',
  field_id: 'atlas.marine-contact', value: false, valid_from: 1000, valid_to: 1100,
  source_id: source.id, method: 'direct', status: 'sourced', metadata: {}, ...extra});
const numeric = (id = 'adult-literacy', extra = {}) => contact({field_id: `atlas.${id}`, value: 0,
  metadata: {measurement: {unit: observationRegistry.metrics[`atlas.${id}`].unit,
    definition: observationRegistry.metrics[`atlas.${id}`].definition, period: {from: 1000, to: 1100}, cohort: 'age-15-plus'}}, ...extra});
const extension = {id: 'fixture', version: 1,
  types: [{id: 'fixture.instrument', definition: 'Synthetic instrument kind.'}],
  metrics: [{id: 'fixture.number', definition: 'Synthetic scale.', unit: 'fixture-units', minimum: -10, maximum: 10}],
  fields: [{id: 'fixture.reading', definition: 'Synthetic observation.', subject_kinds: ['fixture.instrument'], value_type: 'number', metric_id: 'fixture.number'}]};

test('registration is additive, versioned, immutable and JSON-only; conflicts fail closed', () => {
  const before = JSON.stringify(observationRegistry), registry = createObservationRegistry([extension]);
  assert.equal(registry.fields['atlas.government-primary'].subject_kinds[0], 'polity');
  assert.ok(registry.fields['fixture.reading']); assert.equal(JSON.stringify(observationRegistry), before);
  assert.throws(() => {registry.fields['fixture.reading'].definition = 'Mutated';}, TypeError);
  for (const modules of [[extension, extension], [{...extension, version: 2}], [{...extension, id: 'atlas'}],
    [{...extension, types: [{id: 'location', definition: 'Override'}]}],
    [{...extension, fields: [{...extension.fields[0], metric_id: 'missing'}]}],
    [{...extension, action: () => {}}], [{...extension, date: new Date()}],
    [{...extension, metrics: [{...extension.metrics[0], maximum: -11}]}]]) {
    assert.throws(() => createObservationRegistry(modules));
  }
});

test('serialization hooks/getters cannot replace module identity or metadata, and never execute', () => {
  let executions = 0;
  const replacement = {id: 'fixture', version: 1};
  Object.defineProperty(replacement, 'toJSON', {value: () => {executions++; return {id: 'atlas', version: 1};}});
  assert.throws(() => createObservationRegistry([replacement]), /hidden/);
  const getter = {id: 'fixture', version: 1};
  Object.defineProperty(getter, 'fields', {enumerable: true, get() {executions++; return [];}});
  assert.throws(() => createObservationRegistry([getter]), /Accessors/);
  const metadata = {};
  Object.defineProperty(metadata, 'toJSON', {value: () => {executions++; return {evidence_priority: -1000};}});
  assert.throws(() => normalizeTypedObservation(contact({metadata}), context), /hidden/);
  assert.equal(executions, 0);
  for (const invalid of [Array(2), Object.assign([], {note: 'lost'}), Object.assign({}, {[Symbol('lost')]: 1}), {date: new Date()}]) {
    assert.throws(() => normalizeTypedObservation(contact({metadata: {nested: invalid}}), context));
  }
  const parsed = JSON.parse(JSON.stringify(extension));
  assert.deepEqual(createObservationRegistry([parsed]), createObservationRegistry([extension]));
});

test('false and literal zero remain sourced; absent, unknown and unresolved are distinct', () => {
  assert.equal(normalizeTypedObservation(contact(), context).value, false);
  assert.equal(normalizeTypedObservation(numeric(), context).value, 0);
  const rows = resolveTypedObservations([contact({value: null, status: 'unresolved'})], 1050, context);
  assert.equal(rows[0].status, 'unresolved'); assert.equal(rows[0].value, null);
  assert.deepEqual(typedObservationAt([], 'location', 'fixture:location', 'atlas.marine-contact'),
    {subject_kind: 'location', subject_id: 'fixture:location', field_id: 'atlas.marine-contact', value: null, status: 'unknown', evidence: null});
  for (const value of [false, 0, 'unknown']) assert.throws(() => normalizeTypedObservation(contact({value, status: 'unknown'}), context));
  assert.throws(() => normalizeTypedObservation(contact({value: null}), context));
});

test('no year zero, interval extrapolation, lifetime overflow or modern-reference promotion', () => {
  supportedInterval(-1, 1); supportedInterval(2026, 2027);
  for (const dates of [[0, 1], [-1, 0], [-3001, 1], [2026, 2028], [1100, 1000]]) assert.throws(() => supportedInterval(...dates));
  const ancient = contact({valid_from: -1, valid_to: 1});
  assert.equal(resolveTypedObservations([ancient], -1, context).length, 1);
  assert.equal(resolveTypedObservations([ancient], 1, context).length, 0);
  assert.throws(() => normalizeTypedObservation(contact({source_id: 'fixture:reference'}), context), /source interval/);
  const modern = contact({source_id: 'fixture:reference', valid_from: 2026, valid_to: 2027, method: 'reference', status: 'reference'});
  assert.equal(resolveTypedObservations([modern], 1000, context).length, 0);
  assert.equal(resolveTypedObservations([modern], 2026, context)[0].status, 'reference');
  assert.throws(() => normalizeTypedObservation({...modern, method: 'direct', status: 'sourced'}, context), /Reference/);
  assert.throws(() => normalizeTypedObservation(contact(), {...context, entities: [{id: 'fixture:location', kind: 'location', valid_from: 1050}]}), /lifetime/);
});

test('numeric measurement rejects incompatible units, PPP, cohort, household weighting and uncertainty', () => {
  const gdp = numeric('gdp-per-person');
  assert.throws(() => normalizeTypedObservation(gdp, context), /PPP/);
  const measurement = {...gdp.metadata.measurement, price_basis: 'constant', ppp_scope: 'gdp', benchmark_year: 2021,
    series_id: 'fixture:series', comparability_group: 'fixture:territory-period'};
  const compatible = {...gdp, metadata: {measurement, original_values: [{value: '12.3400', unit: 'fixture:currency', source_id: source.id}],
    derivation_input_ids: ['fixture:input'], uncertainty: {lower: 0, upper: 1, method: 'Fixture supported bounds'}}};
  assert.deepEqual(normalizeTypedObservation(compatible, context).metadata, compatible.metadata);
  for (const patch of [{unit: 'persons'}, {ppp_scope: 'consumption'}, {price_basis: 'current'}, {benchmark_year: 0},
    {period: {from: 0, to: 1}}, {comparability_group: ''}]) {
    assert.throws(() => normalizeTypedObservation({...compatible, metadata: {...compatible.metadata, measurement: {...measurement, ...patch}}}, context));
  }
  for (const value of [-1, 101, NaN, Infinity, '80', false]) assert.throws(() => normalizeTypedObservation(numeric('adult-literacy', {value}), context));
  assert.throws(() => normalizeTypedObservation(numeric('adult-literacy', {metadata: {measurement: {...numeric().metadata.measurement, cohort: 'all-ages'}}}), context), /cohort/);
  const median = numeric('median-purchasing-power', {metadata: {measurement: {...measurement,
    unit: observationRegistry.metrics['atlas.median-purchasing-power'].unit, ppp_scope: 'consumption'}}});
  assert.throws(() => normalizeTypedObservation(median, context), /equivalence/);
  const medianBasis = {...median.metadata.measurement, equivalence_scale: 'fixture:documented-scale', weighting_basis: 'person'};
  assert.equal(normalizeTypedObservation({...median, metadata: {measurement: medianBasis}}, context).value, 0);
  assert.throws(() => normalizeTypedObservation({...median, metadata: {measurement: {...medianBasis, weighting_basis: 'household'}}}, context), /person/);
  assert.throws(() => normalizeTypedObservation({...compatible, metadata: {...compatible.metadata, uncertainty: {lower: 1, upper: 2, method: 'bad'}}}, context), /uncertainty/);
  const annual = numeric('annual-disease-deaths');
  assert.throws(() => normalizeTypedObservation(annual, context), /period basis/);
  assert.throws(() => normalizeTypedObservation({...annual, metadata: {measurement: {...annual.metadata.measurement, period_basis: 'cumulative'}}}, context), /cumulative/);
  assert.equal(normalizeTypedObservation({...annual, metadata: {measurement: {...annual.metadata.measurement, period_basis: 'annual'}}}, context).value, 0);
});

test('entity government, controlled identities and feature links preserve the existing graph', () => {
  const government = contact({subject_id: 'fixture:polity', subject_kind: 'polity', field_id: 'atlas.government-primary', value: 'fixture:class'});
  assert.equal(normalizeTypedObservation(government, context).subject_id, 'fixture:polity');
  assert.throws(() => normalizeTypedObservation({...government, subject_id: 'fixture:location', subject_kind: 'location'}, context));
  assert.throws(() => normalizeTypedObservation({...government, value: 'fixture:language'}, context));
  const link = {id: 'fixture:link', source_entity_id: 'fixture:outbreak', target_entity_id: 'fixture:location',
    relationship_type: 'atlas.outbreak-location', valid_from: 1000, valid_to: 1100, source_id: source.id,
    metadata: {footprints_sha256: 'b'.repeat(64), original_source_sha256: source.metadata.sha256}};
  assert.deepEqual(normalizeTypedRelationship(link, context).metadata, link.metadata);
  assert.throws(() => normalizeTypedRelationship({...link, source_entity_id: 'fixture:port'}, context), /endpoint/);
  assert.throws(() => normalizeTypedRelationship({...link, relationship_type: 'unknown'}, context));
  const port = contact({subject_id: 'fixture:port', subject_kind: 'port', field_id: 'atlas.port-functions', value: ['fixture:function']});
  assert.deepEqual(normalizeTypedObservation(port, context).value, ['fixture:function']);
  assert.throws(() => normalizeTypedObservation({...port, value: ['fixture:function', 'fixture:function']}, context));
});

test('direct/derived/reference/estimate/example precedence, explicit unknown and retirements are deterministic', () => {
  const direct = contact({id: 'fixture:b'}), tied = contact({id: 'fixture:a', value: true});
  const derived = contact({id: 'fixture:derived', method: 'derived', status: 'derived', value: true, metadata: {derivation_input_ids: [direct.id]}});
  const estimated = contact({id: 'fixture:estimate', method: 'estimate', status: 'estimate', source_id: 'fixture:estimate', value: true});
  const example = contact({id: 'fixture:example', is_example: 1, status: 'example', source_id: 'fixture:example', value: true});
  assert.equal(resolveTypedObservations([derived, estimated, example, direct], 1050, context)[0].value, false);
  assert.equal(resolveTypedObservations([direct, tied], 1050, context)[0].evidence.id, tied.id);
  assert.deepEqual(resolveTypedObservations([tied, direct], 1050, context), resolveTypedObservations([direct, tied], 1050, context));
  assert.equal(resolveTypedObservations([direct, derived], 1050, {...context, retired_ids: [direct.id]})[0].status, 'derived');
  assert.equal(resolveTypedObservations([derived, contact({value: null, status: 'unknown'})], 1050, context)[0].value, null);
  assert.equal(resolveTypedObservations([example], 1050, context).length, 0);
  assert.equal(resolveTypedObservations([example], 1050, {...context, examples: true})[0].status, 'example');
  assert.throws(() => normalizeTypedObservation(contact({source_id: 'fixture:example'}), context));
  assert.throws(() => normalizeTypedObservation(contact({source_id: 'fixture:estimate'}), context));
  assert.throws(() => normalizeTypedObservation({...derived, metadata: {}}, context), /input IDs/);
  assert.throws(() => normalizeTypedObservation({...derived, metadata: {derivation_input_ids: [derived.id]}}, context), /Self-derived/);
  assert.throws(() => normalizeTypedObservation(contact({evidence_priority: -100}), context), /priority/);
  assert.throws(() => resolveTypedObservations([direct, direct], 1050, context), /Duplicate/);
});

test('directly quoted estimates retain estimate labels and the preserved method-based priority', () => {
  const sourced = contact({id: 'fixture:z'});
  const quoted = contact({id: 'fixture:a', method: 'direct', status: 'estimate', source_id: 'fixture:estimate', value: true});
  const result = resolveTypedObservations([sourced, quoted], 1050, context)[0];
  assert.equal(result.priority, 0); assert.equal(result.status, 'estimate'); assert.equal(result.evidence.id, quoted.id);
  assert.equal(resolveTypedObservations([{...quoted, method: 'estimate'}, sourced], 1050, context)[0].evidence.id, sourced.id);
});

test('shared pure snapshot seam round-trips all retained source, unit and derivation metadata without mutation', () => {
  const rows = [numeric('adult-literacy', {metadata: {...numeric().metadata, original_values: [{value: '00.00', unit: 'percent'}],
    source_hashes: ['c'.repeat(64)], precision: 'fixture:rounded', uncertainty: {lower: 0, upper: 1, method: 'Fixture bounds'}}}), contact({id: 'fixture:other'})];
  const before = JSON.stringify({rows, context});
  const serialized = JSON.parse(before);
  assert.deepEqual(resolveTypedObservations(rows, 1050, context), resolveTypedObservations(serialized.rows, 1050, serialized.context));
  assert.equal(JSON.stringify({rows, context}), before);
  assert.deepEqual(resolveTypedObservations([], -3000), []);
  assert.deepEqual(resolveTypedObservations([], 2026), []);
});

test('existing eight attributes, legacy values and precedence stay unchanged', () => {
  assert.deepEqual(locationAttributes, ['owner', 'population', 'culture', 'religion', 'rank', 'topography', 'vegetation', 'climate', 'habitation']);
  for (const [row, expected] of [[{method: 'direct'}, 0], [{method: 'direct', evidence_priority: 2}, 2], [{method: 'derived'}, 10],
    [{method: 'majority-area'}, 10], [{method: 'reference'}, 20], [{method: 'estimate'}, 30], [{method: 'direct', is_example: 1}, 40]]) assert.equal(evidencePriority(row), expected);
  const legacy = [{id: 'fixture:legacy', location_id: 'fixture:location', attribute: 'population', value: 42,
    valid_from: 1000, valid_to: 1100, source_id: source.id, method: 'direct', status: 'sourced', metadata: {original_value: '00042'}}];
  const before = JSON.stringify(legacy);
  const result = resolveAttributes([{id: 'fixture:location', properties: {}}], 1050, {records: legacy}).get('fixture:location');
  assert.equal(result.population, 42); assert.equal(result.provenance.population.metadata.original_value, '00042');
  assert.equal(JSON.stringify(legacy), before);
});

test('retained synthetic transport fixture matches date-pinned expected results and original bytes', () => {
  const bytes = fs.readFileSync(new URL('./fixtures/typed-observation-contract-v1.json', import.meta.url));
  const fixture = JSON.parse(bytes);
  for (const [year, expected] of Object.entries(fixture.expected)) {
    const transport = JSON.parse(JSON.stringify(fixture));
    const resolved = resolveTypedObservations(transport.observations, Number(year), transport);
    assert.deepEqual(resolved.map(row => [row.field_id, row.value, row.status, row.evidence.id]), expected);
    assert.deepEqual(resolved, resolveTypedObservations(fixture.observations, Number(year), fixture));
  }
  assert.deepEqual(fs.readFileSync(new URL('./fixtures/typed-observation-contract-v1.json', import.meta.url)), bytes);
});
