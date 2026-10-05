# Native monthly water diagnostics

`scripts/diagnose-geographic-water.py` compares retained gap components with original
dated JRC MonthlyHistory GeoTIFF bytes. It is a diagnostic adapter for issue #946.
It does not repair geography or approve a water exception in the integration gate.

The input registry pins the whole original files, source months, licence, retrieval
receipts, original component-file and feature hashes, component evaluation commit,
original geography evaluation context, anchors and any explicit pilot bounds.
Original files are retained unchanged, rather than relabelling a crop as an original.
The raster's actual CRS, affine transform, extent, dimensions, byte type and masks
are checked before bounded window reads. No resampling or coordinate snapping occurs.

Counts describe native pixel centres strictly inside the sampled continuous shape.
Centres on its boundary or in holes are excluded. A subpixel seam may contain no
centres at all; this remains unknown. An anchor's containing source pixel is recorded
separately, including whether that pixel's centre lies inside the gap.

Raw classes and conditional interpretation are both retained. The published guide
describes monthly-history values as 0 = no observations, 1 = not water, 2 = water.
Its detailed monthly schema is stated for Earth Engine; the FTP TIFF files lack
embedded class labels. Applying that schema to their conforming byte values is an
explicit inference, not independent confirmation of FTP encoding. Unexpected values
or masks stop processing. No-observation values are never counted as dry land.

The FTP directory label `VER5-0` is preserved verbatim. It is not silently renamed
to the newer summary product `GSW v1.5`. The dated source files used here precede
that summary release. New summary occurrence and older observation-count metadata
are not combined to manufacture confidence. The retrieved guide and data-access
page retain the provider's update and known-error notes.

The Iran–Pakistan pilot samples one complete retained component, with January and
July 2017 observations. This matches the Iranian source's reference year but does
not establish the Pakistani source's 2019 conditions. The Portugal–Spain pilot
samples an explicit small area around the previously recorded anchor, with January
and July 2020 observations. Its full connected component crosses the native tile
boundary; unsampled portions remain unknown. Neither two-month pilot establishes
annual permanence, seasonality, current water extent or political ownership.

All component water statuses remain unknown. Mixed land/water pixels, narrow gaps,
unknown local registration error, unobserved cells and unsampled dates require
further evidence. The source's nominal resolution is approximately 30 metres;
this is not a certified local geolocation error bound. The guide explicitly notes
spatially variable offsets when combining Landsat collections, sometimes exceeding
one pixel. No hard offset bound is assumed here.

Run the controls with the committed Python preparation dependencies installed:

```sh
python -I -B test/geographic-water.py
```

Reproduction requires an immutable commit containing `inputs.json` and the original
source files. Pass the registry's actual whole-file bytes and SHA-256, and choose an
unused destination. The evidence manifest records the exact command and input commit.
Mutable working-tree source substitutions do not affect reads. Output overwrites,
oversized originals/windows, partial source coverage, unknown classes, changed native
grids and mismatched component hashes are rejected.

JRC original monthly files carry CC BY 4.0 in their retained `copyright.txt`.
Attribution: **Source: EC JRC/Google**. Dataset citation: Jean-François Pekel,
Andrew Cottam, Noel Gorelick and Alan S. Belward, *High-resolution mapping of global
surface water and its long-term changes*, Nature 540, 418–422 (2016),
doi:10.1038/nature20584. Diagnostic outputs are new derived artifacts; originals
and their hashes remain unchanged. Nearby location IDs inherited from the original
audit are investigation context, not certified adjacency or an assignment.
