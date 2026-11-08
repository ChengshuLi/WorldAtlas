# Land seed and verifier through Python APIs

The active seed rasterizer now uses GDAL's Python API, independent per-thread
OGR datasets, and a general NumPy interval composer. Full-width strip affine
transforms, original strip ordering, polygon validation, witness guards, source
pins, selected-root coverage, exact populations and output RLE are retained.
The transition composer examines only bit changes intersecting selected component
intervals. Whole-component rules stay interval operations. It contains no
current-region, root-ID, label-assignment or global-grid special case.

The old custom C++ seed helper and tile verifier are removed. The verifier now
constructs expected canonical tile records independently from complete seed RLE
using NumPy tile-row bands. Every offset, row endpoint and category is validated,
then all tile files must match exactly. Unexpected/noncanonical files fail.
The verifier source is part of checkpoint identity; a retired binary identity
cannot silently resume under the new implementation.

Source recovery is complete: the ordinary regional producer and fresh Python
water/terminal closure checkers recreated both complete pinned polygons in
16.7991 seconds. The Europe polygon file is 1,752,831 bytes with SHA-256
412d7579077df4d9acbac543db5a20c03faa52d85055102165f806029035f9b9.
The North America polygon is 716,419 bytes with SHA-256
cb9dadc9fa518f89788ae66d537a4a1f2c177908aaa36d3ffa243039c599aa5a.
Stored proofs were not substituted for fresh checks. The existing local-derived
snapshot and byte-equivalent historical physical streams remain explicitly
provisional; this is not provider authentication or geographic acceptance.

Tiny tests cover independent dense cell and tile oracles, randomized component
layouts, arbitrary rule order and bits, zero/maximum uint32 roots, empty rows,
all categories, nonbinary steps, exact-center polygon vertices, different strip
sizes and thread counts, malformed offsets, missing roots, corruption,
noncanonical names and occupied dangling output symlinks. Runtime tests forbid
process launches and ctypes bridges. All old reviewed producer freezes remain
unchanged, so source changes do not silently acquire reviewed status.

Complete-world parity and isolated serial/parallel timing for this new seed
producer and verifier are **pending** the physical worker's measurement release.
The reusable `prepare_seed_raster_replay.py` and `benchmark_seed_raster.py` tools
record source/code pins and exact UTC intervals, compare all seed output hashes
and populations, and never launch the whole user-owned pipeline. No new seed
speed ratio, final-land artifact or end-to-end result is claimed here.
