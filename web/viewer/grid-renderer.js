const dimBrightness = 0.55;

// Canvas fallback renders the same fully loaded native runs, never an overview.
export function renderPixels(meta, data, width, height, scale, ox, oy, activeMask=0, outlineMask=0, outlineWidth=1) {
  const pixels = new Uint32Array(width * height);
  const selectedPixels = outlineMask ? new Uint8Array(pixels.length) : null;
  const colors = meta.palette.map((rgb, code) => {
    const [r, g, b] = activeMask && !(activeMask & (1 << code))
      ? rgb.map(channel => Math.round(channel * dimBrightness)) : rgb;
    return (0xff000000 | b << 16 | g << 8 | r) >>> 0;
  });
  let previousY = -999;
  for (let py = 0; py < height; py++) {
    const y = Math.floor((py + 0.5 - oy) / scale), offset = py * width;
    if (y === previousY && py > 0) {
      pixels.copyWithin(offset, offset - width, offset);
      selectedPixels?.copyWithin(offset, offset - width, offset);
      continue;
    }
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
      const left=Math.max(0,Math.floor((0.5-ox)/scale)-copy*meta.width);
      let lo=data.rows[y],hi=data.rows[y+1];
      while(lo<hi){const mid=(lo+hi)>>>1;if(data.runs[mid*2]<=left)lo=mid+1;else hi=mid;}
      let start=Math.max(0,boundaryPixel(copy*meta.width));
      for(let r=lo;r<data.rows[y+1]&&start<width;r++) {
        const end=Math.min(width,Math.max(0,boundaryPixel(copy*meta.width+data.runs[r*2])));
        if (end > start) {
          const code = data.runs[r*2+1];
          pixels.fill(colors[code], offset+start, offset+end);
          if (outlineMask & (1 << code)) selectedPixels.fill(1, offset+start, offset+end);
        }
        start=end;
      }
    }
  }
  if (selectedPixels) {
    const vertical = width * outlineWidth;
    for (let i = 0; i < selectedPixels.length; i++) {
      if (!selectedPixels[i]) continue;
      const x = i % width;
      if ((x >= outlineWidth && !selectedPixels[i-outlineWidth])
          || (x + outlineWidth < width && !selectedPixels[i+outlineWidth])
          || (i >= vertical && !selectedPixels[i-vertical])
          || (i + vertical < selectedPixels.length && !selectedPixels[i+vertical])) {
        pixels[i] = 0xffffffff;
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
  let ctx = canvas.getContext('2d', {alpha:false}), currentMeta=meta, currentData=data, disposed=false;
  if (!ctx) throw Error('No supported map rendering context');
  return { draw({scale,ox,oy,dpr,selected,activeMask=0,outlineMask=0}) {
    if(disposed)return;
    const pixels = renderPixels(currentMeta,currentData,canvas.width,canvas.height,scale*dpr,ox*dpr,oy*dpr,
      activeMask,outlineMask,Math.round(dpr));
    ctx.setTransform(1,0,0,1,0,0);
    ctx.putImageData(new ImageData(new Uint8ClampedArray(pixels.buffer),canvas.width,canvas.height),0,0);
    ctx.setTransform(dpr,0,0,dpr,0,0);
    const w=canvas.width/dpr,h=canvas.height/dpr;
    if(scale>=9){
      ctx.setTransform(1,0,0,1,0,0);ctx.fillStyle='#ffffff66';
      for(const x of gridLinePixels(ox*dpr,scale*dpr,canvas.width,currentMeta.width,true)) ctx.fillRect(x,0,1,canvas.height);
      for(const y of gridLinePixels(oy*dpr,scale*dpr,canvas.height,currentMeta.height)) ctx.fillRect(0,y,canvas.width,1);
      ctx.setTransform(dpr,0,0,dpr,0,0);
    }
    if(selected){
      ctx.strokeStyle='#182c3c';ctx.lineWidth=2;const period=currentMeta.width*scale;
      for(let copy=Math.floor(-ox/period)-1;copy<=Math.ceil((w-ox)/period)+1;copy++)
        ctx.strokeRect(ox+(selected.x+copy*currentMeta.width)*scale,oy+selected.y*scale,Math.max(scale,3),Math.max(scale,3));
    }
  }, destroy(){if(disposed)return;disposed=true;currentData=null;currentMeta=null;ctx=null;}};
}
export function gridFitsTexture(maxSize, rowWords, runWords) {
  const width = Math.min(4096, maxSize);
  return width > 0 && Math.ceil(rowWords / width) <= maxSize && Math.ceil(runWords / width) <= maxSize;
}
export function createRenderer(canvas, meta, data) {
  // Check capacity before binding the display canvas to WebGL: a canvas cannot
  // switch to a 2D context afterward. Low-capacity GPUs use the same RLE data.
  const probe = typeof OffscreenCanvas !== 'undefined' ? new OffscreenCanvas(1, 1) : document.createElement('canvas');
  const probeGL = probe.getContext('webgl2');
  const fits = probeGL && gridFitsTexture(probeGL.getParameter(probeGL.MAX_TEXTURE_SIZE), data.rows.length, data.runs.length);
  if (probeGL) probeGL.getExtension('WEBGL_lose_context')?.loseContext();
  if (!fits) return canvasRenderer(canvas, meta, data);
  let gl = canvas.getContext('webgl2', { alpha: false, antialias: false, depth: false, stencil: false });
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
  uniform uint uActiveMask;
  uniform uint uOutlineMask;
  uniform vec3 uPalette[32];
  out vec4 color;
  uint rowWord(int i) { return texelFetch(uRows, ivec2(i % uTextureWidth, i / uTextureWidth), 0).r; }
  uint runWord(int i) { return texelFetch(uRuns, ivec2(i % uTextureWidth, i / uTextureWidth), 0).r; }
  uint codeAt(vec2 screen) {
    ivec2 cell = ivec2(floor((screen - uOffset) / uScale));
    cell.x=((cell.x % uWorld.x)+uWorld.x)%uWorld.x;
    if (cell.y < 0 || cell.y >= uWorld.y) return 0u;
    int lo = int(rowWord(cell.y)), hi = int(rowWord(cell.y + 1));
    for (int i=0; i<24; i++) {
      if (lo >= hi) break;
      int mid = (lo + hi) / 2;
      if (int(runWord(mid * 2)) <= cell.x) lo=mid+1; else hi=mid;
    }
    return runWord(lo * 2 + 1);
  }
  bool outsideSelection(vec2 screen) {
    return all(greaterThanEqual(screen, vec2(0.0))) && all(lessThan(screen, uViewport))
      && (uOutlineMask & (1u << codeAt(screen))) == 0u;
  }
  void main() {
    vec2 screen = vec2(gl_FragCoord.x, uViewport.y - gl_FragCoord.y);
    vec2 position = (screen - uOffset) / uScale;
    uint value = codeAt(screen);
    if (value == 0u) { color=vec4(0.91,0.94,0.95,1.0); return; }
    vec3 rgb = uPalette[int(value)];
    if (uActiveMask != 0u && (uActiveMask & (1u << value)) == 0u) rgb *= ${dimBrightness};
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
    if ((uOutlineMask & (1u << value)) != 0u) {
      float width = round(uScale / uCssScale);
      vec2 dx = vec2(width, 0.0), dy = vec2(0.0, width);
      if (outsideSelection(screen + dx) || outsideSelection(screen - dx)
          || outsideSelection(screen + dy) || outsideSelection(screen - dy)) rgb = vec3(1.0);
    }
    color=vec4(rgb,1.0);
  }`;
  function shader(type, text) {
    const s=gl.createShader(type); gl.shaderSource(s,text); gl.compileShader(s);
    if(!gl.getShaderParameter(s,gl.COMPILE_STATUS)) throw Error(gl.getShaderInfoLog(s));
    return s;
  }
  let program=gl.createProgram();
  const vs=shader(gl.VERTEX_SHADER,vertex), fs=shader(gl.FRAGMENT_SHADER,fragment);
  gl.attachShader(program,vs);gl.attachShader(program,fs);gl.linkProgram(program);
  if(!gl.getProgramParameter(program,gl.LINK_STATUS)) throw Error(gl.getProgramInfoLog(program));
  gl.deleteShader(vs);gl.deleteShader(fs);gl.useProgram(program);
  const width=Math.min(4096,gl.getParameter(gl.MAX_TEXTURE_SIZE)), textures=[];
  function texture(values, unit, name) {
    const height=Math.ceil(values.length/width);
    if(height>gl.getParameter(gl.MAX_TEXTURE_SIZE)) throw Error('Native grid exceeds this GPU texture capacity');
    const padded=new Uint32Array(width*height);padded.set(values);
    const t=gl.createTexture();textures.push(t);gl.activeTexture(gl.TEXTURE0+unit);gl.bindTexture(gl.TEXTURE_2D,t);
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.NEAREST);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.NEAREST);
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);
    gl.texImage2D(gl.TEXTURE_2D,0,gl.R32UI,width,height,0,gl.RED_INTEGER,gl.UNSIGNED_INT,padded);
    gl.uniform1i(gl.getUniformLocation(program,name),unit);
  }
  texture(data.rows,0,'uRows');texture(data.runs,1,'uRuns');
  gl.uniform1i(gl.getUniformLocation(program,'uTextureWidth'),width);
  gl.uniform2i(gl.getUniformLocation(program,'uWorld'),meta.width,meta.height);
  gl.uniform3fv(gl.getUniformLocation(program,'uPalette[0]'),new Float32Array(meta.palette.slice(0,32).flat().map(v=>v/255)));
  let uniforms=Object.fromEntries(['uViewport','uOffset','uScale','uCssScale','uSelected','uActiveMask','uOutlineMask'].map(n=>[n,gl.getUniformLocation(program,n)]));
  if(gl.getError()!==gl.NO_ERROR) throw Error('GPU native map upload failed');
  // Texture upload is complete. Do not retain the large typed RLE streams in
  // the renderer closure; the WebGL textures are the renderer's owned copy.
  data=null;meta=null;
  let disposed=false;
  return {
    draw({scale,ox,oy,dpr,selected,activeMask=0,outlineMask=0}) {
      if(disposed)return;
      gl.viewport(0,0,canvas.width,canvas.height);gl.useProgram(program);
      gl.uniform2f(uniforms.uViewport,canvas.width,canvas.height);
      gl.uniform2f(uniforms.uOffset,ox*dpr,oy*dpr);
      gl.uniform1f(uniforms.uScale,scale*dpr);gl.uniform1f(uniforms.uCssScale,scale);
      gl.uniform2i(uniforms.uSelected,selected?.x??-1,selected?.y??-1);
      gl.uniform1ui(uniforms.uActiveMask,activeMask>>>0);
      gl.uniform1ui(uniforms.uOutlineMask,outlineMask>>>0);
      gl.drawArrays(gl.TRIANGLES,0,3);
    },
    destroy(){
      if(disposed)return;disposed=true;
      if(gl){gl.useProgram(null);for(let i=0;i<textures.length;i++){gl.activeTexture(gl.TEXTURE0+i);gl.bindTexture(gl.TEXTURE_2D,null);gl.deleteTexture(textures[i]);}}
      textures.length=0;
      if(program)gl?.deleteProgram(program);
      program=null;uniforms=null;gl=null;
    }
  };
}
