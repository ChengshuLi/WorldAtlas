# Southern South America interior batch 5 evidence

Issue #446, branch base `702a55f8e03a2442a153eb1176919feaf84eb115`, packet ID `regional-review:afee7ce9a5601ab2`. This is a source and semantic research packet for exactly 215 issue-owned members. It does not certify the region or authorize source imports, a boundary edit, or a release.

## Files

- `issue-scope-pinned.json`, `issue-scope-pin.json`, and `scope.json` preserve the issue and its exact machine scope.
- `baseline-files.json` pins the actual baseline blobs used for identity, hierarchy, release and part checks.
- `unit-review.csv` provides one disposition/evidence note per scoped location, including names, parents, source vintage, role, license and geometry type.
- `pry-source-crosswalk.csv` links all records in the exact original Paraguay source to their current base representation.
- `source-inventory.json` records exact source hashes, retrieval dates, terms and restoration instructions.
- `ury-gb-2017.geojson` and `ury-igm-current.geojson` are byte-preserved original GeoJSON responses. Their source terms and hashes are in the inventory.
- `reproduce.py` performs positive identity/scope/crosswalk checks and a negative duplicate-roster control. It writes the deterministic `reproduction-results.json`.
- `verify-packet.py` checks retained file hashes, scope/roster equality, baseline blob pins, crosswalk totals, retained-source hashes, packet size/symlink rules and the single issue-close reference without fetching the oversized source.
- `findings.md` records the interpretation, factual limits and handoffs. `follow-up-issues.json` pins the five blocked, bounded child issues linked for subsequent work.
- `claim-receipt.json` preserves the serialized reservation accepted for this issue.

## Reproduction

Run the retained-packet checks from the repository root:

```sh
python3 data/regional-review/regional-review-afee7ce9a5601ab2/verify-packet.py
```

Run source reproduction from the repository root:

```sh
python3 data/regional-review/regional-review-afee7ce9a5601ab2/reproduce.py
```

The Paraguay GeoJSON is 45,589,273 bytes, above the 32 MiB retained-original limit, so it is not committed. Before reproduction, restore its exact bytes from the pinned URL in `source-inventory.json` to `data/regional-review/regional-review-afee7ce9a5601ab2/pry-source-temporary.geojson` and verify the listed SHA-256. The script refuses a different source version. Do not normalize, reproject or recompress it. Remove that temporary file after reproduction; the reproducible extraction ledger and restoration recipe remain.

## Interpretation

A source-ID or name match establishes identity only. The reproduction does not prove legal boundaries or geographic accuracy. In particular, the Paraguay statistical cartography is expressly reference-only; the Uruguay name comparison is not a polygon overlay; and the Southern Patagonian Ice Field is not treated as an administrative territory or sovereign claim.
