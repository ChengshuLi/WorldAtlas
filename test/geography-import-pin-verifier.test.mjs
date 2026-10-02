import test from 'node:test';
import assert from 'node:assert/strict';
import {exerciseGeographyImportPin} from '../scripts/verify-geography-import-pin.mjs';

test('live geography concurrency verifier refuses production, shared sessions and missing interactive drivers before writes',async()=>{
 let queries=0;const driver={query:async()=>{queries++;return {rows:[{pid:42}]};},runTransaction:async()=>{throw Error('Must not write');}};
 await assert.rejects(exerciseGeographyImportPin({publisherDriver:driver,importDriver:driver}),/disposable/);assert.equal(queries,0);
 await assert.rejects(exerciseGeographyImportPin({publisherDriver:driver,importDriver:driver,disposableBranch:true,disposableBranchId:'br-test-only'}),/independent/);assert.equal(queries,0);
 await assert.rejects(exerciseGeographyImportPin({publisherDriver:driver,importDriver:{...driver},disposableBranch:true,disposableBranchId:'br-test-only'}),/separate real/);assert.equal(queries,2);
 await assert.rejects(exerciseGeographyImportPin({publisherDriver:driver,importDriver:{...driver},disposableBranch:true,disposableBranchId:'br-test-only',timeoutMs:999}),/timeout/);assert.equal(queries,2);
});
