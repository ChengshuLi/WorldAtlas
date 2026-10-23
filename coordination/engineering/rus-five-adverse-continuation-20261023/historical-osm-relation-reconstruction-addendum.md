## Bounded historical OSM relation reconstruction addendum (2026-10-23)

This follow-up corrects the earlier route-limitation summary. The prior relation-version `/full` request returning HTTP 404 and the first Overpass endpoint returning HTTP 406 were responses from those specific routes, not access denials and not evidence that historical reconstruction was unavailable. The same bounded query succeeded at the public `lz4.overpass-api.de` Overpass instance (HTTP 200). No alternate route was used to bypass a denial; none occurred.

The query requested only relations 1241910, 1526041, and 1517228 and their descendants at the historical date 2017-12-31T23:59:59Z:

```text
[out:json][timeout:180][date:"2017-12-31T23:59:59Z"];
relation(id:1241910,1526041,1517228);
(._;>>;);
out meta geom;
```

The 3,361,947-byte response had SHA-256 `073c9a78b33b9576a0e6ca0f88146df785c84448bfbdd20989afb8b5d4c49aa` when checked locally by the author. The raw response is retained locally, not published; the reviewer could not independently recompute this response hash. It contained 9,231 elements. The retained RUS archive is `RUS_ADM2-faa6461e-source.zip`, 50,309,119 bytes, SHA-256 `faa6461e6a85d021ac4b99ee983b3cf92fa05d4468a8ea79e2dea2615fc30aab`; its metadata calls the boundary representative year 2017 and identifies OpenStreetMap/Wambacher, but does not specify an extraction date. OSM data attribution: © OpenStreetMap contributors, [ODbL 1.0](https://www.openstreetmap.org/copyright).

We compared the exact DBF feature IDs and SHP coordinate vertices with the date-bounded member-way geometries, using standard-library parsing only:

- Trubchevsky relation 1241910 v25 (2017-11-20; latest member-way edit 2017-12-12): 1,003 exact shared vertices; 6 archive vertices and 12 OSM vertices were not exact set matches.
- Tarasovsky relation 1526041 v20 (2016-11-23; latest member-way edit 2017-07-19): all 1,580 unique OSM vertices match the archive feature; its 1,581st feature vertex closes the ring by repeating the first vertex.
- Krasnosulinsky relation 1517228 v38 (2017-09-17; latest member-way edit 2017-11-22): 3,233 exact shared vertices; the only unmatched pair is 3.222 m apart by a local equirectangular approximation.

This materially strengthens feature-to-relation lineage for all three retained RUS features. It does not identify the archive's exact extraction date, establish that these exact historical relation versions generated its bytes, or resolve source applicability at the five disputed centers. The separate retained full-resolution source comparison still places all five inside the corresponding full UKR feature and outside the full RUS feature. The treaty maps still lack reliable local registration/point-side evidence. Therefore all five original keys remain held and researched-unresolved as proposed: zero repairs, zero owner changes, zero hold removals, no package completion, and no change to the original 2,566,967-cell denominator. No sovereignty or current-legal-boundary conclusion is made.

The full raw geometry response is retained only in the local research workspace and is not included here; this public addendum contains the bounded method, provenance, counts, hashes, and limits needed to review the conclusion.
