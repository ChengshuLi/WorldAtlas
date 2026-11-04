#!/usr/bin/env python3
"""Diagnostic only: compare mismatch centers to current polygons and alignment to old mask.

Usage: /usr/bin/python3 cell_diagnostics.py config.json > results.json
Config specifies SHA-256 pins for all inputs, including every vector sidecar. Historical
mask is a derived artifact, not the missing historical polygons. This cannot attribute cause.
"""
import collections, hashlib, json, math, sys
from pathlib import Path
from osgeo import gdal, ogr, osr
import numpy as np

def verified(spec):
    if not isinstance(spec,dict) or set(spec)!={'path','sha256'} or not isinstance(spec['sha256'],str) or len(spec['sha256'])!=64 or any(x not in '0123456789abcdef' for x in spec['sha256']): raise ValueError('invalid input pin')
    path=Path(spec['path']); h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024), b''): h.update(b)
    if h.hexdigest()!=spec['sha256']: raise ValueError('hash mismatch: '+str(path))
    return str(path)

def main(cfg):
    c=json.loads(Path(cfg).read_text()); files=c['inputs']; mismatch=verified(files['mismatch']); oldp=verified(files['historical_land_mask']);newp=verified(files['new_land_mask']); vector_files=[verified(x) for x in files['new_land_files']]; source=files['new_land_dataset']
    source_path=Path(source).resolve(); pinned={Path(x).resolve() for x in vector_files}
    if source_path not in pinned or source_path.suffix.lower()!='.shp': raise ValueError('new_land_dataset must be a pinned shapefile')
    for extension in ('.shp','.shx','.dbf','.prj'):
        if source_path.with_suffix(extension) not in pinned: raise ValueError('missing required shapefile sidecar pin: '+extension)
    for extension in ('.cpg','.qix','.sbn','.sbx'):
        path=source_path.with_suffix(extension)
        if path.exists() and path not in pinned: raise ValueError('un-pinned shapefile sidecar: '+extension)
    W=c['grid']['width']; H=c['grid']['height']; west=c['grid']['west']; north=c['grid']['north']; step=c['grid']['step']
    if type(W) is not int or type(H) is not int or W<=0 or H<=0 or any(type(v) not in (int,float) or not math.isfinite(v) for v in (west,north,step)) or step<=0: raise ValueError('invalid grid')
    bb=c['study_bbox']
    if not isinstance(bb,list) or len(bb)!=4 or any(type(v) not in (int,float) or not math.isfinite(v) for v in bb) or bb[0]>=bb[2] or bb[1]>=bb[3]: raise ValueError('invalid study bbox')
    pts=[]; bins=collections.defaultdict(list)
    with open(mismatch) as mismatch_file:
        for line in mismatch_file:
            d=json.loads(line)
            if (any(type(d.get(k)) is not int for k in ('row','start','end','reference','candidate')) or not 0<=d['row']<H or not 0<=d['start']<d['end']<=W or d['reference'] not in (1,17) or d['candidate'] not in (1,17) or d['reference']==d['candidate']): raise ValueError('invalid mismatch span')
            for x in range(d['start'],d['end']):
                y=d['row']; lon=west+(x+.5)*step;lat=north-(y+.5)*step
                q=ogr.Geometry(ogr.wkbPoint);q.AddPoint_2D(lon,lat)
                p={'row':y,'column':x,'lon':lon,'lat':lat,'reference':d['reference'],'candidate':d['candidate'],'inside':0,'touching':0,'point':q};bins[(math.floor(lon),math.floor(lat))].append(len(pts));pts.append(p)
    ds=ogr.Open(source)
    if ds is None: raise ValueError('cannot open new land dataset')
    layer=ds.GetLayer()
    if layer is None: raise ValueError('missing new land layer')
    expected_srs=osr.SpatialReference();expected_srs.ImportFromEPSG(4326);expected_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    def same_wgs84(srs):
        if srs is None:return False
        srs=srs.Clone();srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER);return bool(srs.IsSame(expected_srs))
    if not same_wgs84(layer.GetSpatialRef()): raise ValueError('land dataset must use WGS84')
    for feature in layer:
        geom=feature.GetGeometryRef()
        if geom is None:continue
        a,b,d,e=geom.GetEnvelope()
        for (bx,by),ids in bins.items():
            if bx+1<a or bx>b or by+1<d or by>e:continue
            for i in ids:
                p=pts[i];x=p['lon'];y=p['lat']
                if not (a<=x<=b and d<=y<=e):continue
                if geom.Contains(p['point']):p['inside']+=1
                elif geom.Intersects(p['point']):p['touching']+=1
    categories=collections.Counter((p['reference'],p['candidate'],p['inside']>0,p['touching']>0) for p in pts)
    report={'mismatch_cells':len(pts),'current_polygon_containment':[{'reference':k[0],'candidate':k[1],'strictly_inside':k[2],'touching':k[3],'count':v} for k,v in sorted(categories.items())], 'limitations':'Historical mask is derived, not historical source geometry. Neither containment nor shifts establish source-edit causation.'}
    Q=[p for p in pts if bb[0]<=p['lon']<bb[2] and bb[1]<=p['lat']<bb[3]]
    if not Q: raise ValueError('study bbox contains no mismatch points')
    margin=10;x0=min(p['column'] for p in Q)-margin;x1=max(p['column'] for p in Q)+margin+1;y0=min(p['row'] for p in Q)-margin;y1=max(p['row'] for p in Q)+margin+1
    if x0<0 or y0<0 or x1>W or y1>H:raise ValueError('study window out of grid')
    w=x1-x0;h=y1-y0;old_ds=gdal.Open(oldp);new_ds=gdal.Open(newp)
    for raster in (old_ds,new_ds):
        if raster is None: raise ValueError('cannot open land mask')
        raster_srs=raster.GetSpatialRef()
        if not same_wgs84(raster_srs): raise ValueError('raster must use WGS84')
        if raster.RasterXSize!=W or raster.RasterYSize!=H:raise ValueError('raster dimensions differ from grid')
        expected=(west,step,0,north,0,-step)
        if any(abs(a-b)>1e-12 for a,b in zip(raster.GetGeoTransform(),expected)):raise ValueError('raster transform differs from grid')
    old=old_ds.ReadAsArray(x0,y0,w,h);new=new_ds.ReadAsArray(x0,y0,w,h)
    if old is None or new is None or np.any(~np.isin(old,[0,1])) or np.any(~np.isin(new,[0,1])): raise ValueError('land masks must be binary')
    r=3;reference=old[r:-r,r:-r];current=new[r:-r,r:-r]
    shifts=[{'dy':dy,'dx':dx,'differences':int(np.count_nonzero(reference!=new[r+dy:h-r+dy,r+dx:w-r+dx]))} for dy in range(-3,4) for dx in range(-3,4)]
    layer.ResetReading(); layer.SetSpatialFilterRect(west+x0*step-.01,north-y1*step-.01,west+x1*step+.01,north-y0*step+.01)
    mds=ogr.GetDriverByName('Memory').CreateDataSource(''); ml=mds.CreateLayer('land',srs=layer.GetSpatialRef(),geom_type=ogr.wkbUnknown)
    for f in layer:
        ff=ogr.Feature(ml.GetLayerDefn());ff.SetGeometry(f.GetGeometryRef());ml.CreateFeature(ff)
    sub=[]
    for dy in (-.5,-.25,0,.25,.5):
      for dx in (-.5,-.25,0,.25,.5):
        rast=gdal.GetDriverByName('MEM').Create('',w,h,1,gdal.GDT_Byte);rast.SetGeoTransform((west+(x0+dx)*step,step,0,north-(y0+dy)*step,0,-step));gdal.RasterizeLayer(rast,[1],ml,burn_values=[1]); a=rast.ReadAsArray()[r:-r,r:-r]
        sub.append({'dy':dy,'dx':dx,'differences':int(np.count_nonzero(reference!=a)),'differences_from_new_mask':int(np.count_nonzero(current!=a))})
    report['study']={'bbox':bb,'changed_cells':len(Q),'window_xy':[x0,y0,x1,y1],'interior_cells':int(reference.size),'features':ml.GetFeatureCount(),'integer_shifts':shifts,'subcell_shifts':sub}
    print(json.dumps(report,indent=2))
if __name__=='__main__':
    if len(sys.argv)!=2:raise SystemExit(__doc__)
    main(sys.argv[1])
