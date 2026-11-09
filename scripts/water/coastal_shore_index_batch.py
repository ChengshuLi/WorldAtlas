"""Batched RLE interval overlay for the exact four-neighbor shoreline index.

All physical and land boundaries remain cuts. Adjacent physical rows are shifted
by one row in flattened coordinates. A shared cut-rank map propagates all four
RLE value streams without repeated binary searches or per-cell expansion.
Batches are complete row ranges, not data/resource ceilings.
"""
import numpy as np

from coastal_shore_index import CoastalShoreIndex


def flat_rows(grid, first_row, end_row, width):
    offsets,runs=grid;first,last=int(offsets[first_row]),int(offsets[end_row])
    values=runs[2*first:2*last]
    local_ends=values[0::2];categories=values[1::2]
    counts=np.diff(offsets[first_row:end_row+1].astype(np.int64))
    row=np.repeat(np.arange(first_row,end_row,dtype=np.uint64),counts)
    ends=local_ends.astype(np.uint64)+row*width
    terminals=offsets[first_row+1:end_row+1].astype(np.int64)-first-1
    if (not len(ends) or np.any(local_ends[terminals]!=width) or int(ends[0])<=first_row*width
        or np.any(ends[1:]<=ends[:-1])):
        raise ValueError('invalid RLE row')
    return ends,categories,first


class BatchedCoastalShoreIndex(CoastalShoreIndex):
    def __init__(self,physical,land,width,height,*,rows_per_batch=256):
        if any(type(value) is not int or value<=0 for value in (width,height,rows_per_batch)):
            raise ValueError('invalid grid or row batch')
        for offsets,runs in (physical,land):
            if (len(offsets)!=height+1 or len(runs)%2 or int(offsets[0])!=0
                or int(offsets[-1])!=len(runs)//2 or np.any(offsets[1:]<=offsets[:-1])):
                raise ValueError('invalid RLE row')
        self.width,self.height=width,height
        all_starts=[];all_ends=[];all_codes=[];offsets=[np.asarray([0],dtype=np.uint64)];total=0
        prows,_=physical
        for y0 in range(0,height,rows_per_batch):
            y1=min(height,y0+rows_per_batch);begin,end=y0*width,y1*width
            context_first=max(0,y0-1);context_end=min(height,y1+1)
            pe,pv,first=flat_rows(physical,context_first,context_end,width)
            le,lv,_=flat_rows(land,y0,y1,width)
            if np.any((pv!=1)&(pv!=17)):raise ValueError('invalid physical or land row')
            def portion(a,b):
                a,b=int(prows[a])-first,int(prows[b])-first
                return pe[a:b],pv[a:b]
            # Select neighboring source rows before shifting, avoiding unsigned
            # wrap at the poles even for the largest supported coordinates.
            previous,prev_values=portion(max(0,y0-1),max(0,y1-1));previous=previous+width
            following,next_values=portion(min(height,y0+1),min(height,y1+1));following=following-width
            current,cv=portion(y0,y1)
            # Missing polar neighbors contribute no water. Each of the four
            # RLE streams then covers the entire current block.
            if y0==0:
                previous=np.r_[np.uint64(width),previous];prev_values=np.r_[np.uint32(0),prev_values]
            if y1==height:
                following=np.r_[following,np.uint64(end)];next_values=np.r_[next_values,np.uint32(0)]
            groups=(current,le,previous,following)
            cuts,inverse=np.unique(np.concatenate((np.asarray([begin],dtype=np.uint64),*groups)),return_inverse=True)
            ranks=[];offset=1
            for group in groups:
                ranks.append(inverse[offset:offset+len(group)]);offset+=len(group)
            def expand(values,end_ranks):
                # Repeat over CUT intervals, never over individual grid cells.
                return np.repeat(values,np.diff(np.r_[0,end_ranks]))
            starts,stops=cuts[:-1],cuts[1:]
            physical_values=expand(cv,ranks[0]);categories=expand(lv,ranks[1])
            if np.any((physical_values==17)&((categories<17)|(categories>22))):
                raise ValueError('invalid physical or land row')
            wet=expand(prev_values==1,ranks[2])|expand(next_values==1,ranks[3])
            chosen=(physical_values==17)&wet
            aa,bb,cc=starts[chosen],stops[chosen],categories[chosen]
            ce=current
            changes=np.flatnonzero((cv[:-1]!=cv[1:])&(ce[:-1]%width!=0))
            side=np.where(cv[changes]==17,ce[changes]-1,ce[changes])
            side_categories=categories[np.where(cv[changes]==17,ranks[0][changes]-1,ranks[0][changes])]
            current_first=int(prows[y0])
            firsts=prows[y0:y1].astype(np.int64)-current_first
            lasts=prows[y0+1:y1+1].astype(np.int64)-current_first-1
            different=cv[firsts]!=cv[lasts]
            seam_rows=np.arange(y0,y1,dtype=np.uint64)[different]
            first_land=cv[firsts[different]]==17
            seam=np.where(first_land,seam_rows*width,seam_rows*width+width-1)
            row_end_ranks=ranks[0][lasts];row_start_ranks=np.r_[0,row_end_ranks[:-1]]
            seam_categories=categories[np.where(first_land,row_start_ranks[different],row_end_ranks[different]-1)]
            side=np.concatenate((side,seam))
            if len(side):
                aa=np.concatenate((aa,side));bb=np.concatenate((bb,side+1))
                cc=np.concatenate((cc,side_categories,seam_categories))
            if len(aa):
                order=np.argsort(aa,kind='stable');aa,bb,cc=aa[order],bb[order],cc[order]
                split=np.r_[True,(aa[1:]>np.maximum.accumulate(bb)[:-1])|(cc[1:]!=cc[:-1])|(aa[1:]//width!=aa[:-1]//width)]
                indices=np.flatnonzero(split);row=aa[indices]//width
                counts=np.bincount((row-y0).astype(np.intp),minlength=y1-y0)
                all_starts.append((aa[indices]-row*width).astype(np.uint32))
                all_ends.append((np.maximum.reduceat(bb,indices)-row*width).astype(np.uint32))
                all_codes.append(cc[indices].astype(np.uint8))
            else:counts=np.zeros(y1-y0,dtype=np.int64)
            offsets.append(total+np.cumsum(counts,dtype=np.uint64));total=int(offsets[-1][-1])
        self.offsets=np.concatenate(offsets)
        self.starts=np.concatenate(all_starts) if all_starts else np.empty(0,dtype=np.uint32)
        self.ends=np.concatenate(all_ends) if all_ends else np.empty(0,dtype=np.uint32)
        self.codes=np.concatenate(all_codes) if all_codes else np.empty(0,dtype=np.uint8)
