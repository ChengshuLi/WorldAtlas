# Zambia–Zimbabwe boundary and water-source follow-up

This versioned follow-up adds primary boundary law and a contemporaneous boundary study to the source-only evidence in the parent packet. It does not replace, edit, or reinterpret the first packet's component measurements. Its purpose is to make the controlling boundary description, map-sheet custody trail, and remaining source request concrete for the same ten components and four recorded contact subjects.

## What the new records establish

The official *Northern Rhodesia and Southern Rhodesia (Boundaries) Order in Council 1963* was made 20 December 1963 and took effect 1 January 1964. Its schedule describes the river boundary primarily by the Zambezi medium filum and by channels around named island groups; it separately defines the Lake Kariba reach with straight-line points. It says the described boundary is shown on maps signed and dated 19 December 1963 and deposited with the Surveyors General of Northern and Southern Rhodesia. The schedule lists 1:50,000 sheets including Federal Surveys 1529 C3, 1529 C4, 1628 B2, 1628 B4 and DCS 1530 SW1/SW2, among others. These legal and custody statements are substantially more direct than regional summaries, but the text does not expose the map images or provide registered coordinates for the ten Atlas components.

The U.S. Department of State's 1964 *International Boundary Study No. 30: Zambia (ZA) & Zimbabwe (ZI)* reproduces the map-sheet list and gives approximate whole-minute coordinates for several named islands. The listed positions are regional orientation only. The report does not identify any of the ten components or four contacts, provide positional accuracy, or establish present physical water or bilateral boundary interpretation.

The IDE-JETRO library catalogue identifies Zimbabwe Surveyor-General 1:50,000 topographic sheets by sheet number and title, including 1529 C3 (Nyakasanga), 1529 C4 (Rukomechi), 1530 C1 (Mupata Gorge), 1530 C2 (Kanyemba), and 1628 B2 (Chirundu). Its catalogue describes a 1967–1991, 564-sheet series. Those records help locate later topographic sheets; they do not establish that the catalogue copies are the signed 19 December 1963 boundary maps. Neither scan was found in the public catalogue results inspected for this follow-up.

## Physical-water evidence and limits

No newly located source supplied dated, candidate-scale water polygons or imagery for the ten component footprints. The ZAMWIS public description says the information system holds historical and contemporary spatial, hydrological time-series, and Earth-observation information, but the public page inspected did not expose a downloadable candidate-scale dataset or item-level metadata. A public Zambia national geospatial service directory was also inspected; its indexed services did not expose an explicitly named basin-wide river-water dataset. This is a discovery limitation, not evidence that either institution lacks suitable data.

The first packet's independent Natural Earth major-lake reference remains a limited diagnostic and is not complete river/water coverage. Keep `water_status` unverified, retain `touches_reference_shore: false`, and keep all ten component classifications at mixed evidence. The added legal text cannot decide whether an individual component is river water, an island, a bank, or an administrative geometry artifact.

## Durable handoff and resume condition

The next source step is an acquisition request to the current Surveyor-General offices in Zambia and Zimbabwe for the signed 19 December 1963 deposited maps, especially the listed 1:50,000 sheets intersecting the issue extent. Request the original sheet editions, scan provenance, scale, datum/projection, control points or registration notes, stated positional accuracy, map rights/reuse terms, and any later jointly accepted boundary plotting. The precise map-sheet-to-component coverage must be confirmed from sheet indexes or the map images; it must not be inferred from the coarse island coordinates or sheet names alone.

For physical water, request from ZAMCOM/ZAMWIS or the Zambezi River Authority (ZRA) date-stamped hydrography or Earth-observation layers covering all ten component footprints and four contacts, including acquisition dates, spatial resolution/scale, vertical or shoreline reference where applicable, processing lineage, coverage gaps, and license. Ask for the historical dates relevant to the Atlas inputs, not only current flow or reservoir summaries. No request has been sent from this packet.

**Resume condition:** continue when a custodian supplies the source bytes or a stable public item/API with sufficient metadata and lawful reuse terms. Then authenticate and preserve the originals, register each image/layer to a declared CRS with documented control and error, compare all ten components and four contacts against both source dates/products without altering the original geometries, and retain the unknown classifications unless the evidence directly resolves the specific question. If no source is supplied, leave the issue open with the present findings and this named custodian/data request as the handoff.

## Captured source files and rights

The UK Order PDF under `sources/` is a byte-identical download from the official legal record. The legislation text is available for reuse under the Open Government Licence v3.0, subject to any identified third-party material; the PDF is used with attribution. The U.S. Department of State study is cited at its stable host URL but is not copied into the repository because reuse terms for the host's scan/format were not established. Hashes and source roles are in `source-inventory.json`.

The previous exact evidence manifest is preserved byte-for-byte as `prior-evidence-quality.json` (SHA-256 `105c411d0e3354f0ffda965e9ff626feb9baaf2f78b10667df49784918bd79f1`). The root evidence manifest is refreshed for this PR so the trusted checker can account for all added files; the first packet's source, run, control, and finding files remain unchanged.

## Source references

- The National Archives, [1963 Order in Council, official PDF](https://www.legislation.gov.uk/uksi/1963/2083/pdfs/uksi_19632083_en.pdf); reuse information at [legislation.gov.uk contributors and reuse](https://www.legislation.gov.uk/contributors).
- U.S. Department of State, Office of the Geographer, *International Boundary Study No. 30: Zambia (ZA) & Zimbabwe (ZI)* (1964), [PDF hosted by Florida State University Law Library](https://library.law.fsu.edu/Digital-Collections/LimitsinSeas/pdf/ibs030.pdf).
- IDE-JETRO Library, [Zimbabwe topographic map catalogue and sheet index](https://d-arch.ide.go.jp/map/mokuroku/mokuroku-689.1-AM-1%26category-103.html).
- Zambezi Watercourse Commission, [ZAMWIS description](https://www.zambezicommission.org/zamwis); [Zambezi River Authority](https://www.zambezira.org/).
- Zambia National Geospatial Data Register, [public catalogue entry point](https://ngdr.gsb.gov.zm/); linked [ArcGIS REST service directory](https://www.map.gov.zm/arcgis/rest/services?f=pjson).
