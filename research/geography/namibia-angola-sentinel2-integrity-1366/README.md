# Namibia–Angola Sentinel-2 integrity successor

This packet is an additive integrity review of the retained #1366 optical analysis. It preserves the earlier source files, geometries, IDs, reports and source windows. It does not revise the historical measurements, assign territory, decide a boundary, approve an import, or establish legal or physical status.

## Scope and source identity

The inherited data contain 21 candidate physical-component geometries and ten source-contact polygons: Angola ADM2 Dirico, Cuangar and Calai; Namibia ADM2 Grootfontein, Berseba, Rehoboth West, Rundu Urban, two distinct Lüderitz IDs, and Tsumeb. The two Lüderitz records remain distinct by their source IDs. Contact results refer only to candidate-union intersections, not the full administrative polygons. Across all records there are 16 unique Sentinel-2 Level-2A scene identities and an exact 31-mask × 16-scene matrix (496 rows).

The source packet retains 2019–2020 STAC discovery pages, selected item records, source-window and metadata receipts, native granule XML, tile metadata, COG HTTP HEAD records, and the sampled NPZ windows. These are inherited bytes authenticated at their retained Git commits, rather than a new remote acquisition. The original packet recorded HTTP 206 range reads and source object ETags; this successor did not download or hash whole COGs.

The 21 candidate geometries are source products whose 2018 Angola and 2007 Namibia vintages overlap. Their source identity does not establish current completeness, legal authority, survey accuracy, or boundary ownership. The retained JRC evidence describes water-classified products; the cited treaty and archival material do not precisely locate the line. Exact historic or present river course, legal status, territorial assignment, and cause of sensing-time conflicts remain unresolved. See the inherited gap-source packet and its source-quality limitations for the broader work.

## Reproduction and checks

Run with Python 3.12, NumPy 2.3.5, Shapely 2.1.2 and pyproj 3.7.2. These commands use the bundled Python runtime used for the retained runs:

```sh
/Users/chengshuli/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 research/geography/namibia-angola-sentinel2-integrity-1366/reconcile.py
/Users/chengshuli/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 research/geography/namibia-angola-sentinel2-integrity-1366/input_controls.py
/Users/chengshuli/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 research/geography/namibia-angola-sentinel2-integrity-1366/writer_controls.py
/Users/chengshuli/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 research/geography/namibia-angola-sentinel2-integrity-1366/legacy_entrypoint_controls.py
```

`reconcile.py` reads original bytes from immutable Git objects, checks the declared source and issue pins, decodes the 16 NPZ files under per-file and aggregate byte caps, verifies their array inventory and scene roster, and independently rebuilds all component/contact membership bits from the original geometries and native pixel-center affine transforms. It then recomputes each measurement with the retained method and compares every inherited measurement field against run one. It preserves both catalog `datetime` and native granule `SENSING_TIME`. Full result sets are published to fresh exclusive vintages through the authenticated shared `NewVintage` writer, with a completion receipt installed last.

Two clean complete runs produced the same reconciliation file SHA-256: `db240a9cd70e98a3f51c4f9c0518d3cd250a749e6a3e73897a04fd23d4b7a7bd`. The result contains 496 measurement rows and checks 1,751,344 retained pixel centers; component and contact bit mismatches are both zero. All retained measurement fields and all 21 component plus 10 contact aggregate summaries match the earlier complete report. These confirm reproducibility against retained nominal-grid windows, not independent ground-control accuracy.

The four material catalog/native sensing-time differences are retained per scene: 792.663543 seconds (`S2B_33KZA_20190221_0_L2A`), 866.957175 seconds (`S2B_34KBF_20190221_0_L2A`), 336.761901 seconds (`S2B_34KCF_20190221_0_L2A`), and 63.992610 seconds (`S2A_34KDF_20190223_0_L2A`). The other 12 are below one second. No cause is inferred, and the original seasonal bins and pixel measurements remain unchanged.

The four discrepant scenes contribute 124 rows to the 496-row table (31 masks per scene). This is a four-product time metadata discrepancy repeated across mask summaries, not 124 distinct acquisition events.

`input_controls.py` exercises the exact roster, byte receipt, array-shape and membership admission functions. It rejects missing, duplicate and foreign scenes; stale receipt hashes; wrong 10 m block dimensions; and coherent component/contact bit changes whose replacement NPZ receipt has a matching fresh hash. `writer_controls.py` exercises the actual pinned shared writer and confirms rejection of traversal, symlink and occupied destinations. A real OS `RLIMIT_FSIZE` error after a partial result write leaves a 1,024-byte failed artifact without `publication.json`.

`legacy_entrypoint_controls.py` copies the unchanged selector and analysis scripts plus their exact pinned inputs into a private owned fixture, then runs those real entrypoints. The selector reproduces an occupied-output overwrite and follows a dangling output symlink. The complete analysis CLI reproduces overwrite, `../` traversal, dangling-symlink writes and a 1,024-byte partial result after a real OS file-size error; its ordinary full output matches retained run one byte-for-byte. The exact `deterministic_npz` function AST from the pinned extractor reproduces overwrite and dangling-symlink writes. These are defect reproductions, not passing repair tests. Remote STAC/COG acquisition and full Rasterio extraction were not run because Rasterio/GDAL are unavailable. Fixing the legacy acquisition, selection, extraction, analysis and receipt writers requires an engineering handoff in paths outside this issue's owned directory.

The inherited source notice states Copernicus Sentinel data are free and open subject to the stated legal exceptions and attribution. This notice covers the product origin; it does not verify the terms of the Element84 mirror or catalog. Copernicus attribution is retained in the inherited packet. No new license grant or mirror-term determination is made here.

## Engineering follow-up and limits

The prior CLI has demonstrated unsafe overwrite, symlink and traversal behavior in selection, extraction and analysis writers, as well as gaps in the old receipt, membership and execution-code admission. This packet provides a safe authenticated successor reconciliation and exercises the shared fresh-vintage result writer. It does not alter legacy entry points because they are outside this issue's owned paths. An engineering owner must apply and exercise full destination-set admission at the legacy acquisition, selection, extraction, analysis and receipt/result writer entry points, including their remote execution paths. The bounded offline controls here do not claim that those entry points are repaired.

No fresh remote scene acquisition, whole-COG hash, independent ground-control survey, legal boundary determination, physical water classification, source-authority approval, or production import/publication was performed. Copernicus product rights do not independently establish mirror rights. Counts over intersecting masks and dates are nonadditive; SCL6 or index thresholds are optical screens only.
