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
export function createRenderer(canvas, meta, data) {
  const gl = canvas.getContext('webgl2', { alpha: false, antialias: false, depth: false, stencil: false });
  if (!gl) throw Error('This viewer requires WebGL 2. Please enable hardware acceleration.');
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
    if (cell.x < 0 || cell.y < 0 || cell.x >= uWorld.x || cell.y >= uWorld.y) { color=vec4(0.91,0.94,0.95,1.0); return; }
    int lo = int(rowWord(cell.y)), hi = int(rowWord(cell.y + 1));
    for (int i=0; i<24; i++) {
      if (lo >= hi) break;
      int mid = (lo + hi) / 2;
      if (int(runWord(mid * 2)) <= cell.x) lo=mid+1; else hi=mid;
    }
    uint value = runWord(lo * 2 + 1);
    vec3 rgb = uPalette[int(value)];
    if (uCssScale >= 9.0 && min(fract(position.x),fract(position.y)) < 0.5/uCssScale) rgb=mix(rgb,vec3(1.0),0.22);
    if (uSelected.x >= 0) {
      float ratio=uScale/uCssScale;
      vec2 q=screen-(uOffset+vec2(uSelected)*uScale);
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
