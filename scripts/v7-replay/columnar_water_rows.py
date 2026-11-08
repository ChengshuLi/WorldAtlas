"""Stream validated water rows as columns, retaining the original format fallback.

Canonical JSON fields use the installed PyArrow parser. Legacy aliases, coercions
and parser representations that do not preserve the Python-reader contract resume
through the original reader. Rule/member objects are materialized only if the
policy resolver needs its reference path.
"""
import codecs
import gzip
import heapq
import io
import itertools
import re

import numpy as np
import pyarrow as pa
import pyarrow.json as paj
import pyarrow.compute as pc

import compose_full_water_grid as reference


class OriginalReaderRequired(Exception):
    pass


class CompatibleJSONLines(io.RawIOBase):
    """Validate the original UTF-8/one-object-per-line contract before Arrow."""
    def __init__(self, source):
        super().__init__();self.source=source
        self.decoder=codecs.getincrementaldecoder('utf8')();self.pending='';self.tail=''

    def readable(self):return True

    def read(self, size=-1):
        if size == 0:return b''
        raw=self.source.read(size);text=self.decoder.decode(raw,final=not raw)
        joined=self.tail+text
        # Arrow may normalize escaped surrogate representations or a BOM;
        # retain Python's exact handling instead. CR-only line splitting also
        # belongs to the existing universal-newline reader.
        if '\ufeff' in joined or '\r' in text or re.search(r'\\u[dD][89a-fA-F][0-9a-fA-F]{2}',joined):
            raise OriginalReaderRequired()
        self.tail=joined[-8:]
        pieces=(self.pending+text).split('\n');self.pending=pieces.pop()
        if not raw:pieces.append(self.pending);self.pending=''
        for line in pieces:
            stripped=line.strip()
            if stripped and (not stripped.startswith('{') or not stripped.endswith('}')
                             or re.search(r'}[ \t]*{',line)):
                raise OriginalReaderRequired()
        return raw


class ColumnSpans:
    """Numeric coordinates plus deferred, exact source metadata for one row."""
    def __init__(self, starts, stops, codes, *, arrow=None, legacy=None, children=(), order=None):
        self.columns=(starts,stops,codes)
        self.arrow,self.legacy,self.children,self.order=arrow,legacy,children,order

    def __len__(self):return len(self.columns[0])

    @classmethod
    def from_arrow(cls, spans):
        columns=[spans.field(key).to_numpy(zero_copy_only=True) for key in ('start','end','code')]
        return cls(columns[0].astype(np.uint32),columns[1].astype(np.uint32),columns[2],arrow=spans)

    @classmethod
    def from_legacy(cls, records):
        arrays=[np.fromiter((record[i] for record in records),dtype=dtype,count=len(records))
                for i,dtype in ((1,np.uint32),(2,np.uint32),(3,np.int64))]
        return cls(*arrays,legacy=records)

    @classmethod
    def combine(cls, children):
        if len(children)==1:return children[0]
        columns=[np.concatenate([child.columns[i] for child in children]) for i in range(3)]
        order=np.lexsort((columns[1],columns[0]))
        return cls(*(column[order] for column in columns),children=children,order=order)

    def reference_records(self, row):
        if self.legacy is not None:return self.legacy
        if self.arrow is not None:
            return [(row,span['start'],span['end'],span['code'],span['rule_id'],span['member_id'],None,None)
                    for span in self.arrow.to_pylist()]
        records=[record for child in self.children for record in child.reference_records(row)]
        return [records[int(i)] for i in self.order]


def original_remainder(tile, y0, y1, sparse, emitted):
    spans=itertools.islice(reference.tile_spans(tile,y0,y1,'water',sparse),emitted,None)
    for row,group in itertools.groupby(spans,key=lambda record:record[0]):
        yield row,ColumnSpans.from_legacy(list(group))


def tile_rows(tile, y0, y1, sparse, *, block_size=1<<20):
    fields=pa.struct([('start',pa.int64()),('end',pa.int64()),('code',pa.int64()),
                      ('rule_id',pa.string()),('member_id',pa.string())])
    schema=pa.schema([('row',pa.int64()),('spans',pa.list_(fields))])
    first,last=tile['_rows'];expected=first;last_row=first-1;last_end=-1;emitted=0
    try:
        opener=gzip.open if tile['_path'].suffix=='.gz' else open
        with opener(tile['_path'],'rb') as source,CompatibleJSONLines(source) as validated:
            with paj.open_json(validated,read_options=paj.ReadOptions(block_size=block_size),
                    parse_options=paj.ParseOptions(explicit_schema=schema,unexpected_field_behavior='ignore')) as reader:
                for batch in reader:
                    batch.validate(full=True)
                    rows,lists=batch.column(0),batch.column(1)
                    if rows.null_count or lists.null_count:raise OriginalReaderRequired()
                    for i in range(len(rows)):
                        row=int(rows[i].as_py());values=lists[i].values
                        if ((sparse and row<last_row)
                            or (not sparse and (row<last_row or (row!=last_row and row!=expected)))
                            or not first<=row<last):raise OriginalReaderRequired()
                        if row!=last_row:last_row,last_end,expected=row,-1,row+1
                        if not len(values):continue
                        if values.null_count or any(values.field(name).null_count for name in ('start','end','code','rule_id','member_id')):
                            raise OriginalReaderRequired()
                        starts,stops,codes=[values.field(name).to_numpy(zero_copy_only=True) for name in ('start','end','code')]
                        if (np.any(starts<0) or np.any(starts>=stops) or np.any(stops>reference.W)
                            or starts[0]<last_end or np.any(starts[1:]<stops[:-1])):raise OriginalReaderRequired()
                        if tile['_cols'] is not None and (np.any(starts<tile['_cols'][0]) or np.any(stops>tile['_cols'][1])):
                            raise OriginalReaderRequired()
                        last_end=int(stops[-1])
                        if y0<=row<y1:
                            # Lengths validate required identities without making
                            # a Python string for every source span.
                            if (np.any(codes<1) or np.any(codes>10)
                                or pc.any(pc.equal(values.field('rule_id'),'')).as_py()
                                or pc.any(pc.equal(values.field('member_id'),'')).as_py()):
                                raise OriginalReaderRequired()
                            result=ColumnSpans.from_arrow(values)
                            emitted+=len(result)
                            yield row,result
        if not sparse and (expected!=last or last_row!=last-1):raise OriginalReaderRequired()
    except (OriginalReaderRequired,pa.ArrowInvalid,pa.ArrowNotImplementedError,UnicodeError):
        yield from original_remainder(tile,y0,y1,sparse,emitted)


def layer_rows(manifest, y0, y1):
    streams=[tile_rows(tile,y0,y1,manifest.get('_sparse_rows_allowed',False)) for tile in manifest['_tiles']]
    merged=heapq.merge(*streams,key=lambda item:item[0])
    for row,group in itertools.groupby(merged,key=lambda item:item[0]):
        yield row,ColumnSpans.combine([item[1] for item in group])


class RowCursor:
    def __init__(self, manifest, y0, y1):
        self.iterator=iter(layer_rows(manifest,y0,y1));self.next=next(self.iterator,None)

    def take(self,row):
        if self.next is not None and self.next[0]<row:
            raise ValueError(f'layer row skipped: saw {self.next[0]}, expected {row}')
        if self.next is not None and self.next[0]==row:
            records=self.next[1];self.next=next(self.iterator,None);return records
        return []
