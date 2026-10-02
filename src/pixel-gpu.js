import {GRID_WIDTH} from './pixel-grid.js';
const vertex=`#version 300 es
void main(){vec2 p=vec2((gl_VertexID<<1)&2,gl_VertexID&2);gl_Position=vec4(p*2.-1.,0.,1.);}`;
const fragment=`#version 300 es
precision highp float;
precision highp int;
precision highp usampler2D;
uniform usampler2D locationRows,locationRuns,politicalRows,politicalRuns,metadata;
uniform sampler2D colors,politicalColors;
uniform vec2 origin,viewport;
uniform float scale,dpr,zoom;
uniform bool hasPolitical,localBorders;
uniform uint selected;
uniform uint locationWorldSize,politicalWorldSize,locationCoordinateBits,politicalCoordinateBits;
uniform bool locationCompact,politicalCompact;
out vec4 outColor;
ivec2 texel(uint i,usampler2D data){uint width=uint(textureSize(data,0).x);return ivec2(int(i%width),int(i/width));}
ivec2 texel(uint i,sampler2D data){uint width=uint(textureSize(data,0).x);return ivec2(int(i%width),int(i/width));}
uvec3 unpackRun(usampler2D runs,uint i,bool compact,uint bits){
  if(!compact)return texelFetch(runs,texel(i,runs),0).xyz;
  uvec4 pair=texelFetch(runs,texel(i/2u,runs),0);
  uvec2 words=(i&1u)==0u?pair.xy:pair.zw;
  uint mask=(1u<<bits)-1u;
  return uvec3(words.x&mask,(words.y&mask)+1u,(words.x>>bits)|((words.y>>bits)<<(32u-bits)));
}
uint lookup(usampler2D rows,usampler2D runs,vec2 p,bool compact,uint bits,uint worldSize){
  ivec2 cell=ivec2(floor(p));
  if(cell.x<0||cell.y<0||uint(cell.x)>=worldSize||uint(cell.y)>=worldSize)return 0u;
  uvec2 row=texelFetch(rows,texel(uint(cell.y),rows),0).rg;
  uint lo=row.x,hi=lo+row.y,end=hi;
  for(int i=0;i<32&&lo<hi;i++){uint mid=lo+(hi-lo)/2u;uvec3 run=unpackRun(runs,mid,compact,bits);if(run.y<=uint(cell.x))lo=mid+1u;else hi=mid;}
  if(lo==end)return 0u;
  uvec3 run=unpackRun(runs,lo,compact,bits);
  return run.x<=uint(cell.x)?run.z:0u;
}
// Style boundaries in screen pixels, independently of geographic cell size.
vec2 boundary(uint a,uint b,uint pa,uint pb){
  if(a==b&&(!hasPolitical||pa==pb))return vec2(0.);
  if(a==selected||b==selected){if(selected!=0u&&a!=b)return vec2(2.5,1.);}
  if(a==0u||b==0u)return a==b?vec2(0.):vec2(1.,.65);
  uvec2 ma=texelFetch(metadata,texel(a,metadata),0).rg,mb=texelFetch(metadata,texel(b,metadata),0).rg;
  if((hasPolitical&&pa!=pb)||(!hasPolitical&&ma.y!=mb.y))return vec2(2.,.95);
  if(a==b)return vec2(0.);
  if(ma.x!=mb.x)return vec2(zoom<7.?.8:1.5,.8);
  return localBorders&&zoom>=7.?vec2(.5,min(.6,(zoom-6.)*.12)):vec2(0.);
}
void main(){
  vec2 screen=vec2(gl_FragCoord.x,viewport.y-gl_FragCoord.y)/dpr;
  vec2 p=origin+screen/scale;
  uint id=lookup(locationRows,locationRuns,p,locationCompact,locationCoordinateBits,locationWorldSize);
  // Distant water needs no outside half-stroke or further ownership lookups.
  if(id==0u&&scale<1.){outColor=vec4(0.);return;}
  uint pid=hasPolitical?lookup(politicalRows,politicalRuns,p,politicalCompact,politicalCoordinateBits,politicalWorldSize):0u;
  vec4 color=id==0u?vec4(0.):texelFetch(colors,texel(id,colors),0);
  if(id!=0u&&pid!=0u)color=texelFetch(politicalColors,texel(pid,politicalColors),0);
  float alpha=0.;bool highlight=false;
  for(int axis=0;axis<4;axis++){
    vec2 dir=axis==0?vec2(-1.,0.):axis==1?vec2(1.,0.):axis==2?vec2(0.,-1.):vec2(0.,1.);
    // At close zoom, use exact cell-edge distances. Below one screen pixel
    // per cell, neighboring display pixels resolve visible boundaries.
    vec2 f=fract(p);float distance=axis==0?f.x:axis==1?1.-f.x:axis==2?f.y:1.-f.y;
    distance*=scale;
    if(scale>=1.&&distance>1.75)continue;
    vec2 q=p+dir*max(1.,1./scale);
    uint other=lookup(locationRows,locationRuns,q,locationCompact,locationCoordinateBits,locationWorldSize),op=hasPolitical?lookup(politicalRows,politicalRuns,q,politicalCompact,politicalCoordinateBits,politicalWorldSize):0u;
    vec2 style=boundary(id,other,pid,op);
    float coverage=scale>=1.?clamp(style.x*.5-distance+.5/dpr,0.,1.):style.x*.5;
    if(style.y*coverage>alpha){alpha=style.y*coverage;highlight=selected!=0u&&id!=other&&(id==selected||other==selected);}
  }
  vec3 ink=highlight?vec3(1.,.965,.843):vec3(.137,.169,.145);
  outColor=vec4(mix(color.rgb,ink,alpha),max(color.a,alpha));
}`;

export class PixelGPU{
  constructor(canvas){
    const gl=this.gl=canvas.getContext('webgl2',{alpha:true,antialias:false,premultipliedAlpha:false});
    if(!gl)throw new Error('WebGL2 unavailable');
    const shader=(kind,source)=>{const s=gl.createShader(kind);gl.shaderSource(s,source);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw new Error(gl.getShaderInfoLog(s));return s;};
    const program=this.program=gl.createProgram();const shaders=[shader(gl.VERTEX_SHADER,vertex),shader(gl.FRAGMENT_SHADER,fragment)];
    shaders.forEach(s=>gl.attachShader(program,s));gl.linkProgram(program);shaders.forEach(s=>gl.deleteShader(s));
    if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw new Error(gl.getProgramInfoLog(program));
    gl.useProgram(program);this.textures=new Map();this.uploads=0;this.ownershipUploads=0;this.ownershipLayouts={};
    ['locationRows','locationRuns','politicalRows','politicalRuns','metadata','colors','politicalColors'].forEach((name,i)=>{
      this.textures.set(name,{unit:i,texture:gl.createTexture()});gl.uniform1i(gl.getUniformLocation(program,name),i);
      this.upload(name,name.includes('Colors')||name==='colors'?new Uint8Array(4):new Uint32Array(4),4);
    });
    for(const name of ['location','political'])this.layout(name,{version:1,size:GRID_WIDTH,coordinateBits:Math.ceil(Math.log2(GRID_WIDTH))});
  }
  upload(name,data,channels=4){
    const gl=this.gl,{unit,texture}=this.textures.get(name),bytes=data instanceof Uint8Array;
    const limit=gl.getParameter(gl.MAX_TEXTURE_SIZE),texels=Math.ceil(data.length/channels);
    // Keep one ownership asset on every device. Wider textures accommodate the
    // same fixed grid on devices whose texture height is limited to 4096.
    let width=Math.min(2048,limit);while(Math.ceil(texels/width)>limit&&width<limit)width=Math.min(width*2,limit);
    const height=Math.max(1,Math.ceil(texels/width));
    if(height>limit)throw new Error('Ownership texture exceeds device limit');
    const padded=new data.constructor(width*height*channels);padded.set(data);
    gl.activeTexture(gl.TEXTURE0+unit);gl.bindTexture(gl.TEXTURE_2D,texture);
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.NEAREST);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.NEAREST);
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);
    gl.texImage2D(gl.TEXTURE_2D,0,bytes?gl.RGBA8:channels===2?gl.RG32UI:gl.RGBA32UI,width,height,0,bytes?gl.RGBA:channels===2?gl.RG_INTEGER:gl.RGBA_INTEGER,bytes?gl.UNSIGNED_BYTE:gl.UNSIGNED_INT,padded);
    this.uploads++;
  }
  layout(name,grid){
    const gl=this.gl;this.ownershipLayouts[name]={version:grid.version??1,size:grid.size,coordinateBits:grid.coordinateBits??Math.ceil(Math.log2(grid.size))};
    gl.uniform1ui(gl.getUniformLocation(this.program,name+'WorldSize'),grid.size);
    gl.uniform1ui(gl.getUniformLocation(this.program,name+'CoordinateBits'),this.ownershipLayouts[name].coordinateBits);
    gl.uniform1i(gl.getUniformLocation(this.program,name+'Compact'),grid.version===2);
  }
  ownership(name,grid){this.upload(name+'Rows',grid.rows,2);this.upload(name+'Runs',grid.runs);this.ownershipUploads+=2;this.layout(name,grid);}
  draw({origin,scale,zoom,localBorders,selected,hasPolitical,dpr}){
    const gl=this.gl,u=name=>gl.getUniformLocation(this.program,name);gl.viewport(0,0,gl.canvas.width,gl.canvas.height);
    gl.uniform2f(u('origin'),origin.x,origin.y);gl.uniform2f(u('viewport'),gl.canvas.width,gl.canvas.height);
    gl.uniform1f(u('scale'),scale);gl.uniform1f(u('zoom'),zoom);gl.uniform1f(u('dpr'),dpr);
    gl.uniform1i(u('localBorders'),localBorders);gl.uniform1i(u('hasPolitical'),hasPolitical);gl.uniform1ui(u('selected'),selected);
    gl.drawArrays(gl.TRIANGLES,0,3);
  }
  destroy(){const gl=this.gl;for(const {texture} of this.textures.values())gl.deleteTexture(texture);gl.deleteProgram(this.program);}
}
