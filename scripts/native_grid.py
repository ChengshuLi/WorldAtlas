"""Read the canonical exclusive-end row-run grid without dense-world allocation."""
import gzip
import json
from pathlib import Path
import numpy as np

class NativeGrid:
    def __init__(self, folder):
        self.folder=Path(folder)
        self.meta=json.loads((self.folder/'proposal.json').read_text())
        self.width=self.meta['width'];self.height=self.meta['height'];self.step=self.meta['step']
        self.rows=np.frombuffer(gzip.decompress((self.folder/'rows.u32.gz').read_bytes()),'<u4')
        self.runs=np.frombuffer(gzip.decompress((self.folder/'runs.u32.gz').read_bytes()),'<u4').reshape(-1,2)
        assert len(self.rows)==self.height+1 and self.rows[-1]==len(self.runs)
    def row(self,y):
        if not 0<=y<self.height:raise IndexError(y)
        runs=self.runs[self.rows[y]:self.rows[y+1]]
        assert runs[-1,0]==self.width
        return np.repeat(runs[:,1],np.diff(np.r_[0,runs[:,0]])).astype('uint8')
    def at(self,x,y):
        if not(0<=x<self.width and 0<=y<self.height):raise IndexError((x,y))
        runs=self.runs[self.rows[y]:self.rows[y+1]]
        return int(runs[np.searchsorted(runs[:,0],x,side='right'),1])
    def at_lonlat(self,lon,lat):
        x=int(np.floor((lon+180)/self.step))%self.width
        y=int(np.floor((90-lat)/self.step))
        return self.at(x,y)
    @staticmethod
    def is_land(raw):return np.asarray(raw)>=16
