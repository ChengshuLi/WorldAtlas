# Fixed-grid resolution and coverage review

All **49,614 current location footprints** were compiled globally at four independent fixed canonical resolutions. Every candidate uses actual polygon cell centers, even-odd holes and the existing minimum-location-index tie rule. The grid does not depend on viewport zoom, pan or resize.

The coarsest tested candidate representing every current location with no location above the existing **25% area-distortion screen** is **canonical zoom 10 (262,144 cells per side; about 153 m at the equator)**. This is a numerical selection for current geometries, not approval of geographic source semantics or permission to activate a larger renderer.

## Complete-world measured results

| Canonical zoom | Width | Represented | Missing | Existing high-distortion screen | All-location WGS84 errors >25% | Runs | Packed bytes | Gzip bytes | Preparation seconds | Peak RSS bytes |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 7 | 32,768 | 49,561 | 53 | 123 | 211 | 3,502,067 | 56,295,216 | 10,185,804 | 8.19 | 1,063,202,816 |
| 8 | 65,536 | 49,604 | 10 | 46 | 59 | 7,115,157 | 114,366,800 | 20,373,654 | 11.47 | 1,393,565,696 |
| 9 | 131,072 | 49,612 | 2 | 8 | 10 | 14,344,942 | 230,567,648 | 40,932,995 | 18.74 | 1,921,593,344 |
| 10 | 262,144 | 49,614 | 0 | 0 | 0 | 28,807,323 | 463,014,320 | 82,287,340 | 31.12 | 2,818,203,648 |

The existing distortion screen applies to source projected areas of at least one candidate cell. The all-location screen also includes sub-cell territories: it finds 211 / 59 / 10 / 0 locations above 25% at zooms 7 / 8 / 9 / 10. Zoom 10’s largest WGS84 area error is **22.4364%**. Geographic areas use the validated WGS84 ellipsoid surface integral along original longitude/latitude edges, including antimeridian normalization. Each raster row receives its exact ellipsoidal latitude-strip area; equal physical area per Mercator cell is never assumed.

All 32,768 baseline rows and all 3,502,067 packed runs match the shipped canonical zoom-7 table exactly. Therefore the independent sparse compiler reproduces the ownership of every existing canonical cell globally, including holes and overlaps. Each finer candidate repeats complete polygon ownership preparation rather than extrapolating the earlier missing-location list. Preparation timings include source loading, hashing, sparse compilation, packing and gzip; they exclude one-time Python source-area preparation and browser loading. Each candidate runs sequentially in its own bounded Node process.

## Finer center grids are not nested

Zoom 8 removes 43 baseline omissions but four previously represented units disappear: Georgia–Puget Basin, El Marsa, Kepulauan Seribu and Kalayaan. Their cell-center alignment changes. Bajo Nuevo Bank is represented at zoom 8, disappears at zoom 9 and returns at zoom 10. Consequently a finer grid cannot be certified by only checking the old 53 missing polygons.

The report independently investigates all **57 distinct missing IDs** across complete candidates at fixed zooms up to 14, stopping after at least 64 isolated interior hits. Isolated component hits are explicitly not collision-resolved global ownership at uncompiled resolutions. No finer full-world candidate was needed once zoom 10 met the current representation screen.

## Original version-1 device and hosting measurements

| Zoom | 2048-wide run-texture height | Fits MAX_TEXTURE_SIZE 2048 / 4096 / 8192 / 16384 | Estimated artifact after grid replacement | Headroom below 256 MiB |
| ---: | ---: | --- | ---: | ---: |
| 7 | 1,710 | yes / yes / yes / yes | 182,537,965 | 85,897,491 |
| 8 | 3,475 | no / yes / yes / yes | 192,725,815 | 75,709,641 |
| 9 | 7,005 | no / no / yes / yes | 213,285,156 | 55,150,300 |
| 10 | 14,067 | no / no / no / yes | 254,639,501 | 13,795,955 |

Measured existing Worker/client/migration package: **182,537,965 bytes**. Estimates replace the 10,185,804-byte existing grid gzip with candidate gzip and leave other measured assets intact. Chunking remains 4 MiB uncompressed integer words per file, with actual compressed chunk hashes and maximum part sizes recorded; no single candidate part approaches the 25 MiB asset-file limit. Current original ownership-history assets are redundant for the normal runtime client and could be externalized separately, but this audit does not mutate packaging.

A real local headless Chromium WebGL2 software-GPU probe returned **MAX_TEXTURE_SIZE 8192** and **MAX_ARRAY_TEXTURE_LAYERS 2048**. This is an execution-workspace result, not a physical mobile-device benchmark. Zoom 10’s existing run texture would be 14,067 pixels tall and therefore **fails our observed renderer limit**. Its 463 MB packed CPU table and comparable GPU allocation also require mobile memory/loading benchmarks. CSS mobile emulation cannot establish physical mobile memory capacity.

The original shader hardcoded a 32,768-world bound. Version 2 now passes world size and coordinate bits as uniforms, while render transforms still import fixed GRID_ZOOM. Those transforms must change consistently before activating another canonical resolution. No viewport-dependent re-pixelization, arbitrary cell assignment, polygon inflation or navigation-time ownership texture uploads are proposed.

## Implemented compact renderer and measured transports

Version 2 stores each run in two Uint32 words rather than four: inclusive start/end coordinates occupy the low coordinate bits; the owner ID is split across the high bits. Two runs share one RGBA32UI texel. Both the CPU and GPU continue reading version-1 assets. All 3,502,067 baseline runs roundtrip exactly; 14,008,268 boundary/gap cell queries agree. Real framebuffer checks cover holes, odd run counts, high owner IDs and the maximum zoom-10 coordinates. A real historical case, South Dublin in 1444, renders all 368 sampled canonical cells with its resolved England owner despite only 84.5% source-polygon coverage.

| Zoom | Compact CPU ownership bytes | Compact GPU padded bytes | Run texture height | Plain compact gzip | Byte-shuffle gzip | Row-varint gzip | Shuffled browser load/decode ms | GPU upload phase ms |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 7 | 28,278,680 | 28,278,784 | 855 | 11,240,369 | 6,406,163 | 7,337,348 | 229 | 74 |
| 9 | 115,808,112 | 115,834,880 | 3,503 | 50,294,718 | 24,404,257 | 31,084,349 | 506 | 111 |
| 10 | 232,555,736 | 232,587,264 | 7,034 | 105,291,797 | 47,575,630 | 63,444,663 | 1,000 | 200 |

These are actual globally compiled ownership assets, not size extrapolations. The byte-shuffle transport groups each little-endian byte plane before gzip; the row-local varint alternative encodes unsigned start gaps and lengths, plus zigzag owner deltas, resetting at row and chunk boundaries. **Byte shuffle wins at every tested resolution**. Every decoded word was compared exactly: 7,069,670 / 28,952,028 / 58,138,934 words at 7 / 9 / 10. Manifest parts optionally specify `encoding: 'byte-shuffle'` or `'row-varint'`; offsets and word counts describe the decoded compact arrays. Rows load before dependent varint runs.

Actual Chromium WebGL uploads at all three resolutions fit observed MAX_TEXTURE_SIZE 8192, return zero errors and render the sampled source interiors correctly. Repeated desktop and mobile-viewport navigation performs zero ownership uploads. Median complete-frame times, measured with synchronous framebuffer readback, were 304 / 228.4 / 197.9 ms for 1280×720 and 47.9 / 31.5 / 33.7 ms for 390×844 at 7 / 9 / 10. These software-GPU measurements include an expensive synchronization step and **do not establish physical mobile/desktop frame rates or memory capacity**. Submission times alone were 0–0.2 ms and must not be described as completed frames. Warm CPU fallback ownership sampling took about 4–5 ms desktop and 1–2 ms mobile viewport; those measurements exclude canvas color composition.

Observed JS heap totals were approximately 92 / 342 / 521 MB, including concurrent decompression buffers and unrelated runtime allocations; permanent ownership arrays use the compact bytes above. A physical mobile benchmark remains open. Compact zoom 10 fits a texture limit of 8192 but still does not fit 4096; CPU fallback remains necessary on those devices.

The later locally built baseline artifact measured 203,395,418 bytes with ordinary compact zoom-7 gzip. Replacing only that ownership payload with byte-shuffled zoom 10 estimates **239,730,679 bytes**, leaving **28,704,777 bytes** below 256 MiB. Byte-shuffled zoom 9 estimates 216,559,306 bytes, leaving 51,876,150 bytes. These are dated estimates, not a hosting gate for future builds; rerun the actual artifact-size check after integration and source changes. Externalizing redundant source archives can add further headroom. No resolution was activated by this benchmark.

Reproduce compact assets and rendering with `node test/compact-ownership-benchmark.mjs`; add zoom 9 with `--candidate --zoom=9`. Run `node test/ownership-transport-benchmark.mjs` for complete-word transport comparisons, then `node test/compact-ownership-benchmark.mjs --assets-only --zooms=7,9,10 --transport=byte-shuffle` for actual browser loading and framebuffer measurements. Focused correctness checks: `node --test test/pixel-ownership.test.mjs test/compact-ownership.test.mjs`.

## Source defects remain independent

* Borama’s original source area is about 1,575 km², while the current political-reference mask leaves about 1.24 km². A finer grid represents the clipped remnant; it cannot recover erased geography.
* Namibia’s 2007 source contains suspicious northern names on tiny southern footprints. Hakahana’s urban role must be reviewed separately; small area alone does not prove a source defect. Source label/coordinate and constituency roles need correction before semantic closure.
* Marshall island original/current footprints differ substantially; original polygons may include marine water, so replacing them solely from area ratios is unjustified. Validate named atoll dry land and full subordinate-island coverage.
* Vatican’s original low-resolution reference is only about 0.0122 km², and the current remnant is about 0.0106 km². Rendering that remnant at zoom 10 does not certify actual territorial extent. Attempts to retrieve independent Vatican geography pages returned 403 and were not counted as evidence.

Source-comparison records preserve exact IDs, source URLs, original/current areas and retained-area ratios. The prior country/reference coverage report explicitly does not claim exact coastline completeness. Zero ownership ID means **water or a source coverage gap**, never unclaimed land; separating every gap from ocean requires an independently approved coastline/water reference. Current polygon ownership is exhaustive, while that source-land completeness task remains open.

## Reproduce and validate

Run `node scripts/audit-grid-resolutions.mjs --zooms=7,8,9,10 --isolated-max-zoom=14`. The script prepares candidates one at a time, stores temporary bounded results in `.cache/grid-resolution-review`, and writes [grid-resolution-review.json](../data/grid-resolution-review.json). It does not change the live grid, source geometry or renderer. Use `--aggregate-only` only with current footprint-hash-matching candidate receipts.

The report stores each location ID once, aligned source area arrays and candidate cell-count/geographic-area arrays; every location therefore has a recorded result at every candidate. Exact missing/high-distortion records, packed chunk hashes, baseline-equivalence evidence and source-algorithm hashes remain inspectable.

Input footprint SHA256: `1c8c1584520d7360375c8ac79f12fe840dd8a47efb10f3d05c8517689667dd58`. Global geographic semantic approval is still incomplete; the selected candidate remains **deployment-pending** until source review and renderer/device validation are resolved.
