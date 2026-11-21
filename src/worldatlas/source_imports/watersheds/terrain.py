"""Read the source's grid of heights and fill gaps from another elevation map."""
from dataclasses import dataclass
import math

import numpy as np
from osgeo import gdal, gdal_array
from pyproj import CRS, Transformer

gdal.UseExceptions()


@dataclass
class Grid:
    """Keep the heights and map positions of a rectangular piece of terrain.

    Args:
        elevation: Heights in metres, indexed by row and column.
        transform: GDAL values for the crop's top-left corner and cell steps.
        crs: The map's coordinate system. It tells us what x and y mean.
        secondary_cells: Number of primary heights filled from secondary terrain.
        native_origin: The transform for the full grid, when known.
        window_offset: Row and column where this crop starts in the full grid.
    """

    elevation: np.ndarray
    transform: tuple
    crs: str
    secondary_cells: int = 0
    native_origin: tuple | None = None
    window_offset: tuple = (0, 0)

    def cell_coordinates(self, rows, columns, center=True):
        """Find the map coordinates of a row and column.

        Row 0, column 0 is the first cell of the crop. Add half a cell in
        each direction to get its center instead of its top-left corner.

        Args:
            rows: Row indices, as a scalar or an array.
            columns: Column indices, with a shape compatible with rows.
            center: Whether integer indices denote cell centers or upper-left corners.

        Returns:
            The x and y coordinates in the grid's coordinate reference.
        """
        offset = .5 if center else 0.
        # Local (0, 0) in a crop starting at (100, 200) means full-grid
        # (100, 200). A different crop must get the same coordinates there.
        left, x_per_column, x_per_row, top, y_per_column, y_per_row = self.native_origin or self.transform
        rows, columns = rows + self.window_offset[0], columns + self.window_offset[1]
        return (left + (columns + offset) * x_per_column + (rows + offset) * x_per_row,
                top + (columns + offset) * y_per_column + (rows + offset) * y_per_row)


def read_native_elevation_crop(paths, bounds, *, bounds_crs=4326):
    """Crop aligned source tiles without changing their cell positions or values.

    If the crop limits already use the source grid's coordinates, use
    those limits directly. In an overlap, take the last usable height in
    the tile list.

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
    # If the crop starts partway through column 10, keep column 10.
    # Round the far edge outward too so we keep every cell the crop touches.
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
        native_column = round((actual[0] - origin[0]) / origin[1])
        native_row = round((actual[3] - origin[3]) / origin[5])
        # A tile may start 20 cells over. A shift of 20.5 would put its
        # cell centers between the primary grid's centers.
        if (actual[0], actual[3]) != (
            origin[0] + native_column * origin[1],
            origin[3] + native_row * origin[5],
        ):
            raise ValueError('primary tile origins are not aligned')
        column, row = native_column - col0, native_row - row0
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


def wrap_array_as_raster(values, grid):
    """Let GDAL write into an existing NumPy array at known map positions.

    Args:
        values: NumPy array with the terrain grid's shape.
        grid: Terrain coordinate reference and affine transform.

    Returns:
        An in-memory GDAL dataset. Changes GDAL makes appear in ``values``.
    """
    destination = gdal_array.OpenArray(values)
    destination.SetGeoTransform(grid.transform)
    destination.SetProjection(CRS.from_user_input(grid.crs).to_wkt())
    return destination


def align_raster_to_grid(paths, grid, *, resampling='bilinear'):
    """Read a second map using the primary grid's cell positions.

    Args:
        paths: Raster dataset paths to align.
        grid: Destination grid and coordinate reference.
        resampling: How GDAL picks a value at each position. Average nearby
            heights with bilinear sampling. For codes such as land and
            water, use nearest-neighbor to keep a real code.

    Returns:
        The aligned array, with NaN where the sources provide no value.
    """
    values = np.full(grid.elevation.shape, np.nan)
    destination = wrap_array_as_raster(values, grid)
    destination.GetRasterBand(1).SetNoDataValue(np.nan)
    gdal.Warp(destination, [str(path) for path in paths],
              resampleAlg=resampling, dstNodata=np.nan)
    return values


def prepare_elevation_grid(primary, bounds, secondary=(), height_offset=None, *, bounds_crs=4326):
    """Read primary terrain and fill gaps from secondary terrain.

    Two maps can measure height from different zero levels. If the second
    map says 100 m and its offset here is +3 m, the height we use is 103 m.
    Keep the primary map's heights wherever they already exist.

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
    grid = read_native_elevation_crop(primary, bounds, bounds_crs=bounds_crs)
    missing = ~np.isfinite(grid.elevation)
    grid.secondary_cells = int(missing.sum())
    if missing.any() and secondary:
        values = align_raster_to_grid(secondary, grid)
        if height_offset is not None:
            values += align_raster_to_grid([height_offset], grid)
        grid.elevation[missing] = values[missing]
    remaining = int((~np.isfinite(grid.elevation)).sum())
    if remaining:
        raise ValueError(f'elevation sources leave {remaining} missing cells')
    return grid
