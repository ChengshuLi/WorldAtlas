import { loadLocalGrid, cellValue, wrapColumn } from './grid-data.js';
import { createRenderer } from './grid-renderer.js';
import { makeLegendItems, matchingLegendItems, toggleSelection, activeCategoryMask } from './legend-model.js';

const $ = (selector) => document.querySelector(selector);
const map = $('#map');
const canvas = $('#canvas');
const status = $('#status');

let meta, data, renderer;
let items = [];
let selectedGroups = new Set();
let hoveredGroup = null;
let selectedCell = null;
let scale = 1;
let ox = 0;
let oy = 0;
let dpr = 1;
let drag = null;
let drawing = false;

function minScale() {
  return Math.min(map.clientWidth / meta.width, map.clientHeight / meta.height);
}

function constrain() {
  if (!meta) return;
  scale = Math.max(minScale(), scale);
  const period = meta.width * scale;
  ox %= period;
  if (ox > 0) ox -= period;

  const height = meta.height * scale;
  const viewportHeight = map.clientHeight;
  oy = height <= viewportHeight
    ? (viewportHeight - height) / 2
    : Math.min(0, Math.max(viewportHeight - height, oy));
}

function fitWorld() {
  if (!meta) return;
  scale = minScale();
  ox = (map.clientWidth - meta.width * scale) / 2;
  oy = (map.clientHeight - meta.height * scale) / 2;
  constrain();
  requestDraw();
}

function zoom(factor, x = map.clientWidth / 2, y = map.clientHeight / 2) {
  if (!meta) return;
  const nextScale = Math.max(minScale(), Math.min(36, scale * factor));
  ox = x - (x - ox) * nextScale / scale;
  oy = y - (y - oy) * nextScale / scale;
  scale = nextScale;
  constrain();
  requestDraw();
}

function requestDraw() {
  if (drawing) return;
  drawing = true;
  requestAnimationFrame(() => {
    drawing = false;
    if (!renderer) return;
    constrain();
    renderer.draw({
      scale, ox, oy, dpr,
      selected: selectedCell,
      activeMask: activeCategoryMask(items, selectedGroups, hoveredGroup),
      outlineMask: activeCategoryMask(items, selectedGroups),
    });
  });
}

function resize() {
  dpr = Math.min(devicePixelRatio || 1, 2);
  canvas.width = Math.round(map.clientWidth * dpr);
  canvas.height = Math.round(map.clientHeight * dpr);
  if (renderer) requestDraw();
}

function cellAt(px, py) {
  const x = wrapColumn(Math.floor((px - ox) / scale), meta.width);
  const y = Math.floor((py - oy) / scale);
  return y >= 0 && y < meta.height ? { x, y } : null;
}

function selectCell(cell) {
  selectedCell = cell;
  const selection = $('#selection');
  if (cell) {
    const value = cellValue(data.rows, data.runs, cell.x, cell.y);
    const category = meta.categories.find((entry) => entry.id === value);
    const lon = -180 + (cell.x + 0.5) * meta.step;
    const lat = 90 - (cell.y + 0.5) * meta.step;
    selection.textContent = `Cell ${cell.x}, ${cell.y} · ${lat.toFixed(5)}°, ${lon.toFixed(5)}° · ${category?.name || 'Unknown'} (${category?.physical_class || 'unknown'})`;
  } else {
    selection.textContent = 'Click a cell to select it.';
  }
  requestDraw();
}

function renderLegend() {
  const list = $('#legend-list');
  list.replaceChildren();
  const visible = matchingLegendItems(items, $('#legend-search').value);
  if (!visible.length) {
    const empty = document.createElement('div');
    empty.className = 'legend-empty';
    empty.textContent = 'No matching continents.';
    list.append(empty);
    return;
  }

  for (const item of visible) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'legend-item';
    button.setAttribute('aria-pressed', String(selectedGroups.has(item.id)));

    const swatch = document.createElement('i');
    swatch.className = 'swatch';
    swatch.style.backgroundColor = `rgb(${item.color.join(',')})`;
    swatch.setAttribute('aria-hidden', 'true');

    const name = document.createElement('span');
    name.className = 'legend-name';
    name.textContent = item.name;

    const count = document.createElement('span');
    count.className = 'legend-count';
    count.textContent = Number(item.count).toLocaleString() + ' cells';
    button.append(swatch, name, count);

    function highlight() {
      hoveredGroup = item.id;
      requestDraw();
    }

    function clearHighlight() {
      hoveredGroup = null;
      requestDraw();
    }

    button.addEventListener('pointerenter', highlight);
    button.addEventListener('pointerleave', clearHighlight);
    button.addEventListener('focus', highlight);
    button.addEventListener('blur', clearHighlight);
    button.addEventListener('click', () => {
      selectedGroups = toggleSelection(selectedGroups, item.id);
      hoveredGroup = null;
      renderLegend();
      requestDraw();
    });
    list.append(button);
  }

  $('#legend-clear').hidden = selectedGroups.size === 0;
}

function setLegend(open) {
  $('#legend-panel').hidden = !open;
  const toggle = $('#legend-toggle');
  toggle.hidden = open;
  toggle.setAttribute('aria-expanded', String(open));
  hoveredGroup = null;
  requestDraw();
  (open ? $('#legend-search') : toggle).focus({ preventScroll: true });
}

function bindLegendControls() {
  $('#legend-collapse').addEventListener('click', () => setLegend(false));
  $('#legend-toggle').addEventListener('click', () => setLegend(true));
  $('#legend-search').addEventListener('input', renderLegend);
  $('#legend-clear').addEventListener('click', () => {
    selectedGroups.clear();
    hoveredGroup = null;
    renderLegend();
    requestDraw();
  });
}

function bindMapControls() {
  $('#tool-in').addEventListener('click', () => zoom(2));
  $('#tool-out').addEventListener('click', () => zoom(0.5));
  $('#tool-world').addEventListener('click', fitWorld);

  canvas.addEventListener('pointerdown', (event) => {
    if (!data) return;
    canvas.focus({ preventScroll: true });
    canvas.setPointerCapture(event.pointerId);
    drag = { id: event.pointerId, x: event.offsetX, y: event.offsetY, ox, oy, moved: 0 };
  });
  canvas.addEventListener('pointermove', (event) => {
    if (!data || drag?.id !== event.pointerId) return;
    const dx = event.offsetX - drag.x;
    const dy = event.offsetY - drag.y;
    drag.moved = Math.max(drag.moved, Math.hypot(dx, dy));
    ox = drag.ox + dx;
    oy = drag.oy + dy;
    requestDraw();
  });
  canvas.addEventListener('pointerup', (event) => {
    if (drag?.id === event.pointerId && drag.moved < 5) {
      selectCell(cellAt(event.offsetX, event.offsetY));
    }
    drag = null;
  });
  canvas.addEventListener('pointercancel', () => {
    drag = null;
  });
  canvas.addEventListener('wheel', (event) => {
    if (!data) return;
    event.preventDefault();
    zoom(Math.exp(-event.deltaY * 0.002), event.offsetX, event.offsetY);
  }, { passive: false });
  canvas.addEventListener('keydown', (event) => {
    if (!data || event.defaultPrevented || event.isComposing || event.ctrlKey || event.metaKey || event.altKey) return;
    const key = event.key.toLowerCase();
    if (key === 'tab' && !event.shiftKey) {
      event.preventDefault();
      fitWorld();
      return;
    }
    if (key === '+' || key === '=') {
      event.preventDefault();
      zoom(2);
      return;
    }
    if (key === '-') {
      event.preventDefault();
      zoom(0.5);
      return;
    }
    const delta = { w: [0, 64], a: [64, 0], s: [0, -64], d: [-64, 0] }[key];
    if (delta) {
      event.preventDefault();
      ox += delta[0];
      oy += delta[1];
      constrain();
      requestDraw();
    }
  });
}

async function startViewer() {
  try {
    const configURL = new URL('./config.json', import.meta.url);
    const response = await fetch(configURL);
    if (!response.ok) throw Error('Map configuration could not load');
    meta = await response.json();
    meta.palette = Array.from({ length: 32 }, () => [0, 0, 0]);
    for (const category of meta.categories) {
      const rgb = category.physical_class === 'water' ? meta.water_rgb : category.rgb;
      if (!rgb) throw Error('Map configuration is missing a category color');
      meta.palette[category.id] = rgb;
    }
    data = await loadLocalGrid(meta, configURL);
    if (meta.map_version) {
      const release = $('#map-release');
      release.textContent = `${meta.map_version.toUpperCase()} · SHA-256 ${meta.combined_sha256.slice(0, 12)}`;
      release.title = `SHA-256 of the decoded rows and runs. Full hash: ${meta.combined_sha256}`;
    }
    renderer = createRenderer(canvas, meta, data);
    items = makeLegendItems(meta.categories, meta.counts, meta.water_rgb);
    renderLegend();
    resize();
    fitWorld();
    status.textContent = '';
  } catch (error) {
    status.textContent = error?.message || String(error);
    status.classList.add('error');
  }
}

bindLegendControls();
bindMapControls();
new ResizeObserver(resize).observe(map);
await startViewer();

canvas.addEventListener('webglcontextlost', (event) => {
  event.preventDefault();
  renderer?.destroy?.();
  renderer = null;
  data = null;
  status.textContent = 'Graphics context lost. Reload to restore the map.';
  status.classList.add('error');
});
window.addEventListener('pagehide', () => renderer?.destroy?.(), { once: true });
