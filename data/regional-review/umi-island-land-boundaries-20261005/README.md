# Baker, Howland, Jarvis and Palmyra dry-land source review

Issue #1061 · retrieved/researched 2026-10-05 (America/Los_Angeles) · baseline `f1a6c0abc29de7bf7b7a081a8a9864b0450c0427`.

This packet reviews only `UMI-5171` Baker Island, `UMI-5172` Howland Island, `UMI-5173` Jarvis Island and `UMI-5178` Palmyra Atoll. It preserves their current feature IDs, province parent links, and `owner:Q30` / United States Minor Outlying Islands reference-owner metadata. In the hierarchy, Baker and Howland sit under the physical `Howland and Baker Islands` area; Palmyra and Jarvis sit under the physical `Line Islands` area. That physical group does not make Palmyra or Jarvis Kiribati. It does not change geography, certify regional coverage or authorize imports.

## Result

NOAA NGS's Continually Updated Shoreline Product (CUSP) Pacific Islands download is the strongest lawful, publicly downloadable current-product candidate found for this scope. NOAA describes CUSP as its best available contemporary shoreline, stitched from NOAA and non-NOAA sources and reviewed against contemporary imagery. It also says the source data may not include a complete shoreline, and that names/boundary representation are not necessarily authoritative. The Data.gov record assigns CC0 but labels access `non-public`, while NOAA serves the regional ZIP publicly; retain this catalog inconsistency. NOAA InPort says access constraints are none, but says the data are not for litigation, are supplied without warranty, and requests NOAA credit.

The regional ZIP was fetched 2026-10-05. The server's `Last-Modified` header is 2026-08-05; the archive entries carry that date. A CUSP archive timestamp is not the observation date of each line. The site records show:

In the site windows, the CUSP source dates remain April 2004 at Baker, May 2005 at Howland, and March 2004 at Jarvis. Palmyra has 2001 linework and newer lines dated 2022-04-25, 2023-04-08 and 2023-04-28. The regional archive timestamp is not the observation date. At Palmyra, the original project archive has more natural mean-high-water line records than appear in CUSP; the polygonized CUSP footprint intersects most, but not all, of the original archive's polygonized footprint. CUSP also carries newer Palmyra lines with blank source IDs, so the exact image/source relationship for those additions is not recoverable from the feature rows. `results.json` records the exact source feature dates, counts, extents and controlled geometry comparisons for each site.

The results also show material overlay discrepancies: Howland's atlas polygon is spatially disjoint from the candidate; Baker and Jarvis overlap only part of the polygonized source; Palmyra's atlas polygon does not contain the full CUSP-derived footprint. These are area/shape diagnostics, not percentages of real coastline or proof of complete dry land. Polygonizing clipped source lines can omit unclosed pieces or split rings. The four fixed windows are in `verify.py`. All reported areas use the shared WGS84 straight-source-edge ellipsoidal helper; overlays inherit source linework and polygonization limits.

The current Atlas polygons are materially inconsistent with the candidate shorelines. Howland is spatially disjoint; Baker and Jarvis cover only part of the diagnostic source footprints; Palmyra does not contain the full CUSP-derived footprint. This supports a bounded engineering restoration/reconciliation handoff for these exact four IDs using the latest NOAA source as a candidate, with fidelity and source-vintage review before any change. It does not justify copying every CUSP line into land polygons or silently replacing geometry.

## Palmyra membership and lagoon limits

FWS currently describes Palmyra as about 26 islets among several lagoons. Its 2013 release described 25 islets and 580 acres of land, while a 2011 final environmental impact statement describes the atoll before restoration as approximately 54 small islets around three central lagoons. These differently dated and framed counts are not a stable, complete name roster. They cannot serve as a polygon completeness test.

In the independently retrieved OpenStreetMap screen (database timestamp 2026-10-06T04:08:02Z), the Palmyra window contains 16 named point records: 15 individual island labels and a separate “Palmyra Atoll” label. It has 34 coastline ways, which polygonize to 32 valid rings in this window. Five of those point labels fall outside the polygons produced from CUSP's Palmyra lines. Because map labels can be approximate and NOAA says its shoreline may be incomplete, this is an investigation signal only; it does not prove which islets CUSP omits. NOAA CUSP has 55 natural MHW line records that polygonize to 53 rings, but CUSP itself disclaims complete coverage and does not name its islets. None of these totals certifies all islets, cays, lagoons, emergent sand or rocks.

No inspected authoritative source supplies a current, complete named-islet/cay roster tied to reusable land vertices and lagoon membership. This is an unresolved research finding. The actual dry-land extent and the atoll's internal land/water granularity remain open for engineering and source follow-up.

## Territorial and protected-area meaning

FWS identifies Baker, Howland and Jarvis as separate named U.S. National Wildlife Refuge units. Its current pages distinguish their small terrestrial portions from extensive submerged refuge/monument areas: Baker 531 terrestrial acres of 410,184 refuge acres; Howland 648 of 410,999; Jarvis 1,273 of 429,853 (the Jarvis figure includes submerged protection extending 200 nautical miles). Palmyra's refuge includes associated waters/submerged lands out to 12 nautical miles; the Pacific Remote Islands Marine National Monument extends around it farther. These protected-area extents are not island/atoll dry-land outlines.

The names “Phoenix Islands” and “Line Islands” describe physical groupings in regional sources; they do not change these subjects' U.S. parent. Preserve the existing `UMI` parent and IDs. Do not combine Palmyra or Jarvis with Kiribati, or Baker/Howland with Kiribati's Phoenix Islands. No adjacent sovereign boundary is inferred from a coastline, refuge or monument line.

## Reproduction and limits

From the repository root, use Python 3.12 and install the exact pins into scratch inside this packet:

```sh
PACKET=data/regional-review/umi-island-land-boundaries-20261005
mkdir -p "$PACKET/.scratch/python"
python3.12 -m pip install --target "$PACKET/.scratch/python" -r "$PACKET/requirements.txt"
PYTHONPATH="$PWD/$PACKET/.scratch/python:$PWD/scripts" python3.12 "$PACKET/verify_twice.py"
rm -rf "$PACKET/.scratch"
```

The reproduction uses retained NOAA CUSP, four original NOAA project archives, OSM and pinned Atlas part 28/hierarchy bytes; it makes no network requests and writes deterministic `results.json`. Two runs on the PR base `f1a6c0abc29de7bf7b7a081a8a9864b0450c0427` produced identical result SHA-256 `893bf77dbebb58be2e267847e08b0aea0ee0c82d6d3d1743a6a87298f48768fa`. Positive and negative geometry controls pass. See `evidence-quality.json` for pinned baseline bytes, sources, file receipts, result bindings and explicit limits.

The OSM response is retained under ODbL 1.0 with attribution to OpenStreetMap contributors; the saved query is a reproducible equivalent tag/window query. The original request POST body was not retained at first retrieval, so this saved query documents how to repeat the screen, not an assertion of byte-identical query provenance. OSM is not authoritative. NOAA reports and datasets are old at three locations, and Palmyra's newer CUSP lines do not establish complete atoll coverage. Public FWS descriptive pages establish identity, protected-area meaning and dated approximate counts, but not current shoreline vertices or a complete islet inventory.

No IDs, geographic parent links, history, source release pins or production geography were changed. The source evidence supports an engineering reconciliation child for the mismatched outlines and further authoritative inventory research for Palmyra. That follow-up must preserve the U.S. reference-owner distinction from Kiribati and the unresolved shoreline/completeness limits.
