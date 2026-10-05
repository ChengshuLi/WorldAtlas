// Continuous camera movement using the same Leaflet 1.9.4 primitives as TouchZoom.
// Geography and ownership remain cached in the renderers; only the camera changes.
export function wheelPixels(event, height) {
  return event.deltaY * (event.deltaMode === 1 ? 40 : event.deltaMode === 2 ? height : 1);
}

export function nextZoom(current, target, elapsed) {
  const next = current + (target - current) * (1 - Math.exp(-elapsed / 45));
  return Math.abs(target - next) < 0.001 ? target : next;
}

export function installWheelZoom(map) {
  const container = map.getContainer();
  let active = false, target, anchor, pointer, lastTime, pending, direction, moving = false;
  const finish = () => {
    cancelAnimationFrame(pending);
    if (!active) return;
    active = false;
    container.classList.remove('atlas-wheel-zoom');
    moving = true;
    map._moveEnd(true);
    moving = false;
  };
  const tick = time => {
    const zoom = nextZoom(map.getZoom(), target, Math.min(time - lastTime, 64));
    lastTime = time;
    const offset = pointer.subtract(map.getSize().divideBy(2));
    const center = map.unproject(map.project(anchor, zoom).subtract(offset), zoom);
    moving = true;
    map._move(map._limitCenter(center, zoom, map.options.maxBounds), zoom, {pinch:true, round:false});
    moving = false;
    if (zoom === target) finish();
    else pending = requestAnimationFrame(tick);
  };
  const wheel = event => {
    // Let the browser handle its own zoom gestures and horizontal scrolling.
    if (event.ctrlKey || event.metaKey || !event.deltaY) return;
    event.preventDefault();
    event.stopPropagation();
    const delta = -wheelPixels(event, map.getSize().y) / 80;
    const sign = Math.sign(delta);
    const starting = !active;
    if (starting) {
      map._stop();
      if (map._animatingZoom) map._onZoomTransitionEnd();
      target = map.getZoom();
      lastTime = performance.now();
      active = true;
      container.classList.add('atlas-wheel-zoom');
      moving = true;
      map._moveStart(true, false);
      moving = false;
    } else if (sign !== direction) {
      // A reversal responds immediately instead of paying off old momentum.
      target = map.getZoom();
    }
    direction = sign;
    const nextPointer = map.mouseEventToContainerPoint(event);
    if (starting || !nextPointer.equals(pointer)) {
      pointer = nextPointer;
      anchor = map.containerPointToLatLng(pointer);
    }
    target = Math.max(map.getMinZoom(), Math.min(map.getMaxZoom(), target + delta));
    cancelAnimationFrame(pending);
    pending = requestAnimationFrame(tick);
  };
  const externalMove = () => { if (!moving) finish(); };
  container.addEventListener('wheel', wheel, {passive:false});
  container.addEventListener('pointerdown', finish);
  map.on('movestart resize', externalMove);
  const remove = () => {
    finish();
    container.removeEventListener('wheel', wheel);
    container.removeEventListener('pointerdown', finish);
    map.off('movestart resize', externalMove);
    map.off('unload', remove);
  };
  map.on('unload', remove);
  return remove;
}
