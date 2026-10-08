import {effectiveFootprintBounds} from './effective-footprint.js';
import {NATIVE_GRID_METHOD} from './native-grid.js';
import L from 'leaflet';
import {GRID_ZOOM,projectCell,createGridIndex,borderKind,borderStyle,viewStride} from './pixel-grid.js';
import {pickOwnership} from './pixel-ownership.js';
import {coverageExplanation,coverageText,coverageContent} from './coverage-classification.js';
import {updateLocationMetadata} from './pixel-metadata.js';
const colorCache=new Map();
function rgb(css){
  if(colorCache.has(css))return colorCache.get(css);
  let out;
  if(css.startsWith('#'))out=[1,3,5].map(i=>parseInt(css.slice(i,i+2),16));
  else {
    const [h,s,l]=css.match(/[\d.]+/g).map(Number);const sat=s/100,light=l/100;
    const a=sat*Math.min(light,1-light);
    out=[0,8,4].map(n=>{const k=(n+h/30)%12;return Math.round(255*(light-a*Math.max(-1,Math.min(k-3,9-k,1))));});
  }
  colorCache.set(css,out);return out;
}

export class PixelCanvasLayer extends L.Layer {
  constructor(features,options){super();
    const composite=features.some(feature=>Object.hasOwn(feature,'additiveFootprint'));
    if(composite && (options.ownership?.method!==NATIVE_GRID_METHOD || !/^[a-f0-9]{64}$/.test(options.ownership.effective_footprint_sha256??'')))
      throw Error('Additive footprints require the authenticated native grid; projected fallback is unsupported');
    this.index=createGridIndex(features,{ordered:options.orderedOwners===true});
    if(composite)for(const item of this.index){
      if(Object.hasOwn(item.feature,'additiveFootprint')){
        const [west,south,east,north]=effectiveFootprintBounds(item.feature);
        const [left,bottom]=projectCell(west,south),[right,top]=projectCell(east,north);
        item.bounds=[left,top,right,bottom];
      }
      // Only metadata/bounds are needed: both drawing and picking use the same
      // supplied native grid. No projected composite is sent to the worker.
      item.polygons=[];
    }
    this.options=options;this.frame=null;this.sequence=0;this.jobs=new Map();this.worker=new Worker(new URL('./pixel-worker.js',import.meta.url),{type:'module'});this.worker.onmessage=({data})=>{this.jobs.get(data.request)?.(data);this.jobs.delete(data.request);};if(options.ownership){this.worker.postMessage({type:'precompiled',grid:options.ownership});}else this.sendIndex('locations',this.index);if(options.coverage)this.worker.postMessage({type:'coverage',grid:options.coverage.grid});this.provinceIds=[null,...this.index.map(x=>x.feature.properties.parent_id)];}
  sendIndex(type,index){const slim=index.map(({index,polygons,bounds})=>({index,polygons,bounds}));this.worker.postMessage({type,index:slim},slim.flatMap(i=>i.polygons.flatMap(p=>p.map(r=>r.buffer))));}
  onAdd(map){
    this.map=map;this.canvas=L.DomUtil.create('canvas','atlas-pixel-canvas leaflet-layer leaflet-zoom-animated');this.canvas.setAttribute('aria-label','Pixel world map');
    this.canvas.dataset.gridZoom=String(GRID_ZOOM);map.getPane('overlayPane').append(this.canvas);
    this.canvas.style.pointerEvents='none';map.on('move',this.moveCamera,this);map.on('moveend resize',this.redraw,this);map.on('zoomanim',this.animateZoom,this);map.on('mousemove',this.hover,this);map.on('click',this.click,this);
    this.tooltip=L.tooltip({sticky:true});this.redraw();
  }
  onRemove(map){cancelAnimationFrame(this.pending);map.off('move',this.moveCamera,this);map.off('moveend resize',this.redraw,this);map.off('zoomanim',this.animateZoom,this);map.off('mousemove',this.hover,this);map.off('click',this.click,this);this.tooltip.remove();this.canvas.remove();this.worker.terminate();this.map=null;this.jobs.clear();}
  animateZoom(event){
    if(!this.origin)return;
    const scale=this.map.getZoomScale(event.zoom,this.drawZoom);
    const position=this.map._latLngToNewLayerPoint(this.origin,event.zoom,event.center);
    L.DomUtil.setTransform(this.canvas,position,scale);
  }
  moveCamera(){
    // Move the cached image during the gesture; do CPU sampling once it settles.
    ++this.sequence;
    cancelAnimationFrame(this.pending);
    if(this.origin)L.DomUtil.setTransform(this.canvas,this.map.latLngToLayerPoint(this.origin),this.map.getZoomScale(this.map.getZoom(),this.drawZoom));
    // Zooming out exposes new areas. Sample them occasionally, with one job in
    // flight, instead of either leaving them blank or repainting every frame.
    if(this.origin&&this.map.getZoom()<this.drawZoom&&!this.cameraDraw&&performance.now()-(this.lastCameraDraw||0)>150){
      this.lastCameraDraw=performance.now();
      this.cameraDraw=this.draw().finally(()=>{this.cameraDraw=null;});
    }
  }
  setStyle(){this.redraw();}
  updateMetadata(features){this.provinceIds=updateLocationMetadata(this.index,features);}
  bringToFront(){}
  setPolitical(features){if(this.politicalFeatures!==features){this.politicalFeatures=features;this.political=features.length?createGridIndex(features):null;this.sendIndex('political',this.political || []);this.frame=null;}this.redraw();}
  redraw(){cancelAnimationFrame(this.pending);this.pending=requestAnimationFrame(()=>this.draw());}
  async draw(){
    if(!this.map)return;
    const zoom=this.map.getZoom(),scale=2**(zoom-GRID_ZOOM),stride=viewStride(zoom);
    const top=this.map.project(this.map.getBounds().getNorthWest(),GRID_ZOOM),size=this.map.getSize();
    const x=Math.floor(top.x/stride)*stride,y=Math.floor(top.y/stride)*stride;
    const width=Math.ceil(size.x/(scale*stride))+2,height=Math.ceil(size.y/(scale*stride))+2;
    const key=[x,y,width,height,stride].join('/');
    const request=++this.sequence,started=performance.now();
    if(this.frame?.key!==key){
      const result=await new Promise(resolve=>{this.jobs.set(request,resolve);this.worker.postMessage({type:'frame',request,frame:{key,x,y,width,height,stride}});});
      if(!this.map || request!==this.sequence)return;
      this.frame={key,x,y,width,height,stride,...result};
    }
    const frame=this.frame,{ids,political,physical}=frame;
    const low=document.createElement('canvas');low.width=width;low.height=height;const ctx=low.getContext('2d'),pixels=ctx.createImageData(width,height);
    const locationColors=[],politicalColors=[],groups=[];
    for(let i=0;i<ids.length;i++){
      const id=ids[i];if(!id)continue;
      if(!locationColors[id]){const f=this.index[id-1].feature;locationColors[id]=rgb(this.options.color(f));groups[id]=this.options.borderKey?.(f);}
      const pid=political?.[i];if(pid&&!politicalColors[pid])politicalColors[pid]=rgb(this.options.politicalColor(this.political[pid-1].feature));
      const c=pid?politicalColors[pid]:locationColors[id],offset=i*4;
      pixels.data[offset]=c[0];pixels.data[offset+1]=c[1];pixels.data[offset+2]=c[2];pixels.data[offset+3]=255;
    }
    ctx.putImageData(pixels,0,0);
    const pixelSize=scale*stride,dpr=window.devicePixelRatio||1;
    const screenW=width*pixelSize,screenH=height*pixelSize;
    this.canvas.width=Math.ceil(screenW*dpr);this.canvas.height=Math.ceil(screenH*dpr);this.canvas.style.width=`${screenW}px`;this.canvas.style.height=`${screenH}px`;
    this.origin=this.map.unproject(L.point(x,y),GRID_ZOOM);this.drawZoom=zoom;
    const point=this.map.latLngToLayerPoint(this.origin);L.DomUtil.setTransform(this.canvas,point,1);
    const out=this.canvas.getContext('2d');out.scale(dpr,dpr);out.imageSmoothingEnabled=false;out.drawImage(low,0,0,screenW,screenH);
    if(physical){
      const mask=document.createElement('canvas');mask.width=width;mask.height=height;
      const maskContext=mask.getContext('2d'),maskPixels=maskContext.createImageData(width,height);let gaps=0;
      for(let i=0;i<ids.length;i++)if(!ids[i]&&physical[i]===1){maskPixels.data[i*4+3]=255;gaps++;}
      if(gaps){
        maskContext.putImageData(maskPixels,0,0);
        const overlay=document.createElement('canvas');overlay.width=this.canvas.width;overlay.height=this.canvas.height;
        const overlayContext=overlay.getContext('2d');overlayContext.scale(dpr,dpr);overlayContext.imageSmoothingEnabled=false;
        overlayContext.drawImage(mask,0,0,screenW,screenH);overlayContext.globalCompositeOperation='source-in';
        const tile=document.createElement('canvas');tile.width=8;tile.height=8;
        const tileContext=tile.getContext('2d'),tilePixels=tileContext.createImageData(8,8);
        for(let y=0;y<8;y++)for(let x=0;x<8;x++)tilePixels.data.set((x+y)%8<2?[170,79,36,255]:[247,223,179,255],(y*8+x)*4);
        tileContext.putImageData(tilePixels,0,0);overlayContext.fillStyle=overlayContext.createPattern(tile,'repeat');overlayContext.fillRect(0,0,screenW,screenH);
        out.drawImage(overlay,0,0,screenW,screenH);
      }
    }
    const paths={location:new Path2D(),province:new Path2D(),coast:new Path2D(),group:new Path2D(),selected:new Path2D()};
    const selected=this.options.selected();
    const edge=(a,b,x1,y1,x2,y2,pa,pb)=>{
      let kind=borderKind(a,b,this.provinceIds);
      if(a && b && ((political && pa!==pb) || (!political && groups[a]!==groups[b])))kind='group';
      if(!kind)return;
      const highlight=(a && this.index[a-1].feature.id===selected)||(b && this.index[b-1].feature.id===selected);
      const path=highlight?paths.selected:paths[kind];path.moveTo(x1*pixelSize,y1*pixelSize);path.lineTo(x2*pixelSize,y2*pixelSize);
    };
    for(let row=0;row<height;row++)for(let col=0;col<width;col++){
      const i=row*width+col;if(col+1<width)edge(ids[i],ids[i+1],col+1,row,col+1,row+1,political?.[i],political?.[i+1]);
      if(row+1<height)edge(ids[i],ids[i+width],col,row+1,col+1,row+1,political?.[i],political?.[i+width]);
    }
    out.lineJoin='miter';
    for(const kind of ['location','province','coast']){
      const style=borderStyle(kind,zoom);if(!style || (kind==='location' && !this.options.locationBorders()))continue;
      out.strokeStyle=`rgba(35,43,37,${style.alpha})`;out.lineWidth=style.width;out.stroke(paths[kind]);
    }
    out.strokeStyle='rgba(28,35,29,.95)';out.lineWidth=2;out.stroke(paths.group);
    out.strokeStyle='#fff6d7';out.lineWidth=2.5;out.stroke(paths.selected);
    this.canvas.dataset.rendered='true';this.canvas.dataset.locationBorders=String(zoom>=7 && this.options.locationBorders());
    this.canvas.dataset.provinceBorders='true';this.canvas.dataset.cellCount=String(ids.length);this.canvas.dataset.renderMs=String(Math.round(performance.now()-started));this.canvas.dataset.worker='true';
    this.canvas.dataset.compilations=String(frame.compilations);this.canvas.dataset.compileMs=String(Math.round(frame.compileMs));this.canvas.dataset.frame=key;this.canvas.dataset.ownershipUploads='0';
  }
  pick(latlng){
    if(!this.frame)return null;
    const p=this.map.project(latlng,GRID_ZOOM),f=this.frame;
    if(this.options.ownership)return this.index[pickOwnership(this.options.ownership,p.x,p.y)-1]?.feature||null;
    const col=Math.floor((p.x-f.x)/f.stride),row=Math.floor((p.y-f.y)/f.stride);
    if(col<0 || row<0 || col>=f.width || row>=f.height)return null;
    return this.index[f.ids[row*f.width+col]-1]?.feature || null;
  }
  coverageInfo(latlng){return coverageExplanation(this.options.coverage,this.map.project(latlng,GRID_ZOOM),latlng);}
  hover(event){const f=this.pick(event.latlng);const text=document.createElement('span');text.textContent=f?(this.options.label?.(f)||f.properties.name):coverageText(this.coverageInfo(event.latlng));this.tooltip.setContent(text).setLatLng(event.latlng).addTo(this.map);}
  click(event){const f=this.pick(event.latlng);if(f){this.map.closePopup();this.options.select(f.id);}else L.popup().setLatLng(event.latlng).setContent(coverageContent(this.coverageInfo(event.latlng))).openOn(this.map);}
}
