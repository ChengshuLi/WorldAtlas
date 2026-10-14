# Independent Timor/PNG source review

Reviewer `/root/borneo_owner_evidence`, distinct from evidence author `/root/timor_png_owner_evidence`. Source/custody/transcription review only. No treaty download, GIS or datum transform, locator-distance rerun, source/native producer, owner choice, repair or repository change.

**Disposition: usable as source-only acquisition pointers after the transcription corrections below. Not approved as geographic boundary predicates, current authority, owner clearance or qualification.**

## Actual independent checks

- Whole original PDF hashes and page counts checked: Timor signed scan SHA `8566efc4f097ad8af104aefa0170e58ec2630f3ce3000fae3dccc7a969130711`, 915,536 bytes / 29 pages; PNG Act SHA `80db589d7757f44cd3c58328f3b2215c31ebfe24088c9842a6265c97b0e53018`, 178,129 bytes / 4 pages; Timor factsheet SHA `7d2f8a0388a19483ef4c742dee44e5e449853e0759403adf6c374a5516e4001a`, 667,313 bytes / 2 pages.
- `exact-six-centres.json` SHA `099255b963b98c5b437e3169a5846987e6ea18b1bcdf74ffc2659e706be51c30`: all six original interval fields, owner/stable-ID and complete competitor lists match the frozen original outcome intervals 15–20. Independently compared exact rational longitudes and binary64 latitude/hex to the immutable native table at `5b32388df0501b013ac9a3ba97864932db493d59`, encoded SHA `ab0becdda100da3473d7bb5d34ccda6510aa1c0490c407082072c7201ad1e147`, decoded SHA `66db3d02ede56a75e9c58426ad1388552be3bf7e5e4477476f198983b7436d23`. No raster read.
- Visually read original page renders 1–3, 5, 8, 11, 13, 26, 27 and 29 and high-resolution point crops. Independently rendered page 8 directly from the authenticated original PDF using the existing bundled `pdftoppm`; `independent-original-pdf-page-08.png` confirms the corrected T307005 digit. No dependency installation.
- Independently extracted/read the actual PNG PDF's scheduled treaty, including Articles 1, 2, 9 and 11. All four pages are text-only; no chart is embedded. Saved extraction is `independent-png-act-extracted.txt`; hash/centre checks are `independent-source-input-checks.json`.

## Corrections and point transcription

The earlier southern Fatumean **256 m** value was based on misread T626 eastings; the original rows use **717xxx** eastings near T626009–011. It is superseded, not evidence for a remote location.

This review found another consequential transcription error: **T307005 is E726427.77, N8985381.65, class M**, not E726127.77. The author corrected the packet and reports northern Fatumean **39.903721 m**, superseding **36.36 m**. This review authenticates the corrected digits; it does not independently certify the author's scalar projection or distance arithmetic.

The five actual reported chord endpoint pairs read as follows (E/N, metres, each class M):

| Locator | Independently read endpoints |
|---|---|
| Balibo first cell | T504005 718363.88 / 8997460.27; T504006 718484.82 / 8997788.91 |
| Balibo second cell | T504004 718231.64 / 8997426.18; T504005 as above |
| Northern Fatumean | T307004 726634.37 / 8985391.20; T307005 corrected above |
| Southern Fatumean | T626011 717940.53 / 8977676.61; T626012 718027.56 / 8977425.29 |
| Tilomar | T702003 729081.12 / 8954389.50; T702004 729182.15 / 8953907.01 |

The review also found page-13 T626009 northing **8977799.83**, previously **8977799.85**, and T702005's correct page citation: **PDF page 14**, not page 13. Its coordinates 729274.10 / 8953788.54 match that page's first row. These ancillary points are not endpoints of the five reported nearest chords. The author corrected T626009; the author also corrected the page citation. Final locator JSON SHA `32151bdf8ae3ae14bbdf0bf0dea9d5a1719f6dc774e00ceb382bec732e699f06` passes all fifteen literal coordinate and page-citation comparisons in `independent-transcription-disposition.json`. The original PDF and images remain unchanged. All fifteen retained point-coordinate rows were visually inspected; the independent checks concern those literal coordinates and citations, not the locator projection/arithmetic.

## Treaty interpretation controls

[The signed 2005 agreement](https://www.gftm.gov.tl/wp-content/uploads/2021/01/3a.-TL-and-IND-Provisional-Land-Boundary.pdf) dates signature to 8 April at Dili and specifies entry 30 days later. Annex A declares CBDRF **ITRF2000/WGS84, UTM Zone 51 S**, with M median, RB paired river-bank and OF other-feature classes. Article 1 connects agreed points using Annex B's approximate mapping; Articles 2 and 7 preserve further definitive delineation work. Annex B adds approximate turning points and an interim band of **10 m on both sides**. Its index describes detailed 1:10,000 and 1:25,000 sheets; those detailed sheets are absent from this 29-page body. Annex C shows Dilumil/Memo and two Oecusse exceptions. Thus table adjacency is not an authenticated straight final boundary. The band is a treaty-scoped interim rule, not a numerical epsilon for other atlas operations. Even an unsigned chord distance exceeding 10 m cannot clear an owner without the actual connecting line, date/epoch and administrative/physical obligations.

The author's corrected reported chord distances are 3.09 / 33.99 / **39.90** / 12.92 / 8.06 m. They remain **unsigned, approximate locator results only**. No transform was rerun in this review. The [February 2026 factsheet](https://www.gftm.gov.tl/wp-content/uploads/2026/04/19123-FACT-SHEET-February-2026_Land-Boundaries_English.pdf) records a 2013 addendum and two remaining Oecusse segments. It is a dated summary, not authentication of a definitive line at these five centres or a latest-October-2026 status claim.

[The actual FAO-hosted PNG Chapter 85 reproduction](https://faolex.fao.org/docs/pdf/bi-21371.pdf) approves the scheduled Australia–Indonesia agreement. Article 1 separates northern marker-geodesic, Fly-thalweg and southern marker-geodesic branches. The retained PNG centre **140.94070169282057, −6.885633631960563** falls within the historical latitude span described for the Fly branch, near its southern end. This is a locator-scope inference only: neither 141°E nor 141°01′10″E can replace the intervening waterway. Article 2 requires periodic river imagery; Article 9 requires agreed determination of unresolved locations; Article 11 makes entry depend on ratification exchange. Signature is 12 February 1973; the PDF's 2025 conversion metadata is not treaty/Act enactment or effective-date proof. No named datum or annexed chart was found in this body.

## Specific next source bodies

1. Complete Annex B detailed main-border sheet(s) and turning-point records containing T504004–006, T307004–005, T626011–012 and T702003–004. Do not infer sheet numbers from point prefixes. Acquire applicable definitive delineation/demarcation records and the 2013 addendum with full coordinates and scope, then authenticate the common reference frame/epoch and transformations.
2. Full UU3/2013 attached Malaka formation map and complete Permendagri80/2018 Malaka–Belu coordinate/map annex, including its TLS terminal join; exact TLS Balibo/Fatumean/Tilomar administrative mapping and source-vintage joins. The saved formation-law artifact is correctly labelled a normalized web excerpt, not original full HTML; no exact lower-tier ownership follows from it.
3. PNG treaty annexed chart and relevant 12-Feb-1970 joint-survey report, plus applicable refreshed Fly-thalweg geometry around the exact centre and dated PNG Lake Murray LLG / Indonesia Merauke administrative binding. Retained queue `land` is not a new river/water determination.

The UN PDF remains unavailable. `acquisition-blockers.json` records web HTTP403 and two automatic approval denials before execution: the reviewer treated the trusted task's no-fetch restriction as controlling and did not accept the later assistant clarification. No UN file exists. This review made **no further download or retry**. Reading the already-preserved FAO equivalent completes the available treaty-text review; it does not supply the missing chart or current survey. No clearance, exclusion, qualification or acceptance is supported by this packet.
