import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { runInNewContext } from 'node:vm';
const html = readFileSync(new URL('../web/index.html', import.meta.url), 'utf8');
const functions = html.slice(html.indexOf('function minimumScale()'), html.indexOf('function draw()'));
function run(width, height, code) {
  const state = { map: { clientWidth: width, clientHeight: height }, meta: { width: 16384, height: 6827 }, scale: 1, ox: 0, oy: 0, requestDraw() {} };
  runInNewContext(functions + '\n' + code, state);
  return state;
}
function covered(s) {
  const eps = 1e-8;
  assert.ok(s.ox <= eps && s.oy <= eps);
  assert.ok(s.ox > -s.meta.width * s.scale - eps);
  assert.ok(s.oy + s.meta.height * s.scale >= s.map.clientHeight - eps);
}
for (const [width, height] of [[1200, 700], [390, 800], [2400, 500]]) {
  test(`world reset fills ${width}×${height} without blank margins`, () => covered(run(width, height, 'fit();')));
  test(`zoom-out is clamped and horizontal pan wraps for ${width}×${height}`, () => {
    covered(run(width, height, 'scale=.005; ox=100000; oy=-100000; constrainView();'));
    covered(run(width, height, 'scale=9; ox=-999999; oy=999999; constrainView();'));
  });
}
test('resize reclamps and repeated constraints are stable', () => {
  const s=run(1200,700,'fit(); map.clientHeight=1300; constrainView(); var before=[scale,ox,oy]; for(let i=0;i<50;i++) constrainView();');
  covered(s);assert.deepEqual([s.scale,s.ox,s.oy],Array.from(s.before));
});
test('valid zoomed-in position remains unchanged', () => {
  const s=run(1200,700,'scale=2; ox=-1000; oy=-2000; constrainView();');
  assert.equal(s.scale,2);assert.equal(s.ox,-1000);assert.equal(s.oy,-2000);
});
