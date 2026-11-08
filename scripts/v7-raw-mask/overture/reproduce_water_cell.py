#!/usr/bin/env python3
"""Extract and replay pinned source features near a differing water-mask cell."""
import argparse
from contextlib import redirect_stdout
import json
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
from osgeo import gdal

import rasterize_water_shard as build


def run(source, expected, config, row, column, output):
    source,config,output=map(lambda p:Path(p).resolve(),(source,config,output))
    if build.sha256(source)!=expected:raise ValueError('raw source hash mismatch')
    data=config.read_bytes();cfg=json.loads(data);grid=cfg['grid']
    if not 0<=row<grid['height'] or not 0<=column<grid['width']:raise ValueError('cell outside grid')
    if source.is_relative_to(output) or config.is_relative_to(output):raise ValueError('output contains original input')
    x=grid['west']+(column+.5)*grid['step'];y=grid['north']-(row+.5)*grid['step']
    # One pixel of padding includes center-tie candidates even when a source
    # envelope lies a floating-point rounding error beyond the cell center.
    step=grid['step'];pf=pq.ParquetFile(source,pre_buffer=False);tables=[];selected=[];first=0
    for group in range(pf.metadata.num_row_groups):
        boxes=pf.read_row_group(group,columns=['bbox'],use_threads=False).column('bbox').combine_chunks()
        mask=pc.and_(pc.and_(pc.less_equal(pc.struct_field(boxes,'xmin'),x+step),
                            pc.greater_equal(pc.struct_field(boxes,'xmax'),x-step)),
                     pc.and_(pc.less_equal(pc.struct_field(boxes,'ymin'),y+step),
                             pc.greater_equal(pc.struct_field(boxes,'ymax'),y-step)))
        indices=np.flatnonzero(pc.fill_null(mask,False).to_numpy(zero_copy_only=False))
        if len(indices):
            table=pf.read_row_group(group,columns=['id','subtype','geometry'],use_threads=False).take(pa.array(indices))
            tables.append(table)
            selected.extend({'source_row':first+int(index),'id':ident} for index,ident in zip(indices,table.column('id').to_pylist()))
        first+=pf.metadata.row_group(group).num_rows
    if not tables:raise ValueError('no nearby source features')
    output.mkdir();inputs=output/'inputs';inputs.mkdir()
    table=pa.concat_tables(tables).replace_schema_metadata(pf.schema_arrow.metadata)
    extracted=inputs/'cell-features.parquet';pq.write_table(table,extracted)
    report={'schema':'worldatlas-water-cell-reproduction-v1','source_sha256':expected,
        'configuration_sha256':build.sha256(config),'row':row,'column':column,
        'longitude':x,'latitude':y,'features':selected,'extracted_sha256':build.sha256(extracted),'results':{}}
    for name,engine,method in [('python','python','hybrid'),('gdal-hybrid','gdal','hybrid'),('gdal-tiled','gdal','tiled')]:
        variant=inputs/(name+'.json');variant.write_text(json.dumps({**cfg,'batch_method':method},indent=2)+'\n')
        destination=output/name
        with (output/(name+'.log')).open('x') as log,redirect_stdout(log):
            build.run(extracted,report['extracted_sha256'],destination,variant,engine=engine)
        raster=gdal.Open(str(destination/'water.tif'))
        report['results'][name]={'cell_value':int(raster.ReadAsArray(column,row,1,1)[0,0]),
            'report_sha256':build.sha256(destination/'report.json'),'mask_sha256':build.sha256(destination/'water.tif')}
        raster=None
    if build.sha256(source)!=expected or config.read_bytes()!=data:raise ValueError('original input changed')
    (output/'reproduction.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('source','sha256','config','row','column','output'):p.add_argument(name,type=int if name in ('row','column') else str)
    a=p.parse_args();print(json.dumps(run(a.source,a.sha256,a.config,a.row,a.column,a.output),indent=2))
