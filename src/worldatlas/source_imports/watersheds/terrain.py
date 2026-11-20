"""Read native elevation grids and fill missing cells from aligned real data."""
from dataclasses import dataclass
import math

import numpy as np
from osgeo import gdal, gdal_array
from pyproj import CRS, Transformer

gdal.UseExceptions()


@dataclass
class Grid:
    """Hold a terrain crop and the information needed to locate its cells.

    Args:
        elevation: Heights in metres, indexed by row and column.
        transform: GDAL coefficients that map crop indices to source coordinates.
        crs: Coordinate reference of the source raster.
        secondary_cells: Number of primary heights filled from secondary terrain.
        native_origin: The same coefficients for the uncropped reference grid, if known.
        window_offset: Row and column of the crop's first cell in that grid.
    """

    elevation: np.ndarray
    transform: tuple
    crs: str
    secondary_cells: int = 0
    native_origin: tuple | None = None
    window_offset: tuple = (0, 0)

    def coordinates(self, rows, columns, center=True):
        """Convert crop-relative grid positions to source coordinates.

        Args:
            rows: Row indices, as a scalar or an array.
            columns: Column indices, with a shape compatible with rows.
            center: Whether integer indices denote cell centers or upper-left corners.

        Returns:
            The x and y coordinates in the grid's coordinate reference.
        """
        offset = .5 if center else 0.
        # Use the common origin so overlapping crops compute identical coordinates.
        x, a, b, y, d, e = self.native_origin or self.transform
        rows, columns = rows + self.window_offset[0], columns + self.window_offset[1]
        return (x + (columns + offset) * a + (rows + offset) * b,
                y + (columns + offset) * d + (rows + offset) * e)


def read_native(paths, bounds, *, bounds_crs=4326):
    """Crop aligned source tiles without changing their cell positions or values.

    Native projected rectangles avoid enlarging a crop through a round trip
    through longitude and latitude. Later valid tiles take precedence in the
    selected source order.

    Args:
        paths: Aligned primary raster dataset paths, in compositing order.
        bounds: West, south, east, and north limits in the bounds coordinate reference.
        bounds_crs: Coordinate reference of those limits, WGS84 by default.

    Returns:
        The native grid window, with missing heights represented by NaN.

    Raises:
        ValueError: The requested bounds or primary tile grid is invalid.
    """
    if not paths or len(bounds) != 4 or not np.isfinite(bounds).all():
        raise ValueError('source tiles and finite analysis bounds are required')
    west, south, east, north = bounds
    bounds_crs = CRS.from_user_input(bounds_crs)
    if not (west < east and south < north):
        raise ValueError('invalid analysis bounds')
    if bounds_crs.equals(CRS.from_epsg(4326), ignore_axis_order=True) and not (
            -180 <= west < east <= 180 and -90 <= south < north <= 90):
        raise ValueError('invalid WGS84 analysis bounds')
    datasets = [gdal.Open(str(path)) for path in paths]
    first = datasets[0]
    crs = first.GetProjection()
    reference = CRS.from_user_input(crs)
    origin = first.GetGeoTransform()
    if not np.isfinite(origin).all() or origin[1] <= 0 or origin[5] >= 0 or origin[2] or origin[4]:
        raise ValueError('a finite north-up native grid is required')
    left, bottom, right, top = Transformer.from_crs(
        bounds_crs, reference, always_xy=True).transform_bounds(*bounds, densify_pts=21, errcheck=True)
    # Round outward to include every native cell intersecting the requested area.
    col0 = math.floor((left - origin[0]) / origin[1])
    col1 = math.ceil((right - origin[0]) / origin[1])
    row0 = math.floor((top - origin[3]) / origin[5])
    row1 = math.ceil((bottom - origin[3]) / origin[5])
    transform = (origin[0] + col0 * origin[1], origin[1], 0.,
                 origin[3] + row0 * origin[5], 0., origin[5])
    elevation = np.full((row1 - row0, col1 - col0), np.nan, dtype='float64')
    for dataset in datasets:
        actual = dataset.GetGeoTransform()
        if CRS.from_user_input(dataset.GetProjection()) != reference or actual[1:3] != origin[1:3] or actual[4:] != origin[4:]:
            raise ValueError('primary tiles must share one native grid and CRS')
        offsets = ((actual[0] - transform[0]) / origin[1],
                   (actual[3] - transform[3]) / origin[5])
        # This checks tile alignment, not numerical ties in drainage routing.
        if not np.allclose(offsets, np.rint(offsets), rtol=0, atol=1e-7):
            raise ValueError('primary tile origins are not aligned')
        column, row = map(round, offsets)
        x0, y0 = max(0, column), max(0, row)
        x1 = min(elevation.shape[1], column + dataset.RasterXSize)
        y1 = min(elevation.shape[0], row + dataset.RasterYSize)
        if x1 <= x0 or y1 <= y0:
            continue
        band = dataset.GetRasterBand(1)
        values = band.ReadAsArray(x0 - column, y0 - row, x1 - x0, y1 - y0)
        usable = band.GetMaskBand().ReadAsArray(x0 - column, y0 - row, x1 - x0, y1 - y0) != 0
        usable &= np.isfinite(values)
        elevation[y0:y1, x0:x1][usable] = values[usable]
    return Grid(elevation, transform, crs, native_origin=origin, window_offset=(row0, col0))


def raster_on_grid(values, grid):
    """Give GDAL a writable view of a NumPy raster on the terrain grid.

    Args:
        values: NumPy array with the terrain grid's shape.
        grid: Terrain coordinate reference and affine transform.

    Returns:
        An in-memory GDAL dataset backed by the supplied array.
    """
    destination = gdal_array.OpenArray(values)
    destination.SetGeoTransform(grid.transform)
    destination.SetProjection(CRS.from_user_input(grid.crs).to_wkt())
    return destination


def align(paths, grid, *, resampling='bilinear'):
    """Read other raster values at the primary grid's cell positions.

    Args:
        paths: Raster dataset paths to align.
        grid: Destination grid and coordinate reference.
        resampling: GDAL sampling method. Use nearest-neighbor for category codes.

    Returns:
        The aligned array, with NaN where the sources provide no value.
    """
    values = np.full(grid.elevation.shape, np.nan)
    destination = raster_on_grid(values, grid)
    destination.GetRasterBand(1).SetNoDataValue(np.nan)
    gdal.Warp(destination, [str(path) for path in paths],
              resampleAlg=resampling, dstNodata=np.nan)
    return values


def prepare(primary, bounds, secondary=(), height_offset=None, *, bounds_crs=4326):
    """Read primary terrain and fill gaps from secondary terrain.

    For EGM2008 heights converted to WGS84 ellipsoidal heights, the offset is
    the EGM2008 geoid undulation. Its source is selected and cataloged normally.

    Args:
        primary: Aligned native raster paths in compositing order.
        bounds: West, south, east, and north limits for the crop.
        secondary: Optional raster paths supplying missing heights.
        height_offset: Optional raster of offsets in metres to add to secondary heights.
        bounds_crs: Coordinate reference of the requested bounds.

    Returns:
        The primary grid with finite heights and a count of filled cells.

    Raises:
        ValueError: The combined terrain sources leave cells without a finite height.
    """
    grid = read_native(primary, bounds, bounds_crs=bounds_crs)
    missing = ~np.isfinite(grid.elevation)
    grid.secondary_cells = int(missing.sum())
    if missing.any() and secondary:
        values = align(secondary, grid)
        if height_offset is not None:
            values += align([height_offset], grid)
        grid.elevation[missing] = values[missing]
    remaining = int((~np.isfinite(grid.elevation)).sum())
    if remaining:
        raise ValueError(f'elevation sources leave {remaining} missing cells')
    return grid
