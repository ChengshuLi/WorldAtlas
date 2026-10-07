#!/usr/bin/env python3
"""Reproduce JRC annual water and Angolan legal-parallel screening for #1243."""
import hashlib, json, os, pathlib
import numpy as np
import rasterio
from rasterio.features import geometry_mask
from rasterio.windows import Window
from shapely.geometry import shape, mapping, box, LineString
from shapely import to_wkb

ROOT = pathlib.Path(__file__).resolve().parent
OUT = pathlib.Path(os.environ.get('OUTPUT_DIR', ROOT / 'outputs'))
OUT.mkdir(parents=True, exist_ok=True)

def readj(path):
    return json.loads(pathlib.Path(path).read_text())

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def geomsha(geom):
    return sha(to_wkb(geom, byte_order=1, output_dimension=2))

def counts_for(ds, geom):
    xmin, ymin, xmax, ymax = geom.bounds
    pixel_x, pixel_y = abs(ds.transform.a), abs(ds.transform.e)
    # Expand a full pixel so all_touched includes edge neighbors. Then align the
    # raster read to the actual integer grid; rounding lengths to nearest could
    # silently omit edge pixel centers for fractional polygon windows.
    xmin -= pixel_x
    xmax += pixel_x
    ymin -= pixel_y
    ymax += pixel_y
    raw_window = ds.window(xmin, ymin, xmax, ymax)
    col = max(0, int(np.floor(raw_window.col_off)))
    row = max(0, int(np.floor(raw_window.row_off)))
    col_stop = min(ds.width, int(np.ceil(raw_window.col_off + raw_window.width)))
    row_stop = min(ds.height, int(np.ceil(raw_window.row_off + raw_window.height)))
    window = Window(col, row, max(1, col_stop - col), max(1, row_stop - row))
    arr = ds.read(1, window=window)
    transform = ds.window_transform(window)
    result = {}
    for all_touched in (False, True):
        mask = geometry_mask([mapping(geom)], out_shape=arr.shape, transform=transform,
                             invert=True, all_touched=all_touched)
        values, numbers = np.unique(arr[mask], return_counts=True)
        counts = {str(value): 0 for value in range(4)}
        for value, number in zip(values, numbers):
            value = int(value)
            if value not in range(4):
                raise ValueError(f'Unexpected JRC waterClass value: {value}')
            counts[str(value)] = int(number)
        if sum(counts.values()) != int(mask.sum()):
            raise ValueError('Raster mask and class totals disagree')
        result['all_touched' if all_touched else 'pixel_centres'] = counts
    return result

def load_raster(year, receipt, features):
    filename = f'jrc-gsw-yearly-{year}-0000320000-0000760000.tif'
    path = ROOT / 'sources/jrc-gsw-v1.4' / filename
    pin = next(row for row in receipt['products'] if row['title'].endswith(str(year)))
    raw = path.read_bytes()
    if len(raw) != pin['bytes'] or sha(raw) != pin['sha256']:
        raise ValueError(f'JRC {year} raster does not match the full-byte pin')
    with rasterio.open(path) as ds:
        if ds.crs.to_epsg() != 4326 or ds.width != 40000 or ds.height != 40000:
            raise ValueError(f'Unexpected JRC {year} raster coordinate system or shape')
        if list(ds.transform)[:6] != [0.00025, 0.0, 10.0, 0.0, -0.00025, 0.0]:
            raise ValueError(f'Unexpected JRC {year} raster transform')
        tile = box(ds.bounds.left, ds.bounds.bottom, ds.bounds.right, ds.bounds.top)
        rows = []
        for kind, feature in features:
            geom = shape(feature['geometry'])
            if not tile.covers(geom):
                raise ValueError(f'JRC tile does not fully cover {kind} {feature["id"]}')
            counts = counts_for(ds, geom)
            center = counts['pixel_centres']
            all_pixels = sum(center.values())
            classified = sum(center[str(value)] for value in (1, 2, 3))
            rows.append({
                'feature_kind': kind,
                'feature_id': feature['id'],
                'geometry_sha256': geomsha(geom),
                'year': year,
                'pixel_counts': counts,
                'pixel_center_count': all_pixels,
                'classified_pixel_center_count': classified,
                'nodata_pixel_center_count': center['0'],
                'not_water_pixel_center_count': center['1'],
                'seasonal_water_pixel_center_count': center['2'],
                'permanent_water_pixel_center_count': center['3'],
                'interpretation': 'Annual 30 m Landsat-derived class observation. Class 0 is NoData. Class 2/3 is positive water evidence only at those classified pixels; it does not classify the complete feature.'
            })
        metadata = {
            'path': str(path.relative_to(ROOT)), 'bytes': len(raw), 'sha256': sha(raw),
            'crs': str(ds.crs), 'width': ds.width, 'height': ds.height,
            'transform': list(ds.transform)[:6],
            'bounds': [ds.bounds.left, ds.bounds.bottom, ds.bounds.right, ds.bounds.top],
            'dtype': ds.dtypes[0], 'geotiff_nodata_tag': ds.nodata,
            'catalog_class_semantics': {'0': 'No data', '1': 'Not water', '2': 'Seasonal water', '3': 'Permanent water'},
            'nominal_pixel_size_m': 30
        }
    return metadata, rows

packet = ROOT
freeze = readj(packet / 'inputs/additional-freeze.json')
if sha(pathlib.Path(__file__).read_bytes()) != freeze['producer_sha256']:
    raise ValueError('Producer differs from frozen code bytes')
for pin in freeze['inputs']:
    raw = (packet / pin['path']).read_bytes()
    if len(raw) != pin['bytes'] or sha(raw) != pin['sha256']:
        raise ValueError(f'Input differs from frozen bytes: {pin["path"]}')
components = readj(packet / 'inputs/component-features.geojson')['features']
contacts = readj(packet / 'inputs/contact-features.geojson')['features']
roster = readj(packet / 'inputs/family-roster.json')
if len(components) != 10 or len(contacts) != 5:
    raise ValueError('Complete ten-component/five-contact family required')
if {feature['id'] for feature in components} != set(roster['component_ids']):
    raise ValueError('Component roster changed')
if {feature['id'] for feature in contacts} != set(roster['contact_ids']):
    raise ValueError('Contact roster changed')
feature_set = [('component', feature) for feature in components]
gsw_receipt = readj(packet / 'inputs/jrc-gsw-v1.4-retrieval.json')
rasters = {}
water_rows = []
for year in (2018, 2019):
    rasters[str(year)], rows = load_raster(year, gsw_receipt, feature_set)
    water_rows.extend(rows)
water_by_feature = {}
for kind, feature in feature_set:
    rows = [row for row in water_rows if row['feature_kind'] == kind and row['feature_id'] == feature['id']]
    water_by_feature[(kind, feature['id'])] = {
        'any_seasonal_water_pixel': any(row['seasonal_water_pixel_center_count'] > 0 for row in rows),
        'any_permanent_water_pixel': any(row['permanent_water_pixel_center_count'] > 0 for row in rows),
        'all_pixel_centres_nodata_both_years': all(row['classified_pixel_center_count'] == 0 for row in rows),
        'classified_pixel_centres_by_year': {str(row['year']): row['classified_pixel_center_count'] for row in rows},
        'seasonal_water_pixel_centres_by_year': {str(row['year']): row['seasonal_water_pixel_center_count'] for row in rows}
    }
component_water = [water_by_feature[('component', feature['id'])] for feature in components]
water_summary = {
    'component_count': len(components),
    'years': [2018, 2019],
    'components_with_any_seasonal_water_pixel': sum(row['any_seasonal_water_pixel'] for row in component_water),
    'components_with_any_permanent_water_pixel': sum(row['any_permanent_water_pixel'] for row in component_water),
    'components_all_nodata_both_years': sum(row['all_pixel_centres_nodata_both_years'] for row in component_water),
    'method': 'Exact complete component polygon mask in the EPSG:4326 10° tile; strict pixel-centre and all-touched counts retained; no reprojection, resampling, fill, snapping or vector repair.',
    'limitations': [
        'Catalog value 0 means NoData, not non-water; the GeoTIFF itself has no nodata tag.',
        'Annual product, nominal 30 m Landsat-derived water classification; not a date-specific legal or administrative boundary.',
        'Sparse valid observations do not certify a full component or explain how the Atlas gap was produced.',
        'Five full neighboring administrative contact polygons are retained by exact IDs and geometry hashes as context; they are not candidate footprints and are not sampled by this candidate-scale water screen.'
    ]
}

law_receipt = readj(packet / 'inputs/angola-law-14-24-retrieval.json')
law_pin = law_receipt['products'][0]
law_path = packet / 'sources/official-angola/angola-law-14-24-official-gazette.pdf'
law_raw = law_path.read_bytes()
if len(law_raw) != law_pin['bytes'] or sha(law_raw) != law_pin['sha256']:
    raise ValueError('Official Angolan legal source does not match full-byte pin')
parallels = [
    {'id': 'parallel_8_05_46_6S', 'latitude': -(8 + 5/60 + 46.6/3600), 'legal_description': 'Article 244: Rio Lola to Rio Combe; this parallel to intersection with Rio Uhamba.'},
    {'id': 'parallel_8S', 'latitude': -8.0, 'legal_description': 'Article 244: Rio Camanguna to the 8th parallel and along it to Rio Lucaia; also Rio Cuengo to the 8th parallel and along it to Rio Luita.'},
    {'id': 'parallel_7_55S', 'latitude': -(7 + 55/60), 'legal_description': 'Article 244: Rio Lucaia to the 7°55′S parallel and along it to Rio Capucumba.'},
    {'id': 'parallel_7_34_24_3S', 'latitude': -(7 + 34/60 + 24.3/3600), 'legal_description': 'Article 244: the 7°34′24.3″S parallel from the Luita/Cuilo confluence to Rio Camabemba.'}
]
legal_rows = []
for kind, feature in feature_set:
    geom = shape(feature['geometry'])
    hits = []
    for parallel in parallels:
        line = LineString([(geom.bounds[0] - 0.001, parallel['latitude']), (geom.bounds[2] + 0.001, parallel['latitude'])])
        intersection = geom.intersection(line)
        if not intersection.is_empty:
            hits.append({
                'parallel_id': parallel['id'], 'latitude': parallel['latitude'],
                'intersection_type': intersection.geom_type,
                'intersection_wkb_hex': intersection.wkb_hex,
                'intersection_geometry_sha256': geomsha(intersection),
                'intersection_length_degrees': intersection.length,
                'legal_description': parallel['legal_description'],
                'scope_limit': 'The legal text names river endpoints without coordinate geometry; this is only an intersection with the infinite parallel coordinate, not confirmation that the law-defined segment spans this feature.'
            })
    legal_rows.append({'feature_kind': kind, 'feature_id': feature['id'], 'geometry_sha256': geomsha(geom), 'legal_parallel_intersections': hits})
component_legal = [row for row in legal_rows if row['feature_kind'] == 'component']
legal_summary = {
    'component_count': len(components), 'contact_count': len(contacts),
    'components_intersecting_named_parallel_coordinates': sum(bool(row['legal_parallel_intersections']) for row in component_legal),
    'law_vintage': '2024-09-05',
    'legal_authority': 'Republic of Angola, Lei n.º 14/24, Diário da República I Série n.º 171, Article 244, printed page 9954 (PDF page 156)',
    'source_pdf_bytes': len(law_raw), 'source_pdf_sha256': sha(law_raw),
    'interpretation': 'Current official provincial legal description is a source lead for present Lunda-Norte limits. It postdates the consumed AGO 2018/COD 2019 products and is not a historical source geometry. It does not establish physical water, causal stage, or a candidate ownership decision.',
    'limitations': [
        'The law gives river-course references and latitude parallels but not complete georeferenced river/line geometry or river endpoint coordinates.',
        'The law annex map is not treated as georeferenced; no map registration was available.',
        'Recorded exact intersections are with infinite coordinate parallels, not verified finite legal segments.'
    ]
}

# Metrics are direct scalar values so each one can be bound to this generated file.
component_results = []
for feature in sorted(components, key=lambda item: item['id']):
    wid = water_by_feature[('component', feature['id'])]
    legal = next(row for row in component_legal if row['feature_id'] == feature['id'])
    prior = readj(packet / 'outputs/component-assessment.json')
    assessment = next(row for row in prior['components'] if row['component_id'] == feature['id'])
    component_results.append({
        'component_id': feature['id'],
        'existing_whole_component_disposition': assessment['classification'],
        'jrc_water_findings': wid,
        'jrc_yearly_pixel_counts': [row for row in water_rows if row['feature_kind'] == 'component' and row['feature_id'] == feature['id']],
        'official_lunda_norte_legal_parallel_intersections': legal['legal_parallel_intersections'],
        'disposition': 'unresolved for whole-footprint water status and cause; pixel detections and coordinate-parallel intersections are partial evidence only'
    })
source_digest = sha(json.dumps({
    'jrc_2018_sha256': rasters['2018']['sha256'],
    'jrc_2019_sha256': rasters['2019']['sha256'],
    'law_pdf_sha256': legal_summary['source_pdf_sha256'],
    'component_features_sha256': sha((packet / 'inputs/component-features.geojson').read_bytes()),
    'contact_features_sha256': sha((packet / 'inputs/contact-features.geojson').read_bytes()),
    'producer_sha256': sha(pathlib.Path(__file__).read_bytes()),
    'frozen_input_manifest_sha256': sha((packet / 'inputs/additional-freeze.json').read_bytes())
}, sort_keys=True, separators=(',', ':')).encode())

output = {
    'family_id': roster['id'],
    'component_ids_sha256': roster['component_ids_sha256'],
    'contact_ids': sorted(roster['contact_ids']),
    'contact_count': len(contacts),
    'input_pin_set_sha256': source_digest,
    'jrc_water_summary': water_summary,
    'official_boundary_summary': legal_summary,
    'components_with_seasonal_water_pixel': water_summary['components_with_any_seasonal_water_pixel'],
    'components_with_permanent_water_pixel': water_summary['components_with_any_permanent_water_pixel'],
    'components_all_nodata_both_years': water_summary['components_all_nodata_both_years'],
    'components_intersecting_legal_parallel_coordinates': legal_summary['components_intersecting_named_parallel_coordinates'],
    'source': {
        'dataset': 'JRC Global Surface Water v1.4 YearlyHistory',
        'catalog_url': 'https://developers.google.com/earth-engine/datasets/catalog/JRC_GSW1_4_YearlyHistory',
        'license': 'Copernicus Programme; free of charge without restriction of use; attribute EC JRC/Google',
        'class_semantics': {'0': 'No data', '1': 'Not water', '2': 'Seasonal water', '3': 'Permanent water'},
        'tiles': rasters
    },
    'legal_source': {
        'title': law_receipt['source_title'],
        'url': law_pin['url'],
        'printed_page': 9954,
        'pdf_page': 156,
        'article': '244, Lunda-Norte geographic limits',
        'file_bytes': len(law_raw), 'sha256': sha(law_raw),
        'parallels': parallels
    },
    'components': component_results,
    'contacts': [
        {
            'contact_id': feature['id'],
            'geometry_type': feature['geometry']['type'],
            'geometry_sha256': geomsha(shape(feature['geometry'])),
            'disposition': 'complete neighboring administrative polygon retained as contact context; not a candidate gap footprint and not included in candidate-scale water or legal-parallel classification'
        } for feature in sorted(contacts, key=lambda item: item['id'])
    ],
    'overall_disposition': 'No whole component or contact is classified as land, water, legally owned, or caused by an identified processing stage. Preserve all ten component geometries and five original contacts; no repair or approval is proposed.'
}
(OUT / 'physical-water-authority-assessment.json').write_text(json.dumps(output, sort_keys=True, separators=(',', ':'), ensure_ascii=False) + '\n')
