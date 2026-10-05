import L from 'leaflet';
import {GRID_ZOOM,createGridIndex} from './pixel-grid.js';
import {pickOwnership} from './pixel-ownership.js';
import {PixelGPU} from './pixel-gpu.js';
import {PixelCanvasLayer} from './pixel-canvas-layer.js';
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

export class PixelLayer extends L.Layer {
  constructor(features,options){
    super();this.canvas=L.DomUtil.create('canvas','atlas-pixel-canvas leaflet-layer leaflet-zoom-animated');
    try{this.gpu=new PixelGPU(this.canvas);}catch(error){console.warn('Using Canvas map renderer:',error.message);return new PixelCanvasLayer(features,options);}
    this.index=createGridIndex(features);this.ids=new Map(this.index.map(i=>[i.feature.id,i.index]));this.options=options;
    this.revisions={locations:0,political:0};this.grids={};this.styleDirty=true;
    this.worker=new Worker(new URL('./pixel-gpu-worker.js',import.meta.url),{type:'module'});
    this.worker.onmessage=({data})=>{
      if(data.revision!==this.revisions[data.type])return;
      this.grids[data.type]=data.grid;
      if(!this.lost)this.gpu.ownership(data.type==='locations'?'location':'political',data.grid);
      this.canvas.dataset.compilations=String(data.compilations);this.canvas.dataset.compileMs=String(Math.round(data.compileMs));this.redraw();
    };
    if(options.ownership){this.grids.locations=options.ownership;this.gpu.ownership('location',options.ownership);this.canvas.dataset.compilations='0';this.canvas.dataset.compileMs='0';this.canvas.dataset.precompiled='true';}
    else this.sendIndex('locations',this.index);
    this.canvas.addEventListener('webglcontextlost',event=>{event.preventDefault();this.lost=true;});
    this.canvas.addEventListener('webglcontextrestored',()=>{
      this.gpu=new PixelGPU(this.canvas);this.lost=false;
      for(const [type,grid] of Object.entries(this.grids))this.gpu.ownership(type==='locations'?'location':'political',grid);
      this.styleDirty=true;this.redraw();
    });
  }
  sendIndex(type,index){
    const slim=index.map(({index,polygons,bounds})=>({index,polygons,bounds}));
    this.worker.postMessage({type,revision:++this.revisions[type],index:slim},slim.flatMap(i=>i.polygons.flatMap(p=>p.map(r=>r.buffer))));
  }
  onAdd(map){
    this.map=map;this.canvas.setAttribute('aria-label','Pixel world map');this.canvas.style.pointerEvents='none';
    this.canvas.dataset.gridZoom=String(GRID_ZOOM);this.canvas.dataset.renderer='webgl2';
    map.getPane('overlayPane').append(this.canvas);this.tooltip=L.tooltip({sticky:true});
    map.on('move',this.moveCamera,this);map.on('moveend resize',this.redraw,this);map.on('zoomanim',this.animateZoom,this);
    map.on('mousemove',this.hover,this);map.on('click',this.click,this);this.redraw();
  }
  onRemove(map){
    cancelAnimationFrame(this.pending);map.off('move',this.moveCamera,this);map.off('moveend resize',this.redraw,this);map.off('zoomanim',this.animateZoom,this);
    map.off('mousemove',this.hover,this);map.off('click',this.click,this);this.tooltip.remove();this.canvas.remove();this.worker.terminate();this.gpu.destroy();this.map=null;
  }
  animateZoom(event){
    if(!this.origin)return;
    L.DomUtil.setTransform(this.canvas,this.map._latLngToNewLayerPoint(this.origin,event.zoom,event.center),this.map.getZoomScale(event.zoom,this.drawZoom));
  }
  moveCamera(){
    if(this.origin)L.DomUtil.setTransform(this.canvas,this.map.latLngToLayerPoint(this.origin),this.map.getZoomScale(this.map.getZoom(),this.drawZoom));
    this.redraw();
  }
  setStyle(){this.styleDirty=true;this.redraw();}
  updateMetadata(features){updateLocationMetadata(this.index,features);this.styleDirty=true;}
  bringToFront(){}
  setPolitical(features){
    if(this.politicalFeatures===features)return;
    this.politicalFeatures=features;this.political=features.length?createGridIndex(features):[];
    delete this.grids.political;
    if(features.length)this.sendIndex('political',this.political);else this.revisions.political++;
    this.styleDirty=true;this.redraw();
  }
  palettes(){
    const colors=new Uint8Array((this.index.length+1)*4),metadata=new Uint32Array((this.index.length+1)*2);
    const provinces=new Map(),groups=new Map();
    const number=(map,key)=>{if(!map.has(key))map.set(key,map.size+1);return map.get(key);};
    for(const {index,feature} of this.index){
      colors.set([...rgb(this.options.color(feature)),255],index*4);
      metadata[index*2]=number(provinces,feature.properties.parent_id);metadata[index*2+1]=number(groups,this.options.borderKey?.(feature));
    }
    const political=new Uint8Array(((this.political?.length||0)+1)*4);
    for(const {index,feature} of this.political||[])political.set([...rgb(this.options.politicalColor(feature)),255],index*4);
    this.gpu.upload('colors',colors);this.gpu.upload('metadata',metadata,2);this.gpu.upload('politicalColors',political);this.styleDirty=false;
  }
  redraw(){if(!this.pending)this.pending=requestAnimationFrame(()=>{this.pending=null;this.draw();});}
  draw(){
    if(!this.map||!this.grids.locations||this.lost)return;
    const started=performance.now(),zoom=this.map.getZoom(),scale=2**(zoom-GRID_ZOOM),size=this.map.getSize(),dpr=window.devicePixelRatio||1;
    if(this.styleDirty)this.palettes();
    const width=Math.round(size.x*dpr),height=Math.round(size.y*dpr);
    if(this.canvas.width!==width||this.canvas.height!==height){this.canvas.width=width;this.canvas.height=height;this.canvas.style.width=`${size.x}px`;this.canvas.style.height=`${size.y}px`;}
    this.origin=this.map.containerPointToLatLng([0,0]);this.drawZoom=zoom;
    L.DomUtil.setTransform(this.canvas,this.map.containerPointToLayerPoint([0,0]),1);
    const origin=this.map.project(this.origin,GRID_ZOOM);
    this.gpu.draw({origin,scale,zoom,dpr,localBorders:this.options.locationBorders(),selected:this.ids.get(this.options.selected())||0,hasPolitical:!!this.grids.political});
    Object.assign(this.canvas.dataset,{rendered:'true',locationBorders:String(zoom>=7&&this.options.locationBorders()),provinceBorders:'true',cellCount:String(width*height),renderMs:String(Math.round(performance.now()-started)),worker:'true',frame:[origin.x,origin.y,zoom,width,height].join('/'),uploads:String(this.gpu.uploads),ownershipUploads:String(this.gpu.ownershipUploads),cellPixels:String(scale),stride:'1'});
  }
  pick(latlng){const p=this.map.project(latlng,GRID_ZOOM);return this.index[pickOwnership(this.grids.locations,p.x,p.y)-1]?.feature||null;}
  hover(event){const f=this.pick(event.latlng);if(!f){this.tooltip.remove();return;}const text=document.createElement('span');text.textContent=this.options.label?.(f)||f.properties.name;this.tooltip.setContent(text).setLatLng(event.latlng).addTo(this.map);}
  click(event){const f=this.pick(event.latlng);if(f)this.options.select(f.id);}
}
