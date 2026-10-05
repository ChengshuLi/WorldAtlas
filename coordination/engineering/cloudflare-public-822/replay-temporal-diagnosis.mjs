import fs from 'node:fs';
import assert from 'node:assert/strict';
import {loadHostedTemporalGeography} from '../../../src/hosted-temporal-client.js';

// Replay the captured pre-publication response, never query or mutate Neon.
const captured = JSON.parse(fs.readFileSync(new URL('./captured-temporal-diagnosis.json', import.meta.url)));
const apiGet = async url => captured.temporal_geography[new URL(url, 'https://atlas.invalid').searchParams.get('stream')];
const options = {apiGet, year: captured.year, expectedRevision: captured.revision};
const result = await loadHostedTemporalGeography({...options, expectedGeography: captured.matched_diagnostic_pins});
assert.equal(result.combinedSnapshot.release_id, captured.matched_diagnostic_pins.release_id);
await assert.rejects(
  loadHostedTemporalGeography({...options, expectedGeography: captured.mismatched_staged_pins}),
  error => error.code === 'temporal-geography-pin-mismatch',
);
console.log('Historical diagnosis reproduced: published5 pages match5 and reject staged6. Live6 acceptance remains pending.');
