/** Declarative structural vocabulary; no factual assignments or map algorithms. */
import {assertJSONData} from './json-contract.js';
const freeze = value => {
  if (value && typeof value === 'object') {
    Object.values(value).forEach(freeze);
    Object.freeze(value);
  }
  return value;
};
const type = (id, definition) => ({id, definition});
const metric = (id, unit, definition, extra = {}) => ({id, unit, definition, minimum: 0, ...extra});
const field = (id, subject_kinds, value_type, definition, extra = {}) => ({id, subject_kinds, value_type, definition, ...extra});

export const atlasObservationModule = freeze({
  id: 'atlas', version: 1,
  types: [
    type('location', 'Existing indivisible territorial polygon identity.'),
    type('polity', 'Political entity; government belongs here, not to each owned location.'),
    type('government-class', 'Controlled primary government vocabulary identity; not an assignment.'),
    type('language', 'Spoken-language identity; does not imply culture, script or dialect.'),
    type('disease', 'Disease identity independent of its dated outbreaks.'),
    type('outbreak', 'One outbreak identity; multiple outbreaks may affect a location concurrently.'),
    type('river', 'Cataloged river or reach; contact does not establish navigability.'),
    type('lake', 'Cataloged inland lake, including saline lakes.'),
    type('marine-shoreline', 'Marine shoreline reference feature; distinct from inland lakes.'),
    type('port', 'Port facility identity, independent of settlement rank and coastal contact.'),
    type('port-function', 'Reviewed functional service vocabulary; no inferred maritime capability.'),
  ],
  metrics: [
    metric('atlas.gdp-per-person', 'constant-gdp-ppp/per-person', 'Annual output per supported resident.', {ppp_scope: 'gdp'}),
    metric('atlas.total-gdp', 'constant-gdp-ppp', 'Total annual output for the supported territory.', {ppp_scope: 'gdp'}),
    metric('atlas.median-purchasing-power', 'constant-consumption-ppp/equivalized-person', 'Person-weighted median equivalized real disposable household income; not a mean or GDP.', {ppp_scope: 'consumption', household: true}),
    metric('atlas.adult-literacy', 'percent', 'Residents aged 15+ who read and write with understanding a short everyday statement.', {maximum: 100, cohort: 'age-15-plus'}),
    metric('atlas.annual-disease-deaths', 'persons', 'Disease-attributed deaths during the supported selected year; not cumulative cases or excess mortality.', {period_basis: 'annual'}),
  ],
  fields: [
    field('atlas.government-primary', ['polity'], 'identity', 'One exclusive primary government class; ambiguity stays unresolved.', {value_kind: 'government-class'}),
    field('atlas.primary-spoken-language', ['location'], 'identity', 'Supported primary everyday/home spoken language; broad evidence is not silently refined.', {value_kind: 'language'}),
    ...['gdp-per-person', 'total-gdp', 'median-purchasing-power', 'adult-literacy', 'annual-disease-deaths'].map(id =>
      field(`atlas.${id}`, ['location'], 'number', `Supported ${id} observation; derivation is a separate domain responsibility.`, {metric_id: `atlas.${id}`})),
    field('atlas.river-lake-contact', ['location'], 'boolean', 'Contact with a complete applicable major-river/lake catalog; missing coverage is unknown.'),
    field('atlas.marine-contact', ['location'], 'boolean', 'Supported direct marine-shoreline contact; inland lakes and nearby pixels do not establish it.'),
    field('atlas.port-functions', ['port'], 'identity-list', 'Explicitly documented active facility functions; river-sited maritime is not automatically mixed.', {value_kind: 'port-function'}),
  ],
  relationships: [
    {id: 'atlas.outbreak-disease', source_kinds: ['outbreak'], target_kinds: ['disease'], definition: 'Dated sourced disease attribution for an outbreak.'},
    {id: 'atlas.outbreak-location', source_kinds: ['outbreak'], target_kinds: ['location'], definition: 'Dated affected location; no automatic aggregation or annual allocation.'},
    {id: 'atlas.water-location', source_kinds: ['river', 'lake', 'marine-shoreline'], target_kinds: ['location'], definition: 'Sourced dated feature contact; geometry approval remains separate.'},
    {id: 'atlas.port-location', source_kinds: ['port'], target_kinds: ['location'], definition: 'Dated location association; does not alone establish operating status or functions.'},
  ],
});

function text(value, label) {
  if (typeof value !== 'string' || !value.trim() || value.length > 2000) throw Error(`Invalid registry ${label}`);
}
const kinds = (values, types) => Array.isArray(values) && values.length > 0
  && new Set(values).size === values.length && values.every(id => Object.hasOwn(types, id));

/** Explicit module list is the only registration seam; no global mutation/plugins. */
export function createObservationRegistry(modules = []) {
  if (!Array.isArray(modules) || modules.length > 32) throw Error('Invalid observation module list');
  assertJSONData(modules, {maxBytes: 2097152});
  const result = {version: 1, modules: [], types: {}, metrics: {}, fields: {}, relationships: {}};
  const moduleIds = new Set();
  for (const input of [atlasObservationModule, ...modules]) {
    assertJSONData(input, {objectRequired: true, maxBytes: 65536});
    if (!input || typeof input !== 'object' || Array.isArray(input)
      || !/^[a-z][a-z0-9-]{0,63}$/.test(input.id) || input.version !== 1
      || moduleIds.has(input.id)) throw Error('Invalid or duplicate observation module');
    moduleIds.add(input.id);
    // Round-trip only JSON data; functions/undefined/nonfinite values are rejected.
    const raw = JSON.stringify(input);
    if (raw.length > 65536) throw Error('Observation module exceeds 64 KiB');
    const module = JSON.parse(raw);
    if (module.id !== input.id || module.version !== input.version) throw Error('Serialized module identity changed');
    result.modules.push({id: module.id, version: module.version});
    for (const collection of ['types', 'metrics', 'fields', 'relationships']) {
      const entries = module[collection] ?? [];
      if (!Array.isArray(entries) || entries.length > 128) throw Error('Invalid registry collection');
      for (const entry of entries) {
        if (!entry || typeof entry !== 'object' || Array.isArray(entry)) throw Error('Invalid registry entry');
        text(entry.id, 'ID'); text(entry.definition, 'definition');
        if (module.id !== 'atlas' && !entry.id.startsWith(`${module.id}.`)) throw Error('Extension IDs must use their module namespace');
        if (Object.hasOwn(result[collection], entry.id) || ['__proto__', 'constructor', 'prototype'].includes(entry.id)) throw Error('Duplicate or unsafe registry ID');
        result[collection][entry.id] = entry;
      }
    }
  }
  for (const definition of Object.values(result.metrics)) {
    text(definition.unit, 'unit');
    for (const bound of ['minimum', 'maximum']) if (definition[bound] != null && !Number.isFinite(definition[bound])) throw Error('Invalid metric bound');
    if (definition.minimum != null && definition.maximum != null && definition.maximum < definition.minimum) throw Error('Inverted metric bounds');
    if (definition.ppp_scope != null && !['gdp', 'consumption'].includes(definition.ppp_scope)) throw Error('Invalid PPP scope');
  }
  for (const definition of Object.values(result.fields)) {
    if (!kinds(definition.subject_kinds, result.types) || !['number', 'identity', 'identity-list', 'boolean'].includes(definition.value_type)) throw Error('Invalid field subject or value type');
    if (definition.value_type === 'number') {
      if (!Object.hasOwn(result.metrics, definition.metric_id)) throw Error('Numeric field requires a registered metric');
    } else if (definition.metric_id != null) throw Error('Only numeric fields reference metrics');
    if (['identity', 'identity-list'].includes(definition.value_type) && !Object.hasOwn(result.types, definition.value_kind)) throw Error('Identity field requires a registered value kind');
  }
  for (const definition of Object.values(result.relationships)) {
    if (!kinds(definition.source_kinds, result.types) || !kinds(definition.target_kinds, result.types)) throw Error('Invalid relationship endpoint kinds');
  }
  return freeze(result);
}

export const observationRegistry = createObservationRegistry();
