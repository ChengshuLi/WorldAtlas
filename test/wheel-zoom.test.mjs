import test from 'node:test';
import assert from 'node:assert/strict';
import {wheelPixels,nextZoom} from '../src/wheel-zoom.js';

test('wheel units normalize pixels, lines and pages without quantizing small input',()=>{
  assert.equal(wheelPixels({deltaY:0.5,deltaMode:0},600),0.5);
  assert.equal(wheelPixels({deltaY:-3,deltaMode:1},600),-120);
  assert.equal(wheelPixels({deltaY:1,deltaMode:2},600),600);
});
test('camera smoothing is time based, bounded and converges without a final snap',()=>{
  const one=nextZoom(2,8,32),two=nextZoom(nextZoom(2,8,16),8,16);
  assert.ok(Math.abs(one-two)<1e-12);
  assert.ok(one>2&&one<8);
  assert.ok(nextZoom(8,2,16)<8);
  assert.equal(nextZoom(2,8,-1),2);
  assert.equal(nextZoom(2,2.0001,16),2.0001);
});
