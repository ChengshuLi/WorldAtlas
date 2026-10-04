# IBC-restored BC–Washington reproduction vintage

Created 2026-10-04 as a superseding source-backed receipt for issue #660. The earlier `assessment.json`, `verification.json`, controls, and original #657 packet remain unchanged. This vintage resolves the source-availability limitation recorded in the initial packet, while the reason for the measured coastal offset remains unresolved.

## Source and retention

The International Boundary Commission (IBC) US–Canada Boundary v1.3 archive was downloaded on 2026-10-04 from its official direct endpoint: <https://www.internationalboundarycommission.org/uploads/shapefile/us-canada-boundary-v1-3.zip>. The direct endpoint returned HTTP 200. The official downloads index returned HTTP 404 at the same time, but the direct archive endpoint worked. The downloaded archive was 258,764 bytes and matched SHA-256 `eb327459528b87cbc27e55ccc6bfd6982562c75559823a00b6dc50c04abcaab1` before it was opened. Its bundled metadata dates the source to 2018-04-20 and identifies section 25 as “49th Parallel (Pacific to Columbia Valley).”

Bundled metadata says the dataset is for mapping only; the U.S. metadata states © International Boundary Commission, all rights reserved. The archive was used temporarily and is not retained or redistributed. To repeat this work, download only from the official direct endpoint, recheck the current terms, and verify the exact whole-file size and SHA-256 before use. Never use the line to define an international boundary.

Statistics Canada’s 2021 Census Division data are statistical reference geometry under the Statistics Canada Open Licence; they do not establish political ownership. TIGER/Line 2024 Washington counties are public-domain U.S. Census Bureau cartographic data. Exact byte pins for these and all structural inputs are embedded in `reproduce.py`; it reads them from immutable Git commit `a1fd3383e89dea4c4497bf3a6f469494871ad758` and verifies each whole file before computation. The 38,880,150-byte Census gzip remains in the prior packet, is hash checked by the runner, and is not copied here because it exceeds the evidence manifest’s 32 MiB ordinary-file limit.

## Method and result

Run with GDAL/OGR Python bindings, for example:

```sh
/usr/bin/python3 research/geography/bc-washington-reproduction-followup/vintages/ibc-restored-20261004/reproduce.py --archive /path/to/temporary/us-canada-boundary-v1-3.zip
/usr/bin/python3 research/geography/bc-washington-reproduction-followup/vintages/ibc-restored-20261004/verify_restoration.py --archive /path/to/temporary/us-canada-boundary-v1-3.zip
```

The runner checks the archive size/hash and baseline commit before reading geographies. It verifies all pinned scope, parent-chain, geometry, BC, Census, TIGER, and inherited-ledger files before calculation. All 222 members of the frozen scope and 61 assigned BC members are accounted for. One BC feature (`atlas:physical:CAN-185:BRC`) has no usable area boundary after the inherited `MakeValid` method and contributes no edge; this is explicit. All 29 Census divisions, 39 Washington counties, and the three issue-assigned subjects with complete five-tier parent chains are checked.

The IBC section line is interpreted in EPSG:4269; the source reference geometries use EPSG:4326. GDAL/OGR transforms the line and reference geometries to EPSG:3347. Invalid reference geometries are repaired with `MakeValid`, matching the inherited analyzer. GDAL emits self-intersection warnings and one GeometryCollection operation warning during this inherited method; the process completes and the focused rows match exactly, but this is not an independent validation of those repaired geometries. The line is sampled at 74 equally spaced points, no more than 1 km apart. For samples 50–67 the runner calculates nearest BC, Census Division and Washington county boundaries and strict county polygon containment. Every regenerated row matches the immutable #657 ledger exactly.

The ledger shows 18/18 samples, five empty strict-containment arrays at samples 55, 63, 64, 65 and 66, and nearest-BC distances from 1,011.90 m to 5,888.53 m. Whatcom County (GEOID 53073) remains the nearest Washington county in every row. Prior prose said four noncontainments and 1,011.91 m; the exact inherited and regenerated rows support five and a displayed minimum of 1,011.90 m.

This establishes source reproducibility and arithmetic only. Source vintages, scales, and represented surfaces differ. It does not explain the offset, establish legal boundaries or political ownership, or support a boundary correction. Any future correction needs a coordinated BC–Washington review; shared geometry remains unchanged.

`reproduced-assessment.json` is the immutable versioned result. `validation/` contains the read-only positive check, changed-input and exclusive-create negative checks, and two-run byte reproducibility receipt. The archive itself is intentionally absent.
