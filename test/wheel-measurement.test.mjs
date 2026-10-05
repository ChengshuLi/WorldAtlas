import test from 'node:test';
import assert from 'node:assert/strict';
import {wheelTiming} from '../scripts/wheel-measurement.mjs';
const unchanged=time=>({time,transform:'identity',pane:'identity',frame:'old'});
test('timing uses the last frame before input, including a known delayed change',()=>{
  const data={frames:[0,16,32,48,64],events:[{time:35}],transforms:[unchanged(0),{...unchanged(16),frame:'before'},unchanged(32),{...unchanged(48),transform:'scaled'}]};
  assert.deepEqual(wheelTiming(data),{first_observed_transform_ms:13,raf_p50_ms:16,raf_p95_ms:16,frames_over_34ms:0,frames:4});
});
test('controls reject a false response when unchanged or when no input was observed',()=>{
  const data={frames:[0,16,32,100],events:[{time:10}],transforms:[unchanged(0),unchanged(16),unchanged(32)]};
  assert.equal(wheelTiming(data).first_observed_transform_ms,null);
  assert.equal(wheelTiming(data).frames_over_34ms,1);
  data.events=[];data.transforms.push({...unchanged(100),transform:'unrelated'});
  assert.equal(wheelTiming(data).first_observed_transform_ms,null);
});
