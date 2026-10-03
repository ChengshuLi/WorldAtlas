#!/usr/bin/env python3
"""Reconstruct finite modern Chagos dry-land evidence; never mutate atlas data."""
import argparse, copy, gzip, hashlib, json, pathlib, sys
import xml.etree.ElementTree as ET
from shapely import STRtree, normalize
from shapely.geometry import Polygon, Point, box, shape, mapping
from shapely.geometry.polygon import orient
from shapely.ops import unary_union
from pyproj import Geod
sys.dont_write_bytecode = True
HERE = pathlib.Path(__file__).resolve().parent
GEOD = Geod(ellps='WGS84')

def encoded(value):
    return json.dumps(value,ensure_ascii=False,separators=(',',':')).encode()

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def document(path):
    raw=pathlib.Path(path).read_bytes()
    return json.loads(gzip.decompress(raw) if str(path).endswith('.gz') else raw)

def area(g):
    if g.is_empty: return 0.0
    if g.geom_type=='Polygon': return abs(GEOD.geometry_area_perimeter(orient(g,1))[0])/1e6
    return sum(area(part) for part in g.geoms if part.geom_type in ('Polygon','MultiPolygon','GeometryCollection'))

def whole_water_mask(xml, coast_rings):
    """Closed OSM coast-water, tagged-water and complete relation masks."""
    nodes = {n.attrib['id']: (float(n.attrib['lon']), float(n.attrib['lat'])) for n in xml.findall('node')}
    ways = {w.attrib['id']: w for w in xml.findall('way')}
    masks = [Polygon(r['coordinates']) for r in coast_rings if r['land_on_left_signed_area_km2'] < 0]
    lineage = []
    for w in ways.values():
        tags = {t.attrib['k']: t.attrib['v'] for t in w.findall('tag')}
        if tags.get('natural') != 'water' and tags.get('landuse') != 'reservoir':
            continue
        refs = [n.attrib['ref'] for n in w.findall('nd')]
        if len(refs) < 4 or refs[0] != refs[-1] or any(n not in nodes for n in refs):
            raise ValueError('Incomplete source inland-water way')
        polygon = Polygon([nodes[n] for n in refs])
        if not polygon.is_valid:
            raise ValueError('Invalid source water polygon')
        masks.append(polygon)
        lineage.append({'kind': 'closed-water-way', 'id': w.attrib['id'], 'version': w.attrib.get('version'), 'timestamp': w.attrib.get('timestamp')})

    def assemble(rel, role):
        pending = []
        for m in rel.findall('member'):
            if m.attrib.get('type') != 'way' or m.attrib.get('role', 'outer') != role:
                continue
            w = ways.get(m.attrib['ref'])
            if w is None:
                raise ValueError('Incomplete source water relation')
            refs = [n.attrib['ref'] for n in w.findall('nd')]
            if any(n not in nodes for n in refs):
                raise ValueError('Missing water relation nodes')
            pending.append(refs)
        polygons = []
        while pending:
            chain = pending.pop()
            while chain[0] != chain[-1]:
                for i, other in enumerate(pending):
                    if chain[-1] == other[0]:
                        chain.extend(other[1:])
                    elif chain[-1] == other[-1]:
                        chain.extend(other[-2::-1])
                    elif chain[0] == other[-1]:
                        chain = other[:-1] + chain
                    elif chain[0] == other[0]:
                        chain = other[:0:-1] + chain
                    else:
                        continue
                    pending.pop(i)
                    break
                else:
                    raise ValueError('Open source water relation ring')
            polygon = Polygon([nodes[n] for n in chain])
            if not polygon.is_valid:
                raise ValueError('Invalid source water relation ring')
            polygons.append(polygon)
        return polygons

    for rel in xml.findall('relation'):
        tags = {t.attrib['k']: t.attrib['v'] for t in rel.findall('tag')}
        if tags.get('natural') != 'water' and tags.get('water') not in ['lake', 'pond', 'reservoir', 'lagoon']:
            continue
        outer, inner = assemble(rel, 'outer'), assemble(rel, 'inner')
        if not outer:
            raise ValueError('Water relation has no outer')
        masks.append(unary_union(outer).difference(unary_union(inner)))
        lineage.append({'kind': 'water-relation', 'id': rel.attrib['id'], 'version': rel.attrib.get('version'), 'timestamp': rel.attrib.get('timestamp'), 'outer_count': len(outer), 'inner_count': len(inner)})
    return nodes, ways, masks, lineage



def source_rings(query):
    raw=gzip.decompress((HERE/query['original_path']).read_bytes())
    assert digest(raw)==query['original_sha256'], 'Original XML changed'
    root=ET.fromstring(raw)
    nodes, ways, masks, water_lineage=whole_water_mask(root,query['closed_rings'])
    assert not query['open_chains'], 'Clipped/open coastline source'
    polygons=[]; proofs=[]
    for ring in query['closed_rings']:
        pending=[]
        for version in ring['way_versions']:
            way=ways[version['id']]
            assert all(way.attrib.get(k)==version[k] for k in ['version','timestamp'])
            refs=[n.attrib['ref'] for n in way.findall('nd')]
            assert all(n in nodes for n in refs)
            pending.append(refs)
        chain=pending.pop()
        while pending:
            for i,refs in enumerate(pending):
                if chain[-1]==refs[0]: chain.extend(refs[1:])
                elif refs[-1]==chain[0]: chain=refs[:-1]+chain
                else: continue
                pending.pop(i);break
            else: raise ValueError('Directed coastlines do not join')
        assert chain[0]==chain[-1], 'Open coastline'
        g=Polygon([nodes[n] for n in chain])
        assert g.is_valid and box(*query['requested_bbox']).covers(g)
        assert normalize(g).equals_exact(normalize(Polygon(ring['coordinates'])),0)
        if GEOD.geometry_area_perimeter(g)[0]<0: continue
        # Clip complete water masks to each complete land component. Lagoon
        # islands are retained by relation inner rings, never filled with water.
        dry=g.difference(unary_union(masks))
        assert dry.is_valid and not dry.is_empty
        polygons.append(dry)
        proofs.append({'query':query['name'],'source_class':'OSM-directed-closed-coastline','source_xml_sha256':query['original_sha256'],
                       'source_way_versions':ring['way_versions'],'source_node_count':len(chain),
                       'geometry_sha256':digest(normalize(dry).wkb),'area_km2':area(dry),
                       'bounds':list(dry.bounds),'water_lineage':water_lineage})
    # Complete named island polygons can be mapped without a coastline tag.
    # Retain that distinct source interpretation rather than inventing a shore.
    for w in ways.values():
        tags={t.attrib['k']:t.attrib['v'] for t in w.findall('tag')}
        if tags.get('place') not in ['islet','island'] or tags.get('natural')=='coastline': continue
        refs=[n.attrib['ref'] for n in w.findall('nd')]
        if not tags.get('name') or len(refs)<4 or refs[0]!=refs[-1]: continue
        assert all(n in nodes for n in refs)
        g=Polygon([nodes[n] for n in refs])
        assert g.is_valid and box(*query['requested_bbox']).covers(g)
        # Bound this explicit source-class addition to the individually reviewed
        # original named islet. Other place polygons need their own review.
        assert w.attrib['id']=='1320152445' and tags['name']=='Anniversary Island'
        polygons.append(g)
        proofs.append({'query':query['name'],'source_class':'OSM-closed-named-place-islet-polygon',
                       'source_xml_sha256':query['original_sha256'],'source_tags':tags,
                       'source_way_versions':[{k:w.attrib.get(k) for k in ['id','version','timestamp']}],
                       'source_node_count':len(refs),'geometry_sha256':digest(normalize(g).wkb),
                       'area_km2':area(g),'bounds':list(g.bounds),'water_lineage':[],
                       'interpretation':'Exact named island extent; not tagged coastline; source precision/tide uncertainty retained'})
    return polygons,proofs


def reproduce(baseline,output):
    assert not output.exists(), 'Use a fresh separate output directory'
    output.mkdir(parents=True)
    queries=document(HERE/'source-coastline-index.json.gz')
    sources=[];proofs=[];groups=[]
    for q in queries:
        polygons,rows=source_rings(q);sources.extend(polygons);proofs.extend(rows)
        group=unary_union(polygons)
        groups.append({'name':q['name'],'bbox':q['requested_bbox'],
                       'complete_dry_land_components':len(polygons),'area_km2':area(group),
                       'source_geometry_sha256':digest(normalize(group).wkb),
                       'grouping':'Source family components of retained Chagos territory IOT+00?; no location per ring',
                       'zero_coastlines_is_not_no_land_proof':not polygons})
    component_tree=STRtree(sources)
    for i,g in enumerate(sources):
        for j in component_tree.query(g,predicate='intersects'):
            if int(j)<=i: continue
            assert area(g.intersection(sources[j]))<=1e-12,'Source components overlap beyond0.001m²'
    previous_components=document(HERE/'gshhg-domain-crosswalk.json')['components']
    assert len(previous_components)==62
    for row in previous_components:
        bbox=row['bounds']
        matching=[q['name'] for q in queries if box(*q['requested_bbox']).covers(box(*bbox))]
        assert matching==row['enclosing_modern_queries'] and matching
    source_union=unary_union(sources)
    index=document(baseline/'world-index.json');features=[];parts={}
    for name in index['parts']:
        raw=(baseline/name).read_bytes();parts[name]=digest(raw)
        features.extend(json.loads(raw)['features'])
    before=next(f for f in features if f['properties']['id']=='IOT+00?')
    expected=document(HERE/'baseline-subject.json')
    assert digest(encoded(before))==expected['feature_sha256'], 'Baseline subject changed'
    original=shape(before['geometry']);after=source_union
    assert after.is_valid and original.difference(after).is_empty
    other=[f for f in features if f['properties']['id']!='IOT+00?']
    geometries=[shape(f['geometry']) for f in other];tree=STRtree(geometries)
    overlaps=[]
    for i in tree.query(after,predicate='intersects'):
        overlap=area(after.intersection(geometries[i]))
        if overlap>0: overlaps.append({'id':other[i]['properties']['id'],'area_km2':overlap})
    assert not overlaps,'Unrelated location overlap'
    names=document(HERE/'sources/IO-islands.json');crosswalk=[]
    original_names=gzip.decompress((HERE/'sources/IO-original-island-lines.tsv.gz').read_bytes())
    assert digest(original_names)==document(HERE/'geonames-source.json')['source_island_lines_sha256']
    raw_names={r.split('\t')[0]:r.split('\t') for r in original_names.decode().splitlines()}
    assert set(raw_names)=={r['id'] for r in names}
    for r in names:
        raw=raw_names[r['id']]
        assert r['name']==raw[1] and r['latitude']==float(raw[4]) and r['longitude']==float(raw[5])
    for page in document(HERE/'gazetteer-pages.json'):
        assert digest(gzip.decompress((HERE/page['compressed_path']).read_bytes()))==page['sha256']
    for r in names:
        point=Point(r['longitude'],r['latitude'])
        matching=[q['name'] for q in queries if box(*q['requested_bbox']).covers(point)]
        matches=[p['query'] for p,g in zip(proofs,sources) if g.covers(point)]
        crosswalk.append({'geonames_id':r['id'],'name':r['name'],'feature_code':r['feature_code'],
                          'coordinate':[r['longitude'],r['latitude']],'source_modified':r['modified'],
                          'source_domains':matching,'point_within_dry_components':sorted(set(matches)),
                          'status':'name-point-in-source-dry-land' if matches else
                                   'family-centre-not-land-proof' if r['feature_code'] in ['ATOL','ISLS'] else
                                   'source-name-point-outside-modern-coastline; alias/vintage uncertainty retained',
                          'geometry_was_not_moved_to_fit_name':True})
    updated=copy.deepcopy(before);updated['geometry']=mapping(after)
    updated['properties']['metadata']['chagos_complete_conventional_land_source']={
        'source':'OpenStreetMap contributors ODbL1.0','reference_year':2026,
        'source_index_sha256':digest((HERE/'source-coastline-index.json.gz').read_bytes()),
        'scope':'All complete conventional coastline components in 10 documented domains plus exact named Anniversary islet polygon; tide-dependent reefs separate',
        'historical_names_ownership_not_inferred':True}
    delta=after.difference(original)
    validation={'version':1,'issue':540,'retained_location_id':'IOT+00?',
                'retained_parent_id':before['properties']['parent_id'],'locations_before':len(features),
                'locations_added':0,'groups_added':0,'source_queries':len(queries),
                'source_positive_land_components':len(proofs),'source_coastline_components':sum(p['source_class']=='OSM-directed-closed-coastline' for p in proofs),'source_named_islet_polygons':sum(p['source_class']=='OSM-closed-named-place-islet-polygon' for p in proofs),
                'source_components_mutually_nonoverlapping_to_m2':0.001,'all_complete_rings_valid':True,'open_coastline_chains':0,'area_floor_km2':0,
                'before_area_km2':area(original),'after_area_km2':area(after),'new_land_km2':area(delta),
                'source_union_area_km2':area(source_union),'old_land_removed_km2':area(original.difference(after)),'all_62_old_shoreline_components_in_reviewed_domains':True,'all_70_original_gazetteer_records_accounted':True,
                'unrelated_location_overlap_km2':0,'historical_claims_transferred':False,
                'original_OSM_bytes_verified':True,'new_geography_installed':False,'grid_representation_verified':False,
                'baseline_feature_sha256':digest(encoded(before)),'source_groups':groups,
                'limitations':document(HERE/'tidal-reef-decisions.json')['limits']}
    patch={'version':1,'schema':'worldatlas-sparse-geography-patch-v1','issue':540,
           'status':'staged-source-proposal-not-installed','baseline':{'location_count':len(features),
           'hierarchy_sha256':digest((baseline/'hierarchy.json').read_bytes()),'subject_sha256':digest(encoded(before))},
           'existing_location_updates':[updated],'existing_group_updates':[],
           'added_features':[],'added_groups':[],'creation_proofs':[], 'source_checks':proofs,
           'operations':[{'kind':'retained-id-footprint-restoration','id':'IOT+00?',
                          'before_geometry_sha256':digest(normalize(original).wkb),
                          'after_geometry_sha256':digest(normalize(after).wkb),
                          'source_component_count':len(proofs),'new_land_km2':area(delta)}],
           'supported_from':2026,'supported_to':2027,'input_geography_version':4,'input_hierarchy_sha256':digest((baseline/'hierarchy.json').read_bytes()),'input_part_sha256':parts,
           'history_transfer':False,'historical_claims_transferred':False,'publication_ready':False,
           'holds':validation['limitations'],
           'invalidation_required':['ancestor-unions','geographic-release','fixed-grid','derived-ownership','derived-environment','regional-certificates'],
           'archive_path':'before-features.json.gz'}
    for name,value in [('patch.json.gz',patch),('before-features.json.gz',[before]),
                       ('source-proofs.json.gz',proofs),('named-family-crosswalk.json',crosswalk),('validation.json',validation)]:
        raw=encoded(value)+b'\n';(output/name).write_bytes(gzip.compress(raw,mtime=0) if name.endswith('.gz') else raw)
    (output/'source-land.wkb.gz').write_bytes(gzip.compress(normalize(source_union).wkb,mtime=0))
    wrapper={'type':'FeatureCollection','features':[{'type':'Feature','properties':{'id':'IOT+00?','name':'Chagos modern sourced dry land','reference_only':True,'supported_from':2026,'supported_to':2027,'source_classes':['OSM-directed-closed-coastline','OSM-closed-named-place-islet-polygon']},'geometry':mapping(after)}]}
    (output/'source-dry-land.geojson.gz').write_bytes(gzip.compress(encoded(wrapper)+b'\n',mtime=0))
    index={'version':1,'issue':540,'preparation_script_sha256':digest(pathlib.Path(__file__).read_bytes()),
           'files':{p.name:{'sha256':digest(p.read_bytes())} for p in sorted(output.iterdir()) if p.is_file()},
           'installed_geography_changed':False,'historical_records_changed':False,'publication_ready':False}
    (output/'index.json').write_bytes(encoded(index)+b'\n')
    return validation

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline',type=pathlib.Path,required=True)
    parser.add_argument('--output',type=pathlib.Path,required=True)
    args=parser.parse_args();print(json.dumps(reproduce(args.baseline,args.output),indent=2))
