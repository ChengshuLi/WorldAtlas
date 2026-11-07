"""Parse an explicitly named, closed DMS rectangle in a Federal Register extract.

The caller must hash/authenticate the provider-original document and must supply
section headings from its own reviewed structured decision. This parser never
retrieves a file, makes a selection, or stores geographic data.
"""
import re
from decimal import Decimal

_ROW = re.compile(r"(?m)^\s*([1-4])\s+\.{2,}\s*(\d{1,3})\s*°\s*(\d{1,2})\s*[′']\s*(\d{1,2})\s*[″\"]\s+(\d{1,2})\s*°\s*(\d{1,2})\s*[′']\s*(\d{1,2})\s*[″\"]\s*$")

def rectangle_from_text(text, heading, next_heading):
    if not all(isinstance(x,str) and x for x in (text,heading,next_heading)):
        raise ValueError('text and headings required')
    if len(text)>10_000_000 or text.count(heading)!=1:
        raise ValueError('ambiguous section heading')
    start=text.index(heading)+len(heading)
    if text[start:].count(next_heading)!=1:
        raise ValueError('ambiguous next heading')
    section=text[start:text.index(next_heading,start)]
    if len(re.findall(r'W\.\s*long\.\s*N\.\s*lat\.', section))!=1:
        raise ValueError('expected unambiguous west-longitude/north-latitude heading')
    rows=_ROW.findall(section)
    if len(rows)!=5 or [r[0] for r in rows]!=['1','2','3','4','1']:
        raise ValueError('expected one closed five-row coordinate list')
    points=[]
    for _,ld,lm,ls,ad,am,ass in rows:
        ld,lm,ls,ad,am,ass=map(int,(ld,lm,ls,ad,am,ass))
        if not (0<=ld<=180 and 0<=ad<=90 and 0<=lm<60 and 0<=ls<60 and 0<=am<60 and 0<=ass<60):
            raise ValueError('coordinate outside bounds')
        lon=-(Decimal(ld)+Decimal(lm)/60+Decimal(ls)/3600)
        lat=Decimal(ad)+Decimal(am)/60+Decimal(ass)/3600
        if lon < -180 or lat>90:raise ValueError('coordinate outside bounds')
        points.append((lon,lat))
    if points[0]!=points[4] or len(set(points[:4]))!=4:
        raise ValueError('rectangle not closed')
    xs={x for x,y in points[:4]}; ys={y for x,y in points[:4]}
    if len(xs)!=2 or len(ys)!=2 or set(points[:4])!={(x,y) for x in xs for y in ys}:
        raise ValueError('coordinates do not describe a rectangle')
    for a,b in zip(points,points[1:]):
        if (a[0]==b[0])==(a[1]==b[1]):raise ValueError('invalid rectangle edge order')
    return {'type':'Polygon','coordinates':[[[float(x),float(y)] for x,y in points]]}

def extract_pdf_rectangle(path, expected_sha256, expected_size, expected_geometry_sha256, page, crop, heading, next_heading):
    """Hash-check a bounded PDF, extract its reviewed page/column and verify geometry."""
    import hashlib,json,subprocess,tempfile,os,fcntl,sys
    from pathlib import Path
    if not isinstance(expected_sha256,str) or re.fullmatch(r'[0-9a-f]{64}',expected_sha256) is None or not isinstance(expected_geometry_sha256,str) or re.fullmatch(r'[0-9a-f]{64}',expected_geometry_sha256) is None:
        raise ValueError('invalid pinned hashes')
    if type(expected_size) is not int or not 1 <= expected_size <= 32*1024*1024 or type(page) is not int or not 1 <= page <= 10000:
        raise ValueError('invalid source limits')
    if not isinstance(crop,dict) or set(crop)!={'x','y','width','height'} or any(type(v) is not int or not 0 <= v <= 10000 for v in crop.values()) or not crop['width'] or not crop['height']:
        raise ValueError('invalid crop')
    path=Path(path)
    def read_verified():
        if path.stat().st_size!=expected_size:raise ValueError('source PDF mismatch')
        with path.open('rb') as source:
            data=source.read(expected_size+1)
        if len(data)!=expected_size or not data.startswith(b'%PDF-') or hashlib.sha256(data).hexdigest()!=expected_sha256:
            raise ValueError('source PDF mismatch')
        return data
    data=read_verified()
    args=['/usr/bin/prlimit','--fsize=10000000:10000000','--','/usr/bin/pdftotext','-f',str(page),'-l',str(page),'-r','72','-x',str(crop['x']),'-y',str(crop['y']),'-W',str(crop['width']),'-H',str(crop['height']),'-layout','-','-']
    if sys.platform != 'linux':raise ValueError('sealed source requires Linux')
    # Linux fcntl ABI constants; some Python builds omit these names.
    add_seals=getattr(fcntl,'F_ADD_SEALS',1033);get_seals=getattr(fcntl,'F_GET_SEALS',1034)
    seals=1|2|4|8
    fd=os.memfd_create('pinned-pdf',os.MFD_ALLOW_SEALING)
    with os.fdopen(fd,'w+b') as source, tempfile.TemporaryFile() as output:
        source.write(data);source.flush()
        fcntl.fcntl(source.fileno(),add_seals,seals)
        if fcntl.fcntl(source.fileno(),get_seals)&seals != seals:raise ValueError('source could not be sealed')
        source.seek(0)
        subprocess.run(args,check=True,stdin=source,stdout=output,stderr=subprocess.DEVNULL)
        if output.tell()>10_000_000:raise ValueError('extracted page too large')
        output.seek(0);text=output.read().decode('utf-8')
    geom=rectangle_from_text(text,heading,next_heading)
    canonical=json.dumps(geom,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
    if hashlib.sha256(canonical).hexdigest()!=expected_geometry_sha256:raise ValueError('geometry hash mismatch')
    read_verified()
    return geom
