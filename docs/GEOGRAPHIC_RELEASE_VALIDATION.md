# Geographic reference release validation

The geographic migration changes modern reference names and memberships without rewriting the identity registry, moving historical evidence, changing location footprints, or asserting ancient administrative memberships. Structural publication is separate from semantic geographic approval; open continent review findings remain open.

Run the complete local gate with:

```sh
node --test test/geographic-release-preparation.mjs
```

This test uses SQLite with foreign keys enabled and every real `drizzle/*.sql` migration in sorted order, including geographic reference release constraints and the unsettled-rank migration. Its D1 adapter calls the actual record import, release staging, release finalization, paging, and entity profile services. It does not substitute a simplified schema or manufacture successful publication by writing a published status directly.

The test regenerates the complete release set in a temporary directory and compares it with the checked-in preparation output. Every batch must have the pinned byte hash, fit the 1 MiB import limit, and fit the 250-row service limit. All immutable catalog batch hashes and the original archive hash must remain unchanged.

It imports the entire original catalog, including archived geographic identities, through the record service, then stages the entire generated release set through the corresponding services. Before publication, reference memberships must remain invisible. Every original identity and source column is compared with the original catalog. Archived original claims remain on their original IDs in the original archive; its full byte hash is checked before and after preparation and publication. Separately, test-only dated evidence is imported through the record service and compared before and after publication to exercise preservation of existing hosted records.

For both releases, the test independently reconstructs canonical SHA-256 hashes using UTF-8 binary identifier ordering. It checks every membership, every active adjacent-tier parent, all six tier counts, every source decision digest, the migration digest, location identity preservation, and unchanged footprint hashes. It checks the entire crosswalk against the actual before/after inventory: all created, retired or merged, renamed, and reparented entities must be accounted for exactly once per change type. Merge endpoints must stay in tier and target a surviving identity. The actual service then hashes all stored rows across pagination boundaries before publishing each release.

A separate mutation test translates a real location polygon, preserving ring closure and topology, while preserving every stable ID in a temporary source fixture. Preparation must reject the changed footprint against the immutable pre-migration pin before writing either release. The actual source geometry remains unchanged.

Publication must preserve the baseline as an explicitly selectable older release. The latest profile overlays current reference names and parents while exposing original registry fields. Every renamed or reparented profile is checked against both releases. Dated preferred names take precedence over reference labels; unsupported ancient names remain unknown. An illustrative dated population record remains attached to its original location. All active memberships and all crosswalk rows are read back through the public paging functions, with exact inventory coverage and ordering checks. Published membership mutation and release deletion must fail.

This is a local exhaustive data and service gate, not a hosted deployment or browser test. It does not verify the Sites audience, remote D1 upload, remote object storage, interactive navigation, or independently approve any polygon's semantic suitability. Those remain separate release gates.

## Recorded dataset

The reviewed preparation contains 16 new group identities, 84,749 reference membership rows, and 470 explicit crosswalk rows. The baseline retains 84,733 geographic identity rows, including archived identities. Both releases have 49,614 active locations and six continents. Baseline group counts are 5,220 provinces, 489 areas, 66 regions, and 29 subcontinents. Reviewed group counts are 5,132 provinces, 470 areas, 66 regions, and 29 subcontinents. Thus the reviewed hierarchy has 5,703 active groups. These counts describe the pinned preparation, not a declaration that all groups have completed independent semantic review.

Verified on 2 October 2026: the complete dataset/service pass succeeded with 9 tests (59 seconds), and the separate same-ID footprint mutation gate succeeded with 1 test (5 seconds). Logs: `/workspace/scratch/geographic-release-validation-final.log` and `/workspace/scratch/geographic-release-mutation-final.log`. The mutation test used `--test-name-pattern='same-ID footprint'`; it exercised the added pre-migration footprint guard against real source data in a temporary fixture. No hosted deployment or browser validation is asserted by these results.
