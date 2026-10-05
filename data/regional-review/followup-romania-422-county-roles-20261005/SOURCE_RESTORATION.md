# Romania ADM1 source restoration and provenance

Retrieved/inspected 2026-10-05. The retained original bytes are in the prior #422 evidence packet at immutable commit [`9469f09592ced973a3448cf66b6100b741b64c0d`](https://github.com/ChengshuLi/WorldAtlas/tree/9469f09592ced973a3448cf66b6100b741b64c0d/data/regional-review/regional-review-3c4fe25a21fa428d/source/gb).

- GeoJSON: `gb-ROU-ADM1.geojson`, 32,428,002 bytes, SHA-256 `e70d8bedfcaad1b99f387b044f7e7563102b98ccee982496a092178d05f22387`.
- Metadata: `ROU-ADM1-geoBoundaries-ROU-ADM1-metaData.json`, 861 bytes, SHA-256 `ffbe05c013dabcff41f69c0691e9dbd9e8468b331244d6d67dd139b8ec7298fd`.
- Attribution/use text: `ROU-ADM1-CITATION-AND-USE-geoBoundaries.txt`, 4,316 bytes, SHA-256 `f6ea7572bea6036c4cdcacf8c0ca7bf09098d4e600d19546d7432533e9a290d5`.

The source metadata reports boundary year 2017, 42 ADM1 features, canonical type “Counties”, source “World Bank”, and CC BY 4.0. The retained county-role crosswalk identifies 41 statutory counties and one Bucharest Municipality. This demonstrates the metadata’s canonical label is too coarse for the 42nd unit; it does not demonstrate that any polygon is legally correct. The #422 source manifest and per-subject assessments remain preserved at the same commit.

License lineage remains partly unresolved. The original geoBoundaries metadata gives ArcGIS item `361134ff4ff44e78a9aeec01af9a5175`; the World Bank Data Catalog’s Romania Counties record links item `40320b20a03e469596202d77d5f5d374`. The catalog and retained metadata both display CC BY 4.0, but the item IDs differ and neither REST item was retrievable during this research. Keep the existing bytes/attribution and do not silently repin to either object.

The official ANCPI 2024 county layer is listed on [data.gov.ro](https://data.gov.ro/dataset/unitati-administrativ-teritoriale-07-03-2024) as a 8,175,720-byte SHP ZIP, updated 2024-05-17, CC BY 4.0, containing counties plus Bucharest Municipality. Restore from [the listed resource URL](https://data.gov.ro/dataset/37639a5a-64d0-4682-b8ab-f7188a28ae8e/resource/d94e8e1a-297a-4061-ba09-85eff048a35f/download/unitate_administrativa_judet.zip), hash the downloaded archive, preserve its license notice, then compare identities, CRS, dates, and boundaries. Repeated retrieval attempts timed out; no archive bytes or hash were obtained, so no geometry comparison is claimed.

The source feature collection is large enough to approach the evidence validator’s per-file limit; restore the exact commit/path rather than re-downloading the upstream URL. The evidence manifest binds its baseline bytes and all 9 issue pins to the immutable baseline commit.
