import test from 'node:test';
import assert from 'node:assert/strict';
import {validateLanePaths} from '../scripts/check-handoff-scope.mjs';

test('engineering literal grants retain branch fallback, exact-file and directory boundaries',()=>{
 const ownedPaths=['coordination/engineering/batch/composition/','coordination/engineering/prevention/helper.mjs','.github/workflows/fixture.yml'];
 validateLanePaths('engineering/repair',['coordination/engineering/repair.json','coordination/engineering/repair/proof.json','coordination/engineering/batch/composition/README.md','coordination/engineering/prevention/helper.mjs','.github/workflows/fixture.yml'],{ownedPaths});
 for(const file of ['coordination/engineering/batch/README.md','coordination/engineering/batch/composition-sibling/README.md','coordination/engineering/prevention/helper.mjs.bak','coordination/engineering/prevention/helper.mjs/nested','coordination/engineering/unrelated/README.md'])assert.throws(()=>validateLanePaths('engineering/repair',[file],{ownedPaths}));
 for(const grant of ['coordination/engineering/','coordination/engineering','coordination/','scripts/','coordination/engineering/batch/../other/','coordination/engineering/batch//nested/','coordination/engineering/batch/./nested/','coordination/engineering/batch/*','/coordination/engineering/batch/','coordination\\engineering\\batch','research/campaigns/a/','research/geography/a/','data/regional-review/a/'])assert.throws(()=>validateLanePaths('engineering/repair',[],{ownedPaths:[grant]}));
 assert.throws(()=>validateLanePaths('engineering/repair',[],{ownedPaths:[ownedPaths[0],ownedPaths[0]]}));
 for(const file of ['research/campaigns/a/input.json','research/geography/a/input.json','data/regional-review/a/input.json'])assert.throws(()=>validateLanePaths('engineering/repair',[file],{ownedPaths}));
});
