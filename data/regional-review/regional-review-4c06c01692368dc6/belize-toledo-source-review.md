# Belize member source review: Toledo

**Packet:** [#186](https://github.com/ChengshuLi/WorldAtlas/issues/186), `regional-review:4c06c01692368dc6` (v5)
**Exact subject:** `gb:BLZ:ADM1:66346737B22858594960980`
**Area:** Belize
**Source role:** Districts, GeoBoundaries ADM1
**Classification:** **Insufficient evidence for regional tier/parent approval.** The source membership and administrative district role are verified for this row; this alone does not establish the region's semantic parent decision or authoritative boundary provenance.

## Source and inspection

Retained the original [GeoBoundaries BLZ ADM1 GeoJSON](sources/geoBoundaries-BLZ-ADM1.geojson) and its [metadata sidecar](sources/geoBoundaries-BLZ-ADM1-metaData.json) from pinned repository commit [`9469f09592ced973a3448cf66b6100b741b64c0d`](https://github.com/wmgeolab/geoBoundaries/tree/9469f09592ced973a3448cf66b6100b741b64c0d/releaseData/gbOpen/BLZ/ADM1). The source URL recorded by the issue resolves to this immutable commit. Retrieved 2026-10-19 UTC.

The dataset contains six features. Their six `shapeID` values exactly equal the six Belize `gb:BLZ:ADM1:<shapeID>` member IDs in #186's pinned scope. The assigned member matches `shapeID` `66346737B22858594960980`; its feature reports `shapeName=Toledo`, `shapeGroup=BLZ`, `shapeType=ADM1`, `shapeISO=BZ-TOL`, and a `Polygon` geometry. This directly confirms source membership and the dataset's ADM1 district label for this one subject.

The sidecar independently reports `boundaryYear=2006`, `boundaryType=ADM1`, `boundaryCanonical=Districts`, `admUnitCount=6`, and `boundaryLicense=Creative Commons Attribution 2.5 Generic`. It names `geoBoundaries, Wikimedia Commons` as the boundary source and records a source-data update date of 2023-02-22 and build date of 2023-12-12. Attribution: GeoBoundaries Belize ADM1 dataset, built 2023-12-12; underlying source credited by its metadata to Wikimedia Commons; CC BY 2.5.

Retained source SHA-256 values:

- GeoJSON: `c75826394c11129d493cc4a250005fae1bfd26d60921edc1ed9471609866083b`
- Metadata sidecar: `98e9c5b80423c3b904a9fabb470b84ca16c8f000232fc819d3456da1438aad29`

## Uncertainty and remaining work

The sidecar's `boundarySourceURL` is the incomplete string `https//commons.wikimedia.org/wiki/File`; it does not identify a specific Wikimedia file. I did not verify an original Belize government/legal source, the district's administrative authority, currentness, or the source polygon's legal boundary accuracy. The 2006 vintage and ADM1/Districts labels support an administrative-district candidate, but do not on their own prove the atlas tier, parent purpose, or suitability of the polygon for a frozen regional boundary. This row therefore remains **insufficient evidence** for those semantic decisions. Other packet members remain open and were not reviewed here.
