#!/usr/bin/env python3
"""Match modeled outlet points to archived HydroBASINS polygons and terminal IDs."""
import argparse,hashlib,json,os,shutil,tempfile,zipfile
import shapefile
from shapely.geometry import Point,shape

def run(zip_path,zip_sha,points):
    h=hashlib.sha256()
    with open(zip_path,'rb') as f:
        for chunk in iter(lambda:f.read(1048576),b''):h.update(chunk)
    if h.hexdigest()!=zip_sha:raise ValueError('archive checksum mismatch')
    with tempfile.TemporaryDirectory() as tmp,zipfile.ZipFile(zip_path) as z:
        names=[i for i in z.infolist() if i.filename.lower().endswith(('.shp','.shx','.dbf'))]
        if len(names)!=3 or sum(x.file_size for x in names)>1_000_000_000:raise ValueError('unexpected archive contents')
        bases={os.path.splitext(os.path.basename(i.filename))[0] for i in names}
        if len(bases)!=1 or len({os.path.splitext(i.filename)[1].lower() for i in names})!=3:raise ValueError('shapefile parts mismatch')
        for i in names:
            with z.open(i) as src,open(os.path.join(tmp,os.path.basename(i.filename)),'wb') as dst:shutil.copyfileobj(src,dst)
        r=shapefile.Reader(os.path.join(tmp,next(iter(bases))+'.shp')); result=[];roots=set()
        for pt in points:
            hits=[]
            for sr in r.iterShapeRecords(bbox=(pt[0]-.001,pt[1]-.001,pt[0]+.001,pt[1]+.001)):
                if shape(sr.shape.__geo_interface__).covers(Point(*pt)):
                    rec=sr.record.as_dict();hits.append({'hybas_id':rec['HYBAS_ID'],'main_bas':rec['MAIN_BAS'],'next_sink':rec['NEXT_SINK']});roots.add(rec['MAIN_BAS'])
            result.append({'point':pt,'hits':hits})
        terminals=[]
        for sr in r.iterShapeRecords():
            rec=sr.record.as_dict()
            if rec['HYBAS_ID'] in roots:terminals.append({'hybas_id':rec['HYBAS_ID'],'next_down':rec['NEXT_DOWN'],'bbox':list(sr.shape.bbox)})
        return {'points':result,'terminal_records':terminals,'archive_sha256':zip_sha}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--archive',required=True);p.add_argument('--archive-sha256',required=True);p.add_argument('--flow',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();flow=json.load(open(a.flow)); points=sorted({tuple(pt) for pair in flow['outlet_pairs_lonlat'] for pt in pair})
    result=run(a.archive,a.archive_sha256,points)
    with open(a.output,'x') as f:json.dump(result,f)
    print(json.dumps(result))
