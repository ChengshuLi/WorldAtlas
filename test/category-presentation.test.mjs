import test from 'node:test';
import assert from 'node:assert/strict';
import {categoryPresentationKey} from '../src/category-presentation.js';

test('map and legend presentation keys preserve source identities and distinguish concurrent names', () => {
  const a={value:"People's Republic of China",category_id:'owner:Q148'};
  const b={value:'Republic of China',category_id:'owner:Q148'};
  assert.notEqual(categoryPresentationKey('owner',a),categoryPresentationKey('owner',b));
  assert.equal(JSON.parse(categoryPresentationKey('owner',a))[0],a.category_id);
  assert.equal(a.category_id,b.category_id);
  assert.equal(categoryPresentationKey('owner',{value:null,category_id:'owner:old'}),null);
});
test('shared named modes distinguish display groups; fixed classifications and hierarchy use stable IDs', () => {
  for(const mode of ['culture','religion']) assert.deepEqual(JSON.parse(categoryPresentationKey(mode,{value:'Name',category_id:'stable'})),['stable','Name']);
  assert.equal(categoryPresentationKey('climate',{value:'Af tropical rainforest',category_id:'climate:Af'}),'climate:Af');
  assert.equal(categoryPresentationKey('province',{},'framework:province:stable'),'framework:province:stable');
});
