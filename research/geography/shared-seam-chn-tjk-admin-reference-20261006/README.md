# Modern administrative-source availability: China–Tajikistan seam

This packet evaluates modern official administrative identity and whether an accessible, appropriately detailed and reusable official boundary product was established for the three exact #1096 subjects. It does not repeat #1099's source-versus-Atlas overlay and does not determine the international boundary, land/water status, legal authority, or territorial assignment.

## Finding

Official government and statistics sources support the present-day administrative identity and parent context described in `crosswalk.json`. They do not provide a verified joint geometry product for these three units. China's National Fundamental Geographic Information Center (NGCC) catalogue advertises 1:250,000 public geographic data and county polygon layers, but the cited catalogue page's version, applicable product terms, and precise boundary vintage could not be established from retrievable product documentation. Tianditu's administrative search/API material describes names, codes, levels, centers and bounding boxes, not a redistributable boundary-vector download. Tajikistan's official Statistics Agency supplies counts/tables, while its geoportal describes cadastral parcel lookup; neither establishes downloadable district boundary vectors. Accordingly, no new geometry comparison is supported by this packet.

This is a bounded “not established” result, not proof that no geometry exists. The missing evidence is a named national product with a retrievable vector package, exact vintage and scale/precision metadata, and terms explicitly applicable to retained redistribution. The 1:250,000 China catalogue is a lead for a separately approved follow-up; do not treat an online basemap, geocoder, cadastral lookup, or map image as source geometry.

## Identity evidence

The exact Atlas IDs remain those in the issue contract. For China, official county government portals identify 阿克陶县 (Akto County) within 克孜勒苏柯尔克孜自治州 (Kizilsu Kyrgyz Autonomous Prefecture) and 塔什库尔干塔吉克自治县 (Tashkurgan Tajik Autonomous County); the latter county's government portal identifies itself under 喀什地区 (Kashgar Prefecture). The Atlas labels `Anketaoxian` and `Tashenkuergantajike` are upstream transliterations, not official English names. An official Xinjiang code list published in 2010 lists Akto 653022 and Tashkurgan 653131, with prefecture codes 653000 and 653100. These are historical code references, not asserted as the latest 2026 code registry.

For Tajikistan, the President's official 2026 GBAO trip record names Murghob among districts in the Gorno-Badakhshan Autonomous Region. The official Statistics Agency workbook retained here is titled “Number of administrative area units as of January 1, 2025”; it supplies administrative counts, not boundary geometry. Its English column labels are preserved literally in the machine-readable output, including the dash in the `Districts` column. The packet does not reinterpret an ambiguous translated header as a different unit class. Its published web page carries a CC BY 4.0 reuse notice. The workbook is retained with its whole XLSX bytes; its package-member inventory and decoded size are recorded in `sources/source-inventory.json`.

## Reproduction and limits

`scripts/inspect_admin_table.py` reads the retained XLSX with Python's standard library and checks the workbook title, date and exact GBAO row cells. A negative control mutates the value under the literal `Regions` column and verifies that the same acceptance predicate rejects it. Execute it after committing the exact code, twice, and preserve both complete JSON outputs. It does not reclassify the publisher's column values, infer Murghob's outline or calculate geographic metrics.

The baseline is main commit `d79cf13a564fbdeb5895fef4725cc2968d5be9d1`. It pins the actual grid and hierarchy files, the full immutable report file containing the inherited fragment, and the exact containing feature files for all three IDs. The fragment's ID and canonical full-feature hash are separately identified in `crosswalk.json`; the feature hash is not misrepresented as a whole-file digest.

No PDF, raster or vector boundary file was acquired. The identified 12.48 MB Tajik PDF remains outside this packet. China product rights/precision and Tajik vector availability remain unresolved. None of these administrative references establishes an international boundary or physical gap classification.

## Sources

See `crosswalk.json` and `sources/source-inventory.json` for URLs, source roles, dates, terms and limits. Official source pages are linked rather than copied wholesale. Retrieval date for this packet: 2026-10-06.
