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

## Bounded alternative-source check

The European Environment Agency's metadata for EuroRegionalMap 2019 describes a
European topographic vector product at 1:250,000, with a December 2018 reference
period. It says the 2019 administrative-boundary layer used EuroBoundaryMap
2019 and that Moldova's boundaries were slightly adapted to topographic features.
This is a distinct, coarser regional product; its metadata does not link it to
the consumed 2020 MDA source or identify the 133 residual cells. The metadata
explicitly limits use to internal EEA purposes, and its direct-download link
requires Eionet authentication. I did not retrieve the dataset or its restricted
country-lineage documents, and did not attempt access. It therefore cannot be
used as a lawful geometry comparison here and does not resolve the original
source-applicability findings. [EEA EuroRegionalMap 2019 metadata](https://sdi.eea.europa.eu/catalogue/idp/api/records/ec36e79b-615a-4484-a3a5-2714dc3951c5).

## National cadastral catalogue lineage check

I used the public National Spatial Data Infrastructure (NSDI) Geoportal's
GeoNetwork metadata search to examine records for UAT II. The portal describes
itself as a platform for discovering, viewing and exchanging spatial data and
metadata. An initial search request without GeoNetwork's required
`bucket=metadata` parameter returned an empty HTTP 400; the corrected,
metadata-only POST returned 12 UAT-related catalog records. The companion UAT II
dataset record is UUID `b4bd4737-55ed-4b7b-89c7-91a08dab2a1d` and the separate
view-service record is UUID `68559473-2964-486c-bac8-0adfb71d6056`.

The UAT II dataset record's lineage statement says the registry dataset was
initially created during 2002–2005 from cartographic materials then available,
with stated precision of 10–20 m. It says updates have been performed since
2014 following cadastral boundary-establishment works, under the State Register
regulation approved by Government Decision 1518/2003 and an AGCC instruction
dated 5 September 2016; updates are made as needed from boundary-establishment
files. Its record publication date is 27 January 2012; its metadata was revised
9 October 2026. The record has no boundary-validity date, no dated 2020
snapshot, no explicit source link to the consumed geoBoundaries 2020 feature, and
no per-cell mapping. These lineage statements identify a potentially relevant
official source family, but do not prove which revision the 2020 MDA source
represents or whether the service's current features match it.

The separate record identifies a UAT II WMS view service, EPSG:4026, with a
creation date of 31 May 2016, publication date of 1 January 2004, and revision
date of 9 October 2026. Its published layer is `w_rsuat:mv_uat1`; the abstract
describes named polygon boundaries for districts, Chișinău, Bălți and Găgăuzia.
The linked GetCapabilities response (retrieved 23 October 2026) confirms WMS
1.3.0, the layer name, and service-level `Fees=NONE` and
`AccessConstraints=NONE`. This describes access to the service, not reuse rights
for its underlying dataset. The dataset record marks access/use conditions as
unknown. The separate 2025 INDS monitoring table lists view service availability
for administrative unit levels I and II, but no WFS or file-based download.

I then used the WMS's advertised `GetFeatureInfo` operation, in `text/plain`
format, for three representative existing MDA residual centers. The request
used layer `w_rsuat:mv_uat1`, WMS 1.3.0, CRS:84, a 3-by-3 pixel identify window
with a 0.0002-degree half-width around each center, and a feature limit of five.
The Taraclia sample returned current attributes `ido=2031`, `CUATM=8700`; the
Ștefan Vodă sample returned `ido=2030`, `CUATM=8500`. A representative
Transnistria sample returned no feature. These are current-service observations
only. They neither establish which 2020 source revision was consumed nor
explain the full residual groups. In particular, a current label match does
not resolve archived source membership, and one no-feature result does not
distinguish source omission from service coverage.

Python's TLS validation failed locally before reaching the service; system
`curl` with normal certificate verification succeeded. An initial JSON identify
response included complete feature geometry despite the small point request. I
did not save or redistribute that response. I switched to the service's
`text/plain` identify representation, which returned selected attributes and a
geometry summary but no coordinate arrays. No GetMap, WFS, dataset download,
bulk extraction, or 133-cell identify run was performed. Dataset reuse terms
remain unknown, so these results are retained as limited source observations;
they are not a basis for redistributing geometry.

The metadata and three current-service samples provide useful official context,
but the consumed 2020 snapshot, source-feature identity, current-to-2020
geometry relation, and per-cell applicability remain unresolved. The samples
are heterogeneous and cannot classify the 133 residual cells. No MDA cell,
owner, hold, qualification, repair, or credit changed. Exact parameters and
returned attributes are recorded in
`research/official-uat2-cadastral-catalogue-20261023.json`.

The exact catalog records were saved only in the task's temporary directory to
avoid redistributing personal contact fields; the response hashes are
`db336666cb19ad53c49c8b3a38ad046b2e11ecd4abd1e47ce8f7ada842420f6a` (WMS
service metadata, 21,884 bytes),
`9e2c2543d43152c44481062ef0bb047b6e263d3f127f11c1ecfed9c5a3666aa1` (UAT II
dataset metadata, 23,201 bytes), and
`7cbb231ce4b52f7cfb306d7e08857fd6367fa7a9328f7c851ce4186a74e3ba29` (WMS
GetCapabilities, 264,946 bytes). The official catalog entries are [UAT II
dataset metadata](https://geoportalinds.gov.md/geonetwork/srv/api/records/b4bd4737-55ed-4b7b-89c7-91a08dab2a1d)
and [UAT II view-service metadata](https://geoportalinds.gov.md/geonetwork/srv/api/records/68559473-2964-486c-bac8-0adfb71d6056).

## Original-contract and source-family reconciliation

The authenticated original contract at issue [#2582](https://github.com/ChengshuLi/WorldAtlas/issues/2582)
requires each interval to be either a qualified additive repair to its recorded
location or a documented exception, with actual selected-native conservation
and source/physical witness checks; existing river water remains
location-owned. It does not make exact identification of a universal 2020
official boundary snapshot a predicate, and the 1,853-cell upstream-match
subset was described as a conservative first scope rather than a universal
source-match rule. This distinction matters: absence from the archived full
source is adverse evidence to interpret, not an automatic failed predicate.

The accepted full-scope native and retained-witness results are already in the
public record; this review did not repeat them. Native diagnostics supported
1,918 of the 1,986 original cells and held 68 UKR source contacts. The other 65
are additional research holds, not native failures. The retained physical join
reports physical support for all 1,986 cells, zero missing physical witnesses,
zero inland-water overlap, and exact vector joins for all 539 intervals. It
also reports zero direct owner assignments for the 68 UKR contacts. These facts
do not decide source applicability or alter ownership. Sources: merged PR
[#2583](https://github.com/ChengshuLi/WorldAtlas/pull/2583) and its retained
`mda-retained-witness-join.json.gz` (Git blob
`84e7454b0cd4af9e44cea2ab3f3fece9e7911df7`); the original-source comparison
is retained in PR [#2675](https://github.com/ChengshuLi/WorldAtlas/pull/2675),
`source-version-key-comparison.json.gz` (Git blob
`db6472f961e451784175d2c832f8216c53b6d937`).

The source-family crosswalk confirms that the 68 contacts are reproduced by
the retained original UKR source family, not by a newly substituted current
layer: 62 contact the archived Odessa feature and 6 the archived Vinnytsia
feature. Those archived records are part of the retained 2017 UKR family; the
source comparison identifies their feature IDs as
`gb:UKR:ADM1:14850775B53240635394722` and
`gb:UKR:ADM1:14850775B93300237551625`. Each contact remains ownerless. The
original source-family comparison does not establish legal jurisdiction or a
territorial exclusion.

| Pending source stratum | Count | Retained source result | Decision-relevant question still open |
| --- | ---: | --- | --- |
| MDA match plus UKR contact | 46 | Unique matching archived full MDA target and a separate archived UKR source contact; 44 Odessa and 2 Vinnytsia contacts. | Whether the two source families' exact recorded witnesses justify the MDA repair for each key under the source-specific original contract; contact alone does not assign ownership. |
| MDA-only archived-source nonmatch | 65 | Center belongs to the consumed simplified MDA feature but lies outside its matching archived full-resolution MDA feature; no UKR contact. | Whether the source-version displacement is compatible with the consumed source's documented precision and available applicable local evidence. The original MDA source remains a real source witness; full-resolution nonmembership alone is not a universal veto. |
| UKR contact outside archived MDA source | 22 | UKR archived-source contact and no matching archived full MDA membership. | Whether the source contact is applicable to each recorded MDA location or reflects source-family/version displacement. One current Transnistria no-feature result cannot answer this for the group. |

The exact target cross-tab and feature IDs above locate the issue without
extrapolating the three current WMS samples. For the 65, the UAT II catalog
states 10–20 m source precision and updates since 2014 from boundary
establishment files, but does not identify the consumed 2020 MDA revision.
That is relevant source context, not a proven explanation of any particular
cell displacement. The 2024 BNS layer is also current context only. For the 68,
the exact archived UKR contacts and lack of owner assignments are now
authenticated; no source evidence examined so far establishes whether each
contact displaces, contradicts, or is compatible with the recorded MDA
location. The three WMS identify examples do not resolve this.

Accordingly, this crosswalk narrows the scientific question but does not
support a defensible class-wide disposition. All 133 remain pending with all
native holds unchanged. A future disposition must assess the applicable
source/physical witnesses at the exact interval or a genuinely shared source
predicate, and may not turn the 65 full-source nonmatches or 68 ownerless
contacts into automatic failures. No geometry, physical, owner, or native
diagnostic was rerun for this reconciliation, and no cell, qualification,
repair, unresolved outcome, or credit was changed.


## Exact source-family spatial follow-up

The retained source-family comparison was followed by a bounded check using the
exact original center coordinates, not the modern UAT II service. All 68 original
UKR-contact centers were tested against every feature of the retained full-source
UKR ADM1 family (27 features; 761,290 bytes; SHA-256
`4a5947e7497574d51f93255dfa7e03dce0c7acf6ecee52d25773a5205854a399`). All 68
remain inside exactly one full-source UKR feature: 62 Odessa Oblast and 6
Vinnytsia Oblast; zero misses and zero multi-feature hits. The foreign contact
is therefore present in the retained full UKR family too. This confirms source
family persistence, not legal ownership or which MDA source membership governs.
The 46/22 MDA-source split remains intact.

For the 65 MDA-only keys, the correct comparison is the exact consumed simplified
source `retained/gb-MDA-ADM1-000.bin` (317,753 bytes, SHA-256
`b9f85b5b94d053cd3fc7f60d9823ec2ba9cd37b780f4935a778203d67cb5f523`) against
the archived full upstream source `primary/source-archive/upstream-mda-37.geojson`
(525,940 bytes, SHA-256
`ca7378f66c2a635e2a0ceccf58cfa711c6390bebb13ee656efa5d72c4dda45de`). All 65
centers uniquely hit their same-named target in the consumed simplified source
and hit no feature in the complete archived upstream family. A bounded nearest
ring-segment diagnostic found simplified-boundary inside-depth median 11.553 m
(p90 40.728 m; range 0.128–69.062 m) and full-boundary outside-depth median
17.626 m (p90 38.930 m; range 0.045–60.590 m). Distances use a local
equirectangular tangent-plane approximation and are diagnostic only; they are not
position-accuracy estimates. The original archive metadata identifies UNHCR and
OCHA FISS sources and representative year 2020, and its shapefile history dates
processing to 2019, but gives no quantitative positional accuracy or scale.
Thus these offsets demonstrate a near-boundary source-version disagreement, not
which representation is more accurate. The 2024 cadastral lineage and current
UAT II stated precision cannot be retroactively assigned to this source pair.

The full methods, exact pins, per-key distance diagnostics, and explicit limits
are recorded in
`research/source-family-spatial-followup.json` (SHA-256
`de3e1e3034af7ad80ee67953241d8b2c2a4f5037877f8a365c551a045a18de8f`). This is
additional research evidence only. No owner, hold, qualification, repair, or
acceptance changed; all 133 residuals remain pending.


## Bounded current UAT II point-identify follow-up

To test whether an independent current service could add useful center-level
evidence, I queried all 133 exact held centers once each through the official UAT II
WMS `GetFeatureInfo` service (`w_rsuat:mv_uat1`). Requests used WMS 1.3.0,
`CRS:84`, a 3×3 pixel view centered at I=1/J=1, a BBOX of ±0.0002 degrees,
`text/plain`, and a one-second sequential delay. All 133 returned HTTP 200. I
retained only selected IDs, administrative names, CUATM and parent attributes;
response bodies and geometry summaries/arrays were discarded.

The current service returned a feature whose normalized name matched the original
MDA target for 60/65 MDA-only keys, 40/46 MDA-match-plus-UKR-contact keys, and
8/22 UKR-contact/outside-full-MDA keys. It returned no feature for the other 25
keys (5, 6, and 14 respectively), and no conflicting name for any key. The
center pixel covers approximately 9.89–10.40 m east-west by 14.83 m north-south
at these latitudes. The service metadata states 10–20 m precision and says the
dataset has been updated since 2014, but provides no per-feature valid-time or
link to the consumed 2020 MDA release. The pixel footprint and service precision
are comparable to the measured 65-key source-version offsets.

These results add independent current-name corroboration for 108 centers, but
cannot identify the side of a precise administrative boundary or decide which
2020 source representation governs. The 25 no-feature results are not evidence
of territorial absence: coverage/representation for those centers is not
established. Therefore this check does not resolve any held class by itself. It
also does not create an exact-2020 snapshot requirement. Full requests, retained
non-geometric attributes, counts, pins, and limitations are in
`research/uat2-133-attribute-identify-followup.json` (SHA-256 `ddadab445a4a537c51cb73c6232c8c34a0fe30ae0eb6a2665cdd26e09172796b`). No owner,
hold, qualification, repair, or acceptance changed; the 133 remain pending.


## Proposed disposition from the combined evidence

The existing independent reviewer assessed the original issue #2582 criteria,
retained whole-scope native/physical results, exact MDA/UKR source-family tests,
and 133-point current UAT II attribute comparison. It supports a bounded
**65-key positive-repair candidate**: all 65 uniquely hit the same-name/ISO
feature in the consumed simplified MDA source, have no UKR contact, are within
the existing 1,918 native-supported cells, and share the whole-scope physical
support. The archived full MDA nonmatches remain adverse version evidence, but
the original contract does not require a universal full-source match. The 60
current UAT name matches corroborate current labels; 5 no-feature results do not
reverse the consumed-source membership. The exact current-E observer now confirms all 65 are owner-zero, matching the full residual partition of 133 owner-zero and 1,853 owned cells. This binding uses DATA commit `0e50bd281afec27ce32fac8dcb4dfe2401f94b6c`, CODE commit `008cd5c3932ed9ffd9df55487017a7ddd2fbe8d0`, and selected reference `geography:final:e8aa1f2bb536d87df8c87c3061b345338f282053ded21d7102263463e673f551`. It is an ownership observation only, not qualification. The 65 still need the normal additive construction route, exact-head review, and one stock delivery; they are not yet counted.

The same reviewer supports a separate **68-key researched-unresolved proposal**
with holds intact. All 68 UKR contacts persist in full UKR source; 46 also match
full MDA while 22 do not. The current UAT service returns same-target labels for
48 and no feature for 20, without resolving cross-source applicability. The five
Taraclia cells have regional adjacency context but no cell-specific source link.
Ordinary Law 764/passport routes yielded 403/verification-interstitial limits;
no bypass or exhaustive-search claim is made. The key-level adverse evidence and
research basis remain explicit in
`research/mda-133-disposition-proposal.json` (SHA-256 `f1cbb66e82c0e07e55129268c97507f41ce23fc83f3df1f6c01580cacb2e8e23`).

No repairs, unresolved completions, hold removals, or package completion are
claimed here. The proposal covers 65 positive candidates plus 68 unresolved
candidates within the full 1,986-cell, 539-interval, 16-owner scope. Current E
binding is complete for all 1,986 keys, but all 133 remain pending construction or
unresolved disposition review/delivery and root acceptance. The exact owner
observation is in `research/selected-owner-observation-001.json`.
