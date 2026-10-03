import {DatabaseSync} from 'node:sqlite';
import {createGridIndex} from '../src/pixel-grid.js';
import {compileOwnership,packOwnership,pickOwnership,ownershipRun} from '../src/pixel-ownership.js';
import {categoryColor,formatYear} from '../src/model.js';
import {categoryPresentationKey} from '../src/category-presentation.js';

// Select a real, partially covered territory rather than a mocked owner value.
export async function findHistoricalMapCase(getSnapshot){
 const db=new DatabaseSync('data/atlas.sqlite',{readOnly:true});
 try{
  const location=db.prepare('SELECT id,name,geometry FROM locations WHERE active=1 AND id=?');
  for(const year of [1444,1000]){
   const result=await getSnapshot(year);
   if(result.polities.length)throw Error('Normal snapshots must not expose independent political fills');
   const direct=new Set([...result.states,...result.attributes.filter(r=>r.attribute==='owner'&&r.method==='direct')].map(r=>r.location_id));
   for(const row of db.prepare("SELECT entity_id FROM entity_history WHERE field='attributes' AND is_example=0 AND valid_from<=? AND valid_to>?").all(year,year))direct.add(row.entity_id);
   const legendNames=new Set([...new Set(result.attributes.filter(r=>r.attribute==='owner'&&r.value).map(r=>r.value))].sort((a,b)=>a.localeCompare(b)).slice(0,80));
   for(const record of result.attributes){
    if(record.attribute!=='owner'||record.method!=='majority-area'||!record.value||record.metadata.share<=.5||record.metadata.share>=.99||direct.has(record.location_id)||!legendNames.has(record.value))continue;
    const row=location.get(record.location_id);if(!row)continue;
    const boundary=result.boundaries.find(b=>b.location_id===row.id);
    const index=createGridIndex([{id:row.id,geometry:boundary?.geometry||JSON.parse(row.geometry)}]),bounds=index[0].bounds;
    if(bounds[2]-bounds[0]>90||bounds[3]-bounds[1]>90)continue;
    const grid=packOwnership(compileOwnership(index)),cells=[];
    for(let y=Math.max(0,Math.floor(bounds[1]));y<Math.min(grid.size,Math.ceil(bounds[3]));y++){
     const offset=grid.rows[y*2],end=offset+grid.rows[y*2+1];
     for(let k=offset;k<end;k++){
      const run=ownershipRun(grid,k);
      for(let x=run.start+1;x<run.end-1;x++)if(pickOwnership(grid,x,y-1)===1&&pickOwnership(grid,x,y+1)===1)cells.push([x+.5,y+.5]);
     }
    }
    if(cells.length<24)continue;
    return {year,record,name:row.name,id:row.id,cells,center:[(bounds[0]+bounds[2])/2,(bounds[1]+bounds[3])/2]};
   }
  }
  throw Error('No real 50–99% majority territory with visible interior cells found in 1444 or 1000');
 }finally{db.close();}
}

export async function checkHistoricalMapCase(page,example){
 await page.locator('#year-input').fill(String(example.year));await page.locator('#year-form button').click();
 await page.waitForFunction(year=>document.querySelector('#map-year').textContent===year,formatYear(example.year),{timeout:60000});
 await page.locator('#loading').waitFor({state:'hidden'});
 await page.locator('[data-mode="owner"]').click();
 await page.locator('#search').fill(example.name);await page.locator(`[data-result="${example.id}"]`).click();
 const displayedOwner=await page.locator('#details dl > div').filter({has:page.locator('dt',{hasText:/^Owner$/})}).locator('dd').textContent();
 if(displayedOwner!==example.record.value)throw Error(`Inspector owner ${displayedOwner} differs from prepared ${example.record.value}`);
 await page.waitForFunction(center=>{
  const gl=document.querySelector('.atlas-pixel-canvas')?.getContext('webgl2');if(!gl)return false;
  const program=gl.getParameter(gl.CURRENT_PROGRAM),u=name=>gl.getUniform(program,gl.getUniformLocation(program,name));
  const origin=u('origin'),viewport=u('viewport'),scale=u('scale'),dpr=u('dpr');
  return scale>=4&&center[0]>=origin[0]&&center[0]<origin[0]+viewport[0]/scale/dpr&&center[1]>=origin[1]&&center[1]<origin[1]+viewport[1]/scale/dpr;
 },example.center);
 return page.evaluate(async({cells,owner,css})=>{
  await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));
  const canvas=document.querySelector('.atlas-pixel-canvas'),gl=canvas.getContext('webgl2'),program=gl.getParameter(gl.CURRENT_PROGRAM),u=name=>gl.getUniform(program,gl.getUniformLocation(program,name));
  const selected=u('selected'),origin=u('origin'),scale=u('scale'),dpr=u('dpr');
  const originalFramebuffer=gl.getParameter(gl.FRAMEBUFFER_BINDING),originalActive=gl.getParameter(gl.ACTIVE_TEXTURE),framebuffer=gl.createFramebuffer();
  const attach=name=>{gl.activeTexture(gl.TEXTURE0+u(name));const texture=gl.getParameter(gl.TEXTURE_BINDING_2D);gl.bindFramebuffer(gl.FRAMEBUFFER,framebuffer);gl.framebufferTexture2D(gl.FRAMEBUFFER,gl.COLOR_ATTACHMENT0,gl.TEXTURE_2D,texture,0);};
  const integer=(name,index)=>{attach(name);const out=new Uint32Array(4);gl.readPixels(index%2048,Math.floor(index/2048),1,1,gl.RGBA_INTEGER,gl.UNSIGNED_INT,out);return out;};
  const rows=new Map(),runs=new Map();
  const lookup=(x,y)=>{
   if(!rows.has(y))rows.set(y,integer('locationRows',y));
   const row=rows.get(y);let lo=row[0],hi=lo+row[1],end=hi;
   const run=i=>{
    if(!runs.has(i)){
     const compact=u('locationCompact'),bits=u('locationCoordinateBits'),raw=integer('locationRuns',compact?Math.floor(i/2):i);
     if(compact){const offset=(i%2)*2,a=raw[offset],b=raw[offset+1],mask=2**bits-1;runs.set(i,[a&mask,(b&mask)+1,(a>>>bits)+(b>>>bits)*2**(32-bits)]);}else runs.set(i,raw);
    }
    return runs.get(i);
   };
   while(lo<hi){const mid=(lo+hi)>>>1;if(run(mid)[1]<=x)lo=mid+1;else hi=mid;}
   return lo<end&&run(lo)[0]<=x?run(lo)[2]:0;
  };
  const eligible=cells.filter(([x,y])=>lookup(Math.floor(x),Math.floor(y))===selected);
  attach('colors');const palette=new Uint8Array(4);gl.readPixels(selected%2048,Math.floor(selected/2048),1,1,gl.RGBA,gl.UNSIGNED_BYTE,palette);
  gl.bindFramebuffer(gl.FRAMEBUFFER,originalFramebuffer);gl.activeTexture(originalActive);gl.deleteFramebuffer(framebuffer);
  gl.drawArrays(gl.TRIANGLES,0,3);
  const pixels=new Uint8Array(canvas.width*canvas.height*4);gl.readPixels(0,0,canvas.width,canvas.height,gl.RGBA,gl.UNSIGNED_BYTE,pixels);
  let tested=0,mismatches=0;
  for(const [x,y] of eligible){
   const px=Math.floor((x-origin[0])*scale*dpr),py=canvas.height-1-Math.floor((y-origin[1])*scale*dpr);
   if(px<0||py<0||px>=canvas.width||py>=canvas.height)continue;
   tested++;const offset=(py*canvas.width+px)*4;
   if([...palette].some((value,k)=>Math.abs(value-pixels[offset+k])>1))mismatches++;
  }
  const probe=document.createElement('i');probe.style.backgroundColor=css;document.body.append(probe);
  const expected=getComputedStyle(probe).backgroundColor;probe.remove();
  const legend=[...document.querySelectorAll('#legend-items .legend-item')].find(line=>line.querySelector('span')?.textContent===owner);
  return {selected,tested,eligible:eligible.length,totalCells:cells.length,mismatches,palette:[...palette],expected,legend:legend?getComputedStyle(legend.querySelector('i')).backgroundColor:null,hasPolitical:u('hasPolitical'),error:gl.getError()};
 },{cells:example.cells,owner:example.record.value,css:categoryColor(categoryPresentationKey('owner',{value:example.record.value,category_id:example.record.category_id}))});
}
