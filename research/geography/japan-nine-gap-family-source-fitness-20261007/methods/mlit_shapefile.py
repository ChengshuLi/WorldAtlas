"""Read the complete official N03 shapefile and DBF without editing coordinates."""
import io, struct
from shapely.geometry import Polygon, MultiPolygon, Point
from shapely.validation import explain_validity


def dbf_rows(raw):
    if len(raw)<33: raise ValueError('DBF too short')
    count=struct.unpack_from('<I',raw,4)[0]; header=struct.unpack_from('<H',raw,8)[0]; recsize=struct.unpack_from('<H',raw,10)[0]
    fields=[];offset=1;pos=32
    while pos < header and raw[pos] != 0x0d:
        desc=raw[pos:pos+32]
        name=desc[:11].split(b'\0',1)[0].decode('ascii')
        kind=chr(desc[11]); width=desc[16]; decimal=desc[17]
        fields.append((name,kind,width,decimal,offset));offset+=width;pos+=32
    if header < 33 or recsize != offset or header + count*recsize > len(raw): raise ValueError('DBF layout/count mismatch')
    rows=[]
    for i in range(count):
        row=raw[header+i*recsize:header+(i+1)*recsize]
        if len(row)!=recsize or row[0] not in (0x20,0x2a):raise ValueError('Invalid DBF row')
        value={'__deleted__':row[0]==0x2a}
        for name,kind,width,decimal,start in fields:
            b=row[start:start+width]
            if kind in ('N','F'):
                s=b.decode('ascii').strip();v=None if not s or s=='*' else (float(s) if decimal else int(s))
            else:
                s=b.decode('cp932').strip();v=s or None
            value[name]=v
        rows.append(value)
    return rows,{'record_count':count,'header_bytes':header,'record_bytes':recsize,'fields':[{'name':n,'kind':k,'width':w,'decimal':d} for n,k,w,d,_ in fields]}


def signed_area(ring):
    return sum(ring[i][0]*ring[i+1][1]-ring[i+1][0]*ring[i][1] for i in range(len(ring)-1))/2


def rings_to_geometry(rings):
    shells=[]; holes=[]; errors=[]
    for ring in rings:
        if len(ring)<4 or ring[0]!=ring[-1]: errors.append('open-or-short-ring');continue
        area=signed_area(ring)
        if area<0:shells.append((abs(area),ring))
        else:holes.append((area,ring))
    # ESRI Polygon rings encode shells clockwise and holes counter-clockwise.
    if not shells and holes:
        shells=[(a,r) for a,r in holes];holes=[];errors.append('no-clockwise-shell-ring')
    assigned=[[] for _ in shells]
    for _,hole in holes:
        hole_point=Polygon(hole).representative_point()
        choices=[]
        for i,(area,shell) in enumerate(shells):
            try:
                if Polygon(shell).contains(hole_point):choices.append((area,i))
            except Exception:pass
        if not choices:errors.append('orphan-hole-ring')
        else:assigned[min(choices)[1]].append(hole)
    polys=[]
    for (_,shell),inner in zip(shells,assigned):
        try:polys.append(Polygon(shell,inner))
        except Exception:errors.append('polygon-construction-failed')
    if not polys:return None,errors or ['no-polygon-rings']
    geom=polys[0] if len(polys)==1 else MultiPolygon(polys)
    return geom,errors


def iter_features(zipfile_object, check_validity=False, query_bounds=None, reader_receipt=None):
    dbf=zipfile_object.read('N03-17_170101.dbf')
    rows,dbf_info=dbf_rows(dbf)
    if reader_receipt is not None:
        reader_receipt.update({'dbf_record_count':dbf_info['record_count'],'dbf_layout':dbf_info})
    shp=zipfile_object.open('N03-17_170101.shp')
    header=shp.read(100)
    if len(header)!=100 or struct.unpack_from('>I',header)[0]!=9994 or struct.unpack_from('<I',header,28)[0]!=1000:
        raise ValueError('Invalid SHP header')
    shape_type=struct.unpack_from('<I',header,32)[0]
    if shape_type!=5:raise ValueError(f'Expected Polygon shape type 5, found {shape_type}')
    ordinal=0; bbox_skipped=0
    while True:
        rh=shp.read(8)
        if not rh:break
        if len(rh)!=8:raise ValueError('Truncated SHP record header')
        record_number,words=struct.unpack('>II',rh);size=words*2
        content=shp.read(size)
        if len(content)!=size:raise ValueError('Truncated SHP record')
        if ordinal>=len(rows):raise ValueError('More SHP records than DBF records')
        attrs=rows[ordinal];stype=struct.unpack_from('<I',content)[0]
        geom=None;errors=[]
        if stype==0: errors=['null-shape']
        elif stype==5:
            # SHP record bbox is an exact source-record envelope. It is used
            # only to skip geometry construction outside every target envelope;
            # retained rows still undergo full native-ring construction and
            # exact Shapely predicates. It never decides an overlay result.
            if query_bounds is not None:
                minx,miny,maxx,maxy=struct.unpack_from('<dddd',content,4)
                if not any(minx<=b[2] and maxx>=b[0] and miny<=b[3] and maxy>=b[1] for b in query_bounds):
                    ordinal+=1; bbox_skipped+=1
                    continue
            n_parts,n_points=struct.unpack_from('<II',content,36)
            need=44+4*n_parts+16*n_points
            if need!=len(content):raise ValueError('SHP polygon record size differs')
            starts=list(struct.unpack_from('<'+'I'*n_parts,content,44))
            xypos=44+4*n_parts
            points=[struct.unpack_from('<dd',content,xypos+16*i) for i in range(n_points)]
            starts.append(n_points);rings=[]
            for a,b in zip(starts,starts[1:]):rings.append(points[a:b])
            geom,errors=rings_to_geometry(rings)
        else:errors=[f'unsupported-shape-type-{stype}']
        valid = None if geom is None or not check_validity else bool(geom.is_valid)
        validity = None if geom is None or not check_validity else explain_validity(geom)
        yield {'record_ordinal':ordinal,'record_number':record_number,'shape_type':stype,'properties':attrs,'geometry':geom,'geometry_errors':errors,'validity':validity,'valid':valid}
        ordinal+=1
    shp.close()
    if ordinal!=len(rows):raise ValueError('SHP/DBF record count mismatch')
    if dbf_info['record_count']!=ordinal:raise ValueError('DBF count mismatch')
    if reader_receipt is not None:
        reader_receipt.update({'shp_record_count':ordinal,'bbox_skipped_record_count':bbox_skipped,'bbox_selected_record_count':ordinal-bbox_skipped})
