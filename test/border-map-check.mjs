// Inspect actual uploaded geographic IDs and read the map framebuffer, rather
// than relying on renderer data-* flags. Selection outlines are excluded.
export async function borderSamples(page){
 return page.evaluate(()=>{
  const canvas=document.querySelector('.atlas-pixel-canvas'),gl=canvas.getContext('webgl2'),program=gl.getParameter(gl.CURRENT_PROGRAM),u=name=>gl.getUniform(program,gl.getUniformLocation(program,name));
  const origin=[...u('origin')],scale=u('scale'),dpr=u('dpr'),selected=u('selected');
  const original=gl.getParameter(gl.FRAMEBUFFER_BINDING),active=gl.getParameter(gl.ACTIVE_TEXTURE),fb=gl.createFramebuffer();
  const attach=name=>{gl.activeTexture(gl.TEXTURE0+u(name));const tex=gl.getParameter(gl.TEXTURE_BINDING_2D);gl.bindFramebuffer(gl.FRAMEBUFFER,fb);gl.framebufferTexture2D(gl.FRAMEBUFFER,gl.COLOR_ATTACHMENT0,gl.TEXTURE_2D,tex,0);};
  const size=u('locationWorldSize')??32768,compact=u('locationCompact'),bits=u('locationCoordinateBits'),mask=2**bits-1,rowHeight=Math.ceil(size/2048);
  attach('locationRows');const rows=new Uint32Array(2048*rowHeight*4);gl.readPixels(0,0,2048,rowHeight,gl.RGBA_INTEGER,gl.UNSIGNED_INT,rows);
  let allEnd=0;for(let y=0;y<size;y++)allEnd=Math.max(allEnd,rows[y*4]+rows[y*4+1]);
  const runHeight=Math.ceil(allEnd/(compact?2:1)/2048);
  attach('locationRuns');const runs=new Uint32Array(2048*runHeight*4);gl.readPixels(0,0,2048,runHeight,gl.RGBA_INTEGER,gl.UNSIGNED_INT,runs);
  const run=i=>{const a=runs[i*(compact?2:4)],b=runs[i*(compact?2:4)+1];return compact?[a&mask,(b&mask)+1,(a>>>bits)+(b>>>bits)*2**(32-bits)]:[a,b,runs[i*4+2]];};
  let maxId=0;for(let k=0;k<allEnd;k++)maxId=Math.max(maxId,run(k)[2]);const metadataHeight=Math.ceil((maxId+1)/2048);attach('metadata');const metadata=new Uint32Array(2048*metadataHeight*4);gl.readPixels(0,0,2048,metadataHeight,gl.RGBA_INTEGER,gl.UNSIGNED_INT,metadata);
  const lookup=(x,y)=>{let lo=rows[y*4],hi=lo+rows[y*4+1],end=hi;while(lo<hi){const mid=(lo+hi)>>>1;if(run(mid)[1]<=x)lo=mid+1;else hi=mid;}return lo<end&&run(lo)[0]<=x?run(lo)[2]:0;};
  const found={},maxX=origin[0]+(canvas.width/dpr-330)/scale,maxY=origin[1]+(canvas.height/dpr-120)/scale;
  for(let y=Math.max(2,Math.ceil(origin[1]+50/scale));y<Math.min(size-2,maxY);y++){
   const end=rows[y*4]+rows[y*4+1];
   for(let k=rows[y*4];k+1<end;k++){
    const left=run(k),right=run(k+1),x=left[1],a=left[2],b=right[2];
    if(x!==right[0]||x<origin[0]+30/scale||x>maxX||a===b||a===selected||b===selected||metadata[a*4+1]!==metadata[b*4+1])continue;
    const kind=metadata[a*4]===metadata[b*4]?'location':'province';if(found[kind])continue;
    if([-2,-1,0,1,2].some(d=>lookup(x-1,y+d)!==a||lookup(x,y+d)!==b))continue;
    found[kind]={x,y:y+.5,a,b};
   }
   if(found.location&&found.province)break;
  }
  gl.bindFramebuffer(gl.FRAMEBUFFER,original);gl.activeTexture(active);gl.deleteFramebuffer(fb);gl.drawArrays(gl.TRIANGLES,0,3);
  return {found,origin,scale,dpr,zoom:u('zoom'),error:gl.getError()};
 });
}
export async function readBorderPixels(page,samples,override){
 return page.evaluate(({found,override})=>{
  const canvas=document.querySelector('.atlas-pixel-canvas'),gl=canvas.getContext('webgl2'),program=gl.getParameter(gl.CURRENT_PROGRAM),u=name=>gl.getUniform(program,gl.getUniformLocation(program,name)),origin=u('origin'),scale=u('scale'),dpr=u('dpr');
  const previous=u('localBorders');if(override!==undefined)gl.uniform1i(gl.getUniformLocation(program,'localBorders'),override);gl.drawArrays(gl.TRIANGLES,0,3);const pixels=new Uint8Array(canvas.width*canvas.height*4);gl.readPixels(0,0,canvas.width,canvas.height,gl.RGBA,gl.UNSIGNED_BYTE,pixels);
  const out={};for(const [kind,{x,y}]of Object.entries(found)){const px=Math.floor((x-origin[0])*scale*dpr),py=canvas.height-1-Math.floor((y-origin[1])*scale*dpr);out[kind]=[];for(let offset=-4;offset<=4;offset++)out[kind].push([...pixels.slice((py*canvas.width+px+offset)*4,(py*canvas.width+px+offset)*4+4)]);}
  const result={pixels:out,localBorders:u('localBorders'),error:gl.getError()};gl.uniform1i(gl.getUniformLocation(program,'localBorders'),previous);gl.drawArrays(gl.TRIANGLES,0,3);return result;
 },{...samples,override});
}
