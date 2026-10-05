# Guinea-Bissau sector roster reconciliation (#812)

Research snapshot retrieved 2026-10-05 UTC. This is a review packet for the 39
existing `gb:GNB:ADM2:<geoBoundaries shapeID>` subjects. It does not authorize
or propose a geography import and does not certify a legal boundary.

## Finding

The official UN Second Administrative Level Boundaries (SALB) Guinea-Bissau
page identifies DGGC (Direcção Geral de Geografia e Cadastro) as the national
geospatial authority and links a validated administrative-units layer. The
SALB REST layer describes first- and second-level units, says its data are
suitable at 1:1,000,000, and gives a temporal range of 2016-01-01 through the
last verification/update (2021-09-02). Its query returns 39 features and its
ADM2 codes run from `GNB001001` through `GNB009005` with gaps by parent.
The layer has eight regional ADM1 parents and one autonomous Bissau parent;
all 39 SALB ADM2 rows are included in `crosswalk-screen.csv`.

The 2024 UK PCGN factfile says there are eight regions plus one autonomous
sector, then describes 39 sectors at ADM2 level and points to the UN SALB
roster as supplied by DGGC. The Guinea-Bissau 2025 National Communication to
the UNFCCC instead says the eight regions are divided into 36 sectors and
lists Bissau as a separate autonomous sector. The latter is a 36-region-sector
count, with Bissau separate; it does not name its 36 sectors. SALB/PCGN's 39
ADM2 records include the Bissau autonomous feature, leaving a difference of
two among non-autonomous regional sectors (38 versus 36). Separating Bissau
accounts for one count convention, but does not reconcile the remaining two.
No accessible primary roster or effective-date instrument was found to
identify which two regional units account for the difference. Do not infer
that the 2025 36-unit roster is complete at 36 or that the SALB 39 rows are
current in 2025.

Within SALB, `GNB008001` is named “Sector Autônomo de Bissau” at ADM2 and is
under ADM1 code `GNB008`, named “Sector Autonomo de Bissau”. The 2025
government count explicitly treats Bissau separately. The exact Atlas parent
is `framework:province:bissau:8673c43d44f4`. It is the ADM2 feature for the
autonomous sector, not a ninth region; the codes show parent and child levels,
even though the parent and child names refer to the same autonomous entity.

## Crosswalk method and limits

`reproduce.py` binds the old geoBoundaries GeoJSON and the 2026-10-05 SALB
GeoJSON by exact byte hash. For each of all 39 old source IDs, it emits the
Atlas subject ID and declared parent, names equivalent after removal of the
generic `Setor`/`Sector` and `de` tokens plus Unicode accent/punctuation and
token-order normalization, the greatest overlap from the repository's
`worldatlas-evidence-geometry-v1` WGS84 straight-source-edge ellipsoidal
area helper, the reciprocal area share for the top candidate, and the three
greatest-overlap SALB candidates. The overlap screen uses EPSG:4326
longitude/latitude GeoJSON and the shared helper; it is not a legal-boundary
normalized-name candidate and an area candidate are separate
observations. `screen-consistent-name-and-parent` means only that the
normalized name candidate, greatest overlap, and Atlas/SALB parent names
agree; every other row is `review-required`. Neither result establishes legal
identity, authoritative parentage, or completeness. The inputs differ in
source vintage/lineage (geoBoundaries 2017 OSM/Wambacher-derived, versus SALB
temporal validity ending 2021-09-02), and their geometries may have changed.
The screening table is a candidate crosswalk, not a forced one-to-one mapping.
`salb-roster.csv` records all 39
exact SALB ADM2 IDs, names, ADM1 codes/names, and boundary-touching SALB
neighbor codes. Boundary-touching is a strict geometry screen and does not
represent every administrative or maritime neighbor.

The earlier #472 packet's parent-name relationship is retained verbatim as
Atlas's declared parent. SALB `adm1cd`/`adm1nm` are the authoritative roster
parent fields available in this snapshot. The old packet's separate
`overlay_parent_name` is a spatial-screen result, not a legal source parent;
neither overlay field should be substituted for the retained hierarchy.

The 39-row crosswalk screen has 21 rows where normalized name, largest-area
candidate, and parent name agree, and 18 requiring review. For example,
geoBoundaries `Setor de Boe` (Atlas parent Cacheu) has a normalized SALB name
candidate `Boé` under Gabú, while its largest overlap candidate is `Caió`
under Cacheu. `Setor de Tite` has a Tite name candidate under Quinara but its
largest overlap candidate is Bolama/Bijagós. These are vintage/identity
conflicts to investigate; neither name nor overlap alone determines the
current legal unit. Row-level vintage, license, completeness and uncertainty
fields are included for both source rosters, together with exact IDs/parents.

## Source register, hashes, and terms

| Evidence | Retrieval / vintage | SHA-256 | Rights and use |
| --- | --- | --- | --- |
| Existing geoBoundaries GNB ADM2 GeoJSON, parent packet | pinned 2017; baseline `6b60f1598b7b1f222b671cb57e12561fd3c3fb93` | `8839091ee5599651642efc6f8ac65d82a4f40e779bd38debedfd417649bfc680` | ODbL 1.0; keep its attribution and share-alike obligations. |
| UN SALB GeoJSON item `59a87026ba7c4e718c330817fa459789` | official item response retrieved 2026-10-05 UTC; layer validity 2016-01-01–2021-09-02 | `aa5bcf549d10140e372012484c355a4f794fa304a87f225c7d95d3ebafc4cd28` | SALB Terms of Use: non-commercial use only; attribute DGGC and “from SALB Data, United Nations”; do not change geometry/content without contributor consent. Exact source bytes are restored by URL and hash, not redistributed in this packet. |
| UN SALB Guinea-Bissau country page | retrieved 2026-10-05 UTC | `fb26244440e95148c66e9f9dd9dc38dce3d974f7a1b538e7dd350fcf4ce87a93` | Identifies DGGC and links the validated units layer; its broad page-level start date differs from the more specific REST layer metadata. |
| UN SALB Terms of Use 2021 | retrieved 2026-10-05 UTC | `aaac013743486c9f4be986e236fdba6b3a4ac0ff00921cecc171c42778544381` | Primary evidence for the non-commercial restriction, attribution and geometry/content terms; cited, not redistributed. |
| SALB REST layer metadata JSON | downloaded 2026-10-05 UTC | `56f9bd7057a567d07f1db11c463f63f7c174b02daee7f38d23c75836d5250cd1` | Public service metadata; cite DGGC/SALB/UN. |
| UK PCGN Guinea-Bissau toponymic factfile PDF | official UK government asset, retrieved 2026-10-05 UTC; file is the 2024 factfile | `2ba9d5a71da25fc8c173da80be134381e91001c0873518bfa50d4c040df54dbf` | Crown copyright / Open Government Licence noted in the factfile. Cited, not republished. |
| Guinea-Bissau NC4 under UNFCCC | submitted 2025-11-17; retrievable official record/PDF URL below | `4481f2a8346c7b71d6ffb5e7b6badc504ac4271c61982ea82d9ed2306b12a694` | The saved retrieval copy is a mirror whose bytes exactly match the SHA-256 retained in the earlier #472 official-context record; direct official PDF URL returned an anti-bot response during this retrieval. Cited as official filing; no source text is republished. |

The SALB web page exposes a general administrative-data validity range of
2000-01-01 to its last update, while the service layer metadata specifically
describes this layer's validity as 2016-01-01 to 2021-09-02. The current item
response is 410,290 bytes and is hash-pinned in `sources.json` and the evidence
manifest. A prior 411,079-byte response observed on 2026-10-05 had a different
file hash. A local comparison found the same 39 exact ADM2 IDs, names, and ADM1
parents; all 19,642 coordinate values matched when rounded to nine decimal
places, with 16,346 serialized numeric values differing and a maximum absolute
difference of 5.684341886080802e-14 degrees. Treat this as a serialized-source
version observation, not evidence of legal boundary continuity. The older raw
snapshot was not retained because the SALB terms restrict geometry
redistribution; its exact byte sequence is no longer restorable from the URL.
The script uses the currently restorable 410,290-byte response, rejects any
other bytes, and records the older retrieval only as a bounded comparison.

The service layer metadata specifies the temporal range used for the 39-row
roster; the broader country-page 2000 start is retained as a page-level
observation, not an inferred geometry start date. The endpoint's copyrightText
credits MITC/DGGC and the SALB programme, United Nations. SALB's terms disclaim
completeness and warranty. This packet does not treat an official source as
proof of completeness.
Restoration: fetch the GeoJSON from
`https://geoportal.un.org/arcgis/sharing/rest/content/items/59a87026ba7c4e718c330817fa459789/data`
and verify 410290 bytes and SHA-256 `aa5bcf549d10140e372012484c355a4f794fa304a87f225c7d95d3ebafc4cd28` before use. The prior 411079-byte response is not restorable by that URL and is not an input to this version of the packet. Fetch layer metadata from
`https://geoservices.un.org/arcgis/rest/services/Hosted/SALB_GNB/FeatureServer/0?f=pjson`.
For the PDFs use the URLs recorded in `sources.json`. For NC4, prefer the
official record `https://unfccc.int/documents/654402` and official PDF
`https://unfccc.int/sites/default/files/resource/GNB_NC4_English_FINAL_16112025_JLT.pdf`;
at retrieval the direct URL was anti-bot blocked, so match any restored copy
against the recorded digest before relying on it.

## Reproduction

This reproduction was run with Python 3 and Shapely 2.0.7, pyproj 3.5.0, and
NumPy 1.24.4. The script enforces those exact versions. They differ from the
repository's general preparation pins in `requirements.txt`; the configured
package mirror did not offer the repository's newer versions during this
review, so the general preparation environment was not used for this run.
Run in a disposable environment containing the three versions above from the
repository root:

```sh
python data/regional-review/west-africa-guinea-bissau-sector-roster/reproduce.py /path/to/restored-salb.geojson --output data/regional-review/west-africa-guinea-bissau-sector-roster/crosswalk-screen.csv
```

The script rejects either a SALB or geoBoundaries byte mismatch, rejects
runtime-version mismatches, and rejects source roster counts other than 39.
The #472 `subject-assessments.csv` used for Atlas parent/source metadata is
pinned by commit, exact byte count, and SHA-256 in the evidence manifest. The
numeric measurements in `crosswalk-screen.csv` and all aggregate metrics are
bound to `summary.json` and enumerated in `summary-metrics.csv`; exact rendered
line templates are recorded in the evidence manifest. `salb-roster.csv` is a
full-row-hash-bound source ID and neighbor ledger. It uses the shared geography helper and verifies positive and negative
known-geometry controls before writing outputs. The saved outputs can be
byte-compared with a rerun. The control shapes are synthetic and establish
method behavior only, not source correctness.

## Remaining action

Request a dated DGGC roster or official effective-date instrument explaining
the 36-versus-38 non-autonomous count and identifying any added, merged,
renamed, or retired sectors. Then review all flagged rows and geographic
neighbors with primary evidence before any engineering change. No correction
to Atlas IDs or parents is proposed by this packet.
