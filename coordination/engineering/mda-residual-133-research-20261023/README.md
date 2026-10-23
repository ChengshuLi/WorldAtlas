# MDA residual source-applicability research

This is an evidence checkpoint for the 133 still-held cells in the original
`gb-MDA-ADM1--repair-evaluation` package. It does not change owners, holds,
qualifications, repairs, or the 1,986-cell / 539-interval / 16-owner original
denominator. The earlier accepted 1,853 repairs remain a separate accepted
partition.

## Original evidence and remaining partition

The retained 2020 MDA source comparison records 1,899 cells with a unique
archived MDA target and 87 outside that archived family. Within the 133
residual cells, the existing evidence separates 46 cells with an MDA source
match and UKR contact, 65 MDA-only cells outside the archived MDA family, and
22 UKR-contact cells also outside the archived MDA family. The retained
original UKR family has 27 features and the ROU family has 42; the source-key
join reports 68 UKR contacts and zero ROU contacts. These are bounded
source-family comparisons, not a current worldwide competitor census or a
legal-boundary finding. See `mda-source-applicability-independent-assessment.json`,
`source-version-key-comparison.json.gz`, and `mda-retained-witness-join.json.gz`
for the preserved inputs and method limitations.

## Newly examined official proposal

The Romanian-language Moldovan government announcement was retrieved during
this review from:

`https://www.gov.md/ro/comunicate-de-presa/guvernul-prezentat-propunerea-noii-harti-administrativ-teritoriale`

The saved response was 70,680 bytes, SHA-256
`e9ad8ecd6da1e9a4c9893fbde932b896a792d19e8c55ac20d95bb16830546d58`.
Its text describes the administrative map as a government proposal (273
municipalities and three regions); it says the initial legislation is still
to be consulted on, then considered by Government and sent to Parliament, and
that transition planning remains. The announcement identifies the page
content as CC BY-SA 4.0. The aggregate figures below are an adaptation of
that proposed map data and are attributed to the Government of Moldova. The
underlying data is identified on the source site under the
[Creative Commons Attribution-ShareAlike 4.0 International license](https://creativecommons.org/licenses/by-sa/4.0/); these aggregate figures are shared under that same license.

The linked map-data response at
`https://primariiputernice.gov.md/harta/date/harta.js` was 3,579,256 bytes,
SHA-256 `70ac11f7f9c75f22a00d0a6b35def8e34cbc5730e5694243c0ebe73ee7f2e826`;
this matches the earlier HTTP 200 retained readback in
`research/primary-readback-004.json`. Its proposed cluster layer contains 273
features. A bounded, local center-to-proposed-cluster comparison was already
performed for the three residual groups. Its aggregate counts were 32 of 46
for the MDA-match/UKR-contact group, 41 of 65 for the MDA-only nonmatch group,
and 5 of 22 for the UKR-contact nonmatch group; 55 of 133 had no proposed
cluster hit and none had multiple hits. These partial, mixed matches do not
settle any group. No per-cell placement, coordinate, or raw proposal geometry
is included here. The per-key overlay output was not retained, so it is not
available for the independent cross-tab suggested in the review; the overlay
will not be rerun merely to produce that cross-tab. The proposal is not a
replacement for the 2020 consumed MDA source, does not identify the legal
status of individual disputed cells, and does not qualify any repair or
unresolved disposition.

## Outcome and next evidence step

No residual key is reclassified. All 133 remain pending under the original
contract. The reviewer recommended a non-geometric cross-tab of any retained
proposal-overlay results against original target names and source feature
identifiers, followed by source-context review only for affected targets.
That per-key overlay output is unavailable in the bounded local evidence; do
not recreate it because the proposal cannot establish source-version
applicability.

A separate non-geometric cross-tab of the **retained original disposition
intervals** against the **retained 2020 source-version comparison** expanded
and matched all 1,986 cells, with zero missing keys and zero target-name
mismatches. It did not rerun a geometry operation. This locates the residual
source patterns by original target:

| Original target | MDA-only archived-source nonmatches (65) | MDA match with UKR contact (46) | UKR contact outside archived MDA source (22) |
| --- | ---: | ---: | ---: |
| Cahul | 5 | 5 | 2 |
| Cantemir | 13 | 0 | 0 |
| Causeni | 3 | 6 | 1 |
| Cimislia | 0 | 0 | 1 |
| Edinet | 2 | 0 | 0 |
| Gagauzia | 0 | 1 | 2 |
| Leova | 1 | 0 | 0 |
| Soroca | 0 | 2 | 4 |
| Stefan Voda | 37 | 21 | 1 |
| Taraclia | 0 | 5 | 0 |
| Transnistria | 4 | 6 | 11 |
| **Total** | **65** | **46** | **22** |

The affected target labels are linked to the exact archived MDA feature
identities as follows. These are properties from the retained 2020 source
inspection, not new geometry findings:

| Target / ISO | Archived MDA source feature ID | 65 nonmatches | 46 MDA + UKR | 22 UKR outside MDA |
| --- | --- | ---: | ---: | ---: |
| Cahul / MD-CA | `25212430B51059014460141` | 5 | 5 | 2 |
| Cantemir / MD-CT | `25212430B81482951983667` | 13 | 0 | 0 |
| Causeni / MD-CS | `25212430B31479954216778` | 3 | 6 | 1 |
| Cimislia / MD-CM | `25212430B51243918943413` | 0 | 0 | 1 |
| Edinet / MD-ED | `25212430B65458906379390` | 2 | 0 | 0 |
| Gagauzia / MD-GA | `25212430B55748044124793` | 0 | 1 | 2 |
| Leova / MD-LE | `25212430B269818099865` | 1 | 0 | 0 |
| Soroca / MD-SO | `25212430B70903588336793` | 0 | 2 | 4 |
| Stefan Voda / MD-SV | `25212430B10989766506063` | 37 | 21 | 1 |
| Taraclia / MD-TA | `25212430B43456438192105` | 0 | 5 | 0 |
| Transnistria / MD-SN | `25212430B22111314945643` | 4 | 6 | 11 |

The join uses `mda-disposition.json.gz` (SHA-256
`1b4f5609a69c68002a11accc0a21873e011b90e7e9603ad4595bb2f01ef1bd74`; Git
blob `84e7454b0cd4af9e44cea2ab3f3fece9e7911df7`) and
`source-version-key-comparison.json.gz` (SHA-256
`eafea1576d7b5e28e4e9f3a2ec43743b07e296f7500586e731639afa2dfe681b`; Git
blob `db6472f961e451784175d2c832f8216c53b6d937`). Feature identity rows
come from `source-identity-clarification.json` (SHA-256
`b8accc6866f2bf6af77ebe3515a002884dc57bb92d869e28d7ee03cdde17d421`). This
finite name/count cross-tab does not establish source applicability, legal
status, or a positive repair; no key-level location is included.

## Additional official source-context examination

The Moldovan Energy Projects Implementation Unit's December 2023
environmental and social assessment for the Vulcanesti–Chisinau transmission
project was examined through its published text, especially printed pages
58–59: <https://www.ucipe.gov.md/sites/default/files/2025-08/final-report-esia-esmp-for-400-kv-ohtl-vulcanesti-chisinau-specific-for-taraclia-district-december-2023.pdf>.
It describes Taraclia as a Moldovan administrative district with 26 localities
in 15 level-I units, states that it borders Gagauzia, Cahul and Ukraine's
Odessa region, and describes its two separated parts. The report cites Law
764/2001 for the administrative framework. This supports the plausibility of
MDA/UKR adjacency in regional context, including the five Taraclia residual
contacts in the retained cross-tab. It supplies no cell-level locations,
versioned boundary geometry, or lineage between those contacts and the exact
2020 MDA source feature, so it does not qualify or clear any of the five.
Only the report's text was examined; no map image or raw project data was
used.

A second official source was examined through the National Bureau of
Statistics' GeoStatistica portal, announced on 20 October 2026
(`https://statistica.gov.md/ro/bns-lanseaza-oficial-portalul-geostatistica-12_62688.html`;
portal: `https://geo.statistica.md/`). The announcement says it maps 2024
population-and-housing census data at levels including districts, communes,
and localities, with some data available to download. The portal page is a
JavaScript shell; the web reader returned no application content. An initial
bounded local request failed DNS, but after network-enabled access was
authorized, the same official hostname resolved and returned HTTP 200. The
public ArcGIS catalog linked by the page was then read through its normal REST
search and metadata routes; 279 BNS Feature Services were enumerated.

One official polygon service, `raioane` (BNS ArcGIS item
`f16603049f434617916eb59451048538`,
`https://services-eu1.arcgis.com/Pqa2pBN0HSNd7QdR/arcgis/rest/services/raioane/FeatureServer`),
has 37 features in WKID 4026 (`MOLDREF99_Moldova_TM`). Its layer metadata was
created 23 March 2026 and last synchronized/modified 4 September 2026, but
contains no source lineage or boundary-validity date. Its attributes name
Taraclia, code `87`, type `Raion`. Comparing only names and codes against the
retained 37-feature 2020 archive found 34 exact name matches, 36 after case
folding, and one changed label: `Transnistria` in the archive versus
`Unitatile administrativ-teritoriale din stânga Nistrului` in the BNS layer.
The two other differences are capitalization only (`RIscani`/`Riscani` and
`SIngerei`/`Singerei`). This is a name-level comparison, not geometry or
source-lineage evidence. No polygons, coordinates, or cell-level comparisons
were requested or examined. The Hub site's site-level metadata says CC BY 4.0,
but the individual Feature Service item has blank license and access-information
fields; no geometry is redistributed. The new layer offers current regional
context but does not establish lineage to the consumed 2020 MDA source or
resolve the five Taraclia contacts.

The report cites Law 764/2001 on the administrative-territorial organization.
The official legislation portal's indexed result was located; the exact
report-cited listing URL and two other official listing/PDF endpoints all
returned HTTP 403 through the available web reader:
`https://www.legis.md/cautare/getResults?doc_id=138831&lang=ro#`,
`https://www.legis.md/cautare/getResults?doc_id=62962&lang=ro`, and
`https://www.legis.md/cautare/downloadpdf/62950`. The search index exposes
only a short synopsis; the law text itself was not obtained. No alternate
route was used. This is a limit on those attempted reads, not evidence that
the law or boundary data is unavailable everywhere. The report's citation to
the law remains contextual and does not substitute for the exact source
lineage.

The report also cites the Taraclia district passport
(`https://raiontaraclia.md/pasport-rajona/`). The available web reader returned
a Cloudflare verification interstitial with no document content. The read
stopped there; no browser interaction, direct HTTP retry, alternate route, or
challenge bypass was attempted. Thus that potentially relevant primary record
has been identified but not examined; the Taraclia source-applicability
question remains pending.

The district passport and the law remain identified primary-source leads,
but their attempted ordinary web-reader routes returned a verification
challenge/HTTP 403 and yielded no content. Do not route around those responses.
The GeoStatistica layer was examined through its normal public catalog and
service metadata, but supplies no source lineage or versioned boundary
validity, and its individual service record has no license text. A further
comparison should proceed only if applicable lawful use terms are clear and
the result could add source-specific evidence relevant to the original
contract. These leads remain pending, not evidence exhaustion. No coordinates
or per-key overlay need to be reconstructed for this contextual check. Any subsequent
positive candidate still requires the original source, physical, native,
selected-owner, and independent-review checks; the prior whole-scope physical
and observer runs must not be repeated without a justified changed-input
reason.

The prior attempts to access current cadastral geometry (HTTP 403), the
CUATM lookup (HTTP 404), and the direct law-PDF route (HTTP 403) remain stopped.
Those results establish only that those attempted routes were unavailable;
they do not prove every possible source route is unavailable. No credentials,
new terms, external outreach, or alternative transport was used here.
