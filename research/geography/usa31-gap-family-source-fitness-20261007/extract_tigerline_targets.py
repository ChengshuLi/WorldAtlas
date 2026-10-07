#!/usr/bin/env python3
"""Extract only three target county records from externally restored TIGER/Line ZIPs.

The full archives stay outside the repository. Each archive must match its fixed
expected byte count; the receipt records whole-archive, member-file and exact
selected shapefile/DBF record hashes.
"""
from pathlib import Path
from zipfile import ZipFile
import hashlib, json, struct, sys, tempfile, shutil

OUT=Path(__file__).parent/'sources'
TARGETS={'36059','36103','36119'}
EXPECTED={'2018':79219478,'2025':83989800}

def sha(b): return hashlib.sha256(b).hexdigest()
def parse_dbf(raw):
    count=struct.unpack_from('<I',raw,4)[0]; header=struct.unpack_from('<H',raw,8)[0]; record=struct.unpack_from('<H',raw,10)[0]
    fields=[];pos=32
    while raw[pos]!=0x0d:
        d=raw[pos:pos+32];name=d[:11].split(b'\0',1)[0].decode('ascii');typ=chr(d[11]);length=d[16];dec=d[17]
        fields.append((name,typ,length,dec));pos+=32
    assert header==pos+1 and len(raw)>=header+count*record
    rows=[]
    for idx in range(count):
        start=header+idx*record; rec=raw[start:start+record]
        if rec[0]==0x2a: rows.append((idx,rec,None));continue
        at=1;value={}
        for name,typ,length,dec in fields:
            data=rec[at:at+length];at+=length
            try: txt=data.decode('utf-8').strip()
            except UnicodeDecodeError: txt=data.decode('cp1252').strip()
            if not txt: v=None
            elif typ in ('N','F'):
                try: v=int(txt) if dec==0 else float(txt)
                except ValueError: v=txt
            elif typ=='L': v=txt.upper() in ('Y','T')
            else:v=txt
            value[name]=v
        rows.append((idx,rec,value))
    return fields,rows,header,record

def parse_shp(raw, wanted):
    assert len(raw)>=100 and struct.unpack_from('<I',raw,32)[0]==5
    shx_path=[]
    # Keep complete exact target record bodies by matching DBF row ordinal and SHP index.
    records={};offset=100
    ordinal=0
    while offset<len(raw):
        number,words=struct.unpack_from('>II',raw,offset);n=words*2
        content=raw[offset+8:offset+8+n]
        if len(content)!=n: raise ValueError('truncated shapefile record')
        stype=struct.unpack_from('<I',content,0)[0]
        if stype!=5: raise ValueError(f'unsupported geometry type {stype}')
        xmin,ymin,xmax,ymax=struct.unpack_from('<4d',content,4)
        nparts,npoints=struct.unpack_from('<2I',content,36)
        pos=44;parts=list(struct.unpack_from('<%dI'%nparts,content,pos)) if nparts else [];pos+=4*nparts
        pts=list(struct.iter_unpack('<2d',content[pos:pos+npoints*16]))
        if len(pts)!=npoints: raise ValueError('invalid point count')
        starts=parts+[npoints];rings=[]
        for j in range(len(parts)):
            ring=[[float(x),float(y)] for x,y in pts[starts[j]:starts[j+1]]]
            if ring and ring[0]!=ring[-1]:ring.append(ring[0])
            rings.append(ring)
        records[ordinal]={'record_number':number,'shape_record_sha256':sha(raw[offset:offset+8+n]),'shape_content_sha256':sha(content),'bbox':[xmin,ymin,xmax,ymax],'rings':rings}
        ordinal+=1;offset+=8+n
    if ordinal!=len(wanted): raise ValueError('shapefile/DBF record count mismatch')
    return records

def signed_area(ring):
    return sum(ring[i][0]*ring[i+1][1]-ring[i+1][0]*ring[i][1] for i in range(len(ring)-1))/2

def contains(ring,pt):
    x,y=pt;inside=False
    for (x1,y1),(x2,y2) in zip(ring,ring[1:]):
        if (y1>y)!=(y2>y) and x<(x2-x1)*(y-y1)/(y2-y1)+x1:inside=not inside
    return inside

def polygon_coordinates(rings):
    shells=[r for r in rings if signed_area(r)<0];holes=[r for r in rings if signed_area(r)>0]
    if not shells and rings:shells=[rings[0]];holes=rings[1:]
    polys=[[shell] for shell in shells]
    shell_area=[abs(signed_area(s)) for s in shells]
    for hole in holes:
        if not hole:continue
        candidates=[i for i,s in enumerate(shells) if contains(s,hole[0])]
        if candidates:polys[min(candidates,key=lambda i:shell_area[i])].append(hole)
    return polys[0] if len(polys)==1 else polys

def archive_info(path,year):
    raw_hash=hashlib.sha256();size=0
    with path.open('rb') as f:
        while b:=f.read(1024*1024):size+=len(b);raw_hash.update(b)
    if size!=EXPECTED[year]:raise ValueError(f'{year} archive size {size} differs from expected {EXPECTED[year]}')
    return size,raw_hash.hexdigest()

def extract(year,path):
    path=Path(path);size,archive_sha=archive_info(path,year)
    prefix=f'tl_{year}_us_county'
    with tempfile.TemporaryDirectory(prefix=f'usa31-tiger{year}-') as td:
        d=Path(td)
        with ZipFile(path) as z:
            names={Path(n).name:n for n in z.namelist()}
            dbf_name,shp_name,prj_name,cpg_name=[names[prefix+ext] for ext in ('.dbf','.shp','.prj','.cpg')]
            dbf=z.read(dbf_name); shp=z.read(shp_name);prj=z.read(prj_name);cpg=z.read(cpg_name)
        fields,rows,header_len,record_len=parse_dbf(dbf)
        geoid_field='GEOID' if any(f[0]=='GEOID' for f in fields) else 'GEOID'
        selected={str(row[geoid_field]):(idx,raw,row) for idx,raw,row in rows if row and str(row.get(geoid_field)) in TARGETS}
        if set(selected)!=TARGETS:raise ValueError(f'{year} target GEOIDs missing: {TARGETS-set(selected)}')
        records=parse_shp(shp,rows)
        features=[];per_feature=[]
        for geoid in sorted(TARGETS):
            idx,dbf_record,props=selected[geoid]; rec=records[idx]
            if props.get('STATEFP')!='36':raise ValueError('unexpected state GEOID')
            coordinates=polygon_coordinates(rec['rings'])
            geometry={'type':'Polygon','coordinates':coordinates} if len(coordinates) and isinstance(coordinates[0][0][0],float) else {'type':'MultiPolygon','coordinates':coordinates}
            feature={'type':'Feature','id':geoid,'properties':props,'geometry':geometry}
            features.append(feature)
            per_feature.append({'geoid':geoid,'record_ordinal':idx,'dbf_record_sha256':sha(dbf_record),'shp_record_sha256':rec['shape_record_sha256'],'shp_content_sha256':rec['shape_content_sha256'],'canonical_feature_sha256':sha(json.dumps(feature,sort_keys=True,separators=(',',':')).encode())})
        source_text=prj.decode('ascii').strip(); native='EPSG:4269' if 'GCS_North_American_1983' in source_text else 'unknown'
        if native!='EPSG:4269':raise ValueError(f'Unexpected source CRS: {source_text}')
        collection={'type':'FeatureCollection','name':prefix,'source_crs':native,'features':features}
        body=(json.dumps(collection,separators=(',',':'),ensure_ascii=False)+'\n').encode()
        out=OUT/f'census-tigerline-{year}-target-counties.geojson';out.write_bytes(body)
        receipt={'year':int(year),'source_url':f'https://www2.census.gov/geo/tiger/TIGER{year}/COUNTY/{prefix}.zip','archive_bytes':size,'archive_sha256':archive_sha,'archive_location':'Temporary storage outside repository; local filesystem path intentionally omitted.','shapefile_member':{'name':shp_name,'bytes':len(shp),'sha256':sha(shp)},'dbf_member':{'name':dbf_name,'bytes':len(dbf),'sha256':sha(dbf)},'prj_member':{'name':prj_name,'bytes':len(prj),'sha256':sha(prj),'text':source_text,'epsg':native},'cpg_member':{'name':cpg_name,'bytes':len(cpg),'sha256':sha(cpg),'text':cpg.decode('ascii','replace')},'dbf_fields':[{'name':n,'type':t,'length':l,'decimals':d} for n,t,l,d in fields],'features':per_feature,'output_path':str(out.relative_to(OUT.parent)),'output_bytes':len(body),'output_sha256':sha(body),'geometry_coordinates_retained_in_native_crs':True,'license_note':'Census Bureau source; no separate archive license text was included in the ZIP. Treat as source evidence; preserve source terms separately.'}
        (OUT/f'census-tigerline-{year}-extraction.json').write_text(json.dumps(receipt,indent=2)+'\n')
        print(json.dumps({'year':year,'archive_bytes':size,'archive_sha256':archive_sha,'features':len(features),'geojson_bytes':len(body),'geojson_sha256':sha(body)}))

if __name__=='__main__':
    if len(sys.argv)!=3:raise SystemExit('Usage: extract_tigerline_targets.py YEAR /path/to/tl_YEAR_us_county.zip')
    extract(sys.argv[1],sys.argv[2])
