#!/usr/bin/env python3
"""Validate an unselected closure with strictly scoped endpoint-cell land contact.

Uses a pinned, separately reviewed exact all-touched grid implementation. This
is a physical-mask proof, not a route-selection, geographic, or ring proof.
"""
import argparse, hashlib, importlib.util, json, sys
from pathlib import Path
SUPPORT=Path(__file__).resolve().with_name('validate_water_closure_v2.py')
SUPPORT_SHA='1e796c7f9bc8843252398eed54093265581446c9f4cac10dcb3b4c424b6e1bd1'
if hashlib.sha256(SUPPORT.read_bytes()).hexdigest()!=SUPPORT_SHA: raise RuntimeError('checker support hash mismatch')
spec=importlib.util.spec_from_file_location('exact_water_support', SUPPORT); m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


def read_geom(path,expected):
    with open(path,'rb') as f:raw=f.read()
    digest,points=m.geom_and_points(raw)
    if digest!=expected:raise ValueError('geometry hash mismatch: '+str(path))
    return hashlib.sha256(raw).hexdigest(),points


def terminal_cell(pt):
    x,y=pt[:2]
    if x.denominator==1 or y.denominator==1:raise ValueError('terminal on grid boundary is ambiguous')
    return (x.numerator//x.denominator,y.numerator//y.denominator)


def verify_path(points,start,end,code,water,land):
    if points[0][:2]!=start[:2] or points[-1][:2]!=end[:2]:raise ValueError('closure does not bind exact oriented L2 endpoints')
    startcell,endcell=terminal_cell(start),terminal_cell(end)
    if startcell==endcell:raise ValueError('terminals share one cell')
    startcode,endcode=code(*startcell),code(*endcell)
    if startcode not in (water,land) or endcode not in (water,land):raise ValueError('invalid terminal code')
    visits=0; landseen=set()
    for i,(a,b) in enumerate(zip(points,points[1:])):
        segment_lands=set()
        for x,y in m.touched_segment(a[0],a[1],b[0],b[1]):
            visits+=1
            v=code(x,y)
            if v==water:continue
            if v!=land:raise ValueError('unrecognized physical code')
            allowed=(i==0 and (x,y)==startcell) or (i==len(points)-2 and (x,y)==endcell)
            if not allowed:raise ValueError(f'closure touches nonterminal land x={x}, y={y}, segment={i}')
            segment_lands.add((x,y));landseen.add((x,y))
        if len(segment_lands)>1:raise ValueError('segment touches more than one land cell')
    return {'cell_visits':visits,'start_terminal':{'cell_xy':list(startcell),'physical_code':startcode},'end_terminal':{'cell_xy':list(endcell),'physical_code':endcode},'terminal_land_cells_touched':[list(x) for x in sorted(landseen)]}


def exact_lonlat(pt):
    lon=m.WEST + pt[0]*m.STEP; lat=m.NORTH - pt[1]*m.STEP
    return {'longitude_numerator':lon.numerator,'longitude_denominator':lon.denominator,'latitude_numerator':lat.numerator,'latitude_denominator':lat.denominator}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--contract',required=True);p.add_argument('--contract-sha256',required=True);p.add_argument('--physical-dir',required=True)
    p.add_argument('--closure',required=True);p.add_argument('--closure-sha256',required=True)
    for side in ('start','end'):
        p.add_argument('--'+side+'-geometry',required=True);p.add_argument('--'+side+'-geometry-sha256',required=True);p.add_argument('--'+side+'-endpoint',choices=('start','end'),required=True)
    p.add_argument('--output',required=True);a=p.parse_args();ch,contract=m.load_contract(a.contract,a.contract_sha256)
    checker=m.sha(Path(__file__).resolve());assert m.sha(SUPPORT)==SUPPORT_SHA
    evidence=m.verify_producer_code(a.contract,contract);report=m.verify_physical_report(a.physical_dir,contract);mask=m.Mask(a.physical_dir)
    paths=[Path(a.closure),Path(a.start_geometry),Path(a.end_geometry)];expected=[a.closure_sha256,a.start_geometry_sha256,a.end_geometry_sha256]
    pairs=[read_geom(p,h) for p,h in zip(paths,expected)];closure,sg,eg=[p[1] for p in pairs]
    start=sg[0 if a.start_endpoint=='start' else -1];end=eg[0 if a.end_endpoint=='start' else -1]
    outcome=verify_path(closure,start,end,mask.code,m.WATER,m.LAND)
    mask.verify_again()
    if m.sha(Path(__file__).resolve())!=checker or m.sha(SUPPORT)!=SUPPORT_SHA or m.sha(Path(a.contract))!=ch or m.sha(report)!=contract['physical']['report_sha256'] or m.sha(evidence)!=contract['physical']['encoding_evidence_sha256'] or any(m.sha(p)!=pair[0] for p,pair in zip(paths,pairs)):raise ValueError('input changed during validation')
    proof={'schema':'physical-terminal-closure-proof-v1','status':'valid','checker_sha256':checker,'support_checker_sha256':SUPPORT_SHA,'contract_sha256':ch,'physical_rows_sha256':m.ROWS,'physical_runs_sha256':m.RUNS,'physical_report_sha256':contract['physical']['report_sha256'],'encoding_evidence_sha256':contract['physical']['encoding_evidence_sha256'],'geometry_sha256':a.closure_sha256,'start_geometry_sha256':a.start_geometry_sha256,'start_endpoint':a.start_endpoint,'start_endpoint_lonlat_exact':exact_lonlat(start),'end_geometry_sha256':a.end_geometry_sha256,'end_endpoint':a.end_endpoint,'end_endpoint_lonlat_exact':exact_lonlat(end),'terminal_policy':'Land may be touched only in the exact start cell on the first segment and the exact end cell on the last segment. Terminals on grid edges are rejected. Each segment may touch at most one land cell. All other closed touched cells must be physical water.','no_land_land_edge_touched':True,'verification':outcome,'warnings':['No route selection, land-cell classification, full-ring simplicity, historical equivalence, or source authority is established.']}
    with open(a.output,'x') as f:json.dump(proof,f,indent=2);f.write('\n')
    print(json.dumps(proof,indent=2))

if __name__=='__main__':
    try:main()
    except Exception as e:print('REJECTED: '+type(e).__name__+': '+str(e),file=sys.stderr);sys.exit(1)
