"""Disk-backed exact spherical mainland-run search with bounded tile cache."""
from collections import OrderedDict
import math,ctypes,subprocess
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree

class TileIndex:
    def __init__(self, directory,width,height,step,north, segment_distance,unit,radius,
                 tile_cells=1024, cache_bytes=64*1024*1024, buffer_bytes=64*1024):
        self.dir=Path(directory);self.dir.mkdir();self.w=width;self.h=height;self.step=step;self.north=north
        source=Path(__file__).resolve().parent/'distance_kernel.cpp';libpath=self.dir/'distance-kernel.so'
        built=subprocess.run(['g++','-O3','-std=c++17','-Wall','-Wextra','-Werror','-fPIC','-shared',str(source),'-o',str(libpath)],capture_output=True,text=True)
        if built.returncode:raise ValueError('distance kernel compilation failed: '+built.stderr[-2000:])
        self.lib=ctypes.CDLL(str(libpath));self.kernel=self.lib.nearest_haversines
        self.kernel.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p]
        self.kernel.restype=None
        maxdiff=max(width,height)+1;self.sin2=np.sin(np.arange(maxdiff,dtype=np.float64)*step*math.pi/360)**2
        self.coslat=np.cos(np.deg2rad(north-(np.arange(height,dtype=np.float64)+.5)*step))
        self.segment_distance=segment_distance;self.unit=unit;self.R=radius;self.tile_cells=tile_cells
        self.cache_bytes=cache_bytes;self.buffer_bytes=buffer_bytes;self.buffers={};self.tiles=set();self.cache=OrderedDict();self.cache_size=0
        self.current_tile_y=None
        self.count=0;self.cache_hits=0;self.cache_misses=0;self.read_bytes=0;self.max_resident_cache=0
    def path(self,tile):return self.dir/('%05d-%05d.bin'%tile)
    def flush(self,tile):
        buf=self.buffers.get(tile)
        if buf:
            with open(self.path(tile),'ab') as f:f.write(buf)
            buf.clear()
    def append(self,y,a,b,code):
        self.append_row(y,np.asarray([(a,b,code)],dtype=np.uint32))
    def append_row(self,y,segments):
        """Append sorted non-overlapping row segments in vectorized tile batches."""
        if not len(segments):return
        segments=np.asarray(segments,dtype=np.uint32).reshape(-1,3)
        if np.any(segments[:,0]>=segments[:,1]) or (len(segments)>1 and np.any(segments[1:,0]<segments[:-1,1])):raise ValueError('seed row segments must be ordered and disjoint')
        cell=self.tile_cells;tile_y=y//cell
        if self.current_tile_y is None:self.current_tile_y=tile_y
        if tile_y!=self.current_tile_y:
            if tile_y<self.current_tile_y:raise ValueError('seed rows must be appended in order')
            for t in self.buffers:self.flush(t)
            self.buffers.clear();self.current_tile_y=tile_y
        start=int(segments[0,0])//cell; stop=int(segments[-1,1]-1)//cell
        tiles=np.arange(start,stop+1,dtype=np.int64);lefts=tiles*cell;rights=np.minimum(self.w,lefts+cell)
        lows=np.searchsorted(segments[:,1],lefts,side='right');highs=np.searchsorted(segments[:,0],rights,side='left')
        touched=np.flatnonzero(lows!=highs)
        for t in touched:
            tx=int(tiles[t]);left=int(lefts[t]);right=int(rights[t]);lo=int(lows[t]);hi=int(highs[t])
            part=segments[lo:hi];n=len(part); records=np.empty((n,4),dtype='<u4');records[:,0]=y
            records[:,1]=np.maximum(part[:,0],left);records[:,2]=np.minimum(part[:,1],right);records[:,3]=part[:,2]
            tile=(tile_y,tx);buf=self.buffers.setdefault(tile,bytearray());buf.extend(records.tobytes());self.tiles.add(tile);self.count+=n
            if len(buf)>=self.buffer_bytes:self.flush(tile)
    def finish(self):
        for tile in self.buffers:self.flush(tile)
        self.buffers.clear()
        if not self.tiles:raise ValueError('no mainland seeds')
        self.ids=sorted(self.tiles);self.tree_points=[];radii=[]
        for ty,tx in self.ids:
            y0=ty*self.tile_cells;y1=min(self.h,y0+self.tile_cells);x0=tx*self.tile_cells;x1=min(self.w,x0+self.tile_cells)
            lat=self.north-(y0+y1)*self.step/2;lon=-180+(x0+x1)*self.step/2
            self.tree_points.append((lat,lon))
            # Triangle path along a meridian then parallel: conservative even
            # near a pole; x/y limits include the full tile, not only centers.
            radii.append(((y1-y0)+(x1-x0))*self.step*math.pi/180*self.R/2)
        points=np.asarray(self.tree_points);self.tree=cKDTree(self.unit(points[:,0],points[:,1]));self.maxradius=max(radii)
    def validate_batch(self,raw):
        if len(raw)%16:raise ValueError('corrupt tile length')
        data=np.frombuffer(raw,dtype='<u4').reshape(-1,4)
        if len(data) and (np.any(data[:,0]>=self.h) or np.any(data[:,1]>=data[:,2]) or np.any(data[:,2]>self.w) or np.any((data[:,3]<17)|(data[:,3]>22))):
            raise ValueError('corrupt tile records')
        return data
    def arrays(self,tile):
        if tile in self.cache:
            self.cache_hits+=1;data=self.cache.pop(tile);self.cache[tile]=data;return [data]
        self.cache_misses+=1;path=self.path(tile);size=path.stat().st_size
        if size<=self.cache_bytes:
            while self.cache and self.cache_size+size>self.cache_bytes:
                _,v=self.cache.popitem(last=False);self.cache_size-=v.nbytes
            with open(path,'rb') as f:data=self.validate_batch(f.read())
            self.read_bytes+=size;self.cache[tile]=data;self.cache_size+=size;self.max_resident_cache=max(self.max_resident_cache,self.cache_size)
            return [data]
        # Oversized tiles stream in capped chunks instead of breaching the cache.
        def stream():
            with open(path,'rb') as f:
                while True:
                    raw=f.read(max(16,(self.cache_bytes//16)*16))
                    if not raw:break
                    self.read_bytes+=len(raw);yield self.validate_batch(raw)
        return stream()
    def nearest(self,y,a,b,tol):
        lat=self.north-(y+.5)*self.step;lon=-180+((a+b-1)/2+.5)*self.step
        point=self.unit(np.array([lat]),np.array([lon]))[0]
        qr=(b-a-1)*self.step*math.pi/180*self.R/2
        k=min(16,len(self.ids));seen=set(); distances={}
        while True:
            chord,idx=self.tree.query(point,k=k,workers=1);chord=np.atleast_1d(chord);idx=np.atleast_1d(idx)
            for i in idx:
                i=int(i)
                if i in seen:continue
                seen.add(i)
                for data in self.arrays(self.ids[i]):
                    # Compiled bounded-batch loop: compare haversines first,
                    # converting only each tile's six minima back to metres.
                    hav=np.full(6,np.inf,dtype=np.float64)
                    self.kernel(data.ctypes.data,len(data),y,a,b,self.w,self.sin2.ctypes.data,self.coslat.ctypes.data,hav.ctypes.data)
                    for i in np.flatnonzero(np.isfinite(hav)):
                        code=int(i)+17;angle=2*math.asin(math.sqrt(min(1,max(0,float(hav[i])))))
                        distances[code]=min(distances.get(code,math.inf),self.R*angle)
            best=min(distances.values())
            lower=2*self.R*math.asin(min(1,float(chord[-1])/2))-self.maxradius-qr
            if k==len(self.ids) or lower>best+tol+1e-6:return distances
            k=min(2*k,len(self.ids))
    def stats(self):
        return {'tile_count':len(self.ids),'seed_segments':self.count,'cache_limit_bytes':self.cache_bytes,'cache_peak_bytes':self.max_resident_cache,'cache_hits':self.cache_hits,'cache_misses':self.cache_misses,'tile_bytes_read':self.read_bytes}
