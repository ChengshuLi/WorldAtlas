# DJI original repair operations

## Pinned checkout

- Branch: `engineering/djibouti-original-repair-20261019-01a154ad`
- Input/code commit: `261e709ac9e1837b3399537f9f53cfa6550e3a01`
- Worker identity: `01a154ad-085e-738b-95cf-eb6b663b400f`

## Source-batch extractor sparse input

The current-main reader expects the plain file
`coordination/engineering/global-current-cell-work-queue-20261014/normalized-source-seams.json`.
The first extractor invocation encountered ENOENT on the `.json.gz` spelling;
the full stderr was not retained. I added the existing plain `.json` path to
this worktree's sparse patterns. No reader, source, or shared script was edited,
and no compressed alias was created. Its exact Git object and content hash are
recorded in `source-identity-v1/source-identity-joins.json`.

Successful command:

```sh
node coordination/engineering/global-current-cell-work-queue-20261014/source-batch-intervals.mjs \
  gb-DJI-ADM2--repair-evaluation \
  coordination/engineering/djibouti-original-repair-20261019/source-batch-intervals-v1
```

Result: 683 land cells, 394 intervals, nine targets, across blocks 029 and 030.

The independent selected-owner observer was run at the same commit. Its result
is `selected-owner-observation-v1.json`; it is observational only and reports
zero base, additive, and effective owners for all 683 queried cells.

## Identity evidence boundary

`source-identity-v1/source-identity-joins.json` joins nine original ADM2
Features to their exact queue lineage target IDs and records each queue
`province_id` parent reference. ADM1 names are only candidate context matches
to the parent ID slug: the source ADM2 Features expose no parent identifier.
Both full original DJI source FeatureCollections are retained beside the join
report, including all six ADM1 and eleven ADM2 Features and roster owners.

This evidence establishes identity and queue relationships only. It does not
establish current source applicability, administrative authority, or physical
support. Do not use ADM1 as a negative witness without an exact applicability
finding. The positive source-family roster is the complete ADM2 family.
