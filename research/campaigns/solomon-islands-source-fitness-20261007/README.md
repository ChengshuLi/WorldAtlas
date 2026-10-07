# Solomon Islands source fitness and physical support

Issue [#1424](https://github.com/ChengshuLi/WorldAtlas/issues/1424) scopes seven complete fine families, their twelve components, eight compatible candidates, four noncandidate siblings, and five shared Solomon Islands ADM1 contacts. This is a source-only classification. The other 21 families and 33 components in the same two operational batches are preserved as context in [`batch-context.json`](batch-context.json); no conclusion about those other families is made here.

## Finding

The retained geoBoundaries simplified ADM1 product verifies the identity and names of the five shared contact features. It does not support approval of the target slivers: all five source/current contact geometries are valid but unequal, their WGS84 symmetric differences range from 21.750 to 80.772 km², and the product's represented year is 2021 with no verified effective date. The eight compatible candidates total only about 202.304 m². Treat this administrative product as comparative context, not evidence for those tiny boundaries, legal authority, land/water truth, or ownership.

The retained GSHHG Level-1 pointsets fully cover the eight candidates in the existing source-relative comparison. The four noncandidate siblings remain visible: two have mixed mapped-L1 and outside support, and two lie outside mapped-L1 context. The physical-comparison rows retain `unknown-source-fitness-and-observation-date`; mapped support is not a physical-land or dry-land determination.

## Exact component disposition

The prefixes below identify the full 64-hex component IDs in [`assessment.json`](assessment.json) and the issue body. Full route, physical-result, query, source-row and batch records are preserved in `batch-context.json`.

| Component prefix | Candidate? | Retained comparison disposition |
| --- | --- | --- |
| `721838ee` | Yes | Fully covered by mapped GSHHG L1 land pointset; source status remains unknown |
| `854f216a` | Yes | Fully covered by mapped GSHHG L1 land pointset; source status remains unknown |
| `10f89b38` | Yes | Fully covered by mapped GSHHG L1 land pointset; source status remains unknown |
| `6a0546bc` | Yes | Fully covered by mapped GSHHG L1 land pointset; source status remains unknown |
| `2b39965d` | Yes | Fully covered by mapped GSHHG L1 land pointset; source status remains unknown |
| `abc8439a` | Yes | Fully covered by mapped GSHHG L1 land pointset; source status remains unknown |
| `8bce0aff` | Yes | Fully covered by mapped GSHHG L1 land pointset; source status remains unknown |
| `aed8ce56` | Yes | Fully covered by mapped GSHHG L1 land pointset; source status remains unknown |
| `7deb1a01` | No | Mixed mapped-L1 and outside-L1 support |
| `cf77bf20` | No | Mixed mapped-L1 and outside-L1 support |
| `371f640e` | No | Outside mapped-L1 context |
| `5144bba8` | No | Outside mapped-L1 context |

Every scoped physical output remains `unknown-source-fitness-and-observation-date`; its authority is unapproved. No candidate is classified as legally bounded, physically land, dry, or owned.

## Administrative product and five contacts

The exact consumed product is `gb:SLB:ADM1`, geoBoundaries **simplified** at commit `9469f09`: 33,558 compressed bytes (`bb5015f3…d15c8`), 93,632 decoded bytes (`418f5f1a…0798c`), ten features, CRS84 (`urn:ogc:def:crs:OGC:1.3:CRS84`). The retained registry records represented year 2021, source-data update 2023-01-19 and build date 2023-12-12. Those are product metadata dates, not an effective-boundary date. The current ADM1 records have the same exact shapeIDs and names.

| Contact | shapeID | Source/current symmetric difference |
| --- | --- | ---: |
| Central | `17018030B21762340724861` | 25.644 km² |
| Isabel | `17018030B36628097040544` | 33.638 km² |
| Makira | `17018030B43755880178831` | 24.236 km² |
| Choiseul | `17018030B68013150931387` | 21.750 km² |
| Western | `17018030B8659224027401` | 80.772 km² |

Both representations were valid. The comparison used the shared `worldatlas-evidence-geometry-v1` helper, longitude-first WGS84 and its straight-source-edge ellipsoidal area method. Equality and symmetric-difference area are diagnostics only. Product simplification and the difference itself do not establish which outline is correct.

The retained source records credit Natural Earth and report Public Domain for the underlying source; the separate geoBoundaries derivative-use statement records CC BY 4.0 attribution. The project preserves those statements, but does not independently verify underlying permission particulars, source authority, effective dates, or political interpretation.

## Physical source and retained records

The input is the original GSHHG 2.3.7 archive, `gshhs_f.b`, retained in four exact archive chunks with whole-archive SHA-256 `28600e8f…e82bc`. Its Level-1 native records were restored by byte offset from that archive; 26 records cover all 45 components in the two complete batches, and the six source IDs for the scoped twelve are 149, 160, 167, 204, 656 and 1804. The packet retains those 26 exact native records in [`native-source-records.bin`](native-source-records.bin), with offsets, native record hashes, coordinate-byte hashes and decoded pointset hashes in `batch-context.json`. All 55 context query pointset joins and their source-record hash pointers were checked against those native bytes.

The official [GSHHG project page](https://www.soest.hawaii.edu/wessel/gshhg/) dates release 2.3.7 to 2017-06-15 and describes source datasets with heterogeneous/older observation dates. The 2017 release date is not an observation date for these records. Its source documentation also cautions that the dataset may not be suitable for very large-scale mapping. Retained `LICENSE.TXT` says LGPL v3 or later; the official page describes LGPL v3 or any earlier version. This wording difference is preserved without a legal interpretation.

The complete batch handoff carries both batch rows, all 28 complete family rows and all 45 component rows, 39 retained admin-binding rows, 45 physical-comparison rows, all 26 linked source rows and the exact native source bytes. Classification conclusions remain limited to the twelve issue subjects and five named contacts.

## Limits and reproduction

Source fitness is **insufficient for finalizing or approving the approximately 202 m² candidate area**. The source/current differences are much larger than the target components, the administrative product is simplified and its effective date is unknown, and physical pointset support is source-relative. Registration, source precision, heterogeneous observation dates, seasonal wetness and unrecorded river widths remain unresolved. No legal boundary, dry-land, ownership or physical truth claim follows from this packet.

No source data was downloaded. The packet includes byte-identical copies of the retained 33,558-byte geoBoundaries product and the 26 queried GSHHG native records; all byte-level work used retained repository evidence. The official source pages were consulted only for product/version/license context. No broad imagery inspection, application/geography edit, source import or production action was performed.

Recreate the assessment and its controls from the immutable baseline:

```sh
python3 research/campaigns/solomon-islands-source-fitness-20261007/verify.py \
  --repo . --out-dir research/campaigns/solomon-islands-source-fitness-20261007
node scripts/evidence-quality.mjs research/campaigns/solomon-islands-source-fitness-20261007/evidence-quality.json .
```

The evidence validator checks bytes and manifest relationships. Independent source review is still required; this packet does not grant geography approval or authorize imports.
