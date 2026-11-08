"""General NumPy run composition for GDAL Byte seed strips, no native helper.

Only actual mask transitions inside selected physical component intervals can
change the output. Whole-component rules need one span, not a per-cell loop.
Rows remain explicit boundaries even when a zero interval spans several rows.
"""
import numpy as np

MAX_U32=(1 << 32)-1


class RuleIndex:
    def __init__(self, rules):
        table=[]
        for rule in rules:
            if len(rule)!=4 or any(isinstance(value,(bool,np.bool_)) or not isinstance(value,(int,np.integer)) for value in rule):
                raise ValueError('integer root/bit/inside/outside rules required')
            root,bit,inside,outside=map(int,rule)
            if (not 0<=root<=MAX_U32 or bit not in (0,1,2,4,8,16,32,64,128) or
                    not 17<=inside<=22 or not 17<=outside<=22 or (bit==0 and inside!=outside)):
                raise ValueError('invalid seed rule')
            table.append((root,bit,inside,outside))
        if not table:raise ValueError('missing seed rules')
        self.table=np.asarray(table,dtype='<u4')
        self.order=np.argsort(self.table[:,0],kind='stable');self.roots=self.table[self.order,0]
        if np.any(self.roots[1:]==self.roots[:-1]):raise ValueError('duplicate seed root')

    def required_bits(self, records):
        """Polygon dependencies of present selected intervals, never geography.

        Full interval/offset validation still happens in strip before output.
        Whole-component rules and unselected roots do not inspect any mask bit.
        """
        records=np.asarray(records)
        if records.ndim!=2 or records.shape[1]!=3 or records.dtype.kind not in 'iu':
            raise ValueError('component records required')
        positions=np.searchsorted(self.roots,records[:,2]);safe=np.minimum(positions,len(self.roots)-1)
        selected=(positions<len(self.roots)) & (self.roots[safe]==records[:,2])
        return int(np.bitwise_or.reduce(self.table[self.order[positions[selected]],1],initial=np.uint32(0)))

    def strip(self, mask, offsets, records):
        mask=np.asarray(mask);offsets=np.asarray(offsets);records=np.asarray(records)
        if mask.dtype!=np.uint8 or mask.ndim!=2 or min(mask.shape)<=0:raise ValueError('Byte raster strip required')
        height,width=mask.shape
        if (offsets.ndim!=1 or len(offsets)!=height+1 or offsets.dtype.kind not in 'iu' or
                records.ndim!=2 or records.shape[1]!=3 or records.dtype.kind not in 'iu' or
                int(offsets[0])!=0 or int(offsets[-1])!=len(records) or np.any(offsets[1:]<offsets[:-1])):
            raise ValueError('invalid component strip offsets or records')
        if len(records) and (np.any(records<0) or np.any(records>MAX_U32)):
            raise ValueError('component values outside uint32')
        rows=np.searchsorted(offsets,np.arange(len(records)),side='right')-1
        if len(records):
            starts,ends=records[:,0],records[:,1]
            if (np.any(starts>=ends) or np.any(ends>width) or
                    np.any((rows[1:]==rows[:-1]) & (starts[1:]<ends[:-1]))):
                raise ValueError('invalid or overlapping component intervals')
        pos=np.searchsorted(self.roots,records[:,2]);safe=np.minimum(pos,len(self.roots)-1)
        selected=(pos<len(self.roots)) & (self.roots[safe]==records[:,2])
        selected_rule=self.order[pos[selected]]
        starts=rows[selected].astype(np.int64)*width+records[selected,0].astype(np.int64)
        ends=rows[selected].astype(np.int64)*width+records[selected,1].astype(np.int64)
        bits=self.table[selected_rule,1];flat=mask.reshape(-1)
        groups=[]
        for bit in np.unique(bits):
            chosen=np.flatnonzero(bits==bit);a,b=starts[chosen],ends[chosen];owners=selected_rule[chosen]
            if bit==0:
                groups.append((a,b,owners,np.ones(len(a),dtype=bool)))
                continue
            inside=(flat & int(bit))!=0
            changes=np.flatnonzero(inside[1:]!=inside[:-1])+1
            lo=np.searchsorted(changes,a,side='right');hi=np.searchsorted(changes,b,side='left')
            count=hi-lo;repeat=count+1
            parent=np.repeat(np.arange(len(a)),repeat)
            within=np.arange(int(repeat.sum()))-np.repeat(np.cumsum(repeat)-repeat,repeat)
            stop=np.repeat(b,repeat).copy();middle=within<np.repeat(count,repeat)
            stop[middle]=changes[(np.repeat(lo,repeat)+within)[middle]]
            begin=np.r_[0,stop[:-1]];first=within==0;begin[first]=a[parent[first]]
            groups.append((begin,stop,owners[parent],inside[begin]))
        n=len(self.table);root_inside=np.zeros(n,dtype=np.uint64);root_outside=np.zeros(n,dtype=np.uint64)
        categories=np.zeros(6,dtype=np.uint64)
        if groups:
            a=np.concatenate([part[0] for part in groups]);b=np.concatenate([part[1] for part in groups])
            owner=np.concatenate([part[2] for part in groups]);inside=np.concatenate([part[3] for part in groups])
            labels=np.where(inside,self.table[owner,2],self.table[owner,3])
            lengths=(b-a).astype(np.uint64)
            np.add.at(root_inside,owner[inside],lengths[inside]);np.add.at(root_outside,owner[~inside],lengths[~inside])
            np.add.at(categories,labels-17,lengths)
            order=np.argsort(a,kind='stable');a,b,labels=a[order],b[order],labels[order]
            finish=np.empty(2*len(a)+1,dtype=np.int64);values=np.zeros(len(finish),dtype=np.uint8)
            finish[:-1:2]=a;finish[1:-1:2]=b;finish[-1]=mask.size;values[1:-1:2]=labels
            positive=finish>np.r_[0,finish[:-1]];finish,values=finish[positive],values[positive]
        else:
            finish=np.asarray([mask.size],dtype=np.int64);values=np.asarray([0],dtype=np.uint8)
        row_ends=np.arange(width,mask.size+1,width,dtype=np.int64)
        boundaries=np.union1d(finish,row_ends);codes=values[np.searchsorted(finish,boundaries,side='left')]
        keep=np.r_[(codes[:-1]!=codes[1:]) | (boundaries[:-1]%width==0),True]
        boundaries,codes=boundaries[keep],codes[keep]
        rows=(boundaries-1)//width
        pairs=np.column_stack(((boundaries-1)%width+1,codes)).astype('<u4')
        counts=np.bincount(rows,minlength=height)
        return pairs,counts,root_inside,root_outside,categories
