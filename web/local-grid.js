export function wrapColumn(x,width) { return ((x % width) + width) % width; }
// Lossless native-cell data. Every row stores ordered [exclusiveEndX, value] runs.
export function validateGrid(meta, rows, runs) {
  if (rows.length !== meta.height + 1 || rows[0] !== 0 || runs.length !== meta.local_grid.run_count * 2 || rows[meta.height] !== meta.local_grid.run_count)
    throw Error('Native grid dimensions do not match');
  for (let y = 0; y < meta.height; y++) {
    if (rows[y + 1] <= rows[y]) throw Error('Empty native row');
    let end = 0;
    for (let r = rows[y]; r < rows[y + 1]; r++) {
      const next = runs[2 * r], value = runs[2 * r + 1];
      if (next <= end || next > meta.width || (value & 15) < 1 || (value & 15) > 10 || value > 26)
        throw Error('Invalid native run');
      end = next;
    }
    if (end !== meta.width) throw Error('Native row is incomplete');
  }
}
export function cellValue(rows, runs, x, y) {
  let lo = rows[y], hi = rows[y + 1];
  while (lo < hi) {
    const mid = (lo + hi) >>> 1;
    if (runs[2 * mid] <= x) lo = mid + 1;
    else hi = mid;
  }
  return runs[2 * lo + 1];
}
export async function loadLocalGrid(meta, base) {
  async function load(name) {
    const response = await fetch(new URL(meta.local_grid[name], base));
    if (!response.ok) throw Error('Native map could not load');
    const stream = response.body.pipeThrough(new DecompressionStream('gzip'));
    const buffer = await new Response(stream).arrayBuffer();
    const hash = [...new Uint8Array(await crypto.subtle.digest('SHA-256', buffer))].map(v => v.toString(16).padStart(2, '0')).join('');
    if (hash !== meta.local_grid[name + '_sha256']) throw Error('Native map checksum mismatch');
    return new Uint32Array(buffer);
  }
  const [rows, runs] = await Promise.all([load('rows'), load('runs')]);
  validateGrid(meta, rows, runs);
  return { rows, runs };
}
// Canvas fallback renders the same fully loaded native runs, never an overview.
export function renderPixels(meta, data, width, height, scale, ox, oy) {
  const pixels = new Uint32Array(width * height);
  const colors = meta.palette.map(rgb => (255 << 24 | rgb[2] << 16 | rgb[1] << 8 | rgb[0]) >>> 0);
  let previousY = -999;
  for (let py = 0; py < height; py++) {
    const y = Math.floor((py + 0.5 - oy) / scale), offset = py * width;
    if (y === previousY && py > 0) { pixels.copyWithin(offset, offset - width, offset); continue; }
    previousY = y;
    if (y < 0 || y >= meta.height) { pixels.fill(0xfff2ece6, offset, offset + width); continue; }
    const period=meta.width*scale;
    // Correct boundary rounding against the same expression used by picking.
    const boundaryPixel=(cell)=>{
      let p=Math.ceil(ox+cell*scale-0.5);
      while(Math.floor((p+0.5-ox)/scale)<cell)p++;
      while(Math.floor((p-0.5-ox)/scale)>=cell)p--;
      return p;
    };
    const first=Math.floor((0.5-ox)/period),last=Math.floor((width-0.5-ox)/period);
    for(let copy=first;copy<=last;copy++) {
      const offsetX=ox+copy*period;
      const left=Math.max(0,Math.floor((0.5-ox)/scale)-copy*meta.width);
      let lo=data.rows[y],hi=data.rows[y+1];
      while(lo<hi){const mid=(lo+hi)>>>1;if(data.runs[mid*2]<=left)lo=mid+1;else hi=mid;}
      let start=Math.max(0,boundaryPixel(copy*meta.width));
      for(let r=lo;r<data.rows[y+1]&&start<width;r++) {
        const end=Math.min(width,Math.max(0,boundaryPixel(copy*meta.width+data.runs[r*2])));
        if(end>start)pixels.fill(colors[data.runs[r*2+1]],offset+start,offset+end);
        start=end;
      }
    }
  }
  return pixels;
}
export function gridLinePixels(offset, scale, extent, worldSize, repeat=false) {
  const result=[];
  const first=repeat?Math.floor(-offset/scale):Math.max(0,Math.floor(-offset/scale));
  const last=repeat?Math.ceil((extent-offset)/scale):Math.min(worldSize,Math.ceil((extent-offset)/scale));
  for(let cell=first;cell<=last;cell++) {
    const pixel=Math.floor(offset+cell*scale);
    if(pixel>=0 && pixel<extent) result.push(pixel);
  }
  return result;
}
function canvasRenderer(canvas, meta, data) {
  const ctx = canvas.getContext('2d', {alpha:false});
  if (!ctx) throw Error('No supported map rendering context');
  return { draw({scale,ox,oy,dpr,selected}) {
    const pixels = renderPixels(meta,data,canvas.width,canvas.height,scale*dpr,ox*dpr,oy*dpr);
    ctx.setTransform(1,0,0,1,0,0);
    ctx.putImageData(new ImageData(new Uint8ClampedArray(pixels.buffer),canvas.width,canvas.height),0,0);
    ctx.setTransform(dpr,0,0,dpr,0,0);
    const w=canvas.width/dpr,h=canvas.height/dpr;
    if(scale>=9){
      ctx.setTransform(1,0,0,1,0,0);ctx.fillStyle='#ffffff66';
      for(const x of gridLinePixels(ox*dpr,scale*dpr,canvas.width,meta.width,true)) ctx.fillRect(x,0,1,canvas.height);
      for(const y of gridLinePixels(oy*dpr,scale*dpr,canvas.height,meta.height)) ctx.fillRect(0,y,canvas.width,1);
      ctx.setTransform(dpr,0,0,dpr,0,0);
    }
    if(selected){
      ctx.strokeStyle='#182c3c';ctx.lineWidth=2;const period=meta.width*scale;
      for(let copy=Math.floor(-ox/period)-1;copy<=Math.ceil((w-ox)/period)+1;copy++)
        ctx.strokeRect(ox+(selected.x+copy*meta.width)*scale,oy+selected.y*scale,Math.max(scale,3),Math.max(scale,3));
    }
  }};
}
export function createRenderer(canvas, meta, data) {
  const gl = canvas.getContext('webgl2', { alpha: false, antialias: false, depth: false, stencil: false });
  if (!gl) return canvasRenderer(canvas, meta, data);
  const vertex = `#version 300 es
  void main() {
    vec2 p = vec2(float((gl_VertexID << 1) & 2), float(gl_VertexID & 2));
    gl_Position = vec4(p * 2.0 - 1.0, 0.0, 1.0);
  }`;
  const fragment = `#version 300 es
  precision highp float;
  precision highp int;
  precision highp usampler2D;
  uniform usampler2D uRows;
  uniform usampler2D uRuns;
  uniform int uTextureWidth;
  uniform ivec2 uWorld;
  uniform vec2 uViewport;
  uniform vec2 uOffset;
  uniform float uScale;
  uniform float uCssScale;
  uniform ivec2 uSelected;
  uniform vec3 uPalette[32];
  out vec4 color;
  uint rowWord(int i) { return texelFetch(uRows, ivec2(i % uTextureWidth, i / uTextureWidth), 0).r; }
  uint runWord(int i) { return texelFetch(uRuns, ivec2(i % uTextureWidth, i / uTextureWidth), 0).r; }
  void main() {
    vec2 screen = vec2(gl_FragCoord.x, uViewport.y - gl_FragCoord.y);
    vec2 position = (screen - uOffset) / uScale;
    ivec2 cell = ivec2(floor(position));
    cell.x=((cell.x % uWorld.x)+uWorld.x)%uWorld.x;
    if (cell.y < 0 || cell.y >= uWorld.y) { color=vec4(0.91,0.94,0.95,1.0); return; }
    int lo = int(rowWord(cell.y)), hi = int(rowWord(cell.y + 1));
    for (int i=0; i<24; i++) {
      if (lo >= hi) break;
      int mid = (lo + hi) / 2;
      if (int(runWord(mid * 2)) <= cell.x) lo=mid+1; else hi=mid;
    }
    uint value = runWord(lo * 2 + 1);
    vec3 rgb = uPalette[int(value)];
    if (uCssScale >= 9.0) {
      vec2 nearestBoundary=floor(position+0.5);
      vec2 linePixel=floor(uOffset+nearestBoundary*uScale)+0.5;
      vec2 distanceToLine=abs(screen-linePixel);
      if(min(distanceToLine.x,distanceToLine.y)<0.51) rgb=mix(rgb,vec3(1.0),0.4);
    }
    if (uSelected.x >= 0) {
      float ratio=uScale/uCssScale;
      float selectedX=float(uSelected.x)+floor((position.x-float(uSelected.x))/float(uWorld.x)+0.5)*float(uWorld.x);
      vec2 q=(position-vec2(selectedX,float(uSelected.y)))*uScale;
      float side=max(uScale,3.0*ratio);
      if(q.x>=0.0 && q.y>=0.0 && q.x<side && q.y<side && min(min(q.x,q.y),min(side-q.x,side-q.y))<1.5*ratio) rgb=vec3(0.09,0.17,0.23);
    }
    color=vec4(rgb,1.0);
  }`;
  function shader(type, text) {
    const s=gl.createShader(type); gl.shaderSource(s,text); gl.compileShader(s);
    if(!gl.getShaderParameter(s,gl.COMPILE_STATUS)) throw Error(gl.getShaderInfoLog(s));
    return s;
  }
  const program=gl.createProgram();
  const vs=shader(gl.VERTEX_SHADER,vertex), fs=shader(gl.FRAGMENT_SHADER,fragment);
  gl.attachShader(program,vs);gl.attachShader(program,fs);gl.linkProgram(program);
  if(!gl.getProgramParameter(program,gl.LINK_STATUS)) throw Error(gl.getProgramInfoLog(program));
  gl.deleteShader(vs);gl.deleteShader(fs);gl.useProgram(program);
  const width=Math.min(4096,gl.getParameter(gl.MAX_TEXTURE_SIZE));
  function texture(values, unit, name) {
    const height=Math.ceil(values.length/width);
    if(height>gl.getParameter(gl.MAX_TEXTURE_SIZE)) throw Error('Native grid exceeds this GPU texture capacity');
    const padded=new Uint32Array(width*height);padded.set(values);
    const t=gl.createTexture();gl.activeTexture(gl.TEXTURE0+unit);gl.bindTexture(gl.TEXTURE_2D,t);
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.NEAREST);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.NEAREST);
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);
    gl.texImage2D(gl.TEXTURE_2D,0,gl.R32UI,width,height,0,gl.RED_INTEGER,gl.UNSIGNED_INT,padded);
    gl.uniform1i(gl.getUniformLocation(program,name),unit);
  }
  texture(data.rows,0,'uRows');texture(data.runs,1,'uRuns');
  gl.uniform1i(gl.getUniformLocation(program,'uTextureWidth'),width);
  gl.uniform2i(gl.getUniformLocation(program,'uWorld'),meta.width,meta.height);
  gl.uniform3fv(gl.getUniformLocation(program,'uPalette[0]'),new Float32Array(meta.palette.slice(0,32).flat().map(v=>v/255)));
  const uniforms=Object.fromEntries(['uViewport','uOffset','uScale','uCssScale','uSelected'].map(n=>[n,gl.getUniformLocation(program,n)]));
  if(gl.getError()!==gl.NO_ERROR) throw Error('GPU native map upload failed');
  return {
    draw({scale,ox,oy,dpr,selected}) {
      gl.viewport(0,0,canvas.width,canvas.height);gl.useProgram(program);
      gl.uniform2f(uniforms.uViewport,canvas.width,canvas.height);
      gl.uniform2f(uniforms.uOffset,ox*dpr,oy*dpr);
      gl.uniform1f(uniforms.uScale,scale*dpr);gl.uniform1f(uniforms.uCssScale,scale);
      gl.uniform2i(uniforms.uSelected,selected?.x??-1,selected?.y??-1);
      gl.drawArrays(gl.TRIANGLES,0,3);
    }
  };
}
