#!/usr/bin/env python3
"""Streaming adapters for the WorldAtlas row-offset + (end,code) RLE format.

The final prefill class raster is expected to encode physical land as 17..22,
already-assigned coastal/named-basin water as 1..6, and residual eligible water
as 0. Eligibility is then computed as physical code 1 intersect class code 0;
old ocean label rasters are never consulted.
"""
from __future__ import annotations
from pathlib import Path
import struct


class RunRasterU32LE:
    """A row-indexed RLE raster: row offsets, then uint32 (x_end, code) pairs."""
    def __init__(self, rows_path, runs_path, width, height, *, offset_bytes=4):
        if offset_bytes not in (4, 8):
            raise ValueError('offset_bytes must be 4 or 8')
        self.width, self.height, self.offset_bytes = width, height, offset_bytes
        self.rows_path, self.runs_path = Path(rows_path), Path(runs_path)
        row_fmt = '<I' if offset_bytes == 4 else '<Q'
        raw = self.rows_path.read_bytes()
        if len(raw) != (height + 1) * offset_bytes:
            raise ValueError(f'row-offset file length {len(raw)} != {(height+1)*offset_bytes}')
        self.offsets = tuple(v[0] for v in struct.iter_unpack(row_fmt, raw))
        if self.offsets[0] != 0 or any(a > b for a,b in zip(self.offsets,self.offsets[1:])):
            raise ValueError('row offsets must be monotonic and start at zero')
        self.run_count = self.runs_path.stat().st_size // 8
        if self.runs_path.stat().st_size % 8 or self.offsets[-1] != self.run_count:
            raise ValueError('row offsets do not exactly index the (end,code) run file')
        self._runs = self.runs_path.open('rb')

    def close(self):
        if self._runs:
            self._runs.close();self._runs=None

    def __enter__(self):return self
    def __exit__(self,*exc):self.close()

    def row(self, y):
        if not 0 <= y < self.height:
            raise IndexError(y)
        if self._runs is None:raise ValueError('RLE raster reader is closed')
        a,b = self.offsets[y:y+2]
        self._runs.seek(a * 8)
        raw = self._runs.read((b-a)*8)
        out=[];prev=0
        for end,code in struct.iter_unpack('<II',raw):
            if end <= prev or end > self.width:
                raise ValueError(f'invalid run end {end} in row {y} after {prev}')
            out.append((end,code));prev=end
        if prev != self.width:
            raise ValueError(f'row {y} ends at {prev}, expected width {self.width}')
        return out


def code_intervals(runs, wanted):
    """Return sorted half-open x intervals assigned to `wanted` from end/code runs."""
    out=[];start=0
    for end,code in runs:
        if code == wanted: out.append((start,end))
        start=end
    return out


def intersect_intervals(a,b):
    """Intersect two sorted disjoint half-open interval sequences."""
    out=[];i=j=0
    while i<len(a) and j<len(b):
        lo=max(a[i][0],b[j][0]);hi=min(a[i][1],b[j][1])
        if lo<hi:out.append((lo,hi))
        a_end,b_end=a[i][1],b[j][1]
        if a_end<=b_end:i+=1
        if b_end<=a_end:j+=1
    return out


def validate_prefill_row(physical_runs, class_runs, width):
    """Check complete rows contain only stable land/water prefill codes.

    Physical 17 (dry) must map to land codes 17..22. Physical 1 (water) must
    map to 0 (residual eligible) or 1..6 (already assigned continental water).
    In particular, a legacy ocean code 7..10 in the input is rejected.
    """
    if not physical_runs or not class_runs or physical_runs[-1][0]!=width or class_runs[-1][0]!=width:
        raise ValueError('physical and prefill-class rows must both cover the full width')
    i=j=0
    while i<len(physical_runs) and j<len(class_runs):
        pe,pc=physical_runs[i];ce,cc=class_runs[j];end=min(pe,ce)
        if pc==17:
            if cc not in (17,18,19,20,21,22):raise ValueError(f'physical land has invalid prefill code {cc}')
        elif pc==1:
            if cc not in (0,1,2,3,4,5,6):raise ValueError(f'physical water has invalid/inherited prefill code {cc}')
        else:raise ValueError(f'unknown physical code {pc}')
        if pe==end:i+=1
        if ce==end:j+=1
    if i!=len(physical_runs) or j!=len(class_runs):raise ValueError('physical and prefill-class rows do not end together')


def make_prefill_adapters(physical, final_class, width, height):
    """Build callbacks for fresh fill from physical + complete prefill-class RLEs.

    `final_class` must already include all finalized 1–6 water assignments and
    all 17–22 land cells; code 0 is reserved for residual physical water.
    An inconsistent zero on physical land is not treated as ocean eligibility.
    """
    if (physical.width,physical.height)!=(width,height) or (final_class.width,final_class.height)!=(width,height):
        raise ValueError('input raster dimensions differ from requested grid')
    def eligible_rows(y):
        pr=physical.row(y);cr=final_class.row(y);validate_prefill_row(pr,cr,width)
        phys=code_intervals(pr,1)
        residual=code_intervals(cr,0)
        return intersect_intervals(phys,residual)
    def classification_rows(y):
        runs=final_class.row(y)
        start=0;out=[]
        for end,code in runs:
            out.append((end,code));start=end
        return out
    return eligible_rows,classification_rows
