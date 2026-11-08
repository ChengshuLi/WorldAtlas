#!/usr/bin/env python3
"""Run fresh four-ocean fill from finalized physical + prefill RLE layers.

This writes only to the explicitly selected staging output directory. It refuses
legacy ocean values, incomplete rows, missing seed cells, seed collisions, and
out-of-grid source cuts. It does not publish or mutate frozen artifacts.
"""
from __future__ import annotations
import argparse,hashlib,json,sys
from pathlib import Path
from partition_core import CutEdges,floodfill_run_graph,export_jsonl_tiles
from exclusive_outputs import create_binary_exclusive, create_directory_exclusive, create_gzip_text_exclusive, create_text_exclusive, create_run_directory, write_json_exclusive
from rle_inputs import RunRasterU32LE,make_prefill_adapters

W,H=131072,54614
SEEDS={7:(54613,32768),8:(14563,32768),9:(94663,43690),10:(65536,1820)}
SEED_META={7:{'nominal_longitude_deg':-30.0,'nominal_latitude_deg':0.0,'label':'Atlantic'},
           8:{'nominal_longitude_deg':-140.0,'nominal_latitude_deg':0.0,'label':'Pacific'},
           9:{'nominal_longitude_deg':80.0,'nominal_latitude_deg':-30.0,'label':'Indian'},
           10:{'nominal_longitude_deg':0.0,'nominal_latitude_deg':85.0,'label':'Arctic'}}

def sha256(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(8*1024*1024),b''):h.update(block)
    return h.hexdigest()

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--physical-rows',required=True);p.add_argument('--physical-runs',required=True)
    p.add_argument('--class-rows',required=True);p.add_argument('--class-runs',required=True)
    p.add_argument('--class-offset-bytes',type=int,choices=(4,8),default=4)
    p.add_argument('--cuts',required=True,help='source barrier edge binary (u32 triples)')
    p.add_argument('--output-dir',required=True)
    p.add_argument('--tile-height',type=int,default=256)
    p.add_argument('--mask-only-prefill',action='store_true',
      help='prefill code 1 is only a binary ocean-exclusion mask; omit continent-adjacency labels from unseeded-component QA')
    args=p.parse_args()
    out=Path(args.output_dir)
    if out.exists():raise FileExistsError(f'output directory already exists; use a fresh exclusive run directory: {out}')
    # partition_core creates this directory exclusively before its first output.
    physical=RunRasterU32LE(args.physical_rows,args.physical_runs,W,H,offset_bytes=4)
    final_class=RunRasterU32LE(args.class_rows,args.class_runs,W,H,offset_bytes=args.class_offset_bytes)
    cuts=CutEdges.read_u32le(args.cuts)
    # Reject graph edges outside valid center-neighbor ranges before processing.
    if any(not(0<=y<H and all(0<=x<W-1 for x in xs)) for y,xs in cuts.horizontal.items()):raise ValueError('horizontal source cut outside grid')
    if any(not(0<=y<H-1 and all(0<=x<W for x in xs)) for y,xs in cuts.vertical.items()):raise ValueError('vertical source cut outside grid')
    if any(not(0<=y<H) for y in cuts.wrap):raise ValueError('wrap source cut outside grid')
    eligible_rows,classification_rows=make_prefill_adapters(physical,final_class,W,H)
    inputs={'physical_rows':{'path':str(args.physical_rows),'sha256':sha256(args.physical_rows)},
      'physical_runs':{'path':str(args.physical_runs),'sha256':sha256(args.physical_runs)},
      'final_prefill_class_rows':{'path':str(args.class_rows),'sha256':sha256(args.class_rows)},
      'final_prefill_class_runs':{'path':str(args.class_runs),'sha256':sha256(args.class_runs)},
      'class_row_offset_bytes':args.class_offset_bytes,
      'source_cut_edges':{'path':str(args.cuts),'sha256':sha256(args.cuts)},
      'legacy_ocean_label_inheritance':False,
      'mask_only_prefill':bool(args.mask_only_prefill)}
    if args.mask_only_prefill:
        inputs['prefill_code_1_semantics']='binary excluded-water mask placeholder; not a continent assignment'
        unassigned_policy=('mask-only provisional run: omit continent adjacency labels because prefill code 1 is a binary placeholder; '
          'report source-barrier contact separately and defer closed-pocket continent decisions until real 1–6 classes are available')
        classification_rows=None
    else:
        unassigned_policy='report source-cut contact separately; only components without source-cut contact may be reviewed for approved enclosed-water nearest-shore assignment'
    manifest=floodfill_run_graph(eligible_rows,W,H,cuts,SEEDS,out,manifest_inputs=inputs,
      unassigned_policy=unassigned_policy,
      classification_rows=classification_rows,seed_metadata=SEED_META)
    tiles=export_jsonl_tiles(out,W,H,tile_height=args.tile_height,manifest_inputs=inputs)
    print(json.dumps({'status':'staged-only','output_dir':str(out),'manifest':manifest,'tile_manifest':tiles},indent=2))

if __name__=='__main__':main()
