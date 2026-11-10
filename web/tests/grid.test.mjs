import assert from 'node:assert/strict';
import test from 'node:test';
import { cellValue, validateGrid, wrapColumn } from '../viewer/grid-data.js';
import { gridFitsTexture, renderPixels } from '../viewer/grid-renderer.js';

const meta = { width: 4, height: 2, local_grid: { run_count: 4 } };
const rows = Uint32Array.of(0, 2, 4);
const runs = Uint32Array.of(2, 1, 4, 17, 1, 2, 4, 18);

test('native runs pick the correct cell on each side of a run boundary and the dateline', () => {
  validateGrid(meta, rows, runs);
  const pick = (x, y) => cellValue(rows, runs, wrapColumn(x, meta.width), y);
  assert.deepEqual([-1, 0, 1, 2, 3, 4].map((x) => pick(x, 0)), [17, 1, 1, 17, 17, 1]);
  assert.deepEqual([0, 1, 2, 3].map((x) => pick(x, 1)), [2, 18, 18, 18]);
});

test('grid validation rejects malformed offsets, runs, and category codes', () => {
  assert.throws(() => validateGrid(meta, Uint32Array.of(1, 2, 4), runs), /dimensions/);
  assert.throws(() => validateGrid(meta, Uint32Array.of(0, 0, 4), runs), /Empty native row/);
  assert.throws(() => validateGrid(meta, rows, runs.subarray(0, 6)), /dimensions/);
  for (const [index, replacement, error] of [
    [2, 2, /Invalid native run/],
    [2, 5, /Invalid native run/],
    [2, 3, /Native row is incomplete/],
    [3, 16, /Invalid native run/],
  ]) {
    const altered = runs.slice();
    altered[index] = replacement;
    assert.throws(() => validateGrid(meta, rows, altered), error);
  }
});

test('the CPU renderer repeats the map at the dateline and mutes filtered cells', () => {
  const palette = Array.from({ length: 32 }, (_, id) => [id, 0, 0]);
  const rgb = (r, g = 0, b = 0) => (0xff000000 | b << 16 | g << 8 | r) >>> 0;
  const pixels = (mask) => [...renderPixels({ ...meta, palette }, { rows, runs }, 6, 1, 1, 1, 0, mask)];
  assert.deepEqual(pixels(0), [17, 1, 1, 17, 17, 1].map((id) => rgb(id)));
  assert.deepEqual(pixels(1 << 17), [17, 1, 1, 17, 17, 1].map((id) => (
    id === 17 ? rgb(id) : rgb(Math.round(id * 0.55))
  )));
  assert.equal(gridFitsTexture(4, 16, 16), true);
  assert.equal(gridFitsTexture(4, 16, 17), false);
});

test('the outline follows selection coverage across land, water, and adjacent entities', () => {
  const palette = Array.from({ length: 32 }, (_, id) => [id, 0, 0]);
  const data = {
    rows: Uint32Array.of(0, 4),
    runs: Uint32Array.of(1, 1, 2, 17, 3, 18, 4, 7),
  };
  const africa = (1 << 1) | (1 << 17);
  const asia = 1 << 18;
  const render = mask => renderPixels({ ...meta, height: 1, palette }, data, 8, 1, 2, 0, 0, mask, mask);
  assert.equal(render(africa)[1], 0xff000001);
  assert.equal(render(africa)[3], 0xffffffff);
  assert.equal(render(africa | asia)[3], 0xff000011);
  assert.equal(render(africa | asia)[5], 0xffffffff);
});
