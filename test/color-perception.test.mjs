import test from 'node:test';
import assert from 'node:assert/strict';
import {colorLab,colorDifferences,cssRGB,displayCategoryKey,visionModels} from '../src/color-perception.js';
const close = (a,b) => a.forEach((v,i) => assert.ok(Math.abs(v-b[i]) < 0.000002));
test('published OKLab reference controls include white, black and red', () => {
  close(colorLab('#ffffff'),[1,0,0]); close(colorLab('#000000'),[0,0,0]);
  close(colorLab('#ff0000'),[0.62795536,0.22486306,0.12584630]);
});
test('full-severity models preserve achromatic controls and reduce red/green separation', () => {
  for (const model of visionModels) close(colorLab('#ffffff',model),[1,0,0]);
  const d = colorDifferences('#ff0000','#00ff00'); assert.ok(d.deuteranopia < d.normal);
  for (const value of Object.values(colorDifferences('#123456','#123456'))) assert.equal(value,0);
  assert.throws(() => colorLab('#ffffff','unsupported'),/Unknown/);
});
test('generated HSL colors decode consistently and malformed colors are rejected', () => {
  assert.deepEqual(cssRGB('hsl(0 100% 50%)'),[255,0,0]); assert.deepEqual(cssRGB('hsl(120 100% 50%)'),[0,255,0]);
  assert.throws(() => cssRGB('red'),/Use/); assert.throws(() => cssRGB('hsl(0 200% 50%)'),/bounds/);
});
test('source-name display distinction preserves entity identity without ambiguous concatenation', () => {
  const id = 'owner:Q148'; assert.notEqual(displayCategoryKey(id,"People's Republic of China"),displayCategoryKey(id,'Republic of China'));
  assert.equal(JSON.parse(displayCategoryKey(id,'Republic of China'))[0],id);
  assert.equal(displayCategoryKey(null,'Unknown'),null); assert.equal(displayCategoryKey('climate:Af'),'climate:Af');
  assert.equal(displayCategoryKey('x',' e\u0301 '),displayCategoryKey('x','é'));
  assert.notEqual(displayCategoryKey('x/y','z'),displayCategoryKey('x','y/z'));
});
