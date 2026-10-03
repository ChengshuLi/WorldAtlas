# Fugloy evidence packet (#522)

Scope: the one pinned location `atlas:restoration:location:fugloy`, its full parent chain, and its partial Føroyar area context. See `assessment.json` for the exhaustive one-of-one location decision, source receipts, settlement and administrative roles, all detached ring findings, and explicit limits.

The exact OpenStreetMap response is retained by the merged Europe–Asia restoration packet. Its original 2026-10-02 API response is `modern-coastlines/FugloyWide.osm.xml.gz` inside `data/macro-improvements/macro-coverage-europe-asia/geometry-and-modern-sources.tar.gz`. The assessment records the archive/member and decompressed SHA-256 digests, ODbL attribution, and a byte-restoration command. No external municipal page bytes or images are copied; their current canonical URLs and retrieval limitations are recorded.

Reproduce the evidence checks from the repository root:

```sh
python3 data/regional-review/regional-supplement-aeeb316450496155/verify.py
```

The verifier checks the retained OSM member bytes, every assigned parent id, the release-5 regional handoff, the exact one-location scope and 34 additional closed rings/two open chains. It does not certify the rings' relation to the island, a municipal boundary, a tidal datum, complete Faroe/Nordic Europe coverage, or regional approval.

No shared hierarchy, geometry, source archive, application or live product was changed.
