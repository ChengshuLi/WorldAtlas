"""Discover named physical-island anchors from an authenticated country ZIP.

A GeoNames ISL record identifies an island, not a group or satellite roster.
The caller's explicit physical-size rule determines operational main anchors;
that size classification is not attributed to GeoNames.
"""
from collections import defaultdict
import bisect
import math
from pathlib import Path
import re
import zipfile
from component_scan import _pin, _offsets, _runs, sha256_file
from regional_rule import _require

ID=re.compile(r'^[1-9][0-9]{0,15}$')


def discover(source_spec, row_spec, run_spec, grid, components, proposals, *, max_satellite_cells):
    """Resolve all country ISL witnesses to current roots, then choose anchors.

    source_spec names the exact source/version/country and its content pin.
    The caller authenticates the catalog and selects an operational size limit;
    only completely counted roots present in components and with an already
    established target are eligible. Every source witness is checked against the
    same component stream; a point in water or an unknown root is not guessed.
    """
    _require(isinstance(source_spec,dict) and set(source_spec)=={'path','sha256','source_id','source_version','country'} and
             all(isinstance(source_spec[k],str) and source_spec[k] for k in source_spec), 'invalid anchor source')
    country=source_spec['country']
    _require(re.fullmatch(r'[A-Z]{2}',country) is not None and type(max_satellite_cells) is int and max_satellite_cells>0, 'invalid anchor policy')
    source=_pin({'path':source_spec['path'],'sha256':source_spec['sha256']});rp,sp=_pin(row_spec),_pin(run_spec)
    w,h,west,north,step=(grid[k] for k in ('width','height','west','north','step'))
    offsets=_offsets(rp,sp,h); rows=defaultdict(list);seen=set();records=0
    try:
        with zipfile.ZipFile(source) as archive:
            entries=[e for e in archive.infolist() if e.filename==country+'.txt']
            _require(len(entries)==1 and not entries[0].is_dir() and entries[0].file_size<=64*1024*1024, 'invalid country archive')
            with archive.open(entries[0]) as f:
                for raw in f:
                    _require(len(raw)<=1024*1024, 'oversized source record')
                    fields=raw.decode('utf-8','strict').rstrip('\r\n').split('\t')
                    _require(len(fields)==19, 'invalid country record')
                    if fields[6:9]!=['T','ISL',country]:
                        continue
                    feature,name=fields[0],fields[1]
                    _require(ID.fullmatch(feature) and feature not in seen and name and len(name)<=256,'invalid island identity')
                    seen.add(feature);records+=1
                    try: lat=float(fields[4]);lon=float(fields[5])
                    except ValueError: raise ValueError('invalid island point') from None
                    _require(math.isfinite(lat) and math.isfinite(lon) and -90<=lat<=90 and -180<=lon<180, 'invalid island point')
                    x=math.floor((lon-west)/step);y=math.floor((north-lat)/step)
                    if 0<=x<w and 0<=y<h:
                        rows[y].append((x,feature,name))
    except (UnicodeError,zipfile.BadZipFile,RuntimeError) as exc:
        raise ValueError('invalid country archive') from exc
    matched=defaultdict(list);water=0;outside_roots=0
    with sp.open('rb') as f:
        for y,points in rows.items():
            runs=list(_runs(f,offsets[y],offsets[y+1],w));starts=[a for a,_,_ in runs]
            for x,feature,name in points:
                i=bisect.bisect_right(starts,x)-1
                if i<0 or x>=runs[i][1]:
                    water+=1;continue
                root=runs[i][2]
                if root not in components:
                    outside_roots+=1;continue
                matched[root].append((feature,name))
    anchors={}
    for root,features in matched.items():
        proposal=proposals.get(root)
        if components[root]['total']<=max_satellite_cells or not proposal:
            continue
        ordered=sorted(features,key=lambda p:int(p[0]));feature,name=ordered[0]
        anchors[root]={'code':proposal['code'],'source_id':source_spec['source_id'],
                       'source_version':source_spec['source_version'],'source_sha256':source_spec['sha256'],
                       'source_feature_id':feature,'source_feature_ids':[i for i,_ in ordered],
                       'main_island_evidence':f'GeoNames ISL witness {name}; physical component has {components[root]["total"]} cells, above operational threshold {max_satellite_cells}'}
    _require(sha256_file(source)==source_spec['sha256'] and sha256_file(rp)==row_spec['sha256'] and
             sha256_file(sp)==run_spec['sha256'], 'anchor inputs changed')
    return {'anchors':anchors,'statistics':{'island_records':records,'source_points_on_water':water,
             'source_points_outside_buffer_roots':outside_roots,'matched_roots':len(matched),'eligible_anchors':len(anchors)}}
