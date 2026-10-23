// Captured immutable normative rule bytes; production pins and paths stay unchanged.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
export function normativeLatitudeBytes() {
  const raw=fs.readFileSync(new URL('./native-row-latitudes.f64le.gz',import.meta.url));
  assert.equal(raw.length,1851757);
  assert.equal(createHash('sha256').update(raw).digest('hex'),'ab0becdda100da3473d7bb5d34ccda6510aa1c0490c407082072c7201ad1e147');
  return raw;
}
