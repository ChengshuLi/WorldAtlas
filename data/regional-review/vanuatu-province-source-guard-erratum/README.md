# Vanuatu source digest and fresh reproduction erratum (#1250)

Research snapshot: 2026-10-06 America/Los_Angeles. Worker reservation: `01a10948-7d38-75d0-bc01-4cc28ea41f49`. Branch: `geography/vanuatu-source-digest-1250-20261007`. This is additive evidence under the issue-owned prefix. It preserves the original #912/#1165 packet, six IDs, classifications, source files, release pins and 24 historic measurements.

## Reconciled source products

At geoBoundaries repository commit `9469f09592ced973a3448cf66b6100b741b64c0d`, the exact release path `releaseData/gbOpen/VUT/ADM1/` contains separate Git LFS objects `geoBoundaries-VUT-ADM1.geojson` and `geoBoundaries-VUT-ADM1_simplified.geojson`. The `63e1878b…` registry digest is the 133,712-byte simplified LFS payload. The original packet's full product is 1,094,439 bytes with SHA-256 `69f44b96…`; the simplified payload has SHA-256 `63e1878b…`. `source/lfs-restoration-pointers.json` records each object’s exact path, LFS OID, byte count, retrieval time and pointer Git blob SHA-1; adjacent `.lfs-pointer` files preserve the original pointer text. The SHA-1 values identify small Git pointer blobs, not the GeoJSON payloads.

Both complete products have six features. Selection by native `properties.shapeID` finds each of the exact six issue IDs once. All six `shapeID`, `shapeName` and `shapeType` values agree across products. This reconciles the registry hash as a different upstream distribution product; it does not reproduce geoBoundaries' simplification algorithm or establish that the geometries are legally authoritative. The historic #912 screen continues to consume the full source exactly as before. No geometry was substituted or changed.

The retained geoBoundaries metadata describes a 2017 ADM1 boundary sourced from OpenStreetMap/Wambacher, with source data update 2023-01-19, build date 2023-12-12, six ADM1 units and ODbL 1.0. The accompanying citation file separately licenses geoBoundaries-generated code and derivative works under CC BY 4.0; this does not replace the boundary data's ODbL terms. The metadata's `licenseSource` and `boundarySourceURL` fields contain malformed `https//` strings, so those URL values are not treated as verified. Product vintage/identity and license do not demonstrate current statutory boundaries, effective dates, municipality carve-outs or completeness.

## Frozen baseline and fresh runs

`source/input-pins.json` records exact whole-file SHA-256/byte pins for the historical measurement baseline `a32ae163473a42ed28d7bedf7e9930414beb54f8`, the original packet/producer merge `72029cd16057199be441058c69dd783604541100`, and the original producer, validator, report, source, and shared helpers. The original shared Python helpers are byte-identical to the locally executed versions. The pinned world index lists 36 inputs: parts 0–33 plus `source-restoration-additions.json` and `macro-loose-ends-v5-additions.json`; their total is 203,277,878 bytes. The exact original producer's calculations execute against the historical baseline after its overwrite-capable final write is removed from the parsed program. Only the new runner publishes results, through exclusive fresh paths.

`vintages/20261007-fresh-seven/reproduction.json` and `vintages/20261007-fresh-eight/reproduction.json` are byte-identical (8,899 bytes; SHA-256 `88ff099392aa927057a563d404cdf2c4f369d0cf9763b2cf8bb5241eb379d3f2`). Their six complete subject rows, including parents and classifications, match the original report exactly; all 24 numeric metrics match exactly. All six classifications remain `insufficient-evidence`. The measures compare Atlas footprints to a 2017 OSM-derived product using the retained shared WGS84 straight-edge ellipsoidal method; they are diagnostic screens, not truth scores.

The exact pinned hierarchy retains each subject under a same-named `framework:province:*` reference group, with one child under `framework:area:vanuatu:97c1380d5908`. Each group has `framework_status: retained-reference`; semantic review and boundary status remain open. This describes stored Atlas parent purpose, not legal parentage. Neither those parent IDs nor one-child structure is evidence that the province groups are approved.

`controls.py` records passing positive, negative and reproducibility controls. The runner rejects changed pinned inputs and code, output path traversal, symlink escape and an existing destination; the existing-output sentinel remains byte-for-byte unchanged. It scans all 36 pinned parts for unique subject occurrence before measuring. `evidence-quality.json` inventories every changed file, exact baseline inputs, metrics, outputs, methods and controls. The issue's 8 MiB reserve and 256 MiB cap are preserved; actual inventory totals are reported there.

## Carried-forward geographic findings and limits

The original #912 packet's source inventory remains authoritative for its prior bounded source review and remains unchanged. It records DLA's six named provinces and island-group descriptions, the Act's Orders-based boundary authority and municipality exclusion, and the differing subordinate references: current DLA area-council roster (71), conflicting brochure total (80), and OCHA/SPC ADM2 reference (66 features with blank license metadata). The consulted evidence did not supply current boundary-defining Orders, exact legal municipal exclusions, or complete lawful linework for every outer island. Profile maps/counts and area-council numbers are not boundary evidence. DLA PDF retention remains restoration-only under its previously recorded terms.

No boundary correction, source-authority upgrade, hierarchy change, regional approval, import, publication, deployment or historical import is proposed. The source identity and fresh reproduction correction does not complete the original Vanuatu region review. Follow the explicit scientific-source waits in #912; do not reopen it or extend its exhausted budget.

## Reproduction

With the repository's Python 3.12 environment plus Shapely 2 and pyproj installed, run from the repository root:

```sh
python3 data/regional-review/vanuatu-province-source-guard-erratum/reproduce.py
python3 data/regional-review/vanuatu-province-source-guard-erratum/controls.py
```

The two fresh version directories are immutable and exclusive. A repeat can pass two new unique names with `--run-one` and `--run-two`; existing results and control fixtures are never overwritten. The project evidence validator is `node scripts/evidence-quality.mjs data/regional-review/vanuatu-province-source-guard-erratum/evidence-quality.json`.
