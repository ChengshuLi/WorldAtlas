"""Allocate published GHSL native cell counts conservatively to fixed atlas land.

No temporal interpolation, cell-centre count sampling or settlement-total transfer.
Boundary cells use exact planar overlap in the dataset's equal-area projection;
unallocated source mass and unsupported land remain explicit in the receipt.
"""
import argparse
import collections
import gzip
import hashlib
import json
import math
import pathlib
import shutil
import subprocess
import time
import zipfile

import numpy as np
import rasterio
from rasterio.features import rasterize
from rasterio.windows import Window, from_bounds
from pyproj import Transformer
from shapely import area as geometry_area, box, intersection, make_valid
from shapely.geometry import Polygon, mapping, shape
from shapely import STRtree
from majority import canonical, polygons

ROOT = pathlib.Path(__file__).resolve().parents[1]
CACHE = ROOT / '.cache/ghsl'
OUT = ROOT / 'data/population-ghsl'
SOURCE_DOI = 'https://doi.org/10.2905/2FF68A52-5B5B-4A22-8F40-C41DA8332CFE'
METHODOLOGY = 'https://doi.org/10.1080/17538947.2024.2390454'
LICENSE_URL = 'https://human-settlement.emergency.copernicus.eu/GHSLhowToCite.php'
MIN_SOURCE_COVERAGE = .999
PROJECTION_CHORD_ERROR_METRES = .0005


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def source_contract(epoch, archive_sha, download_url):
    role = 'projected' if epoch > 2020 else 'modeled'
    return {'id': f'ghsl:population:R2023A:E{epoch}', 'name': f'GHSL GHS-POP R2023A, {epoch} {role} residential population',
        'url': SOURCE_DOI, 'license': 'CC BY 4.0', 'vintage': f'R2023A / E{epoch}; native 1 km Mollweide counts',
        'supported_from': epoch, 'supported_to': epoch + 1, 'status': 'estimate',
        'metadata': {'source_download_url': download_url, 'sha256': archive_sha, 'methodology': METHODOLOGY,
            'product_notice': LICENSE_URL, 'source_epoch': epoch, 'modeled': True, 'no_interpolation': True,
            'snapshot_only': True, 'attribution': 'European Union / Joint Research Centre; Schiavina, Freire and MacManus. Adapted by WorldAtlas.'}}


def projected_ring(ring, projection):
    """Adaptively bound perpendicular projection curvature, not geographic spacing.

    Horizontal Mollweide parallels need no extra vertices. Quarter/mid/three-quarter
    probes detect inflections; this avoids millions of needless uniform subdivisions.
    """
    coords = np.asarray(ring.coords, dtype=np.float64)
    for depth in range(25):
        px, py = projection.transform(coords[:, 0], coords[:, 1])
        projected = np.column_stack((px, py))
        vectors = projected[1:] - projected[:-1]
        length = np.hypot(vectors[:, 0], vectors[:, 1])
        max_error = np.zeros(len(vectors), dtype=float)
        for fraction in (.25, .5, .75):
            probe = coords[:-1] + fraction * (coords[1:] - coords[:-1])
            qx, qy = projection.transform(probe[:, 0], probe[:, 1])
            offset = np.column_stack((qx, qy)) - projected[:-1]
            error = np.abs(offset[:, 0] * vectors[:, 1] - offset[:, 1] * vectors[:, 0]) / np.maximum(length, 1e-30)
            max_error = np.maximum(max_error, error)
        split = max_error > PROJECTION_CHORD_ERROR_METRES
        if not split.any():
            return projected
        origin_indices = np.r_[0, np.cumsum(1 + split.astype(np.int64))]
        refined = np.empty((len(coords) + int(split.sum()), 2), dtype=np.float64)
        refined[origin_indices] = coords
        refined[origin_indices[:-1][split] + 1] = (coords[:-1][split] + coords[1:][split]) / 2
        coords = refined
    raise ValueError('Projection curvature failed to converge within the millimetre bound')


def project_piece(piece, projection):
    return Polygon(projected_ring(piece.exterior, projection), [projected_ring(r, projection) for r in piece.interiors])


def intersection_partition(piece):
    """Disjoint exact clipping partitions reduce repeated GEOS edge-index building.

    Raster masks still use the original polygon. Only exact boundary intersections
    query these smaller parts, with their area sum checked against the original.
    """
    work = [(piece, 0)]
    leaves = []
    while work:
        part, depth = work.pop()
        vertices = len(part.exterior.coords) + sum(len(r.coords) for r in part.interiors)
        if vertices <= 128 or depth >= 18:
            leaves.append(part)
            continue
        lo_x, lo_y, hi_x, hi_y = part.bounds
        if hi_x - lo_x >= hi_y - lo_y:
            mid = (lo_x + hi_x) / 2
            clips = [box(lo_x - 1, lo_y - 1, mid, hi_y + 1), box(mid, lo_y - 1, hi_x + 1, hi_y + 1)]
        else:
            mid = (lo_y + hi_y) / 2
            clips = [box(lo_x - 1, lo_y - 1, hi_x + 1, mid), box(lo_x - 1, mid, hi_x + 1, hi_y + 1)]
        for clip in clips:
            for p in polygons(part.intersection(clip)):
                if not p.is_empty and p.area > 0:
                    work.append((p, depth + 1))
    if not math.isclose(sum(p.area for p in leaves), piece.area, rel_tol=1e-10, abs_tol=1e-5):
        raise ValueError('Exact polygon intersection partition failed area conservation')
    parts = np.array(leaves, dtype=object)
    return STRtree(parts), parts


def cell_shares(piece, affine, height, width, partition=None):
    """Exact edge overlap; cells away from every boundary are wholly inside/outside."""
    if not height or not width:
        return np.zeros((height, width), dtype=np.float64)
    interior = rasterize([(mapping(piece), 1)], out_shape=(height, width), transform=affine, dtype='uint8').astype(bool)
    # GDAL line rasterization can omit the adjacent cell when a boundary clips a
    # tiny corner. Conservatively inspect its full one-cell neighborhood. The
    # halo is outside this strip too, so clipping at strip edges cannot hide it.
    expanded_affine = affine * affine.translation(-1, -1)
    edge = rasterize([(mapping(piece.boundary), 1)], out_shape=(height + 2, width + 2), transform=expanded_affine, all_touched=True, dtype='uint8').astype(bool)
    boundary = np.zeros((height, width), dtype=bool)
    for dy in range(3):
        for dx in range(3):
            boundary |= edge[dy:dy + height, dx:dx + width]
    weights = interior.astype(np.float64)
    rows, cols = np.nonzero(boundary)
    if len(rows):
        left = affine.c + cols * affine.a
        top = affine.f + rows * affine.e
        cells = box(left, top + affine.e, left + affine.a, top)
        if partition is None:
            areas = geometry_area(intersection(cells, piece))
        else:
            tree, pieces = partition
            cell_ids, part_ids = tree.query(cells, predicate='intersects')
            areas = np.bincount(cell_ids, weights=geometry_area(intersection(cells[cell_ids], pieces[part_ids])), minlength=len(cells))
        weights[rows, cols] = np.clip(areas / abs(affine.a * affine.e), 0, 1)
    return weights


def allocate(piece, dataset, proof):
    """Bounded strips support islands, holes, polar footprints and huge rural units."""
    window = from_bounds(*piece.bounds, dataset.transform)
    first_col = max(0, math.floor(window.col_off))
    end_col = min(dataset.width, math.ceil(window.col_off + window.width))
    first_row = max(0, math.floor(window.row_off))
    end_row = min(dataset.height, math.ceil(window.row_off + window.height))
    population = covered = valid_zero_area = 0.
    cell_area = abs(dataset.transform.a * dataset.transform.e)
    partition = intersection_partition(piece)
    for row in range(first_row, end_row, 128):
        height = min(128, end_row - row)
        width = end_col - first_col
        if width <= 0:
            continue
        win = Window(first_col, row, width, height)
        affine = dataset.window_transform(win)
        weights = cell_shares(piece, affine, height, width, partition)
        if not weights.any():
            continue
        counts = dataset.read(1, window=win)
        valid = np.isfinite(counts) & (counts >= 0)
        invalid = ~valid & (counts != dataset.nodata)
        if invalid.any():
            raise ValueError('Unexpected negative or nonfinite source population value')
        population += float(np.sum(np.where(valid, counts, 0) * weights, dtype=np.float64))
        covered += float(np.sum(weights[valid], dtype=np.float64)) * cell_area
        valid_zero_area += float(np.sum(weights[valid & (counts == 0)], dtype=np.float64)) * cell_area
        view = proof[row:row + height, first_col:end_col]
        view[:] += weights.astype(np.float32)
    return population, covered, valid_zero_area


def conservation_gate(source_total, allocated_total, direct_total, maximum_cell_share, overlapping_cells):
    """Independent cell ledger and location totals must agree without duplication."""
    totals = (source_total, allocated_total, direct_total, maximum_cell_share)
    if not all(math.isfinite(n) and n >= 0 for n in totals):
        raise ValueError('Population conservation requires finite nonnegative totals')
    if overlapping_cells or maximum_cell_share > 1 + 3e-6 or allocated_total > source_total * (1 + 1e-8) or abs(allocated_total - direct_total) > max(1, source_total * 5e-8):
        raise ValueError(f'Population allocation conservation gate failed: overlaps={overlapping_cells}; maximum-share={maximum_cell_share}; global={source_total}; allocated={allocated_total}; per-location={direct_total}')


def self_test():
    from affine import Affine
    from shapely.geometry import Polygon, MultiPolygon
    affine = Affine(1, 0, 0, 0, -1, 2)
    left = box(0, 0, .5, 2)
    right = box(.5, 0, 2, 2)
    a = cell_shares(left, affine, 2, 2)
    b = cell_shares(right, affine, 2, 2)
    assert np.allclose(a + b, 1)
    assert np.allclose(a[:, 0], .5) and not a[:, 1].any()
    counts = np.array([[100, 200], [300, 400]])
    assert float(np.sum(counts * a)) == 200
    assert float(np.sum(counts * (a + b))) == 1000
    diagonal = Polygon([(0, 0), (2, 0), (0, 2), (0, 0)])
    assert math.isclose(cell_shares(diagonal, affine, 2, 2).sum(), 2)
    donut = Polygon(box(0, 0, 2, 2).exterior.coords, [box(.5, .5, 1.5, 1.5).exterior.coords])
    assert math.isclose(cell_shares(donut, affine, 2, 2).sum(), 3)
    islands = MultiPolygon([box(.1, .1, .2, .2), box(.3, .3, .4, .4)])
    assert math.isclose(cell_shares(islands, affine, 2, 2).sum(), .02)
    missing = np.array([[True, False], [False, False]])
    assert math.isclose(cell_shares(left, affine, 2, 2)[missing].sum(), .5)
    assert np.allclose(cell_shares(donut, affine, 2, 2, intersection_partition(donut)), cell_shares(donut, affine, 2, 2))
    dense = box(0, 0, 2, 2).segmentize(.001)
    assert np.allclose(cell_shares(dense, affine, 2, 2, intersection_partition(dense)), cell_shares(dense, affine, 2, 2))
    # Small corner cuts and strip edges are the actual global failure mechanism:
    # a centre mask alone must not turn a fractional cell into a whole cell.
    corner = Polygon([(0, 0), (4, 0), (4, 4), (2.01, 4), (2.01, 2.999), (1.999, 3.001), (1.999, 4), (0, 4)])
    corner_affine = Affine(1, 0, 0, 0, -1, 4)
    exact = np.array([[corner.intersection(box(col, 3 - row, col + 1, 4 - row)).area for col in range(4)] for row in range(4)])
    assert np.allclose(cell_shares(corner, corner_affine, 4, 4), exact, atol=1e-12)
    for row in range(4):
        strip = cell_shares(corner, corner_affine * corner_affine.translation(0, row), 1, 4)
        assert np.allclose(strip, exact[row:row + 1], atol=1e-12)
    conservation_gate(1000, 1000, 1000, 1, 0)
    conservation_gate(1000, 800, 800, 1, 0)
    for args in [(1000, 1001, 1001, 1, 0), (1000, 800, 802, 1, 0), (1000, 800, 800, 1.00001, 0), (1000, 800, 800, 1, 1), (math.nan, 800, 800, 1, 0)]:
        try:
            conservation_gate(*args)
        except ValueError:
            pass
        else:
            raise AssertionError(f'Invalid conservation proof accepted: {args}')
    print('PASS: full-cell conservation, fractional splits, diagonal, holes, subcell islands, missing-source area, corner/strip regression and global proof rejection')
    publication_self_test()


def publication_self_test():
    """Run the real preparer on a tiny fixture and preserve a prior valid export."""
    import contextlib
    import io
    import tempfile
    from affine import Affine
    from unittest.mock import patch
    global ROOT, CACHE, OUT
    original_paths = ROOT, CACHE, OUT
    with tempfile.TemporaryDirectory(prefix='atlas-ghsl-test-') as directory:
        try:
            ROOT = pathlib.Path(directory)
            CACHE = ROOT / '.cache/ghsl'
            OUT = ROOT / 'data/population-ghsl'
            CACHE.mkdir(parents=True)
            (ROOT / 'data').mkdir()
            raster = CACHE / 'test.tif'
            with rasterio.open(raster, 'w', driver='GTiff', height=2, width=2, count=1, dtype='float64', crs='ESRI:54009', transform=Affine(1000, 0, 0, 0, -1000, 2000), nodata=-200) as dataset:
                dataset.write(np.array([[100, 200], [300, 400]], dtype=np.float64), 1)
            with zipfile.ZipFile(CACHE / '2020.zip', 'w') as archive:
                archive.write(raster, 'test.tif')
            inverse = Transformer.from_crs('ESRI:54009', 'EPSG:4326', always_xy=True)

            def feature(identity, left, right):
                coordinates = [inverse.transform(x, y) for x, y in [(left, 0), (right, 0), (right, 2000), (left, 2000), (left, 0)]]
                return {'type': 'Feature', 'properties': {'id': identity, 'reference_owner': 'Fixture'}, 'geometry': {'type': 'Polygon', 'coordinates': [coordinates]}}

            (ROOT / 'data/world-index.json').write_text(json.dumps({'parts': ['fixture.json']}))
            features = [feature('left', 0, 1000), feature('right', 1000, 2000)]
            part = ROOT / 'data/fixture.json'
            part.write_text(json.dumps({'features': features}))
            with patch.object(subprocess, 'check_output', return_value='0' * 64), contextlib.redirect_stdout(io.StringIO()):
                prepare(2020)
            index_path = OUT / 'index.json'
            before = index_path.read_bytes()
            index = json.loads(before)
            rows = [r for part_row in index['parts'] for r in json.loads(gzip.decompress((OUT / part_row['path']).read_bytes()))]
            assert [(r['location_id'], r['value']) for r in rows] == [('left', 400), ('right', 600)]
            assert all(r['method'] == 'estimate' and r['status'] == 'estimate' for r in rows)
            assert all(digest(OUT / p['path']) == p['sha256'] for p in index['parts'])
            assert index['sources'][0]['status'] == 'estimate'
            receipt = json.loads(gzip.decompress((OUT / index['epochs'][0]['receipt']).read_bytes()))
            assert receipt['overallocated_cells'] == 0 and math.isclose(receipt['source_total_population'], 1000)
            # A second run that double-counts land must neither commit a manifest
            # nor overwrite any content referenced by the first successful one.
            part.write_text(json.dumps({'features': features + [feature('overlap', 0, 2000)]}))
            with patch.object(subprocess, 'check_output', return_value='0' * 64), contextlib.redirect_stdout(io.StringIO()):
                try:
                    prepare(2020)
                except ValueError as error:
                    assert 'conservation gate failed' in str(error)
                else:
                    raise AssertionError('Overlapping fixture published')
            assert index_path.read_bytes() == before
            assert all(digest(OUT / p['path']) == p['sha256'] for p in index['parts'])
            # A geographically mixed run must leave the previous manifest and
            # its immutable parts intact, just like a conservation failure.
            part.write_text(json.dumps({'features': features}))
            with patch.object(subprocess, 'check_output', side_effect=['0' * 64, '1' * 64]), contextlib.redirect_stdout(io.StringIO()):
                try:
                    prepare(2020)
                except ValueError as error:
                    assert 'Footprints changed during execution' in str(error)
                else:
                    raise AssertionError('Concurrent footprint change published')
            assert index_path.read_bytes() == before
            assert all(digest(OUT / p['path']) == p['sha256'] for p in index['parts'])
        finally:
            ROOT, CACHE, OUT = original_paths
    print('PASS: real synthetic source preparation, estimate contracts, immutable assets and failed-run publication rollback')


def prepare(epoch):
    if epoch not in range(1975, 2031, 5):
        raise ValueError('Only published five-year epochs are supported')
    CACHE.mkdir(exist_ok=True)
    OUT.mkdir(exist_ok=True)
    algorithm_sha = digest(pathlib.Path(__file__))
    archive = CACHE / f'{epoch}.zip'
    if not archive.exists():
        raise FileNotFoundError(f'Download the actual native archive into {archive}; no silent network download')
    archive_sha = digest(archive)
    with zipfile.ZipFile(archive) as z:
        files = [n for n in z.namelist() if n.lower().endswith('.tif')]
        if len(files) != 1:
            raise ValueError('Expected one native global GeoTIFF')
        raster = CACHE / pathlib.Path(files[0]).name
        # Re-extract from the pinned archive rather than trusting a same-length
        # cached file. ZipFile verifies the member CRC on full read; only a
        # completed payload atomically replaces the working raster.
        pending_raster = raster.with_suffix(raster.suffix + '.pending')
        with z.open(files[0]) as src, pending_raster.open('wb') as target:
            while block := src.read(1024 * 1024):
                target.write(block)
        pending_raster.replace(raster)
    raster_sha = digest(raster)
    footprint_hash = subprocess.check_output(['node', 'scripts/stamp-prepared.mjs', '--hash'], cwd=ROOT, text=True).strip()
    staging = CACHE / f'staging-{epoch}-{algorithm_sha[:16]}-{footprint_hash[:16]}'
    staging.mkdir(exist_ok=True)
    part_paths = json.loads((ROOT / 'data/world-index.json').read_text())['parts']
    publication_rows = []
    summaries = []
    ids = set()
    by_owner = collections.defaultdict(lambda: {'locations': 0, 'allocated_population': 0., 'supported_values': 0})
    projection = Transformer.from_crs('EPSG:4326', 'ESRI:54009', always_xy=True)
    source_status = 'projection' if epoch > 2020 else 'modeled-estimate'
    proof_path = CACHE / f'allocated-weights-{epoch}.f32'
    source_url = f'https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/GHS_POP_GLOBE_R2023A/GHS_POP_E{epoch}_GLOBE_R2023A_54009_1000/V1-0/GHS_POP_E{epoch}_GLOBE_R2023A_54009_1000_V1_0.zip'
    last = time.monotonic()
    with rasterio.open(raster) as dataset:
        if dataset.crs.to_authority() != ('ESRI', '54009') or dataset.transform.a != 1000 or dataset.transform.e != -1000 or dataset.nodata != -200:
            raise ValueError(f'Unexpected native source grid {dataset.crs}, {dataset.transform}, {dataset.nodata}')
        proof = np.memmap(proof_path, dtype=np.float32, mode='w+', shape=(dataset.height, dataset.width))
        proof[:] = 0
        for part_path in part_paths:
            features = json.loads((ROOT / 'data' / part_path).read_text())['features']
            records = []
            for feature in features:
                properties = feature['properties']
                identity = properties['id']
                if identity in ids:
                    raise ValueError('Duplicate location identity')
                ids.add(identity)
                geometry = canonical(shape(feature['geometry']))
                population = covered = total = zeros = 0.
                for piece in polygons(geometry):
                    if piece.is_empty:
                        continue
                    # Adaptively densify only genuinely curved projected source edges.
                    projected = make_valid(project_piece(piece, projection))
                    for p in polygons(projected):
                        if p.is_empty:
                            continue
                        if not all(math.isfinite(v) for v in p.bounds):
                            raise ValueError(f'Nonfinite projected land footprint for {identity}')
                        value, area, zero_area = allocate(p, dataset, proof)
                        population += value
                        covered += area
                        zeros += zero_area
                        total += p.area
                coverage = min(1., covered / total) if total else 0.
                value = round(population) if coverage >= MIN_SOURCE_COVERAGE else None
                record = {'id': f'ghsl:{epoch}:{identity}:population', 'location_id': identity, 'attribute': 'population', 'value': value,
                    'category_id': None, 'source_id': f'ghsl:population:R2023A:E{epoch}', 'source': 'GHSL GHS-POP R2023A', 'source_url': SOURCE_DOI,
                    'valid_from': epoch, 'valid_to': epoch + 1, 'method': 'estimate', 'status': 'estimate' if value is not None else 'unknown', 'is_example': 0,
                    'metadata': {'license': 'CC BY 4.0', 'attribution': 'European Union / JRC; Schiavina, Freire and MacManus. Adapted by WorldAtlas.',
                       'source_year': epoch, 'source_status': source_status, 'estimate': True, 'assignment_method': 'equal-area-cell-overlap', 'source_epoch_only': True, 'no_interpolation': True,
                       'native_grid': 'World Mollweide ESRI:54009; 1000 m; counts per cell, not density', 'coverage': round(coverage, 12),
                       'projection_chord_error_metres': PROJECTION_CHORD_ERROR_METRES,
                       'partial_supported_population': round(population, 9), 'precision': 'Modeled count rounded to whole people for storage; not census precision',
                       'coverage_threshold': MIN_SOURCE_COVERAGE, 'unsupported_reason': None if value is not None else 'Source NoData or outside grid covers part of the applicable location land',
                       'methodology': METHODOLOGY, 'product_notice': LICENSE_URL, 'source_sha256': archive_sha, 'raster_sha256': raster_sha,
                       'method': 'Full native-cell counts split by exact intersection area with location land in equal-area coordinates; remainder unassigned. No count×cell-area multiplication or nearest-cell assignment.'}}
                records.append(record)
                summaries.append({'id': identity, 'land_area_m2': total, 'supported_area_m2': covered, 'zero_model_area_m2': zeros, 'allocated_population': population, 'coverage': coverage})
                owner = by_owner[properties['reference_owner']]
                owner['locations'] += 1
                owner['allocated_population'] += population
                owner['supported_values'] += value is not None
                if time.monotonic() - last > 15:
                    print(f'Epoch {epoch}: inspected {len(ids)} locations', flush=True)
                    last = time.monotonic()
            raw = json.dumps(records, separators=(',', ':'), ensure_ascii=False).encode()
            content = gzip.compress(raw, mtime=0)
            part_sha = hashlib.sha256(content).hexdigest()
            name = f'epoch-{epoch}-{pathlib.Path(part_path).stem}-{part_sha}.json.gz'
            (staging / name).write_bytes(content)
            publication_rows.append({'path': name, 'records': len(records), 'bytes': len(content), 'sha256': part_sha})
            print(f'Epoch {epoch}: wrote {name}, {len(ids)} total locations', flush=True)
        source_total = allocated_total = 0.
        max_weight = 0.
        overlapping_cells = 0
        nodata_cells = 0
        for row in range(0, dataset.height, 256):
            height = min(256, dataset.height - row)
            values = dataset.read(1, window=Window(0, row, dataset.width, height))
            valid = np.isfinite(values) & (values >= 0)
            if np.any(~valid & (values != dataset.nodata)):
                raise ValueError('Unexpected negative or nonfinite source population value in global proof')
            weights = np.asarray(proof[row:row + height], dtype=np.float64)
            source_total += float(np.sum(values[valid], dtype=np.float64))
            allocated_total += float(np.sum(np.where(valid, values, 0) * weights, dtype=np.float64))
            max_weight = max(max_weight, float(weights.max()))
            overlapping_cells += int((weights > 1 + 3e-6).sum())
            nodata_cells += int((~valid).sum())
        proof.flush()
        del proof
        direct_total = sum(s['allocated_population'] for s in summaries)
        conservation_gate(source_total, allocated_total, direct_total, max_weight, overlapping_cells)
        native_grid = {'width': dataset.width, 'height': dataset.height, 'transform': list(dataset.transform), 'crs': dataset.crs.to_string(), 'nodata': dataset.nodata, 'dtype': dataset.dtypes[0]}
    receipt = {'version': 1, 'epoch': epoch, 'source_url': source_url, 'archive_sha256': archive_sha, 'raster_sha256': raster_sha, 'native_grid': native_grid,
        'footprints_sha256': footprint_hash, 'locations': len(ids), 'supported_values': sum(s['coverage'] >= MIN_SOURCE_COVERAGE for s in summaries),
        'source_total_population': source_total, 'allocated_population_from_cell_ledger': allocated_total, 'allocated_population_from_location_summaries': direct_total,
        'unassigned_population': source_total - allocated_total, 'unassigned_reason': 'Source population outside current atlas land, fractional coastal cells, source/geographic gaps and excluded Antarctica; no forced reassignment.',
        'maximum_cell_allocated_share': max_weight, 'overallocated_cells': overlapping_cells, 'source_nodata_cells': nodata_cells,
        'proof_precision': 'Float32 per-cell allocation ledger, independently compared to Float64 per-location totals; max allowed cell overage 3e-6, mass difference max(1 person, source total×5e-8).',
        'by_reference_owner': dict(by_owner), 'locations_summary': summaries,
        'algorithm_sha256': algorithm_sha, 'source_license': 'CC BY 4.0', 'license_url': LICENSE_URL, 'methodology_url': METHODOLOGY,
        'limitations': ['Modeled gridded residential population, not a historical census.', 'Areal allocation assumes uniform population within each native cell.', 'Modern fixed territories applied at the source epoch; no claim of historical boundary identity.', 'No rank/habitation inference; no unsupported-date carry-forward.']}
    if digest(pathlib.Path(__file__)) != algorithm_sha:
        raise ValueError('Preparation algorithm changed during execution; rerun before publication')
    if subprocess.check_output(['node', 'scripts/stamp-prepared.mjs', '--hash'], cwd=ROOT, text=True).strip() != footprint_hash:
        raise ValueError('Footprints changed during execution; rerun before publication')
    receipt_content = gzip.compress(json.dumps(receipt, separators=(',', ':')).encode(), mtime=0)
    receipt_name = f'epoch-{epoch}-receipt-{hashlib.sha256(receipt_content).hexdigest()}.json.gz'
    (staging / receipt_name).write_bytes(receipt_content)
    index_path = OUT / 'index.json'
    index = json.loads(index_path.read_text()) if index_path.exists() else {'version': 1, 'epochs': [], 'parts': [], 'source': 'GHSL GHS-POP R2023A', 'license': 'CC BY 4.0', 'source_url': SOURCE_DOI}
    index['epochs'] = [e for e in index['epochs'] if e['year'] != epoch] + [{'year': epoch, 'valid_from': epoch, 'valid_to': epoch + 1, 'status': source_status, 'receipt': receipt_name, 'locations': len(ids), 'supported_values': receipt['supported_values']}]
    index['parts'] = [p for p in index['parts'] if p.get('epoch') != epoch] + [p | {'epoch': epoch} for p in publication_rows]
    index.update(footprints_sha256=footprint_hash, locations=len(ids))
    source = source_contract(epoch, archive_sha, source_url)
    sources_path = OUT / 'sources.json'
    sources = json.loads(sources_path.read_text()) if sources_path.exists() else []
    previous_sources = [s for s in sources if s['id'] == source['id']]
    if previous_sources and previous_sources != [source]:
        raise ValueError('Stable population source ID collision; source revision requires a new identity')
    index['sources'] = [s for s in sources if s['id'] != source['id']] + [source]
    # Immutable content-addressed parts preserve a previous successful export if
    # this run is interrupted. The manifest is the final atomic commit point.
    for name in [p['path'] for p in publication_rows] + [receipt_name]:
        destination = OUT / name
        if destination.exists():
            if digest(destination) != digest(staging / name):
                raise ValueError('Content-addressed population asset collision')
        else:
            shutil.copyfile(staging / name, destination)
    pending_index = OUT / 'index.json.pending'
    pending_index.write_text(json.dumps(index, indent=2) + '\n')
    pending_sources = OUT / 'sources.json.pending'
    pending_sources.write_text(json.dumps(index['sources'], indent=2) + '\n')
    pending_sources.replace(sources_path)
    pending_index.replace(index_path)
    proof_path.unlink()
    print(json.dumps({k: v for k, v in receipt.items() if k not in ['by_reference_owner', 'locations_summary']}, indent=2), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--epoch', type=int, default=2020)
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if args.self_test:
        self_test()
    else:
        prepare(args.epoch)
