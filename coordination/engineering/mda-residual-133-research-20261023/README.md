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

On 2026-10-23, the Romanian-language Moldovan government announcement was
retrieved from:

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
applicability. The next useful step is targeted examination of the already
retained MDA/UKR source-context records for the three adverse classes. Any subsequent
positive candidate still requires the original source, physical, native,
selected-owner, and independent-review checks; the prior whole-scope physical
and observer runs must not be repeated without a justified changed-input
reason.

The prior attempts to access current cadastral geometry (HTTP 403), the
CUATM lookup (HTTP 404), and the direct law-PDF route (HTTP 403) remain stopped.
Those results establish only that those attempted routes were unavailable;
they do not prove every possible source route is unavailable. No credentials,
new terms, external outreach, or alternative transport was used here.
