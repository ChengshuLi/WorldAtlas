import { loadLocalGrid, cellValue, wrapColumn } from "./grid-data.js";
import { createRenderer, replaceWithCanvas } from "./grid-renderer.js";
import {
  makeLegendItems,
  matchingLegendItems,
  toggleSelection,
  activeCategoryCodes,
} from "./legend-model.js";

const $ = (selector) => document.querySelector(selector);
const map = $("#map");
let canvas = $("#canvas");
const status = $("#status");

let meta, data, renderer;
let items = [];
let selectedGroups = new Set();
let hoveredGroup = null;
let selectedCell = null;
let scale = 1;
let ox = 0;
let oy = 0;
let dpr = 1;
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
  oy =
    height <= viewportHeight
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

function zoom(
  factor,
  x = map.clientWidth / 2,
  y = map.clientHeight / 2,
  nextX = x,
  nextY = y,
) {
  if (!meta) return;
  const nextScale = Math.max(minScale(), Math.min(36, scale * factor));
  ox = nextX - ((x - ox) * nextScale) / scale;
  oy = nextY - ((y - oy) * nextScale) / scale;
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
      scale,
      ox,
      oy,
      dpr,
      selected: selectedCell,
      activeCodes: activeCategoryCodes(items, selectedGroups, hoveredGroup),
      outlineCodes: activeCategoryCodes(items, selectedGroups),
    });
  });
}

function resize() {
  dpr = Math.min(devicePixelRatio || 1, 2);
  canvas.width = Math.round(map.clientWidth * dpr);
  canvas.height = Math.round(map.clientHeight * dpr);
  if (renderer) requestDraw();
}

function cellAt(clientX, clientY) {
  const bounds = canvas.getBoundingClientRect();
  const px = Math.floor((clientX - bounds.left) * canvas.width / bounds.width);
  const py = Math.floor((clientY - bounds.top) * canvas.height / bounds.height);
  if (px < 0 || px >= canvas.width || py < 0 || py >= canvas.height) return null;

  // Both renderers sample the center of each backing pixel.
  const pixelScale = scale * dpr;
  const x = wrapColumn(Math.floor((px + 0.5 - ox * dpr) / pixelScale), meta.width);
  const y = Math.floor((py + 0.5 - oy * dpr) / pixelScale);
  return y >= 0 && y < meta.height ? { x, y } : null;
}

function selectCell(cell) {
  selectedCell = cell;
  const selection = $("#selection");
  if (cell) {
    const value = cellValue(data.rows, data.runs, cell.x, cell.y);
    const category = meta.categories.find((entry) => entry.id === value);
    const lon = -180 + (cell.x + 0.5) * meta.step;
    const lat = 90 - (cell.y + 0.5) * meta.step;
    selection.textContent = `Cell ${cell.x}, ${cell.y} · ${lat.toFixed(5)}°, ${lon.toFixed(5)}° · ${category?.name || "Unknown"} (${category?.physical_class || "unknown"})`;
  } else {
    selection.textContent = "Click a cell to select it.";
  }
  requestDraw();
}

function renderLegend() {
  const list = $("#legend-list");
  list.replaceChildren();
  const clear = $("#legend-clear");
  clear.hidden = selectedGroups.size === 0;
  const visible = matchingLegendItems(items, $("#legend-search").value);
  if (!visible.length) {
    const empty = document.createElement("div");
    empty.className = "legend-empty";
    empty.textContent = "No matching areas.";
    list.append(empty);
    return;
  }

  for (const item of visible) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "legend-item";
    button.setAttribute("aria-pressed", String(selectedGroups.has(item.id)));

    const swatch = document.createElement("i");
    swatch.className = "swatch";
    swatch.style.backgroundColor = `rgb(${item.color.join(",")})`;
    swatch.setAttribute("aria-hidden", "true");

    const name = document.createElement("span");
    name.className = "legend-name";
    name.textContent = item.name;

    const count = document.createElement("span");
    count.className = "legend-count";
    count.textContent = Number(item.count).toLocaleString() + " cells";
    button.append(swatch, name, count);

    function highlight() {
      hoveredGroup = item.id;
      requestDraw();
    }

    function clearHighlight() {
      hoveredGroup = null;
      requestDraw();
    }

    button.addEventListener("pointerenter", highlight);
    button.addEventListener("pointerleave", clearHighlight);
    button.addEventListener("focus", highlight);
    button.addEventListener("blur", clearHighlight);
    button.addEventListener("click", () => {
      selectedGroups = toggleSelection(selectedGroups, item.id);
      hoveredGroup = null;
      button.setAttribute("aria-pressed", String(selectedGroups.has(item.id)));
      clear.hidden = selectedGroups.size === 0;
      requestDraw();
    });
    list.append(button);
  }
}

function setLegend(open) {
  const panel = $("#legend-panel");
  panel.hidden = !open;
  const toggle = $("#legend-toggle");
  toggle.hidden = open;
  toggle.setAttribute("aria-expanded", String(open));
  hoveredGroup = null;
  requestDraw();
  (open ? panel : toggle).focus({ preventScroll: true });
}

function bindLegendControls() {
  $("#legend-collapse").addEventListener("click", () => setLegend(false));
  $("#legend-toggle").addEventListener("click", () => setLegend(true));
  $("#legend-search").addEventListener("input", () => {
    hoveredGroup = null;
    renderLegend();
    requestDraw();
  });
  $("#legend-clear").addEventListener("click", () => {
    selectedGroups.clear();
    hoveredGroup = null;
    renderLegend();
    $("#legend-panel").focus({ preventScroll: true });
    requestDraw();
  });
}

function bindMapControls() {
  $("#tool-in").addEventListener("click", () => zoom(2));
  $("#tool-out").addEventListener("click", () => zoom(0.5));
  $("#tool-world").addEventListener("click", fitWorld);
  $("#tool-sources").addEventListener("click", () => $("#sources-dialog").showModal());
}

function bindCanvasControls() {
  const pointers = new Map();
  let drag = null;
  let pinch = null;
  const startDrag = ({ x, y }, panning = false) => ({ x, y, ox, oy, panning });

  function measurePinch() {
    const [a, b] = pointers.values();
    return {
      x: (a.x + b.x) / 2,
      y: (a.y + b.y) / 2,
      distance: Math.hypot(b.x - a.x, b.y - a.y),
    };
  }

  canvas.addEventListener("pointerdown", (event) => {
    if (!data || event.button > 0 || pointers.size === 2) return;
    const active = pointers.values().next().value;
    if (active && (active.type !== "touch" || event.pointerType !== "touch")) return;

    const point = { x: event.offsetX, y: event.offsetY, type: event.pointerType };
    canvas.focus({ preventScroll: true });
    canvas.setPointerCapture(event.pointerId);
    pointers.set(event.pointerId, point);
    if (pointers.size === 2) {
      pinch = measurePinch();
      drag = null;
    } else {
      drag = startDrag(point);
    }
  });
  canvas.addEventListener("pointermove", (event) => {
    const point = pointers.get(event.pointerId);
    if (!data || !point) return;
    point.x = event.offsetX;
    point.y = event.offsetY;
    if (pinch) {
      const next = measurePinch();
      if (pinch.distance && next.distance) {
        zoom(next.distance / pinch.distance, pinch.x, pinch.y, next.x, next.y);
      }
      pinch = next;
      return;
    }
    const dx = point.x - drag.x;
    const dy = point.y - drag.y;
    if (!drag.panning && Math.hypot(dx, dy) < 5) return;
    drag.panning = true;
    ox = drag.ox + dx;
    oy = drag.oy + dy;
    requestDraw();
  });
  function finishPointer(event) {
    if (!pointers.delete(event.pointerId)) return;
    if (pinch) {
      pinch = null;
      drag = startDrag(pointers.values().next().value, true);
      return;
    }
    if (event.type === "pointerup" && !drag.panning) {
      selectCell(cellAt(event.clientX, event.clientY));
    }
    drag = null;
  }
  canvas.addEventListener("pointerup", finishPointer);
  canvas.addEventListener("pointercancel", finishPointer);
  canvas.addEventListener("lostpointercapture", finishPointer);
  canvas.addEventListener(
    "wheel",
    (event) => {
      if (!data) return;
      event.preventDefault();
      zoom(Math.exp(-event.deltaY * 0.002), event.offsetX, event.offsetY);
    },
    { passive: false },
  );
  canvas.addEventListener("keydown", (event) => {
    if (
      !data ||
      event.defaultPrevented ||
      event.isComposing ||
      event.ctrlKey ||
      event.metaKey ||
      event.altKey
    )
      return;
    const key = event.key.toLowerCase();
    if (key === "+" || key === "=") {
      event.preventDefault();
      zoom(2);
      return;
    }
    if (key === "-") {
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
  canvas.addEventListener("webglcontextlost", (event) => {
    event.preventDefault();
    pointers.clear();
    renderer.destroy();
    try {
      setRenderer(replaceWithCanvas(canvas, meta, data));
      requestDraw();
    } catch (error) {
      renderer = null;
      data = null;
      showError(error);
    }
  }, { once: true });
}

function setRenderer(next) {
  renderer = next;
  canvas = renderer.canvas;
  bindCanvasControls();
}

function showError(error) {
  status.textContent = error?.message || String(error);
  status.classList.add("error");
}

async function startViewer() {
  try {
    const configURL = new URL("./config.json", import.meta.url);
    const response = await fetch(configURL);
    if (!response.ok) throw Error("Map configuration could not load");
    meta = await response.json();
    const legendResponse = await fetch(new URL(meta.legend, configURL));
    if (!legendResponse.ok) throw Error("Map legend could not load");
    items = makeLegendItems(await legendResponse.json(), meta.categories);
    const entities = new Map(items.map((item) => [item.id, item]));
    meta.palette = new Map();
    for (const category of meta.categories) {
      const entity = entities.get(category.entity_id);
      const rgb =
        category.physical_class === "water" ? meta.water_rgb : entity.color;
      if (!rgb) throw Error("Map configuration is missing a category color");
      category.name = entity.name;
      meta.palette.set(category.id, rgb);
    }
    const grid = await loadLocalGrid(meta, configURL);
    if (meta.map_version) {
      const release = $("#map-release");
      release.textContent = `${meta.map_version.toUpperCase()} · SHA-256 ${meta.combined_sha256.slice(0, 12)}`;
      release.title = `SHA-256 of the decoded rows and runs. Full hash: ${meta.combined_sha256}`;
    }
    setRenderer(createRenderer(canvas, meta, grid));
    data = grid;
    renderLegend();
    resize();
    fitWorld();
    status.textContent = "";
  } catch (error) {
    showError(error);
  }
}

bindLegendControls();
bindMapControls();
new ResizeObserver(resize).observe(map);
await startViewer();

window.addEventListener("pagehide", (event) => {
  if (!event.persisted) renderer?.destroy();
});
