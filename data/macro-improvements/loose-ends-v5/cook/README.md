# Complete Cook atoll dry-land footprints — issue 540

This offline engineering stage replaces only the modern reference geometries of
**Manuae (`COK-4951`)** and **Aitutaki (`COK-4956`)**. Their corrected modern names,
stable identities and complete geographic parent chains remain unchanged. No new
locations, groups or factual historical records are created. This stage is not
an installed or published release and does not approve regional interiors.

Both complete named-atoll footprints already have retained, hashed original
OpenStreetMap XML in the preceding Cook review. The existing exact-node coastline
assembler replays those bytes. Seven Manuae land rings and 28 Aitutaki land rings
remain two named territories, not 35 new locations. One and seven explicit water
masks respectively remove mapped inland water. Source data is ODbL 1.0,
© OpenStreetMap contributors. Original compressed bytes are copied unchanged into
`prepared/sources/`; wrapper geometries, raw hashes, archive hashes, URLs,
way versions/timestamps and source support are retained in the stage.

Source support is **modern reference `[2026,2027)` only**. Removing parts of the
old generalized outlines is a cartographic correction, not evidence that land
historically disappeared. The old features and original catalog identities are
archived verbatim as decoded JSON. The prior Cook archive preserves earlier
Natural Earth labels and legacy records and is explicitly hash-pinned here.
No historical name, owner, population or other attribute is inferred or copied.
Current private historical records still require the publisher's scope review.

The executed validation scans all **49,623** installed location footprints for
positive-area conflicts, replays original source bytes, checks geometry validity
and exact retained parent chains, and measures before/after land differences.
The explicit numerical overlap tolerance is 0.001 m². No buffering, footprint
inflation or arbitrary water-cell reassignment is used. Canonical cell centers:

| Atoll | Zoom 10 | Zoom 11 |
| --- | ---: | ---: |
| Manuae | 320 | 1,285 |
| Aitutaki | 886 | 3,525 |

At zoom 10, two of Manuae's seven source land components and eight of Aitutaki's
28 have no cell center. At zoom 11 those counts fall to zero and three. The full
source geometry includes every reviewed component; these are sub-cell rendering
limits, not additional location identities or an excuse to expand coastlines.
`grid-check.json.gz` records every component's representation result.

Reproduce from the exact current release-4 baseline using existing dependencies:

```sh
python3 data/macro-improvements/loose-ends-v5/cook/verify.py --output /tmp/cook-loose-ends
node data/macro-improvements/loose-ends-v5/cook/verify-contract.mjs /tmp/cook-loose-ends
```

Use a fresh output directory. `prepared/candidate-patch.json.gz` contains sparse
`existing_location_updates`, `replacement_deltas`, current source-part and
hierarchy pins, and exact source wrappers. `prepared/index.json` and its pinned
`migration-receipt.json.gz` are accepted by the production
`validateGeometryMigrations` gate: all unchanged IDs, two exact predecessor
features, full-world before/after footprint hashes, two `source-backed-replace`
relationships and inspected source URLs/hashes are accounted for. This receipt
is standalone against release 4; combined v5 staging must compose corrections in
the actual migration order and recompute its complete footprint hashes.

Installation remains the root publisher's responsibility: revalidate live direct
records, preserve original records, regenerate only affected derived attributes,
rebuild bottom-up parent footprints and one fixed canonical grid, then publish
and verify matching release/certificate/queue pins. Current factual source
support and unknowns must not be widened. Mapped water coverage is not exhaustive
hydrological coverage, and OSM is not a survey-accuracy claim.
