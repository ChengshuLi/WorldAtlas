import {validYear} from './model.js';
import {evidencePriority} from './evidence-priority.js';
import {observationRegistry} from './observation-registry.js';

const object = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const text = (value, label) => {
  if (typeof value !== 'string' || !value.trim() || value.length > 2000) throw Error(`Invalid ${label}`);
  return value;
};
const unknownStatuses = ['unknown', 'unresolved', 'disputed', 'no-majority'];
const methods = ['direct', 'derived', 'reference', 'estimate'];
const statuses = ['sourced', 'derived', 'reference', 'estimate', 'example', ...unknownStatuses];
export function supportedInterval(from, to) {
  if (!validYear(from) || !(validYear(to) || to === 2027) || to <= from) throw Error('Invalid supported half-open interval; no year zero');
  return {from, to};
}
function jsonObject(value, label) {
  if (!object(value)) throw Error(`Invalid ${label}`);
  // Validate without rewriting the original source/provenance metadata.
  const inspect = (v, ancestors = new Set()) => {
    if (v === null || typeof v === 'string' || typeof v === 'boolean') return;
    if (typeof v === 'number') { if (Number.isFinite(v)) return; throw Error('Nonfinite JSON number'); }
    if (!v || typeof v !== 'object' || !Array.isArray(v) && Object.getPrototypeOf(v) !== Object.prototype && Object.getPrototypeOf(v) !== null) throw Error('Metadata must contain only JSON data');
    if (ancestors.has(v)) throw Error('Cyclic metadata');
    const next = new Set(ancestors); next.add(v);
    for (const item of Object.values(v)) inspect(item, next);
  };
  inspect(value);
  if (new TextEncoder().encode(JSON.stringify(value)).length > 16384) throw Error('Metadata exceeds 16 KiB');
  return value;
}
function entity(id, kind, entities, label) {
  text(id, label);
  const found = entities.get(id);
  if (!found || found.kind !== kind) throw Error(`${label} is absent or has the wrong kind`);
  return found;
}
function withinEntity(row, found) {
  if (found.valid_from != null && !validYear(found.valid_from)
    || found.valid_to != null && !(validYear(found.valid_to) || found.valid_to === 2027)) throw Error('Invalid entity lifetime');
  if (found.valid_from != null && row.valid_from < found.valid_from
    || found.valid_to != null && row.valid_to > found.valid_to) throw Error('Observation exceeds subject lifetime');
}
function contextMaps({sources = [], entities = []} = {}) {
  const map = (rows, label) => {
    if (!Array.isArray(rows) || rows.length > 100000) throw Error(`Invalid ${label} catalog`);
    const result = new Map();
    for (const row of rows) {
      if (!object(row)) throw Error(`Invalid ${label} identity`);
      text(row.id, `${label} ID`);
      if (result.has(row.id)) throw Error(`Duplicate ${label} identity`);
      result.set(row.id, row);
    }
    return result;
  };
  return {sources: map(sources, 'source'), entities: map(entities, 'entity')};
}
function evidence(input, sources) {
  if (!object(input)) throw Error('Invalid typed evidence');
  text(input.id, 'stable observation/link ID'); text(input.source_id, 'source ID');
  supportedInterval(input.valid_from, input.valid_to);
  const source = sources.get(input.source_id);
  if (!source || !['historical', 'reference', 'estimate', 'example'].includes(source.status)) throw Error('Missing or invalid source');
  supportedInterval(source.supported_from, source.supported_to);
  if (input.valid_from < source.supported_from || input.valid_to > source.supported_to) throw Error('Evidence exceeds supported source interval');
  const method = input.method ?? 'direct', is_example = input.is_example ?? 0;
  if (!methods.includes(method) || ![0, 1].includes(is_example)) throw Error('Invalid evidence method/example flag');
  const status = input.status ?? (is_example ? 'example' : input.value === null ? 'unknown' : method === 'direct' ? 'sourced' : method);
  if (!statuses.includes(status)) throw Error('Invalid evidence status');
  if (source.status === 'example' && !is_example || status === 'example' && !is_example) throw Error('Example evidence must remain explicitly labeled');
  if (!unknownStatuses.includes(status) && !is_example) {
    if (source.status === 'reference' && (method !== 'reference' || status !== 'reference')) throw Error('Reference source cannot become historical evidence');
    if (source.status === 'estimate' && status !== 'estimate') throw Error('Estimated source must remain estimated');
    if (status === 'sourced' && method !== 'direct' || status === 'derived' && method !== 'derived'
      || status === 'reference' && method !== 'reference' || method === 'reference' && status !== 'reference') throw Error('Evidence status/method mismatch');
  }
  const metadata = jsonObject(input.metadata ?? {}, 'evidence metadata');
  if (metadata.evidence_priority != null || input.evidence_priority != null) throw Error('Typed evidence cannot override resolution priority');
  if (metadata.derivation_input_ids != null) {
    const ids = metadata.derivation_input_ids;
    if (!Array.isArray(ids) || ids.length > 128 || new Set(ids).size !== ids.length) throw Error('Invalid derivation input IDs');
    for (const id of ids) { text(id, 'derivation input ID'); if (id === input.id) throw Error('Self-derived evidence'); }
  }
  if (method === 'derived' && !metadata.derivation_input_ids?.length) throw Error('Derived evidence requires retained input IDs');
  return {...input, version: 1, method, status, is_example, metadata, source_status: source.status};
}
function measurement(row, metric, source) {
  const value = row.metadata.measurement;
  if (!object(value) || value.unit !== metric.unit) throw Error('Numeric observation requires its registered measurement unit');
  text(value.definition, 'measurement definition');
  if (!object(value.period)) throw Error('Numeric observation requires an observation period');
  supportedInterval(value.period.from, value.period.to);
  if (value.period.from < source.supported_from || value.period.to > source.supported_to) throw Error('Measurement period exceeds source support');
  if (metric.period_basis && value.period_basis !== metric.period_basis) throw Error('Incompatible measurement period basis; cumulative totals are not annual observations');
  if (metric.ppp_scope) {
    if (value.price_basis !== 'constant' || value.ppp_scope !== metric.ppp_scope || !validYear(value.benchmark_year)) throw Error('Missing or incompatible constant-price PPP basis');
    text(value.series_id, 'PPP series'); text(value.comparability_group, 'comparability group');
  }
  if (metric.household) {
    text(value.equivalence_scale, 'household equivalence scale');
    if (value.weighting_basis !== 'person') throw Error('Canonical median requires person weighting');
  }
  if (metric.cohort && value.cohort !== metric.cohort) throw Error('Incompatible measurement cohort');
  const uncertainty = row.metadata.uncertainty;
  if (uncertainty != null) {
    if (!object(uncertainty) || !Number.isFinite(uncertainty.lower) || !Number.isFinite(uncertainty.upper)
      || uncertainty.lower > row.value || uncertainty.upper < row.value
      || metric.minimum != null && uncertainty.lower < metric.minimum
      || metric.maximum != null && uncertainty.upper > metric.maximum) throw Error('Invalid uncertainty bounds');
    text(uncertainty.method, 'uncertainty method');
  }
}
function normalize(input, maps, registry) {
  const row = evidence(input, maps.sources);
  if (input.version != null && input.version !== 1) throw Error('Unsupported observation version');
  const definition = registry.fields[row.field_id];
  if (!Object.hasOwn(registry.fields, row.field_id) || !definition.subject_kinds.includes(row.subject_kind)) throw Error('Unknown field or wrong subject kind');
  const subject = entity(row.subject_id, row.subject_kind, maps.entities, 'observation subject');
  withinEntity(row, subject);
  if (subject.is_example && !row.is_example) throw Error('Example subject cannot become factual evidence');
  if (!Object.hasOwn(row, 'value') || row.value === undefined) throw Error('Observation requires an explicit value');
  if (unknownStatuses.includes(row.status)) {
    if (row.value !== null) throw Error('Unknown/unresolved evidence requires null, not zero or false');
  } else if (row.value === null) throw Error('Null observation requires unknown/unresolved status');
  if (row.value !== null) {
    if (definition.value_type === 'boolean' && typeof row.value !== 'boolean') throw Error('Contact value must be boolean');
    if (definition.value_type === 'number') {
      const metric = registry.metrics[definition.metric_id];
      if (!Number.isFinite(row.value) || typeof row.value !== 'number'
        || metric.minimum != null && row.value < metric.minimum || metric.maximum != null && row.value > metric.maximum) throw Error('Invalid numeric metric value');
      measurement(row, metric, maps.sources.get(row.source_id));
    }
    if (['identity', 'identity-list'].includes(definition.value_type)) {
      const values = definition.value_type === 'identity' ? [row.value] : row.value;
      if (!Array.isArray(values) || values.length === 0 || values.length > 128 || new Set(values).size !== values.length) throw Error('Invalid controlled identity value');
      for (const id of values) {
        const target = entity(id, definition.value_kind, maps.entities, 'observation value');
        withinEntity(row, target);
        if (target.is_example && !row.is_example) throw Error('Example value cannot become factual evidence');
      }
    }
  }
  return row;
}

export function normalizeTypedObservation(input, context = {}, registry = observationRegistry) {
  return normalize(input, contextMaps(context), registry);
}

/** Existing entity/source/link identities remain the endpoints of typed links. */
export function normalizeTypedRelationship(input, context = {}, registry = observationRegistry) {
  const maps = contextMaps(context), row = evidence(input, maps.sources);
  if (input.version != null && input.version !== 1) throw Error('Unsupported link version');
  if (!Object.hasOwn(registry.relationships, row.relationship_type)) throw Error('Unknown typed relationship');
  const definition = registry.relationships[row.relationship_type];
  for (const [side, allowed] of [['source', definition.source_kinds], ['target', definition.target_kinds]]) {
    const found = maps.entities.get(row[`${side}_entity_id`]);
    if (!found || !allowed.includes(found.kind)) throw Error('Invalid typed relationship endpoint');
    withinEntity(row, found);
    if (found.is_example && !row.is_example) throw Error('Example endpoint cannot become factual evidence');
  }
  return row;
}

export const observationKey = row => JSON.stringify([row.subject_kind, row.subject_id, row.field_id]);

export function typedObservationAt(resolved, subject_kind, subject_id, field_id) {
  const key = observationKey({subject_kind, subject_id, field_id});
  return resolved.find(row => observationKey(row) === key)
    ?? {subject_kind, subject_id, field_id, value: null, status: 'unknown', evidence: null};
}

/** Shared pure server/static seam. No carry-forward, interpolation or fallback facts. */
export function resolveTypedObservations(inputs, year, {sources = [], entities = [], retired_ids = [], examples = false, registry = observationRegistry} = {}) {
  if (!validYear(year)) throw Error('Invalid selected year');
  if (!Array.isArray(inputs) || inputs.length > 100000 || !Array.isArray(retired_ids)) throw Error('Invalid observation snapshot');
  const maps = contextMaps({sources, entities}), retired = new Set(retired_ids), seen = new Set(), chosen = new Map();
  for (const id of retired) text(id, 'retired observation ID');
  for (const input of inputs) {
    const row = normalize(input, maps, registry);
    if (seen.has(row.id)) throw Error('Duplicate stable observation ID');
    seen.add(row.id);
    if (retired.has(row.id) || row.valid_from > year || row.valid_to <= year || row.is_example && !examples) continue;
    const key = observationKey(row), old = chosen.get(key), priority = evidencePriority(row);
    if (!old || priority < old.priority || priority === old.priority && row.id < old.evidence.id) {
      chosen.set(key, {subject_kind: row.subject_kind, subject_id: row.subject_id, field_id: row.field_id,
        value: row.value, status: row.is_example ? 'example' : row.status, priority, evidence: row});
    }
  }
  // Stable byte ordering independent of ingestion order or locale.
  return [...chosen.entries()].sort(([a], [b]) => a < b ? -1 : a > b ? 1 : 0).map(([, row]) => row);
}
