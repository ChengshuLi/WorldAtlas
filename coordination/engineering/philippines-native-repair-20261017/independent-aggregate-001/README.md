# Philippines: original aggregate intent and exact source ancestry

Read-only review at accepted baseline `d4968ddc37aa3aa6105e9610c9e6fadbb368ba14`. No author-workspace edits, allocation, source/country screens, or native/physical replay.

## Result

All five unions have exact, legitimate **recorded source-member-to-target ancestry**. Across all 73 members, current `source_member_ids`, original `semantic-report.changes[].replaces`, original `city_membership_audit`, semantic-followup source atoms, and the supplied original-scope roster agree. Every member resolves uniquely in the complete pinned PHL ADM3 product. All five complete target records are unchanged from original target commit `ffa32416fd946ac89da621d02b554ca27733e688`.

This establishes the original aggregate identity, not a current/legal city boundary or semantic approval. Do not replace these original members with an assumed contemporary city footprint.

## Actual construction

`scripts/semantic-locations.py` forms Natural Earth city candidates from qualifying type/curated name and the largest polygon component, subject to the compactness guard. Metro Manila instead starts with the union of Natural Earth ADM1 records whose region is National Capital Region. Candidates are considered in descending geometry area. Within a 0.15-degree buffered spatial query, an unretired prepared member qualifies if candidate overlap is at least 0.5 **or** its normalized parent name matches the candidate name/code. The dominant reference-owner group is selected. `merge()` unions the complete prepared member geometries, requires one owner, and records old member IDs; it does not clip the union to the candidate city boundary.

- Cebu: 15 members. All 15 have named-parent matches, none reaches 0.5 overlap, and 11 have recorded overlap zero. Cebu City itself has recorded overlap 0.40387. Members include Asturias, Balamban, Carmen, Cebu City, City of Naga, City of Talisay, Compostela, Consolacion, Cordova, Danao City, Lapu-Lapu City, Liloan, Mandaue City, Minglanilla and Toledo City.
- Iloilo: 21 members. All 21 have named-parent matches; only 2 reach 0.5 overlap, 19 qualify by parent match below 0.5, and 15 have overlap zero. This is the preserved 21-municipality/city union, not the Iloilo City atom alone.
- Cotabato: 4 members. Cotabato City has 0.73414 overlap; Libungan, Midsayap and Pigkawayan each have zero overlap and named-parent matches.
- Cagayan de Oro: 2 members, both selected by overlap. Cagayan de Oro City has 0.78849; Tagoloan has 0.51448. No named-parent matches.
- Metro Manila: 31 members, all selected by overlap and no named-parent matches. Cainta is explicitly included at 0.72516. Preserve the exact original 31-member set, including the individually named Manila source districts.

The overlap figures above are the original retained construction-audit observations against then-prepared inputs, not new computations against substituted current inputs.

## Holds and comparison caveats

All five current location decisions/followup statuses remain `open`, specifically because aggregate-member scope requires independent functional settlement evidence. Their declared reference vintage is `Undated modern reference`, with license attribution delegated to underlying sources. Existing hierarchy has open semantic review; Cotabato and Metro Manila have `source-parent-role-unresolved` parent diagnostics. Cebu, Iloilo and Cagayan de Oro have only representative-point diagnostic passes, which expressly do not establish whole-footprint or semantic approval.

The constructor writes `coverage_error_degrees2: 0` as a constant. That field is **not a measured full-raw-source-versus-current-target comparison** and must not be reused as such. A bounded Shapely comparison of each complete raw member union with its current target finds all five geometries valid but none topologically equal. Raw-union coverage of current targets is Cebu 99.1112%, Iloilo 99.5140%, Cotabato 98.6906%, Cagayan de Oro 98.0170%, Metro Manila 98.3725%. These planar longitude/latitude area fractions are descriptive diagnostics only, not physical/native/legal proof or permission to modify a target. Full member-by-member fractions and both directional differences are retained in the JSON.

No package qualification constructor or negative-control execution was performed. This review supports retaining the exact source unions as original target evidence; it supplies no newly qualified physical/native result and does not release semantic holds. The old Congo/PHL ancestry-refusal log inspected during research was a Git registration-anchor ancestry refusal, not evidence against these member sets, and is not used as a current result.

## Complete source custody

Independently decoded complete retained products, verified catalogue bytes and SHA-256, checked full feature counts and unique source IDs:

- PHL ADM1: 17 features, 2,812,222 bytes; SHA-256 `8eeef6a9a525a81a647dcaac85e1337b990fc527c4a0e9c70556d5b0905be087`
- PHL ADM2: 87 features, 3,140,454 bytes; SHA-256 `fa77b9f17db2e419acaae714a935f7812be4409e2983675d34020e8426a3e189`
- PHL ADM3: 1,647 features, 7,071,267 bytes; SHA-256 `2ece3d44a5c6a2afb385ffbf3a6b88d83e4d3a3e7eed9a52cb3be1bc59e289fc`

Total 13,023,943 decoded bytes. Registry claims represented year 2020; canonical roles Regions / Provinces / Municipalities; source credits NAMRIA, PSA and OCHA Philippines; declared license CC BY 3.0 IGO. Consumed product URLs are the pinned **simplified** GeoJSON editions: ADM1/ADM2 at geoBoundaries `41af8f1`, ADM3 at `9469f09`. Metadata update/build dates are not new effective-date proof. Entire original metadata and custody descriptors are in JSON.

## Evidence

- `aggregate-intent-review.json`: complete Git input pins; complete metadata/catalogue entries; exact checks; full members, names and retained selection observations; current target properties and hierarchy chains; existing semantic holds; measured union/member comparisons.
- `review_aggregates.py`: bounded read-only reproduction, using immutable `git show` inputs only. Writes the local JSON report, never the author workspace.
- `semantic-locations.py`: pinned constructor copy used for inspection only, not executed.

The report deliberately does not adopt or recalculate cell screening counts or the parent worker's separate 932-atom/native/physical scope.

## Durable packet note

This preserves the exact independent investigator report (SHA-256 `4ae8dcd6ccd3bbb3fe3642756cb2fa7feef971679a24062945198b5650b9bcb3`). Its local screening file supplied only target identities, part locations and proposed member sets. The package's frozen-queue, source-stage and accounting independently reconstruct those identities and all original keys from authenticated original records. `method/preserve-interpretation.py` is the package's fresh-output-only producer for the authenticated original construction, decisions and parent diagnostics; the investigator's local diagnostic writer is not presented as a production reproduction entry point. No scratch helper execution is required to consume this report.
