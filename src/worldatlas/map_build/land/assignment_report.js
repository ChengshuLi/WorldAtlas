/* Local report: draw real native-grid cell runs and keep both maps synchronized. */
const data = JSON.parse(document.getElementById('data').textContent);
const canvases = ['source', 'result'].map(id => document.getElementById(id));
let view = [...data.bounds];
function draw() {
  canvases.forEach((canvas, panel) => {
    const width = Math.max(360, canvas.clientWidth), height = 560;
    const ratio = window.devicePixelRatio || 1;
    canvas.width = width * ratio; canvas.height = height * ratio;
    const context = canvas.getContext('2d'); context.scale(ratio, ratio);
    context.fillStyle = '#eef5fa'; context.fillRect(0, 0, width, height);
    const scale = Math.min(width / view[2], height / view[3]);
    const ox = (width - view[2] * scale) / 2, oy = (height - view[3] * scale) / 2;
    const x = value => ox + (value - view[0]) * scale;
    const y = value => oy + (value - view[1]) * scale;
    const shifts = [-data.grid.width, 0, data.grid.width];
    function spans(values, color, rowHeight) {
      context.fillStyle = color;
      for (const [a, b, row] of values) {
        if (row + rowHeight < view[1] || row > view[1] + view[3]) continue;
        for (const shift of shifts) {
          if (b + shift < view[0] || a + shift > view[0] + view[2]) continue;
          context.fillRect(x(a + shift), y(row), (b - a) * scale, rowHeight * scale);
        }
      }
    }
    spans(data.context, '#d2d7db', data.context_stride);
    if (panel) spans(data.cells, data.color, 1);
    context.strokeStyle = '#235a9c'; context.lineWidth = panel ? 1 : 1.8;
    function path(points, shift, close) {
      context.beginPath();
      points.forEach(([lon, lat], i) => {
        const px = x((lon - data.grid.west) / data.grid.step + shift);
        const py = y((data.grid.north - lat) / data.grid.step);
        if (i) context.lineTo(px, py); else context.moveTo(px, py);
      });
      if (close) context.closePath();
      context.stroke();
    }
    for (const geometry of data.geometries) {
      for (const shift of shifts) {
        if (geometry.type === 'Point') {
          const [lon, lat] = geometry.coordinates;
          const px = x((lon - data.grid.west) / data.grid.step + shift);
          const py = y((data.grid.north - lat) / data.grid.step);
          context.beginPath(); context.arc(px, py, 5, 0, 2 * Math.PI); context.stroke();
          context.beginPath(); context.moveTo(px - 9, py); context.lineTo(px + 9, py);
          context.moveTo(px, py - 9); context.lineTo(px, py + 9); context.stroke();
        } else if (geometry.type === 'Polygon') {
          geometry.coordinates.forEach(ring => path(ring, shift, true));
        } else if (geometry.type === 'MultiPolygon') {
          geometry.coordinates.forEach(polygon => polygon.forEach(ring => path(ring, shift, true)));
        } else if (geometry.type === 'LineString') {
          path(geometry.coordinates, shift, false);
        }
      }
    }
    context.fillStyle = '#183242'; context.font = 'bold 15px system-ui';
    context.fillText(panel ? `Assigned to ${data.entity}` : 'Source geometry', 14, 24);
  });
  const lon = x => ((data.grid.west + x * data.grid.step + 180) % 360 + 360) % 360 - 180;
  document.getElementById('extent').textContent =
    `View: ${lon(view[0]).toFixed(5)}° to ${lon(view[0] + view[2]).toFixed(5)}° longitude; ` +
    `${(data.grid.north - (view[1] + view[3]) * data.grid.step).toFixed(5)}° to ` +
    `${(data.grid.north - view[1] * data.grid.step).toFixed(5)}° latitude.`;
}
for (const canvas of canvases) {
  canvas.addEventListener('wheel', event => {
    event.preventDefault();
    const rect = canvas.getBoundingClientRect();
    const scale = Math.min(rect.width / view[2], 560 / view[3]);
    const fx = (event.clientX - rect.left - (rect.width - view[2] * scale) / 2) / scale;
    const fy = (event.clientY - rect.top - (560 - view[3] * scale) / 2) / scale;
    const factor = event.deltaY > 0 ? 1.3 : 1 / 1.3;
    view = [view[0] + fx * (1 - factor), view[1] + fy * (1 - factor), view[2] * factor, view[3] * factor];
    draw();
  }, {passive: false});
  let drag;
  canvas.addEventListener('pointerdown', event => {
    canvas.setPointerCapture(event.pointerId); drag = [event.clientX, event.clientY, ...view];
  });
  canvas.addEventListener('pointermove', event => {
    if (!drag) return;
    const scale = Math.min(canvas.clientWidth / drag[4], 560 / drag[5]);
    view = [drag[2] - (event.clientX - drag[0]) / scale,
      drag[3] - (event.clientY - drag[1]) / scale, drag[4], drag[5]]; draw();
  });
  canvas.addEventListener('pointerup', () => { drag = null; });
  canvas.addEventListener('pointercancel', () => { drag = null; });
}
document.getElementById('reset').onclick = () => { view = [...data.bounds]; draw(); };
document.getElementById('save').onclick = () => {
  const image = document.createElement('canvas');
  image.width = canvases[0].width * 2; image.height = canvases[0].height;
  const context = image.getContext('2d');
  canvases.forEach((canvas, i) => context.drawImage(canvas, i * canvases[0].width, 0));
  const link = document.createElement('a'); link.download = `${data.number}-assignment.png`;
  link.href = image.toDataURL('image/png'); link.click();
};
window.addEventListener('resize', draw);
draw();
