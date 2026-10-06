import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {readPreparedEvidenceBundle} from '../scripts/read-prepared-evidence-bundle.mjs';
const digest = bytes => createHash('sha256').update(bytes).digest('hex');
test('grid-only build verifies every retained evidence part and import without rewriting any source bytes', async () => {
 const indexBytes=await fs.readFile('data/prepared-evidence/index.json'), index=JSON.parse(indexBytes);
 const files=['index.json',index.imports.path,...index.parts.map(p=>p.path)];
 const imports=JSON.parse(await fs.readFile('data/prepared-evidence/'+index.imports.path));
 files.push(...imports.batches.map(p=>'imports/'+p.path));
 const before=await Promise.all(files.map(async p=>digest(await fs.readFile('data/prepared-evidence/'+p))));
 assert.deepEqual(await readPreparedEvidenceBundle(),index);
 const after=await Promise.all(files.map(async p=>digest(await fs.readFile('data/prepared-evidence/'+p))));
 assert.deepEqual(after,before);
});
