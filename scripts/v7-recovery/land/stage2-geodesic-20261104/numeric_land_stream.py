"""Experimental numeric land writer; the legacy writer remains production.

Ordinary row batches remove Python dispatch per source interval. The optional
geographic override still classifies each relevant land center with the exact
original scalar arithmetic; no pixel array or geographic shortcut is used.
"""
import hashlib
import json
import math
import os
from pathlib import Path

import numpy as np

from row_overlay import overlay_batch
from write_land_stream import MAX_U32,U32,_guard
from ural_delta import SCHEMA as URAL_DELTA_SCHEMA,classify_cell


class BatchRows:
    """Stream both offset and record files; retain only ordinary row batches."""
    def __init__(self,rows,runs,height,columns):
        if type(height) is not int or not 0<height<=MAX_U32 or columns not in (2,3):raise ValueError('invalid stream shape')
        self.rows=open(rows,'rb')
        try:self.runs=open(runs,'rb')
        except BaseException:self.rows.close();raise
        try:
            if os.fstat(self.rows.fileno()).st_size!=4*(height+1) or os.fstat(self.runs.fileno()).st_size%(columns*4):
                raise ValueError('invalid stream lengths')
            self.total=os.fstat(self.runs.fileno()).st_size//(columns*4)
            if self.rows.read(4)!=U32.pack(0):raise ValueError('offsets must start at zero')
            self.rows.seek(height*4);last=self.rows.read(4)
            if len(last)!=4 or U32.unpack(last)[0]!=self.total:raise ValueError('invalid stream offsets')
            self.rows.seek(4);self.height=height;self.columns=columns;self.y=0;self.position=0
        except BaseException:self.close();raise

    def next_rows(self,count):
        if type(count) is not int or count<1 or self.y+count>self.height:raise ValueError('invalid row batch')
        raw=self.rows.read(count*4)
        if len(raw)!=count*4:raise ValueError('truncated row offsets')
        offsets=np.r_[self.position,np.frombuffer(raw,dtype='<u4').astype(np.int64)]
        if np.any(offsets[1:]<offsets[:-1]) or np.any(offsets>self.total):raise ValueError('invalid stream offsets')
        final=int(offsets[-1]);length=(final-self.position)*self.columns*4;raw=self.runs.read(length)
        if len(raw)!=length:raise ValueError('truncated stream')
        offsets-=self.position;self.position=final;self.y+=count
        return offsets,np.frombuffer(raw,dtype='<u4').reshape(-1,self.columns)

    def finish(self):
        if self.y!=self.height or self.position!=self.total or self.rows.read(1) or self.runs.read(1):raise ValueError('stream count mismatch')

    def close(self):self.rows.close();self.runs.close()


class Delta:
    def __init__(self,rule,width,height):
        self.rule=rule;self.width=width
        self.counts={'land_centers':0,'other_land_labels':0,'europe_to_asia':0,'asia_to_europe':0}
        grid=rule.get('grid') if isinstance(rule,dict) else None
        if (not isinstance(rule,dict) or rule.get('schema')!=URAL_DELTA_SCHEMA or not isinstance(grid,dict) or
                set(grid)!={'width','height','west','north','step'} or grid!=
                {'width':width,'height':height,'west':-180,'north':90,'step':360/width}):
            raise ValueError('invalid Ural delta rule or grid binding')
        w,s,e,n=rule.get('scope_bounds',(None,None,None,None))
        if not all(type(v) in (int,float) for v in (w,s,e,n)) or not w<e or not s<n:
            raise ValueError('invalid Ural delta scope')
        if any(type(rule.get(key)) is not int or not 17<=rule[key]<=22 for key in ('europe_code','asia_code')) or rule['europe_code']==rule['asia_code']:
            raise ValueError('invalid Ural delta categories')
        step=grid['step']
        x0=max(0,math.ceil((w-grid['west'])/step-.5-1e-12))
        x1=min(width,math.floor((e-grid['west'])/step-.5+1e-12)+1)
        y0=max(0,math.ceil((grid['north']-n)/step-.5-1e-12))
        y1=min(height,math.floor((grid['north']-s)/step-.5+1e-12)+1)
        if x0>=x1 or y0>=y1:raise ValueError('Ural delta scope has no grid centers')
        self.bounds=x0,x1,y0,y1

    def apply(self,first_row,left,right,codes):
        width=self.width;x0,x1,y0,y1=self.bounds
        rows=left//width+first_row;starts=left%width;stops=(right-1)%width+1
        active=(codes!=0)&(rows>=y0)&(rows<y1)&(starts<x1)&(stops>x0)
        indices=np.flatnonzero(active)
        if not len(indices):return right,codes
        ends_parts=[];code_parts=[];cursor=0;rule=self.rule;grid=rule['grid']
        for index in indices:
            index=int(index)
            if cursor<index:ends_parts.append(right[cursor:index]);code_parts.append(codes[cursor:index])
            row=int(rows[index]);start=int(starts[index]);stop=int(stops[index]);original=int(codes[index])
            if original not in (rule['europe_code'],rule['asia_code']):
                self.counts['other_land_labels']+=1;raise ValueError('non-Europe/Asia land label in Ural delta scope')
            a,b=max(start,x0),min(stop,x1);base=(row-first_row)*width
            ends=[];labels=[]
            def emit(end,label):
                if labels and labels[-1]==label:ends[-1]=end
                else:ends.append(end);labels.append(label)
            if start<a:emit(base+a,original)
            lat=grid['north']-(row+.5)*grid['step']
            # Only land centers are observed by the override. Streaming the
            # changed RLE retains constant space for a huge constant-label span.
            for x in range(a,b):
                lon=grid['west']+(x+.5)*grid['step'];side=classify_cell(rule,lon,lat)
                if side is None:raise ValueError('land center fell outside active Ural delta scope')
                self.counts['land_centers']+=1
                if original==rule['europe_code'] and side==rule['asia_code']:self.counts['europe_to_asia']+=1
                elif original==rule['asia_code'] and side==rule['europe_code']:self.counts['asia_to_europe']+=1
                emit(base+x+1,side)
            if b<stop:emit(base+stop,original)
            ends_parts.append(np.asarray(ends,dtype=np.uint64));code_parts.append(np.asarray(labels,dtype=np.uint32));cursor=index+1
        if cursor<len(right):ends_parts.append(right[cursor:]);code_parts.append(codes[cursor:])
        return np.concatenate(ends_parts),np.concatenate(code_parts)

    def report(self):
        keys=('revision','boundary_id','boundary_sha256','route_id','route_sha256','scope_bounds','europe_code','asia_code')
        return {'schema':URAL_DELTA_SCHEMA,**{key:self.rule[key] for key in keys},'counts':self.counts,'status':'applied-to-land-cell-centers'}


def write_land_stream(width,height,component_rows,component_runs,physical_rows,physical_runs,mainland_rows,mainland_runs,roots,codes,mainland_roots,output_dir,*,disk_reserve_bytes=1<<30,delta_rule=None,batch_rows=128):
    if any(type(value) is not int or not 0<value<=MAX_U32 for value in (width,height)):
        raise ValueError('invalid grid dimensions')
    if type(disk_reserve_bytes) is not int or disk_reserve_bytes<0:raise ValueError('invalid resource guard')
    if type(batch_rows) is not int or batch_rows<1:raise ValueError('invalid row batch')
    delta=Delta(delta_rule,width,height) if delta_rule is not None else None
    mr=tuple(mainland_roots)
    if not mr or any(type(root) is not int or not 0<=root<=MAX_U32 for root in mr) or len(set(mr))!=len(mr):
        raise ValueError('non-empty unique valid mainland roots required')
    seed_ids=set(mr);out=Path(output_dir)
    cs,ps,ss,rs,ks=(os.stat(path).st_size for path in (component_runs,physical_runs,mainland_runs,roots,codes))
    if cs%12 or ps%8 or ss%8 or rs%4 or ks!=rs//4:raise ValueError('invalid input file lengths')
    n=rs//4;estimate=(2*(cs//12)+ps//8+ss//8+height)*8+4*(height+1)+(n+7)//8+4096
    _guard(out.parent,disk_reserve_bytes,estimate);out.mkdir(exist_ok=False)
    streams=[]
    try:
        with (out/'rows.u32le').open('xb') as rowout,(out/'runs.u32le').open('xb') as runout:
            rh,dh=hashlib.sha256(),hashlib.sha256();initial=U32.pack(0);rowout.write(initial);rh.update(initial)
            for rowpath,runpath,columns in ((component_rows,component_runs,3),(physical_rows,physical_runs,2),(mainland_rows,mainland_runs,2)):
                streams.append(BatchRows(rowpath,runpath,height,columns))
            assignments=np.fromfile(roots,dtype='<u4');labels=np.fromfile(codes,dtype=np.uint8)
            if (len(assignments)!=n or len(labels)!=n or np.any(assignments[1:]<=assignments[:-1]) or
                    np.any(np.isin(assignments,mr)) or np.any((labels<17)|(labels>22))):
                raise ValueError('invalid, duplicate, unsorted or mainland assignment')
            seen=np.zeros(n,dtype=bool);seeds_seen=set();total=0;land_cells=0
            for y in range(0,height,batch_rows):
                _guard(out,disk_reserve_bytes);count=min(batch_rows,height-y)
                fields=[value for stream in streams for value in stream.next_rows(count)];components=fields[1]
                left,right,owner,physical,seed=overlay_batch(width,*fields);present=owner>=0
                if np.any(present!=(physical==17)):raise ValueError('physical/component coverage mismatch at row '+str(y))
                if np.any((~present)&(seed!=0)):raise ValueError('mainland seed on water')
                root_values=components[:,2];is_seed=np.isin(root_values,mr);nonseed=~is_seed
                position=np.searchsorted(assignments,root_values)
                if np.any(nonseed):
                    if not n:raise ValueError('component has no assignment')
                    safe=np.minimum(position,n-1)
                    if np.any(nonseed&((position==n)|(assignments[safe]!=root_values))):raise ValueError('component has no assignment')
                seed_mask=np.zeros(len(left),dtype=bool);seed_mask[present]=is_seed[owner[present]]
                if np.any(seed_mask&(seed==0)):raise ValueError('mainland seed gap')
                if np.any(present&(~seed_mask)&(seed!=0)):raise ValueError('mainland seed overlaps non-mainland component')
                component_codes=np.zeros(len(components),dtype=np.uint32)
                if np.any(nonseed):component_codes[nonseed]=labels[position[nonseed]];seen[position[nonseed]]=True
                seeds_seen.update(map(int,np.unique(root_values[is_seed])))
                values=np.zeros(len(left),dtype=np.uint32);values[present]=component_codes[owner[present]];values[seed_mask]=seed[seed_mask]
                land_cells+=int((right[present]-left[present]).sum(dtype=np.uint64))
                ends,values=delta.apply(y,left,right,values) if delta is not None else (right,values)
                keep=np.r_[(values[:-1]!=values[1:])|(ends[:-1]%width==0),True]
                ends,values=ends[keep],values[keep];rows=(ends-1)//width
                pairs=np.column_stack(((ends-1)%width+1,values)).astype('<u4')
                counts=np.bincount(rows.astype(np.int64),minlength=count);offsets=np.cumsum(counts,dtype=np.uint64)+total
                if int(offsets[-1])>MAX_U32:raise ValueError('output run count exceeds u32')
                encoded=pairs.tobytes();runout.write(encoded);dh.update(encoded)
                encoded=offsets.astype('<u4').tobytes();rowout.write(encoded);rh.update(encoded);total=int(offsets[-1])
            for stream in streams:stream.finish()
            if seeds_seen!=seed_ids:raise ValueError('missing designated mainland roots')
            if not np.all(seen):raise ValueError('unused assignment roots')
            _guard(out,disk_reserve_bytes)
            for file in (rowout,runout):file.flush();os.fsync(file.fileno())
        report={'schema':'streamed-land-rle-research-v1','status':'complete','width':width,'height':height,'runs':total,
            'land_cells':land_cells,'assigned_roots':int(seen.sum()),'mainland_roots':sorted(seed_ids),
            'rows_sha256':rh.hexdigest(),'runs_sha256':dh.hexdigest()}
        if delta is not None:report['ural_delta']=delta.report()
        with (out/'report.json.partial').open('x',encoding='utf8') as file:
            json.dump(report,file,sort_keys=True,indent=2);file.write('\n');file.flush();os.fsync(file.fileno())
        os.replace(out/'report.json.partial',out/'report.json');return report
    finally:
        for stream in streams:stream.close()
