# Jamaica source-relative interpretation, 16 October 2026

## Accepted scope proposed for review

The complete original queue package contains 2,251 land-support candidate cells
in 767 half-open intervals. All fourteen source parish features, all fifteen
polygon components, original shapeIDs, owner indices, source ordinals and target
joins are retained. The independent 446-cell physical-interpretation companion
is excluded. The final proposed delivery is all 2,251 exact cells to the fourteen existing
2011-reference parish targets, including all 381 original Saint Catherine cells.
There are zero final holds within this repair package.
No current fourteen-parish inventory or national island-completeness claim is made.

The existing selected targets explicitly describe named parish territories, not
municipal corporations, and retain reference_year 2011. Source-family and target
identity remain unchanged. Kingston and Saint Andrew remain separate reference
parishes despite joint municipal administration. The ministry confirms that
relationship, but its prose is not survey-boundary evidence:
https://www.localgovjamaica.gov.jm/local_govt_entity/kingston-st-andrew-municipal-corporation-ksamc/

## Material Portmore source-vintage question

The 2011 represented source predates the 2025 Counties and Parishes amendment.
Passage, commencement, parish territory and electoral implementation are distinct.
The JIS Senate account dated 1 March 2025 describes inclusion of Hellshire Hills,
Goat Island and the city, with exclusions including Lakes Pen, Grange Lane,
Lime Tree Grove and Quarry Hill. It is a primary government account of passage,
not the authenticated operative boundary instrument:
https://jis.gov.jm/senate-passes-legislation-for-portmore-parish-designation/

The OPM statement of 31 March 2025 reports a consent order lifting an injunction
and further constitutional work. It does not establish an operative commencement
date or provide the court order or survey geometry:
https://opm.gov.jm/government-of-jamaica-welcomes-positive-supreme-court-decision-on-portmore-parish-law/

ECJ's 2 June 2026 statement describes technical electoral-boundary proposals for
Portmore and Saint Catherine following parliamentary instruction, with further
GIS validation and recommendations for parliamentary determination. It concerns
constituency realignment and is not a replacement parish polygon:
https://www.ecj.com.jm/ecj-presents-electoral-boundary-realignment-proposal-for-new-portmore-parish/

The parliamentary Joint Select Committee report is dated October 2021. Its
printed page 12 says the committee could not decide the proposed boundaries,
which were outside its terms of reference; printed page 21 discusses the section
67 process and full legal effect. This committee report is not the operative
2025 boundary instrument. The independent reviewer visually inspected these pages:
https://japarliament.gov.jm/attachments/article/2497/Report-of-the-Joint-Select-Committee-Appointed-to-Concider-And-Report-on-the-Motion-for-Consideration--of-a-Proposal-that-the-City-Municipality-of-Portmore-Becomes-the-15th-Parish-of-Jamaica.pdf

No authenticated operative boundary/commencement instrument was obtained. That
limits any current-law claim; it does not contradict the original 2011-reference
source ownership. The ministry's 19 June 2026 account of the 17 June ministerial
speech describes Portmore as preparing to become the fifteenth parish:
https://megid.gov.jm/government-advancing-j3-4b-in-urban-road-improvements-under-capex/

The unchanged targets explicitly retain reference_year 2011 and each original
parish shapeID. All 381 Saint Catherine cells uniquely join that same original
source owner, including 173 cells in polygon component 0 and 208 in component 1.
No contradictory source-era ownership evidence was found. The established
source-relative restoration contract does not require certification of later
current-law boundaries. Therefore all 381 are included in the final restoration,
with the same limits as the other parishes. They are not assigned to a newly
invented Portmore owner, and no contemporary parish boundary is reconstructed.

A provisional complete-source Saint Catherine hold was explored before distinct
contract review. That conservative proposal added an inapplicable current-law
gate and is superseded. Its `authority/`, `composition/`, original
`source-evidence.json`, `candidate-native-patch.json`, `native-diagnosis-held.json`
and `queue-disposition.json` remain prior, unselected review evidence only.
The final authority is `authority-reference/`; the final disposition is
`queue-disposition-reference.json`. The final 2,251-cell proposal has no holds
based solely on later Portmore commencement uncertainty.

## Custody, dates, licensing and completeness

The authentic simplified geoBoundaries product is consumed unchanged from the
existing corpus: 15,370 gzip bytes, SHA-256
baec92db07d66e43209a6079a1299f485942b445a922f61535d33c8633deec3e;
52,832 decoded bytes, SHA-256
4c7aab86ba321018d45cce317dba6faa1c9a801ca8f5c8df436f9cd76335dbec.
Its retained URL is the simplified product at geoBoundaries commit 9469f09;
the unsimplified product is not substituted:
https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/JAM/ADM1/geoBoundaries-JAM-ADM1_simplified.geojson

The recorded metadata says represented 2011, source update 19 January 2023,
build 12 December 2023, OpenStreetMap/Wambacher, parish, and Creative Commons
Attribution-ShareAlike 2.0. Those dates are preserved in
`source-metadata-custody.json`; represented year does not prove extraction date.
OSMF confirms archived pre-September-2012 data retain CC BY-SA 2.0, but that
does not establish this product's extraction date. More directly, the exact
upstream `sourceData/gbOpen/JAM_ADM1.zip` at commit 9469f09 contains a contradiction:
`meta.txt` declares CC BY-SA 2.0, while its bundled `license.PNG` says OSM data are
ODbL and documentation is CC BY-SA 2.0. The source `.shp.xml` records processing on
5 October 2017. The screenshot was visually inspected. The exact release
CITATION-AND-USE document states CC BY 4.0 for geoBoundaries derivative works and
requires underlying source citations; it does not override underlying terms.
Whole archive/member hashes are in `license-provenance.json`. These original
statements are preserved without resolving the disputed extraction/license
vintage or claiming verified CC BY-SA licensing.

`../ATTRIBUTION.md` credits OpenStreetMap contributors, Wambacher and geoBoundaries,
links the ODbL, CC BY-SA 2.0 and CC BY 4.0 terms, preserves applicable share-alike
obligations, and identifies the publicly available original and modified database
inputs/results. No source bytes or original metadata are silently relicensed.
No raw parliamentary map, contextual municipal polygon or licensing screenshot is
redistributed in this packet.
https://osmfoundation.org/wiki/Licence/Licence_and_Legal_FAQ
https://www.openstreetmap.org/copyright
https://osmfoundation.org/wiki/Licence/Attribution_Guidelines

JIS's undated parish profiles describe the traditional parishes and offshore
islands/cays. They help explain the reference interpretation and national coverage
limit but cannot certify a 2026 parish inventory. Fourteen source features do not
prove all Jamaican islands are represented. Omitted offshore coverage is neither
assigned to a guessed parish nor silently declared complete:
https://jis.gov.jm/information/parish-profiles/

## Physical witnesses and exact native outcome

The unchanged whole-target physical interpreter authenticated 188,612 original
GSHHG metadata records and the complete 95,809,336-byte native member, selecting
29 relevant records. All fourteen complete original Jamaica target queries ran
with Shapely 2.1.2 / GEOS 3.13.1. Six missing/extra reconstruction witnesses on
three targets remain explicitly retained. Stock native diagnosis tested the
complete family and every actual physical/residual/hierarchy/water predicate:
all 2,251 candidate centres passed before the territorial hold. No witness was
suppressed or geometry repaired. The provisional exclusion diagnostic partitions 1,870/381, but it is superseded
by the source-relative contract decision above. The final genuine stock constructor
qualifies all 2,251 cells, retaining all fourteen original source competitors.

Authenticated selected base native rows and accepted additive intervals were
read for all 424 affected rows: zero base-nonzero or accepted-additive overlap.
The separate final emitted loader/picker/sampler and hosted integration checks
remain required. Source membership, custody, physical support and constructor
qualification are distinct from actual selected acceptance or publication.
Original regional source reviews #178 and #179 remain separate and open.
