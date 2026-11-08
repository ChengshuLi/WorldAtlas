"""In-process Python batches over the already loaded GDAL public C API.

No custom native library, compiler, executable or subprocess is used. Arrow WKB
and NumPy tile buffers stay alive until GDAL has finished using their addresses.
"""
import ctypes as ct
import hashlib
import math
from pathlib import Path
import time

import numpy as np
import pyarrow as pa
from osgeo import gdal


class Envelope(ct.Structure):
    _fields_=[(name,ct.c_double) for name in ('min_x','max_x','min_y','max_y')]


def api():
    """Resolve GDAL through its loaded Python extension, never a guessed library."""
    library=ct.CDLL(gdal._gdal.__file__)
    signatures={
        'OGR_G_CreateFromWkb':(ct.c_int,[ct.c_void_p,ct.c_void_p,ct.POINTER(ct.c_void_p),ct.c_int]),
        'OGR_G_DestroyGeometry':(None,[ct.c_void_p]),
        'OGR_G_IsEmpty':(ct.c_int,[ct.c_void_p]),
        'OGR_G_GetGeometryType':(ct.c_int,[ct.c_void_p]),
        'OGR_GT_Flatten':(ct.c_int,[ct.c_int]),
        'OGR_G_IsValid':(ct.c_int,[ct.c_void_p]),
        'OGR_G_GetEnvelope':(None,[ct.c_void_p,ct.POINTER(Envelope)]),
        'OGR_G_GetGeometryCount':(ct.c_int,[ct.c_void_p]),
        'OGR_G_GetGeometryRef':(ct.c_void_p,[ct.c_void_p,ct.c_int]),
        'OGR_G_GetPointCount':(ct.c_int,[ct.c_void_p]),
        'OGR_G_GetPoints':(ct.c_int,[ct.c_void_p,ct.c_void_p,ct.c_int,ct.c_void_p,ct.c_int,ct.c_void_p,ct.c_int]),
        'OGR_G_SetPoints':(None,[ct.c_void_p,ct.c_int,ct.c_void_p,ct.c_int,ct.c_void_p,ct.c_int,ct.c_void_p,ct.c_int]),
        'OGR_G_CreateGeometry':(ct.c_void_p,[ct.c_int]),
        'OGR_G_AddGeometryDirectly':(ct.c_int,[ct.c_void_p,ct.c_void_p]),
        'GDALRasterizeGeometries':(ct.c_int,[ct.c_void_p,ct.c_int,ct.c_void_p,ct.c_int,ct.c_void_p,
            ct.c_void_p,ct.c_void_p,ct.c_void_p,ct.POINTER(ct.c_char_p),ct.c_void_p,ct.c_void_p]),
        'GDALVersionInfo':(ct.c_char_p,[ct.c_char_p]),
    }
    for name,(result,arguments) in signatures.items():
        function=getattr(library,name);function.restype=result;function.argtypes=arguments
    if library.GDALVersionInfo(b'VERSION_NUM').decode()!=gdal.VersionInfo():
        raise ValueError('GDAL runtime version mismatch')
    return library


def finite_points(data, starts, lengths, selected):
    """Recognize only exact finite standard 2D Point WKB, in either byte order."""
    result=np.zeros(len(starts),dtype=np.bool_)
    indices=np.flatnonzero(selected & (lengths==21))
    if not len(indices):return result
    offsets=starts[indices]
    headers=data[offsets[:,None]+np.arange(5)]
    little=np.all(headers==[1,1,0,0,0],axis=1)
    big=np.all(headers==[0,0,0,0,1],axis=1)
    for mask,dtype in ((little,'<f8'),(big,'>f8')):
        slots=np.flatnonzero(mask)
        if len(slots):
            coordinates=data[offsets[slots,None]+np.arange(5,21)].view(dtype).reshape(-1,2)
            result[indices[slots]]=np.all(np.isfinite(coordinates),axis=1)
    return result


class WaterBatch:
    def __init__(self, output=None, method='hybrid'):
        if method not in ('hybrid','tiled'):
            raise ValueError('method must be hybrid or tiled; global vector mode does not preserve tile-local pixel-center ties')
        self.method=method;self.api=api()
        self.provenance={'implementation':'python-gdal-c-api-v1','method':method,
            'binding_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'gdal':gdal.VersionInfo()}
        self.timings={'parse_validate_index_seconds':0.,'tile_burn_seconds':0.}

    def burn(self,raster,geometry,selected,grid,tile):
        if isinstance(geometry,pa.ExtensionArray) and geometry.type.extension_name in ('geoarrow.wkb','geoarrow.large_wkb'):
            geometry=geometry.storage
        if not (pa.types.is_binary(geometry.type) or pa.types.is_large_binary(geometry.type)):
            raise ValueError('GeoParquet geometry must be a binary WKB array')
        started=time.perf_counter();width,height,west,north,step=grid;width=int(width);height=int(height)
        buffers=geometry.buffers();count=len(geometry);status=np.zeros(count,dtype=np.uint8)
        offsets=np.frombuffer(buffers[1],dtype=np.int64 if pa.types.is_large_binary(geometry.type) else np.int32)
        starts=offsets[geometry.offset:geometry.offset+count]
        lengths=offsets[geometry.offset+1:geometry.offset+count+1]-starts
        data=np.frombuffer(buffers[2],dtype=np.uint8) if buffers[2] is not None else np.empty(0,dtype=np.uint8)
        selected=np.asarray(selected,dtype=np.bool_)
        valid=np.ones(count,dtype=np.bool_)
        if buffers[0] is not None:
            bits=np.frombuffer(buffers[0],dtype=np.uint8);positions=np.arange(count)+geometry.offset
            valid=(bits[positions//8]&(1<<(positions%8)))!=0
        points=finite_points(data,starts,lengths,selected & valid)
        owned=set();tiles={};coordinates={};a=self.api
        def own(handle):
            if not handle:raise ValueError('GDAL geometry creation failed')
            owned.add(handle);return handle
        def append(parent,child):
            if a.OGR_G_AddGeometryDirectly(parent,child):raise ValueError('GDAL geometry append failed')
            owned.remove(child)
        def envelope(handle):
            bounds=Envelope();a.OGR_G_GetEnvelope(handle,ct.byref(bounds));return bounds
        def extent(bounds):
            return (max(0,math.floor((bounds.min_x-west)/step)),
                    min(width-1,math.floor((bounds.max_x-west)/step)),
                    max(0,math.floor((north-bounds.max_y)/step)),
                    min(height-1,math.floor((north-bounds.min_y)/step)))
        def strip_geometry(source,top,bottom):
            kind=a.OGR_GT_Flatten(a.OGR_G_GetGeometryType(source));result=own(a.OGR_G_CreateGeometry(kind))
            if kind==6:
                for i in range(a.OGR_G_GetGeometryCount(source)):
                    part=strip_geometry(a.OGR_G_GetGeometryRef(source,i),top,bottom)
                    if part:append(result,part)
                return result if a.OGR_G_GetGeometryCount(result) else None
            for i in range(a.OGR_G_GetGeometryCount(source)):
                ring=a.OGR_G_GetGeometryRef(source,i)
                if ring not in coordinates:
                    size=a.OGR_G_GetPointCount(ring);values=np.empty((size,2),dtype=np.float64)
                    if a.OGR_G_GetPoints(ring,values.ctypes.data,16,values.ctypes.data+8,16,None,0)!=size:
                        raise ValueError('GDAL ring coordinate read failed')
                    coordinates[ring]=values
                values=coordinates[ring];ys=values[:,1];following=np.roll(ys,-1)
                edges=(np.minimum(ys,following)<=top+step)&(np.maximum(ys,following)>=bottom-step)
                keep=edges|np.roll(edges,1)
                if not np.any(keep):
                    if i==0:return None
                    continue
                retained=values[keep]
                if not np.array_equal(retained[0],retained[-1]):retained=np.vstack((retained,retained[0]))
                view=own(a.OGR_G_CreateGeometry(101))
                a.OGR_G_SetPoints(view,len(retained),retained.ctypes.data,16,retained.ctypes.data+8,16,None,0)
                append(result,view)
            return result
        try:
            parsed=[]
            for i in np.flatnonzero(selected):
                if not valid[i]:status[i]=5;return status,int(i)
                if points[i]:status[i]=3;continue
                length=int(lengths[i]);raw=ct.c_void_p()
                if length<=0 or length>np.iinfo(np.int32).max:
                    status[i]=2;return status,int(i)
                error=a.OGR_G_CreateFromWkb(data.ctypes.data+int(starts[i]),None,ct.byref(raw),length)
                if raw.value:own(raw.value)
                if error or not raw.value or a.OGR_G_IsEmpty(raw):status[i]=2;return status,int(i)
                kind=a.OGR_GT_Flatten(a.OGR_G_GetGeometryType(raw))
                if kind not in (3,6):status[i]=3;continue
                if not a.OGR_G_IsValid(raw):status[i]=4;continue
                bounds=envelope(raw)
                if not all(math.isfinite(getattr(bounds,key)) for key,_ in Envelope._fields_):
                    status[i]=6;return status,int(i)
                status[i]=1;parsed.append((raw.value,kind,bounds))
            for raw,kind,bounds in parsed:
                x0,x1,y0,y1=extent(bounds)
                if x0>x1 or y0>y1:continue
                spans_rows=y0//tile!=y1//tile;strips={}
                if self.method=='hybrid' and kind==6:
                    candidates=set()
                    for part in range(a.OGR_G_GetGeometryCount(raw)):
                        component=a.OGR_G_GetGeometryRef(raw,part)
                        if a.OGR_G_IsEmpty(component):continue
                        p,q,r,s=extent(envelope(component))
                        if p<=q and r<=s:
                            candidates.update((ty,tx) for ty in range(r//tile,s//tile+1) for tx in range(p//tile,q//tile+1))
                    candidates=sorted(candidates)
                else:candidates=((ty,tx) for ty in range(y0//tile,y1//tile+1) for tx in range(x0//tile,x1//tile+1))
                for ty,tx in candidates:
                    view=raw
                    if self.method=='hybrid' and spans_rows:
                        if ty not in strips:
                            strips[ty]=strip_geometry(raw,north-ty*tile*step,north-min(height,(ty+1)*tile)*step)
                        view=strips[ty]
                    if view:tiles.setdefault((tx,ty),[]).append(view)
            validated=time.perf_counter();self.timings['parse_validate_index_seconds']+=validated-started
            bands=np.array([1],dtype=np.int32);options=(ct.c_char_p*2)(b'OPTIM=RASTER',None)
            for (tx,ty),handles in tiles.items():
                x,y=tx*tile,ty*tile;w,h=min(tile,width-x),min(tile,height-y)
                values=raster.GetRasterBand(1).ReadAsArray(x,y,w,h,buf_type=gdal.GDT_Byte)
                target=gdal.GetDriverByName('MEM').Create('',w,h,0,gdal.GDT_Byte)
                if target.AddBand(gdal.GDT_Byte,options=[f'DATAPOINTER={values.ctypes.data}','PIXELOFFSET=1',f'LINEOFFSET={w}']):
                    raise ValueError('GDAL borrowed tile band creation failed')
                if target.SetGeoTransform((west+x*step,step,0,north-y*step,0,-step)):
                    raise ValueError('GDAL tile transform failed')
                pointers=np.asarray(handles,dtype=np.uintp);burns=np.ones(len(handles),dtype=np.float64)
                if a.GDALRasterizeGeometries(int(target.this),1,bands.ctypes.data,len(handles),pointers.ctypes.data,
                        None,None,burns.ctypes.data,options,None,None):
                    raise ValueError('GDAL water geometry rasterization failed: '+gdal.GetLastErrorMsg())
                target.FlushCache();target=None
                raster.GetRasterBand(1).WriteArray(values,x,y)
            self.timings['tile_burn_seconds']+=time.perf_counter()-validated
            return status,None
        finally:
            for handle in owned:a.OGR_G_DestroyGeometry(handle)
