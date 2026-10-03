# Chagos: complete named-family source repair (#540)

Source-only stage, recorded 3 October 2026 UTC (2 October in America/Los_Angeles).
No atlas files, historical facts, provider database, grid or Site were changed.
The retained `IOT+00?` territorial identity, present-day name, owner reference and
parent chain stay intact. Subdivision into smaller locations belongs to the
regional interior audit, not this macro coverage correction.

The proposed modern footprint contains **72 complete sourced land components**:
71 directed OSM coastline rings, plus one closed named `place=islet` polygon.
There is **no area cutoff** and no island inflation or water-cell donation.
The 71 coastline components cover all eight conventional named groups: Diego
Garcia, Salomon, Peros Banhos, Egmont, Nelsons, Three Brothers including Resurgent,
Eagle including Sea Cow, and Danger. The named-islet exception is Anniversary
Island: exact retained way `1320152445`, version 1, timestamp 2024-10-02,
13 nodes, 0.001799 km². Its original `place=islet`/name/Wikidata tags supply a
separate positive land interpretation; it is not falsely labelled coastline.

The proposed footprint is 52.769942 km², versus 33.282901 km² currently:
19.487041 km² of sourced additional land. No predecessor land is removed;
all source components are mutually nonoverlapping to 0.001 m², and unrelated
current location overlap is zero. Existing Diego/Salomon geometry comes from
its **exact archived source XML**, not a newer replacement snapshot. Their
small rings formerly excluded by the 0.1 km² threshold are included now.
Complete inland-water and lagoon relations are subtracted with their inner
islands preserved. Sources are modern reference evidence, not ancient claims.

## Exhaustive scoped coverage

OSM defines these coastlines at mean high-water springs (MHWS); the exact tag
definition is retained with its source hash. Ten explicit query domains include the eight named groups and two tidal reefs.
The southern domains were widened to encompass **every one of the 62 retained
GSHHG Chagos comparison components**, despite that older source's coastline
position/area discrepancies. GSHHG is only a dated independent search-domain
check; it does not replace current geometry or prove present-day shoreline truth.
All **70 original GeoNames island/atoll/family records** have individual
crosswalk dispositions. Family-centre points do not establish land; displaced
Longue, Petite Île de la Passe and Anniversary name points are retained as
positional/alias uncertainties rather than moving polygons to fit points.

Blenheim Reef is deliberately excluded from high-water land: the official
ITLOS judgment of 28 April 2023, paragraph 146, treats it as a low-tide elevation
following the parties' survey. Earlier gazetteer descriptions of four cays
are retained but do not supply a verified high-water land outline. NGA's 2026
nautical text mentions an exception at the southern extremity at unspecified
high water. Its observation date/datum are unknown; this qualification is
retained alongside the court's classification, without inventing a polygon.
Speakers Bank's named source describes drying cays, the largest just reaching
the high-water mark. Independently, NGA's 2026 Sailing Directions, section
8.27, describes it as an underwater bank. Its full queried domain contains no
coastline geometry; the nautical account does not rule out every tiny cay.
It remains explicit marine evidence: **absence in OSM alone is not proof of no
land**, and independently verified modern chart-grade high-water delineation
remains unavailable. No positive-area land is invented from an intertidal reef.
Their macro destination remains South Asian Indian Ocean Islands if stronger
future evidence establishes any high-water land.

## Reproduce and integrate

```sh
python data/macro-improvements/loose-ends-v5/chagos/reproduce.py --baseline data --output /tmp/chagos-fresh-output
```

Use a fresh output directory and the pinned original `IOT+00?` baseline.
`prepared/patch.json.gz` is a sparse retained-ID replacement proposal;
`before-features.json.gz` preserves the complete old feature;
`source-dry-land.geojson.gz` is the exact licensed source wrapper;
`index.json` pins all prepared outputs. The script checks original XML and way
versions, closed directed rings, all water masks, valid geometry, zero old-land
loss, source mutual overlap, every other current location, all original GeoNames
bytes/coordinates, original named-page hashes, and the 62 comparison domains.
Grid representation, ancestor unions, ownership/environment invalidation,
release/certificate generation and live publication are the publisher's work.
Passing this source stage does not approve regional interiors or survey accuracy.

OSM source data: contributors, ODbL 1.0, https://www.openstreetmap.org/copyright.
OSM Wiki coastline-definition text: CC BY-SA 2.0 with contributor/history URL.
GeoNames: CC BY 4.0; original selected bytes, full upstream snapshot digest and
URL retained. Wikipedia: CC BY-SA with original bytes and author/history URLs.
ITLOS: official URL, exact full PDF byte hash, source date and short attributed
excerpt retained; full ITLOS PDF is not redistributed without established reuse
terms. NGA's government publication carries its Title 17 no-copyright-claim
notice; its mirror URL, exact full PDF hash and short quotations are retained
without adding the 9.85 MB PDF to Git or deployment.

For the installer-compatible generic receipt, the designated publisher then runs
this **serialized full-world Node job**, after other memory-heavy jobs finish:

```sh
node --max-old-space-size=3072 data/macro-improvements/loose-ends-v5/chagos/finish-contract.mjs
```

It uses production `footprintHash` and `validateGeometryMigrations`, archives the
one changed identity, accounts for all 49,622 reused IDs, and adds exact native
before/after footprint hashes, source evidence and `migration-receipt.json.gz`
to the pinned index. It preserves the source wrapper and source geometries;
patch/index contract augmentation follows the separately verified source-stage
byte-identical replay. It neither installs geography nor transfers history.
