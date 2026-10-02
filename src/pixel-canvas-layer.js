import L from 'leaflet';
import {GRID_ZOOM,createGridIndex,borderKind,borderStyle,viewStride} from './pixel-grid.js';
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
  constructor(features,options){super();this.index=createGridIndex(features);this.options=options;this.frame=null;this.sequence=0;this.jobs=new Map();this.worker=new Worker(new URL('./pixel-worker.js',import.meta.url),{type:'module'});this.worker.onmessage=({data})=>{this.jobs.get(data.request)?.(data);this.jobs.delete(data.request);};if(options.ownership){this.worker.postMessage({type:'precompiled',grid:options.ownership});}else this.sendIndex('locations',this.index);this.provinceIds=[null,...this.index.map(x=>x.feature.properties.parent_id)];}
  sendIndex(type,index){const slim=index.map(({index,polygons,bounds})=>({index,polygons,bounds}));this.worker.postMessage({type,index:slim},slim.flatMap(i=>i.polygons.flatMap(p=>p.map(r=>r.buffer))));}
  onAdd(map){
    this.map=map;this.canvas=L.DomUtil.create('canvas','atlas-pixel-canvas leaflet-layer leaflet-zoom-animated');this.canvas.setAttribute('aria-label','Pixel world map');
    this.canvas.dataset.gridZoom=String(GRID_ZOOM);map.getPane('overlayPane').append(this.canvas);
    this.canvas.style.pointerEvents='none';map.on('moveend resize',this.redraw,this);map.on('zoomanim',this.animateZoom,this);map.on('mousemove',this.hover,this);map.on('click',this.click,this);
    this.tooltip=L.tooltip({sticky:true});this.redraw();
  }
  onRemove(map){cancelAnimationFrame(this.pending);map.off('moveend resize',this.redraw,this);map.off('zoomanim',this.animateZoom,this);map.off('mousemove',this.hover,this);map.off('click',this.click,this);this.tooltip.remove();this.canvas.remove();this.worker.terminate();this.map=null;this.jobs.clear();}
  animateZoom(event){
    if(!this.origin)return;
    const scale=this.map.getZoomScale(event.zoom,this.drawZoom);
    const position=this.map._latLngToNewLayerPoint(this.origin,event.zoom,event.center);
    L.DomUtil.setTransform(this.canvas,position,scale);
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
    const frame=this.frame,{ids,political}=frame;
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
    const col=Math.floor((p.x-f.x)/f.stride),row=Math.floor((p.y-f.y)/f.stride);
    if(col<0 || row<0 || col>=f.width || row>=f.height)return null;
    return this.index[f.ids[row*f.width+col]-1]?.feature || null;
  }
  hover(event){const f=this.pick(event.latlng);if(!f){this.tooltip.remove();return;}const text=document.createElement('span');text.textContent=this.options.label?.(f)||f.properties.name;this.tooltip.setContent(text).setLatLng(event.latlng).addTo(this.map);}
  click(event){const f=this.pick(event.latlng);if(f)this.options.select(f.id);}
}
