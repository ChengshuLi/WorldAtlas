# Namibia: complete reference-source review

Review date: October 1, 2026. This review covers **all 111 current location IDs, all 109 original source records, all 107 replacement candidate constituencies, and all 14 candidate regions**. It does not claim that modern or historical Namibia is semantically complete.

Run `python scripts/review-namibia-source.py` to regenerate `data/namibia-source-review.json.gz` from the pinned downloads in `.cache/namibia-source-review`. The script reads atlas products, reports every old and candidate identity, and never changes geography, the database, or historical evidence. It compares every intersecting old/candidate pair with the project's shared WGS84 ellipsoidal area integral and records coverage shares in both directions.

## The defect is in the upstream 2007 source

The atlas currently uses geoBoundaries' [Namibia ADM2 derivative](https://github.com/wmgeolab/geoBoundaries/blob/9469f09/releaseData/gbOpen/NAM/ADM2/geoBoundaries-NAM-ADM2.geojson), whose metadata identifies [Stanford's 2007 constituencies](https://purl.stanford.edu/cs051py0596), authored by the Namibia Statistics Agency, as the public-domain source. Its canonical role is listed as `Unknown`, with 109 source features. The atlas has 111 IDs because one source territory, labeled Omaruru, was divided into three named physical-geography portions.

The defects are widespread. Only three of the 111 normalized displayed names equal the largest-overlap replacement name. This count includes spelling differences and therefore is **not** a count of 108 independently proven identity errors. Nevertheless, the full crosswalk contains clear large geographic mismatches:

| Current label | Territory occupying its footprint in the independent COD source |
|---|---|
| Arandis | Mukwe |
| Daures | Berseba |
| Karibib | Keetmanshoop Urban |
| Omaruru's three physical-geography portions | Gibeon |
| Oranjemund | Omaruru |
| Linyandi | Sibbinda |
| Sibinda | Linyanti |

Seven distinct original polygons are labeled Luderitz. Six current territories have no overlap with the COD country footprint: Oshakati West, Uukwiyu, Uuvudhiya, Engodi, Guinas and Okankolo. Hakahana is another mismatch: its footprint lies in Kalahari/Gobabis rather than a Windhoek constituency. The review retains all rows, including plausible names and spelling variants, rather than checking only these examples.

The script independently decodes original **SHP bounding boxes and DBF names row by row**, then compares all 109 records to the gbOpen derivative. This verifies that the gross label/coordinate mismatches exist in the original source files. The derivative's simplification changes some bounding boxes by less than 0.001 degrees; the audit records each difference. It does not mistake this simplification for exact geometry equality.

## A coherent, licensed replacement candidate

[OCHA COD-AB on HDX](https://data.humdata.org/dataset/cod-ab-nam) publishes NSA-origin boundaries under **Creative Commons Attribution for Intergovernmental Organisations (CC BY-IGO)**. The downloaded package contains 107 constituencies and 14 regions. Its metadata distinguishes:

- January 1, 2011: source boundary creation and last source edit.
- January 9, 2020: valid for humanitarian use.
- January 28, 2025: accuracy/completeness review.
- An explicit caveat: it is the **former 107-constituency system**, with later Kavango East/West division and Caprivi-to-Zambezi regional labeling. Namibia has adopted 121 constituencies.

These dates are separate facts. A recent review date does not make the boundaries current, and the mixed source/regional context does not establish a precise historical effective date for every parent relationship.

Exhaustive candidate geometry results:

- The union covers the package's own ADM0 footprint completely: **zero gaps, zero outside-country area and zero pair overlaps**.
- Every constituency is fully contained in its declared region to numerical precision.
- One source ring, Naminus/Luderitz, has a self-intersection. Deterministic `make_valid` retains a Polygon and preserves its WGS84 area to numerical precision; retain the original geometry and repair receipt.
- The union is about **824,099.82 km²**; its smallest constituency is about **1.88 km²**. No source polygon is grown to obtain a grid cell.
- Compared to the present atlas, about **839.22 km²** lies only in the current footprint and **793.16 km²** only in the COD footprint. These include source/coastline differences and erroneous detached pieces. They require external-border reconciliation rather than blind replacement against neighboring countries.

The report pins the downloaded archive, metadata, constituency/region/country GeoJSON, original SHP/DBF and additional source assessments with SHA-256 hashes.

## Complete migration proposal and remaining limits

Replace the defective country location layer as **one versioned reference release**, using all 107 coherent COD constituencies and stable new `hdx:NAM:ADM2:<pcode>` identities. Label the framework explicitly as the former constituency framework from the 2011 source, with later regional labeling. Retain all 111 old identities, original footprints and evidence. The full report accounts for every old ID and every candidate code, including zero-correspondence cases and split/multiple correspondences.

The spatial crosswalk is **not an instruction to transfer names, population, ownership or other dated evidence**. Neither matching a footprint nor matching a name alone distinguishes a source join error from genuine territorial succession. Existing evidence stays attached to its original identity until a separately sourced identity/date review approves a transfer. New footprints require ownership/reference preparation and a fresh grid representation audit. The parent hierarchy must be built from membership, with adjacent-country topology gates before publication.

The modern 121-constituency framework remains open. [Esri's 2025 constituency layer](https://www.arcgis.com/home/item.html?id=3f933df86b604db2b655680a221a9a04) explicitly forbids offline export under its license and was excluded. A licensed [FAO DIEM reference service](https://www.arcgis.com/home/item.html?id=3596c3ad318849068eda21517ade30be) returns 214 Namibia rows but only 107 unique constituency codes; it does not provide a verified newer complete framework. Public NSA census pages substantiate a need for modern administrative review but do not supply an independently licensed complete current polygon download in the material inspected. This is a documented source limitation, not permission to silently present the former framework as 2026 boundaries.

The existing compact ownership transport benchmark is already completed in `.cache/compact-ownership-benchmark/transport-results.json`: both tested codecs were round-tripped against every canonical Uint32 word for complete cached grids at zoom levels 7, 9 and 10. This review does not rerun or alter that frozen implementation.
