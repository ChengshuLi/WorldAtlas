# Namibia–Angola gap-family source and physical-reference review

## Scope and disposition

Research status: **partial**. The reproducible source-product comparison is complete. Retained JRC Global Surface Water v1.5 products provide dated, approximately 30 m water observations within the candidate family; exact bank/course evidence and completed demarcation records remain unavailable.

This packet reviews the complete 21-component candidate family and all 10 source-contact features carried by issue #1268. It preserves the original geometry and source diagnostics. It does not assign any candidate to Namibia or Angola, amend a boundary, resolve the broader issue #1202, or authorize a data import.

The geometric result is supported at the product level: all 21 candidates have positive-area intersections with the retained 2018 Angola ADM2 product; 20 also have positive-area intersections with the retained 2007 Namibia ADM2 product. Against the same-release full/detail products, the same counts are 21 and 20. The 10 retained contact features all differ topologically from their full-product counterparts. These findings describe how source polygons overlap the candidates; they do not decide which source is authoritative.

JRC occurrence (March 1984–December 2024) and 2024 seasonality tiles show water-classified pixel centers inside all 21 original candidates. Of 189,481 pixel centers counted across the per-component masks, 66,592 have occurrence above zero, 20,083 have occurrence at least 50%, and 10,203 have occurrence at least 90%; 33,116 have positive 2024 seasonality. These sums are per-component counts and are not a deduplicated area estimate. The original diagnostics still say `unverified`; the JRC observations add physical-reference evidence but do not identify a bank, waterbody type, historic course, legal line, processing cause, or territorial assignment. The JRC release documents a spatially variable co-registration offset at the 2022 Collection 2 transition, commonly sub-pixel and at or above one 30 m pixel in some path/rows. The 1926 treaty framework and archive catalogue leads do not establish completed demarcation at these coordinates. Available Namibia basin materials are generalized context; an approved Okavango–Omatako booklet remains uninspected. No administrative assignment is made.

## Contents

- `inputs/`: immutable issue-scope inputs, contact/source bindings, full 35-pin input inventory, and lineage/source-reference leads.
- `sources/`: byte-preserved consumed simplified geoBoundaries capsules; same-release full products and metadata; exact Git LFS pointer text; the inspected 1926 treaty; and a clearly identified HTML response where MINEA's PDF endpoint returned a portal page.
- `source-geometry-comparison.json`: verifies custody pins and original feature identities, and reports whole-consumed-product intersections.
- `full-product-comparison.json`: compares every candidate against both same-release full products and every candidate against each of the 10 full source contacts; retains intersection and difference geometries, dimension counts, and controls.
- `candidate-classifications.json`: one row per candidate with separate source geometry, physical water, processing cause, authority, and decision-limit fields.
- `official-reference-review.json`: dated source audit, retrieval status, scope, and limits.
- `sources/jrc-gsw-2024/`: complete original JRC tiles, official guide and ISO metadata; occurrence tiles are stored as byte-preserving parts below the evidence file-size limit and reassembled by the script.
- `jrc-gsw-analysis-input-set.json` and `jrc-gsw-water-analysis.json`: source/input pins, raster metadata, and per-component value counts.
- `reproduce_jrc_gsw_water.py`: reassembles and verifies source tiles, then applies an unchanged-geometry pixel-center mask.
- `reproduce_source_geometry.py` and `reproduce_full_product_comparison.py`: complete independent reproduction commands.

## Geometry method

The producer scripts re-read the 35 whole-input pins from their immutable Git commits, verify component features against the content-addressed custody payloads, and verify all 10 contact features against the full consumed products. They compare every candidate with all 109 Namibia and 161 Angola features in the consumed simplified products, retaining each intersecting source-unit intersection and both directed differences as geometries, plus the candidate-minus-combined-union geometry. The second script also checks the same-release full products (109 Namibia, 161 Angola), records positive-area component/source intersections and candidate-minus-source differences, and evaluates all 210 candidate/contact pairs. It retains the source-contact symmetric differences and the geometry of each positive intersection or difference; disjoint pairs are recorded as such.

All overlay coordinates remain in longitude/latitude (EPSG:4326). Area values are planar square degrees and are not ground-area estimates. There is no reprojection, repair, snapping, clipping, assignment, or legal interpretation. Both scripts include positive and negative controls for coverage, disjointness, point-only/line-only/area geometry behavior, missing/invalid inputs, and original-byte preservation. The output records the exact software environment and method details.

## Source and authority limits

The consumed simplified products are recorded as geoBoundaries NAM ADM2 (represented year 2007, Public Domain) and AGO ADM2 (represented year 2018, CC-BY 3.0 IGO). Full products are retained as separate, same-release product observations from commit `9469f09592ced973a3448cf66b6100b741b64c0d`; they are not substituted for the consumed products.

The official 1926 treaty text identifies the Ruacana/Rua Cana waterfall reference, describes a latitude-parallel and Okavango/Cubango sequence, refers to the 1886 Lisbon treaty, and requires joint demarcation. It does not supply a modern georeferenced alignment or the completed survey/beacon record for each candidate. National Archives of Namibia catalogues list 1927–28 Angola Boundary Survey and 1926–28 South Africa–Angola Boundary Commission material, but the underlying records were not obtained. The Ministry's 2008 water-basin map is at 1:2,000,000 and useful only for regional context. The approved Okavango–Omatako basin booklet was identified in the Ministry portal, but its file request timed out; it is not relied upon for a physical-edge claim.

The JRC GSW v1.5 water products are independent optical-satellite classifications. Occurrence is a month-normalized long-term summary across 1984–2024; seasonality is the number of water months in 2024. The source guide identifies pixel value 0 as not water, 1–100 (occurrence) or 1–12 (seasonality) as water, and 255 as NoData. Tiles use EPSG:4326 and a 0.00025° grid. Counts include only pixel centers inside each unchanged candidate; NoData is excluded. Attribution requested by the source page: `Source: EC JRC/Google`. Reproduction retains the source bytes and each candidate’s full value histogram. These observations support water occurrence within the candidate footprints but are not surveyed hydrography, exact bank lines, a historic-channel reconstruction, or an authoritative international-boundary source.

Accordingly, the following questions remain open: the present bank/course and historic channel at each candidate; whether any candidates are water, wetland, floodplain, or land; which processing step produced each candidate; whether the candidates coincide with a legally demarcated line; and whether any source polygon is authoritative for territorial attribution. An archive catalogue listing is a retrieval lead, not proof of the underlying contents.

## Reproduction

From the repository root, using Python 3.12.14, Shapely 2.1.2, and GEOS as recorded by the scripts:

```sh
python3 research/geography/gap-source-namibia-angola-20261006/reproduce_source_geometry.py
python3 research/geography/gap-source-namibia-angola-20261006/reproduce_full_product_comparison.py
python3 research/geography/gap-source-namibia-angola-20261006/reproduce_jrc_gsw_water.py
```

The vector scripts use retained files plus exact immutable Git blobs named in `inputs/whole-input-pins.json`. The JRC script requires Rasterio 1.4.3, NumPy 2.3.5, and Shapely 2.1.2; it verifies all retained raster parts and supporting files before analysis. Expected vector summary: 21 positive-area Angola and 20 positive-area Namibia intersections against both product vintages; 49 of 210 candidate/contact pairs intersect, all with positive area; 10 of 10 source contacts differ topologically between consumed and full products. Expected JRC summary: water-classified pixels occur within all 21 candidates in both products.

## Exact limits

This packet supports statements about retained source bytes, feature identity, product vintage metadata, reproducible polygon overlays, and JRC water-classified pixels within candidate masks. It does not establish legal title, recognized sovereignty, an authoritative current border, an exact physical river edge, historical channel movement, or causation. It is not an approval to publish or import geometry.

The JRC analysis was run twice in full on 2026-10-07 UTC with the same pinned candidate/source inputs and recorded Python/Rasterio/NumPy/Shapely/GDAL environment. Both runs produced identical SHA-256 hashes for the analysis and both synthetic controls. Exact timestamps, commands, all input/output byte hashes, and environment details are retained in `jrc-gsw-reproduction-runs.json`.
